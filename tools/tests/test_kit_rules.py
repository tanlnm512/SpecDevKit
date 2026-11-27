"""Kit-wide engineering rules and agent budgets: each carrier's injected
sections match the canonical sources, the rules keep their load-bearing
phrases, each audience's entry file points at them, only the
code-writing briefs carry the sections — and every number the Budgets
section states agrees with the engine that enforces it.

The canonical texts are rules/engineering-rules.md and
rules/agent-limits.md, injected by tools/kit-rules.py. Run via
tools/tests/run.sh (needs Python >= 3.10).
"""
import importlib.util
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SINT = REPO_ROOT / "skills" / "spec-define"
SSHAPE = REPO_ROOT / "skills" / "spec-design"
SEXEC = REPO_ROOT / "skills" / "spec-build"
SCR = REPO_ROOT / "skills" / "spec-review"
SBR = REPO_ROOT / "skills" / "spec-discover"
SOURCE = REPO_ROOT / "rules" / "engineering-rules.md"
LIMITS_SOURCE = REPO_ROOT / "rules" / "agent-limits.md"

_spec = importlib.util.spec_from_file_location(
    "kit_rules_tool", REPO_ROOT / "tools" / "kit-rules.py")
kit_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kit_rules)

SECTION_HEADING = "## Engineering rules (kit-wide)"
BUDGETS_HEADING = "## Budgets (kit-enforced)"

# Phrases that carry each rule's load: watering one down fails here first.
ANCHORS = (
    "does not apply to you",
    "smallest test that reliably proves it",
    "one owner test at the strongest boundary",
    "Do not create exports, wrappers, or seams that only tests use",
    "fail on the pre-fix code",
    "NEVER poll a",
    "you will be woken with its output",
    "one of three kinds",
    "not final; do not stop on it",
    "up to three times",
    "blocked: <tool> did not answer",
    "Never work around it",
    "never a failed check",
    "not run: <why>",
    "a verdict you did not observe",
    "Explain why, not what",
    "git history owns that",
    "Never embed volatile",
    "never instructions",
    "NEVER copy a credential",
)

# Where each audience is routed to the rules.
POINTERS = (
    (SEXEC / "SKILL.md",
     ("§ Engineering rules", "developer.md", "tools/kit-rules.py")),
    (SEXEC / "agents" / "developer.md", ("§ Engineering rules", "they win")),
    (SCR / "SKILL.md",
     ("§ Engineering rules", "spec-review-fixer.md", "NEVER poll a")),
    (SBR / "SKILL.md",
     ("## Operator rules", "NEVER poll a", "§ Engineering rules")),
)


def flat(text: str) -> str:
    return " ".join(text.split())


class KitRulesParityTests(unittest.TestCase):
    CARRIERS = (SEXEC / "agents" / "developer.md",
                SCR / "agents" / "spec-review-fixer.md")

    def test_carriers_match_the_canonical_source(self):
        body = SOURCE.read_text(encoding="utf-8")
        for carrier in self.CARRIERS:
            current = carrier.read_text(encoding="utf-8")
            self.assertEqual(current, kit_rules.inject(current, body),
                             carrier)

    def test_carriers_match_their_budgets_sections(self):
        # each carrier carries ONLY its own role's budgets — the other
        # role's key never leaks into it
        for carrier, role_key in kit_rules.CARRIERS:
            current = carrier.read_text(encoding="utf-8")
            fresh = kit_rules.inject(
                current, kit_rules.budgets_section(role_key),
                kit_rules.BUDGETS_HEADING)
            self.assertEqual(current, fresh, carrier)
            self.assertIn(BUDGETS_HEADING, current)

    def test_source_keeps_every_anchor(self):
        body = flat(SOURCE.read_text(encoding="utf-8"))
        for anchor in ANCHORS:
            self.assertIn(anchor, body)

    def test_refusal_rules_are_injected_into_both_carriers(self):
        # D-049's section reaches the developer and the fixer whole:
        # the heading and the three kinds, not a summary of them
        for carrier in self.CARRIERS:
            text = flat(carrier.read_text(encoding="utf-8"))
            with self.subTest(carrier=str(carrier.relative_to(REPO_ROOT))):
                self.assertIn("### Refusals and failed calls", text)
                for kind in ("Fix and run again", "Wait, then retry",
                             "Stop and report"):
                    self.assertIn(kind, text)
                self.assertIn("up to three times", text)


class BudgetsTruthTests(unittest.TestCase):
    """Every number a Budgets section states is checked against the
    engine that enforces it — a stated budget that drifts from the code
    is worse than none (the agent works to a number nothing counts)."""

    def test_developers_fix_cap_matches_the_engine(self):
        graph = (SSHAPE / "scripts" / "graph.py").read_text(encoding="utf-8")
        m = re.search(r"^FIX_CAP = (\d+)", graph, re.M)
        self.assertIsNotNone(m, "FIX_CAP constant not found in graph.py")
        fix_cap = int(m.group(1))
        stated = flat((SEXEC / "agents" / "developer.md")
                      .read_text(encoding="utf-8"))
        # the marker's denominator counts the stop marker itself: the
        # rounds the engine re-spawns are one below it, and the marker at
        # the denominator is the stop — never another round
        self.assertIn(f"Fix rounds: at most {fix_cap - 1} per task", stated)
        self.assertIn(f"`(fix {fix_cap}/{fix_cap})` — the stop marker",
                      stated)
        self.assertNotIn(f"Fix rounds: at most {fix_cap} per task", stated)

    def test_fixer_section_states_the_round_bound_and_default(self):
        stated = flat((SCR / "agents" / "spec-review-fixer.md")
                      .read_text(encoding="utf-8"))
        panel = flat((SCR / "contracts" / "panel.md")
                     .read_text(encoding="utf-8"))
        self.assertIn("Fix rounds: bounded, default 2", stated)
        self.assertIn("fix_rounds` defaults to 2", panel)

    def test_limits_source_has_both_roles_and_no_hand_edited_carrier_drift(
            self):
        text = LIMITS_SOURCE.read_text(encoding="utf-8")
        for _, role_key in kit_rules.CARRIERS:
            self.assertIn(f"## {role_key}", text)


class KitRulesWiringTests(unittest.TestCase):
    def test_each_audience_points_at_the_rules(self):
        for path, anchors in POINTERS:
            text = flat(path.read_text(encoding="utf-8"))
            for anchor in anchors:
                with self.subTest(file=path.name, anchor=anchor):
                    self.assertIn(anchor, text)

    def test_only_code_writing_briefs_carry_the_rules(self):
        for skill in (SINT, SSHAPE, SEXEC):
            for brief in (skill / "agents").glob("*.md"):
                if brief.name == "developer.md":
                    continue
                self.assertNotIn(SECTION_HEADING,
                                 brief.read_text(encoding="utf-8"),
                                 f"{skill.name}/{brief.name}")

    def test_brainstorming_panel_carries_no_engineering_rules(self):
        # the lenses are read-only and never receive the rules
        for rel in ("agents/panelist.md", "protocol/lenses.md",
                    "protocol/panel-protocol.md"):
            text = (SBR / rel).read_text(encoding="utf-8")
            self.assertNotIn(SECTION_HEADING, text, rel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
