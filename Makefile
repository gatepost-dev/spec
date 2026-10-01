# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
.PHONY: check test tells lint types licences

check: test tells lint types licences

test:
	python3 -m unittest discover -s scripts/tests -t scripts

tells:
	python3 scripts/check-tells

lint:
	uvx ruff check scripts
	uvx ruff format --check scripts

types:
	uvx mypy

# reuse needs an encoding detector, and uvx installs reuse without one.
licences:
	uvx --with charset-normalizer reuse lint
