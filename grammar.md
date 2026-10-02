# Postcode grammar

Spec version 0.1.0. This file defines how every Gatepost SDK reads and writes Nigeria's digital postcodes. The values live in `data/`. The vectors in `vectors/` test every rule, with two exceptions. Two groups of rules have no shared vectors: the Unicode version (see Normalise) and text that is not well-formed (see Parse). JSON cannot carry invalid UTF-8, and PHP rejects an escape for a lone surrogate. Each SDK tests these rules itself. If this file and a vector disagree, this file wins. Such a disagreement is a bug in the spec.

## Forms

| Form | Example | Use |
|---|---|---|
| Compact | `EK01A03FK01` | storage and comparison |
| Canonical | `EK-01-A03-FK-01` | APIs and logs |
| Display | `EK 01 A03 FK 01` | screens and print |

## Segments

`segments` in `data/format.json` holds the length, the characters and the minimum of each segment.

| Segment | Length | Characters | Rule |
|---|---|---|---|
| state | 2 | letters | one of the 37 codes in `data/states.json` |
| lga | 2 | digits | 01 to 99 |
| district | 3 | letters or digits | any combination |
| area | 2 | letters | |
| unit | 2 | digits | 01 to 99 |

A partial postcode stops after the state, LGA, district or area segment. Its length is 2, 4, 7 or 9 characters. Its precision is the last segment that it contains.

## Normalise

1. Apply Unicode NFKC. This changes full-width letters and digits to ASCII.
2. Remove each separator in `data/format.json`: white space, hyphens and dashes, the full stop, and zero-width characters.
3. Change the ASCII letters a to z to upper case. Keep every other character as it is.

An SDK without a full NFKC can apply NFKC through a table. The table lists only the characters whose NFKC form holds only ASCII characters and separators. The SDK's `parse` and `isLegacy` must then give the same results as with full NFKC, for every input. The SDK's `normalize` can keep a character that full NFKC changes, such as U+00B5, in text that `parse` rejects. Each `normalize` vector gives the same result either way.

Unicode 17.0 is the baseline for NFKC. A table must come from that version. A platform can have a Unicode version older than 17.0. An SDK on that platform can give other results for a character that a later version added. Unicode's stability policy freezes the NFKC form of an assigned character, so only an added character can differ. For example, NFKC in Unicode 17.0 changes U+A7F1 to S, but a platform with Unicode 16.0 or older keeps it. No vector holds such a character.

A format character that is not in the list stays. For example, the right-to-left override U+202E can change the order in which a code shows on screen, so `parse` gives `bad_character` for it.

`normalize` has no length limit. Bound untrusted text before you call it, or call `parse`, which checks the limit first.

## Parse

First count the Unicode code points of the input. Do not count UTF-16 units, UTF-8 bytes or grapheme clusters. A lone surrogate, in a language that can hold one, counts as one code point. The last paragraph of this section gives the rule for input that is not well-formed. An SDK can stop counting at 65. If the input has more than `maxInputCodePoints` code points (64 in `data/format.json`), the error code is `bad_length`, and `parse` does not normalise the input. The limit bounds the cost of NFKC, which can take seconds on a long run of combining marks. Otherwise, normalise the input. Then apply these checks in order. The first check that fails gives the error code.

1. `empty`: no character is left.
2. `legacy_code`: exactly 6 ASCII digits are left (`legacyPattern` in `data/format.json`). These are old NIPOST postcodes.
3. `bad_character`: a character other than A to Z and 0 to 9 is left.
4. `bad_length`: the length is not 11. With `allowPartial`, the lengths 2, 4, 7 and 9 also pass.
5. `unknown_state`: the first two characters are not a code in `data/states.json`.
6. `bad_segment`: a segment breaks its rule in the table above. Check the segments in order, and report the first one that fails.

For `unknown_state` and `bad_segment`, the error names the segment. For the other codes, the segment is null.

Input that is not well-formed Unicode is never a postcode. In a language whose strings hold bytes, the SDK does not count the code points of input that is not valid UTF-8. `parse` gives `bad_length` for such input when it has more than 4 x `maxInputCodePoints` bytes, and `bad_character` otherwise. In a language whose strings can hold a lone surrogate, the surrogate counts as one code point. The input limit applies as usual. Within the limit, `parse` gives `bad_character` for input that holds a lone surrogate. `isLegacy` gives false for input that is not well-formed. `normalize` keeps each byte that is not part of a valid UTF-8 sequence, and each lone surrogate, in place. It normalises the text on each side of such a byte or surrogate on its own. No function throws for input that is not well-formed.

## Suggestions

For `unknown_state` and `bad_segment`, build one corrected code. `suggestions` in `data/format.json` holds the fixes:

- In the letter segments, state and area, change `0` to `O` and `1` to `I`.
- In the digit segments, LGA and unit, change `O` to `0`, `I` to `1` and `L` to `1`.
- Never change the district. NIPOST has not confirmed which characters it uses there.

Parse the corrected code with the same options. If it parses, the suggestion is its canonical form. If it does not parse, or if no character changed, the suggestion is null. A suggestion is a hint only. `parse` never returns a corrected code as a success.

## Legacy postcodes

`isLegacy` is false for input with more than `maxInputCodePoints` code points, and it does not normalise such input. Otherwise, it is true when the normalised input is exactly 6 ASCII digits.

## Hierarchy

- `truncate(code, to)` keeps the segments up to `to`. It fails when `to` is more precise than the code, and when `to` is not a precision. Both are programmer mistakes. Each language uses its standard error for them, for example `RangeError` in TypeScript.
- `parent(code)` returns the code with one segment fewer. A postcode with only the state segment has no parent, so `parent` returns null for it.
- `contains(prefix, code)` is true when the code has every segment of the prefix, in the same places.
- `redact(code)` replaces the unit with `**` in the canonical form. A code without a unit stays the same.

## State names

`stateName(code)` returns the name in `data/states.json`, and it ignores the case of the ASCII letters a to z only. It does not remove spaces or other characters. It does not apply NFKC. An unknown code gives null. The codes are NIPOST's. They equal ISO 3166-2:NG, except BR, GM, KG, SK and YB, where ISO uses BO, GO, KO, SO and YO. Each state in `data/states.json` also keeps its ISO code in the `iso` field.

## GPS precision

`precisionForAccuracy(metres)` returns the most precise segment that a GPS fix of that accuracy supports, from `data/precision.json`. An unknown, negative, infinite or NaN accuracy gives `lga`. The value -0 counts as 0, so it is not negative. A fix with an accuracy equal to a limit gets the precision of that limit.

## Versions

`VERSION` holds the spec version. Each SDK exposes it as `SPEC_VERSION`. Each vector file carries a format version, which is 1.

## Interface

An SDK exposes the symbols in this table and the types that they need. A language file gives the idiomatic form of each name and lists the additions that its language needs, such as an options type. The function names are the names in the vector files. This section covers the core. The interface of the client comes later, with the completed OpenAPI file.

| Symbol | Takes | Returns | Rules |
|---|---|---|---|
| `normalize(text)` | text | text | Normalise |
| `parse(text, allowPartial)` | text, and `allowPartial`, which is false by default | a parse result | Parse |
| `isLegacy(text)` | text | true or false | Legacy postcodes |
| `truncate(code, to)` | a postcode and a precision | a postcode | Hierarchy |
| `parent(code)` | a postcode | a postcode, or null | Hierarchy |
| `contains(prefix, code)` | two postcodes | true or false | Hierarchy |
| `redact(code)` | a postcode | text | Hierarchy |
| `stateName(code)` | text | the name of a state, or null | State names |
| `precisionForAccuracy(metres)` | a number, or no value | a precision | GPS precision |
| `SPEC_VERSION` (a constant) | none | the spec version, as text | Versions |

A parse result is a success or a failure. A success holds a postcode. A failure holds a parse error. A language can shape the result in the way that it expects, if it keeps the fields below. In the vectors, a success has the field `ok` with the value true, beside the fields of the postcode. A failure has `ok` with the value false, and an `error` field that holds the parse error.

A postcode that `parse` accepted has these fields:

- `compact`, `canonical` and `display`: the three forms of the code.
- `precision`: the last segment that the code contains. It is one of `state`, `lga`, `district`, `area` and `unit`.
- `segments`: the text of each of `state`, `lga`, `district`, `area` and `unit`. Each segment after the precision is null. For example, the segments of `EK-01` are `EK` and `01`, and null for the district, the area and the unit.

A parse error has these fields:

- `code`: one of `empty`, `legacy_code`, `bad_character`, `bad_length`, `unknown_state` and `bad_segment`.
- `segment`: the name of the failing segment for `unknown_state` and `bad_segment`, and null for the other codes.
- `suggestion`: the canonical form of one corrected code, or null.
