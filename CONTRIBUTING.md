# Contributing

RepoGraph is a local static analyzer. Read [AGENTS.md](AGENTS.md),
[engineering rules](docs/ENGINEERING_RULES.md), and the architecture, contracts,
schema, security model and testing strategy before changing behavior.

## Development

Use Python 3.11–3.13 and `uv`:

```sh
uv sync --locked --group dev --python 3.12
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest
uv build
uv run --no-sync python scripts/smoke_wheel.py
```

Use a branch and a pull request describing the concrete behavior change and its
validation. Include regression coverage for defects and security boundaries.
Update permanent documents when contracts or semantics change. Increment the
extractor or verifier revision when their documented rules require it. Keep
analysis independent of MCP and model vendors. Never import, evaluate, install,
or execute target-repository code during discovery, indexing or impact analysis.

Run `scripts/benchmark.py` for performance or graph changes. See
[benchmark methodology](docs/BENCHMARKS.md) and [compatibility](docs/COMPATIBILITY.md)
for real JS runners and OS-specific checks. Do not claim a skipped check passed.
Development tests may execute reviewed fixtures; production verification must
retain both host opt-in and explicit prepared-plan approval.

## Contributions and license

By submitting a contribution you agree that it is provided under Apache-2.0,
the project's license. Retain applicable third-party notices. No contributor
license agreement is required. Security reporting is described in [SECURITY.md](SECURITY.md).
