"""Read-only, in-memory proposed edits to already indexed source files."""

import hashlib
from typing import Literal

from pydantic import BaseModel, Field

from repograph.aliases import AliasResolver
from repograph.config import Settings
from repograph.discovery import RepositoryError, normalize_relative, read_source
from repograph.graph import GraphBuilder, GraphService
from repograph.impact import ImpactService
from repograph.models import Diagnostic, GraphSnapshot
from repograph.parsing import parse_source


class ProposedFile(BaseModel):
    path: str = Field(max_length=1024)
    content: str | None = Field(default=None, max_length=1_000_000)


class ScenarioReport(BaseModel):
    kind: Literal["selected_scope", "proposed_content"]
    intent: str = ""
    assumptions: list[str] = Field(default_factory=list)
    base_snapshot_id: str
    proposed_snapshot_id: str | None = None
    paths: list[str]
    added_nodes: int = 0
    removed_nodes: int = 0
    modified_nodes: int = 0
    changed_node_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Hypothetical impact is not an observed behavior change or a guarantee.",
            "No files are written and no repository code is executed.",
        ]
    )


class ScenarioGraph:
    def __init__(self, snapshots: list[GraphSnapshot]):
        self.snapshots = {s.id: s for s in snapshots}
        self.primary = snapshots[0]

    def snapshot(self, snapshot_id: str | None = None) -> GraphSnapshot:
        if snapshot_id is None:
            return self.primary
        if snapshot_id not in self.snapshots:
            raise RepositoryError("snapshot_not_found", "Snapshot is not part of this preview")
        return self.snapshots[snapshot_id]


class ScenarioImpact(ImpactService):
    def _freshness(self, snapshot):
        # Freshness applies to the checked base tree, not to imaginary on-disk edits.
        return "current", [
            Diagnostic(
                code="hypothetical_graph",
                message="In-memory graph from proposed content; freshness refers to the base tree.",
            )
        ]


def prepare_preview(
    settings: Settings, graph: GraphService, proposals: list[ProposedFile], snapshot_id: str | None
):
    base = graph.snapshot(snapshot_id)
    analyzer = ImpactService(settings)
    freshness, _ = analyzer._freshness(base)
    if freshness != "current":
        raise RepositoryError(
            "scenario_stale_base", "Re-index current source before previewing edits"
        )
    edits = {}
    total_proposed = 0
    for proposal in proposals:
        path = normalize_relative(proposal.path)
        if path in edits:
            raise RepositoryError("invalid_scenario", "Duplicate proposed file paths")
        raw = proposal.content.encode("utf-8") if proposal.content is not None else None
        total_proposed += len(raw or b"")
        if raw is not None and (b"\x00" in raw or len(raw) > settings.max_file_bytes):
            raise RepositoryError("invalid_scenario", "Proposed source is binary or oversized")
        edits[path] = raw
    if total_proposed > min(2_000_000, settings.max_total_bytes):
        raise RepositoryError("scenario_byte_limit", "Proposed content exceeds the byte budget")
    indexed = {n.path: n for n in base.nodes if n.kind == "file"}
    if edits.keys() - indexed.keys():
        raise RepositoryError(
            "scenario_unindexed_path", "Proposed edits must target indexed source"
        )
    parsed = []
    total_bytes = 0
    diagnostics = []
    for path, node in sorted(indexed.items()):
        original = read_source(settings, path)
        total_bytes += len(original)
        if total_bytes > settings.max_total_bytes:
            raise RepositoryError("scenario_byte_limit", "Base source exceeds the byte budget")
        if hashlib.sha256(original).hexdigest() != node.content_hash:
            raise RepositoryError("scenario_stale_base", "Source changed during preview; retry")
        raw = edits.get(path, original)
        if raw is None:
            continue
        file = parse_source(path, raw)
        diagnostics.extend(file.diagnostics)
        parsed.append(file)
    aliases = AliasResolver(settings, sorted(indexed))
    if aliases.fingerprint != base.resolution_fingerprint:
        raise RepositoryError("scenario_stale_base", "Alias configuration changed during preview")
    proposed = GraphBuilder(parsed, aliases).build()
    freshness, _ = analyzer._freshness(base)
    if freshness != "current":
        raise RepositoryError("scenario_stale_base", "Base tree changed during preview; retry")
    frozen = ScenarioGraph([proposed, base])
    impact = ScenarioImpact(settings)
    impact.graph = frozen
    old = {n.id: n for n in base.nodes}
    new = {n.id: n for n in proposed.nodes}
    modified = {key for key in old.keys() & new.keys() if old[key] != new[key]}
    return (
        frozen,
        impact,
        ScenarioReport(
            kind="proposed_content",
            base_snapshot_id=base.id,
            proposed_snapshot_id=proposed.id,
            paths=sorted(edits),
            added_nodes=len(new.keys() - old.keys()),
            removed_nodes=len(old.keys() - new.keys()),
            modified_nodes=len(modified),
            changed_node_ids=sorted((new.keys() ^ old.keys()) | modified)[:200],
            limitations=[
                "Proposed edits/deletions target existing indexed source files only.",
                "Test suggestions use the checked base graph and recommend broader verification.",
                "Dependency paths are hypothetical; no files are written and no code executes.",
            ],
        ),
        diagnostics[:200],
    )
