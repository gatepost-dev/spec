<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/gatepost-dev/.github/main/brand/gatepost-lockup-dark.svg">
    <img src="https://raw.githubusercontent.com/gatepost-dev/.github/main/brand/gatepost-lockup.svg" alt="Gatepost" width="220">
  </picture>
</p>

<h1 align="center">{{PACKAGE_NAME}}</h1>

<p align="center">{{ONE_SENTENCE_SUMMARY}}</p>

<p align="center">
  <a href="{{CI_URL}}"><img src="{{CI_BADGE_URL}}" alt="CI status"></a>
  <a href="{{REGISTRY_URL}}"><img src="{{VERSION_BADGE_URL}}" alt="Version"></a>
  <a href="https://github.com/gatepost-dev/{{REPO_NAME}}/blob/main/LICENSE"><img src="https://img.shields.io/badge/licence-Apache--2.0-blue?style=flat" alt="Licence: Apache-2.0"></a>
  <a href="{{SCORECARD_URL}}"><img src="{{SCORECARD_BADGE_URL}}" alt="OpenSSF Scorecard"></a>
</p>

<p align="center">
  <a href="https://gatepost-dev.github.io/docs/">Docs</a>
  &middot;
  <a href="https://gatepost-dev.github.io/docs/playground/">Playground</a>
  &middot;
  <a href="{{DOCS_PAGE_URL}}">{{DOCS_PAGE_NAME}}</a>
  &middot;
  <a href="https://github.com/gatepost-dev/.github/blob/main/CONTRIBUTING.md">Contributing</a>
  &middot;
  <a href="https://github.com/gatepost-dev/{{REPO_NAME}}/discussions">Discussions</a>
</p>

> Unofficial. Not made or endorsed by NIPOST.

```{{LANGUAGE_ID}}
{{QUICKSTART_CODE}}
```

{{ONE_SENTENCE_ABOUT_THE_OUTPUT}}

## Install

```sh
{{INSTALL_COMMAND}}
```

{{UNPUBLISHED_NOTE}}

## Use

```{{LANGUAGE_ID}}
{{SECOND_EXAMPLE_CODE}}
```

| Function | What it does |
|---|---|
| `{{FUNCTION}}` | {{WHAT_IT_DOES}} |

## What it does

- {{CAPABILITY}}

## Requirements

| Requirement | Version |
|---|---|
| {{RUNTIME}} | {{MINIMUM_VERSION}} or later |
| Gatepost spec | {{SPEC_VERSION}} |

## Docs

The guide and the API reference are at {{DOCS_URL}}.

## Support

Ask questions in [GitHub Discussions](https://github.com/gatepost-dev/{{REPO_NAME}}/discussions). Report bugs in [GitHub Issues](https://github.com/gatepost-dev/{{REPO_NAME}}/issues). Report security problems through the [private form](https://github.com/gatepost-dev/{{REPO_NAME}}/security/advisories/new).

## Develop

Read [`CONTRIBUTING.md`](https://github.com/gatepost-dev/.github/blob/main/CONTRIBUTING.md) before you open a pull request. {{REPO_STEPS_LINK}}

## Licence

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

<!--
Template rules, from standards/CODING_STANDARDS.md:
- DOC-2: keep the header block, the notice and these sections in this order. Use HTML only in the header block.
- DOC-2: keep a package README to 100 to 130 lines. A monorepo root README holds a package table and little else.
- DOC-3: CI runs the quickstart and the second example. Keep the quickstart at 10 lines or fewer.
- LIC-3: keep the "Unofficial" line, directly after the header block.
- TELL-14: no emojis. Show a badge only for a thing that exists today.
- Badges: CI, version, licence, Scorecard, in that order. Delete the version badge until the package is on its registry.
  Delete the Scorecard badge unless the repo has a scorecard workflow that has run and published.
- Install: keep the real command. While the package is not on its registry, {{UNPUBLISHED_NOTE}} is one plain sentence:
  "The first alpha is not published yet." Delete it in the commit that publishes the package.
- Delete {{REPO_STEPS_LINK}} if the repo has no steps of its own.
Delete this comment when you fill in the template.
-->
