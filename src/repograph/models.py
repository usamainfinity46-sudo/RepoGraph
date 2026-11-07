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


class Import(BaseModel):
    module: str
    names: list[str] = Field(default_factory=list)
    line: int
    kind: Literal["static", "dynamic", "require"] = "static"
    confidence: Literal["syntactic", "unresolved"] = "syntactic"


class ParsedFile(BaseModel):
    path: str
    language: Language
    sha256: str
    size_bytes: int
    symbols: list[Symbol] = Field(default_factory=list)
    imports: list[Import] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    schema_version: int
    repository: str


class ScanReport(BaseModel):
    schema_version: int = 1
    files: list[ParsedFile] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    complete: bool = True
