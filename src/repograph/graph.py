"""Deterministic static graph construction, conservative resolution, and persistence."""

import hashlib
import json
import posixpath
import time
from collections import Counter, defaultdict
from pathlib import PurePosixPath

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.models import (
    EdgePage,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    IndexReport,
    NodePage,
    ParsedFile,
    SnapshotDelta,
)
from repograph.parsing import PARSER_VERSION
from repograph.service import RepositoryService, pagination

GRAPH_VERSION = "graph-1"
MAX_GRAPH_ITEMS = 200_000


def identity(*parts: str) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=True).encode()).hexdigest()


class GraphBuilder:
    def __init__(self, files: list[ParsedFile]):
        self.files = {file.path: file for file in files}
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[str, GraphEdge] = {}
        self.symbols: dict[tuple[str, str], list[GraphNode]] = defaultdict(list)
        self.modules: dict[str, GraphNode] = {}

    def module(self, path: str, module: str) -> str | None:
        file = self.files[path]
        candidates = []
        if file.language == "python":
            if module.startswith("."):
                count = len(module) - len(module.lstrip("."))
                parent = PurePosixPath(path).parent
                for _ in range(count - 1):
                    if str(parent) == ".":
                        return None
                    parent = parent.parent
                stems = [(parent / module[count:].replace(".", "/")).as_posix()]
            else:
                stems = [module.replace(".", "/"), "src/" + module.replace(".", "/")]
            for stem in stems:
                candidates.extend([stem + ".py", stem.rstrip("/") + "/__init__.py"])
        elif module.startswith("."):
            stem = posixpath.normpath(posixpath.join(posixpath.dirname(path), module))
            if stem.startswith("../") or stem == "..":
                return None
            candidates = [stem]
            if PurePosixPath(stem).suffix in {".js", ".jsx", ".mjs", ".cjs"}:
                # TypeScript projects commonly import the eventual emitted JS path.
                candidates += [
                    str(PurePosixPath(stem).with_suffix(ext))
                    for ext in (".ts", ".tsx", ".mts", ".cts")
                ]
            if not PurePosixPath(stem).suffix:
                candidates += [
                    stem + ext
                    for ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts")
                ]
                candidates += [stem + "/index" + ext for ext in (".js", ".jsx", ".ts", ".tsx")]
        matches = sorted(set(candidates) & self.files.keys())
        return matches[0] if len(matches) == 1 else None

    def unique(self, path: str, name: str) -> GraphNode | None:
        candidates = self.symbols.get((path, name), [])
        return candidates[0] if len(candidates) == 1 else None

    def exported(self, path: str, name: str, seen: frozenset = frozenset()) -> GraphNode | None:
        key = (path, name)
        if key in seen or len(seen) >= 64:
            return None
        seen = seen | {key}
        file = self.files[path]
        if file.language == "python":
            local = self.unique(path, name)
            if local:
                return local
            bindings = [b for b in file.bindings if not b.scope and b.local == name]
            if len(bindings) == 1:
                binding = bindings[0]
                target = self.module(path, binding.module)
                if target and binding.imported:
                    return self.exported(target, binding.imported, seen)
            return None
        exports = [e for e in file.exports if e.name == name]
        if len(exports) != 1:
            return None
        export = exports[0]
        if export.module:
            target = self.module(path, export.module)
            return self.exported(target, export.local, seen) if target else None
        local = self.unique(path, export.local)
        if local:
            return local
        bindings = [b for b in file.bindings if not b.scope and b.local == export.local]
        if len(bindings) == 1 and bindings[0].imported:
            target = self.module(path, bindings[0].module)
            return self.exported(target, bindings[0].imported, seen) if target else None
        return None

    def resolve(self, path: str, scope: str, name: str) -> GraphNode | None:
        if not name or any(not component.isidentifier() for component in name.split(".")):
            return None
        parts = scope.split(".") if scope else []
        if name.startswith(("self.", "cls.", "this.")):
            for length in range(len(parts), 0, -1):
                parent = self.unique(path, ".".join(parts[:length]))
                if parent and parent.kind == "class":
                    return self.unique(path, parent.qualified_name + "." + name.split(".", 1)[1])
            return None
        for length in range(len(parts), -1, -1):
            prefix = ".".join(parts[:length])
            owner = self.unique(path, prefix)
            if self.files[path].language == "python" and owner and owner.kind == "class":
                continue
            qualified = f"{prefix}.{name}".strip(".")
            if any(
                s.scope == prefix and s.name == name.split(".")[0] for s in self.files[path].shadows
            ):
                return None
            if (path, qualified) in self.symbols:
                return self.unique(path, qualified)
            first, _, remainder = name.partition(".")
            bindings = [
                b for b in self.files[path].bindings if b.scope == prefix and b.local == first
            ]
            if len(bindings) == 1:
                binding = bindings[0]
                target = self.module(path, binding.module)
                if not target:
                    return None
                if binding.imported:
                    resolved = self.exported(target, binding.imported)
                    return (
                        self.unique(resolved.path, resolved.qualified_name + "." + remainder)
                        if resolved and remainder
                        else resolved
                    )
                if remainder:
                    # Unaliased Python `import pkg.util` binds `pkg`, not `util`.
                    tail = binding.module.partition(".")[2]
                    if (
                        self.files[path].language == "python"
                        and first == binding.module.split(".")[0]
                        and tail
                        and remainder.startswith(tail + ".")
                    ):
                        remainder = remainder[len(tail) + 1 :]
                    return self.exported(target, remainder)
                return self.modules[target]
            if len(bindings) > 1:
                return None
        return None

    def add_edge(
        self,
        source: GraphNode,
        target: GraphNode | None,
        relation: str,
        path: str,
        line: int,
        name: str,
        confidence: str,
    ) -> None:
        key = identity(source.id, target.id if target else "", relation, str(line), name)
        self.edges[key] = GraphEdge(
            id=key,
            source=source.id,
            target=target.id if target else None,
            relation=relation,
            confidence=confidence,
            path=path,
            line=line,
            target_name=name,
        )
        if len(self.nodes) + len(self.edges) > MAX_GRAPH_ITEMS:
            raise RepositoryError("graph_limit", "Graph exceeds the 200000 item safety limit")

    def build(self) -> GraphSnapshot:
        for path, file in sorted(self.files.items()):
            module = GraphNode(
                id=identity(path, "file"),
                path=path,
                kind="file",
                name=path,
                qualified_name=path,
                content_hash=file.sha256,
                end_byte=file.size_bytes,
            )
            self.modules[path] = module
            self.nodes[module.id] = module
            occurrences: Counter = Counter()
            for symbol in file.symbols:
                key = (symbol.kind, symbol.qualified_name)
                ordinal = occurrences[key]
                occurrences[key] += 1
                node = GraphNode(
                    id=identity(path, *key, str(ordinal)),
                    path=path,
                    kind=symbol.kind,
                    name=symbol.name,
                    qualified_name=symbol.qualified_name,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    start_byte=symbol.start_byte,
                    end_byte=symbol.end_byte,
                    content_hash=symbol.content_hash,
                )
                self.nodes[node.id] = node
                self.symbols[(path, symbol.qualified_name)].append(node)
        if len(self.nodes) > MAX_GRAPH_ITEMS:
            raise RepositoryError("graph_limit", "Graph exceeds the 200000 item safety limit")
        for path, file in sorted(self.files.items()):
            module = self.modules[path]
            for symbol in file.symbols:
                nodes = self.symbols[(path, symbol.qualified_name)]
                node = next(n for n in nodes if n.start_byte == symbol.start_byte)
                parent_name = node.qualified_name.rpartition(".")[0]
                parent = self.unique(path, parent_name) or module
                self.add_edge(parent, node, "contains", path, node.start_line, node.name, "static")
            for item in file.imports:
                target_path = self.module(path, item.module) if item.kind == "static" else None
                self.add_edge(
                    module,
                    self.modules.get(target_path),
                    "imports",
                    path,
                    item.line,
                    item.module,
                    "static" if target_path else "unresolved",
                )
            for reference in file.references:
                source = self.unique(path, reference.scope) or module
                target = self.resolve(path, reference.scope, reference.name)
                self.add_edge(
                    source,
                    target,
                    reference.relation,
                    path,
                    reference.line,
                    reference.name,
                    "heuristic" if target else "unresolved",
                )
        nodes = sorted(self.nodes.values(), key=lambda item: item.id)
        edges = sorted(self.edges.values(), key=lambda item: item.id)
        digest = identity(
            GRAPH_VERSION,
            *(n.model_dump_json() for n in nodes),
            *(e.model_dump_json() for e in edges),
        )
        return GraphSnapshot(id=digest, nodes=nodes, edges=edges)


class GraphService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.repository = RepositoryService(settings)
        self.database = self.repository.database

    def _repository_id(self, connection) -> int:
        connection.execute(
            "INSERT OR IGNORE INTO repositories(root) VALUES(?)", (str(self.settings.root),)
        )
        return connection.execute(
            "SELECT id FROM repositories WHERE root=?", (str(self.settings.root),)
        ).fetchone()[0]

    def index(self) -> IndexReport:
        scan = self.repository.scan()
        if not scan.complete:
            return IndexReport(published=False, scan=scan)
        with self.database.connect() as connection:
            repository_id = self._repository_id(connection)
            files = [
                ParsedFile.model_validate_json(row[0])
                for row in connection.execute(
                    "SELECT data FROM files WHERE repository_id=? ORDER BY path", (repository_id,)
                )
            ]
        snapshot = GraphBuilder(files).build()
        report = IndexReport(
            published=True,
            snapshot_id=snapshot.id,
            scan=scan,
            nodes=len(snapshot.nodes),
            edges=len(snapshot.edges),
            unresolved_edges=sum(edge.target is None for edge in snapshot.edges),
        )
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            old_files = dict(
                connection.execute(
                    "SELECT path,sha256 FROM graph_files WHERE repository_id=?", (repository_id,)
                )
            )
            current_files = {
                file.path: identity(file.sha256, PARSER_VERSION, GRAPH_VERSION) for file in files
            }
            report.updated_files = sum(
                old_files.get(path) != sha for path, sha in current_files.items()
            )
            report.reused_files = len(current_files) - report.updated_files
            report.removed_files = len(old_files.keys() - current_files.keys())
            for table, items in (("graph_nodes", snapshot.nodes), ("graph_edges", snapshot.edges)):
                old = dict(
                    connection.execute(
                        f"SELECT id,data FROM {table} WHERE repository_id=?", (repository_id,)
                    )
                )
                new = {item.id: item.model_dump_json() for item in items}
                for key in old.keys() - new.keys():
                    connection.execute(
                        f"DELETE FROM {table} WHERE repository_id=? AND id=?", (repository_id, key)
                    )
                for item in items:
                    data = new[item.id]
                    if old.get(item.id) == data:
                        continue
                    if table == "graph_nodes":
                        connection.execute(
                            "INSERT INTO graph_nodes VALUES(?,?,?,?) ON CONFLICT(repository_id,id) "
                            "DO UPDATE SET path=excluded.path,data=excluded.data",
                            (repository_id, item.id, item.path, data),
                        )
                        report.nodes_written += 1
                    else:
                        connection.execute(
                            "INSERT INTO graph_edges VALUES(?,?,?,?,?) "
                            "ON CONFLICT(repository_id,id) "
                            "DO UPDATE SET source=excluded.source,target=excluded.target,"
                            "data=excluded.data",
                            (repository_id, item.id, item.source, item.target, data),
                        )
                        report.edges_written += 1
            connection.execute("DELETE FROM graph_files WHERE repository_id=?", (repository_id,))
            connection.executemany(
                "INSERT INTO graph_files VALUES(?,?,?)",
                ((repository_id, path, sha) for path, sha in current_files.items()),
            )
            connection.execute(
                "INSERT OR IGNORE INTO graph_snapshots VALUES(?,?,?,?)",
                (repository_id, snapshot.id, snapshot.model_dump_json(), time.time_ns()),
            )
            connection.execute(
                "INSERT INTO graph_state VALUES(?,?) ON CONFLICT(repository_id) "
                "DO UPDATE SET snapshot_id=excluded.snapshot_id",
                (repository_id, snapshot.id),
            )
            connection.execute(
                "DELETE FROM graph_snapshots WHERE repository_id=? AND id NOT IN "
                "(SELECT id FROM graph_snapshots WHERE repository_id=? "
                "ORDER BY created_at DESC LIMIT 20) AND id!=?",
                (repository_id, repository_id, snapshot.id),
            )
        return report

    def snapshot(self, snapshot_id: str | None = None) -> GraphSnapshot:
        with self.database.connect() as connection:
            repository_id = self._repository_id(connection)
            if snapshot_id is None:
                state = connection.execute(
                    "SELECT snapshot_id FROM graph_state WHERE repository_id=?", (repository_id,)
                ).fetchone()
                if not state:
                    raise RepositoryError(
                        "graph_not_indexed", "Run index_repository before querying the graph"
                    )
                snapshot_id = state[0]
            row = connection.execute(
                "SELECT data FROM graph_snapshots WHERE repository_id=? AND id=?",
                (repository_id, snapshot_id),
            ).fetchone()
            if not row:
                raise RepositoryError(
                    "snapshot_not_found", "Snapshot does not exist or has expired"
                )
        return GraphSnapshot.model_validate_json(row[0])

    def query_symbols(
        self, query: str = "", path: str | None = None, offset: int = 0, limit: int = 100
    ) -> NodePage:
        pagination(offset, limit)
        if len(query) > 1000:
            raise RepositoryError("invalid_query", "Symbol query exceeds 1000 characters")
        snapshot = self.snapshot()
        nodes = sorted(
            (
                n
                for n in snapshot.nodes
                if n.kind != "file"
                and query in n.qualified_name
                and (path is None or n.path == path)
            ),
            key=lambda n: (n.path, n.qualified_name, n.id),
        )
        return NodePage(
            snapshot_id=snapshot.id,
            nodes=nodes[offset : offset + limit],
            total=len(nodes),
            next_offset=offset + limit if offset + limit < len(nodes) else None,
        )

    def dependencies(
        self,
        node_id: str,
        direction: str = "outgoing",
        relation: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> EdgePage:
        pagination(offset, limit)
        if direction not in {"incoming", "outgoing"} or relation not in {
            None,
            "contains",
            "imports",
            "calls",
            "inherits",
        }:
            raise RepositoryError("invalid_query", "Invalid graph direction or relation")
        snapshot = self.snapshot()
        file_node = next(
            (n for n in snapshot.nodes if n.kind == "file" and n.path == node_id), None
        )
        if file_node:
            node_id = file_node.id
        if node_id not in {node.id for node in snapshot.nodes}:
            raise RepositoryError("node_not_found", "Node is not in the current graph")
        edges = [
            e
            for e in snapshot.edges
            if (e.source if direction == "outgoing" else e.target) == node_id
            and (relation is None or e.relation == relation)
        ]
        return EdgePage(
            snapshot_id=snapshot.id,
            edges=edges[offset : offset + limit],
            total=len(edges),
            next_offset=offset + limit if offset + limit < len(edges) else None,
        )

    def compare_snapshots(
        self, before: str, after: str, offset: int = 0, limit: int = 100
    ) -> SnapshotDelta:
        pagination(offset, limit)
        old, new = self.snapshot(before), self.snapshot(after)
        old_nodes, new_nodes = {n.id: n for n in old.nodes}, {n.id: n for n in new.nodes}
        old_edges, new_edges = {e.id: e for e in old.edges}, {e.id: e for e in new.edges}
        groups = {
            "added_nodes": sorted(new_nodes.keys() - old_nodes.keys()),
            "removed_nodes": sorted(old_nodes.keys() - new_nodes.keys()),
            "modified_nodes": sorted(
                key
                for key in old_nodes.keys() & new_nodes.keys()
                if old_nodes[key] != new_nodes[key]
            ),
            "added_edges": sorted(new_edges.keys() - old_edges.keys()),
            "removed_edges": sorted(old_edges.keys() - new_edges.keys()),
            "modified_edges": sorted(
                key
                for key in old_edges.keys() & new_edges.keys()
                if old_edges[key] != new_edges[key]
            ),
        }
        changes = [(group, key) for group, keys in groups.items() for key in keys]
        page = {group: [] for group in groups}
        for group, key in changes[offset : offset + limit]:
            page[group].append(key)
        return SnapshotDelta(
            before=before,
            after=after,
            **page,
            total_changes=len(changes),
            next_offset=offset + limit if offset + limit < len(changes) else None,
        )
