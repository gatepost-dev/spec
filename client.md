# Client

This file defines how every Gatepost client calls NIPOST's gateway. The contract scenarios in `contract/` test each rule here, except the rules that the last section lists. If this file and a scenario disagree, this file wins. Such a disagreement is a bug in the spec.

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
| `timeoutMs` | the longest wait for one attempt, in milliseconds | 8000 |
| `maxRetries` | the most retries after the first attempt | 2 |
| `cacheTtlMs` | how long the client keeps a result, in milliseconds | 0, which turns the cache off |

A `timeoutMs` of 0 or less is a programmer error. So is a negative `maxRetries` or `cacheTtlMs`.

### Lookup result

| Field | Value |
|---|---|
| `postcode` | the postcode that the caller asked for, as the core parsed it |
| `valid` | true when the gateway knows the postcode |
| `status` | `valid`, `invalid`, `not_found`, `restricted`, or null |
| `levelRequested` | the lookup level that the caller asked for |
| `levelReceived` | the lookup level of the data in the response |
| `administrativeAddress` | the state name, the LGA name, the locality name and the zone, or null |
| `recentHouseAddress` | text, or null |
| `buildingUseStatus` | text, or null |

- The client never takes `postcode` from the response. The gateway echoes the caller's text there, also for text that is not a postcode.
- `status` is null when the response has no `status`, or a value that this table does not list.
- `levelReceived` comes from the fields of the response. It is 5 when `point_geometry` is present, 4 for `other_building_info`, 3 for `building_use_status`, and 2 for either address field. Otherwise it is 1.
- `recentHouseAddress` is the text in `recent_house_address.recent`.
- A response with `valid: false` is a result, not an error.

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

- `found` can be true while `unit` is null. The gateway then found an area, but no unit within the radius.
- `confidence` is `low` for a value that this table does not list.
- The gateway sends the coordinate as `[lng, lat]`. The client does not return it.

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

The gateway sends the value of one segment only. For the text `FC01Z`, the suggestion `Z99` gives the postcode `FC-01-Z99`. The client parses that text with partial postcodes allowed. When it does not parse, `postcode` is null.

## Requests

- The client sends `X-API-Key` only when the caller gave a key.
- `lookup` parses the code with the core first. A code that does not parse raises `invalid_input`, and no request goes out. Partial postcodes do not pass. The request sends the canonical form and the level: `code=FC-01-Z99-ZZ-01&level=1`.
- `reverse` sends `lat` and `lng`, and `max_distance_m` when the caller gave a radius.
- `autocomplete` normalises its text with the core. Empty text, text of more than 11 characters, and text with a character other than A to Z and 0 to 9 raise `invalid_input`, and no request goes out. The gateway does not answer an empty `q`. The request sends the normalised text: `q=FC01Z`.

## Errors

`PostcodeError` has these fields:

| Field | Value |
|---|---|
| `code` | one of the error codes below |
| `status` | the HTTP status, or null when no response arrived |
| `apiCode` | the `error.code` of the response body, or null |
| `retryAfterMs` | the wait that `Retry-After` asked for, in milliseconds, or null |

The error code comes from the first row that matches.

| Condition | Error code | Retried |
|---|---|---|
| the client's own check of the input fails | `invalid_input` | no request goes out |
| status 401 | `unauthorized` | no |
| status 402 | `insufficient_credits` | no |
| status 403, with the API code `origin_not_allowed` | `origin_not_allowed` | no |
| status 403, with any other API code | `forbidden` | no |
| status 429 | `rate_limited` | see below |
| status 502, 503 or 504 | `server_error` | yes |
| any other status from 400 to 499 | `invalid_input` | no |
| any other status that is not 200 | `server_error` | no |
| status 200, with a body that is not a JSON object with a `data` field | `server_error` | no |
| no response, because the connection failed | `network_error` | yes |
| no response within `timeoutMs` | `timeout` | yes, except for `autocomplete` |

- `apiCode` is set when the body is a JSON object whose `error.code` is text. The client never raises an error for an unexpected error body.
- A cancelled call ends with the platform's own cancellation error, not with `PostcodeError` (API-11).
- No error message holds the API key (ERR-3).

## Retries

- A client makes at most `1 + maxRetries` attempts for one call.
- Before retry `n`, the first being 1, the client waits `500 x 2^(n - 1)` milliseconds, plus a random wait from 0 to 250 milliseconds. The first retry waits 500 to 750 ms, and the second waits 1000 to 1250 ms.
- A 429 with `Retry-After` of 10 seconds or less: the client waits that long, with no random part, and tries again. `Retry-After` can hold seconds or an HTTP date.
- A 429 with a longer `Retry-After`: the client raises `rate_limited` at once, and `retryAfterMs` holds the wait. A caller can then tell a user when to try again.
- A 429 with no `Retry-After`: the client raises `rate_limited` at once. The gateway counts requests in each clock minute, so a retry after half a second would fail too.
- The client does not retry a timeout of `autocomplete`. The next keystroke replaces the call.

## Sharing, queue and cache

- Two calls of the same method with the same arguments share one request while the first one is in flight. Both callers get the same result or the same error.
- A client sends at most 4 requests at a time. Further calls wait in a queue, in the order of the calls.
- With `cacheTtlMs` above 0, the client keeps each result for that long. A call with the same method and the same arguments then gets the kept result, and no request goes out. Errors stay out of the cache. `clearCache()` removes every kept result.

## Rules that no scenario tests

Each client tests these rules itself.

- The programmer errors in the client options.
- Cancellation (API-11), because each language cancels in its own way.
- That no error message holds the API key.
- The random part of each wait, beyond its bounds.
- A `Retry-After` that holds an HTTP date. A scenario cannot hold a date that is a few seconds ahead.
