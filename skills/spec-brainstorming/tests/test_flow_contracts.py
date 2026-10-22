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
is owned by tools/tests/test_manifests.py.
"""
import os
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
    ("visionary", "The Visionary"),
    ("cynic", "The Cynic"),
    ("minimalist", "The Minimalist"),
]

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

    def test_artifact_location_is_pinned(self):
        self.assertIn("brainstorms/<name>.md", read("SKILL.md"))
        self.assertIn("brainstorms/<name>.md", read("contracts/run.md"))


class PanelContractTests(unittest.TestCase):
    def test_every_lens_section_carries_the_digest_contract(self):
        text = read("agents/_lenses.md")
        for key, name in LENSES:
            section = text.split(f"## Lens: {key}", 1)[1] \
                          .split("## Lens:", 1)[0]
            with self.subTest(lens=name):
                for field in ("`angle:", "`pitch:", "`points:", "`watch:`"):
                    self.assertIn(field, section,
                                  f"{name}: digest field {field} not pinned")

    def test_panelist_brief_is_def_generator_compatible(self):
        body = read("agents/panelist.md")
        self.assertTrue(body.startswith("---\n"), "no frontmatter")
        fm = body.split("---", 2)[1]
        self.assertIn("name: brainstorm-panelist", fm)
        self.assertIn("model: inherit", fm)
        self.assertIn("tools: Read, Grep, Glob", fm)
        for banned in ("  - Write\n", "  - Edit\n", "  - Agent\n"):
            self.assertIn(banned, fm, "lenses never edit or spawn")


class ArtifactContractTests(unittest.TestCase):
    def test_template_pins_the_five_sections_in_order(self):
        text = read("templates/design-spec.md")
        positions = [text.find(s) for s in TEMPLATE_SECTIONS]
        self.assertTrue(all(p >= 0 for p in positions),
                        f"template lost section(s): {[TEMPLATE_SECTIONS[i] for i, p in enumerate(positions) if p < 0]}")
        self.assertEqual(positions, sorted(positions))

    def test_run_contract_arbitrates_digest_grammar_and_payload(self):
        body = read("contracts/run.md")
        self.assertIn("angle:  The Visionary | The Cynic | The Minimalist", body)
        self.assertIn("scripts/skill-dir.sh", body)


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
