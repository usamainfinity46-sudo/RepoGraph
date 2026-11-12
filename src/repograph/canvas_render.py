"""Render trusted bundled UI with escaped, inert repository data."""

import base64
import hashlib
from importlib.resources import files

from repograph.canvas import CanvasReport
from repograph.discovery import RepositoryError


def render_canvas(
    report: CanvasReport | None, *, embedded: bool = False, local: bool = False
) -> str:
    payload = report.model_dump_json() if report is not None else "null"
    if len(payload.encode("utf-8")) > 8_000_000:
        raise RepositoryError("canvas_output_limit", "Narrow canvas scope or reduce the page limit")
    payload = (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    assets = files("repograph").joinpath("canvas_assets")
    css = assets.joinpath("canvas.css").read_text(encoding="utf-8")
    script = assets.joinpath("canvas.js").read_text(encoding="utf-8")
    if embedded or local:
        script += "\n" + assets.joinpath("workbench.js").read_text(encoding="utf-8")
    if embedded:
        script += "\n" + assets.joinpath("app.bundle.js").read_text(encoding="utf-8")
    if local:
        script += "\n" + assets.joinpath("local.js").read_text(encoding="utf-8")
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    style_digest = base64.b64encode(hashlib.sha256(css.encode()).digest()).decode()
    connections = "'self'" if local else "'none'"
    policy = (
        f"default-src 'none'; script-src 'sha256-{digest}'; "
        f"style-src 'sha256-{style_digest}'; style-src-attr 'unsafe-inline'; "
        f"img-src data:; connect-src {connections}; "
        "base-uri 'none'; form-action 'none'"
    )
    template = assets.joinpath("canvas.html").read_text(encoding="utf-8")
    # One substitution pass prevents repository values from being interpreted as template tokens.
    import re

    template = re.sub(r"<style>\s*\{\{CSS\}\}\s*</style>", "<style>{{CSS}}</style>", template)
    template = re.sub(r"<script>\s*\{\{JS\}\}\s*</script>", "<script>{{JS}}</script>", template)
    values = {"CSP": policy, "CSS": css, "DATA": payload, "JS": script}
    html = re.sub(r"\{\{(CSP|CSS|DATA|JS)\}\}", lambda match: values[match[1]], template)
    if len(html.encode("utf-8")) > 8_000_000:
        raise RepositoryError(
            "canvas_output_limit", "Rendered canvas exceeds the output byte limit"
        )
    return html
