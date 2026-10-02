# TypeScript standards

Version 1.0, 1 Oct 2026.

This file and `standards/CODING_STANDARDS.md` together are the standard for TypeScript code. They apply to every package and app in the `js` repo: core, client, field, React wrapper, docs site and demos. Later TypeScript work follows them too, such as the MCP server, the n8n node and the spreadsheet add-ins.

## Versions

- Published packages run on Node 22 or later. Node 22 reaches end of life on 30 Apr 2027. Raise the floor to Node 24 before then (VER-2).
- The development tools need Node 22.22.2 or a later 22.x release, or Node 24.15 or later. CI runs the tests on Node 22 and Node 24, and the other tools on Node 24.
- TypeScript 6.0. typescript-eslint supports only TypeScript versions below 6.1, so TypeScript 7 waits until typescript-eslint supports it. This was checked on 1 Oct 2026.
- React 18 and React 19, for `@gatepost/react`.
- Current evergreen browsers and Safari 16.4 or later, for browser code.
- Packages ship ESM only.

## Tools

`pnpm check` runs every tool below. CI runs `pnpm check` on each pull request and each push to `main`.

| Tool | Job | Settings |
|---|---|---|
| `tsc --noEmit` | type check | `tsconfig.base.json`, see below |
| ESLint with `typescript-eslint` | lint | `strictTypeChecked` and `stylisticTypeChecked`, plus the rules below |
| Prettier | format | `singleQuote: true`, `printWidth: 100`, other options at default |
| Vitest with V8 coverage | unit tests | coverage floors from T-7 |
| fast-check | property tests | `parse`, `normalize` and the hierarchy functions |
| Playwright with `@axe-core/playwright` | browser and accessibility tests | field and docs site |
| monocart-coverage-reports | merged coverage | merges Vitest and Playwright V8 coverage for the field, so T-7 counts browser tests |
| StrykerJS | mutation tests | `@gatepost/core`, weekly scheduled job |
| size-limit | size limits | core 4 KB, client 5 KB, field 20 KB, compressed, as size-limit measures them |
| publint and `@arethetypeswrong/cli` | package checks | every published package |
| API Extractor | API report | `etc/<package>.api.md`, checked in CI |
| Changesets | versions and changelogs | one change file per user-visible change |
| commitlint | commit messages | `@commitlint/config-conventional`, `scope-enum` with the scopes `core`, `client`, `field`, `react`, `repo`, `deps` and `release`, `scope-empty` set to `never` so each commit needs a scope (GIT-1), and `header-max-length` set to 72 characters (TELL-18) |
| REUSE | licence headers | `reuse lint` |
| gitleaks | secret scan | each pull request and each push to `main` |
| `spec/scripts/check-tells` | agent tells | line length 100, file names, TODO form, debug calls, emojis and non-ASCII |
| TypeDoc | API pages | the docs site renders them |

### `tsconfig.base.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022"],
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noPropertyAccessFromIndexSignature": true,
    "verbatimModuleSyntax": true,
    "isolatedDeclarations": true,
    "declaration": true,
    "sourceMap": true,
    "skipLibCheck": false,
    "noEmit": true
  }
}
```

tsdown builds the packages, so `tsc` only checks types. Each package's `tsconfig.json` includes `src` and `test`. Config files, such as `vitest.config.ts`, stay outside the TypeScript project, because `isolatedDeclarations` rejects their default exports. ESLint checks config files without type information.

### Extra ESLint rules

| Rule | Setting | Enforces |
|---|---|---|
| `no-restricted-syntax` for `TSEnumDeclaration` and `TSModuleDeclaration` | error | TS-5 |
| `no-restricted-exports` with `restrictDefaultExports` | error | TS-1 |
| `no-console` | error in packages | TS-12 |
| `@eslint-community/eslint-comments/require-description` | error | TS-13 |
| `eslint --max-warnings 0` | a warning fails the check, such as an unused `eslint-disable` comment | TS-13 |
| `jsdoc/require-jsdoc` with `publicOnly: true`, and `jsdoc/require-example` for exported functions, with `exemptedBy: ['internal']` | error in packages | TS-9 |
| `jsdoc/tag-lines` with `startLines: 1` | error in packages | one blank line between a description and its tags |
| `@typescript-eslint/explicit-module-boundary-types` | error in `packages/*/src` | TS-8 |
| `@typescript-eslint/no-non-null-assertion` | off in `packages/*/test` | TS-4 |
| `no-restricted-imports` for every Node built-in module, by bare name and as `node:*` | error in `packages/*/src` | CS-2 |
| `no-restricted-globals` for `process`, `Buffer`, `__dirname`, `__filename` and `global` | error in `packages/*/src` | CS-2 |
| `max-depth` | 3 | TELL-2 |
| `complexity` | 10 | TELL-2 |
| `max-params` | 4 | TELL-3 |
| `no-empty` with `allowEmptyCatch: false` | error | TELL-9 |
| `@typescript-eslint/no-unnecessary-condition` | error | TELL-10 |
| `@typescript-eslint/require-await` | error | TELL-16 |
| `no-nested-ternary` | error | TELL-17 |

Prettier's `printWidth: 100` matches TELL-1. Prettier does not split long strings or comments, so `check-tells` also checks line length.

`check-tells` bans these debug calls in TypeScript: `console.log`, `console.debug`, `console.dir` and `debugger`.

## Rules

- **TS-1 MUST.** Use named exports only. **(tool)**
- **TS-2 MUST.** Each package has one public entry, `src/index.ts`. The `exports` map in `package.json` has only `.`, plus the field's custom element entry. **(tool)**
- **TS-3 MUST.** Do not use `any`. Narrow `unknown` instead. **(tool)**
- **TS-4 MUST.** Do not use non-null assertions outside tests. **(tool)**
- **TS-5 MUST.** Do not use `enum` or `namespace`. Use string literal unions and modules. **(tool)**
- **TS-6 MUST.** Public types use `readonly` properties and `readonly` arrays, written `readonly T[]`.
- **TS-7 MUST.** A result type is a discriminated union with an `ok` field.
- **TS-8 MUST.** Each exported function and method declares its return type. **(tool)**
- **TS-9 MUST.** Each exported function has a TSDoc comment with `@example`. Each exported type and constant has a TSDoc comment. A helper that other modules use, but that `src/index.ts` does not export, carries the tag `@internal`. **(tool)**
- **TS-22 MUST.** Write an options object type inline as `Readonly<{ name?: Type }>`, and document it with one `@param options` line. The literal `readonly` form fails `eslint-plugin-jsdoc`, and a dotted `@param` name fails the TSDoc parser that API Extractor uses.
- **TS-10 MUST.** An error class extends `Error`, sets `name` and passes `cause`.
- **TS-11 MUST.** A `catch` block treats its value as `unknown` and narrows it. **(tool)**
- **TS-12 MUST.** Packages do not call `console`. **(tool)**
- **TS-13 MUST.** Each `eslint-disable` comment gives a reason. **(tool)**
- **TS-14 MUST.** Each package ships ESM with an `exports` map and type declarations. **(tool)**
- **TS-15 MUST.** Browser code does not read `window`, `document` or `customElements` at import time. The field's guarded registration is the one exception.
- **TS-16 SHOULD.** Prefer functions and plain objects. The allowed classes are `PostcodeClient`, `PostcodeError` and the custom element.
- **TS-17 MUST.** File names use kebab-case. Tests sit in `test/` and end in `.test.ts`.
- **TS-18 MUST.** Type-only imports use `import type`. **(tool)**
- **TS-19 MUST.** `@gatepost/react` supports React 18 and React 19. It uses `forwardRef` while it supports React 18. Each component starts with `'use client'`.
- **TS-20 MUST.** The client reads only the response fields that it knows and ignores the rest (API-14). It parses each response with a narrowing function, not with a type assertion.
- **TS-21 MUST.** The client limits parallel requests with an internal queue, set by API-8. Batch tools, such as spreadsheet add-ins, call the client and add no parallelism of their own.

### Idiomatic additions (API-1)

The TypeScript SDK follows the Interface section of `spec/grammar.md` exactly. It adds no idiomatic symbols.

## Names

| Element | Style | Example |
|---|---|---|
| function, variable, method | camelCase | `precisionForAccuracy` |
| type, class, interface | PascalCase | `ParseResult` |
| exported constant | UPPER_SNAKE_CASE | `SPEC_VERSION` |
| error code value | snake_case string | `'rate_limited'` |
| custom element | kebab-case with prefix | `gatepost-postcode-field` |
| DOM event | kebab-case with prefix | `gatepost-change` |
| CSS custom property | kebab-case with prefix | `--gatepost-accent` |
| file | kebab-case | `precision-for-accuracy.ts` |

## Package layout

```
packages/<name>/
  src/index.ts          public entry, exports only
  src/<module>.ts       one module per file
  test/<module>.test.ts
  etc/<name>.api.md     API Extractor report
  package.json
  README.md             from templates/README.md
  CHANGELOG.md          generated by Changesets
```

## Publishing

- Changesets opens the release pull request.
- A GitHub Actions job publishes with npm trusted publishing and provenance.
- Pre-releases use the dist-tag `alpha` or `beta`. Stable releases use `latest`.
