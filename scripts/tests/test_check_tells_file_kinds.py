# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for check_tells.file_kinds: the kind and the language of a file."""

import unittest

from check_tells import check_text, classify

from tests.check_tells_driver import rules
from tests.check_tells_samples import KIND_BY_PATH, LONG_LINE

LANGUAGE_BY_PATH = {
    "a.ts": "javascript",
    "a.vue": "javascript",
    "a.astro": "javascript",
    "a.svelte": "javascript",
    "a.php": "php",
    "config.php.dist": "php",
    "a.py": "python",
    "a.go": "go",
    "a.kt": "jvm",
    "a.java": "jvm",
    "a.cs": "dotnet",
    "a.dart": "dart",
    "a.swift": "swift",
    "a.css": None,
    "a.html": None,
    "a.sh": None,
    "a.md": None,
}


class ClassifyTest(unittest.TestCase):
    def test_reads_the_kind_of_each_file_name(self) -> None:
        for kind, paths in KIND_BY_PATH.items():
            for path in paths:
                with self.subTest(path=path):
                    self.assertEqual(classify(path, "").kind, kind)

    def test_reads_the_language_of_each_file_name(self) -> None:
        for path, language in LANGUAGE_BY_PATH.items():
            with self.subTest(path=path):
                self.assertEqual(classify(path, "").language, language)

    def test_reads_a_file_without_a_suffix_from_its_first_line(self) -> None:
        self.assertEqual(classify("scripts/run", "#!/usr/bin/env python3\n").kind, "code")
        self.assertEqual(classify("scripts/run", "plain text\n").kind, "other")
        self.assertEqual(classify("scripts/run", "").kind, "other")

    def test_reads_the_suffix_before_a_shebang(self) -> None:
        cases = {
            "notes.txt": "exempt",
            "README.md": "prose",
            "package.json": "config",
            "font.woff": "other",
            "src/locales/en.json": "catalogue",
        }
        for path, kind in cases.items():
            with self.subTest(path=path):
                self.assertEqual(classify(path, "#!/usr/bin/env python3\n").kind, kind)

    def test_reads_the_interpreter_of_a_shebang(self) -> None:
        cases = {
            "#!/usr/bin/env python3": "python",
            "#!/usr/bin/env python": "python",
            "#!/usr/bin/python3": "python",
            "#!/usr/bin/env node": "javascript",
            "#!/usr/bin/node": "javascript",
            "#!/bin/sh": None,
        }
        for first_line, language in cases.items():
            with self.subTest(first_line=first_line):
                self.assertEqual(classify("scripts/run", first_line).language, language)

    def test_reads_a_dist_file_like_the_file_that_it_copies(self) -> None:
        self.assertEqual(rules(check_text("phpunit.xml.dist", LONG_LINE)), ["TELL-1"])
        self.assertEqual(rules(check_text("config.php.dist", "var_dump($x);")), ["TELL-13"])
        self.assertEqual(rules(check_text("PHPUNIT.XML.DIST", LONG_LINE)), ["TELL-1"])

    def test_keeps_the_folder_rules_for_a_dist_file(self) -> None:
        self.assertEqual(check_text("src/locales/en.json.dist", LONG_LINE), [])
