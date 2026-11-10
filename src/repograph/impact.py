"""Bounded reverse dependency analysis with an auditable witness for each result."""

import hashlib
import heapq
from collections import defaultdict

from repograph.aliases import AliasResolver
from repograph.config import Settings
from repograph.discovery import Discovery, RepositoryError, read_source
from repograph.git_service import GitService
from repograph.graph import GraphService
from repograph.models import Diagnostic, ImpactedNode, ImpactEvidence, ImpactReport
from repograph.service import pagination


class ImpactService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.graph = GraphService(settings)

    def _freshness(self, snapshot) -> tuple[str, list[Diagnostic]]:
        discovery = Discovery(self.settings)
        current = set(discovery.files())
        indexed = {n.path: n.content_hash for n in snapshot.nodes if n.kind == "file"}
        diagnostics = list(discovery.diagnostics[:100])
        if not discovery.complete:
            return "unknown", diagnostics
        if current != indexed.keys():
            return "stale", [
                Diagnostic(
                    code="stale_graph",
                    message="Indexed file inventory differs from current repository",
                )
            ]
        total = 0
        for path in sorted(current):
            try:
                source = read_source(self.settings, path)
                total += len(source)
                if total > self.settings.max_total_bytes:
                    return "unknown", [
                        Diagnostic(
                            code="freshness_limit",
                            message="Freshness check reached the aggregate byte limit",
                        )
                    ]
                if hashlib.sha256(source).hexdigest() != indexed[path]:
                    return "stale", [
                        Diagnostic(
                            code="stale_graph",
                            path=path,
                            message="Indexed content differs from current repository",
                        )
                    ]
            except RepositoryError as error:
                return "unknown", [Diagnostic(code=error.code, message=str(error), path=path)]
        try:
            aliases = AliasResolver(self.settings, sorted(current))
        except RepositoryError as error:
            return "unknown", [Diagnostic(code=error.code, message=str(error))]
        if aliases.fingerprint != snapshot.resolution_fingerprint:
            return "stale", [
                Diagnostic(
                    code="stale_alias_config",
                    message="Alias configuration changed; re-index required",
                )
            ]
        return "current", diagnostics + aliases.diagnostics[:100]

    def analyze(
        self,
        paths: list[str] | None = None,
        node_ids: list[str] | None = None,
        baseline: str | None = None,
        snapshot_id: str | None = None,
        before_snapshot_id: str | None = None,
        max_depth: int = 10,
        max_nodes: int = 5000,
        offset: int = 0,
        limit: int = 100,
        *,
        _full: bool = False,
    ) -> ImpactReport:
        pagination(offset, limit)
        if not 0 <= max_depth <= 100 or not 1 <= max_nodes <= 200_000:
            raise RepositoryError(
                "invalid_impact_limit", "max_depth must be 0..100; max_nodes must be 1..200000"
            )
        if len(paths or []) > 200 or len(node_ids or []) > 200:
            raise RepositoryError(
                "too_many_seeds", "At most 200 paths and 200 node IDs may be requested"
            )
        primary = self.graph.snapshot(snapshot_id)
        snapshots = [primary]
        if before_snapshot_id and before_snapshot_id != primary.id:
            snapshots.append(self.graph.snapshot(before_snapshot_id))
        diagnostics = []
        complete = True
        revision = None
        target = None
        if paths is None and not node_ids:
            changes = GitService(self.settings)._analyze(baseline, "WORKTREE")
            paths = sorted(
                {p for change in changes.changes for p in (change.path, change.old_path) if p}
            )
            revision, target = changes.baseline, changes.target
            diagnostics.extend(changes.diagnostics[:100])
            complete = changes.complete
        changed_paths = sorted(set(paths or []))
        # No filesystem reads are needed to normalize seed names, including deleted paths.
        from repograph.discovery import normalize_relative

        changed_paths = sorted({normalize_relative(path) for path in changed_paths})
        nodes = {}
        reverse = defaultdict(list)
        children = defaultdict(set)
        unresolved = set()
        for snapshot in reversed(snapshots):
            nodes.update({node.id: node for node in snapshot.nodes})
            for edge in snapshot.edges:
                if edge.relation == "contains" and edge.target is not None:
                    children[edge.source].add(edge.target)
                if edge.target is None:
                    unresolved.add((snapshot.id, edge.id))
                    continue
                evidence = ImpactEvidence(
                    edge_id=edge.id,
                    snapshot_id=snapshot.id,
                    source=edge.source,
                    target=edge.target,
                    relation=edge.relation,
                    path=edge.path,
                    line=edge.line,
                    confidence=edge.confidence,
                )
                reverse[edge.target].append(evidence)
        seeds = set(node_ids or [])
        missing_nodes = seeds - nodes.keys()
        if missing_nodes:
            raise RepositoryError(
                "node_not_found", "An impact seed is absent from the selected snapshots"
            )
        pending = [seed for seed in seeds if nodes[seed].kind in {"file", "class", "interface"}]
        while pending:
            for child in children[pending.pop()]:
                if child not in seeds:
                    seeds.add(child)
                    pending.append(child)
                    if len(seeds) > max_nodes:
                        raise RepositoryError(
                            "impact_seed_limit", "Container members exceed the node limit"
                        )
        for path in changed_paths:
            matches = {node.id for node in nodes.values() if node.path == path}
            if not matches:
                complete = False
                diagnostics.append(
                    Diagnostic(
                        code="unindexed_change",
                        path=path,
                        message="Path is unindexed; use a before snapshot for deleted/renamed code",
                    )
                )
            seeds.update(matches)
        if len(seeds) > max_nodes:
            raise RepositoryError("impact_seed_limit", "Seed nodes exceed the traversal node limit")
        freshness, freshness_diagnostics = self._freshness(primary)
        diagnostics.extend(freshness_diagnostics)
        complete = complete and freshness == "current"
        if unresolved:
            diagnostics.append(
                Diagnostic(
                    code="unresolved_dependencies",
                    message=f"{len(unresolved)} unresolved edges may hide dependents; "
                    "results are not exhaustive",
                )
            )
        # Contains edges propagate ownership without counting a semantic dependency hop.
        # Each node retains one shortest witness, preferring static over heuristic ties.
        best = {seed: (0, 0) for seed in seeds}
        witnesses: dict[str, tuple[str, list[ImpactEvidence]]] = {
            seed: (seed, []) for seed in seeds
        }
        queue = [(0, 0, seed) for seed in sorted(seeds)]
        heapq.heapify(queue)
        depth_limited = False
        node_limited = False
        while queue:
            depth, rank, node_id = heapq.heappop(queue)
            if best.get(node_id) != (depth, rank):
                continue
            for evidence in sorted(
                reverse[node_id], key=lambda e: (e.source, e.edge_id, e.snapshot_id)
            ):
                candidate = evidence.source
                next_depth = depth + (evidence.relation != "contains")
                next_rank = max(rank, int(evidence.confidence != "static"))
                score = (next_depth, next_rank)
                if candidate in best and best[candidate] <= score:
                    continue
                if next_depth > max_depth:
                    depth_limited = True
                    continue
                if candidate not in best and len(best) >= max_nodes:
                    node_limited = True
                    continue
                origin, witness = witnesses[node_id]
                if len(witness) >= 200:
                    depth_limited = True
                    continue
                best[candidate] = score
                witnesses[candidate] = (origin, [*witness, evidence])
                heapq.heappush(queue, (*score, candidate))
        if depth_limited or node_limited:
            complete = False
            diagnostics.append(
                Diagnostic(
                    code="impact_limit", message="Impact traversal reached a depth or node limit"
                )
            )
        affected = []
        for node_id, (depth, rank) in best.items():
            origin, evidence = witnesses[node_id]
            affected.append(
                ImpactedNode(
                    node=nodes[node_id],
                    depth=depth,
                    classification="changed"
                    if node_id in seeds
                    else "context"
                    if depth == 0
                    else "direct"
                    if depth <= 1
                    else "transitive",
                    confidence="heuristic" if rank else "static",
                    origin=origin,
                    evidence=evidence,
                )
            )
        affected.sort(
            key=lambda item: (item.depth, item.node.path, item.node.qualified_name, item.node.id)
        )
        modules = sorted({item.node.path for item in affected})
        return ImpactReport(
            snapshot_ids=[s.id for s in snapshots],
            baseline=revision,
            target=target,
            changed_paths=changed_paths,
            seeds=sorted(seeds),
            affected=affected if _full else affected[offset : offset + limit],
            total=len(affected),
            next_offset=offset + limit if offset + limit < len(affected) else None,
            affected_modules=modules if _full else modules[:200],
            total_modules=len(modules),
            unresolved_dependencies=len(unresolved),
            freshness=freshness,
            complete=complete,
            diagnostics=diagnostics[:200],
        )
