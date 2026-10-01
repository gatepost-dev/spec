# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
.PHONY: check test lint types licences

check: test lint types licences

test:
	python3 -m unittest discover -s scripts/tests -t scripts

lint:
	uvx ruff check scripts
	uvx ruff format --check scripts

types:
	uvx mypy

licences:
	uvx reuse lint
