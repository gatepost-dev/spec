<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/gatepost-dev/.github/main/brand/gatepost-lockup-dark.svg">
    <img src="https://raw.githubusercontent.com/gatepost-dev/.github/main/brand/gatepost-lockup.svg" alt="Gatepost" width="220">
  </picture>
</p>

<h1 align="center">Gatepost spec</h1>

<p align="center">The shared contract for every Gatepost SDK: the postcode grammar, the data files, the test vectors and the coding standards.</p>

<p align="center">
  <a href="https://github.com/gatepost-dev/spec/actions/workflows/ci.yml"><img src="https://github.com/gatepost-dev/spec/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status"></a>
  <a href="https://github.com/gatepost-dev/spec/blob/main/LICENSE"><img src="https://img.shields.io/badge/licence-Apache--2.0-blue?style=flat" alt="Licence: Apache-2.0"></a>
</p>

<p align="center">
  <a href="https://gatepost-dev.github.io/docs/">Docs</a>
  &middot;
  <a href="https://gatepost-dev.github.io/docs/playground/">Playground</a>
  &middot;
  <a href="https://gatepost-dev.github.io/docs/spec/grammar/">Grammar</a>
  &middot;
  <a href="https://github.com/gatepost-dev/.github/blob/main/CONTRIBUTING.md">Contributing</a>
  &middot;
  <a href="https://github.com/gatepost-dev/spec/discussions">Discussions</a>
</p>

> Unofficial. Not made or endorsed by NIPOST.

This repo defines how every Gatepost SDK reads and writes Nigeria's digital postcodes, and how every Gatepost client calls NIPOST's gateway. An SDK is correct when it passes the shared vectors and the contract scenarios. If `grammar.md` and a vector disagree, `grammar.md` wins, and the disagreement is a bug.

The current version is in [`VERSION`](VERSION).

## A postcode in three forms

| Form | Example | Use |
|---|---|---|
| Compact | `EK01A03FK01` | storage and comparison |
| Canonical | `EK-01-A03-FK-01` | APIs and logs |
| Display | `EK 01 A03 FK 01` | screens and print |

A postcode has five segments, from large to small: state, LGA, district, area and unit. [`grammar.md`](grammar.md) has the rules.

## One test vector

This case is `contains-001` in [`vectors/contains.json`](vectors/contains.json).

```json
{
  "id": "contains-001",
  "description": "finds a full code in its district",
  "input": {
    "prefix": "EK-01-A03",
    "code": "EK-01-A03-FK-01"
  },
  "options": {},
  "expect": {
    "value": true
  }
}
```

Every SDK runs the cases in [`vectors/`](vectors).

## Contents

| Path | Holds |
|---|---|
| [`grammar.md`](grammar.md) | how every SDK reads and writes postcodes, and the public interface |
| [`client.md`](client.md) | how every client calls NIPOST's gateway: results, errors, retries and the queue |
| [`openapi/`](openapi) | NIPOST's gateway, completed with the responses that its own file leaves out |
| [`fixtures/`](fixtures) | synthetic gateway responses and keys for the mock server |
| [`contract/`](contract) | shared client test cases that every client must pass against the mock server |
| [`data/`](data) | state codes, GPS accuracy limits and the postcode format |
| [`vectors/`](vectors) | shared test cases that every SDK must pass |
| [`standards/`](standards) | the coding standards and one file for each language |
| [`CONTEXT.md`](CONTEXT.md) | the glossary |
| [`templates/`](templates) | files for new repos |
| [`scripts/`](scripts) | `check-tells`, the vector builder, a plain reading of the grammar that checks each vector, and the checks of the OpenAPI file, the fixtures and the scenarios |

## Who uses it

| Repo | Language | Implements |
|---|---|---|
| [js](https://github.com/gatepost-dev/js) | TypeScript | the grammar and the client |
| [php](https://github.com/gatepost-dev/php) | PHP | the grammar and the client |

The [docs site](https://gatepost-dev.github.io/docs/) shows the same grammar and client contract as pages for readers.

## Change the spec

A change to the public interface of an SDK starts here. Open an issue first. Then read [`CONTRIBUTING.md`](https://github.com/gatepost-dev/.github/blob/main/CONTRIBUTING.md). Run `make check` before you open a pull request. It needs Python 3.11 or later and `uv`.

## Support

Ask questions in [GitHub Discussions](https://github.com/gatepost-dev/spec/discussions). Report bugs in [GitHub Issues](https://github.com/gatepost-dev/spec/issues). Report security problems through the [private form](https://github.com/gatepost-dev/spec/security/advisories/new).

## Licence

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
