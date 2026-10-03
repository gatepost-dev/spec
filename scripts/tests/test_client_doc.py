# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for client.md: each rule says what a client does, and the standards point to it."""

import re
import tempfile
import unittest
from pathlib import Path

import contract_files
import scenario_truth

CLIENT = contract_files.CLIENT_DOC.read_text(encoding="utf-8")
TYPESCRIPT = contract_files.ROOT / "standards" / "languages" / "typescript.md"
STANDARDS = contract_files.ROOT / "standards" / "CODING_STANDARDS.md"


def section(text: str, heading: str) -> str:
    """Return the text under a heading, up to the next heading of the same or a higher level."""
    level = heading.split(" ", maxsplit=1)[0]
    body = text.partition(f"\n{heading}\n")[2]
    return re.split(rf"\n#{{1,{len(level)}}} ", body)[0]


def bullets(text: str, lead: str) -> list[str]:
    """Return the sub-bullets under the bullet that starts with lead."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"- {lead}"))
    found = []
    for line in lines[start + 1 :]:
        if not line.startswith("  - "):
            break
        found.append(line[4:])
    return found


def row(text: str, first_cell: str) -> list[str]:
    """Return the cells of the table row whose first cell starts with first_cell."""
    line = next(x for x in text.splitlines() if x.startswith(f"| {first_cell}"))
    return [cell.strip() for cell in line.strip("|").split("|")]


class LookupResultTest(unittest.TestCase):
    def test_a_status_is_text_and_an_unknown_value_stays_as_it_is(self) -> None:
        part = section(CLIENT, "### Lookup result")
        cells = row(part, "`status`")
        self.assertTrue(cells[1].startswith("text, or null"))
        self.assertIn("The known values are", cells[1])
        bullet = next(x for x in part.splitlines() if x.startswith("- `status` is null"))
        self.assertIn("returns any other value of `status` as it is", bullet)
        self.assertNotIn("is null when the response has no `status`, or", bullet)

    def test_a_status_that_is_not_text_is_an_unexpected_response(self) -> None:
        part = section(CLIENT, "### Lookup result")
        bullet = next(x for x in part.splitlines() if "and not text" in x)
        self.assertIn("`unexpected_response`", bullet)


class RequestRulesTest(unittest.TestCase):
    requests = section(CLIENT, "## Requests")

    def test_a_bad_input_value_raises_invalid_input_before_any_request(self) -> None:
        lead = "Each of these raises `invalid_input`, and the client sends no request:"
        self.assertEqual(
            [re.sub(r" The .*", "", rule) for rule in bullets(self.requests, lead)],
            [
                "A `level` that is not a whole number from 1 to 5.",
                "A `lat` that is not finite or is outside -90 to 90.",
                "A `lng` that is not finite or is outside -180 to 180.",
                "A `maxDistanceM` below 0 or above 250.",
            ],
        )

    def test_a_distance_over_250_is_rejected_because_the_gateway_would_clamp_it(self) -> None:
        lead = "Each of these raises `invalid_input`, and the client sends no request:"
        rule = bullets(self.requests, lead)[3]
        self.assertIn("the gateway cuts a larger value to 250 without a sign", rule)
        self.assertIn("so the client rejects it", rule)
        self.assertNotIn("is clamped", self.requests)

    def test_each_input_rule_names_its_scenario(self) -> None:
        lead = "Each of these raises `invalid_input`, and the client sends no request:"
        rules = bullets(self.requests, lead)
        names = [re.findall(r"`([a-z-]+-invalid-[a-z-]+)`", rule) for rule in rules]
        self.assertEqual(
            names,
            [
                ["lookup-invalid-level"],
                ["reverse-invalid-lat"],
                ["reverse-invalid-lng"],
                ["reverse-invalid-max-distance", "reverse-invalid-negative-distance"],
            ],
        )

    def test_a_number_is_written_in_its_shortest_decimal_form(self) -> None:
        bullet = next(x for x in self.requests.splitlines() if "shortest decimal form" in x)
        for text in (
            "with no exponent and no trailing zero",
            "`lat=9`, not `lat=9.0`",
            "A negative zero is written `0`",
            "`0.0000001`, not `1e-7`",
            "The mock server compares numbers by value",
            "`reverse-plain-decimal`",
            "`reverse-whole-number`",
        ):
            self.assertIn(text, bullet)


class UnknownFieldsTest(unittest.TestCase):
    def test_a_field_that_the_contract_does_not_use_never_changes_a_result(self) -> None:
        paragraph = next(x for x in CLIENT.split("\n\n") if x.startswith("A client ignores"))
        self.assertIn("a field that this contract does not use", paragraph)
        self.assertIn("never changes the result and never raises an error", paragraph)
        for call in ("lookup", "reverse", "autocomplete"):
            self.assertIn(f"`{call}-unknown-fields`", paragraph)
        self.assertIn("`lookup-unknown-status`", paragraph)


class ErrorRulesTest(unittest.TestCase):
    errors = section(CLIENT, "## Errors")

    def test_each_condition_gives_its_error_code(self) -> None:
        table = [
            [cell.strip() for cell in line.strip("|").split("|")]
            for line in self.errors.splitlines()
            if re.match(r"^\| [^|]+ \| `[a-z_]+` \|", line)
        ]
        self.assertEqual(
            {cells[0]: cells[1] for cells in table},
            {
                "the client's own check of the input fails": "`invalid_input`",
                "status 401": "`unauthorized`",
                "status 402": "`insufficient_credits`",
                "status 403, with the API code `origin_not_allowed`": "`origin_not_allowed`",
                "status 403, with any other API code": "`forbidden`",
                "status 429": "`rate_limited`",
                "status 502, 503 or 504": "`server_error`",
                "any other status from 400 to 499": "`invalid_input`",
                "any other status that is not 200": "`server_error`",
                "status 200, with a body that is not a JSON object with a `data` field, "
                "or with a part that this contract uses missing or of the wrong type": (
                    "`unexpected_response`"
                ),
                "no response, because the connection failed": "`network_error`",
                "no response within `timeoutMs`": "`timeout`",
            },
        )

    def test_a_broken_reply_gives_no_guessed_value(self) -> None:
        text = self.errors
        self.assertIn("The client never returns a guessed empty value", text)


class RetryRulesTest(unittest.TestCase):
    retries = section(CLIENT, "## Retries")

    def test_a_call_has_a_total_deadline(self) -> None:
        bullet = next(x for x in self.retries.splitlines() if "total deadline" in x)
        self.assertIn("starts when the client sends the first attempt", bullet)
        self.assertIn("`(1 + maxRetries) x timeoutMs`", bullet)
        self.assertIn("`500 x 2^(n - 1) + 250`", bullet)
        self.assertIn("raises the error of the last attempt at once", bullet)
        seconds = scenario_truth.deadline_ms(8000, 2) // 1000
        self.assertIn(f"With the defaults for `lookup`, that is {seconds} seconds.", bullet)
        self.assertIn("`lookup-deadline`", bullet)

    def test_a_retry_after_on_a_5xx_is_used_when_valid_and_short(self) -> None:
        bullet = next(x for x in self.retries.splitlines() if x.startswith("- A 502, 503"))
        self.assertIn("valid `Retry-After` of 10 seconds or less", bullet)
        self.assertIn("with no random part", bullet)
        self.assertIn("a whole number of seconds from 0 up, or an HTTP date", bullet)
        self.assertIn("its own wait", bullet)
        self.assertIn("`lookup-retry-after-503`", bullet)
        self.assertIn("`lookup-retry-after-invalid`", bullet)

    def test_autocomplete_waits_15_seconds_and_the_other_calls_8(self) -> None:
        options = section(CLIENT, "### Client options")
        cells = row(options, "`timeoutMs`")
        self.assertEqual(cells[2], "8000, and 15000 for `autocomplete`")
        self.assertNotIn("is open", options)


class SharingRulesTest(unittest.TestCase):
    sharing = section(CLIENT, "## Sharing, queue and cache")

    def test_two_spellings_of_one_postcode_share_one_request(self) -> None:
        bullet = next(x for x in self.sharing.splitlines() if "canonical form" in x)
        self.assertIn('`lookup("fc01z99zz01")` and `lookup("FC-01-Z99-ZZ-01")`', bullet)
        self.assertIn("share one request and one cache entry", bullet)
        self.assertIn("`lookup-shared-spellings`", bullet)

    def test_a_shared_request_stops_only_when_every_caller_cancels(self) -> None:
        bullet = next(x for x in self.sharing.splitlines() if "cancels" in x)
        self.assertIn("only when every caller that shares it cancels", bullet)

    def test_a_cancelled_call_frees_its_place_among_the_four_at_once(self) -> None:
        self.assertIn("A cancelled call frees its place among the 4 at once", self.sharing)

    def test_the_rules_that_only_a_client_can_test_are_listed(self) -> None:
        untested = section(CLIENT, "## Rules that no scenario tests")
        for text in ("shared request", "frees its place", "15 seconds"):
            self.assertIn(text, untested)


class StandardsTest(unittest.TestCase):
    def test_the_ranking_line_and_api_1_send_the_reader_to_client_md(self) -> None:
        lines = STANDARDS.read_text(encoding="utf-8").splitlines()
        ranking = next(x for x in lines if "rank above this document" in x)
        api_1 = next(x for x in lines if x.startswith("- **API-1"))
        self.assertIn("`spec/client.md`", ranking)
        self.assertIn("`spec/client.md` wins over a scenario", ranking)
        self.assertIn("`spec/client.md`", api_1)

    def test_the_mock_server_section_does_not_list_the_core_only_rule(self) -> None:
        text = TYPESCRIPT.read_text(encoding="utf-8")
        mock = section(text, "## The mock server")
        self.assertIn("These rules do not apply to it:", mock)
        self.assertNotIn("CS-2", mock)


class ErrorTableReaderTest(unittest.TestCase):
    def test_a_file_with_no_errors_section_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "client.md"
            path.write_text("# Client\n\n## Requests\n\n| a | `x` | no |\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                contract_files.error_codes(path)


class ScenarioNamesTest(unittest.TestCase):
    def test_each_scenario_that_client_md_names_exists(self) -> None:
        scenarios = contract_files.load_scenarios()
        names = set(re.findall(r"`((?:lookup|reverse|autocomplete)-[a-z0-9-]+)`", CLIENT))
        self.assertGreaterEqual(len(names), 19)
        self.assertEqual(sorted(names - set(scenarios)), [])


class RuleScenarioTest(unittest.TestCase):
    def test_each_rule_names_a_scenario_or_is_left_to_each_client(self) -> None:
        headings = (
            "### Lookup result",
            "### Reverse result",
            "### Autocomplete result",
            "## Requests",
            "## Errors",
            "## Retries",
            "## Sharing, queue and cache",
        )
        rules = [
            rule
            for heading in headings
            for rule in re.split(r"\n(?=- )", section(CLIENT, heading))
            if rule.startswith("- ")
        ]
        unnamed = [rule[2:40] for rule in rules if not contract_files.SCENARIO_NAME.search(rule)]
        self.assertEqual(
            unnamed,
            [
                "A cancelled call ends with the platfor",
                "No error message holds the API key (ER",
                "A shared request stops only when every",
            ],
        )
        untested = section(CLIENT, "## Rules that no scenario tests")
        for text in ("Cancellation (API-11)", "no error message holds", "a shared request stops"):
            self.assertIn(text, untested)
