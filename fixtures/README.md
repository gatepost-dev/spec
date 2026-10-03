# Fixtures

The mock server answers with these files. Each file holds one response of NIPOST's gateway. Every postcode in them is synthetic: the district is `Z99` and the area is `ZZ`. The files hold no real address and no real coordinate.

## Format

```json
{
  "version": 1,
  "description": "The synthetic unit FC-01-Z99-ZZ-01 at lookup level 1.",
  "evidence": "observed",
  "schema": "LookupEnvelope",
  "status": 200,
  "body": { "data": { "postcode": "FC-01-Z99-ZZ-01", "valid": true } }
}
```

- `version` is the format version, which is 1.
- `evidence` is `observed`, `documented` or `assumed`, as in `openapi/gateway.completed.yaml`. It cannot claim more than the mark of the response in that file, or of its error code.
- `schema` names a schema in `components/schemas` of that file. The body must match it.
- `status` is the HTTP status of the response. A response of the OpenAPI file with the same schema must have this status.
- An error body carries an error code of that response. The file name of an error states its code: `rate-limited.json` holds `rate_limited`. A number at the end names a level. `unknown-path.json` names a case, not a code.

`make check` tests each of these rules. It also fails on a postcode outside `FC`, `Z99` and `ZZ`, and on text in the form of a key that is not a mock key.

## How the mock server uses them

| Request | Fixture |
|---|---|
| `lookup` of the postcode in `lookup/valid-level-1.json` | `lookup/valid-level-N.json`, where N is the level |
| `lookup` of another postcode that is well-formed | `lookup/not-found.json` |
| `lookup` of text that is not a postcode | `lookup/invalid.json` |
| `reverse` at the coordinate of `reverse/unit.json` or `reverse/area.json` | that file |
| `reverse` at any other coordinate | `reverse/not-found.json` |
| `nearby` | `nearby/empty.json` |
| an error | the file in `errors/` with the same error code |
| a path that the gateway does not serve | `errors/unknown-path.json`, which `x-gatepost-unknown-path` of the OpenAPI file describes |

- The mock server puts the caller's text, in upper case, in `postcode` of a lookup body, as the gateway does.
- It puts the request's coordinate and the applied radius in a reverse body.
- `level-not-granted-N.json` answers a key that holds level N.
- `keys.json` lists the mock server's keys, and the way that each one behaves.
- `autocomplete`, `assemble` and `disassemble` have no files. The mock server builds their bodies from the postcodes above and from `data/states.json`.

## After a new observation

A call can show a shape that differs from a file here, for example a lookup at level 2. Then change the file and its `evidence`, and change the schema in the OpenAPI file in the same pull request. Never commit the real response. Copy its shape, and keep the synthetic values.
