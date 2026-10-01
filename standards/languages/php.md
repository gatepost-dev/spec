# PHP standards

Version 1.0, 1 Oct 2026.

This file and `standards/CODING_STANDARDS.md` together are the standard for PHP code. Part A applies to the SDK in the `php` repo. Part B applies to WordPress plugins, such as the WooCommerce plugin. Each part names its own code style, because the two ecosystems use different conventions.

## Versions

- PHP 8.1 or later. CI tests PHP 8.1 and the newest PHP release.
- PHP 8.1 reached end of life on 31 Dec 2025, and PHP 8.2 reaches it on 31 Dec 2026. The 8.1 floor serves WordPress stores on older hosting. Under VER-1, ADR 0001 must record this trade-off with current WordPress usage data before the first release. If the data does not support 8.1, raise the floor.
- PHPUnit 11 and later need PHP 8.2. CI runs PHPUnit 10 on PHP 8.1 and the newest PHPUnit on newer PHP versions.
- WordPress and WooCommerce: the plugin sub-plan sets the floors after it tests the Additional Checkout Fields API.

## Part A: the SDK

### Tools

`composer check` runs every tool below. CI runs `composer check` on each push and each pull request.

| Tool | Job | Settings |
|---|---|---|
| PHP-CS-Fixer | format and style | `@PER-CS`, `@PER-CS:risky`, `declare_strict_types`, `strict_comparison`, `strict_param`, `final_class`, `no_unused_imports`, `ordered_imports` |
| PHPStan | static analysis | level `max`, with `phpstan-strict-rules`, `phpstan-deprecation-rules` and `phpstan-phpunit` |
| PHPUnit 10 | unit and contract tests | coverage floors from T-7 |
| Infection | mutation tests | the core namespace, weekly scheduled job |
| Roave BackwardCompatibilityCheck | API check against the last tag | enforces GIT-7 and API-13 |
| `composer validate --strict` and `composer-normalize` | package checks | every push |
| PHPMD | size and complexity | `CyclomaticComplexity` 10, `ExcessiveParameterList` minimum 5, enforces TELL-2 and TELL-3 |
| changie | change files and changelog | one change file per user-visible change, enforces DOC-5 |
| REUSE | licence headers | `reuse lint` |
| gitleaks | secret scan | every push |
| `spec/scripts/check-tells` | agent tells | line length 100, file names, TODO form, debug calls, emojis and non-ASCII |

PHP-CS-Fixer does not limit line length, so `check-tells` enforces TELL-1. PHPMD has no nesting rule, so reviewers check nesting for TELL-2.

`check-tells` bans these debug calls in PHP: `var_dump`, `print_r`, `var_export`, `dd`, `dump`, `error_log` and `debug_print_backtrace`.

### Rules

- **PHP-1 MUST.** Each file declares `declare(strict_types=1);`. **(tool)**
- **PHP-2 MUST.** Namespaces follow PSR-4 under `Gatepost\Postcode\`. **(tool)**
- **PHP-3 MUST.** Classes are `final`, unless the spec names an extension point. **(tool)**
- **PHP-4 MUST.** Value objects have `readonly` properties. Their constructors are private, and named constructors create them, for example `Postcode::parse()`.
- **PHP-5 MUST.** Error codes are string-backed enums. Each case's value is the shared wire value, for example `ErrorCode::RateLimited` is `'rate_limited'`.
- **PHP-6 MUST.** The client depends only on the PSR-18, PSR-17 and PSR-16 interfaces. A concrete HTTP client, such as Guzzle, is a dev dependency only.
- **PHP-7 MUST.** There is no static mutable state.
- **PHP-8 MUST.** Each array has a PHPDoc shape or generic type, for example `list<string>`. **(tool)**
- **PHP-9 MUST.** The package does not depend on `ext-intl` or `ext-mbstring`. Use PCRE patterns with the `u` flag, and static lookup tables with `strtr`.
- **PHP-10 MUST.** The package throws only `PostcodeException`. For programmer errors, it throws `InvalidArgumentException` or `LogicException`.
- **PHP-11 MUST.** Do not use the `@` operator or `eval`. **(tool)**
- **PHP-12 MUST.** Each method declares its parameter types and its return type. **(tool)**
- **PHP-13 SHOULD.** Examples and docs use named arguments, for example `$client->lookup($code, level: 2)`.
- **PHP-14 MUST.** The client decodes JSON into arrays and reads only the keys that it knows (API-14).
- **PHP-15 MUST.** The client is synchronous, so it sends one request at a time. This meets the limit in API-8.

### Idiomatic additions (API-1)

The PHP SDK follows the spec's interface section. Its client constructor takes PSR-18, PSR-17 and PSR-16 objects. These are parameters, not new public symbols.

### Names

| Element | Style | Example |
|---|---|---|
| class, enum, interface | PascalCase | `PostcodeClient` |
| method, variable | camelCase | `precisionForAccuracy` |
| enum case | PascalCase | `ErrorCode::BadLength` |
| constant | UPPER_SNAKE_CASE | `SPEC_VERSION` |
| error code value | snake_case string | `'bad_length'` |

### Package layout

```
src/                  PSR-4 root for Gatepost\Postcode\
src/Client/           the client and its errors
tests/Unit/
tests/Contract/       runs against the mock server
tests/Vectors/        runs spec/vectors/
README.md             from templates/README.md
CHANGELOG.md
```

### Publishing

- A Git tag `vX.Y.Z` on `main` publishes the version on Packagist.
- CI creates the tag. Tags are signed.

## Part B: WordPress plugins

### Tools

`composer check` runs every tool below. CI runs it on each push and each pull request.

| Tool | Job | Settings |
|---|---|---|
| PHPCS with WordPress Coding Standards 3 | style and security sniffs | `WordPress-Extra` and `WordPress-Docs` |
| PHPCompatibilityWP | PHP version check | `testVersion` 8.1 and later |
| PHPStan with `szepeviktor/phpstan-wordpress` | static analysis | level 8 |
| Plugin Check | WordPress.org review rules | `wp plugin check` on the built zip |
| PHPUnit with the WordPress test suite | integration tests | WooCommerce installed |
| Playwright | checkout tests | classic checkout and block checkout |
| Strauss | namespace prefixing for bundled packages | one prefix per plugin, `Gatepost\<Plugin>\Vendor\`, for example `Gatepost\WooCommerce\Vendor\` |
| PHPCS `Generic.Metrics` and `Generic.Files.LineLength` | agent tells | nesting level 3, cyclomatic complexity 10, line length 100 |
| changie | change files and changelog | one change file per user-visible change, enforces DOC-5 |
| `spec/scripts/check-tells` | agent tells | file names, TODO form, debug calls, emojis and non-ASCII |

### Rules

- **WP-1 MUST.** Plugin code follows WordPress Coding Standards 3. PER-CS does not apply to plugin code. **(tool)**
- **WP-2 MUST.** Each global function, class, hook, option, meta key and script handle starts with `gatepost_`, `Gatepost_` or the namespace `Gatepost\`. **(tool)**
- **WP-3 MUST.** Escape output late. Sanitize input early. Check a nonce and a capability before each write. **(tool)**
- **WP-4 MUST.** Each plugin bundles the PHP SDK under its own prefixed namespace with Strauss, for example `Gatepost\WooCommerce\Vendor\`. Two plugins that bundle different SDK versions, including two Gatepost plugins, must not clash.
- **WP-5 MUST.** Plugin Check reports no errors. **(tool)**
- **WP-6 MUST.** The plugin declares compatibility with HPOS and with the cart and checkout blocks.
- **WP-7 MUST.** Each user-facing string uses the plugin's text domain. A string with a placeholder has a translator comment. **(tool)**
- **WP-8 MUST.** The plugin stores only the postcode, the check result and the time of the check. It stores no other data from NIPOST's responses.
- **WP-9 MUST.** Uninstalling the plugin deletes its options. Order meta stays, because it belongs to the store's order records.
- **WP-10 MUST.** The plugin logs only through `wc_get_logger()`, with the source `gatepost`. The logs follow ERR-3.

### Publishing

- CI builds the zip with Strauss and runs Plugin Check on it.
- A GitHub release carries the zip.
- After WordPress.org approves the plugin, CI deploys each release to the WordPress.org SVN repository.
