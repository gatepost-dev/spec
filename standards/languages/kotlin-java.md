# Kotlin and Java standards

Version 1.0, 1 Oct 2026.

This file and `standards/CODING_STANDARDS.md` together are the standard for Kotlin code that Kotlin and Java callers use. They apply to the `kotlin` repo. The repo publishes two artifacts: `postcode-core` and `postcode-client`. Later Android work follows them too, such as the Jetpack Compose field.

## Versions

- The newest stable Kotlin. The build emits JVM bytecode 11.
- Java callers need Java 11 or later. Eclipse Temurin 11 has support until at least 31 Oct 2027.
- Android code supports minSdk 21. No module depends on Google Play services.
- Android 5.0, which is API 21, gets no security updates. An ADR records why the floor stays at API 21: agent-banking POS terminals run old Android versions.
- `postcode-core` depends on the Kotlin standard library only.
- `postcode-client` depends on OkHttp, `kotlinx-coroutines-core` and `kotlinx-serialization-json`. An ADR records the two kotlinx dependencies under DEP-3. A `suspend` call can be cancelled only through `suspendCancellableCoroutine`. The JVM has no standard JSON library.

## Tools

`./gradlew check` runs every tool below. CI runs `./gradlew check` on each pull request and each push to `main`.

| Tool | Job | Settings |
|---|---|---|
| Gradle Kotlin DSL with a version catalog | build | `gradle/libs.versions.toml` |
| Kotlin explicit API mode | public API discipline | `kotlin { explicitApi() }` |
| ktlint | format | `max_line_length = 100` in `.editorconfig` |
| detekt | lint | the settings below |
| binary-compatibility-validator | API dump | `apiCheck` runs in `check`. The `.api` files are in the repo. |
| JUnit 5 | unit, vector and contract tests | |
| kotest-property | property tests | `parse`, `normalize` and the hierarchy functions |
| Kover | coverage | floors from T-7 |
| PIT | mutation tests | `postcode-core`, weekly scheduled job |
| Dokka | API docs | every public symbol |
| Android Lint | Android checks | Android modules only, warnings as errors |
| changie | change files and changelog | one change file per user-visible change |
| `spec/scripts/check-tells` | agent-tell checks | line length, emojis, other non-ASCII in source, the file names `utils`, `helpers`, `common` and `misc`, the `TODO(#123)` form and debug output |
| REUSE | licence headers | `reuse lint` |
| gitleaks | secret scan | each pull request and each push to `main` |

### detekt settings

| Rule | Setting | Enforces |
|---|---|---|
| `style>MaxLineLength` | `maxLineLength: 100` | TELL-1 |
| `complexity>NestedBlockDepth` | `threshold: 4`, which allows 3 levels | TELL-2 |
| `complexity>CyclomaticComplexMethod` | the limit of 10 from TELL-2 | TELL-2 |
| `complexity>LongParameterList` | `functionThreshold: 5`, `constructorThreshold: 5`, `ignoreDefaultParameters: true` | TELL-3 |
| `style>ForbiddenMethodCall` | the debug calls listed under Agent-tell checks | TELL-13 |
| `potential-bugs>UnsafeCallOnNullableType` | active | KT-9 |

### Agent-tell checks

| Rule | Check in Kotlin |
|---|---|
| TELL-1 | ktlint `max_line_length = 100`, detekt `MaxLineLength`, and `check-tells` |
| TELL-2 | detekt `NestedBlockDepth` and `CyclomaticComplexMethod` |
| TELL-3 | detekt `LongParameterList`. Parameters with default values do not count, because Kotlin callers name them. |
| TELL-13 | detekt `ForbiddenMethodCall` and `check-tells`. They ban `println`, `print`, `System.out`, `System.err`, `printStackTrace` and the Android `Log` methods. |
| TELL-14 | `check-tells` |

## Rules

- **KT-1 MUST.** Explicit API mode is on. Each public declaration states its visibility and its return type. **(tool)**
- **KT-2 MUST.** Factory functions live in the companion object of their type, with `@JvmStatic`, for example `Postcode.parse`. Functions with default arguments carry `@JvmOverloads`. Blocking methods carry `@Throws(PostcodeException::class)`.
- **KT-3 MUST.** The public API uses no Kotlin-only types. Do not expose `kotlin.Result`, value classes or `kotlin.time.Duration`. Java callers can call each operation.
- **KT-4 MUST.** Each client operation has three forms. Kotlin callers use `suspend fun lookup()`. Java callers use `lookupBlocking()` or `lookupAsync(..., callback)`.
- **KT-5 MUST.** `lookupAsync` returns a `Cancellable` handle. After a call to `cancel()`, the callback never runs.
- **KT-6 MUST.** The client does not use `CompletableFuture`, because it needs Android API 24.
- **KT-7 MUST.** Callbacks run on a background thread. The docs tell Android callers to move to the main thread.
- **KT-8 MUST.** The client rethrows each `CancellationException`. It never wraps one in `PostcodeException`.
- **KT-9 MUST.** Do not use `!!` outside tests. **(tool)**
- **KT-10 MUST.** Validated value types have a private constructor. A data class that is a value type carries `@ConsistentCopyVisibility`, so its `copy` is private too.
- **KT-11 MUST.** Error codes use `enum class ErrorCode(val wireValue: String)`.
- **KT-12 MUST.** Durations are `Long` milliseconds with the suffix `Millis`, for example `timeoutMillis`. `java.time` needs Android API 26 or desugaring.
- **KT-13 MUST.** The caller can pass an `OkHttpClient`. The client never shuts down an `OkHttpClient` that it did not create.
- **KT-14 MUST.** Each public symbol has a KDoc comment with an example. Dokka renders it.
- **KT-15 MUST.** Each `@Suppress` annotation names the rule and has a comment that gives the reason.
- **KT-16 MUST.** Code writes each non-ASCII or invisible character as an escape sequence, for example `"\u00A0"` and `"\u200B"`. **(tool)**
- **KT-17 MUST.** Tests replace the clock through an internal seam until the spec defines a clock option for API-10.
- **KT-18 MUST.** The client decodes JSON with `kotlinx-serialization-json`, configured with `ignoreUnknownKeys = true` and `coerceInputValues = true`. An unknown enum value then takes the default value of its property, which is the fallback that the spec defines. This follows API-14.
- **KT-19 MUST.** A kotlinx.coroutines `Semaphore` with 4 permits limits each client to 4 requests at a time, as API-8 requires. The blocking and callback forms go through the same semaphore.

## Names

| Element | Style | Example |
|---|---|---|
| class, interface, enum | PascalCase | `PostcodeClient` |
| function, property, parameter | camelCase | `precisionForAccuracy` |
| enum entry | UPPER_SNAKE_CASE | `ErrorCode.RATE_LIMITED` |
| constant | UPPER_SNAKE_CASE | `Postcode.SPEC_VERSION` |
| error code value | snake_case string | `"rate_limited"` |
| package | lower case, no hyphens | `dev.gatepost.postcode` |
| file | PascalCase, named after its main type | `PostcodeClient.kt` |

## Package layout

```
postcode-core/
  src/main/kotlin/dev/gatepost/postcode/
  src/test/kotlin/dev/gatepost/postcode/     unit, vector and property tests
  api/postcode-core.api                      API dump
postcode-client/
  src/main/kotlin/dev/gatepost/postcode/client/
  src/test/kotlin/dev/gatepost/postcode/client/   unit and contract tests
  api/postcode-client.api
gradle/libs.versions.toml
build.gradle.kts
settings.gradle.kts
.changes/                                    changie fragments
README.md                                    from templates/README.md
CHANGELOG.md                                 generated by changie
```

## Publishing

- CI publishes both artifacts to Maven Central through the Central Portal. CI signs each artifact.
- The Maven group is `dev.gatepost` if the team owns `gatepost.dev`. Otherwise the group is `io.github.gatepost-dev`, and the package root is `io.github.gatepostdev.postcode`.
- A signed tag `vX.Y.Z` starts each release.
