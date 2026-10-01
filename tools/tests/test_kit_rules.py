"""Kit-wide engineering rules parity — D-028 (spec-to-prod) / D-012
(spec-code-review) / D-005 (spec-brainstorming).

The three engineering rules (test discipline, backgrounded-job
discipline, strict code commenting) have ONE canonical source,
rules/engineering-rules.md, injected by tools/kit-rules.py into two
carrier views: spec-to-prod's agents/_shared-protocol.md § Engineering
rules (embedded into every spawn payload by graph.py build_payload) and
spec-code-review's agents/code-review-fixer.md § Engineering rules
(runtime-loaded into the fix loop). These tests pin the source→carrier
injection, the load-bearing anchors, the SKILL.md pointers, and the
constitution articles — so the wording cannot fork and the scoping
decisions cannot silently rot. (drift-check.py's kit-rules category
covers the same injection at release time; this suite also pins what
the injector cannot see.)
Run via tools/tests/run.sh (needs Python >= 3.10).
"""
import importlib.util
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
S2P = REPO_ROOT / "skills" / "spec-to-prod"
SCR = REPO_ROOT / "skills" / "spec-code-review"
SBR = REPO_ROOT / "skills" / "spec-brainstorming"
SOURCE = REPO_ROOT / "rules" / "engineering-rules.md"

_spec = importlib.util.spec_from_file_location(
    "kit_rules_tool", REPO_ROOT / "tools" / "kit-rules.py")
kit_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kit_rules)

SECTION_HEADING = "## Engineering rules (kit-wide)"

# Anchors that carry each rule's load: if an edit waters one down, a
# test fails before the rules can silently weaken.
ANCHORS = (
    # scope line
    "does not apply to you",
    # test discipline
    "smallest test that reliably proves it",
    "one owner test at the strongest boundary",
    "Do not create exports, wrappers, or seams that only tests use",
    "fail on the pre-fix code",
    # backgrounded-job discipline
    "NEVER poll a",
    "you will be woken with its output",
    # strict commenting
    "Explain why, not what",
    "git history owns that",
    "Never embed volatile",
)


def section(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"^{re.escape(SECTION_HEADING)}\n.*?(?=^## |\Z)",
        text, re.S | re.M)
    if not match:
        raise AssertionError(f"{SECTION_HEADING!r} not found in {path}")
    return match.group(0).rstrip()


def flat(text: str) -> str:
    """Whitespace-flattened text — anchors survive re-wrapping
    (same convention as the skills' test_workflow_copies.py)."""
    return " ".join(text.split())


class KitRulesParityTests(unittest.TestCase):
    CARRIERS = (S2P / "agents" / "_shared-protocol.md",
                SCR / "agents" / "code-review-fixer.md")

    def test_source_file_exists(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(
            SOURCE.read_text(encoding="utf-8").startswith(SECTION_HEADING))

    def test_carriers_exist(self):
        for carrier in self.CARRIERS:
            self.assertTrue(carrier.is_file(), carrier)

    def test_carriers_match_the_canonical_source(self):
        # the injector's own invariant: each carrier's section equals a
        # fresh injection from rules/engineering-rules.md
        body = SOURCE.read_text(encoding="utf-8")
        for carrier in self.CARRIERS:
            current = carrier.read_text(encoding="utf-8")
            self.assertEqual(current, kit_rules.inject(current, body),
                             carrier)

    def test_kit_rules_check_passes(self):
        self.assertEqual(kit_rules.main(["--check"]), 0)

    def test_sections_are_byte_identical(self):
        a = section(S2P / "agents" / "_shared-protocol.md")
        b = section(SCR / "agents" / "code-review-fixer.md")
        self.assertEqual(a, b)

    def test_section_carries_every_anchor(self):
        body = flat(SOURCE.read_text(encoding="utf-8"))
        for anchor in ANCHORS:
            self.assertIn(anchor, body, anchor)

    def test_subsections_present(self):
        body = section(SCR / "agents" / "code-review-fixer.md")
        for sub in ("### Before adding a test",
                    "### Long foreground tasks",
                    "### Strict code commenting"):
            self.assertIn(sub, body, sub)


class KitRulesWiringTests(unittest.TestCase):
    """The rules must actually reach their audiences: payloads via the
    protocol embed, the fixer via its brief (pinned in the skill's own
    test_workflow_copies.py), and orchestrators via each SKILL.md."""

    def test_s2p_skill_md_points_at_the_canonical_section(self):
        text = flat((S2P / "SKILL.md").read_text(encoding="utf-8"))
        for anchor in ("§ Engineering rules",
                       "NEVER poll a",
                       "ride into every spawn payload"):
            self.assertIn(anchor, text, anchor)

    def test_scr_skill_md_points_at_the_fixer_carrier(self):
        text = flat((SCR / "SKILL.md").read_text(encoding="utf-8"))
        for anchor in ("§ Engineering rules",
                       "code-review-fixer.md",
                       "NEVER poll a"):
            self.assertIn(anchor, text, anchor)

    def test_sbr_skill_md_scopes_the_rules_to_the_orchestrator(self):
        text = flat((SBR / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("## Operator rules", text)
        self.assertIn("NEVER poll a", text)
        self.assertIn("_shared-protocol.md", text)

    def test_implementer_brief_defers_to_the_canonical_section(self):
        text = flat((S2P / "agents" / "spec-implementer.md").read_text(
            encoding="utf-8"))
        self.assertIn("§ Engineering rules", text)
        self.assertIn("they win", text)

    def test_brainstorming_panel_carries_no_engineering_rules(self):
        # D-005: the lenses are read-only — the rules must NOT ride
        # their briefs or the panel protocol
        for name in ("brainstorm-visionary.md", "brainstorm-cynic.md",
                     "brainstorm-minimalist.md", "_panel-protocol.md"):
            text = flat((SBR / "agents" / name).read_text(encoding="utf-8"))
            self.assertNotIn(SECTION_HEADING, text, name)


class KitRulesConstitutionTests(unittest.TestCase):
    """The user chose to bind the repo's own development too: C-07
    (tests), C-08 (comments), C-09 (backgrounded jobs)."""

    def test_constitution_articles_present(self):
        text = flat((REPO_ROOT / "specs" / "CONSTITUTION.md").read_text(
            encoding="utf-8"))
        for anchor in (
            "**C-07**: every added test protects observable behavior",
            "**C-08**: code comments explain why, not what",
            "**C-09**: never poll a backgrounded job",
        ):
            self.assertIn(anchor, text, anchor)

    def test_constitution_rationale_covers_the_new_articles(self):
        text = flat((REPO_ROOT / "specs" / "CONSTITUTION.md").read_text(
            encoding="utf-8"))
        for anchor in ("- C-07: ", "- C-08: ", "- C-09: "):
            self.assertIn(anchor, text, anchor)


if __name__ == "__main__":
    unittest.main(verbosity=2)
