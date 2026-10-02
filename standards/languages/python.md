# Python standards

Version 1.0, 1 Oct 2026.

This file and `standards/CODING_STANDARDS.md` together are the standard for Python code. They apply to the `python` repo. The repo publishes one distribution, `gatepost-postcode`, with the import name `gatepost_postcode`. It holds the core functions, `PostcodeClient` and `AsyncPostcodeClient`. Later Python work follows them too, such as the QGIS plugin.

## Versions

- Python 3.11 or later. CI tests Python 3.11 and the newest Python release.
- Python 3.11 reaches end of life on 31 Oct 2027.
- httpx is the one runtime dependency of the client. The core has none.

## Tools

`make check` runs every tool below. CI runs `make check` on each pull request and each push to `main`.

| Tool | Job | Settings |
|---|---|---|
| uv | environments, lockfile and builds | `uv.lock` is in the repo |
| hatchling | build backend | `pyproject.toml` |
| Ruff format | format | `line-length = 100` |
| Ruff lint | lint | the settings below |
| mypy | type check | `--strict` on `src/` and `tests/` |
| pytest with pytest-cov | unit, vector and contract tests | coverage floors from T-7 |
| Hypothesis | property tests | `parse`, `normalize` and the hierarchy functions |
| mutmut | mutation tests | the core modules, weekly scheduled job |
| griffe | API check against the last tag | `griffe check gatepost_postcode --against <last tag>` |
| towncrier | change files and changelog | one fragment in `changes/` per user-visible change |
| `spec/scripts/check-tells` | agent-tell checks | line length, emojis, other non-ASCII in source, the file names `utils`, `helpers`, `common` and `misc`, the `TODO(#123)` form and debug output |
| REUSE | licence headers | `reuse lint` |
| gitleaks | secret scan | each pull request and each push to `main` |

### Ruff settings

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
preview = true
explicit-preview-rules = true
select = [
  "E", "F", "W", "I", "B", "UP", "SIM", "RUF", "D", "ANN", "S", "PT",
  "PL", "C4", "PIE", "RET", "ERA", "T20", "T10", "C90",
]
extend-select = ["PLR1702", "PLR0917"]
ignore = ["PLR0913"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-nested-blocks = 3
max-positional-args = 4

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "D", "ANN", "PLR2004"]
```

`PLR1702` is a preview rule. `explicit-preview-rules` turns on only the preview rules that the file names. `PLR0913` is off, because TELL-3 counts only positional parameters. `PLR0917` counts only positional parameters.

### Agent-tell checks

| Rule | Check in Python |
|---|---|
| TELL-1 | Ruff `E501` with `line-length = 100`, and `check-tells` |
| TELL-2 | Ruff `C901` with `max-complexity = 10`, and `PLR1702` with `max-nested-blocks = 3` |
| TELL-3 | Ruff `PLR0917` with `max-positional-args = 4`. Keyword-only parameters do not count. |
| TELL-13 | Ruff `T20` and `T10`, and `check-tells`. They ban `print`, `pprint`, `breakpoint` and `pdb.set_trace`. |
| TELL-14 | `check-tells` |

## Rules

- **PY-1 MUST.** The package ships a `py.typed` marker. Every public function and method has full type hints. **(tool)**
- **PY-2 MUST.** Value types are frozen dataclasses with slots: `@dataclass(frozen=True, slots=True)`.
- **PY-3 MUST.** Options are keyword-only. The text argument of `parse` is positional-only: `parse(text, /, *, allow_partial=False)`.
- **PY-4 MUST.** Error codes use `class ErrorCode(StrEnum)`. Each member's value is the shared wire value, for example `ErrorCode.RATE_LIMITED` is `"rate_limited"`.
- **PY-5 MUST.** `PostcodeClient` and `AsyncPostcodeClient` have the same methods, the same options and the same errors. Only `async` and `await` differ.
- **PY-6 MUST.** The caller can pass an `httpx.Client` or an `httpx.AsyncClient` through the keyword `http_client`. The client closes only an HTTP client that it created.
- **PY-7 MUST.** Each client is a context manager. `with` closes the sync client. `async with` closes the async client.
- **PY-8 MUST.** Durations are seconds as `float`, as in httpx. Names have no unit suffix: `timeout`, `cache_ttl` and `retry_after`.
- **PY-9 MUST.** The async client lets `asyncio.CancelledError` pass through. It never catches it and never wraps it.
- **PY-10 MUST.** Errors subclass `PostcodeError`, which subclasses `Exception`. A raised error keeps its cause with `raise ... from ...`.
- **PY-11 MUST.** Each public symbol has a Google-style docstring with an `Example:` section. Write the example with doctest prompts (`>>>`). **(tool)**
- **PY-12 MUST.** The package does not call `print`, `pprint`, `breakpoint` or `pdb.set_trace`. Importing a module has no side effects. **(tool)**
- **PY-13 MUST.** `__all__` in `gatepost_postcode/__init__.py` lists every public symbol. Other modules start with an underscore.
- **PY-14 MUST.** Each `noqa` and each `type: ignore` comment names the rule and gives a reason.
- **PY-15 SHOULD.** Prefer functions and dataclasses. The allowed classes with behaviour are the two clients and the errors.
- **PY-16 MUST.** Code writes each non-ASCII or invisible character as an escape sequence, for example `"\u00a0"` and `"\u200b"`. **(tool)**
- **PY-17 MUST.** Tests replace the clock through an internal seam until the spec defines a clock option for API-10.
- **PY-18 MUST.** The client reads JSON with the `json` module and reads each field that it needs by name. It ignores unknown fields. An unknown value of a known field maps to the fallback that the spec defines. This follows API-14.
- **PY-19 MUST.** A semaphore limits each client to 4 requests at a time, as API-8 requires. The async client uses `asyncio.Semaphore`. The sync client uses `threading.BoundedSemaphore`.

## Names

| Element | Style | Example |
|---|---|---|
| function, method, variable | snake_case | `precision_for_accuracy` |
| class, dataclass, enum | PascalCase | `ParseResult` |
| enum member | UPPER_SNAKE_CASE | `ErrorCode.BAD_LENGTH` |
| constant | UPPER_SNAKE_CASE | `SPEC_VERSION` |
| error code value | snake_case string | `"bad_length"` |
| private module | leading underscore | `_normalize.py` |
| keyword option | snake_case | `allow_partial`, `http_client` |

## Package layout

```
src/gatepost_postcode/
  __init__.py           public API, __all__ only
  _parse.py             one private module per concept
  _client.py
  _async_client.py
  py.typed
tests/unit/
tests/vectors/          runs spec/vectors/
tests/contract/         runs against the mock server
changes/                towncrier fragments
pyproject.toml
uv.lock
README.md               from templates/README.md
CHANGELOG.md            generated by towncrier
```

## Publishing

- A GitHub Actions job builds with `uv build`.
- The job publishes to PyPI with trusted publishing and attestations.
- Pre-releases use PEP 440 suffixes, for example `0.2.0a1`.
