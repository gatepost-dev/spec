# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for check_tells.command: the options, the exit codes and the output."""

import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import check_tells
from check_tells import Violation

from tests.check_tells_driver import git_repo, run_main
from tests.check_tells_samples import SIGN_OFF_LINE, squash


class CommandTest(unittest.TestCase):
    def test_checks_new_files_and_skips_ignored_ones(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("ignored.ts\n", encoding="utf-8")
            (root / "ignored.ts").write_text("console.log(1);\n", encoding="utf-8")
            (root / "new.ts").write_text("console.log(1);\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = check_tells.main(["--root", str(root)])
            self.assertEqual(status, 1)
            self.assertIn("new.ts:1:1: TELL-13", output.getvalue())
            self.assertNotIn("ignored.ts", output.getvalue())

    def test_exits_with_0_for_a_clean_repo(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "clean.ts").write_text("export const a = 1;\n", encoding="utf-8")
            command = [str(Path(__file__).resolve().parents[1] / "check-tells"), "--root", folder]
            self.assertEqual(subprocess.run(command, check=False).returncode, 0)

    def test_prints_a_violation_like_a_compiler_message(self) -> None:
        violation = Violation("src/a.ts", 3, 101, "TELL-1", "The line is too wide.")
        self.assertEqual(str(violation), "src/a.ts:3:101: TELL-1 The line is too wide.")

    def test_prints_the_violations_in_the_order_of_the_files_and_lines(self) -> None:
        with git_repo() as root:
            (root / "b.ts").write_text("console.log(1);\n\nconsole.log(2);\n", encoding="utf-8")
            (root / "a.ts").write_text("export const a = 1;\nconsole.log(1);\n", encoding="utf-8")
            status, output, errors = run_main("--root", str(root))
        self.assertEqual(status, 1)
        self.assertEqual(errors, "")
        self.assertEqual(
            [line.split(": ")[0] for line in output.splitlines()],
            ["a.ts:2:1", "b.ts:1:1", "b.ts:3:1"],
        )

    def test_skips_a_tracked_file_that_is_missing_from_the_work_tree(self) -> None:
        with git_repo() as root:
            (root / "gone.ts").write_text("console.log(1);\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "gone.ts"], check=True)
            (root / "gone.ts").unlink()
            status, output, errors = run_main("--root", str(root))
        self.assertEqual((status, output, errors), (0, "", ""))

    def test_checks_only_the_paths_that_it_is_given(self) -> None:
        with git_repo() as root:
            (root / "a.ts").write_text("console.log(1);\n", encoding="utf-8")
            (root / "b.ts").write_text("console.log(1);\n", encoding="utf-8")
            status, output, _ = run_main("--root", str(root), "b.ts")
        self.assertEqual(status, 1)
        self.assertEqual(output.splitlines(), ["b.ts:1:1: TELL-13 Remove 'console.log('."])

    def test_exits_with_1_and_names_a_code_file_that_is_not_utf_8(self) -> None:
        with git_repo() as root:
            (root / "a.ts").write_bytes(b"const a = '\x93';\n")
            (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff")
            status, output, errors = run_main("--root", str(root))
        self.assertEqual(status, 1)
        self.assertEqual(errors, "")
        self.assertEqual(len(output.splitlines()), 1)
        self.assertIn("a.ts:1:12: TELL-14 Byte 0x93 is not valid UTF-8.", output)


class BadInputTest(unittest.TestCase):
    def assert_one_line_on_stderr(self, result: tuple[int, str, str], *words: str) -> None:
        status, output, errors = result
        self.assertEqual(status, 2)
        self.assertEqual(output, "")
        self.assertEqual(len(errors.splitlines()), 1, errors)
        self.assertTrue(errors.startswith("check-tells: "), errors)
        for word in words:
            self.assertIn(word, errors)

    def test_reports_a_root_that_is_not_a_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            # Stop git from finding a repo above the temporary folder.
            with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(root.parent)}):
                result = run_main("--root", str(root))
        self.assert_one_line_on_stderr(result, str(root), "not a git repository")

    def test_reports_a_root_that_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder).resolve() / "missing"
            result = run_main("--root", str(missing))
        self.assert_one_line_on_stderr(result, str(missing))

    def test_reports_a_path_that_does_not_exist(self) -> None:
        with git_repo() as root:
            result = run_main("--root", str(root), "missing.ts")
        self.assert_one_line_on_stderr(result, "missing.ts", "No such file")

    def test_reports_a_path_that_is_a_folder(self) -> None:
        with git_repo() as root:
            (root / "src").mkdir()
            result = run_main("--root", str(root), "src")
        self.assert_one_line_on_stderr(result, "src", "directory")

    def test_reports_a_path_outside_the_root(self) -> None:
        with git_repo() as root, tempfile.TemporaryDirectory() as other:
            outside = Path(other).resolve() / "a.ts"
            outside.write_text("console.log(1);\n", encoding="utf-8")
            absolute = run_main("--root", str(root), str(outside))
            relative = run_main("--root", str(root), "../" + outside.parent.name + "/a.ts")
        self.assert_one_line_on_stderr(absolute, str(outside), "outside the root")
        self.assert_one_line_on_stderr(relative, "outside the root")

    def test_reports_a_commit_message_file_that_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "message"
            result = run_main("--commit-msg", str(missing))
        self.assert_one_line_on_stderr(result, str(missing), "No such file")

    def test_reports_a_commit_message_that_is_not_utf_8(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            message = Path(folder) / "message"
            message.write_bytes(b"fix: parse caf\xe9\n")
            status, output, errors = run_main("--commit-msg", str(message))
        self.assertEqual((status, errors), (1, ""))
        self.assertIn("commit message:1:15: TELL-14 Byte 0xE9 is not valid UTF-8.", output)

    def test_prints_no_traceback_from_the_command(self) -> None:
        command = [str(Path(__file__).resolve().parents[1] / "check-tells")]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            environment = {**os.environ, "GIT_CEILING_DIRECTORIES": str(root.parent)}
            run = subprocess.run(
                [*command, "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")
        self.assertNotIn("Traceback", run.stderr)
        self.assertEqual(len(run.stderr.splitlines()), 1)


class SquashCommandTest(unittest.TestCase):
    def run_with_message(self, text: str, *options: str) -> tuple[int, str, str]:
        with tempfile.TemporaryDirectory() as folder:
            message = Path(folder) / "message"
            message.write_text(text, encoding="utf-8")
            return run_main("--squash-msg", str(message), *options)

    def test_exits_with_0_for_a_good_message(self) -> None:
        result = self.run_with_message(squash("fix: reject a unit (#7)"), "--no-scope")
        self.assertEqual(result, (0, "", ""))

    def test_exits_with_1_and_prints_each_problem(self) -> None:
        status, output, errors = self.run_with_message("Update files\n\nBody\n")
        self.assertEqual((status, errors), (1, ""))
        self.assertEqual(
            [line.split(" ")[:3] for line in output.splitlines()],
            [["commit", "message:1:1:", "GIT-1"], ["commit", "message:1:1:", "GIT-2"]],
        )

    def test_rejects_a_scope_only_with_the_no_scope_option(self) -> None:
        message = squash("fix(core): reject a unit (#7)")
        self.assertEqual(self.run_with_message(message), (0, "", ""))
        status, output, _ = self.run_with_message(message, "--no-scope")
        self.assertEqual(status, 1)
        self.assertIn("commit message:1:4: GIT-1 Remove the scope (core).", output)

    def test_reads_a_squash_message_that_is_not_utf_8(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            message = Path(folder) / "message"
            message.write_bytes(b"fix: parse caf\xe9\n\n" + SIGN_OFF_LINE.encode() + b"\n")
            status, output, _ = run_main("--squash-msg", str(message))
        self.assertEqual(status, 1)
        self.assertIn("commit message:1:15: TELL-14 Byte 0xE9 is not valid UTF-8.", output)

    def test_reports_a_squash_message_file_that_does_not_exist(self) -> None:
        status, output, errors = run_main("--squash-msg", "no-such-file")
        self.assertEqual((status, output), (2, ""))
        self.assertEqual(len(errors.splitlines()), 1)

    def test_asks_for_a_squash_message_when_it_gets_the_no_scope_option(self) -> None:
        errors = io.StringIO()
        with self.assertRaises(SystemExit) as caught, contextlib.redirect_stderr(errors):
            check_tells.main(["--no-scope"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("--no-scope needs --squash-msg", errors.getvalue())

    def test_reads_one_kind_of_message_at_a_time(self) -> None:
        for options in (
            ["--commit-msg", "a", "--squash-msg", "b"],
            ["--commit-msg", "a", "--signed-off", "b..c"],
            ["--squash-msg", "a", "--signed-off", "b..c"],
        ):
            with self.subTest(options=options):
                errors = io.StringIO()
                with self.assertRaises(SystemExit) as caught, contextlib.redirect_stderr(errors):
                    check_tells.main(options)
                self.assertEqual(caught.exception.code, 2)
