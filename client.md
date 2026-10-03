# Client

This file defines how every Gatepost client calls NIPOST's gateway. The contract scenarios in `contract/` test each rule here, except the rules that the last section lists. Each rule names its scenarios, and `make check` fails when a named scenario has no file or a scenario has no rule here. If this file and a scenario disagree, this file wins. Such a disagreement is a bug in the spec.

`openapi/gateway.completed.yaml` describes the gateway itself. Each response in it carries an evidence mark. Gatepost saw some responses in calls of its own. It knows others only from NIPOST's docs. A client reads both kinds in the same way.

## Interface

A client exposes the symbols in this table and the types that they need. A language file gives the idiomatic form of each name, as for the core.

| Symbol | Takes | Returns |
|---|---|---|
| `PostcodeClient(options)` | client options | a client |
| `lookup(code, level)` | a postcode as text or as a postcode, and a lookup level, which is 1 by default | a lookup result |
| `reverse(lat, lng, maxDistanceM)` | a latitude and a longitude in degrees, and an optional radius in metres | a reverse result |
| `autocomplete(q)` | the text that a user typed | an autocomplete result |
| `clearCache()` | none | none |
| `PostcodeError` | none | the error that each call can raise |

Each call that sends a request is asynchronous, and the caller can cancel it (API-11). The client does not wrap `nearby`, `assemble` and `disassemble`. The core does the work of the assembly endpoints offline. No call to `nearby` has returned a unit yet, so its result has no defined fields.

### Client options

| Option | Meaning | Default |
|---|---|---|
| `apiKey` | the key for the `X-API-Key` header | none, so the client sends no key |
| `baseUrl` | the gateway's address | `https://api.postcode.gov.ng` |
| `transport` | the HTTP transport, in the language's standard form | the platform's own |
| `timeoutMs` | the longest wait for one attempt, in milliseconds | 8000, and 15000 for `autocomplete` |
| `maxRetries` | the most retries after the first attempt | 2 |
| `cacheTtlMs` | how long the client keeps a result, in milliseconds | 0, which disables the cache |

A `timeoutMs` of 0 or less is a programmer error. So is a negative `maxRetries` or `cacheTtlMs`.

### Lookup result

| Field | Value |
|---|---|
| `postcode` | the postcode that the caller asked for, as the core parsed it |
| `valid` | true when the gateway knows the postcode |
| `status` | text, or null. The known values are `valid`, `invalid`, `not_found` and `restricted` |
| `levelRequested` | the lookup level that the caller asked for |
| `levelReceived` | the lookup level of the data in the response |
| `administrativeAddress` | an object with `stateName`, `lgaName`, `localityName` and `zone`, or null |
| `recentHouseAddress` | text, or null |
| `buildingUseStatus` | text, or null |

- The client never takes `postcode` from the response. The gateway echoes the caller's text there, also for text that is not a postcode. The scenario `lookup-echo-ignored` tests this rule.
- `status` is null when the response has no `status`. The client returns any other value of `status` as it is, also when this table does not list it, so that a new gateway status is not lost. The scenarios `lookup-level-2` and `lookup-unknown-status` test this rule.
- `levelReceived` comes from the fields of the response. It is 5 when `point_geometry` is present, 4 for `other_building_info`, 3 for `building_use_status`, and 2 for either address field. Otherwise it is 1. It can be lower than `levelRequested`. The scenarios `lookup-level-2`, `lookup-level-3`, `lookup-level-4`, `lookup-level-5`, `lookup-building-use-only` and `lookup-lower-level` test this rule.
- `recentHouseAddress` is the text in `recent_house_address.recent`. The scenario `lookup-level-2` tests it.
- A `status` that is present, not null and not text raises `unexpected_response`. The scenario `lookup-status-not-text` tests it.
- A response with `valid: false` is a result, not an error. The scenario `lookup-not-found` tests it.

### Reverse result

| Field | Value |
|---|---|
| `found` | true when the gateway found a unit or an area within the radius |
| `radiusM` | the radius that the gateway applied, in metres |
| `unit` | the nearest unit, or null |
| `area` | the area as a postcode, or null |
| `district` | the district as a postcode, or null |
| `state` | the state code, or null |

A unit has these fields:

| Field | Value |
|---|---|
| `postcode` | the unit's postcode, as the core parsed it |
| `distanceM` | the distance from the coordinate, in metres |
| `confidence` | `high`, `medium` or `low` |
| `stateName`, `lgaName`, `localityName` | text, or null |
| `address` | text, or null |

- The scenario `reverse-unit` tests a result with a unit.
- `found` can be true while `unit` is null. The gateway then found an area, but no unit within the radius. The scenario `reverse-area` tests it.
- A response with `found: false` is a result, not an error. The scenario `reverse-not-found` tests it.
- `confidence` is `low` for a value that this table does not list. The scenario `reverse-unknown-confidence` tests it.
- The gateway sends the coordinate as `[lng, lat]`. The client does not return it. The scenario `reverse-unit` tests it.

### Autocomplete result

| Field | Value |
|---|---|
| `segment` | the segment that holds the last character that the user typed |
| `suggestions` | a list of suggestions, in the gateway's order |

A suggestion has these fields:

| Field | Value |
|---|---|
| `code` | the value of the active segment, as the gateway sent it |
| `label` | text, or null |
| `postcode` | the partial postcode of the typed segments before the active one, followed by `code`, or null |

The gateway sends the value of one segment only. For the text `FC01Z`, the suggestion `Z99` gives the postcode `FC-01-Z99`. The client parses that text with partial postcodes allowed. When it does not parse, `postcode` is null. The scenarios `autocomplete-state` and `autocomplete-district` test this rule.

A client ignores a field that this contract does not use, in a lookup, a reverse or an autocomplete response. Such a field never changes the result and never raises an error. The scenarios `lookup-unknown-fields`, `reverse-unknown-fields` and `autocomplete-unknown-fields` test this rule, one for each call. The scenario `lookup-unknown-status` tests that an unknown `status` stays text.

## Requests

- The client sends `X-API-Key` only when the caller gave a key. The scenario `lookup-no-key` tests it.
- `lookup` parses the code with the core first. A code that does not parse raises `invalid_input`, and the client sends no request. Partial postcodes do not pass. The request sends the canonical form and the level: `code=FC-01-Z99-ZZ-01&level=1`. The scenarios `lookup-invalid-input`, `lookup-level-1` and `lookup-default-level` test this rule.
- `reverse` sends `lat` and `lng`, and `max_distance_m` when the caller gave a radius. The scenarios `reverse-unit` and `reverse-area` test this rule.
- Each of these raises `invalid_input`, and the client sends no request:
  - A `level` that is not a whole number from 1 to 5. The scenario `lookup-invalid-level` tests it.
  - A `lat` that is not finite or is outside -90 to 90. The scenario `reverse-invalid-lat` tests it.
  - A `lng` that is not finite or is outside -180 to 180. The scenario `reverse-invalid-lng` tests it.
  - A `maxDistanceM` below 0 or above 250. The OpenAPI file gives the range 0 to 250. The gateway cuts a larger value to 250 without a sign, so the client rejects it. It does not return a result for another radius. The scenarios `reverse-invalid-max-distance` and `reverse-invalid-negative-distance` test it. The scenarios `reverse-max-distance-zero` and `reverse-max-distance-250` test that both limits pass.
- The client writes each number in the query in its shortest decimal form, with no exponent and no trailing zero: `lat=9`, not `lat=9.0` and not `lat=9e0`. A negative zero is written `0`. A small value is written in full: `0.0000001`, not `1e-7`. Languages print numbers in different forms, so one fixed form gives every client the same query for the same input. The mock server compares numbers by value, so it also accepts `9.0`. The scenarios `reverse-plain-decimal` and `reverse-whole-number` test this rule.
- `autocomplete` normalises its text with the core. Empty text, text of more than 11 characters, and text with a character other than A to Z and 0 to 9 raise `invalid_input`, and the client sends no request. The gateway does not answer an empty `q`. The request sends the normalised text: `q=FC01Z`. The scenarios `autocomplete-empty-input`, `autocomplete-too-long`, `autocomplete-bad-character` and `autocomplete-district` test this rule.

## Errors

`PostcodeError` has these fields:

| Field | Value |
|---|---|
| `code` | one of the error codes below |
| `status` | the HTTP status, or null when no response arrived |
| `apiCode` | the `error.code` of the response body, or null |
| `retryAfterMs` | the wait that `Retry-After` asked for, in milliseconds, or null |

The error code comes from the first row that matches.

| Condition | Error code | Retried | Scenarios |
|---|---|---|---|
| the client's own check of the input fails | `invalid_input` | no request is sent | `lookup-invalid-input` |
| status 401 | `unauthorized` | no | `lookup-no-key`, `lookup-invalid-key` |
| status 402 | `insufficient_credits` | no | `lookup-insufficient-credits` |
| status 403, with the API code `origin_not_allowed` | `origin_not_allowed` | no | `lookup-origin-not-allowed` |
| status 403, with any other API code | `forbidden` | no | `lookup-level-not-granted` |
| status 429 | `rate_limited` | see below | `lookup-rate-limited` |
| status 502, 503 or 504 | `server_error` | yes | `lookup-retries-exhausted` |
| any other status from 400 to 499 | `invalid_input` | no | `lookup-bad-request` |
| any other status that is not 200 | `server_error` | no | `lookup-server-error` |
| status 200, with a body that is not a JSON object with a `data` field, or with a part that this contract uses missing or of the wrong type | `unexpected_response` | no | `lookup-malformed-body` |
| no response, because the connection failed | `network_error` | yes | `lookup-network-error` |
| no response within `timeoutMs` | `timeout` | yes, except for `autocomplete` | `lookup-timeout`, `autocomplete-timeout` |

- `apiCode` is set when the body is a JSON object whose `error.code` is text. The client never raises an error for an unexpected error body. The scenarios `lookup-bad-request` and `lookup-malformed-body` test this rule.
- A part that is missing or has the wrong type gives `unexpected_response`. These parts are: `valid` of a lookup, `found` of a reverse, `suggestions` of an autocomplete, a `status` that is present, not null and not text, and a postcode of a reverse result that the core cannot parse. The client never returns a guessed empty value in their place. The scenarios `lookup-malformed-body`, `lookup-missing-valid`, `lookup-status-not-text`, `lookup-no-data`, `reverse-missing-found`, `reverse-bad-postcode` and `autocomplete-suggestions-not-list` test this rule.
- A cancelled call ends with the platform's own cancellation error, not with `PostcodeError` (API-11).
- No error message holds the API key (ERR-3).

## Retries

- A client makes at most `1 + maxRetries` attempts for one call. The scenarios `lookup-retries-exhausted` and `lookup-max-retries-zero` test it.
- Before retry `n`, the first being 1, the client waits `500 x 2^(n - 1)` milliseconds, plus a random wait from 0 to 250 milliseconds. The first retry waits 500 to 750 ms, and the second waits 1000 to 1250 ms. The scenarios `lookup-retry-502`, `lookup-retry-503`, `lookup-retry-504` and `lookup-network-error` test this rule.
- A 429 with `Retry-After` of 10 seconds or less: the client waits that long, with no random part, and retries. `Retry-After` can hold seconds or an HTTP date. The scenarios `lookup-retry-after` and `lookup-retry-after-ten` test this rule.
- A 429 with a longer `Retry-After`: the client raises `rate_limited` at once, and `retryAfterMs` holds the wait. A caller can then tell a user when to try again. The scenarios `lookup-retry-after-eleven` and `lookup-retry-after-too-long` test this rule.
- A 429 with no `Retry-After`, or with an invalid one: the client raises `rate_limited` at once. Calls suggest that the gateway counts requests in each clock minute, so a retry after half a second would probably fail too. The scenario `lookup-rate-limited` tests it.
- A 502, 503 or 504 with a valid `Retry-After` of 10 seconds or less: the client waits that long, with no random part, as for a 429. A valid `Retry-After` is a whole number of seconds from 0 up, or an HTTP date that is not in the past. With any other value, or with no header, the client uses its own wait. `retryAfterMs` holds a valid value. The scenarios `lookup-retry-after-503` and `lookup-retry-after-invalid` test this rule.
- A call has a total deadline. It starts when the client sends the first attempt. It lasts `(1 + maxRetries) x timeoutMs`, plus `500 x 2^(n - 1) + 250` milliseconds for each retry `n`. With the defaults for `lookup`, that is 26 seconds. When the next wait would end after the deadline, the client raises the error of the last attempt at once. The scenario `lookup-deadline` tests this rule.
- The client does not retry a timeout of `autocomplete`. The next keystroke replaces the call. The scenario `autocomplete-timeout` tests it.

## Sharing, queue and cache

- Two calls of the same method with the same arguments share one request while the first one is in flight. Both callers get the same result or the same error. The scenarios `lookup-shared-request` and `lookup-shared-error` test this rule.
- The key of a shared request and of a cache entry is the method with the canonical form of the arguments. So `lookup("fc01z99zz01")` and `lookup("FC-01-Z99-ZZ-01")` share one request and one cache entry. The scenario `lookup-shared-spellings` tests the request.
- A shared request stops only when every caller that shares it cancels. A cancelled call frees its place among the 4 at once.
- A client sends at most 4 requests at a time. Further calls wait in a queue, in the order of the calls. The scenario `lookup-queue-limit` tests the limit.
- With `cacheTtlMs` above 0, the client keeps each result for that long. A call with the same method and the same arguments then gets the kept result, and the client sends no request. Errors stay out of the cache. `clearCache()` removes every kept result. The scenarios `lookup-cache-hit`, `lookup-cache-off` and `lookup-error-not-cached` test this rule.

## Rules that no scenario tests

Each client tests these rules itself.

- The programmer errors in the client options.
- Cancellation (API-11), because each language cancels in its own way.
- That no error message holds the API key.
- The cancellation rules of sharing and the queue: a shared request stops only when every caller cancels, and a cancelled call frees its place among the 4.
- The default `timeoutMs` of 15 seconds for `autocomplete`, because a scenario would wait that long.
- The random part of each wait, beyond its bounds.
- A `Retry-After` that holds an HTTP date. A scenario cannot hold a date that is a few seconds ahead.
- The order of the queue. A scenario counts the requests in flight, but not the order in which they leave.
- `clearCache()`. The scenario format has calls of the three methods only.
