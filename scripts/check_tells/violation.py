# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""The result of a check: one broken rule at one place in a file or a message."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Violation:
    """One broken rule at one place in a file."""

    path: str
    line: int
    column: int
    rule: str
    message: str

    def __str__(self) -> str:
        """Format the violation like a compiler message."""
        return f"{self.path}:{self.line}:{self.column}: {self.rule} {self.message}"
