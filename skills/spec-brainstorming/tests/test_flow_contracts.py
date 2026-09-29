"""The rigid flow contract, pinned.

This skill's product is its structure: five stages in a fixed
order, a panel of three briefed lenses, a pinned digest grammar,
a pinned artifact shape, and a handoff gate. The docs ARE the
deliverable, so their load-bearing shapes get the same protection
code gets elsewhere in this repo — these tests fail the moment a
stage is reordered, a lens loses its digest contract, the template
sheds a pinned section, or the green example stops satisfying the
handoff gate.

The version triple (VERSION · SKILL.md frontmatter · plugin.json)
is owned by tools/tests/test_manifests.py; the workflow dialect
parity is owned by tests/test_workflow_copies.py.
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]

STAGES = [
    "### Stage 1 — context discovery",
    "### Stage 2 — the perspective panel",
    "### Stage 3 — the trade-off matrix",
    "### Stage 4 — socratic refinement",
    "### Stage 5 — handoff",
]

TEMPLATE_SECTIONS = [
    "## Direction",
    "## Problem Statement",
    "## User Personas",
    "## Core MVP Features",
    "## Potential Risk Mitigations",
]

LENSES = [
    ("brainstorm-visionary.md", "The Visionary"),
    ("brainstorm-cynic.md", "The Cynic"),
    ("brainstorm-minimalist.md", "The Minimalist"),
]

# Template placeholders that must never survive into a filled artifact
# (legitimate angle brackets like a CLI's <term> argument are fine).
PLACEHOLDER_STEMS = (
    "<Name>", "<date>", "<persona>", "<angle", "<feature", "<the ",
    "<risk", "<why", "<mitigation", "<the one",
)


def read(rel: str) -> str:
    return (SKILL / rel).read_text()


class StageContractTests(unittest.TestCase):
    def test_five_stages_present_in_order(self):
        text = read("SKILL.md")
        positions = [text.find(s) for s in STAGES]
        self.assertTrue(all(p >= 0 for p in positions),
                        f"missing stage heading(s): {[STAGES[i] for i, p in enumerate(positions) if p < 0]}")
        self.assertEqual(positions, sorted(positions),
                          "the five stages are rigid — SKILL.md lists them out of order")

    def test_rigidity_is_stated(self):
        text = read("SKILL.md")
        self.assertIn("always run in order, none is\nskippable", text)
        for sentence in ("**One question at a time.**",
                         "**The user selects or blends.**",
                         "**Nothing is written under `specs/`.**"):
            self.assertIn(sentence, text, f"principle lost: {sentence}")

    def test_artifact_location_is_pinned(self):
        self.assertIn("brainstorms/<name>.md", read("SKILL.md"))
        self.assertIn("brainstorms/<name>.md", read("contracts/run.md"))


class PanelContractTests(unittest.TestCase):
    def test_every_lens_brief_carries_the_digest_contract(self):
        for file, name in LENSES:
            with self.subTest(lens=name):
                body = read(f"agents/{file}")
                for field in ("`angle:", "`pitch:`", "`points:`", "`watch:`"):
                    self.assertIn(field, body, f"{file}: digest field {field} not pinned")

    def test_lens_briefs_are_def_generator_compatible(self):
        for file, name in LENSES:
            with self.subTest(lens=name):
                body = read(f"agents/{file}")
                self.assertTrue(body.startswith("---\n"), f"{file}: no frontmatter")
                fm = body.split("---", 2)[1]
                self.assertIn(f"name: brainstorm-", fm, f"{file}: role prefix")
                self.assertIn("model: inherit", fm, f"{file}: model")
                self.assertIn("tools: Read, Grep, Glob", fm, f"{file}: tools")
                for banned in ("  - Write\n", "  - Edit\n", "  - Agent\n"):
                    self.assertIn(banned, fm, f"{file}: lenses never edit or spawn")

    def test_shared_protocol_carries_lens_rules(self):
        body = read("agents/_panel-protocol.md")
        self.assertIn("Argue your lens, not the balance", body)
        self.assertIn("Digest only, never edit", body)
        for field in ("`angle:", "`pitch:`", "`points:`", "`watch:`"):
            self.assertIn(field, body)


class ArtifactContractTests(unittest.TestCase):
    def test_template_pins_the_five_sections_in_order(self):
        text = read("templates/design-spec.md")
        positions = [text.find(s) for s in TEMPLATE_SECTIONS]
        self.assertTrue(all(p >= 0 for p in positions),
                        f"template lost section(s): {[TEMPLATE_SECTIONS[i] for i, p in enumerate(positions) if p < 0]}")
        self.assertEqual(positions, sorted(positions))
        self.assertIn("/spec <name>", text, "the template names the next step")

    def test_run_contract_arbitrates_digest_grammar_and_payload(self):
        body = read("contracts/run.md")
        self.assertIn("SKILL.md summarizes; this file arbitrates", body)
        self.assertIn("angle:  The Visionary | The Cynic | The Minimalist", body)
        self.assertIn("scripts/skill-dir.sh", body)

    def test_handoff_gate_is_observer_checkable(self):
        body = read("gates/handoff.md")
        self.assertIn("ALL must hold before `/spec` is named", body)
        self.assertIn("never a silent clobber", body)
        self.assertIn("Kill criteria are observable", body)


class GreenFixtureTests(unittest.TestCase):
    """examples/decision-tracker is the green artifact: it must
    satisfy the same pinned shape — and the handoff gate's honesty
    criteria — that a real run's output must."""

    FIXTURE = "examples/decision-tracker/decision-tracker.md"

    def test_fixture_carries_every_pinned_section(self):
        text = read(self.FIXTURE)
        positions = [text.find(s) for s in TEMPLATE_SECTIONS]
        self.assertTrue(all(p >= 0 for p in positions),
                        f"fixture lost section(s): {[TEMPLATE_SECTIONS[i] for i, p in enumerate(positions) if p < 0]}")
        self.assertEqual(positions, sorted(positions))

    def test_fixture_records_selection_and_rejection(self):
        text = read(self.FIXTURE)
        self.assertRegex(text, r"- Selected: .+")
        self.assertRegex(text, r"- Rationale: .+")
        self.assertRegex(text, r"- Rejected: .+ — .+")

    def test_fixture_risks_carry_early_warnings(self):
        text = read(self.FIXTURE)
        self.assertIn("| Risk (from the panel) | Early warning | Mitigation or acceptance |", text)
        self.assertIn("**Kill criteria**", text)

    def test_fixture_has_no_leftover_placeholders(self):
        text = read(self.FIXTURE)
        for stem in PLACEHOLDER_STEMS:
            self.assertNotIn(stem, text, f"template placeholder survived: {stem}")

    def test_fixture_names_the_next_step(self):
        self.assertIn("/spec decision-tracker", read(self.FIXTURE))


class SkillDirScriptTests(unittest.TestCase):
    def test_resolves_the_first_installed_root(self):
        with tempfile.TemporaryDirectory() as home:
            root = Path(home) / ".agents" / "skills" / "spec-brainstorming"
            root.mkdir(parents=True)
            (root / "SKILL.md").write_text("x")
            r = subprocess.run(
                ["bash", str(SKILL / "scripts" / "skill-dir.sh")],
                capture_output=True, text=True,
                env={**os.environ, "HOME": home}, cwd=SKILL,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), str(root))

    def test_fails_loudly_when_not_installed(self):
        with tempfile.TemporaryDirectory() as home:
            r = subprocess.run(
                ["bash", str(SKILL / "scripts" / "skill-dir.sh")],
                capture_output=True, text=True,
                env={**os.environ, "HOME": home}, cwd=SKILL,
            )
            self.assertEqual(r.returncode, 1)
            self.assertIn("ERROR", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
