# Swift standards

Version 1.0, 1 Oct 2026.

This file and `standards/CODING_STANDARDS.md` together are the standard for Swift code. They apply to the `swift` repo. The repo publishes one Swift package. Its product `GatepostPostcode` holds the core and the client. A later product, `GatepostPostcodeUI`, holds the SwiftUI field.

## Versions

- Swift 6 language mode with complete strict concurrency checking.
- iOS 15 and macOS 12 or later.
- Apple publishes no end-of-life dates. iOS 15 and macOS 12 no longer get regular updates. An ADR records why the floors stay: NIPOST's own iOS widget supports iOS 15.
- The package has no dependencies outside Apple's swiftlang projects. `swift-docc-plugin` is the one package dependency, and only the docs build uses it.

## Tools

`make check` runs every tool below. CI runs `make check` on each pull request and each push to `main`.

| Tool | Job | Settings |
|---|---|---|
| swift-format | format and lint | `lint --strict`, `lineLength` 100 in `.swift-format` |
| SwiftLint | lint | `--strict`, the settings below |
| `swift test` with Swift Testing | unit, vector and contract tests | `--enable-code-coverage` |
| llvm-cov | coverage | floors from T-7 |
| `swift package diagnose-api-breaking-changes` | API check against the last tag | runs on a macOS runner |
| DocC | API docs | `swift-docc-plugin` |
| changie | change files and changelog | one change file per user-visible change |
| `spec/scripts/check-tells` | agent-tell checks | line length, emojis, other non-ASCII in code, the file names `utils`, `helpers`, `common` and `misc`, the `TODO(#123)` form and debug output |
| REUSE | licence headers | `reuse lint` |
| gitleaks | secret scan | each pull request and each push to `main` |

### SwiftLint settings

```yaml
line_length: 100
cyclomatic_complexity: 10
function_parameter_count:
  warning: 4
  ignores_default_parameters: true
opt_in_rules:
  - force_unwrapping
  - implicitly_unwrapped_optional
```

`--strict` turns each warning into a failure.

### Agent-tell checks

| Rule | Check in Swift |
|---|---|
| TELL-1 | swift-format `lineLength` 100, and SwiftLint `line_length` 100 |
| TELL-2 | SwiftLint `cyclomatic_complexity` 10. Nesting of control flow: review. |
| TELL-3 | SwiftLint `function_parameter_count` 4 with `ignores_default_parameters: true`. Parameters with default values do not count. |
| TELL-13 | `check-tells`. It bans `print`, `debugPrint`, `dump` and `NSLog`. |
| TELL-14 | `check-tells` |

## Rules

T-8 and T-9 do not apply to Swift. Swift has no standard tool for mutation tests or property tests, and the shared vectors cover the parser.

- **SW-1 MUST.** Follow the Swift API Design Guidelines. Argument labels make each call read as a phrase, for example `client.lookup(code, level: 2)`.
- **SW-2 MUST.** Each public type conforms to `Sendable`. **(tool)**
- **SW-3 MUST.** Value types are structs with `let` properties. The static `Postcode.parse(_:allowPartial:)` creates them and returns `Result<Postcode, ParseError>`.
- **SW-4 MUST.** Client methods are `async throws`. They throw `PostcodeError`, or `CancellationError` when the task is cancelled. Do not use typed throws for them, because `throws(PostcodeError)` cannot pass on `CancellationError`.
- **SW-5 MUST.** Cancellation follows the task. A cancelled task ends its request, and the method throws `CancellationError`.
- **SW-6 MUST.** `URLSession` reaches the client through a small public protocol with one method. Tests pass a fake that conforms to it. The caller's session stays open after the client ends.
- **SW-7 MUST.** Durations use `TimeInterval` seconds. The Swift `Duration` type needs iOS 16.
- **SW-8 MUST.** Do not use force unwraps, `try!` or implicitly unwrapped optionals outside tests. **(tool)**
- **SW-9 MUST.** `ErrorCode` is a `String` enum. Each raw value is the shared wire value, for example `case rateLimited = "rate_limited"`.
- **SW-10 MUST.** Each public symbol has a DocC comment with a summary, `- Parameters:`, `- Throws:` and a code example.
- **SW-11 MUST.** Each `swiftlint:disable` comment names the rule and gives a reason. Prefer `swiftlint:disable:next` for one line.
- **SW-12 MUST.** Code writes each non-ASCII or invisible character as an escape sequence, for example `"\u{00A0}"` and `"\u{200B}"`. **(tool)**
- **SW-13 MUST.** Tests replace the clock through an internal seam until the spec defines a clock option for API-10.
- **SW-14 MUST.** The client decodes JSON with `Codable`, which ignores unknown keys. A custom `init(from:)` maps an unknown raw value of a known enum to the fallback that the spec defines. This follows API-14.
- **SW-15 MUST.** An internal actor limits each client to 4 requests at a time, as API-8 requires. A waiting call still ends when its task is cancelled.

## Names

| Element | Style | Example |
|---|---|---|
| type, protocol | UpperCamelCase | `PostcodeClient` |
| function, method, property, variable | lowerCamelCase | `precisionForAccuracy` |
| enum case | lowerCamelCase | `ErrorCode.rateLimited` |
| constant | lowerCamelCase static property | `Postcode.specVersion` |
| error code value | snake_case raw value | `"rate_limited"` |
| module and product | UpperCamelCase | `GatepostPostcode` |
| file | named after its main type | `PostcodeClient.swift` |

## Package layout

```
Package.swift
Sources/GatepostPostcode/
  Postcode.swift
  ParseError.swift
  PostcodeClient.swift
  GatepostPostcode.docc/        DocC catalogue
Tests/GatepostPostcodeTests/    unit, vector and contract tests
.swift-format
.swiftlint.yml
.changes/                       changie fragments
Makefile
README.md                       from templates/README.md
CHANGELOG.md                    generated by changie
```

## Publishing

- CI runs the API check and then creates a signed tag without a `v` prefix, for example `1.2.0`. Swift Package Manager reads the tags.
- Do not publish to CocoaPods. Swift Package Manager is the one channel.
