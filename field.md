# Field

This file defines the postcode field of every Gatepost UI: the web field now, and the field of each later UI framework. A field reads the text with the core, and it sends each request through the client. `messages/field_en.arb` holds the text that the field shows. If this file and a field's tests disagree, this file wins.

## Interface

A field exposes the symbols in this table and the types that they need. A language file gives the idiomatic form of each name, as for the core.

| Symbol | Kind | Meaning |
|---|---|---|
| `name`, `value`, `required`, `disabled` | setting | the standard settings of a form control |
| `label` | setting | the visible label. The default is the message `label` |
| `apiKey` | setting | a publishable key. Without a key, the field sends no request |
| `baseUrl` | setting | the gateway's address, as in the client options |
| `confirm` | setting | `none`, `level1` or `level2`. The default is `level1` |
| `gps` | setting | true shows the location button. The default is false |
| `legacy` | setting | `accept` or `reject`. The default is `accept` |
| `messages` | setting | text that replaces messages of the catalogue, by key |
| `change` | event | the form value changed |
| `confirm` | event | the gateway knows the postcode |
| `error` | event | a request failed, the location failed, or the key is a secret key |
| `SPEC_VERSION` | constant | the spec version, as text |

### Events

| Event | Detail |
|---|---|
| `change` | `value`: the form value. `postcode`: the postcode when the text parses as a whole postcode, or null. `source`: `typed`, `pasted`, `suggestion` or `gps`. `accuracyM`: the accuracy of the location in metres when `source` is `gps`, or null |
| `confirm` | `lookup`: the lookup result of the client |
| `error` | `code`: an error code of the client, or `secret_key`, `gps_denied` or `gps_unavailable` |

### On the web

The web field is the custom element `gatepost-postcode-field`. It is a form-associated element, so a plain HTML form submits its form value.

- Each setting is an attribute in kebab-case: `api-key`, `base-url`, `confirm`, `gps`, `legacy`, `label`, `name`, `value`, `required` and `disabled`. The setting `messages` is a property only, because it holds an object.
- Each event has the prefix `gatepost-`: `gatepost-change`, `gatepost-confirm` and `gatepost-error`. The event holds its detail in `detail`, and it bubbles, so a page can listen on the form.
- The module defines the element only when `customElements` exists, so a server can render a page that holds it.

## Form value and validity

- The form value is the canonical form when the text parses as a whole postcode.
- With `legacy` set to `accept`, the 6 digits of a legacy postcode are a form value too.
- For any other text, the form value is the text without white space at the start and the end. A server can then show the user what they typed.
- The field is invalid when `required` is set and the text is empty. It is also invalid when the text is not empty, and its form value is neither of the first two kinds above. So a legacy postcode is invalid when `legacy` is `reject`.
- A lookup never changes the validity. A postcode that the gateway does not know, and a failed request, leave the field valid. The gateway's data is new, so a wrong answer must not stop a user. The app's server checks the postcode again.

## Text

- The field reads its text with `parse`. Partial postcodes do not pass.
- The field shows a parse error after the user leaves the input, after a form submit, or when the normalised text has 11 characters or more. A user who is still typing a short text sees no error.
- When the user leaves the input, a text that parses shows in the display form.
- For an error with a suggestion, the field shows the suggestion and a button that uses it. The field never applies a suggestion by itself.
- Enter submits the form, as in a native text input.

## Lookups

- The field sends a request only when it has a key. Without a key, it checks the format offline, and a text that parses ends in the state `valid`.
- With a key, and `confirm` set to `level1` or `level2`, the field looks up each text that parses as a whole postcode, at that level. It sends no lookup for a legacy postcode.
- A new text cancels the lookup of the previous text.
- The field refuses a secret key, which starts with `nipost_test_` or `nipost_live_`, and sends no request. It logs one console error for the developer when it reads the key. In place of each lookup, it shows the state `error` and raises the event `error` with the code `secret_key`, so an app that listens later still hears of it.
- At level 2, the confirmation names the locality, the LGA and the state from the administrative address. Otherwise, it names the state with `stateName`. It never shows `recentHouseAddress`, because a user can type any postcode, and that address can belong to someone else. The event `confirm` gives the app the whole lookup result.

## Location

- With `gps` set and a key, the field shows a button that uses the device's location. The field asks for the location only when the user presses the button.
- The field sends the coordinate to the gateway with `reverse`. The radius is the accuracy in whole metres, rounded up, at least 25 and at most 250.
- `precisionForAccuracy` gives the most precise segment that the location supports. The field fills in the unit's postcode, truncated to that precision. When the result has no unit, the field uses the area, then the district, if that text parses as a partial postcode.
- A partial postcode stays as text for the user to complete. The field then shows the state `GPS coarse`.
- The user can always type. Typing cancels a location request in progress.

## States

| State | When | Messages |
|---|---|---|
| idle | the text is empty, and the field shows no error | none |
| typing | the text does not parse, and the field shows no error yet | none |
| invalid format | the field shows a parse error | the message of the parse error, and `suggestion` |
| legacy code | the text is a legacy postcode | `legacy_accepted` or `legacy_rejected` |
| checking | a lookup is in progress | `checking` |
| valid | the text parses, and no lookup runs | `valid` |
| not found | the gateway does not know the postcode | `not_found` |
| confirmed | the gateway knows the postcode | `confirmed` or `confirmed_place` |
| error | a lookup failed, or the key is a secret key | `check_failed` or `secret_key` |
| GPS locating | the field waits for the location or for `reverse` | `locating` |
| GPS coarse | the location supports only a partial postcode | `gps_coarse` |
| GPS denied | the field has no location, or no postcode at the location | `gps_denied`, `gps_unavailable` or `gps_not_found` |

## Messages

`messages/field_en.arb` holds each message in British English, in the ARB format that Flutter also reads. Each message has a description. A name in braces, such as `{count}`, is a placeholder, and the field gives its value. A translation is a file `messages/field_<locale>.arb` with the same keys and placeholders. A field shows the catalogue text for a state or an error code, never the message of an error object (UI-2).

### Message keys

| Key | Shown |
|---|---|
| `label` | as the label, when the page gives no `label` |
| `hint` | under the label, at all times |
| `empty` | for the parse error `empty`, when `required` is set |
| `bad_character` | for the parse error `bad_character` |
| `bad_length` | for the parse error `bad_length`, with the count of normalised characters |
| `unknown_state` | for the parse error `unknown_state` |
| `bad_lga` | for the parse error `bad_segment` in the LGA |
| `bad_area` | for the parse error `bad_segment` in the area |
| `bad_unit` | for the parse error `bad_segment` in the unit |
| `suggestion` | after a parse error that has a suggestion, with the suggestion in the display form |
| `use_suggestion` | as the text of the button that uses the suggestion |
| `legacy_accepted` | for a legacy postcode, when `legacy` is `accept` |
| `legacy_rejected` | for a legacy postcode, when `legacy` is `reject` |
| `valid` | in the state `valid`, with the state name |
| `checking` | in the state `checking` |
| `not_found` | in the state `not found` |
| `confirmed` | in the state `confirmed`, with the state name |
| `confirmed_place` | in the state `confirmed`, when the lookup gives the locality, the LGA and the state names |
| `check_failed` | in the state `error`, after a failed lookup |
| `secret_key` | in the state `error`, for a secret key |
| `use_location` | as the text of the location button |
| `locating` | in the state `GPS locating` |
| `gps_coarse` | in the state `GPS coarse`, with the accuracy in whole metres |
| `gps_not_found` | in the state `GPS denied`, when `reverse` found no postcode |
| `gps_denied` | in the state `GPS denied`, when the user refused the location |
| `gps_unavailable` | in the state `GPS denied`, when the device gave no location, or `reverse` failed |

The district segment accepts any letters and digits, so no parse error names it.

## Accessibility

- The field meets WCAG 2.2 AA (UI-1).
- The label names the input. The hint and the current message describe it.
- A screen reader hears each new message once, through a polite live region.
- The field marks the input invalid only while it shows an error.
- Each control works with the keyboard alone. The tab order is the input, the suggestion button, then the location button.
- The field follows the user's reduced-motion setting and text size (UI-4).

## Privacy

- The field stores nothing, sets no cookie and sends no telemetry (SEC-2).
- The field sends a request only for a lookup of a whole postcode, and for `reverse` after the user presses the location button.
