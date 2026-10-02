# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""A plain reading of grammar.md, with every value taken from data/.

The builder holds its expected results as typed literals, so nothing else ties the vectors to
the grammar. This module is a second reading. It does not import the builder, and it keeps no
number, code or table that data/ holds. The tests run every vector through it, so a vector or a
data file that contradicts grammar.md fails there.

No vector can carry text that is not well-formed, so this module leaves out the rules for such
text (grammar.md, Parse).
"""

from __future__ import annotations

import json
import math
import re
import string
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from itertools import accumulate, pairwise, zip_longest
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

LETTERS = frozenset(string.ascii_uppercase)
DIGITS = frozenset(string.digits)
# The words that data/format.json uses for the characters of a segment.
CHARACTER_SETS = {
    "letters": LETTERS,
    "digits": DIGITS,
    "letters-or-digits": LETTERS | DIGITS,
}
# str.upper() would also change letters such as U+0131, which grammar.md keeps.
ASCII_UPPER_CASE = str.maketrans(string.ascii_lowercase, string.ascii_uppercase)
# Only these two codes name a segment and offer a suggestion.
CODES_WITH_SUGGESTION = frozenset({"unknown_state", "bad_segment"})
UNIT_MASK = "**"

# The segments of an accepted postcode, from the state down to its precision.
Postcode = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SegmentRule:
    """The rule for one segment, as data/format.json gives it. A minimum applies to digits."""

    name: str
    length: int
    characters: str
    minimum: int | None


@dataclass(frozen=True, slots=True)
class Failure:
    """A parse error. The segment and the suggestion are None where grammar.md says null."""

    code: str
    segment: str | None = None
    suggestion: str | None = None


@dataclass(frozen=True, slots=True)
class Grammar:
    """The rules of grammar.md, filled with the values of data/."""

    input_limit: int
    segments: tuple[SegmentRule, ...]
    legacy: re.Pattern[str]
    separators: frozenset[str]
    fixes: Mapping[str, Mapping[str, str]]
    states: Mapping[str, str]
    limits: tuple[tuple[float, str], ...]
    fallback: str

    def normalize(self, text: str) -> str:
        """Apply NFKC, remove the separators, then make the ASCII letters upper case."""
        folded = unicodedata.normalize("NFKC", text)
        kept = "".join(character for character in folded if character not in self.separators)
        return kept.translate(ASCII_UPPER_CASE)

    def parse(self, text: str, *, allow_partial: bool = False) -> Postcode | Failure:
        """Read text as a postcode. Over the input limit, give bad_length before normalising."""
        if len(text) > self.input_limit:
            return Failure("bad_length")
        compact = self.normalize(text)
        outcome = self._read_compact(compact, allow_partial)
        if isinstance(outcome, Failure) and outcome.code in CODES_WITH_SUGGESTION:
            return replace(outcome, suggestion=self._suggest(compact, allow_partial))
        return outcome

    def is_legacy(self, text: str) -> bool:
        """Tell whether the text is an old postcode. Over the input limit, the answer is no."""
        if len(text) > self.input_limit:
            return False
        # fullmatch, because a pattern that ends in $ also matches before a final line feed.
        return self.legacy.fullmatch(self.normalize(text)) is not None

    def precision(self, code: Postcode) -> str:
        """Name the last segment of the code."""
        return self.segments[len(code) - 1].name

    def truncate(self, code: Postcode, to: str) -> Postcode:
        """Keep the segments up to a precision. A precision that the code lacks is an error."""
        ranks = {rule.name: rank for rank, rule in enumerate(self.segments, start=1)}
        if to not in ranks or ranks[to] > len(code):
            raise ValueError(f"The code {'-'.join(code)} has no {to!r} precision.")
        return code[: ranks[to]]

    def parent(self, code: Postcode) -> Postcode | None:
        """Drop the last segment. A code with only the state has no parent."""
        return code[:-1] if len(code) > 1 else None

    def contains(self, prefix: Postcode, code: Postcode) -> bool:
        """Tell whether the code has every segment of the prefix, in the same places."""
        return code[: len(prefix)] == prefix

    def redact(self, code: Postcode) -> str:
        """Write the canonical form with the unit hidden. A code without a unit is unchanged."""
        if len(code) == len(self.segments):
            code = (*code[:-1], UNIT_MASK)
        return "-".join(code)

    def state_name(self, code: str) -> str | None:
        """Look up a state code. Only the ASCII letters a to z change case, and NFKC is not used."""
        return self.states.get(code.translate(ASCII_UPPER_CASE))

    def precision_for_accuracy(self, metres: float | None) -> str:
        """Give the most precise segment that a GPS fix of this accuracy supports."""
        # -0.0 is not below 0, so it counts as 0 here. Testing the sign bit would give lga.
        if metres is None or not math.isfinite(metres) or metres < 0:
            return self.fallback
        for limit, precision in self.limits:
            if metres <= limit:
                return precision
        return self.fallback

    def _lengths(self, allow_partial: bool) -> frozenset[int]:
        """Give the lengths that pass: the full length, and each segment end for a partial code."""
        ends = list(accumulate(rule.length for rule in self.segments))
        return frozenset(ends if allow_partial else ends[-1:])

    def _split(self, compact: str) -> Postcode:
        """Cut text of a valid length into its segments."""
        bounds = [0, *accumulate(rule.length for rule in self.segments)]
        return tuple(compact[start:end] for start, end in pairwise(bounds) if start < len(compact))

    def _read_compact(self, compact: str, allow_partial: bool) -> Postcode | Failure:
        """Run the checks of grammar.md on normalised text. Offer no suggestion."""
        failure = self._reject_text(compact, allow_partial)
        if failure is not None:
            return failure
        segments = self._split(compact)
        failure = self._reject_segments(segments)
        return segments if failure is None else failure

    def _reject_text(self, compact: str, allow_partial: bool) -> Failure | None:
        """Run the checks on the whole text: empty, legacy_code, bad_character and bad_length."""
        if not compact:
            return Failure("empty")
        if self.legacy.fullmatch(compact):
            return Failure("legacy_code")
        if not set(compact) <= LETTERS | DIGITS:
            return Failure("bad_character")
        if len(compact) not in self._lengths(allow_partial):
            return Failure("bad_length")
        return None

    def _reject_segments(self, segments: Postcode) -> Failure | None:
        """Run the checks on the segments, in order: unknown_state, then bad_segment."""
        if segments[0] not in self.states:
            return Failure("unknown_state", self.segments[0].name)
        # A partial code has fewer segments than rules, so zip stops at the last segment.
        for rule, segment in zip(self.segments, segments, strict=False):
            if not _fits(rule, segment):
                return Failure("bad_segment", rule.name)
        return None

    def _suggest(self, compact: str, allow_partial: bool) -> str | None:
        """Parse the code with its look-alike characters fixed. Give its canonical form."""
        fixed = self._fix(compact)
        # An unchanged code fails the same way, so it has no suggestion.
        if fixed == compact:
            return None
        # The fixed code has only A to Z and 0 to 9, so it needs no normalising.
        outcome = self._read_compact(fixed, allow_partial)
        return None if isinstance(outcome, Failure) else "-".join(outcome)

    def _fix(self, compact: str) -> str:
        """Change the characters that data/format.json lists, in the kinds of segment it names."""
        fixed: list[str] = []
        # A kind with no table, such as the district, keeps its characters.
        for rule, segment in zip(self.segments, self._split(compact), strict=False):
            table = self.fixes.get(rule.characters, {})
            fixed.append("".join(table.get(character, character) for character in segment))
        return "".join(fixed)


def _fits(rule: SegmentRule, segment: str) -> bool:
    """Tell whether a segment has the characters of its rule and reaches its minimum."""
    allowed = set(segment) <= CHARACTER_SETS[rule.characters]
    return allowed and (rule.minimum is None or int(segment) >= rule.minimum)


def load(data_dir: Path = DATA_DIR) -> Grammar:
    """Read format.json, states.json and precision.json from a folder."""
    layout = _read_json(data_dir / "format.json")
    states = _read_json(data_dir / "states.json")["states"]
    precision = _read_json(data_dir / "precision.json")
    return Grammar(
        input_limit=layout["maxInputCodePoints"],
        segments=tuple(
            SegmentRule(
                segment["name"], segment["length"], segment["characters"], segment.get("minimum")
            )
            for segment in layout["segments"]
        ),
        legacy=re.compile(layout["legacyPattern"]),
        separators=frozenset(
            chr(int(label.removeprefix("U+"), 16)) for label in layout["separators"]
        ),
        fixes=layout["suggestions"],
        states={state["code"]: state["name"] for state in states},
        limits=tuple((row["maxAccuracyM"], row["precision"]) for row in precision["thresholds"]),
        fallback=precision["fallback"],
    )


def _read_json(path: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return document


Case = Mapping[str, Any]
Expected = dict[str, Any]
Reader = Callable[[Grammar, Case], Expected]


def _postcode(grammar: Grammar, canonical: str) -> Postcode:
    """Read an input of a hierarchy vector. The runner rules say to parse it with allowPartial."""
    outcome = grammar.parse(canonical, allow_partial=True)
    if isinstance(outcome, Failure):
        raise ValueError(
            f"The vector input {canonical!r} does not parse. Check the vector and data/."
        )
    return outcome


def _success(grammar: Grammar, code: Postcode) -> Expected:
    """Write an accepted code the way a vector does."""
    names = [rule.name for rule in grammar.segments]
    return {
        "ok": True,
        "compact": "".join(code),
        "canonical": "-".join(code),
        "display": " ".join(code),
        "precision": grammar.precision(code),
        # zip_longest gives null for each segment after the precision.
        "segments": dict(zip_longest(names, code)),
    }


def _read_normalize(grammar: Grammar, case: Case) -> Expected:
    return {"value": grammar.normalize(case["input"])}


def _read_parse(grammar: Grammar, case: Case) -> Expected:
    outcome = grammar.parse(case["input"], allow_partial=bool(case["options"].get("allowPartial")))
    if isinstance(outcome, Failure):
        error = {"code": outcome.code, "segment": outcome.segment, "suggestion": outcome.suggestion}
        return {"ok": False, "error": error}
    return _success(grammar, outcome)


def _read_is_legacy(grammar: Grammar, case: Case) -> Expected:
    return {"value": grammar.is_legacy(case["input"])}


def _read_truncate(grammar: Grammar, case: Case) -> Expected:
    code = _postcode(grammar, case["input"]["code"])
    try:
        shorter = grammar.truncate(code, case["input"]["to"])
    except ValueError:
        return {"rejects": True}
    return {"canonical": "-".join(shorter)}


def _read_parent(grammar: Grammar, case: Case) -> Expected:
    above = grammar.parent(_postcode(grammar, case["input"]["code"]))
    return {"canonical": None if above is None else "-".join(above)}


def _read_contains(grammar: Grammar, case: Case) -> Expected:
    prefix = _postcode(grammar, case["input"]["prefix"])
    return {"value": grammar.contains(prefix, _postcode(grammar, case["input"]["code"]))}


def _read_redact(grammar: Grammar, case: Case) -> Expected:
    return {"value": grammar.redact(_postcode(grammar, case["input"]["code"]))}


def _read_state_name(grammar: Grammar, case: Case) -> Expected:
    return {"value": grammar.state_name(case["input"])}


def _read_precision_for_accuracy(grammar: Grammar, case: Case) -> Expected:
    metres = case["input"]
    # The runner rules turn the strings NaN, Infinity and -Infinity into numbers.
    if isinstance(metres, str):
        metres = float(metres)
    return {"value": grammar.precision_for_accuracy(metres)}


# One reader for each function that a vector file tests, by the name in its function field.
READERS: dict[str, Reader] = {
    "normalize": _read_normalize,
    "parse": _read_parse,
    "isLegacy": _read_is_legacy,
    "truncate": _read_truncate,
    "parent": _read_parent,
    "contains": _read_contains,
    "redact": _read_redact,
    "stateName": _read_state_name,
    "precisionForAccuracy": _read_precision_for_accuracy,
}
