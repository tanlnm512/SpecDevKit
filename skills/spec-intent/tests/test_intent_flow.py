"""Tests for the spec-intent flow — the skill's own proof (T012).

The other three suites here (test_graph/test_check/test_specstate) are
the engine suite as landed by the parity closure; this file is
spec-intent's own and pins what the closure cannot — the skill-level
flow through this skill's scripts (FR-001):

- eval case I1's mechanical skeleton: a scratch repo + a spec dir
  whose intent.md starts from templates/intent.md; `graph.py --span
  intent --emit-spawns` emits the scout payload carrying the intent
  lens; a filled intent.md (grounded facts, no open markers, current
  Baseline) gates green through `check.py --intent-only` and the
  intent node reads DONE. The scouting/grilling themselves are
  conversational — only their start and end states are mechanical.
- FR-007's derived telemetry name: a `--run --span intent` invocation
  with KIT_TELEMETRY_DIR pointed at a temp store records its events
  in spec-intent.jsonl (SKILL_DIR.name), never spec-to-prod's.
- eval case I2's checker side: an intent.md with an open grilling
  marker fails --intent-only naming the family — the non-answer hard
  stop itself is conversational, so the surviving-marker refusal is
  the part a suite can pin, here through spec-intent's own checker
  copy so the skill stays self-contained (NFR-003).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
GRAPH = SCRIPTS / "graph.py"
CHECK = SCRIPTS / "check.py"
SCAFFOLD = SCRIPTS / "scaffold.sh"
INTENT_TEMPLATE = SKILL / "templates" / "intent.md"

# The sanctioned real-git pattern (test_specstate's): identity via env
# so a scratch repo commits without touching the machine's git config.
GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="scout",
               GIT_AUTHOR_EMAIL="scout@example.com",
               GIT_COMMITTER_NAME="scout",
               GIT_COMMITTER_EMAIL="scout@example.com")

FILLED_SPEC = """# Spec: demo

**Status**: draft
**Effort**: standard

## What
Grow the calculator: multiplication beside add.

## Why
Callers chain `add` calls to fake multiplication and get silent wrong
answers; one real operation removes the trap.

## FR/NFR list
- **FR-001**: The system shall multiply two integers.
"""

# The validated end state of I1: every section grounded in the seeded
# repo, the question frontier closed (each question answered or a
# named assumption — no marker survives), and the Baseline at the
# scouted HEAD. Angle-bracket placeholder shapes are absent by
# construction; the template's HTML comments ride along stripped of
# meaning, so they are simply not carried over.
FILLED_INTENT = """# Intent: demo

**Status**: validated
**Tier**: standard
**Created**: 2026-10-10
**Baseline**: v1 @ {sha}

The intake artifact for the calculator growth, scouted against the
seeded repo (one commit: `src/calc.py` ships `add` and nothing else).

## Problem
The user asked: "grow the calculator — I need multiply, not just
add." Add is the only operation today, so every product is a chain of
sums computed by hand and checked by eye.

## Audience
- A caller composing arithmetic at the REPL — chaining `add` to fake
  multiplication gives silently wrong answers today.

## Constraints
- Python stdlib only — the repo is one module with no dependencies.
- `src/calc.py` stays a single module; the repo has no package
  structure to grow into.

## Questions
- Q1 integers only, or floats too? — answered: `add` already takes
  ints and every caller passes ints.
- Q2 what on overflow? — assumed: Python ints are unbounded, so no
  clamp is specified.

## FR seeds
- **FR-001**: The system shall multiply two integers.
- **FR-002**: WHEN either operand is not an integer, the system shall
  raise TypeError.

## Handoff
Next: `/spec-shape demo` — the docset (spec.md onward) is authored
there, never here. The Baseline above is what shape's survey
re-baselines against.
"""

# I2's surviving-frontier artifact: one live grilling marker is the
# whole point, so everything else is filled (the Baseline hex keeps
# the staleness family quiet — the probe reads a markerless non-git
# temp root and skips).
OPEN_MARKER_INTENT = """# Intent: demo

**Status**: draft
**Tier**: standard
**Created**: 2026-10-10
**Baseline**: v1 @ 012345abcdef

## Problem
The user asked to grow the calculator with multiplication; add is the
only operation today.

## Audience
- Callers composing arithmetic at the REPL.

## Constraints
- Python stdlib only.

## Questions
- [NEEDS CLARIFICATION: integers only, or floats too?]

## FR seeds
- **FR-001**: The system shall multiply two integers.

## Handoff
Next: `/spec-shape demo` once the frontier is empty.
"""


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def seed_repo(root: Path) -> str:
    """A one-commit git repo with a tiny src tree — I1's scratch repo;
    returns the short HEAD sha the scout records as the Baseline."""
    src = root / "src"
    src.mkdir(parents=True)
    write(src / "calc.py", "def add(a, b):\n    return a + b\n")

    def g(*args):
        return subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True,
                              env=GIT_ENV, check=True)

    root.mkdir(parents=True, exist_ok=True)
    g("init", "-q")
    g("add", "-A")
    g("commit", "-qm", "seed the calculator")
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--short",
                        "HEAD"], capture_output=True, text=True,
                       env=GIT_ENV, check=True)
    return r.stdout.strip()


def scaffold_intent_dir(tmp: Path) -> tuple[Path, str]:
    """The I1 skeleton: specs/demo scaffolded beside the seeded repo
    (the layout the baseline probe's candidate scan is built for),
    with spec.md crafted filled — the docset state the intent span
    needs — and intent.md as the skill's own template, unfilled."""
    sha = seed_repo(tmp / "repo")
    r = subprocess.run(["bash", str(SCAFFOLD), "--tier", "tiny", "demo",
                        str(tmp)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = tmp / "specs" / "demo"
    write(d / "spec.md", FILLED_SPEC)
    shutil.copyfile(INTENT_TEMPLATE, d / "intent.md")
    return d, sha


def run_cli(script: Path, *args: str, env: dict | None = None):
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True, timeout=300,
                          env=env)


class IntentFlowTests(unittest.TestCase):
    """Eval case I1's mechanical skeleton, start to handoff gate."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="intent-flow-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.spec_dir, self.sha = scaffold_intent_dir(self._tmp)

    def state(self) -> dict:
        r = run_cli(GRAPH, str(self.spec_dir), "--state-json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_template_intent_holds_the_node_ready_behind_a_done_spec(self):
        st = self.state()
        self.assertEqual(st["nodes"]["spec"]["state"], "done")
        intent = st["nodes"]["intent"]
        self.assertEqual(intent["state"], "READY")
        self.assertIn("unfilled template", intent["reason"])
        self.assertIn("intent", st["frontier"])

    def test_span_intent_emits_the_scout_payload_with_the_intent_lens(self):
        r = run_cli(GRAPH, str(self.spec_dir), "--span", "intent",
                    "--emit-spawns")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("role: surveyor, node: intent", r.stdout)
        self.assertIn("emitted 1 payload(s)", r.stdout)
        payloads = sorted((self.spec_dir / "spawns").glob("*/surveyor.md"))
        self.assertEqual(len(payloads), 1)
        text = payloads[0].read_text(encoding="utf-8")
        # the lens section rides the payload verbatim (T011's carrier)
        self.assertIn("## Carried lens — intent ", text)
        # EXEC-001's shape holds here too: the requirement list embeds
        self.assertIn("**FR-001**", text)

    def test_filled_intent_gates_green_and_reads_done(self):
        write(self.spec_dir / "intent.md",
              FILLED_INTENT.format(sha=self.sha))
        r = run_cli(CHECK, str(self.spec_dir), "--intent-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS (0 fail)", r.stdout)
        st = self.state()
        intent = st["nodes"]["intent"]
        self.assertEqual(intent["state"], "done")
        self.assertIn("--intent-only", intent["reason"])
        # the span drained: no intent-span node is runnable anymore
        r = run_cli(GRAPH, str(self.spec_dir), "--span", "intent",
                    "--emit-spawns")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no intent-span agent payloads to emit", r.stdout)


class IntentTelemetryTests(unittest.TestCase):
    """FR-007: the engine reports under its own resolved skill root —
    events from this skill's graph.py land in spec-intent.jsonl, the
    derived SKILL_DIR.name, never the pre-split spec-to-prod store."""

    def test_run_records_events_under_the_derived_skill_name(self):
        with tempfile.TemporaryDirectory(prefix="intent-tel-") as td:
            tmp = Path(td)
            spec_dir, _sha = scaffold_intent_dir(tmp)
            tel = tmp / "telemetry"
            env = dict(os.environ, KIT_TELEMETRY_DIR=str(tel),
                       KIT_TELEMETRY="on")
            r = run_cli(GRAPH, str(spec_dir), "--run", "--span", "intent",
                        env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            store = tel / "spec-intent.jsonl"
            self.assertTrue(store.exists(),
                            "the derived name must be spec-intent's own")
            self.assertFalse((tel / "spec-to-prod.jsonl").exists())
            rows = [json.loads(ln) for ln
                    in store.read_text(encoding="utf-8").splitlines()
                    if ln.strip()]
            self.assertTrue(rows)
            for row in rows:
                self.assertEqual(row["skill"], "spec-intent")
            waves = [row for row in rows if row["event"] == "wave"]
            self.assertEqual(len(waves), 1)
            self.assertEqual(waves[0]["payload"]["roles"], ["intent"])
            self.assertEqual(waves[0]["payload"]["payloads"], 1)


class IntentHardStopTests(unittest.TestCase):
    """Eval case I2's checker side: a non-answered round leaves its
    marker open, and the skill's own checker copy refuses the artifact
    naming the family — the pin that keeps the refusal self-contained
    (the conversational reprint-and-stop itself is judged in I2's
    session eval, not here)."""

    def test_open_marker_fails_intent_only_naming_the_family(self):
        with tempfile.TemporaryDirectory(prefix="intent-stop-") as td:
            d = Path(td) / "specs" / "demo"
            d.mkdir(parents=True)
            write(d / "intent.md", OPEN_MARKER_INTENT)
            r = run_cli(CHECK, str(d), "--intent-only")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("NEEDS CLARIFICATION marker(s) still open",
                          r.stdout)
            self.assertIn("(1 fail)", r.stdout)
            self.assertNotIn("PASS (0 fail)", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
