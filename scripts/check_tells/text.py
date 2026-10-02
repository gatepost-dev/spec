# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""How the checks read text: its lines, and the characters that TELL-14 rejects."""

from __future__ import annotations

LAST_ASCII = 0x7F
EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),
    (0x231A, 0x231B),
    (0x23E9, 0x23F3),
    (0x2600, 0x27BF),
    (0x2B00, 0x2BFF),
    (0xFE0F, 0xFE0F),
)


def split_lines(text: str) -> list[str]:
    """Split text at line feeds only, and remove one carriage return from each line.

    str.splitlines also splits at U+2028, U+2029, U+0085 and the form feed. That hides the
    characters that TELL-14 looks for, and it moves the line numbers.
    """
    return [line.removesuffix("\r") for line in text.split("\n")]


def is_emoji(character: str) -> bool:
    """Tell whether the character is in an emoji range. The ranges include U+FE0F."""
    return any(low <= ord(character) <= high for low, high in EMOJI_RANGES)
