# Vectors

Each JSON file here holds shared test cases for one core function. Every SDK runs every case.

`scripts/build_vectors.py` builds these files. Do not edit them by hand. Edit the builder, then run `python3 scripts/build_vectors.py`.

`scripts/reference.py` is a plain reading of `grammar.md` and `data/`. `make check` runs every case through it. A case fails the check when the reading disagrees with it. The grammar wins over both the case and the reading.

## Format

    { "version": 1, "function": "parse", "description": "...", "cases": [ ... ] }

Each case has these fields:

| Field | Meaning |
|---|---|
| `id` | an id that is unique within one spec version, such as `parse-001`. A new case can change the ids after it. |
| `description` | the behaviour in domain words. Use it in the test name. |
| `input` | the argument, or an object of named arguments |
| `options` | options for the function, such as `{ "allowPartial": true }` |
| `expect` | the expected result |

## Expected results

| Function | `expect` |
|---|---|
| `normalize`, `isLegacy`, `contains`, `redact`, `stateName`, `precisionForAccuracy` | `{ "value": ... }` |
| `parse` | `{ "ok": true, "compact", "canonical", "display", "precision", "segments" }`, or `{ "ok": false, "error": { "code", "segment", "suggestion" } }` |
| `truncate` | `{ "canonical": ... }`, or `{ "rejects": true }` when the call must fail with the language's programmer error |
| `parent` | `{ "canonical": ... }`, where null means no parent |

The Interface section of `grammar.md` defines the fields of a parse result and of a parse error.

## Runner rules

- For `truncate`, `parent`, `contains` and `redact`, the inputs are canonical codes. Parse them with `allowPartial` before the call.
- For `precisionForAccuracy`, change the strings `NaN`, `Infinity` and `-Infinity` into the language's numbers. Change null into the language's "no value".
- Non-ASCII inputs are JSON escapes. Every file is ASCII.
