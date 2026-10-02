# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for reference: it agrees with every vector, and it reads each value from data/."""

import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

import reference

from tests.test_data import grammar_section

ROOT = Path(__file__).resolve().parents[2]
CODE = "EK01A03FK01"

Edit = Callable[[dict[str, Any]], object]
Probe = Callable[[reference.Grammar], object]


def rename_ekiti(document: dict[str, Any]) -> None:
    for state in document["states"]:
        if state["code"] == "EK":
            state["name"] = "Ekiti State"


def remove_ekiti(document: dict[str, Any]) -> None:
    document["states"] = [state for state in document["states"] if state["code"] != "EK"]


# One row for each value in data/: the edit that changes it, and a call whose answer must change
# with it. A reference that keeps its own copy of the value gives the same answer both times.
DATA_CHANGES: dict[str, tuple[dict[str, Edit], Probe]] = {
    "the input limit": (
        {"format": lambda document: document.update(maxInputCodePoints=12)},
        lambda grammar: grammar.parse(CODE + "  "),
    ),
    "a separator": (
        {"format": lambda document: document["separators"].remove("U+002D")},
        lambda grammar: grammar.normalize("EK-01"),
    ),
    "the length of a segment": (
        {"format": lambda document: document["segments"][1].update(length=3)},
        lambda grammar: grammar.parse(CODE),
    ),
    "the characters of a segment": (
        {"format": lambda document: document["segments"][2].update(characters="letters")},
        lambda grammar: grammar.parse(CODE),
    ),
    "the minimum of a segment": (
        {"format": lambda document: document["segments"][1].update(minimum=2)},
        lambda grammar: grammar.parse(CODE),
    ),
    "a fix for a letter segment": (
        {"format": lambda document: document["suggestions"]["letters"].update({"5": "S"})},
        lambda grammar: grammar.parse("EK01A03F501"),
    ),
    "a fix for a digit segment": (
        {"format": lambda document: document["suggestions"]["digits"].update({"B": "8"})},
        lambda grammar: grammar.parse("EK0BA03FK01"),
    ),
    "the legacy pattern": (
        {"format": lambda document: document.update(legacyPattern="^[0-9]{6,7}$")},
        lambda grammar: grammar.is_legacy("9001080"),
    ),
    "a state code": ({"states": remove_ekiti}, lambda grammar: grammar.parse(CODE)),
    "a state name": ({"states": rename_ekiti}, lambda grammar: grammar.state_name("EK")),
    "a GPS limit": (
        {"precision": lambda document: document["thresholds"][1].update(maxAccuracyM=25)},
        lambda grammar: grammar.precision_for_accuracy(22),
    ),
    "the GPS fallback": (
        {"precision": lambda document: document.update(fallback="district")},
        lambda grammar: grammar.precision_for_accuracy(None),
    ),
}


def vector_documents() -> list[tuple[str, dict[str, Any]]]:
    paths = sorted((ROOT / "vectors").glob("*.json"))
    return [(path.name, json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def load_with(edits: dict[str, Edit]) -> reference.Grammar:
    """Load the data files from a temporary folder, after the edits to the named files."""
    with tempfile.TemporaryDirectory() as folder:
        for stem in ("format", "states", "precision"):
            source = reference.DATA_DIR / f"{stem}.json"
            document = json.loads(source.read_text(encoding="utf-8"))
            if stem in edits:
                edits[stem](document)
            (Path(folder) / f"{stem}.json").write_text(json.dumps(document), encoding="utf-8")
        return reference.load(Path(folder))


class ReferenceVectorsTest(unittest.TestCase):
    def test_each_vector_file_has_a_reader(self) -> None:
        missing = [
            f"{name}: {document['function']}"
            for name, document in vector_documents()
            if document["function"] not in reference.READERS
        ]
        self.assertEqual(missing, [])

    def test_each_case_gives_its_expected_value(self) -> None:
        grammar = reference.load()
        for _, document in vector_documents():
            reader = reference.READERS.get(document["function"])
            if reader is None:
                continue
            for case in document["cases"]:
                with self.subTest(case["id"], description=case["description"]):
                    self.assertEqual(reader(grammar, case), case["expect"])


class ReferenceDataTest(unittest.TestCase):
    def test_each_data_value_changes_what_the_reference_reads(self) -> None:
        unchanged = reference.load()
        for name, (edits, probe) in DATA_CHANGES.items():
            with self.subTest(name):
                self.assertNotEqual(probe(load_with(edits)), probe(unchanged))

    def test_truncate_rejects_a_value_that_is_not_a_precision(self) -> None:
        grammar = reference.load()
        code = ("EK", "01", "A03")
        for precision in ("street", "", "UNIT"):
            with self.subTest(precision=precision), self.assertRaises(ValueError):
                grammar.truncate(code, precision)

    def test_truncate_rejects_a_precision_that_the_code_lacks(self) -> None:
        with self.assertRaises(ValueError):
            reference.load().truncate(("EK", "01", "A03"), "area")


class InterfaceTest(unittest.TestCase):
    def test_the_interface_names_each_function_that_a_vector_file_tests(self) -> None:
        interface = grammar_section("Interface")
        functions = {document["function"] for _, document in vector_documents()}
        missing = sorted(name for name in functions if f"`{name}(" not in interface)
        self.assertEqual(missing, [])
        self.assertIn("`SPEC_VERSION`", interface)

    def test_the_interface_names_each_field_of_a_parse_result(self) -> None:
        interface = grammar_section("Interface")
        expected = [
            case["expect"]
            for _, document in vector_documents()
            if document["function"] == "parse"
            for case in document["cases"]
        ]
        fields = {field for outcome in expected for field in outcome}
        fields |= {
            field for outcome in expected if "error" in outcome for field in outcome["error"]
        }
        fields |= {field for outcome in expected if outcome["ok"] for field in outcome["segments"]}
        self.assertEqual(sorted(field for field in fields if f"`{field}`" not in interface), [])
        self.assertIn("after the precision is null", interface)
