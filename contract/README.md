# Contract scenarios

Each JSON file here is one contract scenario. It names the calls that a test makes, the responses that the mock server gives, and the outcome that every client must reach. `client.md` defines the behaviour. The scenarios test it in every SDK (T-3).

## Format

```json
{
  "version": 1,
  "id": "lookup-retry-503",
  "description": "A 503 is retried after the first wait, and the second attempt succeeds.",
  "client": {"apiKey": "nipost_test_mock_l3"},
  "calls": [{"method": "lookup", "code": "FC-01-Z99-ZZ-01", "level": 1}],
  "responses": [
    {"status": 503, "body": {"error": {"code": "unavailable", "message": "try again"}}},
    {"fixture": "lookup/valid-level-1"}
  ],
  "expect": {
    "attempts": 2,
    "waitsMs": [{"min": 500, "max": 750}],
    "outcomes": [{"result": {"postcode": "FC-01-Z99-ZZ-01", "valid": true}}]
  }
}
```

The outcome above is short. A real scenario lists every field of the result.

| Field | Meaning |
|---|---|
| `version` | the format version, which is 1 |
| `id` | the file name without `.json` |
| `description` | the rule that the scenario tests, in one sentence |
| `client` | the client options: `apiKey`, `timeoutMs`, `maxRetries` and `cacheTtlMs`. A missing option keeps its default. The test sets `baseUrl` to the mock server |
| `order` | `parallel` or `sequential`, when there is more than one call |
| `calls` | the calls, in order |
| `responses` | the responses of the mock server, one for each request, in order |
| `expect` | the outcome |

### Calls

| `method` | Other fields |
|---|---|
| `lookup` | `code`, and `level` when the call passes a level |
| `reverse` | `lat`, `lng`, and `maxDistanceM` when the call passes a radius |
| `autocomplete` | `q` |

With `parallel`, the test starts every call before it waits for any of them. With `sequential`, it waits for each call before it starts the next one.

### Responses

The mock server gives the first response to the first request, the second response to the second request, and so on. When the requests outnumber the responses, it repeats the last response. Each response has exactly one of these fields:

| Field | The mock server |
|---|---|
| `body` | sends this JSON body with `status` |
| `text` | sends this text body with `status` |
| `fixture` | sends the fixture `fixtures/<name>.json`, with its status and body |
| `hang` | sends nothing, and keeps the connection open until the client closes it |
| `drop` | closes the connection without a response |

- `headers` adds response headers to `body`, `text` or `fixture`. The mock server adds `Content-Type: application/json` to a JSON body, and the CORS headers to every response.
- `delayMs` makes the mock server wait before it answers.
- A scenario with no request has an empty `responses` list.

### Expect

| Field | Meaning |
|---|---|
| `attempts` | the number of requests that reached the transport, for all calls together |
| `waitsMs` | for one call, the bounds of each wait between two attempts, in milliseconds |
| `maxInFlight` | the most requests that were in flight at one time |
| `request` | the first request: `method`, `path`, `query` and `apiKey`, which is null when the request had no `X-API-Key` header. `query` holds every parameter of the request, and no other, with each value as text |
| `outcomes` | one outcome for each call, in the order of the calls |

An outcome is `{"result": ...}` or `{"error": ...}`. `make check` plays each scenario as `client.md` says. It checks the attempts, the waits, the requests in flight, the first request and each outcome. The reply to the last attempt of a call decides its outcome. A result uses the field names in `client.md`. A postcode in a result is its canonical form. An error has `code`, `status`, `apiCode` and `retryAfterMs`.

A wait runs from the end of one attempt to the start of the next one. Timers can fire late, so a test can accept a wait up to 100 ms over `max`. It must not accept a wait under `min`. The scenario `lookup-retry-after-ten` waits 10 seconds, so a runner needs a time limit of at least 12 seconds for it.

## Running a scenario

1. Start the mock server.
2. Build a client with the scenario's options, and a transport that wraps the real one. The wrapper adds two headers to each request: `X-Scenario-Id` with the scenario's id, and `X-Scenario-Run` with a value that is new for each run. It also counts the requests, the waits between them and the requests in flight.
3. Make the calls, and compare the outcomes and the counts with `expect`.

The client itself never sends `X-Scenario-Id` or `X-Scenario-Run`. The mock server keeps the position in `responses` for each run, so a test can run a scenario again with a new run value. A request with `X-Scenario-Id` and no `X-Scenario-Run` gets a 400 from the mock server.
