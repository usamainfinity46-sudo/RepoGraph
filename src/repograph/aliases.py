"""Bounded static tsconfig/jsconfig paths. Never import executable configuration."""

import hashlib
import json
import posixpath
from pathlib import PurePosixPath

from pydantic import BaseModel, Field, StrictStr

from repograph.config import Settings
from repograph.discovery import (
    Discovery,
    RepositoryError,
    is_link,
    normalize_relative,
    read_content,
)
from repograph.models import Diagnostic


class AliasOptions(BaseModel):
    baseUrl: StrictStr = "."
    paths: dict[StrictStr, list[StrictStr]] = Field(default_factory=dict)


class AliasConfig(BaseModel):
    compilerOptions: AliasOptions = Field(default_factory=AliasOptions)
    extends: StrictStr | list[StrictStr] | None = None


def jsonc(source: str) -> dict:
    """Strip comments/trailing commas only outside JSON strings; reject duplicate keys."""
    chars = list(source)
    quoted = escaped = False
    i = 0
    while i < len(chars):
        c = chars[i]
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c == "/" and i + 1 < len(chars) and chars[i + 1] in {"/", "*"}:
            block = chars[i + 1] == "*"
            end = source.find("*/", i + 2) if block else source.find("\n", i + 2)
            if block and end < 0:
                raise ValueError("Unterminated JSON comment")
            end = end + 2 if block else end if end >= 0 else len(chars)
            for j in range(i, end):
                if chars[j] not in "\r\n":
                    chars[j] = " "
            i = end - 1
        i += 1
    quoted = escaped = False
    for i, c in enumerate(chars):
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c == ",":
            j = i + 1
            while j < len(chars) and chars[j].isspace():
                j += 1
            if j < len(chars) and chars[j] in "}]":
                chars[i] = " "

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate configuration key")
            result[key] = value
        return result

    return json.loads("".join(chars), object_pairs_hook=unique)


def local_path(base: str, value: str) -> str:
    if value.startswith(("/", "\\")) or ":" in value or "\x00" in value:
        raise ValueError("Alias target must be repository-local")
    combined = posixpath.normpath(posixpath.join(base, value.replace("\\", "/")))
    return normalize_relative(combined) if combined != "." else "."


class AliasResolver:
    def __init__(self, settings: Settings, source_paths: list[str]):
        self.configs: dict[str, tuple[str, dict[str, list[str]]]] = {}
        self.diagnostics: list[Diagnostic] = []
        self.fingerprint: str | None = None
        js = [p for p in source_paths if PurePosixPath(p).suffix.lower() != ".py"]
        if not js:
            return
        discovery = Discovery(settings)
        allowed = set(discovery.files(names={"tsconfig.json", "jsconfig.json"}))
        if not discovery.complete:
            raise RepositoryError(
                "alias_inventory_incomplete", "Alias metadata inventory incomplete"
            )
        candidates = {
            (parent / name).as_posix()
            for path in js
            for parent in PurePosixPath(path).parents
            for name in ("tsconfig.json", "jsconfig.json")
        }
        inputs = {}
        total = 0
        for path in sorted(candidates):
            candidate = settings.root / path
            if not candidate.exists() and not is_link(candidate) and path not in allowed:
                continue
            self.configs[path] = (".", {})  # Invalid/ignored nearest config blocks parent fallback.
            try:
                if path not in allowed:
                    raise ValueError("Configuration is excluded or unsafe")
                raw = read_content(settings, path)
                total += len(raw)
                if total > settings.max_total_bytes:
                    raise RepositoryError("alias_byte_limit", "Alias metadata exceeds byte budget")
                inputs[path] = hashlib.sha256(raw).hexdigest()
                if len(raw) > 262_144:
                    raise ValueError("Configuration exceeds 262144 bytes")
                config = AliasConfig.model_validate(jsonc(raw.decode("utf-8-sig")))
                if config.extends is not None:
                    raise ValueError("Inherited configuration is not supported")
                options = config.compilerOptions
                if len(options.paths) > 100:
                    raise ValueError("Too many alias patterns")
                base = local_path(posixpath.dirname(path), options.baseUrl)
                for pattern, targets in options.paths.items():
                    if (
                        not pattern
                        or len(pattern) > 256
                        or pattern.count("*") > 1
                        or pattern.startswith((".", "/", "\\"))
                        or ":" in pattern
                        or "\x00" in pattern
                    ):
                        raise ValueError("Unsupported alias pattern")
                    if not targets or len(targets) > 20:
                        raise ValueError("Alias requires 1..20 targets")
                    for target in targets:
                        if len(target) > 1024 or target.count("*") > pattern.count("*"):
                            raise ValueError("Unsupported alias target")
                        local_path(base, target.replace("*", "alias_capture"))
                self.configs[path] = (base, options.paths)
            except (ValueError, OSError, RecursionError) as error:
                if isinstance(error, RepositoryError) and error.code == "alias_byte_limit":
                    raise
                inputs.setdefault(path, "unavailable")
                self.diagnostics.append(
                    Diagnostic(
                        code="alias_config_unresolved",
                        path=path,
                        message="Static alias configuration unavailable, invalid or unsupported",
                    )
                )
        self.fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()

    def stems(self, path: str, module: str) -> list[str]:
        selected = None
        for parent in PurePosixPath(path).parents:
            for name in ("tsconfig.json", "jsconfig.json"):
                key = (parent / name).as_posix()
                if key in self.configs:
                    selected = self.configs[key]
                    break
            if selected is not None:
                break
        if selected is None:
            return []
        base, patterns = selected
        if module in patterns:
            matches = [(module, "")]
        else:
            matches = []
            for pattern in patterns:
                if "*" not in pattern:
                    continue
                prefix, suffix = pattern.split("*")
                if (
                    module.startswith(prefix)
                    and module.endswith(suffix)
                    and len(module) >= len(prefix) + len(suffix)
                ):
                    matches.append(
                        (
                            pattern,
                            module[len(prefix) : len(module) - len(suffix) if suffix else None],
                        )
                    )
            matches.sort(key=lambda item: (-len(item[0].split("*")[0]), item[0]))
        if not matches:
            return []
        if len(matches) > 1 and len(matches[0][0].split("*")[0]) == len(
            matches[1][0].split("*")[0]
        ):
            return []
        pattern, capture = matches[0]
        try:
            return [local_path(base, target.replace("*", capture)) for target in patterns[pattern]]
        except ValueError:
            return []
