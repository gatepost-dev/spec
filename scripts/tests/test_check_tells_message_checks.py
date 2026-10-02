# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for check_tells.message_checks: commit messages and squash messages."""

import unittest

from check_tells import check_commit_message, check_squash_message

from tests.check_tells_driver import rules
from tests.check_tells_samples import (
    E_ACUTE,
    EM_DASH,
    EMOJI,
    LINE_SEPARATOR,
    PLACEHOLDER_PARAGRAPH,
    RENOVATE_COMMENT,
    SIGN_OFF_LINE,
    squash,
)

COMMIT_TYPES = (
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
)


class CommitMessageTest(unittest.TestCase):
    def test_accepts_a_good_message(self) -> None:
        message = "fix(core): reject a unit of 00\n\nThe spec forbids 00.\n"
        self.assertEqual(check_commit_message(message), [])

    def test_rejects_a_long_subject(self) -> None:
        self.assertEqual(rules(check_commit_message("fix: " + "a" * 70)), ["TELL-18"])

    def test_accepts_a_subject_of_72_characters(self) -> None:
        self.assertEqual(check_commit_message("a" * 72), [])

    def test_rejects_a_subject_of_73_characters(self) -> None:
        found = check_commit_message("a" * 73)
        self.assertEqual(rules(found), ["TELL-18"])
        self.assertEqual(found[0].column, 73)
        self.assertEqual(found[0].message, "The subject has 73 characters. Use 72 or fewer.")

    def test_reads_the_subject_after_blank_lines(self) -> None:
        found = check_commit_message("\n\n" + "a" * 73 + "\n\n" + "b" * 80)
        self.assertEqual([(v.rule, v.line) for v in found], [("TELL-18", 3)])

    def test_rejects_an_emoji(self) -> None:
        self.assertEqual(rules(check_commit_message(f"fix: parse codes {EMOJI}")), ["TELL-14"])

    def test_accepts_an_accented_name_in_a_sign_off(self) -> None:
        message = f"fix: parse codes\n\nSigned-off-by: Ad{E_ACUTE} Bello <a@example.com>\n"
        self.assertEqual(check_commit_message(message), [])

    def test_ignores_git_comment_lines(self) -> None:
        self.assertEqual(check_commit_message(f"fix: parse codes\n# {EMOJI} from git\n"), [])

    def test_accepts_the_last_ascii_character_in_a_commit_message(self) -> None:
        self.assertEqual(check_commit_message("fix: a" + chr(0x7F)), [])
        self.assertEqual(rules(check_commit_message("fix: a" + chr(0x80))), ["TELL-14"])

    def test_rejects_non_ascii_in_a_subject(self) -> None:
        self.assertEqual(rules(check_commit_message("fix: parse caf" + E_ACUTE)), ["TELL-14"])

    def test_rejects_non_ascii_in_a_body_but_not_in_a_sign_off(self) -> None:
        message = (
            "fix: parse codes\n\n"
            f"Use a dash {EM_DASH} here.\n\n"
            f"Signed-off-by: Ad{E_ACUTE} Bello <a@example.com>\n"
        )
        found = check_commit_message(message)
        self.assertEqual(rules(found), ["TELL-14"])
        self.assertEqual(found[0].line, 3)

    def test_reads_a_sign_off_without_regard_to_case(self) -> None:
        message = f"fix: parse codes\n\nCo-Authored-By: Ad{E_ACUTE} Bello <a@example.com>"
        self.assertEqual(check_commit_message(message), [])

    def test_stops_at_the_scissors_line(self) -> None:
        scissors = "# ------------------------ >8 ------------------------"
        message = f"fix: parse codes\n{scissors}\n+    caf{E_ACUTE}"
        self.assertEqual(check_commit_message(message), [])

    def test_reports_the_real_line_of_a_character(self) -> None:
        found = check_commit_message(f"# c1\n# c2\nfix: caf{E_ACUTE}")
        self.assertEqual(rules(found), ["TELL-14"])
        self.assertEqual(found[0].line, 3)

    def test_reports_the_real_line_of_a_long_subject(self) -> None:
        found = check_commit_message("# note\nfix: " + "a" * 70)
        self.assertEqual(rules(found), ["TELL-18"])
        self.assertEqual(found[0].line, 2)

    def test_keeps_a_line_separator_in_a_commit_message(self) -> None:
        found = check_commit_message("fix: a\n\nb" + LINE_SEPARATOR + "c")
        self.assertEqual([(v.rule, v.line) for v in found], [("TELL-14", 3)])


class ConventionalSubjectTest(unittest.TestCase):
    def test_accepts_each_commit_type(self) -> None:
        for kind in COMMIT_TYPES:
            with self.subTest(kind=kind):
                self.assertEqual(check_squash_message(squash(f"{kind}: reject a unit")), [])

    def test_accepts_a_mark_for_a_breaking_change(self) -> None:
        self.assertEqual(check_squash_message(squash("feat!: drop the old name (#4)")), [])

    def test_rejects_a_subject_that_does_not_follow_the_form(self) -> None:
        subjects = [
            "Foundation: standards and grammar (#1)",
            "Fix: reject a unit",
            "fix:reject a unit",
            "fix : reject a unit",
            "fix(): reject a unit",
            "fix",
            "fix: ",
            "Update files",
            ": reject a unit",
            "fix(core:) reject a unit",
        ]
        for subject in subjects:
            with self.subTest(subject=subject):
                found = check_squash_message(squash(subject))
                self.assertEqual(rules(found), ["GIT-1"])
                self.assertEqual((found[0].line, found[0].column), (1, 1))
                self.assertIn("does not follow Conventional Commits", found[0].message)

    def test_rejects_a_type_that_conventional_commits_does_not_list(self) -> None:
        for kind in ("update", "feature", "bugfix", "wip", "chores"):
            with self.subTest(kind=kind):
                found = check_squash_message(squash(f"{kind}: reject a unit"))
                self.assertEqual(rules(found), ["GIT-1"])
                self.assertIn(f"'{kind}' is not a Conventional Commits type", found[0].message)

    def test_names_each_type_that_it_accepts(self) -> None:
        found = check_squash_message(squash("update: reject a unit"))
        self.assertIn(
            "build, chore, ci, docs, feat, fix, perf, refactor, revert, style or test",
            found[0].message,
        )

    def test_accepts_a_scope_unless_the_repo_has_none(self) -> None:
        self.assertEqual(check_squash_message(squash("fix(core): reject a unit")), [])
        self.assertEqual(check_squash_message(squash("fix(core)!: reject a unit")), [])

    def test_rejects_a_scope_in_a_repo_that_has_none(self) -> None:
        for subject in ("fix(core): reject a unit", "feat(deps)!: drop a name"):
            with self.subTest(subject=subject):
                found = check_squash_message(squash(subject), no_scope=True)
                self.assertEqual(rules(found), ["GIT-1"])
                self.assertEqual((found[0].line, found[0].column), (1, subject.index("(") + 1))
                self.assertIn("Remove the scope", found[0].message)

    def test_accepts_a_subject_without_a_scope_in_a_repo_that_has_none(self) -> None:
        self.assertEqual(check_squash_message(squash("fix: reject a unit"), no_scope=True), [])

    def test_rejects_a_message_that_has_no_subject(self) -> None:
        found = check_squash_message("\n  \n")
        self.assertEqual(sorted(rules(found)), ["GIT-1", "GIT-2"])
        self.assertEqual(found[0].message, "The message has no subject.")

    def test_rejects_the_default_squash_subject_of_a_pull_request_with_no_type(self) -> None:
        title = "Foundation: standards, grammar, data, shared vectors and check-tells (#1)"
        found = check_squash_message(squash(title), no_scope=True)
        self.assertEqual(sorted(rules(found)), ["GIT-1", "TELL-18"])

    def test_reads_the_first_line_that_has_text_as_the_subject(self) -> None:
        found = check_squash_message("\n\nupdate: x\n\nbody\n\n" + SIGN_OFF_LINE)
        self.assertEqual([(v.rule, v.line) for v in found], [("GIT-1", 3)])


class SquashMessageTest(unittest.TestCase):
    def test_accepts_a_good_message(self) -> None:
        message = (
            "fix: reject a unit of 00 (#7)\n\n"
            "The parser accepted a unit of 00. It now returns bad_segment.\n\n"
            "Closes #5\n\n" + SIGN_OFF_LINE + "\n"
        )
        self.assertEqual(check_squash_message(message, no_scope=True), [])

    def test_counts_the_suffix_that_the_merge_adds_to_the_title(self) -> None:
        self.assertEqual(check_squash_message(squash("fix: " + "a" * 62 + " (#7)")), [])
        found = check_squash_message(squash("fix: " + "a" * 63 + " (#7)"))
        self.assertEqual(rules(found), ["TELL-18"])
        self.assertEqual(found[0].column, 73)
        self.assertIn("The subject has 73 characters. Use 72 or fewer.", found[0].message)
        self.assertIn("(#N)", found[0].message)

    def test_reads_a_line_that_starts_with_a_hash_as_text(self) -> None:
        body = f"## Notes {EMOJI}\n# {EM_DASH} here"
        found = check_squash_message(squash("fix: reject a unit", body=body))
        self.assertEqual([(v.rule, v.line) for v in found], [("TELL-14", 3), ("TELL-14", 4)])

    def test_reads_a_line_that_starts_with_a_hash_as_a_comment_in_a_commit_file(self) -> None:
        message = f"fix: reject a unit\n\n## Notes {EMOJI}\n"
        self.assertEqual(check_commit_message(message), [])

    def test_rejects_non_ascii_in_the_body_but_not_in_a_sign_off(self) -> None:
        found = check_squash_message(squash("fix: a unit", body=f"Use a dash {EM_DASH} here."))
        self.assertEqual([(v.rule, v.line) for v in found], [("TELL-14", 3)])
        sign_off = f"Signed-off-by: Ad{E_ACUTE} Bello <ada@example.org>"
        self.assertEqual(check_squash_message(squash("fix: a unit", sign_off=sign_off)), [])

    def test_treats_crlf_like_lf(self) -> None:
        message = squash("fix: reject a unit (#7)", body="Closes #5").replace("\n", "\r\n")
        self.assertEqual(check_squash_message(message), [])

    def test_reports_every_problem_once(self) -> None:
        message = "Update files\n\n" + PLACEHOLDER_PARAGRAPH + "\n\nCloses #\n"
        found = check_squash_message(message)
        self.assertEqual(sorted(rules(found)), ["GIT-1", "GIT-2", "TELL-18", "TELL-18"])


class HtmlCommentTest(unittest.TestCase):
    def test_leaves_out_the_comment_that_renovate_ends_a_body_with(self) -> None:
        message = squash("ci: update an action (#4)", body="Update a pinned tool or action.")
        self.assertEqual(check_squash_message(message + RENOVATE_COMMENT + "\n"), [])

    def test_reads_the_comment_of_renovate_when_text_follows_it(self) -> None:
        body = f"{RENOVATE_COMMENT} {EM_DASH} here."
        found = check_squash_message(squash("ci: update an action (#4)", body=body))
        self.assertEqual(
            [(v.rule, v.line, v.column) for v in found],
            [("TELL-14", 3, len(RENOVATE_COMMENT) + 2)],
        )

    def test_reads_a_comment_that_starts_like_the_one_of_renovate_but_holds_other_text(
        self,
    ) -> None:
        payloads = ((EMOJI, EMOJI), (f"a dash {EM_DASH}", EM_DASH), (E_ACUTE, E_ACUTE))
        for payload, character in payloads:
            with self.subTest(payload=payload):
                comment = f"<!--renovate-debug:{payload}-->"
                message = squash("ci: update an action (#4)") + comment + "\n"
                found = check_squash_message(message)
                self.assertEqual(
                    [(v.rule, v.line, v.column) for v in found],
                    [("TELL-14", 6, comment.index(character) + 1)],
                )

    def test_leaves_out_the_comment_of_renovate_so_that_no_text_is_left(self) -> None:
        # The title line is empty, so the first line with text would be the comment.
        found = check_squash_message("\n" + RENOVATE_COMMENT + "\n")
        self.assertEqual(found[0].message, "The message has no subject.")

    def test_leaves_out_the_comment_of_renovate_when_ascii_white_space_follows_it(self) -> None:
        for tail in ("", " ", "\t", "\n", "\r\n", " \t\r\n\n"):
            with self.subTest(tail=tail):
                found = check_squash_message("\n" + RENOVATE_COMMENT + tail)
                self.assertEqual(found[0].message, "The message has no subject.")

    def test_reads_the_comment_of_renovate_when_non_ascii_white_space_follows_it(self) -> None:
        # \s matches each of these, so a pattern that ends in \s* hides them from TELL-14.
        for code_point in (0x3000, 0x2028, 0x00A0, 0x0085, 0x2003):
            with self.subTest(code_point=f"U+{code_point:04X}"):
                message = squash("ci: update an action (#4)")
                found = check_squash_message(message + RENOVATE_COMMENT + chr(code_point) + "\n")
                self.assertEqual(
                    [(v.rule, v.line, v.column) for v in found],
                    [("TELL-14", 6, len(RENOVATE_COMMENT) + 1)],
                )

    def test_reads_the_text_that_a_comment_holds(self) -> None:
        for text, character in ((EMOJI, EMOJI), (f"a dash {EM_DASH} here", EM_DASH)):
            with self.subTest(text=text):
                comment = f"<!-- {text} -->"
                body = f"Why the change is needed.\n\n{comment}"
                found = check_squash_message(squash("fix: a unit", body=body))
                self.assertEqual(
                    [(v.rule, v.line, v.column) for v in found],
                    [("TELL-14", 5, comment.index(character) + 1)],
                )

    def test_reads_a_comment_that_spans_lines(self) -> None:
        body = f"Why the change is needed.\n\n<!--\nClose the issue.\n{EMOJI}\nCloses #\n-->"
        found = check_squash_message(squash("fix: a unit", body=body))
        self.assertEqual([(v.rule, v.line) for v in found], [("TELL-14", 7), ("TELL-18", 8)])

    def test_keeps_the_place_of_the_text_around_a_comment(self) -> None:
        body = f"Use a dash <!-- a\nb --> {EM_DASH} here."
        found = check_squash_message(squash("fix: a unit", body=body))
        self.assertEqual([(v.rule, v.line, v.column) for v in found], [("TELL-14", 4, 7)])

    def test_reports_the_first_bad_character_of_a_line_with_comments(self) -> None:
        body = f"Fix <!-- {EMOJI} --> the {EM_DASH} unit <!-- {EMOJI} --> rule."
        found = check_squash_message(squash("fix: a unit", body=body))
        self.assertEqual(
            [(v.rule, v.line, v.column) for v in found], [("TELL-14", 3, body.index(EMOJI) + 1)]
        )

    def test_does_not_count_a_sign_off_that_a_comment_holds(self) -> None:
        body = f"Why the change is needed.\n\n<!-- {SIGN_OFF_LINE} -->"
        found = check_squash_message(f"fix: a unit\n\n{body}\n")
        self.assertEqual(rules(found), ["GIT-2"])
        self.assertIn("The message has no Signed-off-by line.", found[0].message)

    def test_reads_a_comment_that_does_not_end_as_text(self) -> None:
        body = f"Why the change is needed.\n\n<!-- {EMOJI}"
        found = check_squash_message(squash("fix: a unit", body=body))
        self.assertEqual([(v.rule, v.line) for v in found], [("TELL-14", 5)])

    def test_reads_a_comment_in_the_title_as_text(self) -> None:
        found = check_squash_message(squash(f"fix: a unit <!-- {EMOJI} -->"))
        self.assertEqual([(v.rule, v.line) for v in found], [("TELL-14", 1)])

    def test_reads_a_comment_in_a_message_with_crlf(self) -> None:
        body = f"Why the change is needed.\n\n<!--\n{EMOJI}\n-->"
        message = squash("fix: a unit", body=body).replace("\n", "\r\n")
        found = check_squash_message(message)
        self.assertEqual([(v.rule, v.line, v.column) for v in found], [("TELL-14", 6, 1)])

    def test_leaves_out_nothing_in_a_commit_message_file(self) -> None:
        message = f"fix: a unit\n\n<!-- {EMOJI} -->\n"
        self.assertEqual(rules(check_commit_message(message)), ["TELL-14"])
