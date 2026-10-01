# C# standards

Version 1.0, 1 Oct 2026.

This file and `standards/CODING_STANDARDS.md` together are the standard for C# code. They apply to the `dotnet` repo. The repo publishes one package, `Gatepost.Postcode`, with the core types and the client.

## Versions

- The package targets `netstandard2.0` and `net10.0`.
- CI tests `net10.0` on Linux. CI also tests .NET Framework 4.8 on a Windows runner.
- .NET 10 has support until 14 Nov 2028. .NET Framework 4.8 has support for as long as the Windows version that it runs on. `netstandard2.0` is a specification, not a runtime, so it has no end-of-life date.
- On `netstandard2.0`, the package depends on `System.Text.Json`. An ADR records this under DEP-3. On `net10.0`, the package has no dependencies.
- The C# language version is `latest`. On `netstandard2.0`, `init` accessors need an internal `IsExternalInit` polyfill.

## Tools

`make check` runs every tool below. CI runs `make check` on each push and each pull request.

| Tool | Job | Settings |
|---|---|---|
| `dotnet format --verify-no-changes` | format | `.editorconfig` |
| Roslyn analyzers | lint | `AnalysisLevel` `latest-recommended`, `TreatWarningsAsErrors`, `Nullable` `enable` |
| `GenerateDocumentationFile` | doc check | a missing XML doc comment fails the build |
| Microsoft.CodeAnalysis.PublicApiAnalyzers | API tracking | `PublicAPI.Shipped.txt` and `PublicAPI.Unshipped.txt` |
| Microsoft.CodeAnalysis.BannedApiAnalyzers | banned calls | `BannedSymbols.txt` |
| Microsoft.VisualStudio.Threading.Analyzers | async rules | the `Async` suffix and no `async void` |
| xUnit | unit, vector and contract tests | |
| coverlet | coverage | floors from T-7 |
| CsCheck | property tests | `Parse`, `Normalize` and the hierarchy methods |
| Stryker.NET | mutation tests | core types, weekly scheduled job |
| SourceLink, deterministic builds and symbol packages | debugging support | `ContinuousIntegrationBuild` in CI, `.snupkg` files |
| changie | change files and changelog | one change file per user-visible change |
| `spec/scripts/check-tells` | agent-tell checks | line length, emojis, other non-ASCII in source, the file names `utils`, `helpers`, `common` and `misc`, the `TODO(#123)` form and debug output |
| REUSE | licence headers | `reuse lint` |
| gitleaks | secret scan | every push |

### Agent-tell checks

| Rule | Check in C# |
|---|---|
| TELL-1 | `max_line_length = 100` in `.editorconfig`. `dotnet format` does not enforce it, so `check-tells` does. |
| TELL-2 | CA1502 at error severity, with `CA1502: 10` in `CodeMetricsConfig.txt`. Nesting depth: review. |
| TELL-3 | review. Parameters with default values do not count. Options classes carry the rest, for example `LookupOptions`. |
| TELL-13 | BannedApiAnalyzers and `check-tells`. They ban `Console.Write`, `Console.WriteLine`, `Debug.WriteLine` and `Trace.WriteLine`. |
| TELL-14 | `check-tells` |

## Rules

- **NET-1 MUST.** Nullable reference types are on. The build treats warnings as errors. **(tool)**
- **NET-2 MUST.** Each public type and member has an XML doc comment with `<summary>`, `<param>`, `<exception>` and `<example>`. The build checks that the comment exists. Reviewers check its content.
- **NET-3 MUST.** Async methods end in `Async`. They take a `CancellationToken` as the last parameter. They call `ConfigureAwait(false)`. **(tool)**
- **NET-4 MUST.** When the caller's token is cancelled, the method throws `OperationCanceledException`. When the client's own timeout ends the call, the method throws `PostcodeException` with `ErrorCode.Timeout`. The client checks the caller's token to tell the two apart.
- **NET-5 MUST.** The caller can pass an `HttpClient`. The client never disposes an `HttpClient` that it did not create.
- **NET-6 MUST.** Validated value types are sealed classes with get-only properties. Do not use records for them, because `with` can bypass validation.
- **NET-7 MUST.** Options classes, such as `LookupOptions`, use `init` accessors.
- **NET-8 MUST.** `ErrorCode` is an enum. One internal table maps each member to its wire value, for example `RateLimited` to `rate_limited`.
- **NET-9 MUST.** Do not add idiom aliases, such as `TryParse`, unless the spec adds them first. This follows API-1.
- **NET-10 MUST.** Durations use `TimeSpan`.
- **NET-11 MUST.** A change to the public API updates `PublicAPI.Unshipped.txt`. A release moves the entries to `PublicAPI.Shipped.txt`. **(tool)**
- **NET-12 MUST.** Each `#pragma warning disable` and each `SuppressMessage` attribute gives a justification.
- **NET-13 MUST.** Code writes each non-ASCII or invisible character as an escape sequence, for example `"\u00A0"` and `"\u200B"`. **(tool)**
- **NET-14 SHOULD.** Prefer sealed classes and static methods. Do not add an interface that has one implementation.
- **NET-15 MUST.** Tests replace the clock through an internal seam, with `InternalsVisibleTo`, until the spec defines a clock option for API-10.
- **NET-16 MUST.** The client decodes JSON with `System.Text.Json`, which ignores unknown members by default. Do not set `UnmappedMemberHandling.Disallow`. A custom converter maps an unknown enum string to the fallback that the spec defines. This follows API-14.
- **NET-17 MUST.** A `SemaphoreSlim` with 4 slots limits each client to 4 requests at a time, as API-8 requires. A waiting call still ends when its `CancellationToken` is cancelled.

## Names

| Element | Style | Example |
|---|---|---|
| type, method, property | PascalCase | `PostcodeClient`, `LookupAsync` |
| parameter, local variable | camelCase | `allowPartial` |
| private field | underscore and camelCase | `_httpClient` |
| enum member | PascalCase | `ErrorCode.RateLimited` |
| constant | PascalCase | `Postcode.SpecVersion` |
| error code value | snake_case string | `"rate_limited"` |
| namespace | PascalCase | `Gatepost.Postcode` |
| file | one type per file, named after the type | `PostcodeClient.cs` |

## Package layout

```
src/Gatepost.Postcode/
  Gatepost.Postcode.csproj
  Postcode.cs
  ParseResult.cs
  PostcodeClient.cs
  PublicAPI.Shipped.txt
  PublicAPI.Unshipped.txt
  BannedSymbols.txt
  CodeMetricsConfig.txt
tests/Gatepost.Postcode.Tests/    unit, vector and contract tests
Directory.Build.props             shared build and analyzer settings
.editorconfig
.changes/                         changie fragments
Makefile
README.md                         from templates/README.md
CHANGELOG.md                      generated by changie
```

## Publishing

- CI packs the package with `dotnet pack` and publishes it to NuGet.org with trusted publishing.
- Each package carries SourceLink data and a symbol package.
- A signed tag `vX.Y.Z` starts each release.
