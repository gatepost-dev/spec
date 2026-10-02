#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Build the shared test vectors in vectors/.

This file is the source of truth for the vectors. Edit the cases here, then run
python3 scripts/build_vectors.py. CI runs it with --check, which fails when a vector
file differs from what this script builds.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VECTORS = ROOT / "vectors"
FORMAT_VERSION = 1
STATE_COUNT = 37

EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)
MINUS_SIGN = chr(0x2212)
NO_BREAK_SPACE = chr(0x00A0)
NARROW_NO_BREAK_SPACE = chr(0x202F)
ZERO_WIDTH_SPACE = chr(0x200B)
BYTE_ORDER_MARK = chr(0xFEFF)
SMALL_E_ACUTE = chr(0x00E9)
FI_LIGATURE = chr(0xFB01)
TAB = chr(0x09)
LINE_FEED = chr(0x0A)
SOFT_HYPHEN = chr(0x00AD)
LEFT_TO_RIGHT_MARK = chr(0x200E)
RIGHT_TO_LEFT_MARK = chr(0x200F)
RIGHT_TO_LEFT_OVERRIDE = chr(0x202E)
FULL_WIDTH_HYPHEN = chr(0xFF0D)
COMBINING_ACUTE = chr(0x0301)
HORIZONTAL_ELLIPSIS = chr(0x2026)
ZERO_WIDTH_JOINER = chr(0x200D)
LONG_S = chr(0x017F)
DOTLESS_I = chr(0x0131)
ARABIC_INDIC_LEGACY = "".join(
    chr(code_point) for code_point in (0x0669, 0x0660, 0x0660, 0x0661, 0x0660, 0x0668)
)

WIDTHS = (("state", 2), ("lga", 2), ("district", 3), ("area", 2), ("unit", 2))
PRECISION_BY_LENGTH = {2: "state", 4: "lga", 7: "district", 9: "area", 11: "unit"}
PARTIAL = {"allowPartial": True}
CODE = "EK01A03FK01"
# Mathematical bold capitals start at U+1D400 and digits at U+1D7CE. Each one is 1 code point
# and 2 UTF-16 units, and NFKC maps it to its ASCII form.
MATH_BOLD_CODE = "".join(
    chr(0x1D7CE + int(c)) if c.isdigit() else chr(0x1D400 + ord(c) - ord("A")) for c in CODE
)

Row = tuple[str, Any, dict[str, Any], dict[str, Any]]


def row(
    description: str, input_: Any, expect: dict[str, Any], options: dict[str, Any] | None = None
) -> Row:
    """Make one case. Options default to none."""
    return (description, input_, expect, options or {})


def full_width(text: str) -> str:
    """Change the ASCII letters and digits in text to their full-width forms."""
    return "".join(chr(ord(c) + 0xFEE0) if c.isascii() and c.isalnum() else c for c in text)


def joined(separator: str) -> str:
    """Return the code EK 01 A03 FK 01 with this separator between segments."""
    return separator.join(("EK", "01", "A03", "FK", "01"))


def segments_of(compact: str) -> dict[str, str | None]:
    """Split a compact code into named segments. A missing segment is None."""
    segments: dict[str, str | None] = {}
    start = 0
    for name, width in WIDTHS:
        segments[name] = compact[start : start + width] or None
        start += width
    return segments


def ok(compact: str) -> dict[str, Any]:
    """The expected result of a successful parse."""
    parts = [part for part in segments_of(compact).values() if part]
    return {
        "ok": True,
        "compact": compact,
        "canonical": "-".join(parts),
        "display": " ".join(parts),
        "precision": PRECISION_BY_LENGTH[len(compact)],
        "segments": segments_of(compact),
    }


def failed(code: str, segment: str | None = None, suggestion: str | None = None) -> dict[str, Any]:
    """The expected result of a failed parse."""
    return {"ok": False, "error": {"code": code, "segment": segment, "suggestion": suggestion}}


def value(returned: Any) -> dict[str, Any]:
    """The expected result of a function that returns one value."""
    return {"value": returned}


def load_states() -> list[dict[str, str]]:
    """Read data/states.json and check that it lists 37 different states."""
    states: list[dict[str, str]] = json.loads(
        (ROOT / "data" / "states.json").read_text(encoding="utf-8")
    )["states"]
    if len({state["code"] for state in states}) != STATE_COUNT:
        raise ValueError(f"data/states.json must list {STATE_COUNT} different state codes.")
    return states


def load_format() -> dict[str, Any]:
    """Read data/format.json."""
    postcode_format: dict[str, Any] = json.loads(
        (ROOT / "data" / "format.json").read_text(encoding="utf-8")
    )
    return postcode_format


def load_separators() -> list[int]:
    """Read data/format.json and return its separators as code points."""
    return [int(label.removeprefix("U+"), 16) for label in load_format()["separators"]]


def load_input_limit() -> int:
    """Read data/format.json and return the input limit in code points."""
    limit: int = load_format()["maxInputCodePoints"]
    return limit


def normalize_rows() -> list[Row]:
    """Cases for normalize."""
    want = value(CODE)
    separator_rows = [
        row(f"removes the separator U+{code_point:04X}", joined(chr(code_point)), want)
        for code_point in load_separators()
    ]
    return [
        row("removes hyphens", "EK-01-A03-FK-01", want),
        row("removes spaces and makes letters upper case", "ek 01 a03 fk 01", want),
        row("removes leading and trailing spaces", "  EK01A03FK01  ", want),
        row("removes dots", "EK.01.A03.FK.01", want),
        row("removes en dashes", joined(EN_DASH), want),
        row("removes em dashes", joined(EM_DASH), want),
        row("removes minus signs", joined(MINUS_SIGN), want),
        row("removes no-break spaces", joined(NO_BREAK_SPACE), want),
        row("removes narrow no-break spaces", joined(NARROW_NO_BREAK_SPACE), want),
        row("removes a zero-width space", CODE + ZERO_WIDTH_SPACE, want),
        row("removes a byte order mark", BYTE_ORDER_MARK + CODE, want),
        row("removes soft hyphens", joined(SOFT_HYPHEN), want),
        row("removes direction marks", LEFT_TO_RIGHT_MARK + CODE + RIGHT_TO_LEFT_MARK, want),
        row(
            "keeps a right-to-left override",
            RIGHT_TO_LEFT_OVERRIDE + CODE,
            value(RIGHT_TO_LEFT_OVERRIDE + CODE),
        ),
        row("changes full-width letters and digits to ASCII", full_width(CODE), want),
        # An SDK that makes ASCII letters upper case before NFKC leaves these in lower case.
        row(
            "changes full-width lower-case letters to ASCII upper case",
            full_width("ek01a03fk01"),
            want,
        ),
        row("removes full-width hyphens", joined(FULL_WIDTH_HYPHEN), want),
        row("removes tabs and line feeds", "EK01" + TAB + "A03" + LINE_FEED + "FK01", want),
        row(
            "changes a ligature to its letters",
            "EK01A03" + FI_LIGATURE + "01",
            value("EK01A03FI01"),
        ),
        row("makes mixed-case letters upper case", "eK01a03Fk01", want),
        row("keeps a legacy code", "900 108", value("900108")),
        row("keeps characters that are not separators", "EK01A03FK0!", value("EK01A03FK0!")),
        row(
            "makes only ASCII letters upper case",
            "ek01a03f" + SMALL_E_ACUTE + "01",
            value("EK01A03F" + SMALL_E_ACUTE + "01"),
        ),
        # Unicode upper case changes U+0131 to I, and NFKC leaves it alone.
        row(
            "keeps a dotless i",
            "EK01A03F" + DOTLESS_I + "01",
            value("EK01A03F" + DOTLESS_I + "01"),
        ),
        row("returns an empty string for empty input", "", value("")),
        row("returns an empty string for separators only", " - . ", value("")),
        *separator_rows,
    ]


def parse_rows() -> list[Row]:
    """Cases for forms, lengths, characters and legacy codes."""
    limit = load_input_limit()
    return [
        row("parses the canonical form", "EK-01-A03-FK-01", ok(CODE)),
        row("parses the compact form", CODE, ok(CODE)),
        row("parses the display form in lower case", "ek 01 a03 fk 01", ok(CODE)),
        row("parses a code with en dashes", joined(EN_DASH), ok(CODE)),
        row("parses a code with no-break spaces", joined(NO_BREAK_SPACE), ok(CODE)),
        row("parses a code with a zero-width space", CODE + ZERO_WIDTH_SPACE, ok(CODE)),
        row("parses a code with a byte order mark", BYTE_ORDER_MARK + CODE, ok(CODE)),
        row("parses full-width letters and digits", full_width("EK-01-A03-FK-01"), ok(CODE)),
        row("parses the example on NIPOST's homepage", "FC-02-A09-DB-09", ok("FC02A09DB09")),
        row("parses the example in NIPOST's blog", "LA 12 K23 IV 95", ok("LA12K23IV95")),
        row("parses a NIPOST test code", "AK-11-I61-ZF-12", ok("AK11I61ZF12")),
        row(
            "accepts a letter O in the district of a NIPOST test code",
            "JI-24-O18-JP-23",
            ok("JI24O18JP23"),
        ),
        row("rejects empty input", "", failed("empty")),
        row("rejects spaces only", "   ", failed("empty")),
        row("rejects separators only", " - . ", failed("empty")),
        row("names a legacy code", "900108", failed("legacy_code")),
        row("names a legacy code with a space", "900 108", failed("legacy_code")),
        row(
            "names a legacy code in full-width digits", full_width("900108"), failed("legacy_code")
        ),
        row(
            "names a legacy code when partial codes are allowed",
            "123456",
            failed("legacy_code"),
            PARTIAL,
        ),
        row("rejects five digits", "90010", failed("bad_length")),
        row("rejects an exclamation mark", "EK01A03FK0!", failed("bad_character")),
        row("rejects an underscore", "EK01A03FK0_", failed("bad_character")),
        row("rejects slashes", "EK01/A03/FK01", failed("bad_character")),
        row(
            "rejects a letter outside ASCII",
            "EK01A03F" + SMALL_E_ACUTE + "01",
            failed("bad_character"),
        ),
        row(
            "rejects a right-to-left override",
            RIGHT_TO_LEFT_OVERRIDE + CODE,
            failed("bad_character"),
        ),
        row("rejects Arabic-Indic digits", ARABIC_INDIC_LEGACY, failed("bad_character")),
        row("rejects 10 characters", "EK01A03FK1", failed("bad_length")),
        row("rejects 12 characters", "EK01A03FK01X", failed("bad_length")),
        row("rejects a unit that lost its zero", "EK-01-A03-FK-1", failed("bad_length")),
        row("rejects a state alone by default", "EK", failed("bad_length")),
        row("rejects a district code by default", "EK01A03", failed("bad_length")),
        # The length check comes before the state and segment checks and before suggestions.
        row("checks the length before the state", "XX", failed("bad_length")),
        row("checks the length before the segments", "EK00", failed("bad_length")),
        row("checks the length before a fixable segment", "EKO1A03FK1", failed("bad_length")),
        row("parses a state when partial codes are allowed", "EK", ok("EK"), PARTIAL),
        row("parses an LGA code when partial codes are allowed", "EK01", ok("EK01"), PARTIAL),
        row(
            "parses a district code when partial codes are allowed",
            "ek-01-a03",
            ok("EK01A03"),
            PARTIAL,
        ),
        row(
            "parses an area code when partial codes are allowed",
            "EK01A03FK",
            ok("EK01A03FK"),
            PARTIAL,
        ),
        row("parses a full code when partial codes are allowed", CODE, ok(CODE), PARTIAL),
        row(
            "rejects 3 characters when partial codes are allowed",
            "EK0",
            failed("bad_length"),
            PARTIAL,
        ),
        row(
            "rejects 5 characters when partial codes are allowed",
            "EK01A",
            failed("bad_length"),
            PARTIAL,
        ),
        row(
            "rejects 6 characters when partial codes are allowed",
            "EK01A0",
            failed("bad_length"),
            PARTIAL,
        ),
        row(
            "rejects 8 characters when partial codes are allowed",
            "EK01A03F",
            failed("bad_length"),
            PARTIAL,
        ),
        row(
            "rejects 10 characters when partial codes are allowed",
            "EK01A03FK0",
            failed("bad_length"),
            PARTIAL,
        ),
        row("parses a code padded to the input limit", CODE + " " * (limit - len(CODE)), ok(CODE)),
        row(
            "rejects input over the input limit",
            CODE + " " * (limit - len(CODE) + 1),
            failed("bad_length"),
        ),
        # 54 code points and 65 UTF-16 units. A runner that counts UTF-16 units rejects it.
        row(
            "counts code points, not UTF-16 units",
            MATH_BOLD_CODE + " " * (limit - 2 * len(CODE) + 1),
            ok(CODE),
        ),
        # 64 code points and 75 UTF-16 units. A runner that counts UTF-16 units rejects it.
        row(
            "parses an astral code padded to the input limit",
            MATH_BOLD_CODE + " " * (limit - len(CODE)),
            ok(CODE),
        ),
        # 65 code points, but 1 grapheme cluster and 64 code points after NFKC.
        row(
            "counts combining marks as code points",
            "E" + COMBINING_ACUTE * limit,
            failed("bad_length"),
        ),
        # 33 code points, but 77 after NFKC, because NFKC changes U+2026 to 3 full stops.
        row("counts the input before it normalises", CODE + HORIZONTAL_ELLIPSIS * 22, ok(CODE)),
        # 65 code points. In many regex engines, $ also matches before a final line feed.
        row(
            "rejects input over the limit that ends in a line feed",
            CODE + " " * (limit - len(CODE)) + LINE_FEED,
            failed("bad_length"),
        ),
    ]


def segment_rows() -> list[Row]:
    """Cases for segment rules and typo suggestions."""
    return [
        row("rejects an unknown state", "XX01A03FK01", failed("unknown_state", "state")),
        row("rejects the synthetic state ZZ", "ZZ01Z99ZZ01", failed("unknown_state", "state")),
        row(
            "suggests O for a zero in the state",
            "0G01A03FK01",
            failed("unknown_state", "state", "OG-01-A03-FK-01"),
        ),
        row(
            "suggests I for a one in the state",
            "1M01A03FK01",
            failed("unknown_state", "state", "IM-01-A03-FK-01"),
        ),
        row(
            "gives no suggestion when the fixed state is unknown",
            "E101A03FK01",
            failed("unknown_state", "state"),
        ),
        row(
            "gives no suggestion when the state cannot be fixed",
            "XXO1A03FK01",
            failed("unknown_state", "state"),
        ),
        row(
            "fixes later segments in a state suggestion",
            "0GO1A03FK01",
            failed("unknown_state", "state", "OG-01-A03-FK-01"),
        ),
        row("rejects an LGA of 00", "EK00A03FK01", failed("bad_segment", "lga")),
        row("rejects a unit of 00", "EK01A03FK00", failed("bad_segment", "unit")),
        row(
            "suggests 0 for a letter O in the LGA",
            "EKO1A03FK01",
            failed("bad_segment", "lga", "EK-01-A03-FK-01"),
        ),
        row(
            "suggests 1 for a letter I in the LGA",
            "EKI1A03FK01",
            failed("bad_segment", "lga", "EK-11-A03-FK-01"),
        ),
        row(
            "suggests 1 for a letter L in the LGA",
            "EKL1A03FK01",
            failed("bad_segment", "lga", "EK-11-A03-FK-01"),
        ),
        row(
            "suggests I for a one in the area",
            "EK01A03F101",
            failed("bad_segment", "area", "EK-01-A03-FI-01"),
        ),
        row(
            "suggests O for a zero in the area",
            "EK01A03F001",
            failed("bad_segment", "area", "EK-01-A03-FO-01"),
        ),
        row(
            "suggests 0 for a letter O in the unit",
            "EK01A03FKO1",
            failed("bad_segment", "unit", "EK-01-A03-FK-01"),
        ),
        row(
            "suggests 1 for a letter I in the unit",
            "EK01A03FKI2",
            failed("bad_segment", "unit", "EK-01-A03-FK-12"),
        ),
        row(
            "suggests 1 for a letter L in the unit",
            "EK01A03FKL1",
            failed("bad_segment", "unit", "EK-01-A03-FK-11"),
        ),
        row(
            "suggests 1 for a letter I after a zero in the unit",
            "EK01A03FK0I",
            failed("bad_segment", "unit", "EK-01-A03-FK-01"),
        ),
        row(
            "gives no suggestion when the fix makes a unit of 00",
            "EK01A03FK0O",
            failed("bad_segment", "unit"),
        ),
        row(
            "gives no suggestion when a segment cannot be fixed",
            "EK01A03F2O1",
            failed("bad_segment", "area"),
        ),
        row(
            "reports the first bad segment and fixes them all",
            "EKO1A03F1O1",
            failed("bad_segment", "lga", "EK-01-A03-FI-01"),
        ),
        row(
            "suggests a fix after making letters upper case",
            "eko1a03fk01",
            failed("bad_segment", "lga", "EK-01-A03-FK-01"),
        ),
        row(
            "rejects an LGA of 00 in a partial code", "EK00", failed("bad_segment", "lga"), PARTIAL
        ),
        row("suggests a partial code", "EKO1", failed("bad_segment", "lga", "EK-01"), PARTIAL),
        row(
            "suggests a partial area code",
            "EK01A03F1",
            failed("bad_segment", "area", "EK-01-A03-FI"),
            PARTIAL,
        ),
        row(
            "rejects an unknown state when partial codes are allowed",
            "XX",
            failed("unknown_state", "state"),
            PARTIAL,
        ),
        row(
            "suggests a state for a partial code",
            "0G",
            failed("unknown_state", "state", "OG"),
            PARTIAL,
        ),
        row(
            "suggests an LGA fix for a district code",
            "EKO1A03",
            failed("bad_segment", "lga", "EK-01-A03"),
            PARTIAL,
        ),
        row(
            "rejects an LGA of 00 in a district code",
            "EK00A03",
            failed("bad_segment", "lga"),
            PARTIAL,
        ),
        row(
            "keeps a letter O in the district when it fixes the LGA",
            "EKO1AO3FK01",
            failed("bad_segment", "lga", "EK-01-AO3-FK-01"),
        ),
        row(
            "keeps letters I and L in the district when it fixes the LGA",
            "EKO1AILFK01",
            failed("bad_segment", "lga", "EK-01-AIL-FK-01"),
        ),
        row(
            "accepts letters and digits in any district position", "EK01A0OFK01", ok("EK01A0OFK01")
        ),
    ]


def state_parse_rows() -> list[Row]:
    """One valid synthetic code for each state."""
    return [
        row(
            f"parses a code in {state['name']}",
            f"{state['code']}-01-Z99-ZZ-01",
            ok(f"{state['code']}01Z99ZZ01"),
        )
        for state in load_states()
    ]


def legacy_rows() -> list[Row]:
    """Cases for isLegacy."""
    limit = load_input_limit()
    return [
        row("accepts six digits", "900108", value(True)),
        row("accepts six digits with a space", "900 108", value(True)),
        row("accepts six full-width digits", full_width("900108"), value(True)),
        row("rejects five digits as a legacy code", "90010", value(False)),
        row("rejects seven digits", "9001080", value(False)),
        row("rejects a new postcode", CODE, value(False)),
        row("rejects empty input as a legacy code", "", value(False)),
        row("rejects a letter O among digits", "90O108", value(False)),
        row("rejects six Arabic-Indic digits as a legacy code", ARABIC_INDIC_LEGACY, value(False)),
        row(
            "finds a legacy code padded to the input limit",
            "900108" + " " * (limit - 6),
            value(True),
        ),
        row(
            "rejects a legacy code over the input limit",
            "900108" + " " * (limit - 5),
            value(False),
        ),
        # 65 code points, but 6 grapheme clusters. A grapheme counter gives true, because
        # normalize removes the joiners.
        row(
            "counts zero-width joiners as code points for legacy codes",
            "900108" + ZERO_WIDTH_JOINER * (limit - 5),
            value(False),
        ),
        # 26 code points, but 66 after NFKC, which changes U+2026 to 3 full stops. A count
        # after NFKC gives false.
        row(
            "counts the input before it normalises for legacy codes",
            "900108" + HORIZONTAL_ELLIPSIS * 20,
            value(True),
        ),
        # 65 code points. In many regex engines, $ also matches before a final line feed.
        row(
            "rejects a legacy code over the limit that ends in a line feed",
            "900108" + " " * (limit - 6) + LINE_FEED,
            value(False),
        ),
    ]


def truncate_rows() -> list[Row]:
    """Cases for truncate. Inputs are canonical codes."""
    full = "EK-01-A03-FK-01"
    return [
        row(
            "keeps a full code at unit precision", {"code": full, "to": "unit"}, {"canonical": full}
        ),
        row(
            "cuts a full code to its area",
            {"code": full, "to": "area"},
            {"canonical": "EK-01-A03-FK"},
        ),
        row(
            "cuts a full code to its district",
            {"code": full, "to": "district"},
            {"canonical": "EK-01-A03"},
        ),
        row("cuts a full code to its LGA", {"code": full, "to": "lga"}, {"canonical": "EK-01"}),
        row("cuts a full code to its state", {"code": full, "to": "state"}, {"canonical": "EK"}),
        row(
            "keeps a district code at district precision",
            {"code": "EK-01-A03", "to": "district"},
            {"canonical": "EK-01-A03"},
        ),
        row(
            "refuses to add precision to a district code",
            {"code": "EK-01-A03", "to": "area"},
            {"rejects": True},
        ),
        row(
            "refuses to add precision to a state code",
            {"code": "EK", "to": "lga"},
            {"rejects": True},
        ),
    ]


def parent_rows() -> list[Row]:
    """Cases for parent."""
    return [
        row(
            "gives the area of a full code",
            {"code": "EK-01-A03-FK-01"},
            {"canonical": "EK-01-A03-FK"},
        ),
        row(
            "gives the district of an area code",
            {"code": "EK-01-A03-FK"},
            {"canonical": "EK-01-A03"},
        ),
        row("gives the LGA of a district code", {"code": "EK-01-A03"}, {"canonical": "EK-01"}),
        row("gives the state of an LGA code", {"code": "EK-01"}, {"canonical": "EK"}),
        row("gives nothing for a state code", {"code": "EK"}, {"canonical": None}),
    ]


def contains_rows() -> list[Row]:
    """Cases for contains."""
    full = "EK-01-A03-FK-01"
    return [
        row(
            "finds a full code in its district", {"prefix": "EK-01-A03", "code": full}, value(True)
        ),
        row("finds a full code in its state", {"prefix": "EK", "code": full}, value(True)),
        row("finds a code in itself", {"prefix": full, "code": full}, value(True)),
        row(
            "finds a unit in its area",
            {"prefix": "EK-01-A03-FK", "code": "EK-01-A03-FK-02"},
            value(True),
        ),
        row(
            "rejects a code from another district",
            {"prefix": "EK-01-A04", "code": full},
            value(False),
        ),
        row("rejects a code from another state", {"prefix": "FC", "code": full}, value(False)),
        row(
            "rejects a less precise code inside a more precise one",
            {"prefix": full, "code": "EK-01-A03"},
            value(False),
        ),
        row("rejects a different unit", {"prefix": full, "code": "EK-01-A03-FK-02"}, value(False)),
    ]


def redact_rows() -> list[Row]:
    """Cases for redact."""
    return [
        row("hides the unit of a full code", {"code": "EK-01-A03-FK-01"}, value("EK-01-A03-FK-**")),
        row("keeps an area code as it is", {"code": "EK-01-A03-FK"}, value("EK-01-A03-FK")),
        row("keeps a state code as it is", {"code": "EK"}, value("EK")),
    ]


def state_name_rows() -> list[Row]:
    """Cases for stateName: one for each state, then the edge cases."""
    named = [
        row(f"names {state['code']}", state["code"], value(state["name"]))
        for state in load_states()
    ]
    return [
        *named,
        row("accepts lower case", "ek", value("Ekiti")),
        row("accepts mixed case", "Fc", value("Federal Capital Territory")),
        row("returns nothing for an unknown code", "XX", value(None)),
        row("returns nothing for empty input", "", value(None)),
        row("returns nothing for three letters", "EKI", value(None)),
        row("returns nothing for a code with spaces", " EK ", value(None)),
        row("returns nothing for a code with a leading space", " EK", value(None)),
        row("returns nothing for a code with a trailing space", "EK ", value(None)),
        row("returns nothing for full-width letters", full_width("EK"), value(None)),
        # Python's upper() changes U+017F to S and U+0131 to I. These two would give Osun and Imo.
        row("returns nothing for a long s", "O" + LONG_S, value(None)),
        row("returns nothing for a dotless i", DOTLESS_I + "M", value(None)),
    ]


def accuracy_rows() -> list[Row]:
    """Cases for precisionForAccuracy.

    Runners turn the strings NaN, Infinity and -Infinity into numbers.
    """
    return [
        row("gives the unit at 0 m", 0, value("unit")),
        row("gives the unit at 5 m", 5, value("unit")),
        row("gives the unit at exactly 8 m", 8, value("unit")),
        row("gives the area just above 8 m", 8.1, value("area")),
        row("gives the area at exactly 20 m", 20, value("area")),
        row("gives the district above 20 m", 20.5, value("district")),
        row("gives the district at exactly 50 m", 50, value("district")),
        row("gives the LGA just above 50 m", 50.1, value("lga")),
        row("gives the LGA at 1000 m", 1000, value("lga")),
        row("gives the LGA when the accuracy is unknown", None, value("lga")),
        row("gives the LGA for a negative accuracy", -1, value("lga")),
        row("gives the LGA for NaN", "NaN", value("lga")),
        row("gives the LGA for infinity", "Infinity", value("lga")),
        row("gives the LGA for negative infinity", "-Infinity", value("lga")),
    ]


FILES: dict[str, tuple[str, str, Callable[[], list[Row]]]] = {
    "normalize": ("normalize", "Cleans input before parsing.", normalize_rows),
    "parse": ("parse", "Forms, lengths, characters and legacy codes.", parse_rows),
    "parse-segments": ("parse", "Segment rules and typo suggestions.", segment_rows),
    "parse-states": ("parse", "One valid code for each state.", state_parse_rows),
    "is-legacy": ("isLegacy", "Finds old 6-digit postcodes.", legacy_rows),
    "truncate": ("truncate", "Cuts a code to a less precise segment.", truncate_rows),
    "parent": ("parent", "Gives the code one segment shorter.", parent_rows),
    "contains": ("contains", "Checks that one code lies inside another.", contains_rows),
    "redact": ("redact", "Hides the unit for logs.", redact_rows),
    "state-name": ("stateName", "Names the state for a state code.", state_name_rows),
    "precision-for-accuracy": (
        "precisionForAccuracy",
        "Maps GPS accuracy to precision.",
        accuracy_rows,
    ),
}


def render(stem: str) -> str:
    """Build the JSON text of one vector file."""
    function, description, rows = FILES[stem]
    cases = [
        {
            "id": f"{stem}-{index:03d}",
            "description": text,
            "input": input_,
            "options": options,
            "expect": expect,
        }
        for index, (text, input_, expect, options) in enumerate(rows(), start=1)
    ]
    document = {
        "version": FORMAT_VERSION,
        "function": function,
        "description": description,
        "cases": cases,
    }
    return json.dumps(document, ensure_ascii=True, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the vector files, or with --check, report the ones that are out of date.

    In both modes, report each JSON file in vectors/ that the builder does not write.
    """
    parser = argparse.ArgumentParser(description="Build the shared test vectors.")
    parser.add_argument(
        "--check", action="store_true", help="Fail if a vector file is out of date."
    )
    args = parser.parse_args(argv)
    if not args.check:
        VECTORS.mkdir(exist_ok=True)
    stale: list[str] = []
    for stem in FILES:
        path = VECTORS / f"{stem}.json"
        text = render(stem)
        if not args.check:
            path.write_text(text, encoding="utf-8")
        elif not path.exists() or path.read_text(encoding="utf-8") != text:
            stale.append(path.name)
    strays = sorted(path.name for path in VECTORS.glob("*.json") if path.stem not in FILES)
    if stale:
        sys.stderr.write(
            f"Out of date: {', '.join(stale)}. Run python3 scripts/build_vectors.py.\n"
        )
    for name in strays:
        sys.stderr.write(f"vectors/{name} is not a builder output. Remove it.\n")
    if stale or strays:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
