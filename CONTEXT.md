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
The third segment. Three characters that name a district within an LGA. NIPOST uses districts for postal sorting.
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
The `spec` repo, which holds the grammar, the vectors, the fixtures, the completed OpenAPI file and these standards.
_Avoid_: schema, contract (for the repo)

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

**Tell**:
A habit that makes code look machine-written, such as very long lines.
_Avoid_: smell (smells are design problems), anti-pattern
