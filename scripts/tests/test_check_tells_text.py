# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for check_tells.text: how the checks read lines and characters (TELL-14)."""

import unittest

from check_tells import check_text

from tests.check_tells_driver import rules
from tests.check_tells_samples import (
    E_ACUTE,
    EMOJI,
    KIND_BY_PATH,
    LINE_SEPARATOR,
    LONG_LINE,
    NO_BREAK_SPACE,
    O_DOT_BELOW,
    TO_DO,
)

# The ranges are typed out here, not read from check_tells, so that a change to them fails.
EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),
    (0x231A, 0x231B),
    (0x23E9, 0x23F3),
    (0x2600, 0x27BF),
    (0x2B00, 0x2BFF),
    (0xFE0F, 0xFE0F),
)


class CharacterTest(unittest.TestCase):
    def test_rejects_an_emoji_in_markdown(self) -> None:
        self.assertEqual(rules(check_text("README.md", f"Done {EMOJI}")), ["TELL-14"])

    def test_rejects_an_hourglass_in_markdown(self) -> None:
        self.assertEqual(rules(check_text("README.md", "Waiting " + chr(0x23F3))), ["TELL-14"])
        self.assertEqual(rules(check_text("README.md", "Done " + chr(0x231B))), ["TELL-14"])

    def test_rejects_the_emoji_that_agents_write(self) -> None:
        names = {
            "check mark": 0x2705,
            "cross mark": 0x274C,
            "warning sign": 0x26A0,
            "sparkles": 0x2728,
            "rocket": 0x1F680,
            "star": 0x2B50,
            "arrow": 0x2B06,
        }
        for name, point in names.items():
            with self.subTest(name=name):
                found = check_text("README.md", f"Done {chr(point)} here")
                self.assertEqual(rules(found), ["TELL-14"])
                self.assertEqual(found[0].column, 6)
                self.assertEqual(found[0].message, f"Remove the emoji U+{point:04X}.")

    def test_rejects_both_ends_of_each_emoji_range(self) -> None:
        for low, high in EMOJI_RANGES:
            for point in (low, high):
                with self.subTest(point=f"U+{point:04X}"):
                    found = check_text("README.md", f"a {chr(point)} b")
                    self.assertEqual(rules(found), ["TELL-14"])

    def test_accepts_the_character_next_to_each_emoji_range(self) -> None:
        for low, high in EMOJI_RANGES:
            for point in (low - 1, high + 1):
                with self.subTest(point=f"U+{point:04X}"):
                    self.assertEqual(check_text("README.md", f"a {chr(point)} b"), [])

    def test_rejects_the_emoji_variation_selector_after_a_symbol(self) -> None:
        found = check_text("README.md", "Heart " + chr(0x2764) + chr(0xFE0F))
        self.assertEqual(rules(found), ["TELL-14", "TELL-14"])
        self.assertEqual([violation.column for violation in found], [7, 8])

    def test_rejects_non_ascii_in_code(self) -> None:
        found = check_text("src/a.ts", f"const space = '{NO_BREAK_SPACE}';")
        self.assertEqual(rules(found), ["TELL-14"])
        self.assertIn("U+00A0", found[0].message)

    def test_rejects_non_ascii_in_each_code_and_config_kind(self) -> None:
        for kind in ("code", "config"):
            for path in KIND_BY_PATH[kind]:
                with self.subTest(path=path):
                    found = check_text(path, f"a{NO_BREAK_SPACE}b")
                    self.assertEqual(rules(found), ["TELL-14"])
                    self.assertEqual(found[0].column, 2)

    def test_asks_for_an_escape_sequence_for_non_ascii_and_not_for_an_emoji(self) -> None:
        emoji = check_text("src/a.ts", f"const a = '{EMOJI}';")
        other = check_text("src/a.ts", f"const a = '{E_ACUTE}';")
        self.assertEqual(emoji[0].message, "Remove the emoji U+1F600.")
        self.assertEqual(
            other[0].message,
            "Write U+00E9 as an escape sequence. Code and config use ASCII.",
        )

    def test_reports_one_non_ascii_character_for_each_line(self) -> None:
        found = check_text("src/a.ts", f"{E_ACUTE}{E_ACUTE}\n{E_ACUTE}")
        self.assertEqual([(v.line, v.column) for v in found], [(1, 1), (2, 1)])

    def test_accepts_the_last_ascii_character_in_code(self) -> None:
        self.assertEqual(check_text("src/a.ts", "// " + chr(0x7F)), [])
        self.assertEqual(rules(check_text("src/a.ts", "// " + chr(0x80))), ["TELL-14"])

    def test_accepts_non_ascii_in_prose_and_catalogues(self) -> None:
        self.assertEqual(check_text("docs/guide.md", f"Caf{E_ACUTE}"), [])
        self.assertEqual(check_text("src/locales/yo.json", f'{{"title": "Caf{E_ACUTE}"}}'), [])

    def test_accepts_non_ascii_in_every_file_that_is_not_code_or_config(self) -> None:
        for kind in ("prose", "catalogue", "exempt", "other"):
            for path in KIND_BY_PATH[kind]:
                with self.subTest(path=path):
                    self.assertEqual(check_text(path, f"Caf{E_ACUTE}"), [])

    def test_rejects_an_emoji_in_every_kind_of_file(self) -> None:
        for paths in KIND_BY_PATH.values():
            for path in paths:
                with self.subTest(path=path):
                    found = check_text(path, f"a {EMOJI} b")
                    self.assertEqual(rules(found), ["TELL-14"])
                    self.assertEqual(found[0].column, 3)

    def test_holds_a_code_file_in_a_catalogue_folder_to_ascii(self) -> None:
        line = "export const title = '" + O_DOT_BELOW + "';"
        self.assertEqual(rules(check_text("src/i18n/yo.ts", line)), ["TELL-14"])

    def test_rejects_an_emoji_in_a_catalogue(self) -> None:
        found = check_text("src/locales/en.json", f'{{"ok": "{EMOJI}"}}')
        self.assertEqual(rules(found), ["TELL-14"])

    def test_accepts_non_ascii_in_each_catalogue_folder_and_extension(self) -> None:
        for path in KIND_BY_PATH["catalogue"]:
            with self.subTest(path=path):
                self.assertEqual(check_text(path, f"{O_DOT_BELOW}: {LONG_LINE}"), [])

    def test_holds_other_android_files_to_ascii(self) -> None:
        for path in ("res/layout/strings.xml", "res/values/colors.xml", "strings.xml"):
            with self.subTest(path=path):
                self.assertEqual(rules(check_text(path, f"{E_ACUTE}")), ["TELL-14"])

    def test_reads_a_smart_quote_in_a_style_file(self) -> None:
        found = check_text("src/field.css", "content: " + chr(0x201C) + "x" + chr(0x201D) + ";")
        self.assertEqual(rules(found), ["TELL-14"])

    def test_checks_an_exempt_file_for_emoji_only(self) -> None:
        for path in KIND_BY_PATH["exempt"]:
            with self.subTest(path=path):
                found = check_text(path, f"{LONG_LINE}{E_ACUTE}\n{TO_DO}\n{EMOJI}")
                self.assertEqual([(v.rule, v.line) for v in found], [("TELL-14", 3)])

    def test_checks_a_text_file_with_a_binary_looking_name_for_emoji(self) -> None:
        self.assertEqual(
            rules(check_text("readme.txt", f"Works with WooCommerce {EMOJI}")), ["TELL-14"]
        )
        self.assertEqual(rules(check_text("src/locales/yo.txt", f"Ok {EMOJI}")), ["TELL-14"])


class LineSplitTest(unittest.TestCase):
    def test_keeps_a_line_separator_inside_the_line(self) -> None:
        text = "const a = 1;" + LINE_SEPARATOR + "const b = 2;"
        self.assertEqual(rules(check_text("src/a.ts", text)), ["TELL-14"])

    def test_keeps_the_line_numbers_after_a_form_feed(self) -> None:
        found = check_text("src/a.ts", "const a = 1;" + chr(0x0C) + "\nconsole.log(1);")
        self.assertEqual(rules(found), ["TELL-13"])
        self.assertEqual(found[0].line, 2)

    def test_treats_crlf_like_lf(self) -> None:
        text = "x" * 100 + "\nconsole.log(1);\n"
        found = check_text("src/a.ts", text.replace("\n", "\r\n"))
        self.assertEqual(rules(found), ["TELL-13"])
        self.assertEqual(found, check_text("src/a.ts", text))
