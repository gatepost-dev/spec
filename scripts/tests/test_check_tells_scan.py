# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for check_tells.scan: files that are not UTF-8, and the range of commits."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import check_tells
from check_tells import Violation, check_signed_off

from tests.check_tells_driver import commit, git, git_repo, rules, run_main
from tests.check_tells_samples import E_ACUTE, EMOJI, NO_BREAK_SPACE, SIGN_OFF_LINE


class FileEncodingTest(unittest.TestCase):
    def check(self, name: str, data: bytes) -> list[Violation]:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            file = root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
            return check_tells.check_files(root, [file])

    def test_reports_a_code_file_that_is_not_utf_8(self) -> None:
        data = b"const a = 1;\nconst b = \x93hi\x94;\nconsole.log(b);\n"
        found = self.check("src/a.ts", data)
        self.assertEqual(rules(found), ["TELL-14"])
        self.assertEqual((found[0].path, found[0].line, found[0].column), ("src/a.ts", 2, 11))
        self.assertEqual(
            found[0].message,
            "Byte 0x93 is not valid UTF-8. "
            "Save the file as UTF-8, and use ASCII in code and config.",
        )

    def test_counts_the_column_of_the_bad_byte_in_characters(self) -> None:
        found = self.check("src/a.ts", f"// caf{E_ACUTE} ".encode() + b"\xff")
        self.assertEqual((found[0].line, found[0].column), (1, 9))

    def test_reports_a_config_file_that_is_not_utf_8(self) -> None:
        found = self.check("package.json", b'{"name": "caf\xe9"}\n')
        self.assertEqual(rules(found), ["TELL-14"])
        self.assertEqual((found[0].line, found[0].column), (1, 14))

    def test_reports_a_script_with_a_shebang_that_is_not_utf_8(self) -> None:
        found = self.check("scripts/run", b'#!/usr/bin/env python3\nx = "caf\xe9"\n')
        self.assertEqual(rules(found), ["TELL-14"])
        self.assertEqual(found[0].line, 2)

    def test_reports_a_file_that_starts_with_a_utf_16_byte_order_mark(self) -> None:
        found = self.check("src/a.ts", b"\xff\xfec\x00")
        self.assertEqual((found[0].line, found[0].column), (1, 1))

    def test_skips_a_file_that_is_not_text(self) -> None:
        names = ["logo.png", "docs/a.md", "src/locales/yo.po", "LICENSE", "font.woff", "go.sum"]
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(self.check(name, b"\x89PNG\r\n\x1a\n\xff\xfe\x00"), [])

    def test_reads_a_file_that_is_utf_8(self) -> None:
        data = f"const a = '{NO_BREAK_SPACE}';\n".encode()
        self.assertEqual(rules(self.check("src/a.ts", data)), ["TELL-14"])
        self.assertEqual(self.check("src/a.ts", b"export const a = 1;\n"), [])


class SignedOffRangeTest(unittest.TestCase):
    def test_reports_each_commit_without_a_sign_off(self) -> None:
        with git_repo() as root:
            base = commit(root, "chore: start")
            signed = commit(root, "feat: a\n\n" + SIGN_OFF_LINE)
            unsigned = commit(root, "fix: b")
            found = check_signed_off(root, f"{base}..HEAD")
        self.assertEqual([(v.path, v.rule) for v in found], [(f"commit {unsigned[:12]}", "GIT-2")])
        self.assertNotIn(signed[:12], str(found))

    def test_accepts_a_range_where_each_commit_has_a_sign_off(self) -> None:
        with git_repo() as root:
            base = commit(root, "chore: start")
            commit(root, "feat: a\n\n" + SIGN_OFF_LINE)
            commit(root, "fix: b\n\nWhy.\n\n" + SIGN_OFF_LINE)
            self.assertEqual(check_signed_off(root, f"{base}..HEAD"), [])

    def test_ignores_the_commits_before_the_range(self) -> None:
        with git_repo() as root:
            commit(root, "chore: start")
            base = commit(root, "chore: second")
            commit(root, "feat: a\n\n" + SIGN_OFF_LINE)
            self.assertEqual(check_signed_off(root, f"{base}..HEAD"), [])

    def test_skips_a_merge_commit(self) -> None:
        with git_repo() as root:
            base = commit(root, "chore: start")
            branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
            git(root, "checkout", "-q", "-b", "topic")
            commit(root, "feat: a\n\n" + SIGN_OFF_LINE)
            git(root, "checkout", "-q", branch)
            commit(root, "fix: b\n\n" + SIGN_OFF_LINE)
            git(
                root, "-c", "commit.gpgsign=false", "merge", "--no-ff", "-q", "-m", "Merge", "topic"
            )
            self.assertEqual(check_signed_off(root, f"{base}..HEAD"), [])

    def test_reads_a_line_that_starts_with_a_hash_as_text(self) -> None:
        with git_repo() as root:
            base = commit(root, "chore: start")
            commit(root, "fix: b\n\n# Signed-off-by: Ada Bello <ada@example.org>")
            self.assertEqual(rules(check_signed_off(root, f"{base}..HEAD")), ["GIT-2"])

    @unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen makes the signing key")
    def test_gives_the_hash_of_a_signed_commit_when_git_shows_signatures(self) -> None:
        with git_repo() as root, tempfile.TemporaryDirectory() as keys:
            key = Path(keys) / "key"
            subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True
            )
            allowed = Path(keys) / "allowed"
            allowed.write_text(f"ada@example.org {key.with_suffix('.pub').read_text()}")
            settings = {
                "gpg.format": "ssh",
                "user.signingkey": str(key),
                "gpg.ssh.allowedSignersFile": str(allowed),
                "log.showSignature": "true",
            }
            for name, value in settings.items():
                git(root, "config", name, value)
            base = commit(root, "chore: start")
            git(root, "commit", "--allow-empty", "-q", "-S", "-m", "fix: b")
            signed = git(root, "rev-parse", "HEAD")
            found = check_signed_off(root, f"{base}..HEAD")
        self.assertEqual([violation.path for violation in found], [f"commit {signed[:12]}"])

    def test_does_not_reject_non_ascii_in_a_commit_message(self) -> None:
        with git_repo() as root:
            base = commit(root, "chore: start")
            commit(root, f"fix: caf{E_ACUTE}\n\n" + SIGN_OFF_LINE)
            self.assertEqual(check_signed_off(root, f"{base}..HEAD"), [])

    def test_does_not_run_the_other_message_rules_on_a_commit(self) -> None:
        with git_repo() as root:
            base = commit(root, "chore: start")
            commit(root, "Update files " + EMOJI + "\n\n" + SIGN_OFF_LINE)
            self.assertEqual(check_signed_off(root, f"{base}..HEAD"), [])

    def test_reads_the_range_from_the_command_line(self) -> None:
        with git_repo() as root:
            base = commit(root, "chore: start")
            unsigned = commit(root, "fix: b")
            status, output, errors = run_main("--root", str(root), "--signed-off", f"{base}..HEAD")
        self.assertEqual((status, errors), (1, ""))
        self.assertEqual(len(output.splitlines()), 1)
        self.assertTrue(output.startswith(f"commit {unsigned[:12]}:1:1: GIT-2 "), output)

    def test_exits_with_0_when_each_commit_has_a_sign_off(self) -> None:
        with git_repo() as root:
            base = commit(root, "chore: start")
            commit(root, "fix: b\n\n" + SIGN_OFF_LINE)
            result = run_main("--root", str(root), "--signed-off", f"{base}..HEAD")
        self.assertEqual(result, (0, "", ""))

    def test_reports_a_range_that_git_cannot_read(self) -> None:
        with git_repo() as root:
            commit(root, "chore: start")
            status, output, errors = run_main("--root", str(root), "--signed-off", "nope..HEAD")
        self.assertEqual((status, output), (2, ""))
        self.assertEqual(len(errors.splitlines()), 1, errors)
        self.assertIn("nope..HEAD", errors)

    def test_does_not_read_a_range_as_an_option(self) -> None:
        with git_repo() as root:
            commit(root, "chore: start")
            status, output, errors = run_main("--root", str(root), "--signed-off=--all")
        self.assertEqual((status, output), (2, ""))
        self.assertEqual(len(errors.splitlines()), 1, errors)
