# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for check_tells.message_checks: the sign-off, the template text and the templates."""

import json
import unittest
from pathlib import Path
from typing import Any

import check_tells
from check_tells import check_squash_message

from tests.check_tells_driver import rules
from tests.check_tells_samples import E_ACUTE, PLACEHOLDER_PARAGRAPH, RENOVATE_COMMENT, squash


class SignOffTest(unittest.TestCase):
    def test_requires_a_sign_off(self) -> None:
        found = check_squash_message("fix: reject a unit\n\nWhy the change is needed.\n")
        self.assertEqual(rules(found), ["GIT-2"])
        self.assertEqual((found[0].line, found[0].column), (1, 1))
        self.assertIn("The message has no Signed-off-by line.", found[0].message)

    def test_reads_each_form_of_a_sign_off(self) -> None:
        forms = [
            "Signed-off-by: Ada Bello <ada@example.org>",
            "signed-off-by: Ada Bello <ada@example.org>",
            "SIGNED-OFF-BY: Ada Bello <ada@example.org>",
            "Signed-off-by:  Ada Bello  <ada@example.org>  ",
            "Signed-off-by: A <a@b.c>",
            f"Signed-off-by: Ad{E_ACUTE} Bello <ada@example.org>",
            "Signed-off-by: renovate[bot] <29139614+renovate[bot]@users.noreply.github.com>",
        ]
        for form in forms:
            with self.subTest(form=form):
                self.assertEqual(check_squash_message(squash("fix: a unit", sign_off=form)), [])

    def test_rejects_each_line_that_only_looks_like_a_sign_off(self) -> None:
        forms = [
            "Signed-off-by:",
            "Signed-off-by: Ada Bello",
            "Signed-off-by: <ada@example.org>",
            "Signed-off-by: Ada Bello <ada>",
            "Signed-off-by: Ada Bello ada@example.org",
            "Signed-off-by Ada Bello <ada@example.org>",
            "Reviewed-by: Ada Bello <ada@example.org>",
            "Co-authored-by: Ada Bello <ada@example.org>",
            "- Signed-off-by: Ada Bello <ada@example.org>",
            "Signed-off-by: Ada <Bello> <ada@example.org>",
        ]
        for form in forms:
            with self.subTest(form=form):
                found = check_squash_message(squash("fix: a unit", sign_off=form))
                self.assertEqual(rules(found), ["GIT-2"])

    def test_rejects_the_placeholder_address_of_the_template(self) -> None:
        sign_off = "Signed-off-by: Your Name <you@example.com>"
        found = check_squash_message(squash("fix: a unit", sign_off=sign_off))
        self.assertEqual(rules(found), ["GIT-2"])
        self.assertEqual((found[0].line, found[0].column), (5, 1))
        self.assertIn("placeholder address", found[0].message)

    def test_rejects_the_placeholder_address_in_any_letter_case(self) -> None:
        sign_off = "Signed-off-by: Ada Bello <You@Example.com>"
        found = check_squash_message(squash("fix: a unit", sign_off=sign_off))
        self.assertEqual(rules(found), ["GIT-2"])

    def test_rejects_the_placeholder_address_next_to_a_real_sign_off(self) -> None:
        body = "Signed-off-by: Your Name <you@example.com>"
        found = check_squash_message(squash("fix: a unit", body=body))
        self.assertEqual([(v.rule, v.line) for v in found], [("GIT-2", 3)])

    def test_accepts_the_placeholder_address_in_prose(self) -> None:
        body = "The template shows you@example.com in its sign-off line."
        self.assertEqual(check_squash_message(squash("docs: fix a template", body=body)), [])


class TemplateTextTest(unittest.TestCase):
    def test_rejects_the_placeholder_paragraph_of_the_template(self) -> None:
        found = check_squash_message(squash("fix: a unit", body=PLACEHOLDER_PARAGRAPH))
        self.assertEqual(rules(found), ["TELL-18"])
        self.assertEqual((found[0].line, found[0].column), (3, 1))
        self.assertIn("placeholder paragraph", found[0].message)

    def test_rejects_the_paragraph_after_an_edit_of_its_end_or_its_layout(self) -> None:
        bodies = [
            PLACEHOLDER_PARAGRAPH + " This change fixes a unit.",
            "  " + PLACEHOLDER_PARAGRAPH,
            PLACEHOLDER_PARAGRAPH.removesuffix("."),
            "Write two or three sentences of plain prose\nthat say what this change does.",
        ]
        for body in bodies:
            with self.subTest(body=body):
                found = check_squash_message(squash("fix: a unit", body=body))
                self.assertEqual(rules(found), ["TELL-18"])

    def test_accepts_a_body_that_only_mentions_the_words(self) -> None:
        bodies = [
            "The template asks the author to write two or three sentences of plain prose.",
            "The template says: Write two or three sentences of plain prose.",
        ]
        for body in bodies:
            with self.subTest(body=body):
                found = check_squash_message(squash("docs: fix a template", body=body))
                self.assertEqual(found, [])

    def test_rejects_an_empty_closes_line(self) -> None:
        for body in ("Closes #", "closes #", "Closes #   ", "  Closes #"):
            with self.subTest(body=body):
                found = check_squash_message(squash("fix: a unit", body=body))
                self.assertEqual(rules(found), ["TELL-18"])
                self.assertEqual(found[0].line, 3)
                self.assertIn("Closes #", found[0].message)

    def test_accepts_a_closes_line_with_an_issue(self) -> None:
        for body in ("Closes #5", "Closes #5, closes #6", "Fixes #12"):
            with self.subTest(body=body):
                self.assertEqual(check_squash_message(squash("fix: a unit", body=body)), [])


def read_template(name: str) -> str:
    """Read a file of templates/, which the pull request check and the contributors share."""
    return (Path(__file__).resolve().parents[2] / "templates" / name).read_text(encoding="utf-8")


class PullRequestTemplateTest(unittest.TestCase):
    TITLE = "fix: reject a unit of 00 (#7)"

    def test_holds_the_paragraph_the_closes_line_and_the_sign_off_line(self) -> None:
        lines = read_template("PULL_REQUEST_TEMPLATE.md").split("\n")
        self.assertEqual(
            lines,
            [
                PLACEHOLDER_PARAGRAPH,
                "",
                "Closes #",
                "",
                "Signed-off-by: Your Name <you@example.com>",
                "",
            ],
        )

    def test_has_no_heading_checklist_or_html_comment(self) -> None:
        text = read_template("PULL_REQUEST_TEMPLATE.md")
        starts = ("#", "- [", "* [", "<!--")
        self.assertEqual([line for line in text.split("\n") if line.startswith(starts)], [])
        self.assertNotIn("<!--", text)

    def test_holds_the_text_that_the_check_looks_for(self) -> None:
        text = read_template("PULL_REQUEST_TEMPLATE.md")
        self.assertTrue(text.startswith(check_tells.TEMPLATE_PARAGRAPH))
        self.assertIn(check_tells.PLACEHOLDER_ADDRESS, text)
        self.assertIn("Closes #", text.split("\n"))

    def test_fails_the_squash_check_until_the_author_fills_it_in(self) -> None:
        message = f"{self.TITLE}\n\n" + read_template("PULL_REQUEST_TEMPLATE.md")
        found = check_squash_message(message, no_scope=True)
        self.assertEqual(
            sorted((violation.rule, violation.line) for violation in found),
            [("GIT-2", 7), ("TELL-18", 3), ("TELL-18", 5)],
        )

    def test_passes_the_squash_check_once_the_author_fills_it_in(self) -> None:
        template = read_template("PULL_REQUEST_TEMPLATE.md")
        prose = template.replace(PLACEHOLDER_PARAGRAPH, "The parser accepted a unit of 00.")
        named = prose.replace("Your Name <you@example.com>", "Ada Bello <ada@example.org>")
        with_issue = named.replace("Closes #", "Closes #5")
        without_issue = named.replace("Closes #\n\n", "")
        for body in (with_issue, without_issue):
            with self.subTest(body=body):
                found = check_squash_message(f"{self.TITLE}\n\n{body}", no_scope=True)
                self.assertEqual(found, [])


class CommunityTemplatesTest(unittest.TestCase):
    def test_tell_how_to_add_a_missing_sign_off(self) -> None:
        for name in ("CONTRIBUTING.md", "AGENTS.md"):
            with self.subTest(name=name):
                text = read_template(name)
                self.assertIn("git rebase --signoff", text)
                self.assertIn("--force-with-lease", text)
                self.assertNotIn("DCO check", text)
                self.assertNotIn("remediation", text)

    def test_contributing_points_to_no_code_of_conduct(self) -> None:
        text = read_template("CONTRIBUTING.md")
        self.assertNotIn("Conduct", text)
        self.assertNotIn("CONDUCT", text)

    def test_contributing_holds_the_checklist_of_the_pull_request_template(self) -> None:
        section = read_template("CONTRIBUTING.md").partition("## Open a pull request")[2]
        for rule in ("T-1", "DOC-5", "GIT-7", "DOC-7", "TELL-15", "GIT-2"):
            with self.subTest(rule=rule):
                self.assertIn(rule, section)
        self.assertNotIn("[ ]", section)

    def test_contributing_tells_the_author_what_the_title_and_the_body_become(self) -> None:
        section = read_template("CONTRIBUTING.md").partition("## Open a pull request")[2]
        self.assertIn("commit message on `main`", section)
        self.assertIn("Conventional Commits", section)

    def test_agents_names_the_interface_section_of_the_grammar(self) -> None:
        text = read_template("AGENTS.md")
        self.assertIn("grammar, with its Interface section, and the vectors", text)


class RenovateConfigTest(unittest.TestCase):
    # The hosted Renovate app commits as this author, so the body must be signed off as it.
    HOSTED_APP = "Signed-off-by: renovate[bot] <29139614+renovate[bot]@users.noreply.github.com>"

    def config(self) -> dict[str, Any]:
        path = Path(__file__).resolve().parents[2] / "renovate.json"
        config: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return config

    def test_signs_off_each_commit_as_its_author(self) -> None:
        self.assertEqual(self.config()["commitTrailers"], ["Signed-off-by: {{{gitAuthor}}}"])

    def test_signs_off_the_body_as_the_hosted_app(self) -> None:
        self.assertIn(self.HOSTED_APP, self.config()["prBodyNotes"])

    def test_writes_a_body_that_passes_the_squash_check(self) -> None:
        notes = "\n\n".join(self.config()["prBodyNotes"])
        message = f"ci: update an action (#4)\n\n{notes}\n\n{RENOVATE_COMMENT}\n"
        self.assertEqual(check_squash_message(message, no_scope=True), [])
