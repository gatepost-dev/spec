# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""The checks of the name and the lines of one file.

They cover TELL-1, TELL-7, TELL-13, TELL-14 and CS-6, and the comment that skips one of
them for one line.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from check_tells.debug_calls import check_debug_calls
from check_tells.file_kinds import FileInfo, classify, is_data_json
from check_tells.text import LAST_ASCII, is_emoji, split_lines
from check_tells.violation import Violation

MAX_LINE = 100
TAB_WIDTH = 4
FORBIDDEN_STEMS = frozenset({"utils", "helpers", "common", "misc"})
SKIPPABLE_RULES = frozenset({"TELL-1", "TELL-13", "TELL-14", "CS-6"})
URL = re.compile(r"https?://")
# The words are split, so that this line does not match its own pattern.
TODO_FORM = re.compile(r"\b(?:TO" r"DO|FIX" r"ME)\b(?!\(#\d+\))", re.IGNORECASE)
SKIP = re.compile(r"check-tells: allow ([A-Z]+-\d+)(?: because (\S.*))?")


def check_text(path: str, text: str) -> list[Violation]:
    """Check the name and every line of one file."""
    info = classify(path, text)
    violations = _check_name(info)
    for number, line in enumerate(split_lines(text), start=1):
        violations.extend(_check_line(info, number, line))
    return violations


def _check_name(info: FileInfo) -> list[Violation]:
    stem = PurePosixPath(info.path).name.split(".")[0].lower()
    if stem not in FORBIDDEN_STEMS:
        return []
    message = "Name the file after the concept that it holds, not utils, helpers, common or misc."
    return [Violation(info.path, 1, 1, "TELL-7", message)]


def _check_line(info: FileInfo, number: int, line: str) -> list[Violation]:
    skipped: set[str] = set()
    problems: list[Violation] = []
    if info.kind in ("code", "config"):
        skipped, problems = _skips(info.path, number, line)
    found = [
        violation
        for check in (_line_length, _todo_form, check_debug_calls, _characters)
        for violation in check(info, number, line)
        if violation.rule not in skipped
    ]
    return problems + found


def _skips(path: str, number: int, line: str) -> tuple[set[str], list[Violation]]:
    skipped: set[str] = set()
    problems: list[Violation] = []
    for match in SKIP.finditer(line):
        rule, reason = match.group(1), match.group(2)
        if rule in SKIPPABLE_RULES and reason:
            skipped.add(rule)
            continue
        message = (
            f"Skip only {', '.join(sorted(SKIPPABLE_RULES))}, and give a reason after because."
        )
        problems.append(Violation(path, number, match.start() + 1, "SKIP", message))
    return skipped, problems


def _line_length(info: FileInfo, number: int, line: str) -> list[Violation]:
    if info.kind not in ("code", "config") or info.is_generated or is_data_json(info.path):
        return []
    width = len(line.expandtabs(TAB_WIDTH))
    if width <= MAX_LINE or URL.search(line):
        return []
    message = f"The line is {width} characters wide. Keep lines at {MAX_LINE} or fewer."
    return [Violation(info.path, number, MAX_LINE + 1, "TELL-1", message)]


def _todo_form(info: FileInfo, number: int, line: str) -> list[Violation]:
    if info.kind not in ("code", "config"):
        return []
    return [
        Violation(
            info.path,
            number,
            match.start() + 1,
            "CS-6",
            f"Link an issue in the form {match.group(0).upper()}(#123).",
        )
        for match in TODO_FORM.finditer(line)
    ]


def _characters(info: FileInfo, number: int, line: str) -> list[Violation]:
    found = [
        Violation(info.path, number, index + 1, "TELL-14", f"Remove the emoji U+{ord(char):04X}.")
        for index, char in enumerate(line)
        if is_emoji(char)
    ]
    if found or info.kind not in ("code", "config"):
        return found
    for index, char in enumerate(line):
        if ord(char) > LAST_ASCII:
            message = f"Write U+{ord(char):04X} as an escape sequence. Code and config use ASCII."
            return [Violation(info.path, number, index + 1, "TELL-14", message)]
    return []
