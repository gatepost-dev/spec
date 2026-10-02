# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for check_tells."""

import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import check_tells
from check_tells import (
    Violation,
    check_commit_message,
    check_signed_off,
    check_squash_message,
    check_text,
    classify,
)

EMOJI = chr(0x1F600)
NO_BREAK_SPACE = chr(0x00A0)
E_ACUTE = chr(0x00E9)
EM_DASH = chr(0x2014)
LINE_SEPARATOR = chr(0x2028)
O_DOT_BELOW = chr(0x1ECD)
LONG_LINE = "x" * 150
# Built from two parts, so that this file passes its own to-do check.
TO_DO = "TO" + "DO"
FIX_ME = "FIX" + "ME"
# Built from two parts, so that this file passes its own skip check.
SKIP_MARKER = "check-tells: " + "allow"

# The ranges are typed out here, not read from check_tells, so that a change to them fails.
EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),
    (0x231A, 0x231B),
    (0x23E9, 0x23F3),
    (0x2600, 0x27BF),
    (0x2B00, 0x2BFF),
    (0xFE0F, 0xFE0F),
)
# The debug calls that each language file lists under TELL-13, one sample line for each call.
DEBUG_LINES = {
    "src/a.ts": ["console.log(x);", "console.debug(x);", "console.dir(x);", "debugger;"],
    "src/a.php": [
        "var_dump($x);",
        "print_r($x);",
        "var_export($x);",
        "dd($x);",
        "dump($x);",
        "error_log($x);",
        "debug_print_backtrace();",
    ],
    "pkg/a.py": ["print(x)", "pprint(x)", "breakpoint()", "pdb.set_trace()"],
    "a.go": [
        "fmt.Print(x)",
        "fmt.Printf(x)",
        "fmt.Println(x)",
        "log.Print(x)",
        "log.Printf(x)",
        "log.Println(x)",
        "log.Fatal(x)",
        "log.Fatalf(x)",
        "log.Fatalln(x)",
        "log.Panic(x)",
        "log.Panicf(x)",
        "log.Panicln(x)",
        "print(x)",
        "println(x)",
    ],
    "src/A.kt": [
        "println(x)",
        "print(x)",
        "System.out.println(x)",
        "System.err.println(x)",
        "error.printStackTrace()",
        "Log.v(TAG, x)",
        "Log.d(TAG, x)",
        "Log.i(TAG, x)",
        "Log.w(TAG, x)",
        "Log.e(TAG, x)",
        "Log.wtf(TAG, x)",
    ],
    "src/A.java": ["System.out.println(x);", "System.err.println(x);", "error.printStackTrace();"],
    "src/A.cs": [
        "Console.Write(x);",
        "Console.WriteLine(x);",
        "Debug.WriteLine(x);",
        "Trace.WriteLine(x);",
    ],
    "lib/a.dart": ["print(x);", "debugPrint(x);"],
    "Sources/A.swift": ["print(x)", "debugPrint(x)", "dump(x)", "NSLog(x)"],
}
# One debug call for each file extension that has a language.
DEBUG_LINE_BY_EXTENSION = {
    ".ts": "console.log(x);",
    ".tsx": "console.log(x);",
    ".mts": "console.log(x);",
    ".cts": "console.log(x);",
    ".js": "console.log(x);",
    ".jsx": "console.log(x);",
    ".mjs": "console.log(x);",
    ".cjs": "console.log(x);",
    ".vue": "console.log(x);",
    ".svelte": "console.log(x);",
    ".astro": "console.log(x);",
    ".php": "var_dump($x);",
    ".py": "print(x)",
    ".go": "fmt.Println(x)",
    ".kt": "println(x)",
    ".kts": "println(x)",
    ".java": "System.out.println(x);",
    ".cs": "Console.WriteLine(x);",
    ".dart": "debugPrint(x);",
    ".swift": "NSLog(x)",
}
# Calls that look like a debug call but are not one.
HARMLESS_LINES = {
    "pkg/a.py": ["report.print(x)", "pprint_table(x)", "self.breakpoint(x)", "sprint(x)"],
    "src/a.ts": ["myconsole.log(x);", "console.logs(x);", "console.warn(x);"],
    "src/a.php": ["$this->dump($x);", "Debug::dump($x);", "my_dump($x);", "$dd($x);"],
    "a.go": ["report.Print(x)", "sprint(x)", "s.println(x)"],
    "src/A.kt": ["report.print(x)", "logPrint(x)"],
    "src/A.cs": ["Logger.WriteLine(x);"],
    "lib/a.dart": ["report.print(x);", "sprint(x);"],
    "Sources/A.swift": ["report.print(x)", "sprint(x)"],
}
# Every file name that check-tells must read as a test file, each with the language's debug call.
TEST_FILES = {
    "test/a.ts": "console.log(x);",
    "tests/a.ts": "console.log(x);",
    "src/__tests__/a.ts": "console.log(x);",
    "src/testdata/a.ts": "console.log(x);",
    "testdata/a.go": "fmt.Println(x)",
    "pkg/testdata/a.go": "fmt.Println(x)",
    "Tests/A.cs": "Console.WriteLine(x);",
    "a.test.ts": "console.log(x);",
    "a.spec.ts": "console.log(x);",
    "a.test.tsx": "console.log(x);",
    "a.test.js": "console.log(x);",
    "a.test.jsx": "console.log(x);",
    "a.test.mjs": "console.log(x);",
    "a.test.cjs": "console.log(x);",
    "a.test.mts": "console.log(x);",
    "a.test.cts": "console.log(x);",
    "a_test.go": "fmt.Println(x)",
    "a_test.dart": "debugPrint(x);",
    "test_a.py": "print(x)",
    "src/ATest.kt": "println(x)",
    "src/ATests.kt": "println(x)",
    "src/ATest.java": "System.out.println(x);",
    "src/ATests.java": "System.out.println(x);",
    "src/ATest.cs": "Console.WriteLine(x);",
    "src/ATests.cs": "Console.WriteLine(x);",
    "Sources/ATest.swift": "dump(x)",
    "Sources/ATests.swift": "dump(x)",
}
# File names that look like test files but are not.
NON_TEST_FILES = {
    "src/latest/a.ts": "console.log(x);",
    "src/contest.ts": "console.log(x);",
    "src/a_test.ts": "console.log(x);",
    "src/a.testing.ts": "console.log(x);",
    "src/Latest.kt": "println(x)",
    "src/test.py": "print(x)",
    "src/testdata.py": "print(x)",
}
# A line that breaks each rule that a skip comment can skip.
SKIP_SAMPLES = {
    "TELL-1": ("src/a.ts", LONG_LINE),
    "TELL-13": ("src/a.ts", "console.log(x);"),
    "TELL-14": ("src/a.ts", f"const a = '{NO_BREAK_SPACE}';"),
    "CS-6": ("src/a.ts", f"// {TO_DO}: x"),
}
KIND_BY_PATH = {
    "code": [
        "a.ts",
        "a.tsx",
        "a.mts",
        "a.cts",
        "a.js",
        "a.jsx",
        "a.mjs",
        "a.cjs",
        "a.php",
        "a.py",
        "a.go",
        "a.kt",
        "a.kts",
        "a.java",
        "a.cs",
        "a.dart",
        "a.swift",
        "a.sql",
        "a.sh",
        "a.bash",
        "a.css",
        "a.scss",
        "a.html",
        "a.astro",
        "a.vue",
        "a.svelte",
        "A.TS",
        "config.php.dist",
    ],
    "config": [
        "a.json",
        "a.yml",
        "a.yaml",
        "a.toml",
        "a.xml",
        "a.ini",
        "a.cfg",
        "a.properties",
        "a.gradle",
        "a.neon",
        "a.json5",
        "a.jsonc",
        "A.JSON",
        "phpunit.xml.dist",
        "phpstan.neon.dist",
        "phpstan.dist.neon",
        "Makefile",
        "Dockerfile",
        ".editorconfig",
        ".gitignore",
        ".gitattributes",
        ".npmrc",
    ],
    "prose": ["a.md", "a.mdx", "A.MD"],
    "catalogue": [
        "a.arb",
        "a.po",
        "a.xlf",
        "a.xliff",
        "a.strings",
        "a.stringsdict",
        "src/locales/en.json",
        "src/i18n/en.json",
        "src/l10n/en.json",
        "src/messages/en.json",
        "src/locales/yo/home.json",
        "res/values/strings.xml",
        "res/values-yo/strings.xml",
    ],
    "exempt": [
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
        "composer.lock",
        "go.sum",
        "uv.lock",
        "poetry.lock",
        "Cargo.lock",
        "Package.resolved",
        "pubspec.lock",
        "gradle.lockfile",
        "packages.lock.json",
        "a.svg",
        "a.lock",
        "a.csv",
        "a.txt",
        "a.api",
        "a.snap",
        "a.png",
        "a.jpg",
        "a.ico",
        "src/locales/yo.txt",
    ],
    "other": ["LICENSE", "CODEOWNERS", ".gitmodules", "a.woff", "res/layout/strings.xml.bak"],
}
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


SIGN_OFF_LINE = "Signed-off-by: Ada Bello <ada@example.org>"
PLACEHOLDER_PARAGRAPH = (
    "Write two or three sentences of plain prose that say what this change does and why."
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
# A host with a signing key in its git config must not sign the commits of these tests.
GIT_ENVIRONMENT = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_AUTHOR_NAME": "Ada Bello",
    "GIT_AUTHOR_EMAIL": "ada@example.org",
    "GIT_COMMITTER_NAME": "Ada Bello",
    "GIT_COMMITTER_EMAIL": "ada@example.org",
}


def rules(violations: list[Violation]) -> list[str]:
    return [violation.rule for violation in violations]


@contextlib.contextmanager
def git_repo() -> Iterator[Path]:
    """Make an empty git repo in a temporary folder and give its resolved path."""
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder).resolve()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        yield root


def git(root: Path, *args: str) -> str:
    """Run git in a test repo and give its standard output."""
    run = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **GIT_ENVIRONMENT},
    )
    return run.stdout.strip()


def commit(root: Path, message: str) -> str:
    """Make an empty commit and give its hash."""
    git(root, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def squash(
    subject: str, body: str = "Why the change is needed.", sign_off: str = SIGN_OFF_LINE
) -> str:
    """Build a squash merge message from a title with its suffix, a body and a sign-off."""
    return f"{subject}\n\n{body}\n\n{sign_off}\n"


def run_main(*args: str) -> tuple[int, str, str]:
    """Run the command line and give the exit code, the standard output and the error output."""
    output, errors = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        status = check_tells.main(list(args))
    return status, output.getvalue(), errors.getvalue()


class LineLengthTest(unittest.TestCase):
    def test_accepts_a_line_of_100_characters(self) -> None:
        self.assertEqual(check_text("src/a.ts", "x" * 100), [])

    def test_rejects_a_line_of_101_characters(self) -> None:
        found = check_text("src/a.ts", "x" * 101)
        self.assertEqual(rules(found), ["TELL-1"])
        self.assertEqual(found[0].column, 101)

    def test_counts_a_tab_as_4_columns(self) -> None:
        self.assertEqual(check_text("Makefile", "\t" + "x" * 96), [])
        self.assertEqual(rules(check_text("Makefile", "\t" + "x" * 97)), ["TELL-1"])
        self.assertEqual(check_text("Makefile", "\t\t" + "x" * 92), [])
        self.assertEqual(rules(check_text("Makefile", "\t\t" + "x" * 93)), ["TELL-1"])

    def test_skips_a_line_with_a_url(self) -> None:
        for scheme in ("https", "http"):
            with self.subTest(scheme=scheme):
                line = f"// {scheme}://example.com/" + "a" * 100
                self.assertEqual(check_text("src/a.ts", line), [])

    def test_skips_markdown_lockfiles_and_vectors(self) -> None:
        self.assertEqual(check_text("README.md", "word " * 40), [])
        self.assertEqual(check_text("pnpm-lock.yaml", "x" * 150), [])
        self.assertEqual(check_text("vectors/parse.json", "x" * 150), [])

    def test_skips_json_in_a_data_folder(self) -> None:
        self.assertEqual(check_text("data/states.json", "x" * 150), [])
        self.assertEqual(check_text("vectors/parse.json", "x" * 150), [])
        self.assertEqual(check_text("spec/vectors/parse.json", "x" * 150), [])
        self.assertEqual(check_text("spec/data/format.json", "x" * 150), [])

    def test_checks_other_files_in_a_data_folder(self) -> None:
        self.assertEqual(rules(check_text("data/rules.yml", "x" * 150)), ["TELL-1"])
        self.assertEqual(rules(check_text("vectors/build.py", "x" * 150)), ["TELL-1"])
        self.assertEqual(rules(check_text("package.json", "x" * 150)), ["TELL-1"])
        self.assertEqual(rules(check_text("database/rules.json", "x" * 150)), ["TELL-1"])

    def test_skips_a_message_catalogue(self) -> None:
        line = '{"title": "' + "x" * 150 + '"}'
        self.assertEqual(check_text("src/locales/en.json", line), [])

    def test_skips_a_generated_file(self) -> None:
        text = "// @generated by a script\n" + "x" * 150
        self.assertEqual(check_text("src/spec-data.ts", text), [])

    def test_skips_files_that_other_tools_generate(self) -> None:
        cases = {
            "src/A.cs": "// <auto-generated/>\n",
            "lib/a.g.dart": "// GENERATED CODE - DO NOT MODIFY BY HAND\n",
        }
        for path, header in cases.items():
            with self.subTest(path=path):
                self.assertEqual(check_text(path, header + "x" * 150), [])

    def test_honours_a_skip_with_a_reason(self) -> None:
        line = "x" * 120 + "  // check-tells: allow TELL-1 because the regex cannot be split"
        self.assertEqual(check_text("src/a.ts", line), [])

    def test_checks_each_code_and_config_kind(self) -> None:
        for kind in ("code", "config"):
            for path in KIND_BY_PATH[kind]:
                with self.subTest(path=path):
                    self.assertEqual(rules(check_text(path, LONG_LINE)), ["TELL-1"])

    def test_leaves_every_other_kind_alone(self) -> None:
        for kind in ("prose", "catalogue", "exempt", "other"):
            for path in KIND_BY_PATH[kind]:
                with self.subTest(path=path):
                    self.assertEqual(check_text(path, LONG_LINE), [])

    def test_reads_a_marker_in_the_first_5_lines_of_a_file(self) -> None:
        for marker in ("@generated", "DO NOT EDIT", "<auto-generated", "GENERATED CODE"):
            for marker_line in (1, 5):
                with self.subTest(marker=marker, line=marker_line):
                    text = "\n" * (marker_line - 1) + f"// {marker}\n{LONG_LINE}"
                    self.assertEqual(check_text("src/a.ts", text), [])

    def test_ignores_a_marker_after_the_first_5_lines(self) -> None:
        for marker in ("@generated", "DO NOT EDIT", "<auto-generated", "GENERATED CODE"):
            with self.subTest(marker=marker):
                text = "\n" * 5 + f"// {marker}\n{LONG_LINE}"
                found = check_text("src/a.ts", text)
                self.assertEqual([(v.rule, v.line) for v in found], [("TELL-1", 7)])

    def test_checks_the_other_rules_in_a_generated_file(self) -> None:
        text = "// @generated\nconsole.log(1);\n// " + TO_DO + ": x"
        self.assertEqual(rules(check_text("src/a.ts", text)), ["TELL-13", "CS-6"])


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


class FileNameTest(unittest.TestCase):
    def test_rejects_utils_helpers_common_and_misc(self) -> None:
        for name in ("src/utils.ts", "lib/helpers.py", "common.go", "pkg/Misc.kt"):
            with self.subTest(name=name):
                self.assertEqual(rules(check_text(name, "")), ["TELL-7"])

    def test_rejects_the_name_with_any_extension_or_none(self) -> None:
        for name in ("utils", "helpers.test.ts", "common.d.ts", "src/MISC.md", "Utils.json"):
            with self.subTest(name=name):
                self.assertEqual(rules(check_text(name, "")), ["TELL-7"])

    def test_accepts_a_folder_named_common(self) -> None:
        self.assertEqual(check_text("common/parse.ts", ""), [])

    def test_accepts_a_name_that_only_starts_with_one_of_the_words(self) -> None:
        self.assertEqual(check_text("src/utilities.ts", ""), [])
        self.assertEqual(check_text("src/commonly.ts", ""), [])


class TodoFormTest(unittest.TestCase):
    def test_rejects_a_to_do_without_an_issue(self) -> None:
        self.assertEqual(rules(check_text("src/a.ts", f"// {TO_DO}: handle 00")), ["CS-6"])

    def test_rejects_a_to_do_in_a_config_file(self) -> None:
        found = check_text("Makefile", "# " + TO_DO + ": pin the version")
        self.assertEqual(rules(found), ["CS-6"])

    def test_rejects_a_to_do_or_a_fix_me_in_any_letter_case(self) -> None:
        for word in (TO_DO, TO_DO.lower(), TO_DO.title(), FIX_ME, FIX_ME.lower(), FIX_ME.title()):
            with self.subTest(word=word):
                found = check_text("src/a.ts", f"// {word}: handle 00")
                self.assertEqual(rules(found), ["CS-6"])
                self.assertEqual(found[0].column, 4)
                self.assertEqual(
                    found[0].message, f"Link an issue in the form {word.upper()}(#123)."
                )

    def test_accepts_a_to_do_with_an_issue(self) -> None:
        self.assertEqual(check_text("src/a.ts", f"// {TO_DO}(#12): handle 00"), [])

    def test_accepts_a_to_do_or_a_fix_me_with_an_issue_in_any_letter_case(self) -> None:
        for word in (TO_DO, TO_DO.lower(), FIX_ME, FIX_ME.title()):
            with self.subTest(word=word):
                self.assertEqual(check_text("src/a.ts", f"// {word}(#12): handle 00"), [])

    def test_rejects_a_to_do_with_a_bad_issue_reference(self) -> None:
        for reference in ("(12)", "(#)", "(#x)", " (#12)"):
            with self.subTest(reference=reference):
                found = check_text("src/a.ts", f"// {TO_DO}{reference}: handle 00")
                self.assertEqual(rules(found), ["CS-6"])

    def test_accepts_a_word_that_only_contains_to_do(self) -> None:
        line = "const todos = 1; const mastodon = 2; const fixmeLater = 3; // _todo_form"
        self.assertEqual(check_text("src/a.ts", line), [])

    def test_ignores_prose(self) -> None:
        self.assertEqual(check_text("docs/notes.md", f"{TO_DO}: write this"), [])

    def test_checks_a_config_file_that_php_tools_use(self) -> None:
        found = check_text("phpstan.dist.neon", "# " + TO_DO + ": raise the level")
        self.assertEqual(rules(found), ["CS-6"])


class DebugCallTest(unittest.TestCase):
    def test_rejects_a_debug_call_in_each_language(self) -> None:
        cases = {
            "src/a.ts": "console.log(code);",
            "src/b.ts": "debugger;",
            "src/a.php": "var_dump($code);",
            "pkg/a.py": "print(code)",
            "pkg/b.py": "pdb.set_trace()",
            "pkg/c.py": "breakpoint()",
            "a.go": "fmt.Println(code)",
            "b.go": 'log.Printf("x")',
            "src/A.kt": "println(code)",
            "src/B.kt": 'Log.d(TAG, "x")',
            "src/A.java": "System.out.println(x);",
            "src/B.java": "e.printStackTrace();",
            "src/A.cs": "Console.WriteLine(code);",
            "lib/a.dart": "debugPrint(code);",
            "Sources/A.swift": "dump(code)",
            "Sources/B.swift": 'NSLog("x")',
        }
        for path, line in cases.items():
            with self.subTest(path=path):
                self.assertEqual(rules(check_text(path, line)), ["TELL-13"])

    def test_rejects_each_debug_call_that_a_language_file_lists(self) -> None:
        for path, lines in DEBUG_LINES.items():
            for line in lines:
                with self.subTest(path=path, line=line):
                    self.assertEqual(rules(check_text(path, line)), ["TELL-13"])

    def test_rejects_a_debug_call_in_each_file_extension_with_a_language(self) -> None:
        for extension, line in DEBUG_LINE_BY_EXTENSION.items():
            with self.subTest(extension=extension):
                self.assertEqual(rules(check_text("src/a" + extension, line)), ["TELL-13"])

    def test_names_the_call_and_its_place(self) -> None:
        found = check_text("src/a.ts", "  console.log(x);")
        self.assertEqual((found[0].line, found[0].column), (1, 3))
        self.assertEqual(found[0].message, "Remove 'console.log('.")

    def test_checks_a_code_file_in_a_catalogue_folder(self) -> None:
        found = check_text("src/messages/format.ts", "console.log(1);")
        self.assertEqual(rules(found), ["TELL-13"])

    def test_accepts_methods_with_similar_names(self) -> None:
        self.assertEqual(check_text("pkg/a.py", "report.print(code)"), [])
        self.assertEqual(check_text("pkg/a.py", "pprint_table(code)"), [])

    def test_accepts_each_call_that_only_looks_like_a_debug_call(self) -> None:
        for path, lines in HARMLESS_LINES.items():
            for line in lines:
                with self.subTest(path=path, line=line):
                    self.assertEqual(check_text(path, line), [])

    def test_ignores_test_files_and_comment_lines(self) -> None:
        self.assertEqual(check_text("example_test.go", 'fmt.Println("EK-01")'), [])
        self.assertEqual(check_text("src/a.ts", " * console.log(parse(code));"), [])

    def test_ignores_each_kind_of_test_path(self) -> None:
        cases = {
            "test/parse.ts": "console.log(code);",
            "src/__tests__/parse.ts": "console.log(code);",
            "lib/parse_test.dart": "debugPrint(code);",
            "src/parse.test.ts": "console.log(code);",
            "src/parse.spec.mjs": "console.log(code);",
            "test_parse.py": "print(code)",
            "src/ParseTest.kt": "println(code)",
            "Sources/ParseTests.swift": "dump(code)",
        }
        for path, line in cases.items():
            with self.subTest(path=path):
                self.assertEqual(check_text(path, line), [])

    def test_ignores_every_test_file_name_that_the_standards_allow(self) -> None:
        for path, line in TEST_FILES.items():
            with self.subTest(path=path):
                self.assertEqual(check_text(path, line), [])

    def test_checks_a_file_name_that_only_looks_like_a_test_file(self) -> None:
        for path, line in NON_TEST_FILES.items():
            with self.subTest(path=path):
                self.assertEqual(rules(check_text(path, line)), ["TELL-13"])

    def test_ignores_each_kind_of_comment_start(self) -> None:
        cases = [
            ("src/a.ts", "// console.log(x)"),
            ("src/a.ts", "/* console.log(x)"),
            ("src/a.ts", " * console.log(x)"),
            ("pkg/a.py", "# print(x)"),
        ]
        for path, line in cases:
            with self.subTest(line=line):
                self.assertEqual(check_text(path, line), [])

    def test_ignores_doctest_examples(self) -> None:
        self.assertEqual(check_text("pkg/a.py", '    >>> print(parse("EK01A03FK01"))'), [])
        self.assertEqual(check_text("pkg/a.py", "    ...     print(code)"), [])

    def test_checks_a_spread_line_outside_python(self) -> None:
        line = "    ...items.map((item) => console.log(item)),"
        self.assertEqual(rules(check_text("src/a.ts", line)), ["TELL-13"])

    def test_reads_the_language_from_a_shebang(self) -> None:
        cases = {
            "#!/usr/bin/env python3\nprint(1)": ["TELL-13"],
            "#!/usr/bin/env python\nprint(1)": ["TELL-13"],
            "#!/usr/bin/python3\nprint(1)": ["TELL-13"],
            "#!/usr/bin/env node\nconsole.log(1)": ["TELL-13"],
            "#!/usr/bin/node\nconsole.log(1)": ["TELL-13"],
            "#!/bin/sh\nprint(1)": [],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(rules(check_text("scripts/run", text)), expected)

    def test_does_not_check_markup_or_style_files_for_debug_calls(self) -> None:
        for path in ("site/a.html", "src/a.css", "src/a.scss"):
            with self.subTest(path=path):
                self.assertEqual(check_text(path, "console.log(x);"), [])


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


class SkipTest(unittest.TestCase):
    def test_rejects_a_skip_without_a_reason(self) -> None:
        line = "x" * 120 + f"  // {SKIP_MARKER} TELL-1"
        self.assertEqual(sorted(rules(check_text("src/a.ts", line))), ["SKIP", "TELL-1"])

    def test_rejects_a_skip_of_a_rule_that_cannot_be_skipped(self) -> None:
        line = f"const a = 1; // {SKIP_MARKER} TELL-7 because it is short"
        self.assertEqual(rules(check_text("src/a.ts", line)), ["SKIP"])

    def test_skips_each_rule_that_a_skip_comment_can_skip(self) -> None:
        for rule, (path, line) in SKIP_SAMPLES.items():
            with self.subTest(rule=rule):
                self.assertEqual(rules(check_text(path, line)), [rule])
                skipped = f"{line}  // {SKIP_MARKER} {rule} because the line is a sample"
                self.assertEqual(check_text(path, skipped), [])

    def test_rejects_a_skip_of_each_rule_that_cannot_be_skipped(self) -> None:
        for rule in ("TELL-2", "TELL-7", "TELL-18", "CS-5", "API-3", "GIT-1"):
            with self.subTest(rule=rule):
                line = f"const a = 1; // {SKIP_MARKER} {rule} because it is short"
                found = check_text("src/a.ts", line)
                self.assertEqual(rules(found), ["SKIP"])
                self.assertEqual(found[0].column, 17)

    def test_skips_only_the_rule_that_the_comment_names(self) -> None:
        line = f"console.log('{LONG_LINE}');  // {SKIP_MARKER} TELL-1 because the string is data"
        self.assertEqual(rules(check_text("src/a.ts", line)), ["TELL-13"])

    def test_skips_only_the_line_that_holds_the_comment(self) -> None:
        text = f"console.log(1); // {SKIP_MARKER} TELL-13 because it is a sample\nconsole.log(2);"
        found = check_text("src/a.ts", text)
        self.assertEqual([(v.rule, v.line) for v in found], [("TELL-13", 2)])

    def test_honours_a_skip_in_a_config_file(self) -> None:
        line = f"{LONG_LINE}  # {SKIP_MARKER} TELL-1 because the value is a hash"
        self.assertEqual(check_text("Makefile", line), [])

    def test_ignores_a_skip_marker_in_prose(self) -> None:
        line = "A line such as `" + SKIP_MARKER + " TELL-1` has no reason."
        self.assertEqual(check_text("README.md", line), [])


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
    RENOVATE_COMMENT = "<!--renovate-debug:eyJjcmVhdGVkSW5WZXIiOiI0NC4xMzIuMiJ9-->"

    def test_leaves_out_the_comment_that_renovate_ends_a_body_with(self) -> None:
        message = squash("ci: update an action (#4)", body="Update a pinned tool or action.")
        self.assertEqual(check_squash_message(message + self.RENOVATE_COMMENT + "\n"), [])

    def test_leaves_out_the_text_that_a_comment_holds(self) -> None:
        hidden = [
            EMOJI,
            f"a dash {EM_DASH} here",
            "Closes #",
            PLACEHOLDER_PARAGRAPH,
            "Signed-off-by: Your Name <you@example.com>",
        ]
        for text in hidden:
            with self.subTest(text=text):
                body = f"Why the change is needed.\n\n<!-- {text} -->"
                self.assertEqual(check_squash_message(squash("fix: a unit", body=body)), [])

    def test_leaves_out_a_comment_that_spans_lines(self) -> None:
        body = f"Why the change is needed.\n\n<!--\nClose the issue.\n{EMOJI}\nCloses #\n-->"
        self.assertEqual(check_squash_message(squash("fix: a unit", body=body)), [])

    def test_keeps_the_place_of_the_text_around_a_comment(self) -> None:
        body = f"Use a dash <!-- a\nb --> {EM_DASH} here."
        found = check_squash_message(squash("fix: a unit", body=body))
        self.assertEqual([(v.rule, v.line, v.column) for v in found], [("TELL-14", 4, 7)])

    def test_leaves_out_each_comment_of_a_line_and_not_the_text_between_them(self) -> None:
        body = f"Fix <!-- {EMOJI} --> the {EM_DASH} unit <!-- {EMOJI} --> rule."
        found = check_squash_message(squash("fix: a unit", body=body))
        self.assertEqual(
            [(v.rule, v.line, v.column) for v in found], [("TELL-14", 3, body.index(EM_DASH) + 1)]
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
        self.assertEqual(check_squash_message(message), [])

    def test_leaves_out_nothing_in_a_commit_message_file(self) -> None:
        message = f"fix: a unit\n\n<!-- {EMOJI} -->\n"
        self.assertEqual(rules(check_commit_message(message)), ["TELL-14"])


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
