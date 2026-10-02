# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""TELL-13: the debug calls that each language file lists, and the check of one line."""

from __future__ import annotations

import re

from check_tells.file_kinds import FileInfo
from check_tells.violation import Violation

DEBUG_CALLS: dict[str, tuple[re.Pattern[str], ...]] = {
    "javascript": (re.compile(r"\bconsole\.(log|debug|dir)\s*\("), re.compile(r"\bdebugger\b")),
    "php": (
        re.compile(
            r"(?<![\w>$:])(var_dump|print_r|var_export|dd|dump|error_log|debug_print_backtrace)"
            r"\s*\("
        ),
    ),
    "python": (
        re.compile(r"(?<![\w.])(print|pprint|breakpoint)\s*\("),
        re.compile(r"\bpdb\.set_trace\s*\("),
    ),
    "go": (
        re.compile(r"\bfmt\.Print(f|ln)?\s*\("),
        re.compile(r"\blog\.(Print|Fatal|Panic)(f|ln)?\s*\("),
        re.compile(r"(?<![\w.])(print|println)\s*\("),
    ),
    "jvm": (
        re.compile(r"(?<![\w.])(print|println)\s*\("),
        re.compile(r"\bSystem\.(out|err)\b"),
        re.compile(r"\.printStackTrace\s*\("),
        re.compile(r"\bLog\.(v|d|i|w|e|wtf)\s*\("),
    ),
    "dotnet": (re.compile(r"\b(Console|Debug|Trace)\.Write(Line)?\s*\("),),
    "dart": (re.compile(r"(?<![\w.])(print|debugPrint)\s*\("),),
    "swift": (re.compile(r"(?<![\w.])(print|dump|debugPrint|NSLog)\s*\("),),
}

COMMENT_LINE = re.compile(r"^\s*(//|/\*|\*|#)")
# Doctest prompts (>>> and ...) start the examples in Python docstrings.
DOCTEST_LINE = re.compile(r"^\s*(>>>|\.\.\.)")


def _is_comment(info: FileInfo, line: str) -> bool:
    if COMMENT_LINE.match(line):
        return True
    return info.language == "python" and bool(DOCTEST_LINE.match(line))


def check_debug_calls(info: FileInfo, number: int, line: str) -> list[Violation]:
    """Find the debug calls of the file's language in one line (TELL-13).

    A test file and a comment line have no debug calls.
    """
    if info.kind != "code" or info.is_test or info.language is None or _is_comment(info, line):
        return []
    patterns = DEBUG_CALLS.get(info.language, ())
    return [
        Violation(info.path, number, match.start() + 1, "TELL-13", f"Remove {match.group(0)!r}.")
        for pattern in patterns
        for match in pattern.finditer(line)
    ]
