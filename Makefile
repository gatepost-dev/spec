# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
.PHONY: check test vectors contract tells lint types licences actions

# Each tool has an exact version. A new release can add rules and turn CI red on a change that
# has nothing to do with it. Renovate opens the pull requests that move these versions.
# renovate: datasource=pypi depName=ruff
RUFF_VERSION := 0.16.10
# renovate: datasource=pypi depName=mypy
MYPY_VERSION := 2.4.0
# renovate: datasource=pypi depName=reuse
REUSE_VERSION := 6.2.0
# renovate: datasource=pypi depName=charset-normalizer
CHARSET_NORMALIZER_VERSION := 3.5.2
# renovate: datasource=pypi depName=zizmor
ZIZMOR_VERSION := 1.30.1
# renovate: datasource=pypi depName=pyyaml
PYYAML_VERSION := 6.0.3
# renovate: datasource=pypi depName=jsonschema
JSONSCHEMA_VERSION := 4.26.0
# renovate: datasource=pypi depName=types-pyyaml
TYPES_PYYAML_VERSION := 6.0.12.20260906
# renovate: datasource=pypi depName=types-jsonschema
TYPES_JSONSCHEMA_VERSION := 4.26.0.20260518
# renovate: datasource=pypi depName=openapi-spec-validator
OPENAPI_SPEC_VALIDATOR_VERSION := 0.9.0

# scripts/check-tells has no .py suffix, so the tools need its name.
SCRIPTS := scripts scripts/check-tells

# The checks of the OpenAPI file read YAML and JSON Schema. uv adds the two packages to the
# Python on PATH, so each Python of the CI matrix runs the tests.
PYTHON := uv run --no-project --python-preference only-system \
	--with pyyaml==$(PYYAML_VERSION) --with jsonschema==$(JSONSCHEMA_VERSION) python3

check: test vectors contract tells lint types licences actions

test:
	$(PYTHON) -m unittest discover -s scripts/tests -t scripts

vectors:
	python3 scripts/build_vectors.py --check

contract:
	uvx openapi-spec-validator@$(OPENAPI_SPEC_VALIDATOR_VERSION) openapi/gateway.completed.yaml

tells:
	python3 scripts/check-tells

lint:
	uvx ruff@$(RUFF_VERSION) check $(SCRIPTS)
	uvx ruff@$(RUFF_VERSION) format --check $(SCRIPTS)

types:
	uvx --with types-pyyaml==$(TYPES_PYYAML_VERSION) \
		--with types-jsonschema==$(TYPES_JSONSCHEMA_VERSION) mypy@$(MYPY_VERSION)

# reuse needs an encoding detector, and uvx installs reuse without one.
licences:
	uvx --with charset-normalizer==$(CHARSET_NORMALIZER_VERSION) reuse@$(REUSE_VERSION) lint

# SEC-6: zizmor finds an action that is not pinned to a commit, and text of a pull request that
# reaches a script. Its other checks need a GitHub token, so this run is offline.
actions:
	uvx zizmor@$(ZIZMOR_VERSION) --offline .
