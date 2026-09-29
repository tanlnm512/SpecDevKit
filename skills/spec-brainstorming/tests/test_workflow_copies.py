"""Structural parity between the spec-brainstorming workflow dialects.

Two masters automate one panel wave on two runtimes — the zcode
facade (workflows/spec-brainstorming.dwf.ts) and the Claude Code
workflow runtime (workflows/spec-brainstorming.js). The runtimes
impose different primitives (persistent typed agents + world.run
vs one-shot agents + probe seams), so byte equality is impossible;
what MUST stay identical is the protocol: the phases, the payload
sentences, the lens missions, the digest grammar, and the
degrade/notCovered honesty. These tests are the drift guard for
that layout — a protocol edit to one master that misses the other
fails here.

The briefs themselves are NOT embedded in either master (they are
read from the skill dir at run time, D-004): these tests pin that
too — a rubric sentence pasted into a workflow is a forked lens.

Runtime-specific invariants are pinned as well (no import/export/
declare tokens in the zcode master; meta-first, no module loading,
no nondeterministic primitives, shell only through the probe agent
in the claude script), mirroring the sibling skills' dialect tests.
"""
import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
DWF_TS = SKILL / "workflows" / "spec-brainstorming.dwf.ts"
WF_JS = SKILL / "workflows" / "spec-brainstorming.js"

# The protocol spine both dialects must carry, phase for phase.
PHASES = [
    "Load the lens briefs and the shared panel protocol",
    "Argue the idea from three independent lenses",
    "Assemble the labeled angles for the session",
]

# Load-bearing sentences of the shared payload ask (contracts/run.md's
# stage-2 payload) — anchors that drift the moment someone rewords one
# master's ask without the other.
PAYLOAD_ANCHORS = [
    "Argue this idea from your lens only.",
    "The idea, in the idea-owner's words:",
    "not established — name the gap as an assumption, never a fact",
    "Ground every point in what is stated here; name assumptions as assumptions, never invent facts.",
    "Return only your digest: angle, pitch, points (2-3 lines), watch — one line per field. ",
    "If you cannot satisfy your brief, say so in watch rather than working around it.",
]

# One anchor per lens seat — the degrade floor each master carries.
MISSION_ANCHORS = [
    "You are the Visionary lens of a brainstorming panel",
    "You are the Cynic lens of a brainstorming panel",
    "You are the Minimalist lens of a brainstorming panel",
]

# The honesty contract of the wave: fresh parallel spawns, runtime
# brief loading, degrade behavior, and the session/workflow boundary.
REPORT_ANCHORS = [
    "three lens seats spawned fresh and in parallel from one payload — none saw another's output",
    "loaded from the skill dir at run time",
    "inline mission line",
    "the session must re-ask this lens",
    "stage 1 (context discovery), stage 3 (trade-off matrix), stage 4 (refinement) and stage 5 (handoff) are the session's, always",
    "no user-turn primitive",
]

BRIEF_FILES = [
    "brainstorm-visionary.md",
    "brainstorm-cynic.md",
    "brainstorm-minimalist.md",
    "_panel-protocol.md",
]

# Distinctive sentences that live ONLY in the briefs/protocol — if one
# shows up in a workflow master, the lens rubric has been forked into
# it instead of read at run time.
BRIEF_ONLY_SENTENCES = [
    "Argue your lens, not the balance",
    "A lens that hedges toward the middle",
    "Rubric — argue every side",
    "what survives if 90% is cut",
]


class ParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ts = DWF_TS.read_text()
        cls.js = WF_JS.read_text()

    def test_both_dialects_exist_and_are_bakeable(self):
        for path, text in ((DWF_TS, self.ts), (WF_JS, self.js)):
            self.assertTrue(path.is_file(), f"missing dialect: {path}")
            self.assertIn('"__SKILL_DIR__"', text, f"{path.name}: no bake placeholder")

    def test_phases_are_identical_and_literal(self):
        for phase in PHASES:
            for name, text in (("dwf.ts", self.ts), ("js", self.js)):
                self.assertIn(f'phase("{phase}")', text,
                              f"{name}: phase literal missing or reworded: {phase!r}")

    def test_payload_anchors_are_shared(self):
        for anchor in PAYLOAD_ANCHORS:
            for name, text in (("dwf.ts", self.ts), ("js", self.js)):
                self.assertIn(anchor, text, f"{name}: payload anchor missing: {anchor!r}")

    def test_mission_lines_are_shared(self):
        for anchor in MISSION_ANCHORS:
            for name, text in (("dwf.ts", self.ts), ("js", self.js)):
                self.assertIn(anchor, text, f"{name}: mission anchor missing: {anchor!r}")

    def test_report_honesty_anchors_are_shared(self):
        for anchor in REPORT_ANCHORS:
            for name, text in (("dwf.ts", self.ts), ("js", self.js)):
                self.assertIn(anchor, text, f"{name}: report anchor missing: {anchor!r}")

    def test_digest_grammar_is_pinned_in_both(self):
        # dwf.ts: the typed digest; js: the schema's required fields.
        for field in ("angle: string;", "pitch: string;", "points: string[];", "watch: string;"):
            self.assertIn(field, self.ts, f"dwf.ts: LensDigest lost field {field!r}")
        self.assertIn('required: ["angle", "pitch", "points", "watch"]', self.js)

    def test_briefs_are_injected_at_run_time_not_embedded(self):
        for brief in BRIEF_FILES:
            for name, text in (("dwf.ts", self.ts), ("js", self.js)):
                self.assertIn(f'"{brief}"', text, f"{name}: brief not referenced for runtime load: {brief}")
        for sentence in BRIEF_ONLY_SENTENCES:
            for name, text in (("dwf.ts", self.ts), ("js", self.js)):
                self.assertNotIn(sentence, text,
                                  f"{name}: brief rubric embedded — the lens is forked, not loaded (D-004)")


class ZcodeDialectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ts = DWF_TS.read_text()

    def test_no_facade_forbidden_tokens(self):
        for token in ("import", "export", "declare"):
            self.assertIsNone(
                re.search(rf"\b{token}\b", self.ts),
                f"forbidden token {token!r} in spec-brainstorming.dwf.ts")

    def test_brief_reads_go_through_world_run(self):
        self.assertIn('world.run("cat"', self.ts)

    def test_panel_spawns_ask_the_typed_digest(self):
        self.assertIn("agent(l.name, { system: lensSystem(i) }).ask<LensDigest>(payloadAsk())", self.ts)


class ClaudeDialectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = WF_JS.read_text()

    def test_meta_is_the_first_statement(self):
        first = next(l for l in self.js.splitlines() if l.strip())
        self.assertTrue(first.startswith("export const meta"),
                        f"first statement is: {first!r}")
        self.assertIn('name: "spec-brainstorming"', self.js)

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
        self.assertIn("brief-probe", self.js)

    def test_lens_asks_carry_system_at_their_head(self):
        # the one-shot divergence: system (mission + brief + protocol)
        # rides at the head of each ask, then the shared payload
        self.assertIn('"\\n\\n===\\n\\nTask:\\n\\n" + payloadAsk()', self.js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
