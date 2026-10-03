# Field

This file defines the postcode field of every Gatepost UI: the web field now, and the field of each later UI framework. A field reads the text with the core, and it sends each request through the client. `messages/field_en.arb` holds the text that the field shows. If this file and a field's tests disagree, this file wins.

## Interface

A field exposes the symbols in this table and the types that they need. A language file gives the idiomatic form of each name, as for the core.

| Symbol | Kind | Meaning |
|---|---|---|
| `name`, `value`, `required`, `disabled` | setting | the standard settings of a form control. `value` gives the first text |
| `label` | setting | the visible label. The default is the message `label` |
| `apiKey` | setting | a publishable key. An empty key counts as no key. Without a key, the field sends no request |
| `baseUrl` | setting | the gateway's address, as in the client options |
| `confirm` | setting | `none`, `level1` or `level2`. The default is `level1` |
| `gps` | setting | true shows the location button. The default is false |
| `legacy` | setting | `accept` or `reject`. The default is `accept` |
| `messages` | setting | text that replaces messages of the catalogue, by key |
| `change` | event | the form value changed through the user |
| `confirm` | event | the gateway knows the postcode |
| `error` | event | a failure that the table in Failures gives an event code |
| `SPEC_VERSION` | constant | the spec version, as text |

### Events

| Event | Detail |
|---|---|
| `change` | `value`: the form value. `postcode`: the postcode when the text parses as a whole postcode, or null. `source`: `typed`, `pasted`, `suggestion` or `gps`. `accuracyM`: the accuracy of the location in metres when `source` is `gps`, or null |
| `confirm` | `lookup`: the lookup result of the client |
| `error` | `code`: an error code of the client, or `secret_key`, `gps_denied` or `gps_unavailable`. The table in Failures gives the code of each failure |

### On the web

The web field is the custom element `gatepost-postcode-field`. It is a form-associated element, so a plain HTML form submits its form value.

- Each setting is an attribute in kebab-case: `api-key`, `base-url`, `confirm`, `gps`, `legacy`, `label`, `name`, `value`, `required` and `disabled`. The setting `messages` is a property only, because it holds an object.
- The attribute `value` gives the first text. The property `value` sets the current text, and reading it gives the form value.
- An invalid field gives its message in `validationMessage`, as a native input does.
- Each event has the prefix `gatepost-`: `gatepost-change`, `gatepost-confirm` and `gatepost-error`. The event holds its detail in `detail`, and it bubbles, so a page can listen on the form.
- The module defines the element only when `customElements` exists, so a server can render a page that holds it.

## Form value and validity

- The form value is the canonical form when the text parses as a whole postcode.
- With `legacy` set to `accept`, the 6 digits of a legacy postcode are a form value too.
- For any other text, the form value is the text without white space at the start and the end. A server can then show the user what they typed.
- The field is invalid when `required` is set and the text is empty. It is also invalid when the text is not empty, and its form value is neither of the first two kinds above. So a legacy postcode is invalid when `legacy` is `reject`.
- An invalid field reports the text of its message as its validation message: `empty`, the message of the parse error, or `legacy_rejected`. It reports this text even before the field shows the error.
- A lookup never changes the validity. A postcode that the gateway does not know, and a failed request, leave the field valid. The gateway's data is new, so a wrong answer must not stop a user. The app's server checks the postcode again.
- The setting `value` gives the first text. A form reset restores this text, and the field again waits before it shows an error.
- The field raises `change` only when the user changes the form value: by typing, by pasting, with the suggestion button or with the location button. Text that the app sets raises no `change`.

## Text

- The field reads its text with `parse`. Partial postcodes do not pass.
- The count of a text is the number of code points in its normalised form. Spaces and hyphens do not count.
- Above `maxInputCodePoints` code points (64 in `data/format.json`), the field never calls `normalize`, because NFKC can take seconds on a long text. The count is then the number of code points of the raw text.
- An empty text is never a parse error. It gives the state `idle`, except in a required field that shows errors.
- The field shows errors after the user first leaves the input, or after a validity check fails, such as on a form submit. It stops after a form reset.
- A parse error shows when the field shows errors, or when the count of the text is 11 or more. So a text above the input limit shows its error at once.
- A user who is still typing a short text sees no error.
- A legacy postcode shows its message at once. A new postcode starts with letters, so 6 digits are never the start of one.
- When the user leaves the input, a text that parses shows in the display form. The form value and the state stay the same, so the field raises no `change` and sends no new lookup.
- For an error with a suggestion, the field shows the suggestion and a button that uses it. The field never applies a suggestion by itself.
- The message of the parse error and the message `suggestion` are two separate texts, never one joined string (UI-2).
- The suggestion button puts the suggestion in the input, in the display form. It raises `change` with the source `suggestion`, and it moves the focus to the input.
- Enter submits the form, as in a native text input.

## Lookups

- The field sends a request only when it has a key. Without a key, it checks the format offline, and a text that parses ends in the state `valid`.
- With a key, and `confirm` set to `level1` or `level2`, the field asks the gateway about each whole postcode, with a lookup at that level. It sends no lookup for a legacy postcode.
- The field remembers a lookup that ended with an answer from the gateway: its canonical postcode, its level and its key. The answer gives the state `confirmed` or `not found`.
- When the text or a setting changes, and the three values still match the remembered lookup, the field keeps that lookup and its state. It sends no new request.
- A lookup in progress also stays while the three values still match it.
- When one of the three values changes, the field cancels the lookup in progress. It forgets the remembered lookup and its state. It then starts a new lookup if the text parses as a whole postcode.
- The field never remembers a lookup that failed or was cancelled. So the next change of the text or of a setting tries the same postcode again.
- The state `error` lasts until the text or a setting changes.
- A change of `baseUrl` alone starts no lookup and cancels none. The next request uses the new address.
- A press of the location button cancels the lookup in progress, and the field forgets the remembered lookup.
- The field ignores the answer to a cancelled request. It changes nothing on screen, and it raises no event.
- The field refuses a secret key, which starts with `nipost_test_` or `nipost_live_`. It sends no request with that key, and it shows no location button.
- The field logs one console error for the developer each time it reads a secret key. It reads the key when it starts, and when the key or `baseUrl` changes. The error never holds the key (ERR-3).
- In place of each lookup that it would start, the field shows the state `error` and raises the event `error` with the code `secret_key`. So an app that adds its listener late still hears of it. With `confirm` set to `none`, the field raises no event.
- At level 2, the confirmation names the locality, the LGA and the state from the administrative address, when the lookup gives all three. Otherwise, it names the state of the postcode with `stateName`.
- The event `confirm` gives the app the whole lookup result. Privacy says what the field itself never shows.

## Location

- With `gps` set and a key that the field accepts, the field shows a button that uses the device's location. The field asks for the location only when the user presses the button.
- The field asks the platform for one fix, with high accuracy, no saved fix, and a time limit of 15 seconds.
- A platform with no location API gives the failure `gps_unavailable` at once.
- The field sends the coordinate to the gateway with `reverse`. The radius is the accuracy in whole metres, rounded up, at least 25 and at most 250.
- From the result, the field takes the unit's postcode. When the result has no unit, it takes the area, and then the district, if that text parses as a partial postcode. It never takes the state alone.
- `precisionForAccuracy` gives the most precise segment that the accuracy supports. The field truncates the postcode to that precision, unless the postcode already stops before it.
- So a fix worse than 50 m keeps the state and the LGA only, from a unit, an area or a district.
- When the result holds no postcode, the field shows the message `gps_not_found`.
- Otherwise, the field replaces the text with the postcode in the display form. It raises `change` when the form value changes, as for typing. The source is `gps`, and `accuracyM` is the accuracy of the fix.
- A whole postcode then follows the rules for a typed one. It gets a lookup, or the state `valid` when `confirm` is `none`.
- A partial postcode ends in a space, so the user can type the next segment at once. The input takes the focus, and the field shows the state `GPS coarse`.
- A partial postcode leaves the field invalid until the text is a whole postcode.
- The user can always type. A change of the text cancels a location request in progress.
- A new press of the button and the removal of the field also cancel it. A change of a setting never cancels it.
- While a location request is in progress, the field starts no lookup. A change of a setting then changes only the validity.
- The states `GPS coarse` and `GPS denied` last until the text changes.

## Removal from the page

- When the field is removed from the page, it cancels any request in progress. It forgets the remembered lookup and the state of each request. It then shows the state that its text gives.
- When the field is added again, it starts from that state, as at the first start. So a whole postcode gets a new lookup.

## Failures

Each failure gives one state and one message. The last column gives the code of the event `error`, or "no event". A parse error raises no event either. The field shows it in the state `invalid format`.

| Failure | State | Message | Event code |
|---|---|---|---|
| the gateway does not know the postcode | not found | `not_found` | no event |
| a lookup fails with an error of the client | error | `check_failed` | the code of the client's error, such as `network_error` or `rate_limited` |
| a lookup is due, and the key is a secret key | error | `secret_key` | `secret_key` |
| the user or the platform refuses the location | GPS denied | `gps_denied` | `gps_denied` |
| the platform has no location API | GPS denied | `gps_unavailable` | `gps_unavailable` |
| the device reports that it has no location | GPS denied | `gps_unavailable` | `gps_unavailable` |
| the device gives no location within the time limit | GPS denied | `gps_unavailable` | `gps_unavailable` |
| `reverse` fails with an error of the client | GPS denied | `gps_unavailable` | the code of the client's error |
| `reverse` gives no postcode that parses | GPS denied | `gps_not_found` | no event |

## States

The field shows the first state in this table whose condition holds. The first seven states come from a request. Lookups, Location and Removal from the page say when each of them ends.

| State | When | Messages |
|---|---|---|
| GPS locating | a location request is in progress | `locating` |
| checking | a lookup is in progress | `checking` |
| confirmed | the remembered lookup found the postcode | `confirmed` or `confirmed_place` |
| not found | the remembered lookup says that the gateway does not know the postcode | `not_found` |
| error | the last lookup failed, or it was due and the key is a secret key | `check_failed` or `secret_key` |
| GPS coarse | the last location request gave a partial postcode, and the text has not changed since | `gps_coarse` |
| GPS denied | the last location request failed, and the text has not changed since | `gps_denied`, `gps_unavailable` or `gps_not_found` |
| legacy code | the text is a legacy postcode | `legacy_accepted` or `legacy_rejected` |
| valid | the text parses as a whole postcode | `valid` |
| invalid format | the text is not empty and does not parse, and its parse error shows (see Text). Or the text is empty, `required` is set and the field shows errors | the message of the parse error and `suggestion`, or `empty` |
| typing | the text is not empty and does not parse, and its parse error does not show yet | none |
| idle | the text is empty, and the row `invalid format` does not apply | none |

## Messages

`messages/field_en.arb` holds each message in British English, in the ARB format that Flutter also reads. Each message has a description. A name in braces, such as `{count}`, is a placeholder, and the field gives its value. A translation is a file `messages/field_<locale>.arb` with the same keys and placeholders. A field shows the catalogue text for a state or an error code, never the message of an error object (UI-2).

### Message keys

| Key | Placeholders | Shown |
|---|---|---|
| `label` | none | as the label, when the page gives no `label` |
| `hint` | none | under the label, at all times |
| `empty` | none | for the parse error `empty`, when `required` is set |
| `bad_character` | none | for the parse error `bad_character` |
| `bad_length` | `{count}` | for the parse error `bad_length`. `{count}` is the count of the text |
| `unknown_state` | none | for the parse error `unknown_state` |
| `bad_lga` | none | for the parse error `bad_segment` in the LGA |
| `bad_area` | none | for the parse error `bad_segment` in the area |
| `bad_unit` | none | for the parse error `bad_segment` in the unit |
| `suggestion` | `{postcode}` | after a parse error that has a suggestion. `{postcode}` is the suggestion in the display form |
| `use_suggestion` | none | as the text of the button that uses the suggestion |
| `legacy_accepted` | none | for a legacy postcode, when `legacy` is `accept` |
| `legacy_rejected` | none | for a legacy postcode, when `legacy` is `reject` |
| `valid` | `{state}` | in the state `valid`. `{state}` is the name that `stateName` gives |
| `checking` | none | in the state `checking` |
| `not_found` | none | in the state `not found` |
| `confirmed` | `{state}` | in the state `confirmed`. `{state}` is the name that `stateName` gives |
| `confirmed_place` | `{locality}`, `{lga}`, `{state}` | in the state `confirmed`, when the lookup gives the locality, the LGA and the state names |
| `check_failed` | none | in the state `error`, after a failed lookup |
| `secret_key` | none | in the state `error`, for a secret key |
| `use_location` | none | as the text of the location button |
| `locating` | none | in the state `GPS locating` |
| `gps_coarse` | none | in the state `GPS coarse`. A precise fix with no unit also gives a partial postcode, so the text names no cause and no count of segments |
| `gps_not_found` | none | in the state `GPS denied`, when `reverse` found no postcode |
| `gps_denied` | none | in the state `GPS denied`, when the user or the platform refused the location |
| `gps_unavailable` | none | in the state `GPS denied`, when the platform has no location API, the device gave no location, or `reverse` failed |

The district segment accepts any letters and digits, so no parse error names it.

## Accessibility

- The field meets WCAG 2.2 AA (UI-1).
- The label names the input. The hint and the current message describe it.
- A screen reader hears each new message once, through a polite live region.
- The field marks the input invalid only in the state `invalid format`, and in the state `legacy code` when `legacy` is `reject`.
- Each control works with the keyboard alone. The tab order is the input, the suggestion button, then the location button.
- The field follows the user's reduced-motion setting and text size (UI-4).

## Privacy

- The field stores nothing, sets no cookie and sends no telemetry (SEC-2).
- The field sends a request only for a lookup of a whole postcode, and for `reverse` after the user presses the location button.
- The field never shows a house address, neither the `recentHouseAddress` of a lookup nor the `address` of a reverse unit. A user can type any postcode, and the unit nearest to a location is often a neighbour's house. Either address can belong to someone else.
- The event `confirm` still gives the app the whole lookup result. The app decides what it shows.
