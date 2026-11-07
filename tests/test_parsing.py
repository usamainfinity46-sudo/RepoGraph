import hashlib

import pytest

from repograph.discovery import RepositoryError
from repograph.parsing import parse_source


def test_python_scopes_and_imports():
    source = b"""import os.path as path, sys
from ..helpers import run as execute
@decorate
class Service:
    async def run(self):
        def nested():
            return 1
        return nested()
"""
    result = parse_source("service.py", source)
    assert [(s.qualified_name, s.kind) for s in result.symbols] == [
        ("Service", "class"),
        ("Service.run", "method"),
        ("Service.run.nested", "function"),
    ]
    assert [i.module for i in result.imports] == ["os.path", "sys", "..helpers"]
    assert result.imports[2].names == ["run as execute"]
    assert result.sha256 == hashlib.sha256(source).hexdigest()
    assert not result.diagnostics
    for symbol in result.symbols:
        assert source[symbol.start_byte : symbol.end_byte]


@pytest.mark.parametrize("extension", ["js", "jsx", "mjs", "cjs"])
def test_javascript(extension):
    result = parse_source(
        f"main.{extension}",
        b"""import { read as load } from './io';
export { helper } from './helpers';
export function execute() { return load(); }
const arrow = () => 42;
class Service { run() { return arrow(); } }
const util = require('util');
import('./lazy');
import(variable);
""",
    )
    assert {s.qualified_name for s in result.symbols} == {
        "execute",
        "arrow",
        "Service",
        "Service.run",
    }
    assert [i.module for i in result.imports] == ["./io", "./helpers", "util", "./lazy", "variable"]
    assert all(i.confidence == "unresolved" for i in result.imports[2:])
    assert not result.diagnostics


@pytest.mark.parametrize("extension", ["ts", "mts", "cts", "tsx"])
def test_typescript(extension):
    source = b"""import type { User } from './types';
interface Store { get(): User; }
type ID = string;
export class Repo { fetch(id: ID): User { throw Error(id); } }
export const identity = <T,>(value: T): T => value;
"""
    if extension == "tsx":
        source += b"const View = () => <div>Hello</div>;\n"
    result = parse_source(f"main.{extension}", source)
    assert {"Store", "ID", "Repo", "Repo.fetch", "identity"} <= {
        s.qualified_name for s in result.symbols
    }
    assert result.imports[0].module == "./types"
    assert not result.diagnostics


def test_unicode_coordinates_and_recovery():
    source = "const café = () => 1;\nfunction broken( {".encode()
    result = parse_source("x.js", source)
    symbol = result.symbols[0]
    assert source[symbol.start_byte : symbol.end_byte].decode() == "café = () => 1"
    assert symbol.start_column == 7
    assert symbol.end_column == 22
    assert result.diagnostics


def test_unsupported():
    with pytest.raises(RepositoryError, match="Supported languages"):
        parse_source("x.go", b"package main")


def test_missing_punctuation_diagnostic():
    assert parse_source("x.js", b"function f() {").diagnostics


def test_typescript_require_bound_class_and_namespace():
    result = parse_source(
        "x.ts",
        b"""import util = require("util");
const Thing = class { run() {} };
namespace A { export function f() {} }
""",
    )
    assert [i.module for i in result.imports] == ["util"]
    assert {s.qualified_name for s in result.symbols} == {"Thing", "Thing.run", "A.f"}
