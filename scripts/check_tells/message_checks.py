# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""The checks of a commit message and of the message that a squash merge puts on main.

TELL-14 and TELL-18 apply to both. GIT-1, GIT-2 and the text of the pull request template
apply to the squash message.
"""

from __future__ import annotations

import re

from check_tells.text import LAST_ASCII, is_emoji, split_lines
from check_tells.violation import Violation

NumberedLine = tuple[int, str]

MAX_SUBJECT = 72
# In lower case, because git reads the keys of trailer lines without regard to case.
SIGN_OFF_PREFIXES = ("signed-off-by:", "co-authored-by:")
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
COMMIT_TYPE_LIST = f"{', '.join(COMMIT_TYPES[:-1])} or {COMMIT_TYPES[-1]}"
# A type, a scope that can be missing, a mark for a breaking change that can be missing, a colon,
# a space and text.
SUBJECT_FORM = re.compile(r"(?P<type>[a-z]+)(?P<scope>\([^()\s]+\))?!?: \S")
SIGN_OFF = re.compile(r"signed-off-by:[ \t]+[^<>\s][^<>]*<[^<>\s]+@[^<>\s]+>[ \t]*", re.IGNORECASE)
# The address in the sign-off line of templates/PULL_REQUEST_TEMPLATE.md.
PLACEHOLDER_ADDRESS = "you@example.com"
# The start of the paragraph in that template that asks the author for prose.
TEMPLATE_PARAGRAPH = "Write two or three sentences of plain prose"
EMPTY_CLOSES_LINE = re.compile(r"closes #\s*", re.IGNORECASE)
# Renovate adds this comment to the very end of each pull request body. The author did not
# write it, and its payload is base64.
RENOVATE_COMMENT = re.compile(r"\n?<!--renovate-debug:[A-Za-z0-9+/=]*-->\s*$")
SQUASH_NOTE = " The subject is the title plus the ' (#N)' that the squash merge adds."


def _message_lines(text: str) -> list[NumberedLine]:
    """Pair each line with its number. Drop git's comment lines, and stop at its scissors line."""
    numbered: list[NumberedLine] = []
    for number, line in enumerate(split_lines(text), start=1):
        if line.startswith("# ") and ">8" in line:
            break
        if not line.startswith("#"):
            numbered.append((number, line))
    return numbered


def _subject(lines: list[NumberedLine]) -> NumberedLine | None:
    """Find the subject, which is the first line that has text."""
    return next(((number, line) for number, line in lines if line.strip()), None)


def _check_subject(lines: list[NumberedLine], note: str = "") -> list[Violation]:
    """Check the length of the subject. The note adds advice that fits the message."""
    subject = _subject(lines)
    if subject is None or len(subject[1]) <= MAX_SUBJECT:
        return []
    number, text = subject
    message = f"The subject has {len(text)} characters. Use {MAX_SUBJECT} or fewer.{note}"
    return [Violation("commit message", number, MAX_SUBJECT + 1, "TELL-18", message)]


def _first_bad_character(number: int, line: str) -> Violation | None:
    """Find the first emoji, or the first non-ASCII character outside a sign-off line."""
    allow_non_ascii = line.lower().startswith(SIGN_OFF_PREFIXES)
    for index, char in enumerate(line):
        if is_emoji(char) or (ord(char) > LAST_ASCII and not allow_non_ascii):
            message = f"Remove U+{ord(char):04X}. Commit messages use ASCII."
            return Violation("commit message", number, index + 1, "TELL-14", message)
    return None


def _check_message(lines: list[NumberedLine], note: str = "") -> list[Violation]:
    violations = _check_subject(lines, note)
    for number, line in lines:
        violation = _first_bad_character(number, line)
        if violation is not None:
            violations.append(violation)
    return violations


def _check_subject_form(lines: list[NumberedLine], *, no_scope: bool) -> list[Violation]:
    """Check GIT-1: the subject has a type that Conventional Commits lists, and maybe a scope."""
    subject = _subject(lines)
    if subject is None:
        return [Violation("commit message", 1, 1, "GIT-1", "The message has no subject.")]
    number, text = subject
    match = SUBJECT_FORM.match(text)
    if match is None:
        message = (
            "The subject does not follow Conventional Commits. "
            f"Write 'type: description', where type is {COMMIT_TYPE_LIST}."
        )
        return [Violation("commit message", number, 1, "GIT-1", message)]
    if match["type"] not in COMMIT_TYPES:
        message = f"'{match['type']}' is not a Conventional Commits type. Use {COMMIT_TYPE_LIST}."
        return [Violation("commit message", number, 1, "GIT-1", message)]
    if no_scope and match["scope"]:
        message = (
            f"Remove the scope {match['scope']}. "
            "This repo has no packages, so a subject has no scope."
        )
        column = match.start("scope") + 1
        return [Violation("commit message", number, column, "GIT-1", message)]
    return []


def check_sign_off(lines: list[NumberedLine], path: str) -> list[Violation]:
    """Check GIT-2: the message has a line 'Signed-off-by: Name <address>', not the template's."""
    sign_offs = [(number, line) for number, line in lines if SIGN_OFF.fullmatch(line)]
    if not sign_offs:
        message = (
            "The message has no Signed-off-by line. Add the line 'Signed-off-by: Name <address>'. "
            "git commit --signoff adds it to a commit, and git rebase --signoff adds it to each "
            "commit of a branch."
        )
        return [Violation(path, 1, 1, "GIT-2", message)]
    message = (
        f"The sign-off still holds the placeholder address {PLACEHOLDER_ADDRESS}. "
        "Write your own name and address."
    )
    return [
        Violation(path, number, 1, "GIT-2", message)
        for number, line in sign_offs
        if PLACEHOLDER_ADDRESS in line.lower()
    ]


def _check_template_text(lines: list[NumberedLine]) -> list[Violation]:
    """Find the text of the pull request template that the author did not replace."""
    violations: list[Violation] = []
    for number, line in lines:
        text = line.strip()
        if text.startswith(TEMPLATE_PARAGRAPH):
            message = (
                "The body still holds the placeholder paragraph of the pull request template. "
                "Replace it with two or three sentences that say what the change does and why."
            )
        elif EMPTY_CLOSES_LINE.fullmatch(text):
            message = (
                "The body still holds the line 'Closes #'. Add the issue number after it. "
                "If the change closes no issue, remove the line."
            )
        else:
            continue
        violations.append(Violation("commit message", number, 1, "TELL-18", message))
    return violations


def check_commit_message(text: str) -> list[Violation]:
    """Check the subject length and the characters of a commit message."""
    return _check_message(_message_lines(text))


def check_squash_message(text: str, *, no_scope: bool = False) -> list[Violation]:
    """Check the message that a squash merge puts on main: the pull request title and body.

    The body is not a git message, so a line that starts with # is text and not a comment. GitHub
    keeps the raw body, so the text of an HTML comment reaches main like any other text. The
    check leaves out only the comment that Renovate adds at the very end of its body.
    """
    subject, line_feed, body = text.partition("\n")
    checked = subject + line_feed + RENOVATE_COMMENT.sub("", body)
    lines = list(enumerate(split_lines(checked), start=1))
    return [
        *_check_message(lines, SQUASH_NOTE),
        *_check_subject_form(lines, no_scope=no_scope),
        *check_sign_off(lines, "commit message"),
        *_check_template_text(lines),
    ]
