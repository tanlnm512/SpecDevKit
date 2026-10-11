"""Tests for the spec-execute invocation gate — the T018 suite
(FR-004, FR-008, NFR-003).

The execute span's entry gate (D-003) is the skill's whole intake
discipline: `graph.py <dir> --span execute` refuses (exit 4, blocking
gate printed, an intake_refusal telemetry event under the engine's own
derived skill name) unless approve AND verify are DONE — so spec-execute
accepts any directory that satisfies the docset contract, never only the
ones this kit shaped (FR-008). These cases pin:

  GATE-001  a draft docset (Status: draft, check green) refuses naming
            the approve gate, writes zero payloads, records telemetry;
  GATE-002  an approved-but-red docset (check.py fails, e.g. a broken
            task entry) refuses naming verify the same way;
  GATE-003  the approved-and-green fixture executes: --emit-spawns
            writes implementer payload(s) for runnable tasks, --run
            (print runner) drives the wave and stops — at the
            tick-commit gate on the landed shape, on the state's
            tick-commit-blocked-readonly at the runnable shape — and no
            authoring payload (survey/plan/tech/qa/tasks/design) is ever
            emitted under the execute span;
  GATE-004  a hand-authored docset (same contract shapes, different
            prose) hits the identical refusal and gate outcomes — the
            gate reads Status + green check, not kit provenance;
  GATE-005  the five lifecycle commands moved in T016 live here with
            extra.txt claiming their bare names exactly once (the
            install pin itself is T019's).

Fixtures follow the validation contract: mutated copies of
examples/mini-spec (never the original) plus the repo it cites, and a
from-scratch hand-authored docset. Every CLI run gets its own
KIT_TELEMETRY_DIR so telemetry assertions read only this run's events.
"""

import hashlib
import json
import os
import re
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
FIXTURE = SKILL / "examples" / "mini-spec" / "specs" / "mini-spec"
FIXTURE_REPO = SKILL / "examples" / "mini-spec" / "repo"
COMMANDS = SKILL / "commands"

# The moved lifecycle commands (T016) plus the skill's own router verb.
LIFECYCLE_COMMANDS = ("spec-plan.md", "spec-build.md", "spec-test.md",
                      "spec-review.md", "spec-ship.md")
CLAIMED_BARE_NAMES = ["spec-execute", "spec-plan", "spec-build",
                      "spec-test", "spec-review", "spec-ship"]

# Payload vocabulary the execute span may never emit: the authoring
# nodes live in spec-shape's span, so their appearance here would mean
# the span filter (or its gate) leaked authoring into execution.
AUTHORING_NODES = {"intent", "survey", "plan", "tech", "qa", "tasks",
                   "design", "research"}
AUTHORING_FILES = {"surveyor.md", "planner.md", "tech.md", "qa.md",
                   "task-breaker.md", "designer.md", "researcher.md"}


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def copy_fixture(tmp: Path, name: str = "demo") -> Path:
    """A mutated-copy fixture: the mini-spec docset plus the repo its
    survey cites, so the evidence stays real under the tmp root."""
    (tmp / "specs").mkdir(parents=True, exist_ok=True)
    dst = tmp / "specs" / name
    shutil.copytree(FIXTURE, dst)
    shutil.copytree(FIXTURE_REPO, tmp / "repo")
    return dst


def set_status(spec_dir: Path, word: str) -> None:
    p = spec_dir / "spec.md"
    write(p, p.read_text(encoding="utf-8").replace(
        "**Status**: draft", f"**Status**: {word}"))


def land_all_tasks(spec_dir: Path) -> None:
    """Mark every task `(implemented)` — execute's completion state
    without the forbidden early tick, the delivery-pending stretch
    where tick-commit is the pending human gate."""
    p = spec_dir / "task.md"
    t = p.read_text(encoding="utf-8")
    for tid, head in (("T001", "Implement multiply"),
                      ("T002", "Add multiply tests")):
        t = t.replace(f"- [ ] {tid} [P] {head}",
                      f"- [ ] {tid} [P] (implemented) {head}")
    write(p, t)


def break_task_entry(spec_dir: Path) -> None:
    """A broken task entry shape: the burndown table disagrees with the
    actual entries (5 claimed, 2 present) — a deterministic check.py
    FAIL that never touches the survey evidence."""
    p = spec_dir / "task.md"
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"^(\|\s*1\s*\|\s*)2(\s*\|\s*)0(\s*\|)$",
               r"\g<1>5\g<2>0\g<3>", t, flags=re.M)
    t = re.sub(r"^(\|\s*\*\*Σ\*\*\s*\|\s*)2(\s*\|\s*)0(\s*\|)$",
               r"\g<1>5\g<2>0\g<3>", t, flags=re.M)
    write(p, t)


def run_graph(spec_dir: Path, *args: str, tel: Path) -> subprocess.CompletedProcess:
    """graph.py as the real CLI, with telemetry relocated into `tel` and
    explicitly enabled — the subprocess must never read (or write) the
    developer's real store, and a locally-disabled store would turn the
    telemetry assertions into silent no-ops."""
    env = dict(os.environ, KIT_TELEMETRY_DIR=str(tel), KIT_TELEMETRY="on")
    return subprocess.run(
        [sys.executable, str(GRAPH), str(spec_dir), *args],
        capture_output=True, text=True, timeout=300, env=env)


def run_check(spec_dir: Path) -> int:
    r = subprocess.run([sys.executable, str(CHECK), str(spec_dir)],
                       capture_output=True, text=True, timeout=300)
    return r.returncode


def telemetry_events(tel: Path, skill: str = "spec-execute") -> list[dict]:
    p = tel / f"{skill}.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in
            p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def payload_nodes(stdout: str) -> list[str]:
    """The `node:` value of every written-payload line — the span's
    actual emission surface, independent of file naming. Hyphens count:
    tick-commit is a node name."""
    return re.findall(r"payload: .+ \(role: [\w-]+, node: ([\w-]+)\)",
                      stdout)


def spawn_files(spec_dir: Path) -> list[str]:
    spawns = spec_dir / "spawns"
    if not spawns.exists():
        return []
    return sorted(p.name for p in spawns.rglob("*.md"))


def refusal_gates(stdout: str) -> list[str]:
    return re.findall(r"blocking gate (\w+):", stdout)


def dir_checksum(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


class Gate001DraftRefusalTests(unittest.TestCase):
    """GATE-001 (FR-004): a green docset at Status: draft refuses
    execute-span entry naming the approve gate — exit 4, zero payloads
    written, one intake_refusal telemetry event under the derived skill
    name. The gate is mode-independent: --emit-spawns and --run are both
    executions of the span, so both refuse identically."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="gate001-"))
        cls.spec_dir = copy_fixture(cls._tmp)  # draft as committed
        cls.tel = cls._tmp / "tel"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_draft_refuses_exit_four_naming_approve(self):
        before = dir_checksum(self.spec_dir)
        r = run_graph(self.spec_dir, "--span", "execute", "--emit-spawns",
                      tel=self.tel)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("span entry refused", r.stdout)
        self.assertEqual(refusal_gates(r.stdout), ["approve"])
        # zero payloads: the refusal precedes every executor mode, so
        # the docset (spawns/ included) is byte-identical
        self.assertFalse((self.spec_dir / "spawns").exists())
        self.assertEqual(dir_checksum(self.spec_dir), before)

    def test_draft_refusal_records_intake_refusal_telemetry(self):
        run_graph(self.spec_dir, "--span", "execute", "--emit-spawns",
                  tel=self.tel)
        events = [e for e in telemetry_events(self.tel)
                  if e["event"] == "intake_refusal"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["skill"], "spec-execute")
        self.assertEqual(events[0]["payload"]["span"], "execute")
        self.assertEqual(events[0]["payload"]["gates"], ["approve"])

    def test_run_mode_refuses_identically(self):
        r = run_graph(self.spec_dir, "--span", "execute", "--run",
                      tel=self.tel)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertEqual(refusal_gates(r.stdout), ["approve"])
        self.assertFalse((self.spec_dir / "spawns").exists())


class Gate002RedCheckRefusalTests(unittest.TestCase):
    """GATE-002 (FR-004): Status approved is necessary, not sufficient —
    a red check.py (here: a task entry whose burndown disagrees with the
    actual entries) leaves verify not-DONE, and the span refuses naming
    it (approve appears too, blocked on verify — the engine reports both
    non-DONE gates)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="gate002-"))
        cls.spec_dir = copy_fixture(cls._tmp)
        set_status(cls.spec_dir, "approved")
        break_task_entry(cls.spec_dir)
        cls.tel = cls._tmp / "tel"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_fixture_premise_check_is_red(self):
        self.assertEqual(run_check(self.spec_dir), 1)

    def test_red_check_refuses_naming_verify(self):
        before = dir_checksum(self.spec_dir)
        r = run_graph(self.spec_dir, "--span", "execute", "--emit-spawns",
                      tel=self.tel)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("verify", refusal_gates(r.stdout))
        self.assertIn("check.py exits 1", r.stdout)
        self.assertFalse((self.spec_dir / "spawns").exists())
        self.assertEqual(dir_checksum(self.spec_dir), before)

    def test_red_check_refusal_telemetry_names_verify(self):
        run_graph(self.spec_dir, "--span", "execute", "--run", tel=self.tel)
        events = [e for e in telemetry_events(self.tel)
                  if e["event"] == "intake_refusal"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["skill"], "spec-execute")
        self.assertEqual(events[0]["payload"]["span"], "execute")
        self.assertIn("verify", events[0]["payload"]["gates"])


class Gate003ApprovedGreenExecuteTests(unittest.TestCase):
    """GATE-003 (FR-004, FR-008, NFR-003): the approved-and-green
    docset executes. --emit-spawns writes implementer payload(s) for the
    runnable tasks only; --run with the print runner drives the wave and
    stops — at `AWAITING HUMAN: tick-commit` once every task has landed
    (the print runner mutates nothing, so the runnable shape stops on
    the unchanged state and tick-commit reads blocked-on-execute in
    --state-json, the state half of the same gate) — and no authoring
    payload ever appears under the execute span."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="gate003-"))
        # runnable shape: mini-spec as committed (2 open [P] tasks) + approval
        cls.runnable = copy_fixture(cls._tmp / "a")
        set_status(cls.runnable, "approved")
        # landed shape: every task (implemented) — delivery-pending, the
        # tick-commit human gate is the whole frontier
        cls.landed = copy_fixture(cls._tmp / "b")
        set_status(cls.landed, "approved")
        land_all_tasks(cls.landed)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def assert_no_authoring_payloads(self, stdout: str, files: list[str]):
        for node in payload_nodes(stdout):
            self.assertNotIn(node, AUTHORING_NODES, stdout)
        self.assertEqual(
            sorted(set(files) & AUTHORING_FILES), [], files)

    def test_fixture_premise_check_is_green(self):
        self.assertEqual(run_check(self.runnable), 0)

    def test_emit_spawns_writes_implementer_payloads_for_runnable_tasks(self):
        tel = self._tmp / "tel-runnable"
        r = run_graph(self.runnable, "--span", "execute", "--emit-spawns",
                      tel=tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("span entry refused", r.stdout)
        files = spawn_files(self.runnable)
        self.assertEqual(files, ["implementer-T001.md",
                                 "implementer-T002.md"])
        self.assertEqual(payload_nodes(r.stdout), ["execute", "execute"])
        self.assert_no_authoring_payloads(r.stdout, files)
        # the payload carries its task entry verbatim — one implementer
        # per runnable task, not a generic brief
        text = next((self.runnable / "spawns").glob(
            "*/implementer-T001.md")).read_text(encoding="utf-8")
        self.assertIn("- [ ] T001 [P] Implement multiply", text)

    def test_run_drives_the_execute_wave_with_print_runner(self):
        tel = self._tmp / "tel-run"
        r = run_graph(self.runnable, "--span", "execute", "--run", tel=tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("verify: check.py", r.stdout)
        self.assertIn("exit 0", r.stdout)
        self.assertIn("== wave", r.stdout)
        self.assertIn("frontier: execute", r.stdout)
        self.assertEqual(r.stdout.count("runner[print]: implementer:"), 2)
        files = spawn_files(self.runnable)
        self.assertEqual(files, ["implementer-T001.md",
                                 "implementer-T002.md"])
        self.assert_no_authoring_payloads(r.stdout, files)
        # the print runner mutates no doc state, so the loop stops on the
        # unchanged state — never past it into a second wave
        self.assertEqual(r.stdout.count("== wave"), 1)
        # the runnable shape's tick-commit state: still blocked on
        # execute (the state half of the tick-commit gate)
        s = json.loads(run_graph(self.runnable, "--state-json",
                                 tel=tel).stdout)
        self.assertEqual(s["nodes"]["tick-commit"]["state"], "blocked")
        self.assertIn("waiting on: execute",
                      s["nodes"]["tick-commit"]["reason"])
        # NFR-003: the run recorded its wave under the derived name
        waves = [e for e in telemetry_events(tel) if e["event"] == "wave"]
        self.assertEqual(waves[-1]["payload"]["roles"], ["execute"])

    def test_landed_run_stops_at_the_tick_commit_gate(self):
        tel = self._tmp / "tel-landed"
        # unittest runs these alphabetically, so the emit test below may
        # already have prepared payloads — start from a clean spawns/
        # to prove THIS run's pause writes nothing
        shutil.rmtree(self.landed / "spawns", ignore_errors=True)
        r = run_graph(self.landed, "--span", "execute", "--run", tel=tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        # the pause precedes any wave: nothing is spawned by the run
        self.assertEqual(spawn_files(self.landed), [])
        s = json.loads(run_graph(self.landed, "--state-json",
                                 tel=tel).stdout)
        self.assertEqual(s["nodes"]["execute"]["state"], "done")
        self.assertEqual(s["nodes"]["tick-commit"]["state"], "READY")
        pauses = [e for e in telemetry_events(tel)
                  if e["event"] == "gate_pause"]
        self.assertEqual(pauses[-1]["payload"]["node"], "tick-commit")

    def test_landed_emit_prepares_only_the_reviewer_payload(self):
        # delivery-pending: the execute span's other payload is the
        # tick-commit reviewer's implementation-diff brief — still no
        # authoring role under this span
        tel = self._tmp / "tel-landed-emit"
        shutil.rmtree(self.landed / "spawns", ignore_errors=True)
        r = run_graph(self.landed, "--span", "execute", "--emit-spawns",
                      tel=tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        files = spawn_files(self.landed)
        self.assertEqual(files, ["reviewer-diff.md"])
        self.assertEqual(payload_nodes(r.stdout), ["tick-commit"])
        self.assert_no_authoring_payloads(r.stdout, files)


# ---------------------------------------------------------------------------
# GATE-004: the hand-authored docset. Same contract shapes as mini-spec,
# entirely different prose (no kit template was copied) — the gate reads
# Status + green check.py, never kit provenance (FR-008).
# ---------------------------------------------------------------------------

HAND_SPEC = """# Spec: handbuilt

**Status**: {status}
**Created**: 2026-10-11

## What
A greetings module learns to shout: the existing whisper helper gains a
shout counterpart that uppercases its argument before returning it.

## Why
The demo can only whisper today; shouted banners are the top request on
the audience-feedback list, and presenters work around it by SHOUTING IN
prose, which helps nobody.

## Business value
Audiences read shouted banners from the back of the room; the
whisper-only module loses them in the first ten seconds of every demo.

## User stories
### US1 — Shout a message (P1)
As a demo presenter, I want my message uppercased, so that the back row
can read it.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given the greetings module loaded, When I shout a lowercase
  word, Then the returned text is uppercase.
- AC2: Given any punctuated message, When I shout it, Then every
  punctuation character survives unchanged.

## Requirements
- **FR-001**: WHEN the caller shouts a message, the system shall return
  the message uppercased.
- **FR-002**: WHEN the caller shouts a punctuated message, the system
  shall keep every punctuation character unchanged.
"""

HAND_SURVEY = """---
# Survey: handbuilt

**Created**: 2026-10-11 | **Baseline**: handbuilt v3 @ 1a2b3c4
Phase-A output for a hand-authored fixture: no surveyor agent ran, the
prose exists to satisfy the survey contract shape with real content.

## Items

```
item S1: "greetings module exposes whisper only"
  evidence:   none recorded — hand-authored fixture, no session grep
  status:     DONE
  verify:     none
item S2: "no shout counterpart exists anywhere in the module"
  evidence:   none recorded — hand-authored fixture, no session grep
  status:     TODO
  verify:     none
  gap:        shout is absent from the module surface
```
"""

HAND_RESEARCH = """# Research: handbuilt

not applicable — no open questions at Stage 0

Recorded by hand: the change mirrors an existing helper, so nothing
genuinely unknown remains for a researcher to resolve.
"""

HAND_PLAN = """# Plan: handbuilt

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-11

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1     | Shout lands | shout of a lowercase word returns uppercase | FR-001, FR-002 | — |

## Milestone 1: shout lands
Both requirements land together: the helper and its punctuation
preservation follow one code path. Checkpoint: the module's own test
run stays green.

## Parallelization map
- one implementer owns the module; no parallel wave is needed.
"""

HAND_TECH = """# Tech spec: handbuilt

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-11

## Approach
Mirror the existing whisper helper: one pure function, string in,
uppercased string out, no state anywhere.

### D-001: plain function beside whisper
- **Context**: the module already ships bare helpers; no classes exist.
- **Decision**: a plain module-level function matching the established
  shape.
- **Consequences**: nothing to migrate; callers import directly.
"""

HAND_TASKS = """# Tasks: handbuilt

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state, not intent.

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1     | 2     | 0    |
| **Σ** | 2     | 0    |

## Phase 1: shout lands (FR-001, FR-002)
- [ ] T001 implement the shout helper in the module (FR-001)
- [ ] T002 (after T001) pin punctuation behavior with a test (FR-002)

## Conventions
- todo as written; done flips to checked with a proof note
- Every task cites its FR-###; tasks with no FR are scope creep
"""

HAND_TEST = """# Test cases: handbuilt

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-11
Black-box verification traced to requirements.

## TC-001 — Shout uppercases
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** the greetings module loaded
- **When** shout is called with a lowercase word
- **Then** the returned text is uppercase
- **Pass condition**: `python3 -c 'print("HI")'` exits 0

## TC-002 — Punctuation survives
- **Story**: US1 · **Traces to**: FR-002, AC2
- **Given** the greetings module loaded
- **When** shout is called with a punctuated message
- **Then** every punctuation character is unchanged
- **Pass condition**: `python3 -c 'print("HI!")'` exits 0

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001      | TC-001     | auto               |
| FR-002      | TC-002     | auto               |
"""


def hand_docset(tmp: Path, status: str = "approved") -> Path:
    """A complete docset authored from scratch: same contract shapes as
    the kit's templates, different prose throughout. Written directly —
    no scaffold, no template copy — which is exactly the provenance the
    gate must not care about."""
    d = tmp / "specs" / "handbuilt"
    d.mkdir(parents=True)
    write(d / "spec.md", HAND_SPEC.format(status=status))
    for name, text in (("survey.md", HAND_SURVEY),
                       ("research.md", HAND_RESEARCH),
                       ("plan.md", HAND_PLAN),
                       ("tech-spec.md", HAND_TECH),
                       ("task.md", HAND_TASKS),
                       ("test.md", HAND_TEST)):
        write(d / name, text)
    return d


def land_hand_tasks(spec_dir: Path) -> None:
    p = spec_dir / "task.md"
    t = p.read_text(encoding="utf-8")
    t = t.replace("- [ ] T001 implement",
                  "- [ ] T001 (implemented) implement")
    t = t.replace("- [ ] T002 (after T001) pin",
                  "- [ ] T002 (after T001) (implemented) pin")
    write(p, t)


class Gate004HandAuthoredEquivalenceTests(unittest.TestCase):
    """GATE-004 (FR-008): a hand-authored docset executes identically to
    a shaped one. The gate's inputs are Status and check.py's exit — so
    the draft refusal, the approved run, the emitted payload roles, and
    the tick-commit stop must all match the mini-spec-shaped fixtures'
    outcomes node for node."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="gate004-"))
        cls.hand = hand_docset(cls._tmp / "a", "approved")
        cls.hand_draft = hand_docset(cls._tmp / "b", "draft")
        cls.hand_landed = hand_docset(cls._tmp / "c", "approved")
        land_hand_tasks(cls.hand_landed)
        cls.shaped = copy_fixture(cls._tmp / "d")
        set_status(cls.shaped, "approved")
        cls.shaped_draft = copy_fixture(cls._tmp / "e")
        cls.shaped_landed = copy_fixture(cls._tmp / "f")
        set_status(cls.shaped_landed, "approved")
        land_all_tasks(cls.shaped_landed)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_hand_docset_passes_the_check_green(self):
        self.assertEqual(run_check(self.hand), 0)

    def test_draft_refusal_outcome_matches_the_shaped_fixture(self):
        hand_r = run_graph(self.hand_draft, "--span", "execute",
                           "--emit-spawns", tel=self._tmp / "tel-h")
        shaped_r = run_graph(self.shaped_draft, "--span", "execute",
                             "--emit-spawns", tel=self._tmp / "tel-s")
        self.assertEqual(hand_r.returncode, shaped_r.returncode)
        self.assertEqual(hand_r.returncode, 4)
        self.assertEqual(refusal_gates(hand_r.stdout),
                         refusal_gates(shaped_r.stdout))
        self.assertEqual(refusal_gates(hand_r.stdout), ["approve"])
        self.assertEqual(spawn_files(self.hand_draft), [])

    def test_approved_emit_outcome_matches_the_shaped_fixture(self):
        hand_r = run_graph(self.hand, "--span", "execute", "--emit-spawns",
                           tel=self._tmp / "tel-h")
        shaped_r = run_graph(self.shaped, "--span", "execute",
                             "--emit-spawns", tel=self._tmp / "tel-s")
        self.assertEqual(hand_r.returncode, shaped_r.returncode)
        self.assertEqual(hand_r.returncode, 0, hand_r.stdout + hand_r.stderr)
        # one runnable task (T002 chains after T001) → one implementer
        # payload, node execute — the same emission surface the shaped
        # fixture produces for its own runnable set
        self.assertEqual(payload_nodes(hand_r.stdout), ["execute"])
        self.assertEqual(spawn_files(self.hand), ["implementer.md"])
        self.assertNotIn("span entry refused", hand_r.stdout)
        self.assertEqual(
            set(payload_nodes(hand_r.stdout))
            & AUTHORING_NODES, set())

    def test_landed_run_stop_matches_the_shaped_fixture(self):
        hand_r = run_graph(self.hand_landed, "--span", "execute", "--run",
                           tel=self._tmp / "tel-h")
        shaped_r = run_graph(self.shaped_landed, "--span", "execute",
                             "--run", tel=self._tmp / "tel-s")
        for r in (hand_r, shaped_r):
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        self.assertEqual(spawn_files(self.hand_landed), [])


class Gate005LifecycleCommandSurfaceTests(unittest.TestCase):
    """GATE-005 (FR-004, FR-010's surface half): the five lifecycle
    commands moved in T016 live in spec-execute's commands dir, each
    carrying the skill's own frontmatter binding, and extra.txt claims
    every bare name exactly once — the retired monolith holds none of
    them because its tree is gone (T023; the install-level pin —
    INSTALL sets, sync behavior — is T019's, this is the presence +
    claim coherence T018 names)."""

    def test_the_five_lifecycle_commands_exist_with_content(self):
        for name in LIFECYCLE_COMMANDS:
            p = COMMANDS / name
            self.assertTrue(p.exists(), name)
            text = p.read_text(encoding="utf-8")
            self.assertGreater(len(text.strip()), 100, name)
            self.assertIn("skills: spec-execute", text, name)

    def test_the_skill_router_verb_exists(self):
        p = COMMANDS / "spec-execute.md"
        self.assertTrue(p.exists())
        text = p.read_text(encoding="utf-8")
        self.assertIn("skills: spec-execute", text)
        self.assertIn("--span execute", text)

    def test_extra_txt_claims_every_bare_name_exactly_once(self):
        text = (COMMANDS / "extra.txt").read_text(encoding="utf-8")
        names = text.split()
        self.assertEqual(names, CLAIMED_BARE_NAMES)
        self.assertEqual(len(names), len(set(names)))

    def test_the_retired_monolith_is_gone_so_no_second_claimant_exists(self):
        # exactly one claimant per bare name: T016 moved the files and
        # dropped the claims together, and T023 deleted the monolith
        # outright — the whole tree's absence is the coherence pin now
        self.assertFalse((SKILL.parent / "spec-to-prod").exists(),
                         "the retired monolith must not ship")


if __name__ == "__main__":
    unittest.main(verbosity=2)
