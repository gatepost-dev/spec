# Postcode grammar

Spec version 0.1.0. This file defines how every Gatepost SDK reads and writes Nigeria's digital postcodes. The values live in `data/`. The vectors in `vectors/` test every rule.

## Forms

| Form | Example | Use |
|---|---|---|
| Compact | `EK01A03FK01` | storage and comparison |
| Canonical | `EK-01-A03-FK-01` | APIs and logs |
| Display | `EK 01 A03 FK 01` | screens and print |

## Segments

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

A format character that is not in the list stays. For example, the right-to-left override U+202E can change the order in which a code shows on screen, so `parse` gives `bad_character` for it.

`normalize` has no length limit. Bound untrusted text before you call it, or call `parse`, which checks the limit first.

## Parse

First count the Unicode code points of the input. Do not count UTF-16 units, UTF-8 bytes or grapheme clusters. A lone surrogate, in a language that can hold one, counts as one code point. An SDK can stop counting at 65. If the input has more than `maxInputCodePoints` code points (64 in `data/format.json`), the error code is `bad_length`, and `parse` does not normalise the input. The limit bounds the cost of NFKC, which can take seconds on a long run of combining marks. Otherwise, normalise the input. Then apply these checks in order. The first check that fails gives the error code.

1. `empty`: no character is left.
2. `legacy_code`: exactly 6 ASCII digits are left. These are old NIPOST postcodes.
3. `bad_character`: a character other than A to Z and 0 to 9 is left.
4. `bad_length`: the length is not 11. With `allowPartial`, the lengths 2, 4, 7 and 9 also pass.
5. `unknown_state`: the first two characters are not a code in `data/states.json`.
6. `bad_segment`: a segment breaks its rule in the table above. Check the segments in order, and report the first one that fails.

For `unknown_state` and `bad_segment`, the error names the segment. For the other codes, the segment is null.

## Suggestions

For `unknown_state` and `bad_segment`, build one corrected code:

- In the letter segments, state and area, change 0 to O and 1 to I.
- In the digit segments, LGA and unit, change O to 0, and change I and L to 1.
- Never change the district. NIPOST has not confirmed which characters it uses there.

Parse the corrected code with the same options. If it parses, the suggestion is its canonical form. If it does not parse, or if no character changed, the suggestion is null. A suggestion is a hint only. `parse` never returns a corrected code as a success.

## Legacy codes

`isLegacy` is false for input with more than `maxInputCodePoints` code points, and it does not normalise such input. Otherwise, it is true when the normalised input is exactly 6 ASCII digits.

## Hierarchy

- `truncate(code, to)` keeps the segments up to `to`. It fails when `to` is more precise than the code. Each language uses its standard error for a programmer mistake, for example `RangeError` in TypeScript.
- `parent(code)` returns the code with one segment fewer. A state code has no parent.
- `contains(prefix, code)` is true when the code has every segment of the prefix, in the same places.
- `redact(code)` replaces the unit with `**` in the canonical form. A code without a unit stays the same.

## State names

`stateName(code)` returns the name in `data/states.json`, and it ignores letter case. It does not remove spaces or other characters. An unknown code gives null. The codes follow ISO 3166-2:NG. All 11 state codes in NIPOST's published examples match it. A keyed autocomplete call must confirm the full list.

## GPS precision

`precisionForAccuracy(metres)` returns the most precise segment that a GPS fix of that accuracy supports, from `data/precision.json`. An unknown, negative, infinite or NaN accuracy gives `lga`. A fix with an accuracy equal to a limit gets the precision of that limit.

## Versions

`VERSION` holds the spec version. Each SDK exposes it as `SPEC_VERSION`. Each vector file carries a format version, which is 1.
