# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Read the input of a run and check it: the files of a repo, a message file or a range of commits.

Input that cannot be read raises InputError.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from check_tells.file_checks import check_text
from check_tells.file_kinds import classify
from check_tells.message_checks import check_sign_off
from check_tells.text import split_lines
from check_tells.violation import Violation


class InputError(Exception):
    """The command line names something that check-tells cannot read."""


def _git(root: Path, *arguments: str) -> bytes:
    """Run git in root and give its output. A failure is bad input, such as no repo."""
    try:
        run = subprocess.run(["git", "-C", str(root), *arguments], check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        reason = " ".join(error.stderr.decode(errors="replace").split())
        raise InputError(f"Git failed in {root}: {reason}") from error
    return run.stdout


def tracked_files(root: Path) -> list[Path]:
    """List the files that git tracks, or would track, under root."""
    output = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    names = output.decode().split("\0")
    return [root / name for name in names if name and (root / name).is_file()]


def _commits(root: Path, revision_range: str) -> list[tuple[str, str]]:
    """Give the hash and the message of each commit in a range. Merge commits are left out."""
    output = _git(
        root,
        "log",
        "--no-merges",
        "--no-show-signature",
        "--format=%H%n%B%x00",
        "--end-of-options",
        revision_range,
    )
    records = [record.lstrip("\n") for record in output.decode(errors="replace").split("\0")]
    pairs = (record.partition("\n") for record in records if record)
    return [(commit, message) for commit, _, message in pairs]


def check_signed_off(root: Path, revision_range: str) -> list[Violation]:
    """Check that each commit in a revision range has a sign-off. Merge commits are left out."""
    violations: list[Violation] = []
    for commit, message in _commits(root, revision_range):
        lines = list(enumerate(split_lines(message), start=1))
        violations.extend(check_sign_off(lines, f"commit {commit[:12]}"))
    return violations


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise InputError(f"Cannot read {path}: {error.strerror}.") from error


def _not_utf8(path: str, data: bytes, error: UnicodeDecodeError, advice: str) -> Violation:
    """Point at the first byte that is not UTF-8. All the bytes before it are valid."""
    line_start = data.rfind(b"\n", 0, error.start) + 1
    line = data.count(b"\n", 0, error.start) + 1
    column = len(data[line_start : error.start].decode("utf-8")) + 1
    message = f"Byte 0x{data[error.start]:02X} is not valid UTF-8. {advice}"
    return Violation(path, line, column, "TELL-14", message)


def _check_undecodable(path: str, data: bytes, error: UnicodeDecodeError) -> list[Violation]:
    """Report a code or config file that is not UTF-8. Other files can be binary, so skip them."""
    # Only the suffix and the first bytes decide the kind, and bad bytes would stop the decoder.
    kind = classify(path, data[:512].decode("utf-8", errors="replace")).kind
    if kind not in ("code", "config"):
        return []
    advice = "Save the file as UTF-8, and use ASCII in code and config."
    return [_not_utf8(path, data, error, advice)]


def check_files(root: Path, files: list[Path]) -> list[Violation]:
    """Check each file. Report a code or config file that is not UTF-8, and skip other files."""
    violations: list[Violation] = []
    for file in files:
        if not file.is_relative_to(root):
            raise InputError(f"{file} is outside the root {root}.")
        path = file.relative_to(root).as_posix()
        data = _read(file)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            violations.extend(_check_undecodable(path, data, error))
        else:
            violations.extend(check_text(path, text))
    return violations


def check_message_file(path: Path, check: Callable[[str], list[Violation]]) -> list[Violation]:
    """Read a message file and run a check on its text.

    A file that is not UTF-8 gives a TELL-14 violation at the first bad byte.
    """
    data = _read(path)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        advice = "Save the message as UTF-8, and use ASCII."
        return [_not_utf8("commit message", data, error, advice)]
    return check(text)
