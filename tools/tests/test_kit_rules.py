"""Kit-wide engineering rules: each carrier's injected section matches the
canonical source, and only the code-writing briefs carry the section.

The canonical text is rules/engineering-rules.md, injected by
tools/kit-rules.py. Run via tools/tests/run.sh (needs Python >= 3.10).
"""
import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SINT = REPO_ROOT / "skills" / "spec-intent"
SSHAPE = REPO_ROOT / "skills" / "spec-shape"
SEXEC = REPO_ROOT / "skills" / "spec-execute"
SCR = REPO_ROOT / "skills" / "spec-code-review"
SBR = REPO_ROOT / "skills" / "spec-brainstorming"
SOURCE = REPO_ROOT / "rules" / "engineering-rules.md"

_spec = importlib.util.spec_from_file_location(
    "kit_rules_tool", REPO_ROOT / "tools" / "kit-rules.py")
kit_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kit_rules)

SECTION_HEADING = "## Engineering rules (kit-wide)"


class KitRulesParityTests(unittest.TestCase):
    CARRIERS = (SEXEC / "agents" / "builder.md",
                SCR / "agents" / "code-review-fixer.md")

    def test_carriers_match_the_canonical_source(self):
        body = SOURCE.read_text(encoding="utf-8")
        for carrier in self.CARRIERS:
            current = carrier.read_text(encoding="utf-8")
            self.assertEqual(current, kit_rules.inject(current, body),
                             carrier)


class KitRulesWiringTests(unittest.TestCase):
    def test_only_code_writing_briefs_carry_the_rules(self):
        for skill in (SINT, SSHAPE, SEXEC):
            for brief in (skill / "agents").glob("*.md"):
                if brief.name == "builder.md":
                    continue
                self.assertNotIn(SECTION_HEADING,
                                 brief.read_text(encoding="utf-8"),
                                 f"{skill.name}/{brief.name}")

    def test_brainstorming_panel_carries_no_engineering_rules(self):
        # the lenses are read-only and never receive the rules
        for name in ("panelist.md", "_lenses.md",
                     "_panel-protocol.md"):
            text = (SBR / "agents" / name).read_text(encoding="utf-8")
            self.assertNotIn(SECTION_HEADING, text, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
