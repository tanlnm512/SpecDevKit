"""The release gate: one command proving the release's evidence classes.

End-to-end lifecycle (FR-007's "end-to-end lifecycle evidence"): scaffold.sh
raises a fresh docset in a hermetic temp repo, this file fills it as a real
plan and drives it to the delivered v2 end state — implemented-and-ticked
tasks with proof notes, Before-audit / Closing-audit / Closing-evidence /
Delivered records —
then check.py must read it green and every specstate evidence reader must
recover the recorded lifecycle state from it.

Release surfaces (FR-007's alignment half, in service of FR-005's "a claim
ships only with a gate behind it"): tools/drift-check.py must find the live
tree's generated surfaces matching their canonical sources, and tools/
tests/test_manifests.py must pass version / changelog / manifest alignment.

Hermetic: fixture work happens only inside a tempdir; the live tree is
read, never written. Run: python3 tools/tests/test_release.py
"""
import importlib.util
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "spec-to-prod"
SCAFFOLD = SKILL / "scripts" / "scaffold.sh"
CHECK = SKILL / "scripts" / "check.py"
FREEZE = SKILL / "scripts" / "freeze.py"
DRIFT_CHECK = REPO_ROOT / "tools" / "drift-check.py"
TEST_MANIFESTS = REPO_ROOT / "tools" / "tests" / "test_manifests.py"

SPEC_NAME = "calc-lifecycle"

_spec = importlib.util.spec_from_file_location(
    "specstate", SKILL / "scripts" / "specstate.py")
specstate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(specstate)


def run_py(script: Path, *argv, cwd: Path | None = None,
           timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *argv],
                          capture_output=True, text=True,
                          timeout=timeout, cwd=cwd)


# The fixture plan's content. Deterministic (no clock reads, no randomness):
# a green gate must be reproducible byte for byte. The em dashes in the
# done notes and the research skip line are contract bytes — specstate's
# DONE_NOTE and RESEARCH_SKIP_MARKER read exactly those shapes.
TODAY = "2026-09-21"
BASELINE_SHA = "3fa2b1c"

CALC_PY = '''"""Tiny integer calculator: the module the delivered plan extends."""

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    if a == 0 or b == 0:
        return 0
    return a * b
'''

TEST_CALC_PY = '''"""The proof command the delivered plan's done notes cite."""
import unittest

from calc import multiply


class MultiplyTests(unittest.TestCase):
    def test_six_times_seven_is_forty_two(self):
        self.assertEqual(multiply(6, 7), 42)

    def test_zero_operand_is_zero(self):
        self.assertEqual(multiply(0, 5), 0)


if __name__ == "__main__":
    unittest.main()
'''

SPEC_MD = f'''# Spec: {SPEC_NAME}

**Status**: done
**Created**: {TODAY}
**Branch**: `feature/{SPEC_NAME}`

## What
Add integer multiplication to a tiny calculator module and carry the work
through the full versioned lifecycle: an approved spec, a planned and
implemented task set, mechanical and human audit records, and a delivery
record.

## Why
The lifecycle contract's evidence fields only mean something when one real
plan walks the whole path; this spec is that plan, small enough to verify
by eye.

## Business value
A delivered end-to-end plan proves the contract's records are writable and
mechanically readable, so future plans inherit a worked reference instead
of folklore.

## User stories
### US1 — Multiply two numbers (P1)
As a calculator user, I want to multiply two integers, so that products
need no repeated-addition workaround.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given the calculator module loaded, When I multiply 6 by 7, Then
  the result is 42.
- AC2: Given any operand is zero, When I multiply, Then the result is 0.

## Requirements
- **FR-001**: WHEN the user multiplies two integers, the system shall
  return their integer product.
- **FR-002**: IF either operand is zero, the system shall return 0 without
  special-casing at call sites.

## Scope
**In**: the multiply operation, its tests, and the lifecycle records that
carry it to delivery.
**Out (deferred)**: floating-point operands; division; CLI surface changes.

## Assumptions & risks
- Assumption: integers only — the module is integer-today and its tests
  pin that.
- Risk: a future expression parser needs operator precedence — mitigation:
  the operation stays a pure two-operand function.
'''

PLAN_MD = f'''# Plan: {SPEC_NAME}

**Spec**: [spec.md](spec.md) | **Created**: {TODAY}

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1     | Multiply lands | multiply(6, 7) returns 42 | FR-001, FR-002 | — |
| 2     | Lifecycle records | the delivered plan with audits and proof | — | Phase 1 |

## Dependencies
T002 consumes T001's multiply symbol; T003 runs only after both land and
their proof is green.

## Parallelization map
- Independent: `calc.py` ∥ `test_calc.py` — disjoint files, the tests pin
  the public surface only
- Strictly ordered: implementation → lifecycle records — the records cite
  the proof the implementation produced

## Checkpoints
- **After Phase 1**: `python3 test_calc.py` exits 0 with both multiply
  tests green
- **After Phase 2**: task.md carries Before-audit, Closing-audit, Closing-evidence, and
  Delivered records and check.py reads the docset green

## Risks & mitigations
- Risk: a recorded audit masks a red suite → mitigation: every Closing-audit
  record cites the exact proof command and its exit status.

## Delivery
One end-of-plan commit on `feature/{SPEC_NAME}`; in a repository without
git the Delivered record takes the `-` skip form. (ADR-001, tick-commit
node.)
'''

TECH_SPEC_MD = f'''# Tech Spec: {SPEC_NAME}

**Spec**: [spec.md](spec.md) | **Created**: {TODAY}
**Every file/symbol citation below must come verbatim from [survey.md](survey.md)
or a grep run in this session — never from memory.**

## Architecture
A single module exposes pure arithmetic; a unittest module pins the public
surface. survey.md's baseline pins the pre-multiply module at two
operations (add, subtract).

## Solution
### Chosen approach
Add one pure two-operand function beside the existing operations (covers
FR-001, FR-002), then walk the lifecycle: implement, prove, audit, record
delivery. research.md carries the skip record — no open questions at
Stage 0.

### Alternatives rejected
| Alternative | Why rejected |
|-------------|--------------|
| Operator-expression parser | Precedence machinery for one operation. |
| CLI flag before module surface | The module API is the demoable unit. |

## Impact analysis
The module gains one function; no existing caller changes — the survey
lists the test module as its only consumer.

## Code guide
### Arithmetic module
- Touches: `multiply` in `calc.py` (survey.md evidence)
- Approach: one pure function next to the existing operations
- Verify before implementing: `python3 test_calc.py`
- Pitfalls: keep it total — a zero operand returns 0 by the ordinary rule

### Lifecycle records
- Touches: the seven files under `specs/{SPEC_NAME}/`
- Approach: fill each contract file, record the audits, then tick once
- Verify before implementing: `check.py` green on the docset
- Pitfalls: never tick before the audit records exist

## References
- [survey.md](survey.md) — module baseline and evidence.
- The lifecycle contract: this repo consumes the spec-to-prod skill's
  templates verbatim via scaffold.sh.

## Decisions
### D-001: One pure function, no parser
- **Context**: FR-001 needs one arithmetic behavior, nothing more.
- **Decision**: add a single pure multiply function beside the existing
  operations.
- **Consequences**: no precedence machinery; future parsers compose it.
'''

TASK_MD = f'''# Tasks: {SPEC_NAME}

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Lifecycle**: v2
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ - — mechanical audit green on the finished plan
**Closing-audit**: approved @ - — human gates ruled green over the recorded proof
**Closing-evidence**: pending — replaced with the evidence-file digest
**Delivered**: commit @ - — the fixture repo keeps no git; the skip form records it

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1     | 2     | 2    |
| 2     | 1     | 1    |
| **Σ** | 3     | 3    |

## Phase 1: Multiply lands (FR-001)
<!-- Checkpoint: python3 test_calc.py exits 0 -->
- [x] T001 [P] Implement multiply in `calc.py` (implemented) (FR-001, FR-002)
  - done {TODAY} — python3 test_calc.py exits 0
- [x] T002 [P] Pin the multiply surface in `test_calc.py` (implemented) (FR-001, FR-002)
  - done {TODAY} — python3 test_calc.py exits 0

## Phase 2: Lifecycle records
<!-- Checkpoint: Before-audit, Closing-audit, Closing-evidence, and Delivered all recorded -->
- [x] T003 Record the audits and delivery for the finished plan (after T001, T002: consumes their recorded proof) (implemented) (FR-001, FR-002)
  - done {TODAY} — check.py green on specs/{SPEC_NAME}

## Conventions
- `(implemented)` marks landed work on the entry; the tick carries the
  `done <date> — <proof>` note
- `[P]` = parallelizable — disjoint files, no upstream; chained tasks name
  their upstream and what they consume
- Every task cites its FR-###; tasks with no FR are scope creep
'''

TEST_MD = f'''# Test Cases: {SPEC_NAME}

**Spec**: [spec.md](spec.md) | **Created**: {TODAY}
Black-box, business-language verification traced to requirements. Each case
has an observable pass condition. No implementation details.

## TC-001 — Multiply two integers
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** the calculator module loaded
- **When** a caller multiplies 6 by 7
- **Then** the result is 42
- **Pass condition**: `python3 test_calc.py` exits 0 with the product test
  green

## TC-002 — Zero operand multiplies to zero
- **Story**: US1 · **Traces to**: FR-002, AC2
- **Given** the calculator module loaded
- **When** a caller multiplies by zero
- **Then** the result is 0
- **Pass condition**: `python3 test_calc.py` exits 0 with the zero-operand
  test green

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001      | TC-001     | auto               |
| FR-002      | TC-002     | auto               |
'''

SURVEY_MD = f'''# Survey: {SPEC_NAME}

**Created**: {TODAY} | **Baseline**: v1 @ {BASELINE_SHA}
The survey node's output — the single source of truth for code state. Every
citation in the other four docs traces to a line here. Evidence is pasted
verbatim from grep/read output in the session that wrote it.

## Items

```
item 1: "calculator module lacks multiplication; add and subtract exist"
  evidence:   calc.py:multiply:9
  status:     DONE
  verify:     python3 test_calc.py
  gap:        none — both multiply tests green at delivery
```

## Supporting evidence
The module carries exactly three public operations at delivery: add,
subtract, multiply; the test module is its only consumer.

## Rules
- Every `file:line` pasted from grep/read in this survey — never from memory.
  Can't find it → write `unknown — verify`, don't guess.
- Status derives from evidence, not intent. Run every verify command.
- A number in an old doc is a claim, not evidence — re-count it.
'''

RESEARCH_MD = f'''# Research: {SPEC_NAME}

**Spec**: [spec.md](spec.md) | **Created**: {TODAY}

## Questions

not applicable — no open questions at Stage 0

## Options summary

None — the spec's single technical choice (one pure function beside the
existing operations) was settled by the survey evidence.
'''

CONSTITUTION_MD = '''# Constitution: calc-fixture

## Articles
- **C-01**: Every behavior lands with a test that proves it.
- **C-02**: Lifecycle evidence is recorded, never inferred.
- **C-03**: Generated files are regenerated, never hand-edited.

## Rationale
Proof over assertion: unproven behavior, inferred evidence, and hand-edited
generated files have each broken releases before these articles existed.
'''

INDEX_MD = (f"# Specs index\n"
            f"- [{SPEC_NAME}]({SPEC_NAME}/spec.md) — done (created {TODAY})\n")

CLOSING_EVIDENCE_MD = f'''# Closing evidence: {SPEC_NAME}

**Spec**: [spec.md](spec.md) | **Recorded**: {TODAY}
**Baseline**: non-git fixture

## Mechanical DoD
The fixture's two TCs and repository proof command exit 0; the mechanical
DoD scorecard is green.

## Manual test cases
- No MANUAL TCs in this fixture.

## Regression
`python3 test_calc.py` exits 0.

## Review findings
- Contract review: no BLOCK findings.
- Implementation diff review: no BLOCK findings.

## Rulings surfaced
- D-001 — one pure function; rejected parser machinery.

## Irreversible or state-mutating changes
- none

## User sign-off
Fixture approval recorded by the release-gate builder.
'''


def build_docset() -> tuple[Path, Path]:
    """Fresh repo via scaffold.sh, filled and driven to the delivered v2 end
    state: every contract file a real plan, tasks implemented and ticked
    with proof, all three lifecycle records written. Returns (tmp, repo);
    the caller owns removing tmp."""
    tmp = Path(tempfile.mkdtemp(prefix="release-gate-"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        r = subprocess.run(["bash", str(SCAFFOLD), SPEC_NAME, str(repo)],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise AssertionError(f"scaffold.sh failed: {r.stdout}{r.stderr}")
        spec_dir = repo / "specs" / SPEC_NAME
        for name, text in (("spec.md", SPEC_MD), ("plan.md", PLAN_MD),
                           ("tech-spec.md", TECH_SPEC_MD),
                           ("task.md", TASK_MD), ("test.md", TEST_MD),
                           ("survey.md", SURVEY_MD),
                           ("research.md", RESEARCH_MD)):
            (spec_dir / name).write_text(text, encoding="utf-8")
        (repo / "specs" / "CONSTITUTION.md").write_text(
            CONSTITUTION_MD, encoding="utf-8")
        (repo / "specs" / "context").mkdir()
        (repo / "specs" / "INDEX.md").write_text(INDEX_MD, encoding="utf-8")
        (repo / "calc.py").write_text(CALC_PY, encoding="utf-8")
        (repo / "test_calc.py").write_text(TEST_CALC_PY, encoding="utf-8")
        evidence = spec_dir / "evidence" / "closing.md"
        evidence.parent.mkdir()
        evidence.write_text(CLOSING_EVIDENCE_MD, encoding="utf-8")
        digest = hashlib.sha256(
            CLOSING_EVIDENCE_MD.encode("utf-8")
        ).hexdigest()
        task_path = spec_dir / "task.md"
        task_path.write_text(
            task_path.read_text(encoding="utf-8").replace(
                "**Closing-evidence**: pending — replaced with the evidence-file digest",
                f"**Closing-evidence**: sha256:{digest}",
            ),
            encoding="utf-8",
        )
        r = run_py(FREEZE, str(spec_dir), "--record", cwd=repo)
        if r.returncode != 0:
            raise AssertionError(f"freeze.py failed: {r.stdout}{r.stderr}")
        return tmp, repo
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


class DeliveredLifecycleTests(unittest.TestCase):
    """The whole v2 lifecycle, mechanically, on a scaffolded temp fixture:
    scaffold → fill → implement → prove → audit → deliver, judged only by
    check.py and specstate."""

    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.repo = build_docset()
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        cls.spec_dir = cls.repo / "specs" / SPEC_NAME

    def read(self, name: str) -> str:
        return (self.spec_dir / name).read_text(encoding="utf-8")

    def test_check_py_reads_the_delivered_docset_green(self):
        r = run_py(CHECK, str(self.spec_dir), cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS (0 fail, 0 warn)", r.stdout)

    def test_cited_proof_command_runs_green(self):
        r = subprocess.run([sys.executable, "test_calc.py"], cwd=self.repo,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_v2_lifecycle_header_present(self):
        self.assertIn("**Lifecycle**: v2", self.read("task.md"))

    def test_specstate_recovers_every_lifecycle_record(self):
        task = self.read("task.md")
        self.assertEqual(specstate.spec_status(self.read("spec.md")), "done")
        self.assertEqual(specstate.before_audit_state(task), "passed")
        self.assertEqual(specstate.closing_audit_state(task), "approved")
        self.assertEqual(specstate.delivery_state(task), ("delivered", "-"))

    def test_task_evidence_is_complete(self):
        entries = specstate.task_entries(self.read("task.md"))
        self.assertEqual([e.id for e in entries], ["T001", "T002", "T003"])
        for e in entries:
            self.assertTrue(e.done, e.id)
            self.assertTrue(e.implemented, e.id)
        ticks = specstate.tick_evidence(self.read("task.md"))
        self.assertEqual((ticks.total, ticks.ticked), (3, 3))
        self.assertEqual(ticks.unticked, [])
        self.assertEqual(ticks.noteless, [])

    def test_research_and_survey_records_parse(self):
        self.assertEqual(
            specstate.research_state(self.spec_dir / "research.md"), "skip")
        self.assertEqual(
            specstate.survey_baseline(self.read("survey.md")),
            ("v1", BASELINE_SHA))
        items = specstate.survey_items(self.read("survey.md"))
        self.assertEqual([(i.id, i.status) for i in items], [("1", "DONE")])


class ReleaseGateTests(unittest.TestCase):
    """The aggregate: the one command RELEASE.md names must cover the
    release's mechanical surfaces — generated artifacts against canonical
    sources, and version / changelog / manifest alignment."""

    def test_generated_surfaces_match_canonical_sources(self):
        r = run_py(DRIFT_CHECK)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("drift check: OK", r.stdout)

    def test_version_changelog_manifest_alignment(self):
        r = run_py(TEST_MANIFESTS)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_release_checklist_names_the_gate(self):
        self.assertIn("python3 tools/tests/test_release.py",
                      (REPO_ROOT / "RELEASE.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
