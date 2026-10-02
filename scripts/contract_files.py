# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Read client.md and, from the next change on, the contract scenarios."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT_DOC = ROOT / "client.md"


def error_codes(path: Path = CLIENT_DOC) -> list[str]:
    """Return the error codes in the table of the Errors section of client.md, in order."""
    section = path.read_text(encoding="utf-8").partition("\n## Errors\n")[2].partition("\n## ")[0]
    codes = re.findall(r"^\| [^|]+ \| `([a-z_]+)` \|", section, flags=re.MULTILINE)
    return list(dict.fromkeys(codes))
