"""Versioned public data contracts. Coordinates are one-based, end-exclusive."""

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["python", "javascript", "typescript", "tsx"]


class Diagnostic(BaseModel):
    code: str
    message: str
    path: str | None = None
    line: int | None = None


class Symbol(BaseModel):
    name: str
    qualified_name: str
    kind: Literal["function", "class", "method", "interface", "type"]
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_byte: int
    end_byte: int
    content_hash: str = ""


class Import(BaseModel):
    module: str
    names: list[str] = Field(default_factory=list)
    line: int
    kind: Literal["static", "dynamic", "require"] = "static"
    confidence: Literal["syntactic", "unresolved"] = "syntactic"


class Binding(BaseModel):
    local: str
    module: str
    imported: str | None = None
    scope: str = ""
    line: int


class Reference(BaseModel):
    name: str
    scope: str = ""
    relation: Literal["calls", "inherits"]
    line: int


class Shadow(BaseModel):
    name: str
    scope: str


class Export(BaseModel):
    name: str
    local: str
    module: str | None = None


class ParsedFile(BaseModel):
    path: str
    language: Language
    sha256: str
    size_bytes: int
    symbols: list[Symbol] = Field(default_factory=list)
    imports: list[Import] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    bindings: list[Binding] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    exports: list[Export] = Field(default_factory=list)
    shadows: list[Shadow] = Field(default_factory=list)


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    schema_version: int
    repository: str


class ScanSummary(BaseModel):
    schema_version: int = 1
    discovered: int = 0
    parsed: int = 0
    cached: int = 0
    failed: int = 0
    source_bytes: int = 0
    complete: bool = True
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class FilePage(BaseModel):
    files: list[str]
    total: int
    next_offset: int | None = None
    complete: bool = True
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class ParsePage(BaseModel):
    file: ParsedFile
    total_symbols: int
    total_imports: int
    total_references: int = 0
    total_bindings: int = 0
    total_exports: int = 0
    total_shadows: int = 0
    next_offset: int | None = None


class GraphNode(BaseModel):
    id: str
    path: str
    kind: str
    name: str
    qualified_name: str
    start_line: int = 1
    end_line: int = 1
    start_byte: int = 0
    end_byte: int = 0
    content_hash: str


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str | None
    relation: Literal["contains", "imports", "calls", "inherits"]
    confidence: Literal["static", "heuristic", "unresolved"]
    path: str
    line: int
    target_name: str


class GraphSnapshot(BaseModel):
    id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class IndexReport(BaseModel):
    published: bool
    snapshot_id: str | None = None
    scan: ScanSummary
    updated_files: int = 0
    reused_files: int = 0
    removed_files: int = 0
    nodes: int = 0
    edges: int = 0
    unresolved_edges: int = 0
    nodes_written: int = 0
    edges_written: int = 0


class NodePage(BaseModel):
    snapshot_id: str
    nodes: list[GraphNode]
    total: int
    next_offset: int | None = None


class EdgePage(BaseModel):
    snapshot_id: str
    edges: list[GraphEdge]
    total: int
    next_offset: int | None = None


class SnapshotDelta(BaseModel):
    before: str
    after: str
    added_nodes: list[str]
    removed_nodes: list[str]
    modified_nodes: list[str]
    added_edges: list[str]
    removed_edges: list[str]
    total_changes: int
    next_offset: int | None = None
