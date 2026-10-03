# Gatepost spec

The shared contract for every Gatepost SDK: the postcode grammar, the data files, the test vectors, the coding standards and the repo templates.

> Unofficial. Not made or endorsed by NIPOST.

## Contents

| Path | Holds |
|---|---|
| `grammar.md` | how every SDK reads and writes postcodes, and the public interface |
| `client.md` | how every client calls NIPOST's gateway: results, errors, retries and the queue |
| `openapi/` | NIPOST's gateway, completed with the responses that its own file leaves out |
| `fixtures/` | synthetic gateway responses and keys for the mock server |
| `contract/` | shared client test cases that every client must pass against the mock server |
| `data/` | state codes, GPS accuracy limits and the postcode format |
| `vectors/` | shared test cases that every SDK must pass |
| `standards/` | the coding standards and one file for each language |
| `CONTEXT.md` | the glossary |
| `templates/` | files for new repos |
| `scripts/` | `check-tells`, the vector builder, a plain reading of the grammar that checks each vector, and the checks of the OpenAPI file, the fixtures and the scenarios |

## Check

Run `make check`. It needs Python 3.11 or later and `uv`.

## Licence

Apache-2.0. See `LICENSE` and `NOTICE`.
