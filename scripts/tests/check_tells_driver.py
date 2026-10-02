# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Run check_tells in a test: make git repos, run the command and read the rules."""

import contextlib
import io
import os
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

import check_tells
from check_tells import Violation

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


def run_main(*args: str) -> tuple[int, str, str]:
    """Run the command line and give the exit code, the standard output and the error output."""
    output, errors = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        status = check_tells.main(list(args))
    return status, output.getvalue(), errors.getvalue()
