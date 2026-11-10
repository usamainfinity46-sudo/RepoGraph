# Five-minute local demo

Use an installed RepoGraph executable; follow INSTALLATION.md first. These commands
use POSIX paths; Windows uses `.venv/Scripts/repograph.exe`. Create a scratch
directory, not a production checkout. All analysis commands are static.

Create `calculator.py` containing:

```python
def add(a, b):
    return a + b
```

Create `test_calculator.py` containing:

```python
from calculator import add


def test_add():
    assert add(2, 3) == 5
```

Replace ROOT below with that directory's absolute path:

```sh
repograph --root ROOT index
repograph --root ROOT overview
repograph --root ROOT symbols add
repograph --root ROOT impact calculator.py
repograph --root ROOT suggest-tests calculator.py
```

Expect a published snapshot, two indexed files, an `add` symbol, dependent test
evidence and a recommendation for `test_calculator.py`. IDs/timings vary; results
include conservative module ownership as well as symbol dependencies.

For an execution demo, use an interpreter with pytest installed. Preparation
returns a fixed command preview, fingerprints, warnings and a ten-minute plan ID:

```sh
repograph --root ROOT --enable-verification --test-path test_calculator.py prepare-verification
```

Review that command and approve the exact returned plan explicitly:

```sh
repograph --root ROOT --enable-verification --approve verify PLAN_ID
repograph --root ROOT verification-result PLAN_ID
```

Expect one passing case. Change `a + b` to `a - b`, re-index and prepare/review a
new plan; it should fail. Compare the saved plans:

```sh
repograph --root ROOT --before PASSING_PLAN --after FAILING_PLAN verification-diff
```

The comparison labels a potential regression; it does not prove causality. Tests
execute with host permissions. For Git-driven seeds, initialize/commit this scratch
repository and save a baseline before making the edit. No automatic checkout or
test execution occurs. Client-side equivalents are in MCP_CONTRACTS.md.
