# Gatepost spec

The shared contract for every Gatepost SDK: the postcode grammar, the data files, the test vectors, the coding standards and the repo templates.

> Unofficial. Not made or endorsed by NIPOST.

## Contents

| Path | Holds |
|---|---|
| `grammar.md` | how every SDK reads and writes postcodes |
| `data/` | state codes, GPS accuracy limits and the postcode format |
| `vectors/` | shared test cases that every SDK must pass |
| `standards/` | the coding standards and one file for each language |
| `CONTEXT.md` | the glossary |
| `templates/` | files for new repos |
| `scripts/` | `check-tells` and the vector builder |

## Check

Run `make check`. It needs Python 3.11 or later and `uv`.

## Licence

Apache-2.0. See `LICENSE` and `NOTICE`.
