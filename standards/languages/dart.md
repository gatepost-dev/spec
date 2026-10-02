# Dart standards

Version 1.0, 1 Oct 2026.

This file and `standards/CODING_STANDARDS.md` together are the standard for Dart and Flutter code. They apply to the `dart` repo. The repo publishes two packages: `gatepost_postcode` is pure Dart and holds the core and the client. `gatepost_postcode_field` is the Flutter widget.

## Versions

- Dart 3.7 or later. `pubspec.yaml` sets `sdk: ^3.7.0`, because the formatter reads `page_width` only from language version 3.7.
- The widget package needs a Flutter release that ships Dart 3.7 or later.
- Dart and Flutter support only their newest stable release. No floor has a published end-of-life date.
- package:http is the one runtime dependency of `gatepost_postcode`. The core code does not import it.

## Tools

`make check` runs every tool below. CI runs `make check` on each pull request and each push to `main`.

| Tool | Job | Settings |
|---|---|---|
| `dart format --set-exit-if-changed` | format | `page_width: 100` in `analysis_options.yaml` |
| `dart analyze --fatal-infos` | lint | very_good_analysis and the settings below |
| `flutter analyze --fatal-infos` | lint for the widget package | the same settings |
| `dart test` with the coverage package | unit, vector and contract tests | coverage floors from T-7 |
| `flutter test --coverage` | widget tests | semantics, text scaling and reduced motion |
| dart_apitool | API check against the last release | `diff`, with `--old` set to the last release and `--new` set to the working copy |
| pana | pub.dev score | 160 of 160 points |
| changie | change files and changelog | one change file per user-visible change |
| `spec/scripts/check-tells` | agent-tell checks | line length, emojis, other non-ASCII in source, the file names `utils`, `helpers`, `common` and `misc`, the `TODO(#123)` form and debug output |
| REUSE | licence headers | `reuse lint` |
| gitleaks | secret scan | each pull request and each push to `main` |

### `analysis_options.yaml`

```yaml
include: package:very_good_analysis/analysis_options.yaml

formatter:
  page_width: 100

linter:
  rules:
    lines_longer_than_80_chars: false
    document_ignores: true
```

very_good_analysis turns on `lines_longer_than_80_chars`. This file turns it off, because TELL-1 sets the limit at 100.

### Agent-tell checks

| Rule | Check in Dart |
|---|---|
| TELL-1 | the formatter's `page_width: 100`, and `check-tells` for lines that the formatter cannot split, such as long strings |
| TELL-2 | review. The Dart analyzer has no complexity lint and no nesting lint. |
| TELL-3 | review. Named parameters do not count. The `avoid_positional_boolean_parameters` lint is on. |
| TELL-13 | the `avoid_print` lint, and `check-tells`. They ban `print` and `debugPrint`. |
| TELL-14 | `check-tells` |

## Rules

T-8 and T-9 do not apply to Dart. The shared vectors cover the parser.

- **DART-1 MUST.** Results are sealed classes. `ParseResult` has one subclass for success and one for failure. Callers use an exhaustive `switch`.
- **DART-2 MUST.** Value types are `final class` types with private constructors and `final` fields.
- **DART-3 MUST.** `ErrorCode` is an enhanced enum with a `wireValue` field, for example `ErrorCode.rateLimited` has the value `'rate_limited'`.
- **DART-4 MUST.** The caller can pass an `http.Client`. The client closes only an `http.Client` that it created.
- **DART-5 MUST.** Each client call takes an optional `abortTrigger` future. The client sends an `AbortableRequest`. When the future completes, the call ends with the `RequestAbortedException` from package:http. `IOClient`, `BrowserClient` and `RetryClient` support this. If the caller's `http.Client` cannot abort, the timeout still ends the call.
- **DART-6 MUST.** Durations use `Duration`.
- **DART-7 MUST.** Each public member has a doc comment with an example. The analyzer checks that the comment exists. **(tool)**
- **DART-8 MUST.** Code lives in `lib/src/`. The file `lib/gatepost_postcode.dart` exports only the public API.
- **DART-9 MUST.** Each `// ignore:` comment has a comment that gives the reason. **(tool)**
- **DART-10 MUST.** Code writes each non-ASCII or invisible character as an escape sequence, for example `'\u00A0'` and `'\u200B'`. **(tool)**
- **DART-11 MUST.** The client parses JSON with `dart:convert` and hand-written `fromJson` functions. They read only the keys that they need. An unknown value of a known field maps to the fallback that the spec defines. This follows API-14.
- **DART-12 MUST.** An internal queue limits each client to 4 requests at a time, as API-8 requires. A fifth call waits until one of the first four ends.
- **DART-13 MUST.** Tests replace the clock through an internal seam until the spec defines a clock option for API-10.
- **DART-14 MUST.** Widgets use `const` constructors where possible. **(tool)**
- **DART-15 MUST.** Widgets read colours, radii and fonts from a `ThemeExtension`. They contain no fixed colours.
- **DART-16 MUST.** Each control has a semantics label. Widgets follow `MediaQuery.textScalerOf` and `MediaQuery.disableAnimationsOf`.

## Names

| Element | Style | Example |
|---|---|---|
| class, enum, typedef, extension | UpperCamelCase | `PostcodeClient` |
| function, method, variable, parameter | lowerCamelCase | `precisionForAccuracy` |
| constant | lowerCamelCase | `specVersion` |
| enum value | lowerCamelCase | `ErrorCode.rateLimited` |
| error code value | snake_case string | `'rate_limited'` |
| file and library | lowercase_with_underscores | `postcode_client.dart` |
| package | lowercase_with_underscores | `gatepost_postcode` |

## Package layout

```
packages/gatepost_postcode/
  lib/gatepost_postcode.dart       public exports only
  lib/src/                         one concept per file
  test/                            unit, vector and contract tests
  analysis_options.yaml
  pubspec.yaml
  README.md                        from templates/README.md
  CHANGELOG.md                     generated by changie
packages/gatepost_postcode_field/
  lib/gatepost_postcode_field.dart
  lib/src/
  test/                            widget tests
  example/                         a runnable example app
.changes/                          changie fragments
Makefile
```

## Publishing

- A GitHub Actions job publishes to pub.dev with automated publishing when a version tag reaches the repo.
- A verified publisher owns both packages. The publisher uses the team's domain.
- `dart pub publish --dry-run` runs on each pull request.
