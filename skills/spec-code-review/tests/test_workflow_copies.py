"""Structural parity between the spec-code-review workflow dialects.

Two masters automate one review protocol on two runtimes — the zcode
facade (workflows/spec-code-review.dwf.ts) and the Claude Code workflow
runtime (workflows/spec-code-review.js). The runtimes impose different
primitives (persistent typed agents + world.run vs one-shot agents +
probe seams), so byte equality is impossible; what MUST stay identical
is the protocol: the phases, the panel, the tunables, the ask anchors,
and the report contract. These tests are the drift guard for that
layout — a protocol edit to one master that misses the other fails here.

Runtime-specific invariants are pinned too (no import/export/declare in
the zcode function body; meta-first, no module loading, no
nondeterministic primitives, shell only through probe agents in the
claude script), mirroring tools/tests/test_workflow_defs.py's dialect
tests for spec-run.
"""
import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
DWF_TS = SKILL / "workflows" / "spec-code-review.dwf.ts"
WF_JS = SKILL / "workflows" / "spec-code-review.js"

# The protocol spine both dialects must carry, phase for phase.
PHASES = [
    "Scope the change and run the repo's checks",
    "Review the change through separate lenses and confirm every finding",
    "Fix the confirmed findings and verify every fix",
    "Synthesize the final review report",
]

# Load-bearing sentences of the shared ask texts — anchors that drift
# the moment someone rewords one master's prompts without the other.
ASK_ANCHORS = [
    "never invent one to seem busy",
    "the repo's checks own those",
    "cosmetic proximity is not a fix",
    "An empty findings list is the expected answer for clean fixes",
    "merge | fix-first | human",
    "escalate and say so plainly rather than working around it",
]

# The whole-project mode (target: project) carries its own ask family in
# both masters — anchors that pin the project-side contract.
PROJECT_ASK_ANCHORS = [
    "There is no diff — the target is the file list below",
    "present in the code as it stands",
    "path:line in the current tree",
    "merge means the code is ready as it stands",
]

# The pr and branch targets (0.5.0) resolve to a merge-base diff before
# the panel machinery runs, so the ask family is shared with diff mode.
# These anchors pin the resolution contract in both dialects: the gh pr
# fields, the merge-base/rev-list mechanics, the default-branch
# detection, and the checkout safety rule (never check out over a dirty
# tree; always announce the checkout with the previous HEAD).
PR_TARGET_ANCHORS = [
    "baseRefOid",
    "headRefOid",
    "refs/remotes/origin/HEAD",
    "merge-base",
    "rev-list",
    "needs a pr arg",
    "the working tree is dirty",
    "common ancestor",
    "switch back when done reviewing",
]

# The stated-intent channel and the split recommendation (0.6.0): intent
# (the arg, else the PR description) rides into the reviewer, triage,
# final and fixer asks in both dialects, with the intent-blind
# confirmation rule preserved; oversized changes earn a split line in
# the report. Anchors pin the load-bearing sentences and tunables.
INTENT_SPLIT_ANCHORS = [
    "the author's stated intent",
    "stated intent never waives a demonstrable defect",
    "consider splitting into smaller",
]

# The fix-loop invariant: a reader verifier is never spawned for a
# gate-lens entry (its `where` is a check name, not a file location) —
# the fresh authoritative gate re-run owns those.
GATE_EXCLUSION = '.finding.lens !== "gate"'

# The panel's third representation: each side of the rubric is also an
# installable agent brief (agents/code-review-<lens>.md). The lens focus
# strings below are asserted in BOTH workflow masters AND the matching
# brief, so no representation can drift from the others.
BRIEFS = SKILL / "agents"
LENS_BRIEFS = {
    "correctness": BRIEFS / "code-review-correctness.md",
    "security": BRIEFS / "code-review-security.md",
    "quality": BRIEFS / "code-review-quality.md",
}
FIXER_BRIEF = BRIEFS / "code-review-fixer.md"
PANEL_PROTOCOL = BRIEFS / "_panel-protocol.md"
LENS_FOCUS = {
    "correctness":
        "logic errors, broken edge cases, wrong or missing error handling, "
        "concurrency hazards, broken contracts between caller and callee.",
    "security":
        "untrusted input paths, injection, secrets and token handling, "
        "unsafe deserialization, permission changes, destructive operations.",
    "quality":
        "complexity the next reader pays for, over-engineering, misleading "
        "names, comments and docs that drift from the code, and tests — "
        "behavior this change alters with no test covering it, tests that "
        "cannot fail, and design fit — whether the change follows the "
        "patterns the surrounding code already establishes instead of "
        "inventing a parallel way.",
}


def read(path):
    text = path.read_text(encoding="utf-8")
    # the bake placeholder must sit inside a double-quoted literal on one
    # line, or tools/workflow-defs.py --bake would corrupt the master
    assert 'const SKILL_DIR_BAKED = "__SKILL_DIR__";' in text, path.name
    return text


def flat(text):
    """Collapse all whitespace to single spaces — prose anchors must
    match across each file's own line wrapping."""
    return " ".join(text.split())


class ParityTests(unittest.TestCase):
    def setUp(self):
        self.ts = read(DWF_TS)
        self.js = read(WF_JS)

    def test_both_dialects_exist_and_are_bakeable(self):
        for path in (DWF_TS, WF_JS):
            self.assertTrue(path.is_file(), path)
            self.assertIn("__SKILL_DIR__", path.read_text())
        self.assertIn("scripts/gate.sh", self.js)

    def test_phases_are_identical_and_literal(self):
        ts_phases = re.findall(r'phase\("([^"]+)"\)', self.ts)
        js_phases = re.findall(r'phase\("([^"]+)"\)', self.js)
        self.assertEqual(ts_phases, PHASES)
        self.assertEqual(js_phases, PHASES)

    def test_tunables_match(self):
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn("FAST_MAX_LINES = 400", text, name)
            self.assertIn("FAST_MAX_FILES = 5", text, name)
            self.assertIn("PROJECT_MAX_FILES = 30", text, name)
            self.assertIn("SUGGEST_SPLIT_LINES = 1000", text, name)
            self.assertIn("SUGGEST_SPLIT_FILES = 20", text, name)
            self.assertIn("SEV_RANK", text, name)

    def test_target_mode_branches_are_shared(self):
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn('TARGET === "project"', text, name)
            self.assertIn('"--tree"', text, name)
            # project targeting functions exist under the same names
            self.assertIn("function reviewAskProject", text, name)
            self.assertIn("function triageAskProject", text, name)
            self.assertIn("function confirmAskProject", text, name)
            self.assertIn("function finalAskProject", text, name)

    def test_pr_and_branch_targets_are_shared(self):
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn('TARGET === "branch"', text, name)
            self.assertIn('TARGET === "pr"', text, name)
            self.assertIn("const TARGETS", text, name)
            for anchor in PR_TARGET_ANCHORS:
                self.assertIn(anchor, flat(text), f"{anchor} in {name}")

    def test_panel_definition_matches(self):
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            for label in ("correctness", "security", "quality", "general"):
                self.assertIn(f'label: "{label}"', text, f"{label} in {name}")

    def test_ask_anchors_are_shared(self):
        for anchor in ASK_ANCHORS + PROJECT_ASK_ANCHORS:
            self.assertIn(anchor, flat(self.ts), anchor)
            self.assertIn(anchor, flat(self.js), anchor)

    def test_intent_channel_and_split_advice_are_shared(self):
        # intent rides into reviewer/triage/final/fixer asks in both
        # dialects (4 intentBlock calls each); confirmation stays
        # intent-blind — the confirm asks never see it
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            for anchor in INTENT_SPLIT_ANCHORS:
                self.assertIn(anchor, flat(text), f"{anchor} in {name}")
            # 4 call sites (reviewer, triage, final, fixer) + 1 definition
            self.assertEqual(text.count("intentBlock()"), 5, name)
            self.assertIn("INTENT_ARG", text, name)
            self.assertIn("SUGGEST_SPLIT_LINES", text, name)

    def test_fix_loop_never_verifies_gate_lens_with_a_reader(self):
        self.assertIn(GATE_EXCLUSION, self.ts)
        self.assertIn(GATE_EXCLUSION, self.js)

    def test_report_contract_is_shared(self):
        for token in ("fixStatus", "notCovered", "residualRisks", "testGaps"):
            self.assertIn(token, self.ts, token)
            self.assertIn(token, self.js, token)


class ZcodeDialectTests(unittest.TestCase):
    """The zcode facade compiles a plain function body: no import/export/
    declare token anywhere (comments included), literal phase names, and
    the gate reached through world.run."""

    def setUp(self):
        self.ts = DWF_TS.read_text(encoding="utf-8")

    def test_no_facade_forbidden_tokens(self):
        for token in ("import", "export", "declare"):
            self.assertIsNone(
                re.search(rf"\b{token}\b", self.ts),
                f"forbidden token {token!r} in spec-code-review.dwf.ts")

    def test_gate_runs_through_world_run(self):
        self.assertIn('world.run("bash"', self.ts)
        self.assertIn("scripts/gate.sh", self.ts)

    def test_panel_briefs_are_injected_at_run_time(self):
        # no user-installable agent types on zcode: the briefs are read
        # from the skill dir at run time and appended to the inline
        # personas; a missing brief degrades to the inline rubric
        self.assertIn("world.run(\"cat\"", self.ts)
        for brief in ("_panel-protocol.md",
                      "code-review-correctness.md",
                      "code-review-security.md",
                      "code-review-quality.md",
                      "code-review-fixer.md"):
            self.assertIn(brief, self.ts, brief)


class ClaudeDialectTests(unittest.TestCase):
    """Claude Code dynamic workflows: `export const meta` as the first
    statement, no module loading, no direct fs/shell in the script (the
    probe agents are the seam), deterministic primitives only."""

    def setUp(self):
        self.js = WF_JS.read_text(encoding="utf-8")

    def test_meta_is_the_first_statement(self):
        first = next(l for l in self.js.splitlines() if l.strip())
        self.assertTrue(first.startswith("export const meta"),
                        f"first statement is: {first!r}")
        self.assertIn('name: "spec-code-review"', self.js)

    def test_no_module_loading_and_no_nondeterministic_primitives(self):
        self.assertIsNone(re.search(r"\bimport\b", self.js))
        self.assertIsNone(re.search(r"\brequire\s*\(", self.js))
        self.assertNotIn("Date.now", self.js)
        self.assertNotIn("Math.random", self.js)

    def test_documented_primitives_and_schema_validation(self):
        for token in ("pipeline(", "agent(", "phase(", "log(",
                      "schema:", "additionalProperties: false"):
            self.assertIn(token, self.js)

    def test_shell_needs_route_through_probe_agents(self):
        self.assertNotIn("world.run", self.js)
        self.assertNotIn("subprocess", self.js)
        self.assertIn("gate-probe", self.js)
        self.assertIn("scope-probe", self.js)
        self.assertIn("target-probe", self.js)
        # pr/branch resolution probes (0.5.0): pr metadata, head/dirty
        # state, checkout, merge-base, base-branch detection
        self.assertIn("pr-meta-probe", self.js)
        self.assertIn("pr-head-probe", self.js)
        self.assertIn("pr-checkout-probe", self.js)
        self.assertIn("merge-base-probe", self.js)
        self.assertIn("base-ref-probe", self.js)
        # the gate command reaches the probe shell-quoted, never bare
        self.assertIn('shq(skillDir + "/scripts/gate.sh")', self.js)


class AgentBriefTests(unittest.TestCase):
    """Each side of the rubric is materialized as an agent brief — the
    panel's third representation after the two workflow dialects. The
    briefs must exist, carry def-generator-compatible frontmatter, and
    hold the same lens focus strings the workflows dispatch on."""

    def test_every_rubric_side_has_a_brief(self):
        for label, path in LENS_BRIEFS.items():
            self.assertTrue(path.is_file(), f"{label}: {path}")
        self.assertTrue(FIXER_BRIEF.is_file())
        self.assertTrue(PANEL_PROTOCOL.is_file())
        # shared prose is _-prefixed: never installed as an agent def
        for path in BRIEFS.glob("*.md"):
            if path.stem.startswith("_"):
                continue
            self.assertIn(path, list(LENS_BRIEFS.values()) + [FIXER_BRIEF],
                          f"unpinned brief: {path.name} — add it to the tests")

    def test_brief_frontmatter_is_def_generator_compatible(self):
        # tools/omp/agent-defs parse name, description, tools (comma
        # list), model, effort — the shape every dialect derives from
        for path in list(LENS_BRIEFS.values()) + [FIXER_BRIEF]:
            text = path.read_text(encoding="utf-8")
            m = re.search(r"^name: (\S+)", text, re.M)
            self.assertIsNotNone(m, f"name: in {path.name}")
            self.assertEqual(m.group(1), path.stem)
            self.assertIn("description: ", text)
            self.assertIn("model: inherit", text)
            self.assertIn("tools: ", text)
            self.assertIn("disallowedTools:", text)

    def test_lens_focus_strings_match_every_representation(self):
        ts = DWF_TS.read_text(encoding="utf-8")
        js = WF_JS.read_text(encoding="utf-8")
        for label, focus in LENS_FOCUS.items():
            brief = LENS_BRIEFS[label].read_text(encoding="utf-8")
            for text, name in ((ts, "dwf.ts"), (js, "js"),
                               (brief, f"{label} brief")):
                self.assertIn(flat(focus), flat(text),
                              f"{label} focus in {name}")

    def test_panel_protocol_carries_the_shared_bar(self):
        text = PANEL_PROTOCOL.read_text(encoding="utf-8")
        for anchor in (
            "discrete and actionable",
            "part of the target under review",
            "escalate and say so plainly",
            "Zero findings is the expected answer",
        ):
            self.assertIn(anchor, flat(text))

    def test_fixer_brief_pins_the_hard_rules(self):
        text = FIXER_BRIEF.read_text(encoding="utf-8")
        for anchor in ("Never commit", "pin the corrected behavior in the test"):
            self.assertIn(anchor, flat(text))


if __name__ == "__main__":
    unittest.main(verbosity=2)
