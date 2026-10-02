# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for check_tells.debug_calls: TELL-13."""

import unittest

from check_tells import check_text

from tests.check_tells_driver import rules

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
