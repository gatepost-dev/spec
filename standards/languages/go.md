# Go standards

Version 1.0, 1 Oct 2026.

This file and `standards/CODING_STANDARDS.md` together are the standard for Go code. They apply to the `go` repo. The repo publishes one module, `github.com/gatepost-dev/postcode-go`, with the package `postcode`. The package holds the core functions and the client.

## Versions

- The two newest Go releases. CI tests both. The `go` line in `go.mod` names the older one.
- Go supports each release until two newer releases exist. So the older floor loses support when the next Go release ships, in February or August.
- The module has no dependencies outside the standard library.
- Tools are not dependencies. The Makefile pins each tool version and runs it with `go run`.

## Tools

`make check` runs every tool below. CI runs `make check` on each pull request and each push to `main`.

| Tool | Job | Settings |
|---|---|---|
| gofmt and goimports | format | `goimports -local github.com/gatepost-dev/postcode-go` |
| go vet | static checks | default analyzers |
| staticcheck | static analysis | default checks |
| golangci-lint | lint | the settings below |
| `go test` | unit, vector, contract and example tests | `-race -cover`, coverage floors from T-7 |
| `go test -fuzz` | fuzz tests | `FuzzParse` for 30 seconds on each pull request |
| govulncheck | vulnerability scan | each pull request and each push to `main` |
| gorelease | API check against the last tag | enforces GIT-7 and API-13 |
| changie | change files and changelog | one change file per user-visible change |
| `spec/scripts/check-tells` | agent-tell checks | line length, emojis, other non-ASCII in source, the file names `utils`, `helpers`, `common` and `misc`, the `TODO(#123)` form and debug output |
| REUSE | licence headers | `reuse lint` |
| gitleaks | secret scan | each pull request and each push to `main` |

### golangci-lint settings

```yaml
version: "2"
linters:
  enable:
    - errcheck
    - errorlint
    - exhaustive
    - forbidigo
    - gochecknoglobals
    - gochecknoinits
    - godot
    - gosec
    - lll
    - misspell
    - nolintlint
    - revive
  settings:
    lll:
      line-length: 100
    revive:
      rules:
        - name: argument-limit
          arguments: [4]
        - name: max-control-nesting
          arguments: [3]
        - name: cyclomatic
          arguments: [10]
        - name: exported
        - name: var-naming
    forbidigo:
      forbid:
        - pattern: ^fmt\.Print.*$
        - pattern: ^log\.(Print|Fatal|Panic).*$
        - pattern: ^print(ln)?$
    nolintlint:
      require-explanation: true
      require-specific: true
  exclusions:
    rules:
      - path: _test\.go
        linters:
          - forbidigo
```

Example functions print their output, so `forbidigo` skips test files.

### Agent-tell checks

| Rule | Check in Go |
|---|---|
| TELL-1 | golangci-lint `lll` with `line-length: 100`, and `check-tells`. gofmt has no line limit. |
| TELL-2 | revive `max-control-nesting` 3 and `cyclomatic` 10 |
| TELL-3 | revive `argument-limit` 4. Functional options carry the rest. |
| TELL-13 | `forbidigo` and `check-tells`. They ban `fmt.Print`, `fmt.Printf`, `fmt.Println`, `log.Print`, `log.Fatal`, `log.Panic`, `print` and `println` in library code. |
| TELL-14 | `check-tells` |

## Rules

T-8 does not apply to Go. Fuzz tests cover T-9.

- **GO-1 MUST.** `Parse` and `ParsePartial` return `(Postcode, error)`. A parse failure is a `*ParseError` with `Code`, `Segment` and `Suggestion`.
- **GO-2 MUST.** A client failure is a `*Error` with `Code`, `Status`, `APICode` and `RetryAfter`. Callers read it with `errors.As`.
- **GO-3 MUST.** Each I/O method takes `context.Context` as its first parameter.
- **GO-4 MUST.** If the caller's context ends, the method returns an error that wraps `ctx.Err()`. Then `errors.Is(err, context.Canceled)` works. The client's own 8-second timeout returns a `*Error` with `CodeTimeout`.
- **GO-5 MUST.** `NewClient` takes functional options: `NewClient(opts ...Option)`. Per-call options use the type `LookupOption`, for example `WithLevel(2)`.
- **GO-6 MUST.** The caller can pass an `*http.Client` with `WithHTTPClient`. The client never changes or closes it.
- **GO-7 MUST.** Library code does not panic. The package has no `init` functions and no package-level variables. **(tool)**
- **GO-8 MUST.** Value types keep their fields unexported. Accessor methods expose them, for example `p.Canonical()`.
- **GO-9 MUST.** Each exported symbol has a doc comment that starts with its name and ends with a period. **(tool)**
- **GO-10 MUST.** Each exported function and method has an `Example` function with an `// Output:` comment.
- **GO-11 MUST.** Initialisms keep one case, for example `LGA`, `API`, `URL` and `HTTP`. **(tool)**
- **GO-12 MUST.** Durations use `time.Duration`.
- **GO-13 MUST.** Error strings use lower case and end without punctuation. Wrapped errors use `%w`. **(tool)**
- **GO-14 MUST.** Each `//nolint` comment names the linter and gives a reason. **(tool)**
- **GO-15 MUST.** Names do not repeat the package name. Use `postcode.Client`, not `postcode.PostcodeClient`. **(tool)**
- **GO-16 MUST.** Code writes each non-ASCII or invisible character as an escape sequence, for example `"\u00a0"` and `"\u200b"`. **(tool)**
- **GO-17 MUST.** Contract tests carry the build tag `contract`. CI runs them against the mock server.
- **GO-18 MUST.** Tests replace the clock through an unexported field until the spec defines a clock option for API-10.
- **GO-19 MUST.** Each error string starts with `postcode:`, so that a caller can see which package made it.
- **GO-20 MUST.** The client decodes JSON with `encoding/json`, which ignores unknown fields. Do not call `DisallowUnknownFields`. An unknown value of a known field maps to the fallback that the spec defines. This follows API-14.
- **GO-21 MUST.** A buffered channel of size 4 limits each client to 4 requests at a time, as API-8 requires. A waiting call still ends when its context ends.

## Names

| Element | Style | Example |
|---|---|---|
| exported type, function, method | PascalCase | `ParsePartial`, `Client` |
| unexported identifier | camelCase | `normalize` |
| initialism | one case | `LGA`, `apiKey` |
| client error code | `Code` prefix | `CodeRateLimited` |
| parse error code | `ParseCode` prefix | `ParseCodeBadLength` |
| error code value | snake_case string | `"rate_limited"` |
| option | `With` prefix | `WithLevel`, `WithHTTPClient` |
| spec version | exported constant | `SpecVersion` |
| file | lower case, underscores | `parse.go`, `parse_test.go` |

## Package layout

```
go.mod                  module github.com/gatepost-dev/postcode-go
doc.go                  package documentation
postcode.go             the Postcode type
parse.go
client.go
errors.go
parse_test.go
example_test.go         Example functions
fuzz_test.go
vectors_test.go         runs spec/vectors/
contract_test.go        build tag contract, runs against the mock server
.changes/               changie fragments
Makefile
README.md               from templates/README.md
CHANGELOG.md            generated by changie
```

## Publishing

- CI runs `gorelease` and then creates a signed tag `vX.Y.Z`.
- The Go module proxy serves each tagged version.
- After 1.0, a breaking change needs a new major version path, for example `/v2`.
