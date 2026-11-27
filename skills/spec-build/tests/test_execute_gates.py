"""Invocation gate for spec-build.

`graph.py <dir> --span execute` refuses (exit 4, blocking gate printed,
an intake_refusal telemetry event) unless approve and verify are DONE.
Any directory that satisfies the docset contract is accepted, not only
kit-shaped ones. The cases pin:

  - a draft docset refuses naming approve, writes zero payloads, and
    records telemetry;
  - an approved-but-red docset refuses naming verify the same way;
  - the approved-and-green fixture executes: implementer payloads for
    runnable tasks, the print runner stops at the tick-commit gate on a
    landed shape, and no authoring payload is ever emitted;
  - a hand-authored docset with the same contract shapes gets identical
    refusal and gate outcomes;
  - the lifecycle command surface and its bare-name claims;
  - the wave is file-disjoint, an orphaned claim is named, an open fix
    round re-opens a landed task with its evidence (round 4's payload
    alone carrying its model step), and a tiny-tier Status flip without
    the freeze stays refused, and so does an agent-forged approval: a
    self-authored review and a hand-written record with no signature
    never open execute — only the owner's signed `freeze.py --approve`
    does.

Fixtures are mutated copies of examples/mini-spec (never the original)
plus the repo it cites, and a from-scratch hand-authored docset. Every
CLI run gets its own telemetry dir so assertions read only that run's
events.
"""

import hashlib
import importlib.util
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

_freeze_spec = importlib.util.spec_from_file_location(
    "freeze", SCRIPTS / "freeze.py")
freeze = importlib.util.module_from_spec(_freeze_spec)
_freeze_spec.loader.exec_module(freeze)
_retro_spec = importlib.util.spec_from_file_location(
    "retro", SCRIPTS / "retro.py")
retro = importlib.util.module_from_spec(_retro_spec)
_retro_spec.loader.exec_module(retro)

import _approval  # noqa: E402

# One command per skill (D-033): the router is this package's single
# command; the lifecycle verbs ride it as arguments.
ROUTER_COMMAND = "spec-build.md"
CLAIMED_BARE_NAMES = ["spec-build"]
LIFECYCLE_VERBS = ("implement", "test", "audit", "ship")

# Payload vocabulary the execute span may never emit: the authoring
# nodes live in spec-design's span, so their appearance here would mean
# the span filter (or its gate) leaked authoring into execution.
AUTHORING_NODES = {"intent", "plan", "tech", "qa", "tasks",
                   "design", "research"}
AUTHORING_FILES = {"analyst.md", "planner.md", "tech.md", "qa.md",
                   "task-breaker.md", "designer.md", "researcher.md"}


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def copy_fixture(tmp: Path, name: str = "demo") -> Path:
    """A mutated-copy fixture: the mini-spec docset plus the repo its
    § Code state cites, so the evidence stays real under the tmp root."""
    (tmp / "specs").mkdir(parents=True, exist_ok=True)
    dst = tmp / "specs" / name
    shutil.copytree(FIXTURE, dst)
    shutil.copytree(FIXTURE_REPO, tmp / "repo")
    return dst


def record_approval(spec_dir: Path) -> None:
    """The approve gate's two records: the contract review carrying the
    docset fingerprint, then the owner's signed freeze."""
    approvals = spec_dir / "approvals"
    approvals.mkdir(exist_ok=True)
    write(approvals / "review.md",
          "# Contract review\n\nDocset fingerprint: "
          f"{freeze.docset_fingerprint(spec_dir)}\n\n"
          "tools: Read, Grep, Glob\n"
          "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none\n")
    _approval.approve(spec_dir, review=str(approvals / "review.md"),
                      force=True)


def set_status(spec_dir: Path, word: str) -> None:
    p = spec_dir / "spec.md"
    write(p, p.read_text(encoding="utf-8").replace(
        "**Status**: draft", f"**Status**: {word}"))
    if word == "approved":
        record_approval(spec_dir)


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
    FAIL that never touches the Code state evidence."""
    p = spec_dir / "task.md"
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"^(\|\s*1\s*\|\s*)2(\s*\|\s*)0(\s*\|.*)$",
               r"\g<1>5\g<2>0\g<3>", t, flags=re.M)
    t = re.sub(r"^(\|\s*\*\*Σ\*\*\s*\|\s*)2(\s*\|\s*)0(\s*\|.*)$",
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


def telemetry_events(tel: Path, skill: str = "spec-build") -> list[dict]:
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
    """A green docset at Status: draft refuses execute-span entry naming
    the approve gate: exit 4, zero payloads, one intake_refusal event.
    --emit-spawns and --run both execute the span, so both refuse."""

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
        self.assertEqual(events[0]["skill"], "spec-build")
        self.assertEqual(events[0]["payload"]["span"], "execute")
        self.assertEqual(events[0]["payload"]["gates"], ["approve"])

    def test_run_mode_refuses_identically(self):
        r = run_graph(self.spec_dir, "--span", "execute", "--run",
                      tel=self.tel)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertEqual(refusal_gates(r.stdout), ["approve"])
        self.assertFalse((self.spec_dir / "spawns").exists())


class Gate002RedCheckRefusalTests(unittest.TestCase):
    """Status approved is necessary, not sufficient: a red check.py (a task
    entry whose burndown disagrees with the entries) leaves verify not
    DONE, and the span refuses naming it. The engine also lists approve,
    blocked on verify."""

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
        self.assertEqual(events[0]["skill"], "spec-build")
        self.assertEqual(events[0]["payload"]["span"], "execute")
        self.assertIn("verify", events[0]["payload"]["gates"])


class Gate003ApprovedGreenExecuteTests(unittest.TestCase):
    """The approved-and-green docset executes. --emit-spawns writes
    implementer payloads for runnable tasks only. --run with the print
    runner stops at `AWAITING HUMAN: tick-commit` once every task has
    landed; on the runnable shape the print runner mutates nothing, so
    the state stays put and tick-commit reads blocked. No authoring
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
        self.assertIn("TC-001: `cd repo && python3 -m pytest test_calc.py "
                      "-k multiply`", text)

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
        # the run recorded its wave under the skill's derived name
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
# Hand-authored docset: same contract shapes as mini-spec, entirely different
# prose. The gate reads Status and check.py's exit, never kit provenance.
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

## Quality attributes
- **NFR-001**: Security, Privacy, Performance, Reliability, Observability,
  Accessibility — not applicable: one pure string helper with no input
  boundary, stored data, I/O, or interface beyond its argument.
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

### Rollout
none — the helper ships whole with the delivery commit; reverting that
commit is the rollback.
"""

HAND_TECH = """# Tech spec: handbuilt

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-11
**Baseline**: handbuilt v3 @ 1a2b3c4

## Code state
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

## Approach
Mirror the existing whisper helper: one pure function, string in,
uppercased string out, no state anywhere.

## Interfaces & data
One new module-level function beside whisper; no stored data, no
existing signature changes.

## Decisions
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
| Phase | Total | Done | Verified |
|-------|-------|------|----------|
| 1     | 2     | 0    |          |
| **Σ** | 2     | 0    |          |

## Phase 1: shout lands (FR-001, FR-002)
- [ ] T001 implement the shout helper in the module (FR-001)
  - Proves: TC-001
- [ ] T002 (after T001) pin punctuation behavior with a test (FR-002)
  - Proves: TC-002

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


class Gate010ForgedApprovalTests(unittest.TestCase):
    """An approval only a human can grant: a record any write-capable
    agent can author — the review, the fingerprint, the digest line, the
    manifest, a flipped Status — is refused at the execute gate like a
    draft. Only the owner's signed `freeze.py --approve` opens it."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="gate010-"))
        cls.spec_dir = copy_fixture(cls._tmp)
        cls.tel = cls._tmp / "tel"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_a_forged_approval_is_refused_and_a_signed_one_admitted(self):
        spec_dir = self.spec_dir
        approvals = spec_dir / "approvals"
        approvals.mkdir()
        write(approvals / "review.md",
              "# Contract review\n\nDocset fingerprint: "
              f"{freeze.docset_fingerprint(spec_dir)}\n\n"
              "tools: Read, Grep, Glob\n"
              "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none\n")
        review = freeze.fold_review(
            (approvals / "review.md").read_text(encoding="utf-8"))
        write(approvals / "approval.md", freeze.render(spec_dir, "-", (), review))
        spec = spec_dir / "spec.md"
        write(spec, spec.read_text(encoding="utf-8").replace(
            "**Status**: draft", "**Status**: approved"))

        forged = run_graph(spec_dir, "--run", "--span", "execute",
                           tel=self.tel)
        self.assertEqual(forged.returncode, 4, forged.stdout + forged.stderr)
        self.assertIn("span entry refused", forged.stdout)
        self.assertEqual(refusal_gates(forged.stdout), ["approve", "verify"])
        self.assertFalse((spec_dir / "spawns").exists())

        _approval.approve(spec_dir, force=True, review=str(approvals / "review.md"))
        signed = run_graph(spec_dir, "--run", "--span", "execute",
                           tel=self.tel)
        self.assertNotIn("span entry refused", signed.stdout)
        self.assertNotEqual(signed.returncode, 4, signed.stdout + signed.stderr)


def hand_docset(tmp: Path, status: str = "approved") -> Path:
    """A complete docset authored from scratch: same contract shapes as
    the kit's templates, different prose throughout. Written directly —
    no scaffold, no template copy — which is exactly the provenance the
    gate must not care about."""
    d = tmp / "specs" / "handbuilt"
    d.mkdir(parents=True)
    write(d / "spec.md", HAND_SPEC.format(status=status))
    for name, text in (("research.md", HAND_RESEARCH),
                       ("plan.md", HAND_PLAN),
                       ("tech-spec.md", HAND_TECH),
                       ("task.md", HAND_TASKS),
                       ("test.md", HAND_TEST)):
        write(d / name, text)
    if status == "approved":
        record_approval(d)
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
    """A hand-authored docset executes identically to a shaped one: the
    draft refusal, the approved run, the emitted payload roles, and the
    tick-commit stop all match the mini-spec fixtures node for node."""

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
        # one runnable task (the second chains after the first) gives one
        # implementer payload, the same emission surface as the shaped fixture
        self.assertEqual(payload_nodes(hand_r.stdout), ["execute"])
        self.assertEqual(spawn_files(self.hand), ["implementer-T001.md"])
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


def edit_tasks(spec_dir: Path, *pairs: tuple[str, str]) -> None:
    p = spec_dir / "task.md"
    t = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in t, old
        t = t.replace(old, new)
    write(p, t)


T1 = "- [ ] T001 [P] Implement multiply"
T2 = "- [ ] T002 [P] Add multiply tests"

TINY_SPEC = """# Spec: tiny

**Status**: approved
**Tier**: tiny
**Effort**: standard
**Created**: 2026-10-10

## What
A demo capability proving the one-file contract.

## Why
A one-file spec still needs an approval that is more than a word.

## Requirements
- **FR-001**: The system shall greet the named user.

## Tasks

- [ ] T001 add the greeting module (FR-001) [P]
  - Touches: `src/greet.py`
  - Accept: `python3 -c "assert True"`

## Evidence
"""


class Gate006WaveAndFixRoundTests(unittest.TestCase):
    """What the execute wave may spawn: tasks that share no file, never
    a claimed task, and a landed task again once a fix round opens on
    it — with the round's evidence in the payload, and on round 4 the
    model step (the `Model:` line, the emit line, the native form)."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="gate006-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def approved(self, *task_edits: tuple[str, str]) -> Path:
        spec_dir = copy_fixture(self._tmp)
        set_status(spec_dir, "approved")
        edit_tasks(spec_dir, *task_edits)
        return spec_dir

    def emit(self, spec_dir: Path, *extra: str):
        return run_graph(spec_dir, "--span", "execute", "--emit-spawns",
                         *extra, tel=self.tel)

    def test_tasks_sharing_a_file_never_share_a_wave(self):
        spec_dir = self.approved(
            ("tests to `repo/test_calc.py`",
             "tests to `repo/test_calc.py` and `repo/calc.py`"))
        r = self.emit(spec_dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(spawn_files(spec_dir), ["implementer-T001.md"])
        self.assertIn("deferred: T002 (shares repo/calc.py with T001)",
                      r.stdout)

    def test_a_task_naming_no_files_runs_alone(self):
        spec_dir = hand_docset(self._tmp)
        edit_tasks(spec_dir, ("T002 (after T001) pin", "T002 pin"))
        r = self.emit(spec_dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(spawn_files(spec_dir), ["implementer-T001.md"])
        self.assertIn("deferred: T002 (T001 has no parseable Touches:",
                      r.stdout)

    def test_an_orphaned_claim_is_named_with_its_remedy(self):
        spec_dir = self.approved(
            (T1, T1.replace("[P]", "[P] (in-progress)")),
            (T2, T2.replace("[P]", "[P] (implemented)")))
        for mode in ("--emit-spawns", "--run"):
            r = run_graph(spec_dir, "--span", "execute", mode, tel=self.tel)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("AWAITING ORCHESTRATOR: execute", r.stdout, mode)
            self.assertIn("claimed: T001", r.stdout, mode)
            self.assertIn("orphan", r.stdout, mode)
            self.assertIn("clear the claim", r.stdout, mode)
        self.assertEqual(spawn_files(spec_dir), [])

    def test_an_open_fix_round_reopens_a_landed_task_with_its_evidence(self):
        spec_dir = self.approved(
            (T1, T1.replace("[P]", "[P] (implemented) (fix 1/5)")),
            (T2, T2.replace("[P]", "[P] (implemented)")))
        r = self.emit(spec_dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # the plan is not landed: the builder goes back out, the
        # delivery reviewer does not
        self.assertEqual(spawn_files(spec_dir), ["implementer-T001.md"])
        self.assertIn("evidence missing: T001 fix round 1", r.stdout)
        payload = next((spec_dir / "spawns").glob("*/implementer-T001.md"))
        self.assertIn("FAILURE EVIDENCE NOT RECORDED",
                      payload.read_text(encoding="utf-8"))

        (spec_dir / "notes").mkdir()
        evidence = "E   AssertionError: multiply(2, 3) returned 5"
        write(spec_dir / "notes" / "T001.md",
              f"## Fix round 1\n$ pytest -k multiply\n{evidence}\n")
        r = self.emit(spec_dir)
        self.assertNotIn("evidence missing", r.stdout)
        self.assertIn(evidence, payload.read_text(encoding="utf-8"))
        # one round, nothing to compare it against: no rule yet
        self.assertNotIn("Same-signature rule", payload.read_text(
            encoding="utf-8"))

        # the model step rides the payload on round 4 alone — in its
        # header block, named on the emit line too; under --native-agents
        # that one payload keeps the brief and states both spawn routes
        model_line = ("- Model: this round runs one model step above the "
                      "developer brief's model — fix round 4, the last "
                      "round that spawns, after rounds 1–3 came back wrong "
                      "at that model: four rounds spawn, the fifth failure "
                      "stops")
        brief_heading = "# Developer agent (implement lens)"
        for marker, stepped in (("(fix 4/5)", True), ("(fix 3/5)", False)):
            p = spec_dir / "task.md"
            write(p, re.sub(r"\(fix \d/5\)", marker,
                            p.read_text(encoding="utf-8")))
            for extra in ((), ("--native-agents",)):
                with self.subTest(marker=marker, native=bool(extra)):
                    r = self.emit(spec_dir, *extra)
                    self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                    text = payload.read_text(encoding="utf-8")
                    # the default form always embeds the brief; the
                    # native form embeds it on the model-step round alone
                    self.assertEqual(brief_heading in text,
                                     stepped or not extra)
                    self.assertEqual(model_line in text, stepped)
                    self.assertEqual("\n- Model: " in text, stepped)
                    emitted = next(ln for ln in r.stdout.splitlines()
                                   if "   payload: " in ln
                                   and "implementer-T001.md" in ln)
                    self.assertEqual(
                        "— fix round 4: runs one model step above the "
                        "developer brief's model" in emitted, stepped)
                    if not stepped:
                        continue
                    header = text.split("## Input payload", 1)[0]
                    self.assertIn("- skill_dir: ", header)
                    self.assertIn(model_line, header)
                    self.assertIn("- Rounds: four rounds spawn, the fifth "
                                  "failure stops — this is round 4", text)
                    if extra:
                        self.assertIn("agent type `spec-developer`", text)
                        self.assertIn("spawn-time model override", text)
                        self.assertIn("general-purpose agent on the "
                                      "stronger model", text)
                        # one brief reaching the agent once, protocol aside
                        self.assertEqual(
                            text.count("Long foreground tasks\n"), 1)

    def test_from_the_second_round_the_payload_points_at_the_signature_rule(
            self):
        spec_dir = self.approved(
            (T1, T1.replace("[P]", "[P] (implemented) (fix 2/5)")))
        (spec_dir / "notes").mkdir()
        note = spec_dir / "notes" / "T001.md"
        payload = spec_dir / "spawns" / "wave-4" / "implementer-T001.md"
        rule = ("- Same-signature rule: when the newest `## Fix round` "
                "section's `$ <command>` line is the same command as the "
                "round before it, another round re-runs it — the plan, not "
                "the model, is the suspect (`contracts/execution.md` § Fix "
                "rounds)")

        # two different failing commands: the rule, and no verdict
        write(note, "## Fix round 1\n$ pytest -k multiply\nE   one\n"
                    "## Fix round 2\n$ go test ./...\nFAIL: two\n")
        self.emit(spec_dir)
        text = payload.read_text(encoding="utf-8")
        self.assertIn("- Fix round 2 — failure evidence and prior attempts "
                      f"({note}, verbatim):", text)
        self.assertIn("- Rounds: four rounds spawn, the fifth failure stops "
                      "— this is round 2", text)
        self.assertEqual(text.count(rule), 1)
        self.assertNotIn("This task is there", text)

        # one command twice: the payload says so, naming the command
        write(note, "## Fix round 1\n$ pytest -k multiply\nE   one\n"
                    "## Fix round 2\n$ pytest -k multiply\nE   two\n")
        self.emit(spec_dir)
        self.assertIn(rule + ". This task is there: `$ pytest -k multiply` "
                      "failed the last 2 round(s) — suspect the plan, not "
                      "the model, before spending this round",
                      payload.read_text(encoding="utf-8"))

    def test_tick_refuses_a_task_whose_fix_round_is_open(self):
        spec_dir = self.approved(
            (T1, T1.replace("[P]", "[P] (implemented) (fix 1/5)")))
        before = (spec_dir / "task.md").read_bytes()
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "tick.py"), str(spec_dir),
             "--note", "T001 :: pytest green"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("fix round 1 is open", r.stderr)
        self.assertEqual((spec_dir / "task.md").read_bytes(), before)

    def test_native_agents_payload_names_the_type_and_omits_the_brief(self):
        spec_dir = self.approved((T2, T2.replace("[P]", "[P] (implemented)")))
        brief_heading = "# Developer agent (implement lens)"
        self.emit(spec_dir)
        payload = next((spec_dir / "spawns").glob("*/implementer-T001.md"))
        embedded = payload.read_text(encoding="utf-8")
        self.assertIn(brief_heading, embedded)
        # a rule the brief already carries is not repeated by the protocol
        self.assertEqual(embedded.count("Long foreground tasks\n"), 1)
        # a first run names no model: only round 4's payload does
        self.assertNotIn("- Model:", embedded)

        r = self.emit(spec_dir, "--native-agents")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        native = payload.read_text(encoding="utf-8")
        self.assertNotIn(brief_heading, native)
        self.assertIn("agent type `spec-developer`", native)
        self.assertIn("- [ ] T001 [P] Implement multiply", native)
        self.assertIn("## Universal rules", native)

    def test_the_contract_review_is_not_emittable_from_this_package(self):
        spec_dir = self.approved()
        r = run_graph(spec_dir, "--emit-spawns", "--repair", "approve",
                      tel=self.tel)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("/spec-design", r.stderr)
        self.assertEqual(spawn_files(spec_dir), [])

    def test_fast_mode_hands_the_tiny_wave_to_the_session(self):
        spec_dir = self._tmp / "specs" / "tiny"
        spec_dir.mkdir(parents=True)
        write(spec_dir / "spec.md", TINY_SPEC.replace(
            "**Effort**: standard\n", "**Effort**: standard\n**Mode**: fast\n"))
        _approval.approve(spec_dir, self._tmp)
        r = self.emit(spec_dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(spawn_files(spec_dir), ["implementer-T001.md"])
        self.assertIn("mark.py claim", r.stdout)
        self.assertIn("spawn no developer", r.stdout)
        self.assertNotIn("before spawning them", r.stdout)

    def test_a_tiny_spec_needs_the_freeze_not_just_the_status_word(self):
        spec_dir = self._tmp / "specs" / "tiny"
        spec_dir.mkdir(parents=True)
        write(spec_dir / "spec.md", TINY_SPEC)
        r = self.emit(spec_dir)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("approve", refusal_gates(r.stdout))

        _approval.approve(spec_dir, self._tmp)
        r = self.emit(spec_dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        payload = next((spec_dir / "spawns").glob("*/implementer-T001.md"))
        self.assertIn("- [ ] T001 add the greeting module",
                      payload.read_text(encoding="utf-8"))

        # the in-file status markers move freely; the contract does not
        p = spec_dir / "spec.md"
        write(p, p.read_text(encoding="utf-8").replace(
            "- [ ] T001 add", "- [ ] T001 (in-progress) add"))
        self.assertEqual(run_check(spec_dir), 0)
        write(p, p.read_text(encoding="utf-8").replace(
            "- [ ] T001 (in-progress) add the greeting module (FR-001) [P]",
            "- [x] T001 add the greeting module (FR-001) [P] (fixed 1/5)\n"
            "  - done 2026-10-11 \u2014 greeting test green"))
        self.assertEqual(run_check(spec_dir), 0)
        write(p, p.read_text(encoding="utf-8").replace(
            "  - done 2026-10-11",
            "  - fix 1 \u2014 BLOCK: the error branch has no test\n"
            "  - fixed 1 \u2014 added the case \u2014 suite green\n"
            "  - done 2026-10-11"))
        self.assertEqual(run_check(spec_dir), 0)
        frozen = p.read_text(encoding="utf-8")
        write(p, frozen.replace(
            "\n## Evidence",
            "- [ ] T002 add a farewell (FR-001) [P]\n"
            "  - Touches: `src/bye.py`\n\n## Evidence"))
        self.assertEqual(run_check(spec_dir), 1)
        write(p, frozen.replace("greet the named user", "greet everyone"))
        self.assertEqual(run_check(spec_dir), 1)


class Gate007CustomRunnerHonestStopTests(unittest.TestCase):
    """The custom-runner contract as it reads after the D-041 headless
    lift: in THIS package a custom runner drives execute waves (Gate009
    pins the claim/land/stop behavior end to end; Gate009's no-mark test
    pins the exit-2 refusal where mark.py does not ship, and spec-design's
    Exec009 pins the honest unchanged-state stop on a doc wave). What
    stays pinned here: the print runner still drives a wave for the
    orchestrator to spawn, untouched by the lift."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="gate007-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def test_print_runner_still_drives_the_wave(self):
        spec_dir = copy_fixture(self._tmp / "p")
        set_status(spec_dir, "approved")
        r = run_graph(spec_dir, "--span", "execute", "--run", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count("runner[print]: implementer:"), 2)


class Gate008DigestFileTests(unittest.TestCase):
    """Write-capable payloads carry the digest-file block with a per-wave
    path (D-040); the read-only reviewer's payload never does."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="gate008-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def test_developer_payload_names_its_digest_file(self):
        spec_dir = copy_fixture(self._tmp)
        set_status(spec_dir, "approved")
        r = run_graph(spec_dir, "--span", "execute", "--emit-spawns",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        payload = next((spec_dir / "spawns").glob(
            "*/implementer-T001.md")).read_text(encoding="utf-8")
        self.assertIn("## Digest file", payload)
        self.assertRegex(payload, r"digests/wave-\d+/implementer-T001\.md")
        self.assertIn("as your final action", " ".join(payload.split()))

    def test_reviewer_payload_carries_no_digest_block(self):
        spec_dir = copy_fixture(self._tmp)
        set_status(spec_dir, "approved")
        land_all_tasks(spec_dir)
        r = run_graph(spec_dir, "--span", "execute", "--emit-spawns",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        payload = next((spec_dir / "spawns").glob(
            "*/reviewer-diff.md")).read_text(encoding="utf-8")
        self.assertNotIn("## Digest file", payload)

    def test_digest_capable_covers_the_write_roles_only(self):
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "graph_gate008", SCRIPTS / "graph.py")
        graph = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(graph)
        for brief in ("developer.md", "analyst.md", "architect.md",
                      "tester.md"):
            self.assertTrue(graph.digest_capable({"brief": brief}), brief)
        for brief in ("auditor.md", "integrator.md", "release-manager.md"):
            self.assertFalse(graph.digest_capable({"brief": brief}), brief)
        # the merged designer carries the architect brief
        self.assertTrue(graph.digest_capable({"briefs": ["architect.md"]}))


def write_headless_runner(tmp: Path, blocked: bool) -> str:
    """The headless 'developer': read the payload it was handed,
    write its digest file (blocked or implemented), and leave a
    marker file proving it ran. Its TCs are deterministic one-liners,
    so the scoped proofs land green once the digest is in."""
    if blocked:
        body = ("digest = (f'digest: task {tid} · status blocked: "
                "cannot reach the module · files 0 · commit-line "
                "none · deviation none · note none')\n")
    else:
        body = ("(spec_dir.parent / f'.built-{tid}').write_text('ok')\n"
                "digest = (f'digest: task {tid} · status implemented "
                "· files 1 · commit-line feat: T### · deviation "
                "none · note none')\n")
    path = tmp / f"runner{'-blocked' if blocked else ''}.py"
    write(path, 'import re, sys\n'
          'from pathlib import Path\n'
          'prompt = Path(sys.argv[1]).read_text(encoding="utf-8")\n'
          'spec_dir = Path(re.search(r"- spec_dir: (.+)", prompt)'
          '.group(1).strip())\n'
          'm = re.search(r"implementer-(T\\d{3})", prompt)\n'
          'tid = m.group(1) if m else "T000"\n'
          'wave = re.search(r"wave (\\d+)", prompt)\n'
          'digests = spec_dir / "digests" / f"wave-{wave.group(1) if wave else 1}"\n'
          'digests.mkdir(parents=True, exist_ok=True)\n'
          + body +
          '(digests / f"implementer-{tid}.md")'
          '.write_text("tools: Read, Grep, Glob, Bash, Write, Edit\\n" + digest + "\\n")\n')
    return f"{sys.executable} {path} {{prompt_file}}"


class Gate009HeadlessExecuteTests(unittest.TestCase):
    """The headless lift (D-041): where mark.py ships beside graph.py, a
    custom --runner drives execute waves end to end — mark.py claims,
    the runner runs (batched --parallel), mark.py lands each task whose
    digest reports implemented, and the loop parks at the tick-commit
    HUMAN gate. A blocked digest leaves the task CLAIMED and stops
    AWAITING ORCHESTRATOR. The tick-commit gate is never auto-satisfied."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="gate009-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = hand_docset(self._tmp / "specs" / "a", "approved")
        # the runners write their marker beside the spec dir
        self.repo = self.spec.parent
        self.runner = self._write_runner(blocked=False)

    def _write_runner(self, blocked: bool) -> str:
        return write_headless_runner(self._tmp, blocked)

    def test_headless_run_lands_both_tasks_and_parks_at_tick_commit(self):
        r = run_graph(self.spec, "--span", "execute", "--run",
                      "--runner", self.runner, "--parallel", "2",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("mark.py claim", r.stdout)
        self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        # the runner ran for both tasks, each landed, stamps removed
        for tid in ("T001", "T002"):
            self.assertTrue((self.repo / f".built-{tid}").is_file(),
                            r.stdout)
        t = (self.spec / "task.md").read_text(encoding="utf-8")
        self.assertEqual(t.count("(implemented)"), 2, t)
        self.assertNotIn("(in-progress)", t)
        self.assertNotIn("claimed ", t)
        # execute reads done; the gate stays the user's
        s = json.loads(run_graph(self.spec, "--state-json",
                                 tel=self.tel).stdout)
        self.assertEqual(s["nodes"]["execute"]["state"], "done")
        self.assertEqual(s["nodes"]["tick-commit"]["state"], "READY")
        self.assertNotIn("ticked", t)  # tick.py is still the only ticker

    def test_a_blocked_digest_leaves_the_task_claimed(self):
        blocked_runner = self._write_runner(blocked=True)
        r = run_graph(self.spec, "--span", "execute", "--run",
                      "--runner", blocked_runner, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AWAITING ORCHESTRATOR: execute", r.stdout)
        self.assertIn("held: T001", r.stdout)
        self.assertIn("blocked", r.stdout + r.stderr)
        t = (self.spec / "task.md").read_text(encoding="utf-8")
        self.assertIn("(in-progress)", t)
        self.assertIn("claimed ", t)  # the stamp survives: still claimed
        self.assertNotIn("(implemented)", t)

    def test_a_failing_runner_leaves_the_wave_claimed(self):
        r = run_graph(self.spec, "--span", "execute", "--run",
                      "--runner", "false", tel=self.tel)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("stay CLAIMED", r.stdout)
        t = (self.spec / "task.md").read_text(encoding="utf-8")
        self.assertIn("(in-progress)", t)

    def test_the_round_that_steps_the_model_needs_a_runner_naming_it(self):
        # fix round 4 is the round that runs one model step above the
        # developer brief's model: a runner that cannot name the model
        # would spend it on the same one, so nothing is claimed
        spec = hand_docset(self._tmp / "fix4", "approved")
        edit_tasks(spec, ("- [ ] T001 implement",
                          "- [ ] T001 (fix 4/5) implement"))
        runner = self._write_runner(blocked=False)
        r = run_graph(spec, "--span", "execute", "--run",
                      "--runner", runner, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AWAITING ORCHESTRATOR: execute: the --runner template "
                      "names no {model} — T001 is at fix round 4", r.stdout)
        self.assertIn("held: T001 — fix round 4/5 open", r.stdout)
        self.assertNotIn("(in-progress)", (spec / "task.md").read_text(
            encoding="utf-8"))
        ledger = spec / "runs" / "ledger.jsonl"
        self.assertNotIn('"claim"', ledger.read_text(encoding="utf-8"))
        self.assertFalse((spec.parent / ".built-T001").exists())

        # with {model} the runner is handed the step to resolve: the
        # brief's model, one step up — the round is no longer silent
        stepping = hand_docset(self._tmp / "stepping", "approved")
        edit_tasks(stepping, ("- [ ] T001 implement",
                              "- [ ] T001 (fix 4/5) implement"))
        models = self._tmp / "models.txt"
        r = run_graph(stepping, "--span", "execute", "--run", "--runner",
                      f"echo '{{model}}' >> {models} && {runner}",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(models.read_text(encoding="utf-8").split(),
                         ["sonnet+1"], r.stdout + r.stderr)

        # every other round takes the brief's own model
        first = hand_docset(self._tmp / "first", "approved")
        models.unlink()
        r = run_graph(first, "--span", "execute", "--run", "--runner",
                      f"echo '{{model}}' >> {models} && {runner}",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        self.assertEqual(models.read_text(encoding="utf-8").split(),
                         ["sonnet", "sonnet"], r.stdout + r.stderr)

    def test_a_fix_round_lands_from_a_headless_wave(self):
        # nobody is there to write a --resolution: the landing closes the
        # round citing the digest file it validated
        spec = hand_docset(self._tmp / "fix2", "approved")
        edit_tasks(spec, ("- [ ] T001 implement",
                          "- [ ] T001 (fix 2/5) implement\n"
                          "  - fix 2 \u2014 E   AssertionError: shout('hi') "
                          "== 'hi'"))
        r = run_graph(spec, "--span", "execute", "--run",
                      "--runner", self._write_runner(blocked=False),
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented) (round 2 closed)", r.stdout)
        self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        tasks = (spec / "task.md").read_text(encoding="utf-8")
        self.assertIn("(implemented) (fixed 2/5)", tasks)
        self.assertIn("\u2014 headless round 2: digest digests/", tasks)

    def test_a_package_without_mark_py_still_refuses(self):
        # the lift is scoped to packages that ship mark.py: a package
        # with the same graph.py but no scripts/mark.py keeps the D-038
        # refusal — execute payloads are writable only through the one
        # marker writer
        pkg = self._tmp / "nomark"
        (pkg / "scripts").mkdir(parents=True)
        (pkg / "agents").mkdir()
        (pkg / "protocol").mkdir()
        shutil.copy(SCRIPTS / "graph.py", pkg / "scripts" / "graph.py")
        for name in ("check.py", "specstate.py", "digests.py", "freeze.py",
                     "telemetry.py", "contract.py", "index.py"):
            shutil.copy(SCRIPTS / name, pkg / "scripts" / name)
        shutil.copy(SKILL / "agents" / "developer.md",
                    pkg / "agents" / "developer.md")
        shutil.copy(SKILL / "protocol" / "shared-protocol.md",
                    pkg / "protocol" / "shared-protocol.md")
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.tel),
                   KIT_TELEMETRY="on")
        r = subprocess.run(
            [sys.executable, str(pkg / "scripts" / "graph.py"),
             str(self.spec), "--span", "execute", "--run",
             "--runner", self.runner],
            capture_output=True, text=True, timeout=300, env=env)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("execute payloads need the orchestrator", r.stdout)
        # nothing ran: the wave was refused before any subprocess
        self.assertFalse(any(self.repo.glob(".built-*")), r.stdout)


class Gate005LifecycleCommandSurfaceTests(unittest.TestCase):
    """One command per skill (D-033): spec-build.md is this package's
    single command, every lifecycle verb rides it, and extra.txt claims
    exactly its name. Install-level behavior is tested elsewhere."""

    def test_exactly_one_command_and_it_is_the_router(self):
        cmds = sorted(p.name for p in COMMANDS.glob("*.md"))
        self.assertEqual(cmds, [ROUTER_COMMAND])
        text = (COMMANDS / ROUTER_COMMAND).read_text(encoding="utf-8")
        self.assertGreater(len(text.strip()), 100)
        self.assertIn("skills: spec-build", text)
        self.assertIn("--span execute", text)

    def test_every_lifecycle_verb_rides_the_router(self):
        text = (COMMANDS / ROUTER_COMMAND).read_text(encoding="utf-8")
        for verb in LIFECYCLE_VERBS:
            self.assertIn(f"`{verb} <spec>", text, verb)

    def test_extra_txt_claims_every_bare_name_exactly_once(self):
        text = (COMMANDS / "extra.txt").read_text(encoding="utf-8")
        names = text.split()
        self.assertEqual(names, CLAIMED_BARE_NAMES)
        self.assertEqual(len(names), len(set(names)))

    def test_the_retired_monolith_is_gone_so_no_second_claimant_exists(self):
        # exactly one claimant per bare name: the old monolith must not ship
        self.assertFalse((SKILL.parent / "spec-to-prod").exists(),
                         "the retired monolith must not ship")


HAND_DIGEST = ("tools: Read, Grep, Glob, Bash, Write, Edit\n"
               "digest: task T001 · status implemented · files 1 · "
               "commit-line feat: T001 · deviation none · note none\n")
HAND_REPORTED = "Bash, Edit, Glob, Grep, Read, Write"


def facts(row: dict) -> dict:
    """A ledger row without its timestamp and chain field — the literal
    a test compares."""
    return {k: v for k, v in row.items() if k not in ("ts", "prev")}


def provenance_section(text: str) -> str:
    """retro.md's provenance section: from its heading to the next one."""
    return text.split("## Provenance (run ledger — kept at archive)\n\n",
                      1)[1].split("\n## ", 1)[0].rstrip("\n")


class Gate011RunLedgerTests(unittest.TestCase):
    """The run ledger (D-055): specs/<name>/runs/ledger.jsonl, one row
    per orchestrator event. Every emitted payload is a `wave` row with
    the request's facts (role, lens, payload sha, docset fingerprint,
    the brief's model, the --harness name); a --run opens and closes
    the ledger with its stop reason; the headless wave's claims,
    digests and landings join the same rows. Every graph.py invocation
    that touches the spec sweeps digests/ first: a valid digest file
    gains the one provenance line a ledger row vouches for; a malformed
    one, or one no `wave` or `claim` row records, is left as it is and
    named."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="gate011-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = hand_docset(self._tmp / "specs" / "a", "approved")
        self.ledger = self.spec / "runs" / "ledger.jsonl"

    def rows(self) -> list[dict]:
        if not self.ledger.is_file():
            return []
        return [json.loads(ln) for ln in
                self.ledger.read_text(encoding="utf-8").splitlines()]

    def digest_at(self, spec: Path, wave: int, text: str) -> Path:
        path = spec / "digests" / f"wave-{wave}" / "implementer-T001.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        write(path, text)
        return path

    def test_emit_writes_one_wave_row_per_payload_with_the_requests_facts(self):
        fingerprint = freeze.docset_fingerprint(self.spec)
        r = run_graph(self.spec, "--span", "execute", "--emit-spawns",
                      "--run-id", "r-1a2b", "--harness", "zcode",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # the printed claim command carries the harness on to the claims
        self.assertIn(f"--run-id r-1a2b --harness zcode", r.stdout)
        rows = self.rows()
        # T002 depends on T001, so the wave holds one payload; the hand
        # docset's waves all sit at 4 (authoring done, nothing ticked)
        self.assertEqual([row["event"] for row in rows], ["wave"])
        payload = self.spec / "spawns" / "wave-4" / "implementer-T001.md"
        self.assertEqual(facts(rows[0]), {
            "skill": "spec-build", "event": "wave", "run": "r-1a2b",
            "wave": 4, "node": "execute", "role": "implementer",
            "lens": "build", "stem": "implementer-T001",
            "payload": hashlib.sha256(payload.read_bytes()).hexdigest()[:12],
            "input": fingerprint, "model": "sonnet", "harness": "zcode"})

    def test_a_run_opens_and_closes_the_ledger_with_its_stop_reason(self):
        r = run_graph(self.spec, "--span", "execute", "--run",
                      "--run-id", "r-7q", "--harness", "zcode",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = self.rows()
        self.assertEqual([row["event"] for row in rows],
                         ["run_start", "wave", "run_end"])
        self.assertEqual(facts(rows[0]), {
            "skill": "spec-build", "event": "run_start", "run": "r-7q",
            "harness": "zcode"})
        self.assertEqual(facts(rows[-1]), {
            "skill": "spec-build", "event": "run_end", "run": "r-7q",
            "harness": "zcode", "outcome": "wave_emitted"})

        # a landed docset parks at the human gate: the row names it
        landed = hand_docset(self._tmp / "specs" / "b", "approved")
        land_hand_tasks(landed)
        r = run_graph(landed, "--run", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        end = json.loads((landed / "runs" / "ledger.jsonl").read_text(
            encoding="utf-8").splitlines()[-1])
        self.assertEqual(facts(end), {
            "skill": "spec-build", "event": "run_end", "harness": "unknown",
            "node": "tick-commit", "outcome": "gate_pause"})

        # --harness belongs to the two executor modes only
        r = run_graph(self.spec, "--harness", "zcode", tel=self.tel)
        self.assertEqual(r.returncode, 2)

    def test_a_headless_run_leaves_the_whole_story_in_the_ledger(self):
        runner = write_headless_runner(self._tmp, blocked=False)
        r = run_graph(self.spec, "--span", "execute", "--run",
                      "--runner", runner, "--parallel", "2",
                      "--run-id", "r-head", "--harness", "zcode",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = self.rows()
        # T002 follows T001: one wave lands T001, the next lands T002 (the
        # same wave number — nothing is ticked) — each task's claim,
        # digest and land join its own wave row
        self.assertEqual([row["event"] for row in rows], [
            "run_start", "wave", "claim", "digest", "land", "wave",
            "claim", "digest", "land", "run_end"])
        self.assertEqual(facts(rows[-1]), {
            "skill": "spec-build", "event": "run_end", "run": "r-head",
            "node": "tick-commit", "harness": "zcode",
            "outcome": "gate_pause"})
        for tid in ("T001", "T002"):
            own = [row for row in rows if row.get("task") == tid]
            self.assertEqual([row["event"] for row in own],
                             ["claim", "digest", "land"])
            claim, digest, land = own
            wave = next(row for row in rows if row["event"] == "wave"
                        and row["stem"] == f"implementer-{tid}")
            self.assertEqual(wave["wave"], 4)
            self.assertEqual(claim["payload"], wave["payload"])
            for row in (claim, digest):
                self.assertEqual(
                    (row["run"], row["payload"], row["model"],
                     row["harness"]),
                    ("r-head", wave["payload"], "sonnet", "zcode"))
            self.assertEqual(
                (land["digest"], land["outcome"], land["run"]),
                (digest["digest"], "implemented", "r-head"))
            text = (self.spec / "digests" / "wave-4"
                    / f"implementer-{tid}.md").read_text(encoding="utf-8")
            self.assertEqual(text.count("provenance:"), 1)
            self.assertEqual(text.splitlines()[-1], (
                f"provenance: run r-head · role implementer · lens build · "
                f"model sonnet · harness zcode · payload {wave['payload']} · "
                f"input {wave['input']} · recorded {digest['ts']} · "
                f"tools-reported {HAND_REPORTED}"))

        section = provenance_section(
            retro.retro(self.spec, "handbuilt", self.spec.parent))
        self.assertEqual(section.splitlines()[-1],
                         "Ledger: 2 digest(s) recorded.")
        for tid in ("T001", "T002"):
            wave = next(row for row in rows if row["event"] == "wave"
                        and row["stem"] == f"implementer-{tid}")
            digest = next(row for row in rows if row["event"] == "digest"
                          and row.get("task") == tid)
            self.assertIn(
                f"| {tid} | 4 | r-head | implementer | build | sonnet "
                f"| zcode | {wave['payload']} | {wave['input']} | "
                f"{digest['digest']} | implemented |", section)

    def test_a_hand_written_digest_is_swept_before_every_read(self):
        # each mode that touches the spec sweeps first: a hand-written
        # file no ledger row records is refused — named on stderr, once
        # per content, given no provenance line. The sweep ran; it
        # vouches nothing for a digest nobody's emit or claim asked for
        modes = ([], ["--state-json"], ["--explain", "execute"],
                 ["--emit-spawns"], ["--run"])
        path = self.digest_at(self.spec, 7, HAND_DIGEST)
        refusal = (f"digest: unverified at {path} — it carries no "
                   "`provenance:` line and no ledger row records its "
                   "digest — nothing vouches its content — fix and run "
                   "again: re-spawn the same payload to rewrite its "
                   "digest file\n")
        for argv in modes:
            with self.subTest(argv=argv):
                r = run_graph(self.spec, *argv, tel=self.tel)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn(refusal, r.stderr)
        self.assertNotIn("provenance:", path.read_text(encoding="utf-8"))
        rows = [row for row in self.rows()
                if row["event"] == "digest_malformed"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["wave"], rows[0]["outcome"]),
                         (7, "unverified"))
        self.assertEqual(facts(rows[0]), {
            "skill": "spec-build", "event": "digest_malformed", "wave": 7,
            "task": "T001", "role": "implementer",
            "stem": "implementer-T001", "harness": "unknown",
            "digest": hashlib.sha256(HAND_DIGEST.encode())
            .hexdigest()[:12], "outcome": "unverified"})

        # a pure read and a refusal at the gate touch nothing
        idle = self.digest_at(self.spec, 3, HAND_DIGEST)
        r = run_graph(self.spec, "--launch-check", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(idle.read_text(encoding="utf-8"), HAND_DIGEST)
        draft = copy_fixture(self._tmp, "draft")
        refused = self.digest_at(draft, 1, HAND_DIGEST)
        r = run_graph(draft, "--span", "execute", "--emit-spawns",
                      tel=self.tel)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertEqual(refused.read_text(encoding="utf-8"), HAND_DIGEST)
        self.assertFalse((draft / "runs").exists())

    def test_the_sweep_leaves_a_malformed_file_untouched_and_names_it(self):
        broken = "digest: task T001 · status implemented · files 2 · note none\n"
        path = self.digest_at(self.spec, 2, broken)
        for _ in range(2):
            r = run_graph(self.spec, tel=self.tel)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(r.stderr, (
                f"digest: malformed at {path} — `commit-line` missing — fix "
                "and run again: re-spawn the same payload to rewrite its "
                "digest file\n"))
        self.assertEqual(path.read_text(encoding="utf-8"), broken)
        rows = self.rows()
        self.assertEqual([(row["event"], row["outcome"]) for row in rows],
                         [("digest_malformed", "malformed")])
        self.assertEqual(facts(rows[0]), {
            "skill": "spec-build", "event": "digest_malformed", "wave": 2,
            "task": "T001", "role": "implementer", "stem": "implementer-T001",
            "harness": "unknown",
            "digest": hashlib.sha256(broken.encode()).hexdigest()[:12],
            "outcome": "malformed"})

    def test_retro_folds_the_rows_and_counts_the_malformed(self):
        empty = hand_docset(self._tmp / "specs" / "empty", "approved")
        section = provenance_section(
            retro.retro(empty, "handbuilt", empty.parent))
        self.assertEqual(section, "None recorded.")
        lone = hand_docset(self._tmp / "specs" / "lone", "approved")
        (lone / "runs").mkdir()
        write(lone / "runs" / "ledger.jsonl", json.dumps({
            "ts": "2026-11-26T10:00:00.000000+00:00", "skill": "spec-build",
            "event": "digest_malformed", "wave": 3, "task": "T001",
            "role": "implementer", "stem": "implementer-T001",
            "harness": "unknown", "digest": "0f1e2d3c4b5a",
            "outcome": "malformed"}) + "\n")
        section = provenance_section(
            retro.retro(lone, "handbuilt", lone.parent))
        self.assertEqual(section.splitlines()[:3], [
            "| Task / stem | Wave | Run | Role | Lens | Model | Harness | "
            "Payload | Input | Digest | Outcome |",
            "|" + "---|" * 12,
            "Ledger: 0 digest(s) recorded, 1 malformed."])


if __name__ == "__main__":
    unittest.main(verbosity=2)
