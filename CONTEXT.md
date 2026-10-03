# Gatepost

Unofficial, open-source developer tools for Nigeria's National Digital Postcode. This glossary fixes one name for each concept, in every language and every repo.

## Language

### The postcode

**Postcode**:
The 11-character code that NIPOST gives to one addressable building or location.
_Avoid_: digital address, address code, zip code, postal code

**Legacy postcode**:
An old 6-digit NIPOST postcode. It names an area, not a building.
_Avoid_: old code, zip

**Segment**:
One of the five parts of a postcode: state, LGA, district, area and unit.
_Avoid_: part, field, component, chunk

**State**:
The first segment. Two letters that name one of the 36 states or the Federal Capital Territory.
_Avoid_: region, province

**LGA**:
The second segment. Two digits that name a local government area within a state.
_Avoid_: council, local government, municipality

**District**:
The third segment. Three characters that name a district within an LGA.
_Avoid_: sorting code, sector

**Area**:
The fourth segment. Two letters that name the smallest polygon in the system. An area holds at most 99 units.
_Avoid_: zone, block, neighbourhood

**Unit**:
The fifth segment. Two digits that name one building or delivery point within an area.
_Avoid_: building number, house number, delivery unit

**Partial postcode**:
A postcode that stops after the state, LGA, district or area segment.
_Avoid_: prefix, incomplete code
Exception: `prefix` is the name of the first parameter of `contains`.

**Precision**:
The most specific segment that a postcode or a result contains.
_Avoid_: level, granularity, resolution

### Forms of a postcode

**Compact form**:
The postcode with no separators, for example `EK01A03FK01`.
_Avoid_: raw, plain

**Canonical form**:
The postcode with hyphens between segments, for example `EK-01-A03-FK-01`.
_Avoid_: formatted, standard form

**Display form**:
The postcode with spaces between segments, for example `EK 01 A03 FK 01`.
_Avoid_: pretty, human form

**Normalise**:
To change input in three steps, in this order: apply NFKC, remove the separators, and change the ASCII letters to upper case. `grammar.md` defines the steps.
_Avoid_: sanitise, canonicalise

**Code point**:
One Unicode code point. It is not a UTF-16 unit, a byte or a grapheme cluster. For example, U+1D404 is one code point and two UTF-16 units.
_Avoid_: character (when you count input), char

**Input limit**:
The most code points that `parse` and `isLegacy` read. It is `maxInputCodePoints` in `data/format.json`. Over the limit, `parse` gives `bad_length` and `isLegacy` gives false. Both functions apply the limit before they normalise.
_Avoid_: max length, length limit, size limit

**Suggestion**:
The canonical form that `parse` offers with `unknown_state` or `bad_segment`, when a fix of look-alike characters makes the code parse. It is a hint, never a success. The word means this hint from `parse`. It does not mean the suggestions that NIPOST's autocomplete API returns.
_Avoid_: correction, autocorrect

**Parse result**:
What `parse` returns: a postcode, or a parse error. The Interface section of `grammar.md` defines its fields.
_Avoid_: outcome, response

**Parse error**:
The reason that `parse` rejected its input. It has a code, the failing segment and a suggestion. It is a value that `parse` returns, not an exception.
_Avoid_: validation error, exception

### NIPOST's API

**Gateway**:
NIPOST's public API at `api.postcode.gov.ng`.
_Avoid_: server, backend, endpoint (for the whole API)

**Lookup**:
A request to the gateway for the facts about one postcode.
_Avoid_: query, fetch, resolve

**Lookup level**:
How much data a lookup returns, from 1 for validity only to 5 for point geometry.
_Avoid_: tier, access level, depth

**Reverse geocode**:
A request for the nearest unit to a coordinate.
_Avoid_: reverse lookup, locate

**Accuracy**:
The radius in metres within which a GPS fix is likely correct.
_Avoid_: precision, error margin

**Secret key**:
An API key for servers. It starts with `nipost_test_` or `nipost_live_`.
_Avoid_: private key, API secret

**Publishable key**:
An API key that can ship inside an app or a web page. It starts with `nipost_pk_`.
_Avoid_: public key, client key

**Widget**:
NIPOST's own postcode picker. Gatepost does not build widgets.
_Avoid_: using this word for a Gatepost component

### Gatepost

**Spec**:
The `spec` repo. It holds the grammar, the client contract, the data, the vectors, the fixtures, the completed OpenAPI file and the standards.
_Avoid_: schema, contract (for the repo)

**Contract scenario**:
One shared test case in `spec/contract/`. It names the calls, the mock server's responses and the outcome that every client must reach.
_Avoid_: contract test (for the file), vector, fixture

**Attempt**:
One request that a client sends for one call. A retry is the second or third attempt.
_Avoid_: try, request (when you count them)

**Evidence**:
How Gatepost knows the shape of a gateway response: `observed` in its own calls, `documented` by NIPOST only, or `assumed` by the mock server.
_Avoid_: source, confidence, proof

**Vector**:
One shared test case in `spec/vectors/` that every SDK must pass.
_Avoid_: fixture, example, golden file

**Fixture**:
Synthetic data that the mock server returns.
_Avoid_: vector, stub, sample

**Mock server**:
The local server that imitates the gateway with fixtures.
_Avoid_: fake API, stub server, sandbox

**SDK**:
The core and the client for one language.
_Avoid_: library (for the pair), wrapper, binding

**Core**:
The part of an SDK that parses and formats postcodes without network access.
_Avoid_: utils, base, common

**Client**:
The part of an SDK that calls the gateway.
_Avoid_: API wrapper, service, fetcher

**Field**:
A Gatepost UI component in which a user enters or picks a postcode.
_Avoid_: input, widget, picker

**Confirm**:
To show the user what a postcode points to before the app stores it.
_Avoid_: verify, validate (for this step)

**Check status**:
What the WooCommerce plugin learned about the postcode of an order: `valid`, `invalid`, `unchecked` or `error`. The order meta `_gatepost_postcode_check` holds it.
_Avoid_: verification status, validation result

**Tell**:
A habit that makes code look machine-written, such as very long lines.
_Avoid_: smell (smells are design problems), anti-pattern
