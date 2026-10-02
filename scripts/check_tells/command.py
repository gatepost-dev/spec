# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""The command line: the options, the exit codes and the output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from check_tells.message_checks import check_commit_message, check_squash_message
from check_tells.scan import (
    InputError,
    check_files,
    check_message_file,
    check_signed_off,
    tracked_files,
)
from check_tells.violation import Violation

EXIT_BAD_INPUT = 2


def _run(args: argparse.Namespace) -> list[Violation]:
    if args.commit_msg is not None:
        return check_message_file(args.commit_msg, check_commit_message)
    if args.squash_msg is not None:
        return check_message_file(
            args.squash_msg, lambda text: check_squash_message(text, no_scope=args.no_scope)
        )
    root = args.root.resolve()
    if args.signed_off is not None:
        return check_signed_off(root, args.signed_off)
    files = [(root / path).resolve() for path in args.paths] or tracked_files(root)
    return check_files(root, files)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check-tells", description="Find the agent tells that language tools miss."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="The repo root.")
    messages = parser.add_mutually_exclusive_group()
    messages.add_argument(
        "--commit-msg", type=Path, help="Check this commit message file (TELL-14 and TELL-18)."
    )
    messages.add_argument(
        "--squash-msg",
        type=Path,
        help="Check this file as the message that a squash merge puts on main "
        "(TELL-14, TELL-18, GIT-1, GIT-2 and the text of the pull request template).",
    )
    messages.add_argument(
        "--signed-off",
        metavar="RANGE",
        help="Check that each commit in this git revision range has a sign-off (GIT-2).",
    )
    parser.add_argument(
        "--no-scope",
        action="store_true",
        help="With --squash-msg, reject a scope in the subject "
        "(GIT-1 for a repo without packages).",
    )
    parser.add_argument("paths", nargs="*", type=Path, help="Files to check. Default: all.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the checks and print each violation.

    Return 0 if all is well, 1 if a rule broke and 2 if the input cannot be read.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    if args.no_scope and args.squash_msg is None:
        parser.error("--no-scope needs --squash-msg.")
    try:
        violations = _run(args)
    except InputError as error:
        sys.stderr.write(f"check-tells: {error}\n")
        return EXIT_BAD_INPUT
    for violation in sorted(violations):
        sys.stdout.write(f"{violation}\n")
    return 1 if violations else 0
