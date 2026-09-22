"""Tests for scripts/graph.py — the frontier engine.

graph.py derives the workflow state from doc state alone (architecture §2):
16 nodes, each done/READY/blocked/gate:undetermined/SKIPPED with a reason,
a frontier wave of the READY nodes, loop-edge statuses, task counts, and a
git-availability line that degrades to `SKIPPED (not a git repo)` in this
deliberately non-git workspace. Fixtures are built exactly the way the
validation contract prescribes: scaffold.sh + minimal writes, and mutated
copies of examples/mini-spec (never the original). --state-json is the
authoritative oracle, so node-state assertions read the same dict the CLI
serializes; report/exit-code/JSON-shape assertions go through the real CLI
subprocess. Executor modes (--emit-spawns/--run) live in their own feature.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
GRAPH = SCRIPTS / "graph.py"
SCAFFOLD = SCRIPTS / "scaffold.sh"
FIXTURE = SKILL / "examples" / "mini-spec" / "specs" / "mini-spec"
FIXTURE_REPO = SKILL / "examples" / "mini-spec" / "repo"

_spec = importlib.util.spec_from_file_location("graph", GRAPH)
graph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(graph)


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def scaffold(tmp: Path, name: str = "demo") -> Path:
    r = subprocess.run(["bash", str(SCAFFOLD), name, str(tmp)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return tmp / "specs" / name


def copy_fixture(tmp: Path, name: str = "demo") -> Path:
    """A mutated-copy fixture: mini-spec docset + the repo it cites, so the
    survey's file:symbol:line evidence stays real under the tmp repo root."""
    (tmp / "specs").mkdir(parents=True, exist_ok=True)
    dst = tmp / "specs" / name
    shutil.copytree(FIXTURE, dst)
    shutil.copytree(FIXTURE_REPO, tmp / "repo")
    return dst


def spec_only(tmp: Path, name: str = "demo") -> Path:
    """GRAPH-001's fixture: a filled spec.md and nothing else."""
    d = scaffold(tmp, name)
    write(d / "spec.md", (FIXTURE / "spec.md").read_text(encoding="utf-8"))
    for f in ("survey.md", "research.md", "plan.md", "tech-spec.md",
              "task.md", "test.md"):
        (d / f).unlink()
    return d


def set_status(spec_dir: Path, word: str) -> None:
    p = spec_dir / "spec.md"
    write(p, p.read_text(encoding="utf-8").replace(
        "**Status**: draft", f"**Status**: {word}"))


APPROVED_TASKS = """# Tasks: demo

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ -

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1     | 3     | 0    |
| **Σ** | 3     | 0    |

## Phase 1: land the feature (FR-001, FR-002)
- [ ] T001 [P] implement multiply in `repo/calc.py` (FR-001)
- [ ] T002 (after T001) wire the caller `repo/test_calc.py` (FR-001)
- [ ] T003 (fix 5/5) rescue the stalled refactor (FR-002)

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done + proof note
- Every task cites its FR-###; tasks with no FR are scope creep
"""

TICKED_T1_TASKS = APPROVED_TASKS.replace(
    "- [ ] T001 [P] implement multiply in `repo/calc.py` (FR-001)",
    "- [x] T001 [P] implement multiply in `repo/calc.py` (FR-001)\n"
    "      done 2026-09-08 — python3 -m pytest repo/test_calc.py green",
).replace("| 1     | 3     | 0    |", "| 1     | 3     | 1    |").replace(
    "| **Σ** | 3     | 0    |", "| **Σ** | 3     | 1    |")

IMPLEMENTED_T1_TASKS = APPROVED_TASKS.replace(
    "- [ ] T001 [P] implement multiply in `repo/calc.py` (FR-001)",
    "- [ ] T001 [P] (implemented) implement multiply in `repo/calc.py` "
    "(FR-001)",
)

IMPLEMENTED_ALL_TASKS = APPROVED_TASKS.replace(
    "- [ ] T001 [P] implement multiply in `repo/calc.py` (FR-001)",
    "- [ ] T001 [P] (implemented) implement multiply in `repo/calc.py` "
    "(FR-001)",
).replace(
    "- [ ] T002 (after T001) wire the caller `repo/test_calc.py` (FR-001)",
    "- [ ] T002 (after T001) (implemented) wire the caller "
    "`repo/test_calc.py` (FR-001)",
).replace(
    "- [ ] T003 (fix 5/5) rescue the stalled refactor (FR-002)",
    "- [ ] T003 (fix 5/5) (implemented) rescue the stalled refactor "
    "(FR-002)",
)

MIXED_LANDED_TASKS = APPROVED_TASKS.replace(
    "- [ ] T001 [P] implement multiply in `repo/calc.py` (FR-001)",
    "- [x] T001 [P] implement multiply in `repo/calc.py` (FR-001)\n"
    "      done 2026-09-08 — python3 -m pytest repo/test_calc.py green",
).replace(
    "- [ ] T002 (after T001) wire the caller `repo/test_calc.py` (FR-001)",
    "- [ ] T002 (after T001) (implemented) wire the caller "
    "`repo/test_calc.py` (FR-001)",
).replace(
    "- [ ] T003 (fix 5/5) rescue the stalled refactor (FR-002)",
    "- [ ] ~~T003~~ (fix 5/5) rescue the stalled refactor (FR-002) — "
    "dropped",
).replace("| 1     | 3     | 0    |", "| 1     | 3     | 1    |").replace(
    "| **Σ** | 3     | 0    |", "| **Σ** | 3     | 1    |")

CLAIMED_T1_TASKS = APPROVED_TASKS.replace(
    "- [ ] T001 [P] implement multiply in `repo/calc.py` (FR-001)",
    "- [ ] T001 [P] (in-progress) implement multiply in `repo/calc.py` "
    "(FR-001)",
)

STRUCK_DEP_TASKS = """# Tasks: demo

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ -

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1     | 3     | 0    |
| **Σ** | 3     | 0    |

## Phase 1: land the feature (FR-001, FR-002)
- [ ] ~~T001~~ [P] implement multiply in `repo/calc.py` (FR-001) — dropped
- [ ] T002 (after T001) wire the caller `repo/test_calc.py` (FR-001)
- [ ] T003 (after T099) rescue the stalled refactor (FR-002)

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done + proof note
- Every task cites its FR-###; tasks with no FR are scope creep
"""

DONE_TASKS = """# Tasks: demo

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ -

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1     | 2     | 2    |
| **Σ** | 2     | 2    |

## Phase 1: multiply lands (FR-001, FR-002)
- [x] T001 [P] implement multiply in `repo/calc.py` (FR-001, FR-002)
      done 2026-09-08 — python3 -m pytest repo/test_calc.py green
- [x] T002 [P] add multiply tests to `repo/test_calc.py` (FR-001, FR-002)
      done 2026-09-08 — python3 -m pytest repo/test_calc.py green

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done + proof note
"""

GREEN_TC = 'python3 -c "print(\'proof ok\')"'


def green_test_md(spec_dir: Path) -> None:
    """Swap the fixture's real pytest TC pass conditions to always-green
    commands so the closing audit's DoD scorecard (audit.py dod) passes
    mechanically in the non-git tmp repo."""
    test = (FIXTURE / "test.md").read_text(encoding="utf-8")
    test = test.replace(
        "`cd repo && python3 -m pytest test_calc.py -k multiply` exits 0",
        f"`{GREEN_TC}` exits 0")
    test = test.replace(
        "`cd repo && python3 -m pytest test_calc.py -k zero` exits 0",
        f"`{GREEN_TC}` exits 0")
    write(spec_dir / "test.md", test)


def done_fixture(tmp: Path) -> Path:
    """All tasks ticked, Status: done, before-audit recorded, and TC pass
    conditions swapped to always-green commands so the closing audit's DoD
    scorecard (audit.py dod) passes mechanically in the non-git tmp repo."""
    d = copy_fixture(tmp)
    set_status(d, "done")
    write(d / "task.md", DONE_TASKS)
    green_test_md(d)
    return d


def compute(spec_dir, repo=None):
    return graph.compute_state(Path(spec_dir), repo)


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(GRAPH), *[str(a) for a in args]],
        capture_output=True, text=True, timeout=300)


def frontier_of(state):
    return state["frontier"]


def dir_checksum(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


class Graph001EmptyScaffoldTests(unittest.TestCase):
    """GRAPH-001: filled spec.md only — survey READY, gate undetermined,
    everything downstream blocked, frontier = [survey]."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph001-"))
        cls.spec_dir = spec_only(cls._tmp)
        cls.state = compute(cls.spec_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_frontier_is_survey_only(self):
        self.assertEqual(frontier_of(self.state), ["survey"])

    def test_node_states_match_the_contract(self):
        n = self.state["nodes"]
        self.assertEqual(n["spec"]["state"], "done")
        self.assertEqual(n["clarify"]["state"], "done")
        self.assertEqual(n["research-gate"]["state"], "gate:undetermined")
        self.assertEqual(n["research"]["state"], "blocked")
        self.assertEqual(n["survey"]["state"], "READY")
        for name in ("plan", "tech", "qa", "tasks", "verify", "before-audit",
                     "approve", "execute"):
            self.assertEqual(n[name]["state"], "blocked", name)

    def test_blocked_reasons_name_the_unmet_predecessor(self):
        n = self.state["nodes"]
        self.assertIn("survey", n["plan"]["reason"])
        self.assertIn("survey", n["qa"]["reason"])
        self.assertIn("survey", n["tech"]["reason"])
        # tech alone also demands the research resolution (§2.1).
        self.assertIn("research", n["tech"]["reason"])
        self.assertIn("plan", n["tasks"]["reason"])
        self.assertIn("verify", n["before-audit"]["reason"])
        self.assertIn("before-audit", n["approve"]["reason"])

    def test_default_report_and_gate_pause(self):
        r = run_cli(self.spec_dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("gate:undetermined", r.stdout)
        self.assertIn("survey", r.stdout)
        self.assertEqual(frontier_of(compute(self.spec_dir)), ["survey"])


class Graph002SurveyWaveTests(unittest.TestCase):
    """GRAPH-002: a valid survey flips survey done; plan ∥ qa go READY while
    tech stays blocked on the undetermined gate; real research unblocks tech."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph002-"))
        cls.spec_dir = scaffold(cls._tmp)
        write(cls.spec_dir / "spec.md",
              (FIXTURE / "spec.md").read_text(encoding="utf-8"))
        write(cls.spec_dir / "survey.md",
              (FIXTURE / "survey.md").read_text(encoding="utf-8"))
        # the scaffold ships research.md as the resolved skip marker (D-025)
        # — restore the unfilled template so `before` tests the
        # gate:undetermined state this class exists for
        write(cls.spec_dir / "research.md",
              (SKILL / "templates" / "research.md").read_text(
                  encoding="utf-8"))
        cls.before = compute(cls.spec_dir)
        write(cls.spec_dir / "research.md",
              "## Research: demo\n\n### Q1 how to name the operation\n"
              "- **source**: https://example.com/naming — claim: plain names\n"
              "  relevance: direct · confidence: high\n")
        cls.after = compute(cls.spec_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_survey_done_plan_qa_ready_tech_blocked(self):
        n = self.before["nodes"]
        self.assertEqual(n["survey"]["state"], "done")
        self.assertEqual(n["plan"]["state"], "READY")
        self.assertEqual(n["qa"]["state"], "READY")
        self.assertEqual(n["tech"]["state"], "blocked")
        self.assertIn("research", n["tech"]["reason"])
        self.assertEqual(sorted(frontier_of(self.before)), ["plan", "qa"])

    def test_real_research_unblocks_tech(self):
        n = self.after["nodes"]
        self.assertEqual(n["research"]["state"], "done")
        self.assertEqual(n["research-gate"]["state"], "done")
        self.assertIn("run", n["research-gate"]["reason"])
        self.assertEqual(n["tech"]["state"], "READY")
        self.assertEqual(sorted(frontier_of(self.after)),
                         ["plan", "qa", "tech"])


class Graph003SkipMarkerTests(unittest.TestCase):
    """GRAPH-003: the canonical em-dash skip marker resolves the gate as
    skip — research reads SKIPPED (not blocked), tech goes READY."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph003-"))
        cls.spec_dir = scaffold(cls._tmp)
        write(cls.spec_dir / "spec.md",
              (FIXTURE / "spec.md").read_text(encoding="utf-8"))
        write(cls.spec_dir / "survey.md",
              (FIXTURE / "survey.md").read_text(encoding="utf-8"))
        write(cls.spec_dir / "research.md",
              "# Research: demo\n\nnot applicable — no open questions at Stage 0\n")
        cls.state = compute(cls.spec_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_research_is_skipped_not_blocked(self):
        n = self.state["nodes"]
        self.assertEqual(n["research"]["state"], "SKIPPED")
        self.assertEqual(n["research-gate"]["state"], "done")
        self.assertIn("skip", n["research-gate"]["reason"])
        self.assertEqual(n["tech"]["state"], "READY")
        self.assertEqual(sorted(frontier_of(self.state)),
                         ["plan", "qa", "tech"])


class Graph004ExecuteFrontierTests(unittest.TestCase):
    """GRAPH-004: per-task readiness — deps chain (T002 after T001), fix-cap
    (T003 at 5/5) surfaced for adjudication, ticking T1 unblocks T2."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph004-"))
        cls.spec_dir = copy_fixture(cls._tmp)
        set_status(cls.spec_dir, "approved")
        write(cls.spec_dir / "task.md", APPROVED_TASKS)
        cls.state = compute(cls.spec_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def tasks(self, state):
        return {t["id"]: t for t in state["nodes"]["execute"]["tasks"]}

    def test_execute_ready_with_per_task_frontier(self):
        n = self.state["nodes"]
        self.assertEqual(n["approve"]["state"], "done")
        self.assertEqual(n["execute"]["state"], "READY")
        self.assertEqual(frontier_of(self.state), ["execute"])

    def test_runnable_blocked_and_cap_states(self):
        t = self.tasks(self.state)
        self.assertEqual(t["T001"]["state"], "runnable")
        self.assertEqual(t["T002"]["state"], "blocked")
        self.assertIn("T001", t["T002"]["reason"])
        self.assertEqual(t["T003"]["state"], "at-fix-cap")
        self.assertIn("5/5", t["T003"]["reason"])

    def test_cap_task_is_not_runnable_and_counted(self):
        self.assertEqual(self.state["counts"]["at-fix-cap"], 1)
        self.assertEqual(self.state["counts"]["todo"], 3)

    def test_ticking_t1_unblocks_t2(self):
        write(self.spec_dir / "task.md", TICKED_T1_TASKS)
        state = compute(self.spec_dir)
        t = self.tasks(state)
        self.assertEqual(t["T002"]["state"], "runnable")
        self.assertEqual(t["T001"]["state"], "ticked")
        self.assertEqual(state["counts"]["ticked"], 1)
        self.assertEqual(state["counts"]["todo"], 2)

    def test_directory_and_glob_overlap_surfaces_wave_note(self):
        tasks = """# Tasks

## Phase 1
- [ ] T001 [P] first (FR-001)
  - Touches:
    - `src/module/`
- [ ] T002 [P] second (FR-001)
  - Touches:
    - `src/*.py`
"""
        ts = {t["id"]: t for t in graph.task_frontier(
            graph.specstate.task_entries(tasks))}
        self.assertIn("T002", ts["T001"]["note"])


class LifecycleEvidenceIntegrityTests(unittest.TestCase):
    def test_fabricated_lifecycle_shas_block_verify(self):
        with tempfile.TemporaryDirectory() as td:
            spec = copy_fixture(Path(td))
            set_status(spec, "done")
            task = DONE_TASKS.replace(
                "**Before-audit**: passed @ -",
                "**Before-audit**: passed @ deadbeef\n"
                "**Closing-audit**: approved @ deadbeef\n"
                "**Delivered**: commit @ deadbeef",
            )
            write(spec / "task.md", task)
            node = compute(spec)["nodes"]["verify"]
            self.assertEqual(node["state"], "blocked")
            self.assertIn("check.py exits 1", node["reason"])


class StruckDepFrontierTests(unittest.TestCase):
    """Scrutiny round-1 finding 1: the canonical dropped form
    `- [ ] ~~T###~~ …` parses id=None, but a struck dep still counts as
    satisfied (architecture §2.1) — a dependent of a struck task is
    runnable, and only a dep matching no entry at all reads 'not defined'."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graphstruck-"))
        cls.spec_dir = copy_fixture(cls._tmp)
        set_status(cls.spec_dir, "approved")
        write(cls.spec_dir / "task.md", STRUCK_DEP_TASKS)
        cls.state = compute(cls.spec_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_dependent_of_struck_task_is_runnable(self):
        ts = self.state["nodes"]["execute"]["tasks"]
        struck = [t for t in ts if t["state"] == "struck"]
        self.assertEqual(len(struck), 1)
        # The parser pins the root cause: the struck entry carries id=None.
        self.assertIsNone(struck[0]["id"])
        by_id = {t["id"]: t for t in ts if t["id"]}
        self.assertEqual(by_id["T002"]["state"], "runnable")
        self.assertIn("deps satisfied", by_id["T002"]["reason"])

    def test_undefined_dep_keeps_distinct_reason(self):
        ts = self.state["nodes"]["execute"]["tasks"]
        by_id = {t["id"]: t for t in ts if t["id"]}
        self.assertEqual(by_id["T003"]["state"], "blocked")
        self.assertIn("dependency not defined in task.md: T099",
                      by_id["T003"]["reason"])

    def test_struck_counted_and_execute_ready(self):
        self.assertEqual(self.state["counts"]["struck"], 1)
        self.assertEqual(frontier_of(self.state), ["execute"])


class ImplementedDepFrontierTests(unittest.TestCase):
    """FR-002: an `(after T###)` dependency is satisfied by a landed
    upstream — `(implemented)` (unticked) releases its dependent the same
    way a ticked or struck one does, while a merely claimed (in-progress)
    upstream still blocks. Landing is not ticking: the release happens
    with counts.ticked at zero."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graphimpl-"))
        cls.impl_dir = copy_fixture(cls._tmp / "impl")
        set_status(cls.impl_dir, "approved")
        write(cls.impl_dir / "task.md", IMPLEMENTED_T1_TASKS)
        cls.impl_state = compute(cls.impl_dir)
        cls.claimed_dir = copy_fixture(cls._tmp / "claimed")
        set_status(cls.claimed_dir, "approved")
        write(cls.claimed_dir / "task.md", CLAIMED_T1_TASKS)
        cls.claimed_state = compute(cls.claimed_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def tasks(self, state):
        return {t["id"]: t for t in state["nodes"]["execute"]["tasks"]}

    def test_implemented_dependency_releases_dependent(self):
        t = self.tasks(self.impl_state)
        self.assertEqual(t["T002"]["state"], "runnable")
        self.assertIn("deps satisfied", t["T002"]["reason"])

    def test_landing_is_not_ticking(self):
        t = self.tasks(self.impl_state)
        self.assertNotEqual(t["T001"]["state"], "ticked")
        self.assertEqual(self.impl_state["counts"]["ticked"], 0)

    def test_claimed_dependency_still_blocks(self):
        t = self.tasks(self.claimed_state)
        self.assertEqual(t["T001"]["state"], "claimed")
        self.assertEqual(t["T002"]["state"], "blocked")
        self.assertIn("waiting on T001", t["T002"]["reason"])


class ImplementedExecuteCompletionTests(unittest.TestCase):
    """TC-003 (FR-003/AC1): when every non-dropped task is `(implemented)`
    (unticked), execute is done and closing-audit is the next transition.
    An implemented entry is its own per-task state — never re-spawned as
    runnable — and counts separately from todo; mixed landing (ticked +
    implemented + struck) completes execute too. Past execute the graph
    holds at the inert closing-audit human gate (FR-004): test.md is
    classified, never executed, so tick-commit stays blocked on it."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graphimpl3-"))
        cls.impl_dir = implemented_fixture(cls._tmp / "impl")
        cls.impl_state = compute(cls.impl_dir)
        cls.mixed_dir = copy_fixture(cls._tmp / "mixed")
        set_status(cls.mixed_dir, "approved")
        write(cls.mixed_dir / "task.md", MIXED_LANDED_TASKS)
        cls.mixed_state = compute(cls.mixed_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def tasks(self, state):
        return {t["id"]: t for t in state["nodes"]["execute"]["tasks"]}

    def test_execute_done_without_any_tick(self):
        n = self.impl_state["nodes"]
        self.assertEqual(n["execute"]["state"], "done")
        self.assertIn("implemented", n["execute"]["reason"])

    def test_implemented_tasks_are_their_own_state(self):
        t = self.tasks(self.impl_state)
        for tid in ("T001", "T002", "T003"):
            self.assertEqual(t[tid]["state"], "implemented", tid)
        self.assertNotIn(t["T003"]["state"], ("runnable", "at-fix-cap"),
                         "landed work is neither re-spawned nor adjudicated")

    def test_counts_carry_implemented_separately_from_todo(self):
        c = self.impl_state["counts"]
        self.assertEqual(c["implemented"], 3)
        self.assertEqual(c["todo"], 0)
        self.assertEqual(c["ticked"], 0)
        self.assertEqual(c["claimed"], 0)

    def test_closing_audit_is_the_next_transition(self):
        pause = graph.find_pause(self.impl_state)
        self.assertIsNotNone(pause)
        self.assertEqual(pause[0], "closing-audit")
        r = run_cli(self.impl_dir, "--run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("AWAITING HUMAN: closing-audit", r.stdout)
        self.assertNotIn("implementer", r.stdout)

    def test_implemented_tasks_are_not_respawned(self):
        r = run_cli(self.impl_dir, "--emit-spawns")
        self.assertEqual(r.returncode, 0, r.stderr)
        # no implementer payload (landed tasks are never re-spawned); the
        # one payload prepared at execute-done is the closing reviewer's
        # (D-023) — never an implementer
        self.assertNotIn("implementer", r.stdout)
        self.assertIn("reviewer-diff.md", r.stdout)

    def test_mixed_landing_completes_execute(self):
        n = self.mixed_state["nodes"]
        self.assertEqual(n["execute"]["state"], "done")
        c = self.mixed_state["counts"]
        self.assertEqual((c["ticked"], c["implemented"], c["struck"]),
                         (1, 1, 1))
        self.assertEqual(c["todo"], 0)

    def test_closing_audit_is_the_inert_human_gate(self):
        n = self.impl_state["nodes"]
        self.assertEqual(n["closing-audit"]["state"], "READY")
        self.assertIn("HUMAN GATE", n["closing-audit"]["reason"])
        self.assertIn("not executed", n["closing-audit"]["reason"])
        self.assertEqual(n["tick-commit"]["state"], "blocked")
        self.assertIn("closing-audit", n["tick-commit"]["reason"])


class Graph005LifecycleTests(unittest.TestCase):
    """GRAPH-005: draft → approve is the frontier's human gate; approved →
    execute eligible; done status with every task ticked still holds at the
    inert closing-audit human gate (FR-004) — recorded approval (FR-005),
    not a dod-green docset, is what opens tick-commit. The lifecycle Status
    shows in report and JSON throughout."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph005-"))
        cls.draft = copy_fixture(cls._tmp / "a")
        write(cls.draft / "task.md", APPROVED_TASKS.replace(
            "**Before-audit**: passed @ -",
            "**Before-audit**: passed @ -"))  # recorded while still draft
        cls.draft_state = compute(cls.draft)
        cls.approved = copy_fixture(cls._tmp / "b")
        set_status(cls.approved, "approved")
        write(cls.approved / "task.md", APPROVED_TASKS)
        cls.approved_state = compute(cls.approved)
        cls.done_dir = done_fixture(cls._tmp / "c")
        cls.done_state = compute(cls.done_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_draft_hold_at_approve(self):
        n = self.draft_state["nodes"]
        self.assertEqual(self.draft_state["status"], "draft")
        self.assertEqual(n["before-audit"]["state"], "done")
        self.assertEqual(n["approve"]["state"], "READY")
        self.assertIn("approve", frontier_of(self.draft_state))
        self.assertEqual(n["execute"]["state"], "blocked")
        self.assertIn("approve", n["execute"]["reason"])

    def test_approved_unblocks_execute(self):
        n = self.approved_state["nodes"]
        self.assertEqual(self.approved_state["status"], "approved")
        self.assertEqual(n["approve"]["state"], "done")
        self.assertEqual(n["execute"]["state"], "READY")
        self.assertIn("execute", frontier_of(self.approved_state))

    def test_done_status_holds_at_the_closing_audit_gate(self):
        n = self.done_state["nodes"]
        self.assertEqual(self.done_state["status"], "done")
        self.assertEqual(n["execute"]["state"], "done")
        self.assertEqual(n["closing-audit"]["state"], "READY")
        self.assertEqual(n["tick-commit"]["state"], "blocked")
        self.assertEqual(n["archive"]["state"], "blocked")
        self.assertEqual(frontier_of(self.done_state), ["closing-audit"])

    def test_status_line_in_reports(self):
        for state, word in ((self.draft_state, "draft"),
                            (self.approved_state, "approved"),
                            (self.done_state, "done")):
            self.assertEqual(state["status"], word)
        r = run_cli(self._tmp / "c" / "specs" / "demo", "--state-json")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["status"], "done")


class Graph006ClarifyHoldTests(unittest.TestCase):
    """GRAPH-006: an open NEEDS CLARIFICATION marker holds the whole frontier
    at clarify; removing the marker restores the GRAPH-001 state."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="graph006-"))
        self.spec_dir = spec_only(self._tmp)
        spec = (FIXTURE / "spec.md").read_text(encoding="utf-8")
        write(self.spec_dir / "spec.md",
              spec + "\nNEEDS CLARIFICATION: how should X behave?\n")
        self.held = compute(self.spec_dir)
        write(self.spec_dir / "spec.md", spec)
        self.cleared = compute(self.spec_dir)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_frontier_holds_at_clarify(self):
        n = self.held["nodes"]
        self.assertEqual(n["spec"]["state"], "blocked")
        self.assertIn("NEEDS CLARIFICATION", n["spec"]["reason"])
        self.assertEqual(n["clarify"]["state"], "READY")
        self.assertEqual(frontier_of(self.held), ["clarify"])
        self.assertEqual(n["survey"]["state"], "blocked")

    def test_no_agent_node_scheduled_while_open(self):
        for name in ("survey", "plan", "tech", "qa", "tasks"):
            self.assertEqual(self.held["nodes"][name]["state"], "blocked", name)

    def test_resolving_returns_to_graph001(self):
        n = self.cleared["nodes"]
        self.assertEqual(n["spec"]["state"], "done")
        self.assertEqual(n["clarify"]["state"], "done")
        self.assertEqual(frontier_of(self.cleared), ["survey"])


class Graph007StateJsonShapeTests(unittest.TestCase):
    """GRAPH-007: --state-json is valid JSON with the machine-readable keys
    later asserts consume — on empty, mid-pipeline, and approved states."""

    def test_valid_json_with_required_keys(self):
        tmp = Path(tempfile.mkdtemp(prefix="graph007-"))
        try:
            fixtures = [spec_only(tmp / "a"),
                        copy_fixture(tmp / "b")]
            approved = copy_fixture(tmp / "c")
            set_status(approved, "approved")
            write(approved / "task.md", APPROVED_TASKS)
            fixtures.append(approved)
            for d in fixtures:
                r = subprocess.run(
                    [sys.executable, str(GRAPH), str(d), "--state-json"],
                    capture_output=True, text=True, timeout=300)
                self.assertEqual(r.returncode, 0, r.stderr)
                piped = subprocess.run(
                    [sys.executable, "-m", "json.tool"],
                    input=r.stdout, capture_output=True, text=True)
                self.assertEqual(piped.returncode, 0, piped.stderr)
                s = json.loads(r.stdout)
                for key in ("nodes", "edges", "frontier", "loops", "counts",
                            "git", "status"):
                    self.assertIn(key, s, f"{d}: missing {key}")
                for name, node in s["nodes"].items():
                    self.assertIn(node["state"],
                                  ("done", "READY", "blocked",
                                   "gate:undetermined", "SKIPPED"), name)
                    self.assertTrue(node["reason"], name)
                self.assertEqual(
                    sorted(s["counts"]),
                    ["at-fix-cap", "claimed", "implemented", "struck",
                     "ticked", "todo"])
                self.assertIn("available", s["git"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Graph008MermaidTests(unittest.TestCase):
    """GRAPH-008: --mermaid renders the live state graph — state classes,
    dotted conditional/loop edges, and output that differs per fixture."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph008-"))
        cls.empty = spec_only(cls._tmp / "a")
        cls.approved = copy_fixture(cls._tmp / "b")
        set_status(cls.approved, "approved")
        write(cls.approved / "task.md", APPROVED_TASKS)
        cls.empty_out = run_cli(cls.empty, "--mermaid").stdout
        cls.approved_out = run_cli(cls.approved, "--mermaid").stdout

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_mermaid_directive_and_state_classes(self):
        for out in (self.empty_out, self.approved_out):
            first = out.lstrip().splitlines()[0]
            self.assertRegex(first, r"^(flowchart|graph|stateDiagram-v2)\b")
            self.assertIn("classDef", out)
            self.assertIn("-.->", out)
            self.assertIn("-->", out)

    def test_output_is_live_not_static(self):
        self.assertNotEqual(self.empty_out, self.approved_out)


class Graph009ExitCodeTests(unittest.TestCase):
    """GRAPH-009: 0 any readable spec-dir; 1 unreadable (message, not a
    traceback); 2 usage errors."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph009-"))
        cls.spec_dir = spec_only(cls._tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_readable_dir_exits_zero(self):
        self.assertEqual(run_cli(self.spec_dir).returncode, 0)

    def test_missing_dir_exits_one_with_message(self):
        r = run_cli(self._tmp / "nope")
        self.assertEqual(r.returncode, 1)
        self.assertTrue(r.stderr.strip())
        self.assertNotIn("Traceback", r.stderr)

    def test_file_not_dir_exits_one(self):
        r = run_cli(self.spec_dir / "spec.md")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)

    def test_usage_errors_exit_two(self):
        self.assertEqual(subprocess.run(
            [sys.executable, str(GRAPH)], capture_output=True).returncode, 2)
        self.assertEqual(run_cli(self.spec_dir, "--bogus").returncode, 2)
        self.assertEqual(run_cli(self.spec_dir, "--explain").returncode, 2)


class Graph010NonGitTests(unittest.TestCase):
    """GRAPH-010: git-derived signals degrade loudly — a visible
    `SKIPPED (not a git repo)` line in the report and an explicit git field."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph010-"))
        cls.spec_dir = copy_fixture(cls._tmp)
        cls.report = run_cli(cls.spec_dir).stdout
        cls.state = compute(cls.spec_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_report_carries_the_git_line(self):
        self.assertIn("git: SKIPPED (not a git repo)", self.report)

    def test_json_git_field_encodes_unavailability(self):
        self.assertFalse(self.state["git"]["available"])
        self.assertIsNone(self.state["git"]["head"])

    def test_converge_loop_reports_skip(self):
        self.assertIn("SKIPPED", self.state["loops"]["converge"])
        self.assertIn("not a git repo", self.state["loops"]["converge"])


class Graph011ExplainTests(unittest.TestCase):
    """GRAPH-011: --explain matches the JSON reason; execute explains the
    per-task frontier; unknown nodes exit 2 listing the valid names."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph011-"))
        cls.spec_dir = spec_only(cls._tmp / "a")
        cls.approved = copy_fixture(cls._tmp / "b")
        set_status(cls.approved, "approved")
        write(cls.approved / "task.md", APPROVED_TASKS)
        cls.state = compute(cls.spec_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_explain_survey_matches_json_reason(self):
        r = run_cli(self.spec_dir, "--explain", "survey")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(self.state["nodes"]["survey"]["reason"], r.stdout)

    def test_explain_tech_names_the_research_requirement(self):
        r = run_cli(self.spec_dir, "--explain", "tech")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("research", r.stdout)

    def test_explain_execute_lists_per_task_readiness(self):
        r = run_cli(self.approved, "--explain", "execute")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("T001", r.stdout)
        self.assertIn("T002", r.stdout)
        self.assertIn("T003", r.stdout)
        self.assertIn("runnable", r.stdout)

    def test_unknown_node_exits_two_with_valid_names(self):
        r = run_cli(self.spec_dir, "--explain", "bogus")
        self.assertEqual(r.returncode, 2)
        for name in ("spec", "survey", "execute", "archive"):
            self.assertIn(name, r.stdout + r.stderr)


class Graph012VerifyAndBeforeAuditTests(unittest.TestCase):
    """GRAPH-012: verify reflects check.py (blocked on red, done on green);
    before-audit parses `passed @ <sha>` and the non-git `passed @ -` form."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="graph012-"))
        self.spec_dir = copy_fixture(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_green_fixture_verifies_done(self):
        self.assertEqual(compute(self.spec_dir)["nodes"]["verify"]["state"],
                         "done")

    def test_broken_docset_blocks_verify_with_reason(self):
        task = (self.spec_dir / "task.md").read_text(encoding="utf-8")
        broken = task.replace(
            "## Conventions",
            "- [ ] T009 (after T999) broken dependency (FR-001)\n\n"
            "## Conventions")
        write(self.spec_dir / "task.md", broken)
        n = compute(self.spec_dir)["nodes"]
        self.assertEqual(n["verify"]["state"], "blocked")
        self.assertIn("check.py", n["verify"]["reason"])

    def test_fixing_the_defect_restores_verify_done(self):
        self.test_broken_docset_blocks_verify_with_reason()  # build red state
        write(self.spec_dir / "task.md",
              (FIXTURE / "task.md").read_text(encoding="utf-8"))
        self.assertEqual(compute(self.spec_dir)["nodes"]["verify"]["state"],
                         "done")

    def test_before_audit_forms(self):
        task_path = self.spec_dir / "task.md"
        original = task_path.read_text(encoding="utf-8")
        self.assertEqual(compute(self.spec_dir)["nodes"]["before-audit"]["state"],
                         "READY")  # fixture records pending
        for line in ("**Before-audit**: passed @ 3fa9c21",
                     "Before-audit: passed @ -"):
            write(task_path, original.replace(
                "**Before-audit**: pending — the orchestrator writes "
                "`passed @ <sha>` here", line))
            # A SHA belongs to a git repo; this temp fixture is non-git, so
            # only the dash form can pass the real integrity-aware check.
            # The SHA form is still a parsed before-audit record when verify
            # is green (mocked here).
            with unittest.mock.patch.object(graph, "run_check",
                                            return_value=0):
                state = compute(self.spec_dir)["nodes"]["before-audit"]["state"]
            self.assertEqual(state, "done", line)


class Graph013FixtureIntegrationTests(unittest.TestCase):
    """GRAPH-013: graph.py on the real mini-spec fixture — exit 0, coherent
    state, and byte-identical directory checksums before/after (no mutation)."""

    @classmethod
    def setUpClass(cls):
        cls.before = dir_checksum(FIXTURE)
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "graph.py"), str(FIXTURE),
             "--state-json"], capture_output=True, text=True, timeout=300)
        cls.rc = r.returncode
        cls.stdout = r.stdout
        cls.after = dir_checksum(FIXTURE)

    def test_exit_zero_valid_json_no_mutation(self):
        self.assertEqual(self.rc, 0)
        s = json.loads(self.stdout)
        self.assertEqual(self.before, self.after, "fixture was mutated")

    def test_coherent_state_for_the_check_green_fixture(self):
        n = json.loads(self.stdout)["nodes"]
        self.assertEqual(n["spec"]["state"], "done")
        self.assertEqual(n["research"]["state"], "SKIPPED")
        self.assertEqual(n["survey"]["state"], "done")
        for name in ("plan", "tech", "qa", "tasks", "verify"):
            self.assertEqual(n[name]["state"], "done", name)
        self.assertEqual(n["before-audit"]["state"], "READY")
        self.assertEqual(n["execute"]["state"], "blocked")
        self.assertEqual(json.loads(self.stdout)["frontier"], ["before-audit"])


class Graph014EndStateTests(unittest.TestCase):
    """GRAPH-014: a done-status docset with no recorded closing-audit
    approval reports the closing-audit gate with exit 0 (FR-004 — no
    inspection mode runs the DoD probe to get past it); a zero-file dir
    reports spec pending/blocked, exit 0, no crash."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph014-"))
        cls.done_dir = done_fixture(cls._tmp / "a")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_done_spec_holds_at_the_closing_audit_gate(self):
        r = run_cli(self.done_dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("closing-audit", r.stdout)
        self.assertNotIn("AWAITING HUMAN", r.stdout)
        self.assertEqual(frontier_of(compute(self.done_dir)),
                         ["closing-audit"])

    def test_run_on_done_spec_pauses_at_the_closing_audit_gate(self):
        r = run_cli(self.done_dir, "--run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("AWAITING HUMAN: closing-audit", r.stdout)
        self.assertFalse((self.done_dir / "spawns").exists(),
                         "no spawn past the closing-audit gate")

    def test_zero_file_dir_is_pending_not_a_crash(self):
        empty = self._tmp / "b" / "specs" / "void"
        empty.mkdir(parents=True)
        r = run_cli(empty)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(compute(empty)["nodes"]["spec"]["state"], "blocked")


NOTE_LINE = "      done 2026-09-08 — proof: python3 -m pytest repo/test_calc.py green\n"


class Graph015TickCommitEvidenceTests(unittest.TestCase):
    """GRAPH-015 (FR-006/AC5/AC6, TC-006): tick evidence is durable task.md
    state — the specstate parser reads ticked/struck counts and the gaps
    (unticked, ticked-without-proof-note) the tick-commit gate consumes once
    the closing-audit approval is recorded (FR-005). Node-level: past execute
    the graph holds at the inert closing-audit gate (FR-004, GRAPH-016), so
    tick-commit never opens on inspection alone — whatever test.md's pass
    conditions would score."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="graph015-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_ticked_docset_holds_at_the_closing_audit_gate(self):
        d = closing_fixture(self._tmp / "a", dod_green=True)
        s = compute(d)
        n = s["nodes"]
        self.assertEqual(n["closing-audit"]["state"], "READY")
        self.assertEqual(n["tick-commit"]["state"], "blocked")
        self.assertIn("closing-audit", n["tick-commit"]["reason"])
        self.assertEqual(n["archive"]["state"], "blocked")

    def test_tick_evidence_parser_reads_counts_and_gaps(self):
        open_ev = graph.specstate.tick_evidence(APPROVED_TASKS)
        self.assertEqual((open_ev.total, open_ev.ticked, open_ev.struck),
                         (3, 0, 0))
        self.assertEqual(open_ev.unticked, ["T001", "T002", "T003"])
        self.assertEqual(open_ev.noteless, [])
        done_ev = graph.specstate.tick_evidence(TICKED_ALL_TASKS)
        self.assertEqual((done_ev.total, done_ev.ticked, done_ev.struck),
                         (3, 3, 0))
        self.assertEqual(done_ev.unticked, [])
        self.assertEqual(done_ev.noteless, [])
        noteless_ev = graph.specstate.tick_evidence(
            TICKED_ALL_TASKS.replace(NOTE_LINE, "", 1))
        self.assertEqual(noteless_ev.unticked, [])
        self.assertEqual(noteless_ev.noteless, ["T001"])
        struck_ev = graph.specstate.tick_evidence(STRUCK_DEP_TASKS)
        self.assertEqual(struck_ev.struck, 1)
        self.assertNotIn(None, struck_ev.unticked)
        self.assertTrue(set(struck_ev.unticked) >= {"T002", "T003"})


MUTATING_TC = "touch proof-canary.txt"


def mutating_test_md(spec_dir: Path) -> None:
    """Swap the fixture's real pytest TC pass conditions for a mutating
    command — the probe no graph inspection mode may execute (FR-004)."""
    test = (FIXTURE / "test.md").read_text(encoding="utf-8")
    for tc in ("multiply", "zero"):
        test = test.replace(
            f"`cd repo && python3 -m pytest test_calc.py -k {tc}` exits 0",
            f"`{MUTATING_TC}` exits 0")
    write(spec_dir / "test.md", test)


class Graph016InertInspectionTests(unittest.TestCase):
    """GRAPH-016 (FR-004/AC3, TC-004): every inspection mode — report,
    --state-json, --mermaid, --explain, --emit-spawns, --run --dry-run —
    computes state without executing repository or test.md commands. A
    mutating pass condition stays inert end-to-end; the closing-audit gate
    reports the dry classification (auto/manual counts, nothing executed);
    the live proof path is unreachable from compute_state."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="graph016-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        d = copy_fixture(self._tmp)
        set_status(d, "approved")
        write(d / "task.md", IMPLEMENTED_ALL_TASKS)
        mutating_test_md(d)
        self.spec_dir = d

    def assert_canary_absent(self):
        for root in (self._tmp, self.spec_dir):
            self.assertFalse((root / "proof-canary.txt").exists(),
                             "the mutating pass condition executed")

    def test_mutating_pass_condition_stays_inert_in_every_mode(self):
        modes = ([], ["--state-json"], ["--mermaid"],
                 ["--explain", "closing-audit"],
                 ["--emit-spawns"], ["--run", "--dry-run"])
        for argv in modes:
            r = run_cli(self.spec_dir, *argv)
            self.assertEqual(r.returncode, 0, (argv, r.stderr))
            self.assertNotIn("Traceback", r.stderr)
            self.assert_canary_absent()

    def test_closing_audit_gate_reports_the_dry_classification(self):
        s = compute(self.spec_dir)
        n = s["nodes"]
        self.assertEqual(n["execute"]["state"], "done")
        self.assertEqual(n["closing-audit"]["state"], "READY")
        self.assertIn("HUMAN GATE", n["closing-audit"]["reason"])
        self.assertIn("not executed", n["closing-audit"]["reason"])
        self.assertIn("closing-audit", frontier_of(s))
        self.assertEqual(n["tick-commit"]["state"], "blocked")

    def test_live_proof_path_is_unreachable_from_compute_state(self):
        self.assertFalse(hasattr(graph, "run_dod"),
                         "the live DoD probe must be gone, not dormant")
        def boom(*args, **kwargs):
            self.fail("compute_state reached the live proof path")
        with unittest.mock.patch.object(graph.audit, "proofs_data", boom), \
                unittest.mock.patch.object(graph.audit, "mode_dod", boom):
            s = compute(self.spec_dir)
        self.assertEqual(s["nodes"]["closing-audit"]["state"], "READY")
        self.assert_canary_absent()


class Graph017ClosingApprovalTests(unittest.TestCase):
    """GRAPH-017 (FR-005/AC4, TC-005): the closing-audit gate opens on the
    durable task.md record, never on a mechanical score. Every task landed
    with green TC pass conditions still holds at the gate until
    `Closing-audit: approved` is recorded; the record — and only the record
    — reads done and releases tick-commit (FR-006's approved tick
    transition), on ticked and implemented-unticked plans alike."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="graph017-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_mechanical_green_holds_without_the_record(self):
        # TC-005's given: the checks pass (always-green TCs, every task
        # ticked) but no human acknowledgment is recorded anywhere.
        d = closing_fixture(self._tmp / "a", dod_green=True)
        s = compute(d)
        n = s["nodes"]
        self.assertEqual(n["closing-audit"]["state"], "READY")
        self.assertIn("HUMAN GATE", n["closing-audit"]["reason"])
        self.assertIn("Closing-audit: approved", n["closing-audit"]["reason"])
        self.assertEqual(n["tick-commit"]["state"], "blocked")
        self.assertEqual(frontier_of(s), ["closing-audit"])

    def test_recorded_approval_reads_done_and_opens_tick_commit(self):
        d = closing_fixture(self._tmp / "b", dod_green=True,
                            closing_approved=True)
        s = compute(d)
        n = s["nodes"]
        self.assertEqual(n["closing-audit"]["state"], "done")
        self.assertIn("Closing-audit: approved", n["closing-audit"]["reason"])
        self.assertEqual(n["tick-commit"]["state"], "done")
        self.assertIn("SKIPPED (not a git repo)", n["tick-commit"]["reason"])
        self.assertEqual(n["archive"]["state"], "blocked")

    def test_approval_releases_the_implemented_unticked_plan(self):
        # The FR-003 → FR-005 chain: execute completed on landing alone, the
        # human record opens the gate, and the ticks stay the human's move
        # (tick-commit READY, never auto-ticked).
        d = implemented_fixture(self._tmp / "c", dod_green=True,
                                closing_approved=True)
        s = compute(d)
        n = s["nodes"]
        self.assertEqual(n["execute"]["state"], "done")
        self.assertEqual(n["closing-audit"]["state"], "done")
        self.assertEqual(n["tick-commit"]["state"], "READY")
        self.assertIn("approved ticking", n["tick-commit"]["reason"])
        self.assertEqual(n["archive"]["state"], "blocked")

    def test_run_pauses_at_tick_commit_once_approved(self):
        d = implemented_fixture(self._tmp / "d", dod_green=True,
                                closing_approved=True)
        r = run_cli(d, "--run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        self.assertNotIn("AWAITING HUMAN: closing-audit", r.stdout)
        self.assertFalse((d / "spawns").exists(),
                         "no spawn past the tick-commit gate")

    def test_pending_placeholder_record_does_not_open_the_gate(self):
        d = closing_fixture(self._tmp / "e", dod_green=True)
        tasks = (d / "task.md").read_text(encoding="utf-8")
        write(d / "task.md", tasks
              + "\n**Closing-audit**: pending — the orchestrator writes "
                "`approved @ <sha>` here\n")
        s = compute(d)
        self.assertEqual(s["nodes"]["closing-audit"]["state"], "READY")
        self.assertEqual(s["nodes"]["tick-commit"]["state"], "blocked")


DELIVERY_SHA = "feed7c0"


def with_delivery_record(tasks_md: str, record: str) -> str:
    """task.md text with the `Delivered:` header record appended — record is
    the line body, e.g. `commit @ feed7c0`, the non-git skip `commit @ -`,
    or the scaffold's pending placeholder wording."""
    return tasks_md + f"\n**Delivered**: {record}\n"


class Graph018DeliveryEvidenceTests(unittest.TestCase):
    """GRAPH-018 (FR-006/AC6, TC-006): tick-commit's done citation carries
    durable evidence — the task.md tick counts with proof notes plus the
    delivery record: `Delivered: commit @ <sha>` where git exists, the
    explicit non-git skip where it does not. Ticks alone never read done in
    a git repo, a dash is not a SHA there, and the scaffold's pending
    placeholders never read as records."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="graph018-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def compute_in_git(self, spec_dir):
        """compute_state with the git probes answering as a real repository
        (mocked, never initialized — test_git_degradation's sanctioned
        simulation)."""
        with unittest.mock.patch.object(graph.specstate, "git_available",
                                        return_value=True), \
             unittest.mock.patch.object(graph.specstate, "head_sha",
                                        return_value=DELIVERY_SHA), \
             unittest.mock.patch.object(graph, "run_check", return_value=0):
            return compute(spec_dir)

    def delivered(self, name, record):
        d = closing_fixture(self._tmp / name, closing_approved=True)
        tasks = (d / "task.md").read_text(encoding="utf-8")
        write(d / "task.md", with_delivery_record(tasks, record))
        return d

    def test_recorded_commit_sha_reads_tick_commit_done(self):
        d = self.delivered("a", f"commit @ {DELIVERY_SHA}")
        n = self.compute_in_git(d)["nodes"]
        self.assertEqual(n["tick-commit"]["state"], "done")
        self.assertIn(f"Delivered: commit @ {DELIVERY_SHA}",
                      n["tick-commit"]["reason"])
        self.assertIn("recorded in task.md", n["tick-commit"]["reason"])
        self.assertNotIn("delivery unproven", n["tick-commit"]["reason"])

    def test_ticks_without_delivery_record_stay_ready(self):
        d = closing_fixture(self._tmp / "b", closing_approved=True)
        n = self.compute_in_git(d)["nodes"]
        self.assertEqual(n["tick-commit"]["state"], "READY")
        self.assertIn("delivery unproven", n["tick-commit"]["reason"])
        self.assertIn("no commit SHA observed", n["tick-commit"]["reason"])

    def test_dash_skip_record_is_not_a_sha_where_git_exists(self):
        d = self.delivered("c", "commit @ -")
        n = self.compute_in_git(d)["nodes"]
        self.assertEqual(n["tick-commit"]["state"], "READY")
        self.assertIn("delivery unproven", n["tick-commit"]["reason"])

    def test_delivered_pending_placeholder_stays_ready(self):
        d = self.delivered(
            "d", "pending — the orchestrator writes `commit @ <sha>` here")
        n = self.compute_in_git(d)["nodes"]
        self.assertEqual(n["tick-commit"]["state"], "READY")
        self.assertIn("delivery unproven", n["tick-commit"]["reason"])

    def test_non_git_skip_record_keeps_done(self):
        d = self.delivered("e", "commit @ -")
        s = compute(d)
        self.assertEqual(s["git"]["available"], False)
        self.assertEqual(s["nodes"]["tick-commit"]["state"], "done")
        self.assertIn("SKIPPED (not a git repo)",
                      s["nodes"]["tick-commit"]["reason"])

    def test_scaffold_placeholders_read_pending_never_done(self):
        d = scaffold(self._tmp / "t")
        tasks = (d / "task.md").read_text(encoding="utf-8")
        self.assertEqual(graph.specstate.before_audit_state(tasks), "pending")
        self.assertEqual(graph.specstate.closing_audit_state(tasks), "pending")
        self.assertEqual(graph.specstate.delivery_state(tasks),
                         ("pending", None))


# ---------------------------------------------------------------------------
# Executor modes (--emit-spawns / --run) — EXEC-001..010. Payloads are built
# from doc state alone (brief bodies + _shared-protocol.md + filled input
# payload) into specs/<name>/spawns/wave-<N>/; --run loops waves with the
# configured runner and pauses AWAITING HUMAN at every judgment node without
# ever mutating doc state. The default runner is `print` (echo only).
# ---------------------------------------------------------------------------

def doc_hashes(spec_dir: Path) -> dict:
    """Content hashes of the doc files directly in the spec dir — the doc
    state whose invariance the executor guarantees (spawns/ excluded)."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(spec_dir.glob("*.md"))}


def wave2_fixture(tmp: Path, name: str = "demo") -> Path:
    """The GRAPH-002 after-state: spec + valid survey + real research →
    plan ∥ tech ∥ qa all READY (the stage-2 wave, wave 2)."""
    d = scaffold(tmp, name)
    write(d / "spec.md", (FIXTURE / "spec.md").read_text(encoding="utf-8"))
    write(d / "survey.md", (FIXTURE / "survey.md").read_text(encoding="utf-8"))
    write(d / "research.md",
          "## Research: demo\n\n### Q1 how to name the operation\n"
          "- **source**: https://example.com/naming — claim: plain names\n"
          "  relevance: direct · confidence: high\n")
    return d


def approved_fixture(tmp: Path, name: str = "demo") -> Path:
    """Approved + before-audit recorded + three crafted tasks: execute is
    the whole frontier (T001 runnable, T002 dep-chained, T003 at cap)."""
    d = copy_fixture(tmp, name)
    set_status(d, "approved")
    write(d / "task.md", APPROVED_TASKS)
    return d


TICKED_ALL_TASKS = """# Tasks: demo

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ -

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1     | 3     | 3    |
| **Σ** | 3     | 3    |

## Phase 1: land the feature (FR-001, FR-002)
- [x] T001 [P] implement multiply in `repo/calc.py` (FR-001)
      done 2026-09-08 — proof: python3 -m pytest repo/test_calc.py green
- [x] T002 (after T001) wire the caller `repo/test_calc.py` (FR-001)
      done 2026-09-08 — proof: python3 -m pytest repo/test_calc.py green
- [x] T003 (fix 5/5) rescue the stalled refactor (FR-002)
      done 2026-09-08 — proof: python3 -m pytest repo/test_calc.py green

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done + proof note
"""


def with_closing_approval(tasks_md: str) -> str:
    """task.md text with the durable closing-audit approval record in its
    header — `Closing-audit: approved @ -`, the non-git form (the tmp
    fixtures sit outside any repo), mirroring the Before-audit line."""
    return tasks_md.replace(
        "**Before-audit**: passed @ -",
        "**Before-audit**: passed @ -\n**Closing-audit**: approved @ -")


def closing_fixture(tmp: Path, name: str = "demo", dod_green: bool = False,
                    status: str = "approved",
                    closing_approved: bool = False) -> Path:
    """All tasks ticked + before-audit recorded: the closing-audit /
    tick-commit stretch. dod_green swaps TC pass conditions to always-green
    commands (what audit.py dod's own CLI would score green); dod_red
    (default) keeps the fixture's real pytest TCs, which fail against the
    unimplemented repo. Graph inspection runs neither — both hold at the
    inert closing-audit gate (FR-004) until the approval is recorded in
    task.md (closing_approved, FR-005)."""
    d = copy_fixture(tmp, name)
    set_status(d, status)
    write(d / "task.md", with_closing_approval(TICKED_ALL_TASKS)
          if closing_approved else TICKED_ALL_TASKS)
    if dod_green:
        green_test_md(d)
    return d


def implemented_fixture(tmp: Path, name: str = "demo",
                        dod_green: bool = False,
                        closing_approved: bool = False) -> Path:
    """All tasks `(implemented)`, none ticked + before-audit recorded:
    execute's completion state without the forbidden early tick (TC-003)."""
    d = copy_fixture(tmp, name)
    set_status(d, "approved")
    write(d / "task.md", with_closing_approval(IMPLEMENTED_ALL_TASKS)
          if closing_approved else IMPLEMENTED_ALL_TASKS)
    if dod_green:
        green_test_md(d)
    return d


class Exec001EmitSpawnsTests(unittest.TestCase):
    """EXEC-001: --emit-spawns writes one self-contained payload per
    frontier agent node under spawns/wave-<N>/ — brief body (frontmatter
    stripped) contiguous + byte-verbatim, _shared-protocol.md verbatim,
    filled input payload naming spec dir + FR list, resolved skill_dir."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="exec001-"))
        cls.spec_dir = wave2_fixture(cls._tmp)
        cls.r = run_cli(cls.spec_dir, "--emit-spawns")
        cls.wave = cls.spec_dir / "spawns" / "wave-2"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_one_payload_per_frontier_agent_in_wave_2(self):
        self.assertEqual(self.r.returncode, 0, self.r.stderr)
        self.assertEqual(sorted(p.name for p in self.wave.glob("*.md")),
                         ["planner.md", "qa.md", "tech.md"])
        self.assertIn("wave-2", self.r.stdout)

    def test_brief_body_is_contiguous_verbatim_frontmatter_stripped(self):
        for name, brief in (("planner.md", "spec-planner.md"),
                            ("tech.md", "spec-tech.md"),
                            ("qa.md", "spec-qa.md")):
            raw = (SKILL / "agents" / brief).read_text(encoding="utf-8")
            body = graph.strip_frontmatter(raw)
            payload = (self.wave / name).read_text(encoding="utf-8")
            self.assertIn(body, payload, name)
            self.assertNotIn("disallowedTools", payload, name)

    def test_shared_protocol_verbatim_for_every_role(self):
        protocol = (SKILL / "agents" / "_shared-protocol.md").read_text(
            encoding="utf-8")
        for name in ("planner.md", "tech.md", "qa.md"):
            payload = (self.wave / name).read_text(encoding="utf-8")
            self.assertIn(protocol, payload, name)

    def test_wave_dir_override(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec001b-"))
        try:
            d = wave2_fixture(tmp)
            out = tmp / "custom-wave"
            r = run_cli(d, "--emit-spawns", "--wave-dir", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(sorted(p.name for p in out.glob("*.md")),
                             ["planner.md", "qa.md", "tech.md"])
            self.assertFalse((d / "spawns").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_input_payload_names_spec_dir_frs_and_skill_dir(self):
        payload = (self.wave / "planner.md").read_text(encoding="utf-8")
        self.assertIn(str(self.spec_dir), payload)
        self.assertIn("**FR-001**", payload)
        self.assertIn(str(SKILL), payload)


class Exec002SpawnsDerivedOnlyTests(unittest.TestCase):
    """EXEC-002: spawns/ is a derived, regenerate-only artifact — check.py's
    output and exit are identical with and without it, and re-emitting after
    deletion regenerates byte-identical payloads."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec002-"))
        self.spec_dir = wave2_fixture(self._tmp)
        run_cli(self.spec_dir, "--emit-spawns")

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def check_run(self):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "check.py"), str(self.spec_dir)],
            capture_output=True, text=True, timeout=300)

    def test_check_output_identical_with_and_without_spawns(self):
        with_spawns = self.check_run()
        shutil.rmtree(self.spec_dir / "spawns")
        without = self.check_run()
        self.assertEqual(with_spawns.returncode, without.returncode)
        self.assertEqual(with_spawns.stdout, without.stdout)

    def test_reemit_regenerates_identical_payloads(self):
        before = {p.name: p.read_bytes()
                  for p in (self.spec_dir / "spawns").rglob("*.md")}
        shutil.rmtree(self.spec_dir / "spawns")
        r = run_cli(self.spec_dir, "--emit-spawns")
        self.assertEqual(r.returncode, 0, r.stderr)
        after = {p.name: p.read_bytes()
                 for p in (self.spec_dir / "spawns").rglob("*.md")}
        self.assertEqual(before, after)

    def test_task_md_never_mentions_spawns(self):
        self.assertNotIn(
            "spawns",
            (self.spec_dir / "task.md").read_text(encoding="utf-8"))


class Exec003DryRunTests(unittest.TestCase):
    """EXEC-003: --run --dry-run prints the full wave plan (frontier, payload
    paths, runner invocations) and changes nothing but the payload files."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="exec003-"))
        cls.spec_dir = approved_fixture(cls._tmp)
        cls.before = doc_hashes(cls.spec_dir)
        cls.r = run_cli(cls.spec_dir, "--run", "--dry-run")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_exit_zero_with_full_plan(self):
        self.assertEqual(self.r.returncode, 0, self.r.stderr)
        self.assertIn("wave 4", self.r.stdout)
        self.assertIn("implementer.md", self.r.stdout)
        self.assertIn("print", self.r.stdout)

    def test_doc_state_unchanged_modulo_spawns(self):
        self.assertEqual(self.before, doc_hashes(self.spec_dir))

    def test_payloads_written_no_gate_no_agent_execution(self):
        self.assertTrue((self.spec_dir / "spawns" / "wave-4"
                         / "implementer.md").exists())
        self.assertNotIn("AWAITING HUMAN", self.r.stdout)
        self.assertIn("no doc-state change", self.r.stdout)


class Exec004GatePauseTests(unittest.TestCase):
    """EXEC-004: --run pauses AWAITING HUMAN on judgment nodes — an
    undetermined research-gate stops before any wave; a draft-spec approve
    gate stops without ever writing Status."""

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_undetermined_gate_pauses_before_any_spawn(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec004a-"))
        d = spec_only(self._tmp)
        r = run_cli(d, "--run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("AWAITING HUMAN: research-gate", r.stdout)
        self.assertFalse((d / "spawns").exists(), "no wave for a gate")

    def test_approve_gate_pauses_and_never_writes_status(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec004b-"))
        d = copy_fixture(self._tmp)  # draft; before-audit recorded below
        write(d / "task.md", APPROVED_TASKS)
        before = doc_hashes(d)
        r = run_cli(d, "--run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("AWAITING HUMAN: approve", r.stdout)
        self.assertEqual(before, doc_hashes(d))


class Exec005GateHashInvarianceTests(unittest.TestCase):
    """EXEC-005: at every human gate --run stops with AWAITING HUMAN and
    mutates no doc state — no Status writes, no ticks, no marker removals."""

    def run_gate(self, spec_dir):
        before = doc_hashes(spec_dir)
        r = run_cli(spec_dir, "--run")
        return r, before, doc_hashes(spec_dir)

    def test_clarify_gate_holds_and_never_edits_spec(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec005a-"))
        try:
            d = spec_only(tmp)
            spec = (FIXTURE / "spec.md").read_text(encoding="utf-8")
            write(d / "spec.md",
                  spec + "\nNEEDS CLARIFICATION: how should X behave?\n")
            r, before, after = self.run_gate(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("AWAITING HUMAN: clarify", r.stdout)
            self.assertEqual(before, after)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_closing_audit_gate_on_dod_red(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec005b-"))
        try:
            d = closing_fixture(tmp, dod_green=False)
            r, before, after = self.run_gate(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("AWAITING HUMAN: closing-audit", r.stdout)
            self.assertEqual(before, after)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_dod_green_docset_still_pauses_at_closing_audit(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec005c-"))
        try:
            d = closing_fixture(tmp, dod_green=True, status="approved")
            r, before, after = self.run_gate(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("AWAITING HUMAN: closing-audit", r.stdout)
            self.assertNotIn("AWAITING HUMAN: tick-commit", r.stdout)
            self.assertEqual(before, after)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_before_audit_stop_is_a_pause_too(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec005d-"))
        try:
            d = copy_fixture(tmp)  # verify done, Before-audit pending
            r, before, after = self.run_gate(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("AWAITING HUMAN: before-audit", r.stdout)
            self.assertEqual(before, after)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_gate_fixture_ever_gets_ticked_by_run(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec005e-"))
        try:
            d = approved_fixture(tmp)
            r, before, after = self.run_gate(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(before, after)
            self.assertNotIn("- [x] T0",
                             (d / "task.md").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Exec006RunnerTemplateTests(unittest.TestCase):
    """EXEC-006: --runner placeholders are substituted verbatim with real
    paths; no unsubstituted {...} token survives in the echoed lines."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="exec006-"))
        cls.spec_dir = wave2_fixture(cls._tmp)
        cls.r = run_cli(
            cls.spec_dir, "--run", "--dry-run", "--runner",
            "agentx spawn --prompt {prompt_file} --as {role} "
            "--cwd {spec_dir} --skill {skill_dir}")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def runner_lines(self):
        return [ln for ln in self.r.stdout.splitlines() if "agentx" in ln]

    def test_three_substituted_invocations(self):
        self.assertEqual(self.r.returncode, 0, self.r.stderr)
        self.assertEqual(len(self.runner_lines()), 3)

    def test_no_residual_placeholders(self):
        for ln in self.runner_lines():
            self.assertNotIn("{", ln, ln)

    def test_each_placeholder_gets_a_real_value(self):
        lines = self.runner_lines()
        for role, payload in (("planner", "planner.md"), ("tech", "tech.md"),
                              ("qa", "qa.md")):
            ln = next(l for l in lines if f"--as {role}" in l)
            self.assertIn(str(self.spec_dir / "spawns" / "wave-2" / payload), ln)
            self.assertIn(f"--cwd {self.spec_dir}", ln)
            self.assertIn(f"--skill {SKILL}", ln)


class Exec007MaxWavesTests(unittest.TestCase):
    """EXEC-007: --max-waves bounds the loop — exactly one wave with the
    bound at 1 (print runner: doc state untouched); a runner that really
    writes artifacts advances the frontier and the bound still holds."""

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_bound_of_one_with_print_runner_changes_nothing(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec007a-"))
        d = wave2_fixture(self._tmp)
        before = doc_hashes(d)
        r = run_cli(d, "--run", "--max-waves", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count("== wave"), 1)
        self.assertIn("max-waves", r.stdout)
        self.assertEqual(before, doc_hashes(d),
                         "the print runner never advances doc state")

    def progress_runner(self, spec_dir: Path) -> str:
        map_py = ("import shutil,sys;r,s=sys.argv[1],sys.argv[2];"
                  "m={'planner':'plan.md','tech':'tech-spec.md',"
                  "'qa':'test.md','task-breaker':'task.md'};"
                  "shutil.copy(s+'-seed-'+r+'.md', s+'/'+m[r])")
        return f'python3 -c "{map_py}" {{role}} {{spec_dir}}'

    def seed(self, spec_dir: Path, role: str, text: str) -> None:
        write(Path(f"{spec_dir}-seed-{role}.md"), text)

    def test_real_runner_progresses_and_bound_holds_at_one(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec007b-"))
        d = wave2_fixture(self._tmp)
        self.seed(d, "planner",
                  "# Plan: demo\n\n## Milestone 1: multiply lands\n"
                  "All FR-001 and FR-002 work lands here; checkpoint: pytest "
                  "green.\n\n## Parallelization map\n- planner area: "
                  "`repo/calc.py` disjoint from `repo/test_calc.py`\n")
        self.seed(d, "tech",
                  "# Tech spec: demo\n\n## Approach\nA plain function in the "
                  "arithmetic module (FR-001).\n\n### D-001: plain function\n"
                  "Context: small module. Decision: plain function. "
                  "Consequences: none.\n")
        self.seed(d, "qa",
                  "# Test cases: demo\n\n## TC-001 — multiply\n"
                  "- **Traces to**: FR-001\n"
                  "- **Pass condition**: `python3 -c 'print(42)'` exits 0\n")
        task_before = (d / "task.md").read_bytes()
        r = run_cli(d, "--run", "--max-waves", "1",
                    "--runner", self.progress_runner(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count("== wave"), 1)
        self.assertIn("max-waves", r.stdout)
        self.assertTrue((d / "plan.md").exists(), "runner really ran")
        self.assertTrue((d / "tech-spec.md").exists())
        self.assertTrue((d / "test.md").exists())
        self.assertEqual((d / "task.md").read_bytes(), task_before,
                         "wave 2 never ran (no task-breaker seed)")

    def test_max_waves_two_proceeds_one_wave_further(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec007c-"))
        d = wave2_fixture(self._tmp)
        self.seed(d, "planner",
                  "# Plan: demo\n\n## Milestone 1: multiply lands\n"
                  "All FR-001 and FR-002 work lands here; checkpoint: pytest "
                  "green.\n\n## Parallelization map\n- planner area: "
                  "`repo/calc.py` disjoint from `repo/test_calc.py`\n")
        self.seed(d, "tech",
                  "# Tech spec: demo\n\n## Approach\nA plain function in the "
                  "arithmetic module (FR-001).\n\n### D-001: plain function\n"
                  "Context: small module. Decision: plain function. "
                  "Consequences: none.\n")
        self.seed(d, "qa",
                  "# Test cases: demo\n\n## TC-001 — multiply\n"
                  "- **Traces to**: FR-001\n"
                  "- **Pass condition**: `python3 -c 'print(42)'` exits 0\n")
        task_seed = (
            "# Tasks: demo\n\n**Before-audit**: pending\n\n"
            "## Burndown\n| Phase | Total | Done |\n|-------|-------|"
            "------|\n| 1     | 1     | 0    |\n| **Σ** | 1     | 0    |"
            "\n\n## Phase 1: multiply (FR-001)\n"
            "- [ ] T001 implement multiply in `repo/calc.py` (FR-001)\n")
        self.seed(d, "task-breaker", task_seed)
        r = run_cli(d, "--run", "--max-waves", "2",
                    "--runner", self.progress_runner(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count("== wave"), 2)
        self.assertIn("max-waves", r.stdout)
        self.assertEqual((d / "task.md").read_text(encoding="utf-8"),
                         task_seed, "wave 2 ran the task-breaker payload")


class Exec008VerifyInRunTests(unittest.TestCase):
    """EXEC-008: the mechanical verify node runs check.py directly inside
    --run (output/exit in the run log); a red check never advances."""

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_green_verify_logs_check_exit_zero(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec008a-"))
        d = copy_fixture(self._tmp)
        r = run_cli(d, "--run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("check.py", r.stdout)
        self.assertIn("exit 0", r.stdout)
        self.assertIn("AWAITING HUMAN: before-audit", r.stdout)

    def test_red_verify_surfaces_failure_and_holds(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec008b-"))
        d = copy_fixture(self._tmp)
        task = (d / "task.md").read_text(encoding="utf-8")
        write(d / "task.md", task.replace(
            "## Conventions",
            "- [ ] T009 (after T999) broken dependency (FR-001)\n\n"
            "## Conventions"))
        before = doc_hashes(d)
        r = run_cli(d, "--run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("exit 1", r.stdout)
        self.assertIn("FAIL", r.stdout)
        self.assertNotIn("AWAITING HUMAN: before-audit", r.stdout)
        self.assertEqual(before, doc_hashes(d))


class Exec009PayloadBuildingTests(unittest.TestCase):
    """EXEC-009: implementer payloads carry the task entry byte-verbatim plus
    the TC acceptance commands; the researcher payload carries the spec's
    research questions (prepared at the undetermined gate for the run
    decision — the gate itself is still a pause, never auto-spawned)."""

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_implementer_payload_entry_and_acceptance_commands(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec009a-"))
        d = approved_fixture(self._tmp)
        r = run_cli(d, "--emit-spawns")
        self.assertEqual(r.returncode, 0, r.stderr)
        wave = d / "spawns" / "wave-4"
        payload = (wave / "implementer.md").read_text(encoding="utf-8")
        self.assertIn("- [ ] T001 [P] implement multiply in `repo/calc.py` "
                      "(FR-001)", payload)
        self.assertIn(
            "cd repo && python3 -m pytest test_calc.py -k multiply", payload)
        self.assertFalse((wave / "implementer-T002.md").exists(),
                         "dep-chained task is not runnable")
        self.assertFalse((wave / "implementer-T003.md").exists(),
                         "at-fix-cap task is never auto-scheduled")

    def test_researcher_payload_carries_research_questions(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec009b-"))
        d = spec_only(self._tmp)
        spec = (FIXTURE / "spec.md").read_text(encoding="utf-8")
        write(d / "spec.md", spec +
              "\n## Open questions\n"
              "- Which integer overflow convention should multiply follow?\n"
              "- Should the operation accept bool operands (int subclass)?\n")
        r = run_cli(d, "--emit-spawns")
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = (d / "spawns" / "wave-1" / "researcher.md").read_text(
            encoding="utf-8")
        self.assertIn("Which integer overflow convention should multiply "
                      "follow?", payload)
        self.assertIn("Should the operation accept bool operands", payload)
        self.assertIn("**FR-001**", payload)


class Exec010CrossModeNamingTests(unittest.TestCase):
    """EXEC-010: --emit-spawns and --run --dry-run use identical payload
    paths under the same spawns/wave-<N>/ directory for the same state."""

    def test_identical_wave_paths_across_modes(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec010-"))
        try:
            d1 = wave2_fixture(tmp / "a")
            run_cli(d1, "--emit-spawns")
            emitted = sorted(str(p.relative_to(d1))
                             for p in (d1 / "spawns").rglob("*.md"))
            d2 = wave2_fixture(tmp / "b")
            r = run_cli(d2, "--run", "--dry-run")
            self.assertEqual(r.returncode, 0, r.stderr)
            planned = sorted(str(p.relative_to(d2))
                             for p in (d2 / "spawns").rglob("*.md"))
            self.assertEqual(emitted, planned)
            for rel in planned:
                self.assertIn(rel, r.stdout.replace("\\", "/"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class RunWaveDirTests(unittest.TestCase):
    """Scrutiny round-1 finding 2: --wave-dir is honored by --run too —
    payloads land in DIR instead of the default spawns/wave-<N>/, the same
    override semantics --emit-spawns --wave-dir already has, and the
    runner sees the overridden path."""

    def run_wave(self, tmp: Path) -> tuple[Path, Path, subprocess.CompletedProcess]:
        d = wave2_fixture(tmp)
        out = tmp / "custom-wave"
        r = run_cli(d, "--run", "--max-waves", "1", "--wave-dir", str(out))
        return d, out, r

    def test_run_writes_payloads_into_wave_dir(self):
        tmp = Path(tempfile.mkdtemp(prefix="execrundir-"))
        try:
            d, out, r = self.run_wave(tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(sorted(p.name for p in out.glob("*.md")),
                             ["planner.md", "qa.md", "tech.md"])
            self.assertFalse((d / "spawns").exists(),
                             "--wave-dir must override the default location")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_runner_sees_the_overridden_payload_path(self):
        tmp = Path(tempfile.mkdtemp(prefix="execrundir2-"))
        try:
            _d, out, r = self.run_wave(tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(str(out / "planner.md"),
                          r.stdout.replace("\\", "/"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Exec011RepairDeltaTests(unittest.TestCase):
    """EXEC-011: --repair emits one non-frontier agent node's payload
    (the single-agent repair-run instrument), and a stale survey
    baseline scopes that payload to a DELTA RE-SURVEY block — the files
    git says changed since the baseline, so the converge re-survey
    merges instead of rebuilding. Degradations stay loud: no git, a
    fresh baseline, or a failing diff never reads as an empty delta."""

    def payload_for(self, tmp: Path, git=True, head="def5678",
                    diff=("repo/calc.py", "repo/test_calc.py")):
        d = copy_fixture(tmp)
        patches = [
            unittest.mock.patch.object(graph.specstate, "git_available",
                                       lambda repo: git),
            unittest.mock.patch.object(graph.specstate, "head_sha",
                                       lambda repo: head),
            unittest.mock.patch.object(graph.specstate, "diff_paths",
                                       lambda repo, b, h:
                                       list(diff) if diff is not None else None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return d, graph.input_payload_for(
            "survey", d, tmp / "repo", None)

    def test_stale_baseline_carries_delta_block(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec011a-"))
        try:
            _d, payload = self.payload_for(tmp)
            # copy_fixture's survey baseline is "mini-calc v1 @ 3fa9c21"
            self.assertIn("baseline: mini-calc v1 @ 3fa9c21", payload)
            self.assertIn("DELTA RE-SURVEY: baseline 3fa9c21 != HEAD "
                          "def5678", payload)
            self.assertIn("do NOT rebuild", payload)
            self.assertIn("repo/calc.py", payload)
            self.assertIn("repo/test_calc.py", payload)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_fresh_baseline_has_no_delta_block(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec011b-"))
        try:
            _d, payload = self.payload_for(tmp, head="3fa9c21")
            self.assertNotIn("DELTA RE-SURVEY", payload)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_git_has_no_delta_block(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec011c-"))
        try:
            _d, payload = self.payload_for(tmp, git=False)
            self.assertNotIn("DELTA RE-SURVEY", payload)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_failing_diff_degrades_to_explicit_full_resurvey(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec011d-"))
        try:
            _d, payload = self.payload_for(tmp, diff=None)
            self.assertIn("delta: unavailable", payload)
            self.assertIn("re-survey in full", payload)
            self.assertNotIn("do NOT rebuild", payload)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_empty_diff_says_refresh_the_stamp_only(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec011e-"))
        try:
            _d, payload = self.payload_for(tmp, diff=())
            self.assertIn("no files changed", payload)
            self.assertIn("refresh", payload)
            self.assertNotIn("do NOT rebuild", payload)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_repair_emits_non_frontier_node_payload(self):
        """wave2_fixture sits at wave 2 (plan ∥ tech ∥ qa; survey done) —
        --repair survey adds the surveyor payload to that wave's dir and
        says so; the non-git tmp gets the plain full-survey shape."""
        tmp = Path(tempfile.mkdtemp(prefix="exec011f-"))
        try:
            d = wave2_fixture(tmp)
            r = run_cli(d, "--emit-spawns", "--repair", "survey")
            self.assertEqual(r.returncode, 0, r.stderr)
            wave = d / "spawns" / "wave-2"
            self.assertEqual(sorted(p.name for p in wave.glob("*.md")),
                             ["planner.md", "qa.md", "surveyor.md",
                              "tech.md"])
            payload = (wave / "surveyor.md").read_text(encoding="utf-8")
            self.assertIn("baseline: mini-calc v1 @ 3fa9c21", payload)
            self.assertNotIn("- DELTA RE-SURVEY:", payload)  # non-git tmp
            self.assertIn("repair: survey emitted", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


    def test_docs_only_delta_excludes_the_specs_tree(self):
        """A commit touching only specs/ (task ticks, survey.md's own
        refresh) can't invalidate a code citation — the delta filters
        the specs tree and reads 'no code files changed', never a
        forced re-survey (the cost this block exists to save)."""
        tmp = Path(tempfile.mkdtemp(prefix="exec011h-"))
        try:
            repo = tmp / "repo"
            d = repo / "specs" / "demo"
            d.mkdir(parents=True)
            write(d / "survey.md",
                  "# Survey: demo\n\n**Created**: 2026-09-13 | "
                  "**Baseline**: v1 @ 3fa9c21\n")
            for fn, f in (
                ("git_available", lambda repo: True),
                ("head_sha", lambda repo: "def5678"),
                ("diff_paths", lambda repo, b, h: [
                    "specs/CONSTITUTION.md", "specs/demo/survey.md",
                    "specs/demo/task.md"]),
            ):
                p = unittest.mock.patch.object(graph.specstate, fn, f)
                p.start()
                self.addCleanup(p.stop)
            payload = graph.input_payload_for("survey", d, repo, None)
            self.assertIn("no code files changed", payload)
            self.assertIn("only the specs tree", payload)
            self.assertNotIn("do NOT rebuild", payload)
            self.assertNotIn("specs/demo/task.md", payload)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_repair_frontier_node_is_not_duplicated(self):
        tmp = Path(tempfile.mkdtemp(prefix="exec011g-"))
        try:
            d = spec_only(tmp)  # survey IS the frontier
            r = run_cli(d, "--emit-spawns", "--repair", "survey")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(
                sorted(p.name for p in (d / "spawns" / "wave-1")
                       .glob("*.md")),
                ["researcher.md", "surveyor.md"])
            self.assertIn("already in the frontier", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Exec012RunnerFailureTests(unittest.TestCase):
    """EXEC-012 (FR-008/AC8): a runner that exits nonzero or raises stops
    the run — the diagnostic names the role and node, graph.py exits
    RUNNER_FAILED_EXIT (3), and neither the wave's remaining payloads nor
    any later wave start. dry-run and the print runner never invoke
    anything, so they can never trip the failure path."""

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_nonzero_runner_exits_three_and_stops_everything(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec012a-"))
        d = wave2_fixture(self._tmp)  # wave 2: planner ∥ tech ∥ qa
        r = run_cli(d, "--run", "--runner", "exit 7")
        self.assertEqual(r.returncode, graph.RUNNER_FAILED_EXIT, r.stderr)
        self.assertEqual(r.stdout.count("== wave"), 1, "no later wave")
        self.assertEqual(r.stdout.count("→ exit"), 1,
                         "the wave's remaining payloads are not invoked")
        self.assertIn("role planner", r.stdout)
        self.assertIn("node plan", r.stdout)
        self.assertIn("exited 7", r.stdout)
        self.assertNotIn("no doc-state change", r.stdout)

    def test_raised_runner_exits_three_with_diagnostic(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec012b-"))
        d = wave2_fixture(self._tmp)
        real_run = subprocess.run
        shell_calls = []

        def raising_run(cmd, **kwargs):
            # The runner invocation is the only shell=True subprocess.run
            # (check.py/audit.py probes never use the shell).
            if kwargs.get("shell"):
                shell_calls.append(cmd)
                raise OSError("cannot spawn the runner")
            return real_run(cmd, **kwargs)

        buf = io.StringIO()
        with unittest.mock.patch.object(graph.subprocess, "run",
                                        side_effect=raising_run), \
                contextlib.redirect_stdout(buf):
            rc = graph.run_loop(d, None, "agentx run {prompt_file}", False,
                                None)
        self.assertEqual(rc, graph.RUNNER_FAILED_EXIT)
        self.assertEqual(len(shell_calls), 1, "fail-fast: one attempt only")
        self.assertIn("role planner", buf.getvalue())
        self.assertIn("node plan", buf.getvalue())
        self.assertIn("raised", buf.getvalue())
        self.assertNotIn("Traceback", buf.getvalue())

    def test_failing_runner_progresses_then_stops_at_later_wave(self):
        """A multi-wave run (TC-008's shape): wave 2's runners really land
        plan/tech/qa, wave 3's task-breaker fails — wave 3 is the last one
        started and the exit is nonzero."""
        self._tmp = Path(tempfile.mkdtemp(prefix="exec012c-"))
        d = wave2_fixture(self._tmp)
        self.seed_ok_outputs(d)
        task_seed = (
            "# Tasks: demo\n\n**Before-audit**: pending\n\n"
            "## Burndown\n| Phase | Total | Done |\n|-------|-------|"
            "------|\n| 1     | 1     | 0    |\n| **Σ** | 1     | 0    |"
            "\n\n## Phase 1: multiply (FR-001)\n"
            "- [ ] T001 implement multiply in `repo/calc.py` (FR-001)\n")
        write(Path(f"{d}-seed-task-breaker.md"), task_seed)
        task_before = (d / "task.md").read_bytes()  # scaffold template
        runner = (f'python3 -c "import shutil,sys;r=sys.argv[1];'
                  f'm={{\'planner\':\'plan.md\',\'tech\':\'tech-spec.md\','
                  f'\'qa\':\'test.md\'}};'
                  f'sys.exit(1) if r==\'task-breaker\' else '
                  f'shutil.copy(sys.argv[2]+\'-seed-\'+r+\'.md\','
                  f' sys.argv[2]+\'/\'+m.get(r,\'x\'))" '
                  f'{{role}} {{spec_dir}}')
        r = run_cli(d, "--run", "--runner", runner)
        self.assertEqual(r.returncode, graph.RUNNER_FAILED_EXIT, r.stderr)
        self.assertEqual(r.stdout.count("== wave"), 2)
        self.assertIn("role task-breaker", r.stdout)
        self.assertIn("node tasks", r.stdout)
        self.assertTrue((d / "plan.md").exists(), "wave 2 really ran")
        self.assertEqual((d / "task.md").read_bytes(), task_before,
                         "the failing runner wrote nothing")

    def seed_ok_outputs(self, spec_dir: Path) -> None:
        for role, text in (
            ("planner",
             "# Plan: demo\n\n## Milestone 1: multiply lands\n"
             "All FR-001 and FR-002 work lands here; checkpoint: pytest "
             "green.\n\n## Parallelization map\n- planner area: "
             "`repo/calc.py` disjoint from `repo/test_calc.py`\n"),
            ("tech",
             "# Tech spec: demo\n\n## Approach\nA plain function in the "
             "arithmetic module (FR-001).\n\n### D-001: plain function\n"
             "Context: small module. Decision: plain function. "
             "Consequences: none.\n"),
            ("qa",
             "# Test cases: demo\n\n## TC-001 — multiply\n"
             "- **Traces to**: FR-001\n"
             "- **Pass condition**: `python3 -c 'print(42)'` exits 0\n"),
        ):
            write(Path(f"{spec_dir}-seed-{role}.md"), text)

    def test_dry_run_with_failing_template_stays_exit_zero(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="exec012d-"))
        d = wave2_fixture(self._tmp)
        r = run_cli(d, "--run", "--dry-run", "--runner", "exit 7")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("stopping: runner", r.stdout)


class ExecutorCliValidationTests(unittest.TestCase):
    """Executor flags are bound to their mode: runner/dry-run/max-waves
    require --run; --emit-spawns and --run are separate modes; the wave
    bound must be positive. Violations are usage errors (exit 2)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="execcli-"))
        cls.spec_dir = spec_only(cls._tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_runner_requires_run(self):
        self.assertEqual(
            run_cli(self.spec_dir, "--runner", "echo {prompt_file}").returncode,
            2)

    def test_dry_run_requires_run(self):
        self.assertEqual(run_cli(self.spec_dir, "--dry-run").returncode, 2)

    def test_emit_and_run_are_distinct_modes(self):
        self.assertEqual(
            run_cli(self.spec_dir, "--emit-spawns", "--run").returncode, 2)

    def test_max_waves_must_be_positive(self):
        self.assertEqual(
            run_cli(self.spec_dir, "--run", "--max-waves", "0").returncode, 2)

    def test_wave_dir_requires_emit_or_run(self):
        self.assertEqual(
            run_cli(self.spec_dir, "--wave-dir", "somewhere").returncode, 2)

    def test_repair_requires_emit_spawns(self):
        self.assertEqual(
            run_cli(self.spec_dir, "--repair", "survey").returncode, 2)
        self.assertEqual(
            run_cli(self.spec_dir, "--repair", "survey", "--run").returncode,
            2)

    def test_repair_rejects_unknown_and_non_repairable_nodes(self):
        self.assertEqual(
            run_cli(self.spec_dir, "--emit-spawns", "--repair",
                    "bogus").returncode, 2)
        self.assertEqual(
            run_cli(self.spec_dir, "--emit-spawns", "--repair",
                    "execute").returncode, 2)


    def test_strip_frontmatter(self):
        raw = (SKILL / "agents" / "spec-reviewer.md").read_text(
            encoding="utf-8")
        body = graph.strip_frontmatter(raw)
        self.assertTrue(body.lstrip().startswith("# Reviewer agent"))
        self.assertNotIn("readonly: true", body)


class Graph019LaunchCheckTests(unittest.TestCase):
    """GRAPH-019: --launch-check (D-022) — the spec-run launch advisory.
    Only a heavy span (a multi-payload wave, or any execute span) says
    launch_workflow; a pending human gate, one light doc node, complete,
    and held are inline moves — a workflow launch there reads state once
    and stops seconds later, deciding nothing."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph019-"))
        # research-gate pending: filled spec.md only (GRAPH-001 shape)
        cls.gate_research = spec_only(cls._tmp / "a")
        # clarify pending: the same spec plus an open marker
        cls.gate_clarify = spec_only(cls._tmp / "b")
        write(cls.gate_clarify / "spec.md",
              (FIXTURE / "spec.md").read_text(encoding="utf-8")
              + "\nNEEDS CLARIFICATION: how should X behave?\n")
        # before-audit pending: the mini-spec fixture as committed
        cls.gate_before_audit = copy_fixture(cls._tmp / "c")
        # closing-audit due: everything landed, Status done
        cls.gate_closing = done_fixture(cls._tmp / "d")
        # single: research skip marker resolves the gate, survey is the
        # whole frontier — one light doc node
        cls.single_dir = spec_only(cls._tmp / "e")
        write(cls.single_dir / "research.md",
              "not applicable — no open questions at Stage 0\n")
        # wave (execute span): approved + before-audit recorded, execute
        # is the frontier (T001 runnable; T002 dep-chained; T003 at cap)
        cls.execute_dir = approved_fixture(cls._tmp / "f", "demo")
        # wave (analysis fan-out): survey done + real research →
        # plan ∥ qa ∥ tech all READY (the GRAPH-002 shape)
        cls.analysis_dir = scaffold(cls._tmp / "g", "demo")
        write(cls.analysis_dir / "spec.md",
              (FIXTURE / "spec.md").read_text(encoding="utf-8"))
        write(cls.analysis_dir / "survey.md",
              (FIXTURE / "survey.md").read_text(encoding="utf-8"))
        write(cls.analysis_dir / "research.md",
              "## Research: demo\n\n### Q1 how to name the operation\n"
              "- **source**: https://example.com/naming — claim: plain "
              "names\n  relevance: direct · confidence: high\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def advisory(self, spec_dir):
        r = run_cli(spec_dir, "--launch-check")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_gate_weight_covers_every_pending_human_gate(self):
        for spec_dir, gate in (
                (self.gate_research, "research-gate"),
                (self.gate_clarify, "clarify"),
                (self.gate_before_audit, "before-audit"),
                (self.gate_closing, "closing-audit")):
            adv = self.advisory(spec_dir)
            self.assertEqual(adv["weight"], "gate", spec_dir)
            self.assertEqual(adv["gate"], gate)
            self.assertFalse(adv["launch_workflow"])
            self.assertEqual(adv["payloads"], 0)
            self.assertTrue(adv["reason"])

    def test_single_weight_for_one_light_doc_node(self):
        adv = self.advisory(self.single_dir)
        self.assertEqual(adv["weight"], "single")
        self.assertFalse(adv["launch_workflow"])
        self.assertEqual(adv["frontier_agents"], ["survey"])
        self.assertEqual(adv["payloads"], 1)
        self.assertIn("--emit-spawns", adv["reason"])

    def test_wave_weight_for_the_execute_span(self):
        adv = self.advisory(self.execute_dir)
        self.assertEqual(adv["weight"], "wave")
        self.assertTrue(adv["launch_workflow"])
        self.assertEqual(adv["frontier_agents"], ["execute"])
        # one runnable task (T001) — execute is heavy even as one payload
        self.assertEqual(adv["payloads"], 1)

    def test_wave_weight_for_the_analysis_fan_out(self):
        adv = self.advisory(self.analysis_dir)
        self.assertEqual(adv["weight"], "wave")
        self.assertTrue(adv["launch_workflow"])
        self.assertEqual(sorted(adv["frontier_agents"]),
                         ["plan", "qa", "tech"])
        self.assertEqual(adv["payloads"], 3)

    def test_held_and_complete_map_inline(self):
        st = compute(self.single_dir)
        st["frontier"] = []
        for name in st["nodes"]:
            st["nodes"][name]["state"] = (
                "done" if name == "spec" else "blocked")
        adv = graph.launch_check(st, self.single_dir, self.single_dir)
        self.assertEqual(adv["weight"], "held")
        self.assertFalse(adv["launch_workflow"])
        for name in st["nodes"]:
            st["nodes"][name]["state"] = "done"
        st["status"] = "done"  # else tick-commit is legitimately due
        adv = graph.launch_check(st, self.single_dir, self.single_dir)
        self.assertEqual(adv["weight"], "complete")
        self.assertFalse(adv["launch_workflow"])

    def test_json_shape_is_the_documented_contract(self):
        adv = self.advisory(self.execute_dir)
        self.assertEqual(set(adv), {"spec_dir", "launch_workflow", "gate",
                                    "frontier_agents", "payloads",
                                    "weight", "reason"})

    def test_pure_read_nothing_written(self):
        before = dir_checksum(self.execute_dir)
        self.advisory(self.execute_dir)
        self.assertEqual(dir_checksum(self.execute_dir), before)

    def test_mode_exclusivity(self):
        for flag in ("--state-json", "--emit-spawns", "--run"):
            self.assertEqual(
                run_cli(self.execute_dir, "--launch-check", flag).returncode,
                2, flag)


class Graph020PipelineShorteningTests(unittest.TestCase):
    """GRAPH-020: the 2.11.0 pipeline shortening — mechanical effort
    tiering (D-024), the one-stop before-audit contract + closing pre-check
    instruments (D-023), and the scaffold's skip-marker research default
    (D-025)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix="graph020-"))

        def analysis(tmp, effort):
            d = scaffold(tmp, "demo")
            write(d / "spec.md",
                  (FIXTURE / "spec.md").read_text(encoding="utf-8")
                  + f"\n**Effort**: {effort}\n")
            write(d / "survey.md",
                  (FIXTURE / "survey.md").read_text(encoding="utf-8"))
            write(d / "research.md",
                  "## Research: demo\n\n### Q1 how to name the operation\n"
                  "- **source**: https://example.com/naming — claim: plain "
                  "names\n  relevance: direct · confidence: high\n")
            return d

        cls.standard = analysis(cls._tmp / "a", "standard")
        cls.large = analysis(cls._tmp / "b", "large")
        cls.closing = copy_fixture(cls._tmp / "c")
        set_status(cls.closing, "approved")
        write(cls.closing / "task.md", IMPLEMENTED_ALL_TASKS)
        cls.before_audit = copy_fixture(cls._tmp / "e")
        cls.fresh = scaffold(cls._tmp / "d", "demo")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def payload_lines(self, spec_dir):
        r = run_cli(spec_dir, "--emit-spawns")
        self.assertEqual(r.returncode, 0, r.stderr)
        return [ln for ln in r.stdout.splitlines() if "   payload: " in ln]

    def test_state_json_carries_effort_with_large_default(self):
        self.assertEqual(compute(self.standard)["effort"], "standard")
        self.assertEqual(compute(self.large)["effort"], "large")
        # legacy docsets with no field keep the full-wave graph
        self.assertEqual(compute(self.closing)["effort"], "large")
        # a fresh scaffold reads the template's default: standard
        self.assertEqual(compute(self.fresh)["effort"], "standard")

    def test_standard_collapses_the_design_wave_into_one_payload(self):
        lines = self.payload_lines(self.standard)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("designer.md", lines[0])
        self.assertIn("role: designer", lines[0])
        self.assertIn("node: design", lines[0])
        text = next(self.standard.glob("spawns/*/designer.md")).read_text(
            encoding="utf-8")
        self.assertEqual(text.count("### agents/"), 4)
        self.assertEqual(text.count("## Shared protocol"), 1)
        self.assertIn("Tier: standard", text)

    def test_large_keeps_the_three_payload_design_wave(self):
        roles = sorted(ln.split("role: ")[1].split(",")[0]
                       for ln in self.payload_lines(self.large))
        self.assertEqual(roles, ["planner", "qa", "tech"])

    def test_closing_due_state_prepares_the_reviewer_payload(self):
        lines = self.payload_lines(self.closing)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("reviewer-diff.md", lines[0])
        self.assertIn("role: reviewer", lines[0])
        text = next(self.closing.glob("spawns/*/reviewer-diff.md")).read_text(
            encoding="utf-8")
        self.assertIn("implementation-diff", text)
        self.assertIn("closing audit step 10", text)
        # the reviewer is the one protocol-exempt role
        self.assertNotIn("## Shared protocol", text)

    def test_before_audit_pause_is_one_stop_with_preexecute(self):
        pause = graph.find_pause(compute(self.before_audit))
        self.assertIsNotNone(pause)
        self.assertEqual(pause[0], "before-audit")
        self.assertIn("ONE session", pause[1])
        self.assertIn("pre-execute", pause[1])
        self.assertIn("freeze.py", pause[1])

    def test_closing_pause_names_the_precheck_and_reviewer(self):
        pause = graph.find_pause(compute(self.closing))
        self.assertIsNotNone(pause)
        self.assertEqual(pause[0], "closing-audit")
        self.assertIn("mechanical pre-check", pause[1])
        self.assertIn("reviewer-diff.md", pause[1])

    def test_run_prints_the_prechecks_at_both_pauses(self):
        r = run_cli(self.before_audit, "--run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("before-audit precheck: audit.py pre-execute", r.stdout)
        self.assertIn("AWAITING HUMAN: before-audit", r.stdout)
        r = run_cli(self.closing, "--run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("closing precheck: audit.py scope", r.stdout)
        self.assertIn("closing precheck: audit.py dod --dry-run", r.stdout)
        self.assertIn("AWAITING HUMAN: closing-audit", r.stdout)

    def test_scaffold_ships_the_research_skip_marker(self):
        # its own scaffold — this test writes spec.md, and the shared
        # cls.fresh must stay pristine for the effort assertions
        fresh = scaffold(self._tmp / "f", "demo")
        self.assertEqual(
            (fresh / "research.md").read_text(encoding="utf-8").strip(),
            "not applicable — no open questions at Stage 0")
        write(fresh / "spec.md",
              (FIXTURE / "spec.md").read_text(encoding="utf-8"))
        st = compute(fresh)
        self.assertEqual(st["nodes"]["research-gate"]["state"], "done")
        self.assertIn("skip", st["nodes"]["research-gate"]["reason"])
        # no undetermined pause on a fresh authored spec: survey is the
        # frontier immediately
        self.assertIsNone(graph.find_pause(st))
        self.assertEqual(st["frontier"], ["survey"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
