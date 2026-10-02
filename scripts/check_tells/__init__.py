# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Find the agent tells that language tools miss.

The rules come from standards/CODING_STANDARDS.md: TELL-1, TELL-7, TELL-13, TELL-14
and TELL-18, and CS-6 for the form of to-do comments. For the message that a squash merge
puts on main, it also checks GIT-1 and GIT-2.

Each module has one job:

- violation: the result of a check.
- text: the lines of a text, and the characters that TELL-14 rejects.
- file_kinds: the kind and the language of a file.
- debug_calls: the debug calls of TELL-13.
- file_checks: the checks of the name and the lines of one file.
- message_checks: the checks of commit messages and squash messages.
- scan: the reading of files, message files and commits.
- command: the command line.
"""

from check_tells.command import main
from check_tells.file_checks import check_text
from check_tells.file_kinds import FileInfo, Kind, classify
from check_tells.message_checks import (
    PLACEHOLDER_ADDRESS,
    TEMPLATE_PARAGRAPH,
    check_commit_message,
    check_squash_message,
)
from check_tells.scan import InputError, check_files, check_signed_off, tracked_files
from check_tells.violation import Violation

__all__ = [
    "PLACEHOLDER_ADDRESS",
    "TEMPLATE_PARAGRAPH",
    "FileInfo",
    "InputError",
    "Kind",
    "Violation",
    "check_commit_message",
    "check_files",
    "check_signed_off",
    "check_squash_message",
    "check_text",
    "classify",
    "main",
    "tracked_files",
]
