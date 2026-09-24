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

# The fix-loop invariant: a reader verifier is never spawned for a
# gate-lens entry (its `where` is a check name, not a file location) —
# the fresh authoritative gate re-run owns those.
GATE_EXCLUSION = '.finding.lens !== "gate"'


def read(path):
    text = path.read_text(encoding="utf-8")
    # the bake placeholder must sit inside a double-quoted literal on one
    # line, or tools/workflow-defs.py --bake would corrupt the master
    assert 'const SKILL_DIR_BAKED = "__SKILL_DIR__";' in text, path.name
    return text


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
            self.assertIn("SEV_RANK", text, name)

    def test_panel_definition_matches(self):
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            for label in ("correctness", "security", "quality", "general"):
                self.assertIn(f'label: "{label}"', text, f"{label} in {name}")

    def test_ask_anchors_are_shared(self):
        for anchor in ASK_ANCHORS:
            self.assertIn(anchor, self.ts, anchor)
            self.assertIn(anchor, self.js, anchor)

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
        # the gate command reaches the probe shell-quoted, never bare
        self.assertIn('shq(skillDir + "/scripts/gate.sh")', self.js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
