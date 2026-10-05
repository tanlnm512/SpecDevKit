"""CLI-bound owner suite for the handoff checker.

The checker's command line is its only interface: behavioral
assertions run it as a subprocess, and the placeholder stems stay
pinned to the flow-contract module so the two cannot drift apart.
"""
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_flow_contracts as flow

SKILL = Path(__file__).resolve().parents[1]
CHECKER = SKILL / "scripts" / "check.py"
FIXTURE = SKILL / "examples" / "decision-tracker" / "decision-tracker.md"

PROBLEM_STATEMENT_BLOCK = (
    "## Problem Statement\n"
    "\n"
    "Teams lose decisions made in conversation and re-litigate them later.\n"
    "\n"
)

DIRECTION_BLOCK = (
    "## Direction\n"
    "\n"
    "- Selected: Minimalist core\n"
    "- Rationale: fastest path to observable value\n"
    "- Rejected: Visionary platform — displaces tools the team already trusts\n"
    "\n"
)

RISK_ROW = (
    "| Stale data | usage drops below five reads a week | "
    "refresh prompt on open |\n"
)

BASE_ARTIFACT = (
    "# Demo — design specification\n"
    "\n"
    + DIRECTION_BLOCK
    + PROBLEM_STATEMENT_BLOCK
    + "## User Personas\n"
    "\n"
    "### Persona 1 — the on-call triager\n"
    "\n"
    "- Who: engineer mid-incident.\n"
    "- Needs: one-glance status.\n"
    "- Failed by: scattered dashboards.\n"
    "\n"
    "## Core MVP Features\n"
    "\n"
    "1. Status snapshot — serves the on-call triager. One command prints current state.\n"
    "\n"
    "**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.\n"
    "\n"
    "## Potential Risk Mitigations\n"
    "\n"
    "| Risk (from the panel) | Early warning | Mitigation or acceptance |\n"
    "|---|---|---|\n"
    + RISK_ROW
    + "\n"
    "**Kill criteria**: fewer than five uses per week after week three.\n"
)


def run_checker(path):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(path)],
        capture_output=True, text=True, encoding="utf-8",
    )


def run_text(text, name="artifact.md"):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_text(text, encoding="utf-8")
        return run_checker(path), path


class HandoffCheckTests(unittest.TestCase):
    def test_green_fixture_passes_and_discloses_judgment(self):
        result = run_checker(FIXTURE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertTrue(lines, result.stdout)
        self.assertTrue(lines[-1].startswith("JUDGMENT:"), lines[-1:])

    def test_missing_section_fails_located_with_exit_one(self):
        result, _ = run_text(BASE_ARTIFACT.replace(PROBLEM_STATEMENT_BLOCK, ""))
        self.assertEqual(result.returncode, 1, result.stdout)
        failures = [line for line in result.stdout.splitlines()
                    if line.startswith("FAIL") and "Problem Statement" in line]
        self.assertTrue(failures, result.stdout)
        self.assertTrue(result.stdout.splitlines()[-1].startswith("JUDGMENT:"))

    def test_placeholder_failure_names_stem_and_line(self):
        selected = "- Selected: <angle or blend>"
        text = BASE_ARTIFACT.replace("- Selected: Minimalist core", selected)
        line_number = text.splitlines().index(selected) + 1
        result, _ = run_text(text)
        self.assertEqual(result.returncode, 1, result.stdout)
        hits = [line for line in result.stdout.splitlines() if "<angle" in line]
        self.assertTrue(hits, result.stdout)
        self.assertTrue(any(str(line_number) in line for line in hits), hits)

    def test_criterion_failures_are_named_on_failing_artifacts(self):
        cases = (
            ("incomplete Selected", "- Selected: Minimalist core",
             "- Selected:", "Selected"),
            ("missing Rationale", "- Rationale: fastest path to observable value\n",
             "", "Rationale"),
            ("Rejected without a reason",
             "- Rejected: Visionary platform — displaces tools the team already trusts",
             "- Rejected: Visionary platform", "Rejected"),
            ("no numbered feature item",
             "1. Status snapshot — serves the on-call triager. "
             "One command prints current state.",
             "- Status snapshot — serves the on-call triager.", "feature"),
            ("empty out-of-scope cut list",
             "**Out of scope (day-one cut list)**: web dashboards, "
             "refused to keep day one shippable.",
             "**Out of scope (day-one cut list)**:", "scope"),
            ("missing kill criteria",
             "**Kill criteria**: fewer than five uses per week after week three.\n",
             "", "kill"),
        )
        for name, old, new, criterion in cases:
            with self.subTest(name):
                result, _ = run_text(BASE_ARTIFACT.replace(old, new))
                self.assertEqual(result.returncode, 1, result.stdout)
                hits = [line for line in result.stdout.splitlines()
                        if line.startswith("FAIL")
                        and criterion.lower() in line.lower()]
                self.assertTrue(hits, result.stdout)

    def test_incomplete_risk_rows_fail_in_the_located_line_format(self):
        replacement = (
            "| Stale data |  | refresh prompt on open |\n"
            "| Adoption stalls | no team sign-up in week one |  |\n"
        )
        text = BASE_ARTIFACT.replace(RISK_ROW, replacement)
        result, path = run_text(text)
        self.assertEqual(result.returncode, 1, result.stdout)
        for risk in ("Stale data", "Adoption stalls"):
            line_number = next(number for number, line in enumerate(
                text.splitlines(), 1) if risk in line)
            pattern = rf"^FAIL {re.escape(str(path))}:{line_number} [^:]+: .+$"
            self.assertTrue(
                any(re.match(pattern, line)
                    for line in result.stdout.splitlines()),
                f"{risk}: {result.stdout}",
            )

    def test_operator_named_path_outside_brainstorms_is_used_as_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "operator-picked-handoff.md"
            path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            result = run_checker(path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unreadable_path_fails_naming_the_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist.md"
            result = run_checker(missing)
            self.assertEqual(result.returncode, 1)
            self.assertIn("does-not-exist.md", result.stdout + result.stderr)

    def test_duplicate_required_section_heading_fails(self):
        text = BASE_ARTIFACT.replace(
            PROBLEM_STATEMENT_BLOCK, DIRECTION_BLOCK + PROBLEM_STATEMENT_BLOCK
        )
        result, _ = run_text(text)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(
            any(line.startswith("FAIL") and "Direction" in line
                for line in result.stdout.splitlines()),
            result.stdout,
        )

    def test_risk_table_with_no_data_rows_fails(self):
        result, _ = run_text(BASE_ARTIFACT.replace(RISK_ROW, ""))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(
            any(line.startswith("FAIL") and "risk" in line.lower()
                for line in result.stdout.splitlines()),
            result.stdout,
        )

    def test_placeholder_stems_match_the_flow_contract_pin(self):
        spec = importlib.util.spec_from_file_location("handoff_check", CHECKER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.PLACEHOLDER_STEMS, flow.PLACEHOLDER_STEMS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
