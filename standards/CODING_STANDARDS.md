# Gatepost coding standards

Version 1.0, 1 Oct 2026.

These standards apply to every Gatepost repo, in every language. Each repo also follows its language file in `standards/languages/`. Together, the two files are the standard for that repo.

## How to use this document

- Each rule has an ID, for example `API-3`. Reviews cite the ID.
- A **MUST** rule blocks a merge.
- A **SHOULD** rule can be skipped only with a written reason in the pull request.
- A rule marked **(tool)** is enforced by CI. Reviewers do not check it by hand.
- A language file can change a SHOULD rule for its language. It cannot change a MUST rule.
- `spec/grammar.md` (with its Interface section), `spec/data/`, `spec/vectors/` and the contract scenarios in `spec/contract/` rank above this document. `spec/grammar.md` wins over a vector. This document ranks above the language files. If two of them disagree, the higher one wins. Then fix the lower one.
- To change a rule, open a pull request on the `spec` repo. Increase the version at the top of this file.

## Principles

The rules come from these seven principles. If no rule covers a case, apply the principles.

1. **The spec is the contract.** The spec's interfaces and test vectors define correct behaviour in every language.
2. **One meaning, one name.** Use the terms in `CONTEXT.md`. Use each term the same way in code, tests, docs and errors.
3. **Deep modules.** Put a lot of behaviour behind a small interface. Delete layers that only pass calls through.
4. **Same behaviour, native feel.** Every SDK behaves the same. Every SDK reads like a well-made library in its own language.
5. **Boring is good.** Prefer the standard library, plain data and well-known tools.
6. **Private by default.** Send nothing the caller did not ask for. Keep nothing longer than necessary.
7. **Respect NIPOST's rules.** Follow NIPOST's Terms and Conditions of Use (https://postcode.gov.ng/terms) and its Acceptable Use Policy (https://postcode.gov.ng/acceptable-use).

## Public interface

- **API-1 MUST.** Every public symbol maps to a concept in the Interface section of `spec/grammar.md`. A language file lists the idiomatic additions that its language needs, such as options types, async variants and callback types. To add, rename or remove a concept, change the spec first. To add an idiomatic addition, change the language file first.
- **API-2 MUST.** Names and call shapes follow the cross-language map below.
- **API-3 MUST.** Parse, don't validate. A function that reads a postcode returns a typed result, not a boolean. A boolean helper can exist only as a thin wrapper over `parse`.
- **API-4 MUST.** Expected failures are values. `parse` returns its errors. Only I/O failures, API failures and programmer errors raise or throw.
- **API-5 MUST.** Error codes are stable `snake_case` strings, identical in every language. A new code is a minor change. A removed or renamed code is a breaking change.
- **API-6 MUST.** Public value types are immutable.
- **API-7 MUST.** Options use named parameters or an options object. Do not add a positional boolean parameter, unless the language lets the caller name the argument.
- **API-8 MUST.** Defaults are safe. The cache is off. A call retries at most 2 times. The timeout is 8 seconds. A client sends at most 4 requests at a time.
- **API-9 MUST.** There is no global state. Two clients with different options can run in the same process.
- **API-10 MUST.** The caller can inject the HTTP transport. Tests replace the clock with the language's standard test tools, such as fake timers, or with an internal seam. The clock is not a public option.
- **API-11 MUST.** Each async operation supports cancellation in the language's standard way. A cancelled call ends with the platform's own cancellation error, not with a Gatepost error.
- **API-12 SHOULD.** Keep the interface small. Before you add a public symbol, imagine that you delete it. If the complexity disappears, the symbol only passes calls through, so leave it out. If the complexity moves into each caller, the symbol earns its place.
- **API-13 MUST.** Releases follow semantic versioning. Mark a symbol deprecated for at least one minor release before you remove it.
- **API-14 MUST.** A client ignores unknown fields in a response. It maps an unknown value of a known field to a defined fallback. NIPOST's API is at version 0.1, so new fields will appear. A contract scenario tests this.

### Cross-language map

The behaviour is the same in every SDK. The shape follows each language.

| Language | Parse | Look up a postcode | Error type and code |
|---|---|---|---|
| TypeScript | `parse(input, { allowPartial: true })` returns `ParseResult` | `await client.lookup(code, { level: 2 })` | `PostcodeError`, `code === 'rate_limited'` |
| PHP | `Postcode::parse($input, allowPartial: true)` | `$client->lookup($code, level: 2)` | `PostcodeException`, `errorCode() === ErrorCode::RateLimited` |
| Python | `parse(text, allow_partial=True)` | `client.lookup(code, level=2)`, also on `AsyncPostcodeClient` | `PostcodeError`, `code is ErrorCode.RATE_LIMITED` |
| Go | `postcode.Parse(s)` and `postcode.ParsePartial(s)` return `(Postcode, error)` | `client.Lookup(ctx, code, postcode.WithLevel(2))` | `*postcode.Error`, `Code == postcode.CodeRateLimited` |
| Kotlin and Java | `Postcode.parse(input, allowPartial = true)` returns `ParseResult` | `client.lookup(code, level = 2)`, also `lookupAsync` for Java | `PostcodeException`, `code == ErrorCode.RATE_LIMITED` |
| C# | `Postcode.Parse(input, allowPartial: true)` returns `ParseResult` | `await client.LookupAsync(code, new LookupOptions { Level = 2 }, ct)` | `PostcodeException`, `Code == ErrorCode.RateLimited` |
| Dart | `Postcode.parse(input, allowPartial: true)` returns `ParseResult` | `await client.lookup(code, level: 2)` | `PostcodeException`, `code == ErrorCode.rateLimited` |
| Swift | `Postcode.parse(_:allowPartial:)` returns `Result<Postcode, ParseError>` | `try await client.lookup(code, level: 2)` | `PostcodeError`, `code == .rateLimited` |

In every language, the error code's wire value is the same string, for example `rate_limited`.

## Code structure

- **CS-1 MUST.** A module has one reason to change.
- **CS-2 MUST.** The core has no I/O, no clock and no randomness.
- **CS-3 SHOULD.** A function fits on one screen, about 40 lines. A file stays under about 300 lines.
- **CS-4 MUST.** Values from the spec, such as the GPS accuracy limits and the state codes, come from the spec's data files. Each language keeps them in one place. The vectors test each value, so a wrong copy fails CI.
- **CS-5 MUST.** There is no dead code and no commented-out code.
- **CS-6 MUST.** Each `TODO` or `FIXME` comment links an issue: `TODO(#123): ...` **(tool)**
- **CS-7 MUST.** Comments explain why. The code shows what.
- **CS-8 MUST.** Add no option, hook or abstraction that the spec does not need.
- **CS-9 SHOULD.** Prefer plain data and functions. Use a class when the language expects one, or when it holds configuration, like the client.

## Agent tells

Coding agents repeat some habits so often that readers spot them at once. Each rule below states the target. The "Tell" column names the habit that the rule prevents. These rules apply to people and to agents.

| ID | Rule | Tell | Check |
|---|---|---|---|
| TELL-1 MUST | Keep each line of code at 100 characters or fewer. Lines with a URL, generated files and data files are exempt. | Long one-line chains, conditions, signatures and strings | tool |
| TELL-2 MUST | Keep nesting at 3 levels or fewer, and cyclomatic complexity at 10 or lower. Return early. | Arrow-shaped code, an `if` inside an `if` inside a loop | tool where available |
| TELL-3 MUST | Give a function 4 positional parameters or fewer. Named, keyword-only and defaulted parameters do not count. Group the rest in an options object or named arguments. | Long lists of positional parameters | tool where available |
| TELL-4 MUST | Write a comment only to give a reason, a constraint or a reference. | Comments that repeat the next line, "Step 1" comments, banner comments | review |
| TELL-5 MUST | Make each doc comment add facts that the name and the types do not give. | "Gets the name. Returns the name." | review |
| TELL-6 MUST | Name each value after its meaning in the domain. | `data`, `result`, `obj`, `temp`, `value2`, and type words inside names, such as `postcodeString` | review |
| TELL-7 MUST | Put each helper in the module that owns its concept. | Files named `utils`, `helpers`, `common` or `misc`, and classes named `Manager`, `Helper` or `Processor` | tool for file names, review for classes |
| TELL-8 MUST | Search the repo before you write a helper. Reuse what exists. | The same helper written twice | review |
| TELL-9 MUST | Catch an error only where the code can handle it. Handle it fully there. | `catch` blocks that log and rethrow, catch-all blocks, empty `catch` blocks | tool where available |
| TELL-10 MUST | Trust the type system. Check only for states that can happen. | Null checks on values that cannot be null, checks for impossible states | tool where available |
| TELL-11 MUST | Let errors reach the caller. Use a default value only where the spec defines one. | Fallbacks such as `?? ''` or `catch { return [] }` that hide failures | review |
| TELL-12 MUST | Commit only finished code. | `TODO: implement`, "not implemented" errors, stub functions, placeholder data | tool for TODOs, review for the rest |
| TELL-13 MUST | Remove debug output before you commit. | `console.log`, `print`, `var_dump`, `dd()` | tool |
| TELL-14 MUST | Use ASCII in code, comments, logs and commit messages. Write other characters as escape sequences, such as `\u00A0`. [Message catalogues](#the-check-tells-script) and docs prose can use any script, without emojis. | Emojis, invisible spaces and curly quotes in code | tool |
| TELL-15 MUST | Change only the lines that the task needs. | Diffs that reformat, rename or move unrelated code | review |
| TELL-16 MUST | Mark a function `async` only when it awaits. Send every gateway call through the client, which limits how many run at once. | `async` without `await`, hundreds of gateway calls started at once | tool for `async`, review for calls |
| TELL-17 MUST | Give each ternary one condition. Use `if` or `switch` for more. | Nested ternaries | tool where available |
| TELL-18 MUST | Write a commit subject of 72 characters or fewer, in the imperative mood. Explain why in the body, in prose. | "Update files", bullet lists of every change, emoji commits | tool |
| TELL-19 MUST | Make each test assert a behaviour that a user would notice. | Tests without assertions, snapshot tests of logic, tests of mocks, names like "should work" | review |
| TELL-20 MUST | Add a dependency only when it removes real work. | A package for one small function | review |

### The `check-tells` script

`spec/scripts/check-tells` runs in the CI of every repo. It sorts each file into a kind, and the kind decides which rules apply:

- **Code files** are files in a programming language (`.ts`, `.js`, `.php`, `.py`, `.go`, `.kt`, `.java`, `.cs`, `.dart`, `.swift` and their variants), SQL and shell scripts, files with no extension that start with `#!`, and `.css`, `.scss`, `.html`, `.astro`, `.vue` and `.svelte` files.
- **Config files** are `.json`, `.json5`, `.jsonc`, `.yml`, `.yaml`, `.toml`, `.xml`, `.ini`, `.cfg`, `.properties`, `.gradle` and `.neon` files, and files such as `Makefile` and `Dockerfile`. A `.dist` file counts as the file that it copies, so `phpunit.xml.dist` is a config file.
- **Other files** can use any script: Markdown prose, message catalogues, lockfiles, data files, images and file types that no rule names. A **message catalogue** is a data file that holds translated strings. It is a file that is not code in a folder named `locales`, `i18n`, `l10n` or `messages`, a `.po`, `.arb`, `.xlf`, `.xliff`, `.strings` or `.stringsdict` file, or an Android `strings.xml`. Such a file is not a config file, even when its extension is a config extension, such as `src/locales/en.json`. A code file in such a folder is code, so translations live in data files.

It covers the tool rules that no language tool covers:

- **TELL-1.** It checks line length in code and config files, and it counts a tab as 4 columns. It skips lines with a URL, files that mark themselves as generated in their first 5 lines (`@generated`, `DO NOT EDIT`, `<auto-generated` or `GENERATED CODE`), and JSON files in a folder named `data` or `vectors`.
- **TELL-7.** It rejects files named `utils`, `helpers`, `common` or `misc`, with any extension.
- **TELL-12 and CS-6.** It rejects each `TODO` and `FIXME`, in any letter case, in code and config files, unless it has the form `TODO(#123)` or `FIXME(#123)`.
- **TELL-13.** It rejects the debug calls that the language file lists. It skips test files, comment lines and, in Python, doctest lines that start with `>>>` or `...`.
- **TELL-14.** It rejects emojis in every file, including Markdown, message catalogues and lockfiles. It rejects other non-ASCII characters in code files, config files and commit messages. It also rejects a code or config file that is not valid UTF-8, because it cannot read the file. It skips any other file that is not valid UTF-8, because the file can be an image. Message catalogues, docs prose and the sign-off lines of commit messages are exempt from the non-ASCII check, because translations and contributors' names can need any script.
- **TELL-18.** With `--commit-msg <file>`, it checks the length of a commit subject. Repos without commitlint use this mode.
- **GIT-1.** With `--squash-msg <file>`, it checks the message that a squash merge puts on `main`. That message is the pull request title, then ` (#N)`, then the pull request body. The subject must start with a type from the Conventional Commits list, then a colon and a space. TELL-14 and TELL-18 apply to the same message, and the ` (#N)` counts towards the 72 characters. GitHub keeps the body as written, so the tool reads each HTML comment of the body as text. It leaves out only the comment that Renovate adds at the end of its body, which has the form `<!--renovate-debug:...-->`. With `--no-scope`, the subject must also have no scope, as GIT-1 asks of a repo without packages.
- **GIT-2.** The squash message must have a line `Signed-off-by: Name <address>`, and the address must not be the placeholder of the pull request template. The message must not hold the placeholder paragraph or the line `Closes #` of that template. With `--signed-off <range>`, the tool checks that each commit in a git revision range has a `Signed-off-by` line. It skips merge commits, and it applies no other message rule to a commit, because only the squash message reaches `main`.

A line in a code or config file can skip one check with a comment that names the rule and gives a reason, for example `check-tells: allow TELL-1 because the regex cannot be split`. Reviewers check each skip.

The command exits with 0 when all files pass, with 1 when a rule is broken, and with 2 when its input is bad, for example a path that does not exist or a folder that is not a git repo.

## Dependencies

- **DEP-1 MUST.** A `core` package has no runtime dependencies.
- **DEP-2 MUST.** A client uses the platform's standard HTTP and JSON libraries, or the ones that its language file names.
- **DEP-3 MUST.** A new runtime dependency needs an ADR in `docs/adr/`.
- **DEP-4 MUST.** Each dependency uses a permissive licence, such as MIT, BSD, ISC or Apache-2.0. **(tool)**
- **DEP-5 MUST.** Lockfiles are in the repo. Renovate opens update pull requests each week. **(tool)**

## Runtime versions

- **VER-1 MUST.** Each language file states its runtime floors and the end-of-life date of each floor. A floor that is past its end of life needs an ADR that explains the trade-off.
- **VER-2 MUST.** Raise a floor only in a minor release. Announce the change in the changelog of the release before it.

## Errors and logging

- **ERR-1 MUST.** Each HTTP status maps to exactly one error code. The spec does not define the map yet. It will define the map with the contract scenarios, before the first client release.
- **ERR-2 MUST.** A library does not log. It returns or raises errors. A caller can attach a debug hook.
- **ERR-3 MUST.** No error, log or exception message contains an API key, a NIN, an email address, or a full postcode next to personal data. Use `redact()` for postcodes.
- **ERR-4 MUST.** An error message says what happened and what to do, in plain English. Example: "The postcode has 10 characters. A postcode has 11 characters."

## Security and privacy

- **SEC-1 MUST.** Client-side code refuses secret keys, which start with `nipost_test_` or `nipost_live_`.
- **SEC-2 MUST.** There is no telemetry. An SDK sends only the requests that the caller makes.
- **SEC-3 MUST.** The cache is off by default. When on, it has a time limit and a clear command.
- **SEC-4 MUST.** Call only the documented gateway endpoints.
- **SEC-5 MUST.** CI scans each pull request and each push to `main` for secrets. **(tool)**
- **SEC-6 MUST.** Each GitHub Action is pinned to a full commit SHA. **(tool)**
- **SEC-7 MUST.** Releases come only from CI. They carry provenance or a signature where the registry supports it.
- **SEC-8 MUST.** Each repo has `SECURITY.md`. A reporter gets a reply within 3 working days.

## Tests

- **T-1 MUST.** Write the failing test first for each change in behaviour.
- **T-2 MUST.** Every SDK runs every vector in `spec/vectors/` for the spec version that it implements. **(tool)**
- **T-3 MUST.** Every client passes every contract scenario in `spec/contract/` against the mock server in CI. The scenarios fix the shared client behaviour: error codes, retries, waits, caching and the limit on parallel requests. **(tool)**
- **T-4 MUST.** A test can fail. It asserts a specific value, and it does not repeat the logic under test.
- **T-5 MUST.** Unit tests use no network, no real clock and no sleep.
- **T-6 MUST.** A test name states the behaviour in domain words, for example "rejects a unit of 00".
- **T-7 MUST.** Coverage floors are 95 % of branches for core, 90 % for clients and 80 % for UI. UI coverage includes browser tests. **(tool)**
- **T-8 SHOULD.** Core runs mutation tests each week, with a target score of 85 %. **(tool)**
- **T-9 SHOULD.** The parser has property-based or fuzz tests, where the language has a standard tool for them.
- **T-10 MUST.** UI tests include keyboard-only use and an automated accessibility check.

## Documentation

- **DOC-1 MUST.** Each public symbol has a doc comment. It gives a one-line summary, each parameter, each error and one example.
- **DOC-2 MUST.** Each README follows `templates/README.md`.
- **DOC-3 MUST.** Each code example in a README or on the docs site runs in CI.
- **DOC-4 MUST.** Prose uses plain English. Write sentences of 25 words or fewer, with one idea in each. Use the active voice, and name who does the action. Use the plainest word, and use one word for one meaning. Keep every article and connector. Write a verb, not a noun that is made from it, and do not put more than three nouns in a row. Do not use phrasal verbs, semicolons, stacked hedges, em dashes or marketing words such as "powerful" and "seamless". Do not open with filler or close with a summary. Use British spelling.
- **DOC-5 MUST.** Each package has a changelog that change files generate. It follows the Keep a Changelog format, unless the release tool writes its own format. Changesets, the tool for npm packages, writes its own format.
- **DOC-6 SHOULD.** Record a decision as an ADR when it is hard to reverse, surprising, and the result of a real trade-off. An ADR is a short file in `docs/adr/` that gives the context, the decision and the reason.
- **DOC-7 MUST.** A new domain term goes into `CONTEXT.md` before it goes into code.

## Git, pull requests and releases

- **GIT-1 MUST.** Commits follow Conventional Commits. The scope names the package, or is repo, deps or release for a change outside a package. The spec repo has no packages. Its commits use no scope. **(tool)**
- **GIT-2 MUST.** Each commit has a DCO sign-off: `git commit -s`. **(tool)**
- **GIT-3 MUST.** Commits do not carry co-author lines for AI tools. The person who opens the pull request owns the change.
- **GIT-4 MUST.** Nobody force-pushes to `main` or to a shared branch.
- **GIT-5 SHOULD.** A pull request changes at most about 400 lines. Tests, vectors and generated files do not count.
- **GIT-6 MUST.** A pull request needs one approval and green CI. Merges use squash. The title of the pull request becomes the subject of the commit on `main`, and its body becomes the body, so both follow GIT-1, GIT-2 and TELL-18.
- **GIT-7 MUST.** A pull request that changes the public interface also updates the API report, the docs and a change file. **(tool)**
- **GIT-8 MUST.** Each package exposes a `SPEC_VERSION` constant. It names the spec version that the package implements.

## UI

These rules apply to the field, the docs site and every app screen.

- **UI-1 MUST.** Meet WCAG 2.2 AA.
- **UI-2 MUST.** Each string comes from a [message catalogue](#the-check-tells-script), which is a data file. A code module of strings is code, so it uses ASCII (TELL-14). Do not build sentences by joining strings. A UI shows the catalogue string for an error code, not the library's error message.
- **UI-3 MUST.** Colours, radii and fonts come from theme tokens. Components contain no fixed colours.
- **UI-4 MUST.** Respect the user's reduced-motion setting and text size.
- **UI-5 SHOULD.** Design each new screen on purpose. Choose its layout, type and colour for the task, with the theme tokens of UI-3, and do not keep the defaults of a UI kit or a template.

## Performance

- **PERF-1 MUST.** Each package stays inside its size limit. **(tool)**
- **PERF-2 MUST.** Importing a package does no work: no network calls, no timers and no global registration. The field's custom element is the one exception.
- **PERF-3 SHOULD.** Web packages are tree-shakeable.

## Licence and notices

- **LIC-1 MUST.** Each file has licence information that `reuse lint` accepts. A file whose format has comments starts with two SPDX lines, one for the copyright and one for the licence `Apache-2.0`, unless `REUSE.toml` covers it. `REUSE.toml` covers Markdown, JSON and YAML files, and a few plain files such as `NOTICE`. **(tool)**
- **LIC-2 MUST.** Each repo has `LICENSE` and `NOTICE`.
- **LIC-3 MUST.** Each README and each package description says "Unofficial. Not made or endorsed by NIPOST."

## Cross-language parity

- **PAR-1 MUST.** An SDK that claims a spec version passes every vector and every contract scenario of that version.
- **PAR-2 MUST.** Error codes, defaults and option meanings are identical in every SDK.
- **PAR-3 MUST.** The docs site has a parity table. It shows each SDK, its version, its spec version and its status.

## Gates

### New package gate

A new package can publish its first release only when all of these are true:

- **NPG-1.** The repo has the community files from `templates/`.
- **NPG-2.** The language file's tools run in CI, and they pass.
- **NPG-3.** All vectors pass.
- **NPG-4.** The client passes every contract scenario against the mock server.
- **NPG-5.** The repo holds the API report or API dump.
- **NPG-6.** The README quickstart runs in CI.
- **NPG-7.** The coverage floors pass.
- **NPG-8.** A second person reviewed the whole package twice, once against these standards and once against the spec. Neither review has an open finding.

### Release gate

Each release meets all of these:

- **REL-1.** CI is green on the release commit.
- **REL-2.** The change files describe each user-visible change.
- **REL-3.** Each breaking change has a migration note.
- **REL-4.** The release runs from CI, with provenance or a signature.

### 1.0 gate

A package can release 1.0 only when all of these are true:

- **V1-1.** The spec is at 1.0.
- **V1-2.** The public interface did not change for 4 weeks.
- **V1-3.** At least two production users run the package.
- **V1-4.** The docs cover every public symbol and every error code.

## Review checklist

Tools check the **(tool)** rules. Reviewers check these by hand:

1. The interface: API-1, API-3, API-7 and API-12.
2. The structure: CS-1, CS-7 and CS-8.
3. The errors: ERR-3 and ERR-4.
4. The tests: T-4 and T-6.
5. The docs: DOC-1, DOC-4 and DOC-7.
6. The tells that need a person: TELL-4, TELL-5, TELL-6, TELL-8, TELL-11, TELL-15, TELL-19 and TELL-20.
7. Code smells that no rule names, such as a function that does several jobs, or the same logic in two places. Treat each smell as a judgement call.
