"""Tree-sitter structure extraction. Import observations do not imply resolution."""

import hashlib
from importlib.metadata import version
from pathlib import PurePosixPath

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from repograph.discovery import EXTENSIONS, RepositoryError
from repograph.models import Diagnostic, Import, ParsedFile, Symbol
from repograph.relations import extract_relations

PARSER_VERSION = "extractor-4:" + ":".join(
    version(package)
    for package in (
        "tree-sitter",
        "tree-sitter-python",
        "tree-sitter-javascript",
        "tree-sitter-typescript",
    )
)
LANGUAGES = {
    "python": Language(tree_sitter_python.language()),
    "javascript": Language(tree_sitter_javascript.language()),
    "typescript": Language(tree_sitter_typescript.language_typescript()),
    "tsx": Language(tree_sitter_typescript.language_tsx()),
}
SYMBOL_KINDS = {
    "function_definition": "function",
    "function_declaration": "function",
    "generator_function_declaration": "function",
    "class_definition": "class",
    "class_declaration": "class",
    "abstract_class_declaration": "class",
    "method_definition": "method",
    "method_signature": "method",
    "interface_declaration": "interface",
    "type_alias_declaration": "type",
}


def parse_source(path: str, source: bytes) -> ParsedFile:
    language = EXTENSIONS.get(PurePosixPath(path).suffix.lower())
    if language is None:
        raise RepositoryError(
            "unsupported_language", "Supported languages: Python, JavaScript, TypeScript"
        )
    result = ParsedFile(
        path=path,
        language=language,
        sha256=hashlib.sha256(source).hexdigest(),
        size_bytes=len(source),
    )
    tree = Parser(LANGUAGES[language]).parse(source)

    def text(node: Node | None) -> str:
        return (
            source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
            if node
            else ""
        )

    def descendants(node: Node, kind: str) -> list[Node]:
        output = []
        pending = [node]
        while pending:
            current = pending.pop()
            if current.type == kind:
                output.append(current)
            else:
                pending.extend(reversed(current.named_children))
        return output

    pending = [(tree.root_node, (), None)]
    while pending:
        node, scope, parent_kind = pending.pop()
        next_scope, next_kind = scope, parent_kind
        kind = SYMBOL_KINDS.get(node.type)
        name_node = node.child_by_field_name("name")
        if node.type == "internal_module" and name_node:
            next_scope, next_kind = (*scope, text(name_node)), None
        if node.type == "variable_declarator":
            value = node.child_by_field_name("value")
            if value and value.type in {
                "arrow_function",
                "function_expression",
                "generator_function",
            }:
                kind = "function"
            elif value and value.type == "class":
                kind = "class"
        if node.type == "function_definition" and parent_kind == "class":
            kind = "method"
        if kind and name_node:
            name = text(name_node)
            next_scope, next_kind = (*scope, name), kind
            result.symbols.append(
                Symbol(
                    name=name,
                    qualified_name=".".join(next_scope),
                    kind=kind,
                    start_line=node.start_point.row + 1,
                    start_column=node.start_point.column + 1,
                    end_line=node.end_point.row + 1,
                    end_column=node.end_point.column + 1,
                    start_byte=node.start_byte,
                    end_byte=node.end_byte,
                    content_hash=hashlib.sha256(
                        source[node.start_byte : node.end_byte]
                    ).hexdigest(),
                )
            )
        if node.type in {"import_statement", "import_from_statement"}:
            module = node.child_by_field_name("module_name")
            if language == "python":
                names = [
                    text(child)
                    for child in node.named_children
                    if child != module
                    and child.type in {"dotted_name", "aliased_import", "wildcard_import"}
                ]
                if module:
                    result.imports.append(
                        Import(module=text(module), names=names, line=node.start_point.row + 1)
                    )
                else:
                    for child in node.named_children:
                        target = (
                            child.child_by_field_name("name")
                            if child.type == "aliased_import"
                            else child
                        )
                        result.imports.append(
                            Import(
                                module=text(target),
                                names=[text(child)],
                                line=node.start_point.row + 1,
                            )
                        )
            else:
                target = node.child_by_field_name("source")
                if target:
                    names = [text(child) for child in node.named_children if child != target]
                    result.imports.append(
                        Import(
                            module=text(target)[1:-1], names=names, line=node.start_point.row + 1
                        )
                    )
        elif node.type == "export_statement":
            target = node.child_by_field_name("source")
            if target:
                result.imports.append(
                    Import(module=text(target)[1:-1], line=node.start_point.row + 1)
                )
        elif node.type == "import_require_clause":
            target = node.child_by_field_name("source")
            if target:
                result.imports.append(
                    Import(
                        module=text(target)[1:-1],
                        line=node.start_point.row + 1,
                        kind="require",
                        confidence="unresolved",
                    )
                )
        elif node.type in {"call_expression", "call"}:
            function = node.child_by_field_name("function")
            function_name = text(function)
            if function_name in {"import", "require", "__import__", "importlib.import_module"}:
                arguments = node.child_by_field_name("arguments")
                args = arguments.named_children if arguments else []
                literal = args[0] if args and args[0].type == "string" else None
                # Python string content and JS string_fragment both exclude delimiters.
                contents = (
                    (
                        descendants(literal, "string_content")
                        or descendants(literal, "string_fragment")
                    )
                    if literal
                    else []
                )
                module = (
                    "".join(text(item) for item in contents) if contents else text(literal)[1:-1]
                )
                result.imports.append(
                    Import(
                        module=module if literal else text(args[0]) if args else "",
                        line=node.start_point.row + 1,
                        kind="require" if function_name == "require" else "dynamic",
                        confidence="unresolved",
                    )
                )
        if (node.type == "ERROR" or node.is_missing) and len(result.diagnostics) < 100:
            result.diagnostics.append(
                Diagnostic(
                    code="syntax_error",
                    path=path,
                    line=node.start_point.row + 1,
                    message="Tree-sitter recovered from invalid syntax",
                )
            )
        pending.extend((child, next_scope, next_kind) for child in reversed(node.named_children))
    if tree.root_node.has_error and not result.diagnostics:
        result.diagnostics.append(
            Diagnostic(
                code="syntax_error",
                path=path,
                message="Tree-sitter recovered from invalid or incomplete syntax",
            )
        )
    extract_relations(tree.root_node, source, result)
    return result
