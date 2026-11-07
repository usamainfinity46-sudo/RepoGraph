"""Extract lexical references and import/export bindings without evaluating code."""

from tree_sitter import Node

from repograph.models import Binding, Export, ParsedFile, Reference, Shadow


def extract_relations(root: Node, source: bytes, result: ParsedFile) -> None:
    def text(node: Node | None) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8") if node else ""

    # Reuse declaration spans from the structure extractor to keep scope naming identical.
    declarations = {symbol.start_byte: symbol for symbol in result.symbols}
    pending = [(root, "")]
    while pending:
        node, scope = pending.pop()
        symbol = declarations.get(node.start_byte)
        # Wrapper nodes may share start offsets; only the exact declaration span establishes scope.
        if symbol and symbol.end_byte == node.end_byte:
            scope = symbol.qualified_name
            parent = node.parent
            while parent and parent.type in {"lexical_declaration", "variable_declaration"}:
                parent = parent.parent
            if parent and parent.type == "export_statement":
                result.exports.append(
                    Export(
                        name="default"
                        if any(c.type == "default" for c in parent.children)
                        else symbol.name,
                        local=symbol.qualified_name,
                    )
                )
            if symbol.kind == "class":
                bases = node.child_by_field_name("superclasses")
                if bases:
                    for base in bases.named_children:
                        result.references.append(
                            Reference(
                                name=text(base),
                                scope=scope,
                                relation="inherits",
                                line=base.start_point.row + 1,
                            )
                        )
        if symbol and symbol.end_byte == node.end_byte:
            parameters = node.child_by_field_name("parameters")
            if parameters:
                for parameter in parameters.named_children:
                    name = (
                        parameter
                        if parameter.type == "identifier"
                        else (
                            parameter.child_by_field_name("name")
                            or parameter.child_by_field_name("pattern")
                        )
                    )
                    if name and name.type == "identifier":
                        result.shadows.append(Shadow(name=text(name), scope=scope))
        if node.type in {"assignment", "variable_declarator"} and not (
            symbol and symbol.end_byte == node.end_byte
        ):
            target = node.child_by_field_name("left") or node.child_by_field_name("name")
            if target and target.type == "identifier":
                result.shadows.append(Shadow(name=text(target), scope=scope))
        if node.type == "internal_module":
            name = text(node.child_by_field_name("name"))
            scope = f"{scope}.{name}".strip(".")
        if node.type in {"extends_clause", "implements_clause"}:
            for child in node.named_children:
                result.references.append(
                    Reference(
                        name=text(child),
                        scope=scope,
                        relation="inherits",
                        line=child.start_point.row + 1,
                    )
                )
        if node.type == "class_heritage" and result.language == "javascript":
            for child in node.named_children:
                result.references.append(
                    Reference(
                        name=text(child),
                        scope=scope,
                        relation="inherits",
                        line=child.start_point.row + 1,
                    )
                )
        if node.type in {"call", "call_expression", "new_expression"}:
            target = node.child_by_field_name("function") or node.child_by_field_name("constructor")
            result.references.append(
                Reference(
                    name=text(target), scope=scope, relation="calls", line=node.start_point.row + 1
                )
            )
        if result.language == "python" and node.type in {
            "import_statement",
            "import_from_statement",
        }:
            module = node.child_by_field_name("module_name")
            for child in node.named_children:
                if child == module or child.type not in {
                    "dotted_name",
                    "aliased_import",
                    "wildcard_import",
                }:
                    continue
                original = (
                    text(child.child_by_field_name("name"))
                    if child.type == "aliased_import"
                    else text(child)
                )
                alias = text(child.child_by_field_name("alias")) or (
                    original if module else original.split(".")[0]
                )
                result.bindings.append(
                    Binding(
                        local=alias,
                        module=text(module) if module else original,
                        imported=original if module else None,
                        scope=scope,
                        line=node.start_point.row + 1,
                    )
                )
        if node.type == "import_statement" and result.language != "python":
            target = node.child_by_field_name("source")
            if target:
                for clause in node.named_children:
                    if clause.type != "import_clause":
                        continue
                    for child in clause.named_children:
                        if child.type == "identifier":
                            result.bindings.append(
                                Binding(
                                    local=text(child),
                                    module=text(target)[1:-1],
                                    imported="default",
                                    scope=scope,
                                    line=node.start_point.row + 1,
                                )
                            )
                        elif child.type == "namespace_import":
                            result.bindings.append(
                                Binding(
                                    local=text(child.named_children[-1]),
                                    module=text(target)[1:-1],
                                    scope=scope,
                                    line=node.start_point.row + 1,
                                )
                            )
                        elif child.type == "named_imports":
                            for item in child.named_children:
                                name = text(item.child_by_field_name("name"))
                                alias = text(item.child_by_field_name("alias")) or name
                                result.bindings.append(
                                    Binding(
                                        local=alias,
                                        imported=name,
                                        module=text(target)[1:-1],
                                        scope=scope,
                                        line=node.start_point.row + 1,
                                    )
                                )
        if node.type == "export_statement":
            target = node.child_by_field_name("source")
            for child in node.named_children:
                if child.type == "export_clause":
                    for item in child.named_children:
                        local = text(item.child_by_field_name("name"))
                        name = text(item.child_by_field_name("alias")) or local
                        result.exports.append(
                            Export(
                                name=name,
                                local=local,
                                module=text(target)[1:-1] if target else None,
                            )
                        )
        pending.extend((child, scope) for child in reversed(node.named_children))
