# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests that the README example is a real vector, and that the README keeps its header."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTICE = "> Unofficial. Not made or endorsed by NIPOST."


class ReadmeTest(unittest.TestCase):
    def test_example_vector_is_the_case_in_the_vectors_file(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        block = re.search(r"```json\n(.*?)\n```", readme, re.DOTALL)
        self.assertIsNotNone(block)
        shown = json.loads(block.group(1) if block else "")
        vectors = json.loads((ROOT / "vectors" / "contains.json").read_text(encoding="utf-8"))
        case = next(item for item in vectors["cases"] if item["id"] == shown["id"])
        self.assertEqual(shown, case)

    def test_readme_and_template_keep_the_notice_after_the_header_block(self) -> None:
        for name in ("README.md", "templates/README.md"):
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn(NOTICE, text)
                self.assertLess(text.index('<h1 align="center">'), text.index(NOTICE))
