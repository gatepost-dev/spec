# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for build_vectors."""

import json
import math
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

import build_vectors

ROOT = Path(__file__).resolve().parents[2]


def load(stem: str) -> dict[str, Any]:
    value: object = json.loads((ROOT / "vectors" / f"{stem}.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{stem}.json must hold a JSON object.")
    return value


class BuildVectorsTest(unittest.TestCase):
    def test_vector_files_match_the_builder(self) -> None:
        self.assertEqual(build_vectors.main(["--check"]), 0)

    def test_vector_files_are_ascii(self) -> None:
        for path in sorted((ROOT / "vectors").glob("*.json")):
            with self.subTest(file=path.name):
                self.assertTrue(path.read_text(encoding="utf-8").isascii())

    def test_each_case_has_a_unique_id_and_a_description(self) -> None:
        ids: list[str] = []
        for stem in build_vectors.FILES:
            for case in load(stem)["cases"]:
                ids.append(case["id"])
                self.assertTrue(case["description"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 200)

    def test_each_description_is_unique_across_all_vector_files(self) -> None:
        counts = Counter(
            case["description"] for stem in build_vectors.FILES for case in load(stem)["cases"]
        )
        repeated = sorted(text for text, count in counts.items() if count > 1)
        self.assertEqual(repeated, [])

    def test_each_state_has_a_parse_case_and_a_name_case(self) -> None:
        states = json.loads((ROOT / "data" / "states.json").read_text(encoding="utf-8"))
        codes = {state["code"] for state in states["states"]}
        parsed = {case["input"][:2] for case in load("parse-states")["cases"]}
        named = {case["input"] for case in load("state-name")["cases"]}
        self.assertEqual(parsed, codes)
        self.assertLessEqual(codes, named)

    def test_each_gps_limit_has_a_case_at_the_limit_and_a_case_above_it(self) -> None:
        rules = json.loads((ROOT / "data" / "precision.json").read_text(encoding="utf-8"))
        limits = [threshold["maxAccuracyM"] for threshold in rules["thresholds"]]
        at_limit = [threshold["precision"] for threshold in rules["thresholds"]]
        above_limit = [*at_limit[1:], rules["fallback"]]
        ceilings = [*limits[1:], math.inf]
        measured = [
            (case["input"], case["expect"]["value"])
            for case in load("precision-for-accuracy")["cases"]
            if isinstance(case["input"], int | float)
        ]
        for limit, ceiling, precision, next_precision in zip(
            limits, ceilings, at_limit, above_limit, strict=True
        ):
            with self.subTest(limit=limit):
                self.assertIn((limit, precision), measured)
                above = [expected for metres, expected in measured if limit < metres <= ceiling]
                self.assertIn(next_precision, above)
