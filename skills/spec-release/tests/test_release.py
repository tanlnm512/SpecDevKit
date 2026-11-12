#!/usr/bin/env python3
"""Unit tests for spec-release's release.py, driven at its command line.

Real temp git repos, a bare local disk remote for pushes, no gh on PATH
except where a stub provides canned output. Every assertion keys on the
exit code and the line a model acts on (the row, the plan step, the
record line). check.py integration: the Released record must leave both
tiers green.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RELEASE = REPO_ROOT / "skills" / "spec-release" / "scripts" / "release.py"
CHECK = REPO_ROOT / "skills" / "spec-design" / "scripts" / "check.py"
FREEZE = REPO_ROOT / "skills" / "spec-design" / "scripts" / "freeze.py"

_freeze_spec = importlib.util.spec_from_file_location("freeze", FREEZE)
freeze = importlib.util.module_from_spec(_freeze_spec)
_freeze_spec.loader.exec_module(freeze)

TODAY = "2026-01-15"

CALC_PY = '''"""Tiny integer calculator: the module the delivered specs extend."""

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    if a == 0 or b == 0:
        return 0
    return a * b
'''

TEST_CALC_PY = '''"""The proof command the delivered plans' done notes cite."""
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


def tiny_spec(name: str, sha: str, smoke: bool = False) -> str:
    tasks = f"""## Tasks
- [x] T001 Multiply lands (FR-001) [P]
  Touches: `calc.py`
  Accept: `python3 -m unittest test_calc` exits 0
  done {TODAY} — `python3 -m unittest test_calc` green (2 tests)
- [x] T002 Non-integer input errors cleanly (FR-002) [P]
  Touches: `calc.py`
  Accept: `python3 calc.py multiply 6 x` exits nonzero
  done {TODAY} — `python3 calc.py multiply 6 x` exits 1"""
    if smoke:
        tasks += f"""
- [x] T003 Smoke the delivered CLI (FR-001) [P]
  Touches: `calc.py`
  Accept: `python3 calc.py multiply 6 7` prints 42
  done {TODAY} — `python3 calc.py multiply 6 7` prints 42"""
    return f"""# Spec: {name}

**Status**: done
**Tier**: tiny
**Effort**: standard
**Created**: {TODAY}
**Baseline**: {name} v1 @ {sha}

A delivered one-file contract: the task list lives in § Tasks, ticked
and proven, the delivery record written.

## What
The calculator gains integer multiplication through the module surface.

## Why
Products otherwise need a repeated-addition workaround at every call site.

## User stories
### US1 — Multiply two numbers (P1)
As a calculator user, I want to multiply two integers, so that products
need no workaround.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given two integers, When I run multiply, Then the product prints
  and the command exits 0.
- AC2: Given non-integer input, When I run multiply, Then a one-line
  error prints and the command exits nonzero.

## Requirements
- **FR-001**: The system shall multiply two integers and print the
  product.
- **FR-002**: WHEN either argument is not an integer, the system shall
  print a one-line error and exit nonzero.

{tasks}

Delivered: commit @ {sha}
"""


def full_spec(name: str, sha: str) -> dict[str, str]:
    spec_md = f"""# Spec: {name}

**Status**: done
**Type**: feature
**Created**: {TODAY}
**Branch**: `feature/{name}`

## What
Add integer multiplication to a tiny calculator module and carry the
work through the full versioned lifecycle to a delivered plan.

## Why
The lifecycle contract's evidence fields only mean something when one
real plan walks the whole path; this spec is that plan.

## Business value
A delivered end-to-end plan proves the contract's records are writable
and mechanically readable, so future plans inherit a worked reference.

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
- **FR-002**: IF either operand is zero, the system shall return 0
  without special-casing at call sites.

## Quality attributes
- **NFR-001**: Security, Privacy, Performance, Reliability, Observability,
  Accessibility — not applicable: a pure in-process integer function with
  no input boundary, stored data, I/O, failure mode, signal, or interface
  beyond its two operands.

## Scope
**In**: the multiply operation, its tests, and the lifecycle records.
**Out (deferred)**: floating-point operands; division; CLI surface changes.

## Assumptions & risks
- Assumption: integers only — the module is integer-today and its tests
  pin that.
- Risk: a future expression parser needs operator precedence — mitigation:
  the operation stays a pure two-operand function.
"""
    plan_md = f"""# Plan: {name}

**Spec**: [spec.md](spec.md) | **Created**: {TODAY}

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1     | Multiply lands | multiply(6, 7) returns 42 | FR-001, FR-002 | — |

## Dependencies
T002 consumes T001's multiply symbol; T003 runs only after both land.

## Parallelization map
- Independent: `calc.py` ∥ `test_calc.py` — disjoint files, the tests pin
  the public surface only
- Strictly ordered: implementation → lifecycle records

## Checkpoints
- **After Phase 1**: `python3 test_calc.py` exits 0 with both multiply
  tests green

## Risks & mitigations
- Risk: a tick masks a red suite → mitigation: every done note cites the
  exact proof command and its exit status.

## Delivery
One end-of-plan commit on `feature/{name}`.

### Rollout
- **Exposure**: the module surface only — no callers outside its tests.
- **Post-release check**: `python3 test_calc.py` green on the tagged commit.
"""
    tech_md = f"""# Tech Spec: {name}

**Spec**: [spec.md](spec.md) | **Created**: {TODAY}
**Every file/symbol citation below must come verbatim from [survey.md](survey.md)
or a grep run in this session — never from memory.**

## Architecture
A single module exposes pure arithmetic; a unittest module pins the public
surface.

## Solution
### Chosen approach
Add one pure two-operand function beside the existing operations (covers
FR-001, FR-002).

### Alternatives rejected
| Alternative | Why rejected |
|-------------|--------------|
| Operator-expression parser | Precedence machinery for one operation. |

## Impact analysis
The module gains one function; no existing caller changes — the survey
lists the test module as its only consumer.

## Interfaces & data
- **Interfaces**: one new public function, multiply, taking the same two
  integer operands as add and subtract; existing signatures are unchanged.
- **Data and migrations**: none — the module stores nothing.
- **Compatibility**: additive; no existing caller changes.

## Code guide
### Arithmetic module
- Touches: `multiply` in `calc.py` (survey.md evidence)
- Approach: one pure function next to the existing operations
- Verify before implementing: `python3 test_calc.py`
- Pitfalls: keep it total — a zero operand returns 0 by the ordinary rule

## References
- [survey.md](survey.md) — module baseline and evidence.

## Decisions
### D-001: One pure function, no parser
- **Context**: FR-001 needs one arithmetic behavior, nothing more.
- **Decision**: add a single pure multiply function beside the existing
  operations.
- **Consequences**: no precedence machinery; future parsers compose it.
"""
    task_md = f"""# Tasks: {name}

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Lifecycle**: v2
Status reflects code state per [survey.md](survey.md), not intent.
**Delivered**: commit @ {sha}

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
<!-- Checkpoint: the Delivered record is written and check.py reads green -->
- [x] T003 Record the delivery for the finished plan (after T001, T002) (implemented) (FR-001, FR-002)
  - done {TODAY} — check.py green on specs/{name}

## Conventions
- `(implemented)` marks landed work on the entry; the tick carries the
  `done <date> — <proof>` note
"""
    test_md = f"""# Test Cases: {name}

**Spec**: [spec.md](spec.md) | **Created**: {TODAY}
Black-box, business-language verification traced to requirements.

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
"""
    survey_md = f"""# Survey: {name}

**Created**: {TODAY} | **Baseline**: v1 @ {sha}
The survey node's output — the single source of truth for code state.

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
- Status derives from evidence, not intent. Run every verify command.
"""
    research_md = f"""# Research: {name}

**Spec**: [spec.md](spec.md) | **Created**: {TODAY}

## Questions

not applicable — no open questions at Stage 0

## Options summary

None — the spec's single technical choice (one pure function beside the
existing operations) was settled by the survey evidence.
"""
    delivery_md = ("# Delivery\n\n"
                   "Rollback: revert the release commit — the module is\n"
                   "additive and nothing outside its tests calls it.\n")
    return {"spec.md": spec_md, "plan.md": plan_md, "tech-spec.md": tech_md,
            "task.md": task_md, "test.md": test_md, "survey.md": survey_md,
            "research.md": research_md,
            "notes/delivery.md": delivery_md}


CONSTITUTION_MD = """# Constitution: release-fixture

## Articles
- **C-01**: Every behavior lands with a test that proves it.
- **C-02**: Lifecycle evidence is recorded, never inferred.

## Rationale
Proof over assertion: unproven behavior and inferred evidence have each
broken releases before these articles existed.
"""


# --- harness ----------------------------------------------------------------

def git(repo: Path, *args, stdin: str | None = None, check: bool = True):
    r = subprocess.run(["git", "-C", str(repo), *args], input=stdin,
                       capture_output=True, text=True)
    if check:
        assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r


_BIN: str | None = None


def _git_bindir() -> str:
    """A private bin dir exposing only git: gh can sit beside git on some
    runners, so gh-absence needs a PATH holding nothing else."""
    global _BIN
    if _BIN is None:
        _BIN = tempfile.mkdtemp(prefix="rel-bin-")
        (Path(_BIN) / "git").symlink_to(Path(shutil.which("git")).resolve())
    return _BIN


def env_no_gh() -> dict:
    return {**os.environ, "PATH": _git_bindir()}


@contextmanager
def gh_stub(stdout: str):
    bindir = tempfile.mkdtemp(prefix="gh-stub-")
    gh = Path(bindir) / "gh"
    gh.write_text(f"#!/bin/sh\necho '{stdout}'\n")
    gh.chmod(0o755)
    (Path(bindir) / "git").symlink_to(Path(shutil.which("git")).resolve())
    try:
        yield {**os.environ, "PATH": bindir}
    finally:
        shutil.rmtree(bindir, ignore_errors=True)


def rel(repo: Path, *argv, env=None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(RELEASE), *argv],
                          capture_output=True, text=True, timeout=120,
                          cwd=repo, env=env or env_no_gh())


def add_specs(repo: Path, specs: dict) -> None:
    lines = []
    for name, files in specs.items():
        for rel_path, text in files.items():
            path = repo / "specs" / name / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        tier = "tiny" if "**Tier**: tiny" in files["spec.md"] else "full"
        lines.append(f"- [{name}]({name}/spec.md) — done · feature · {tier}\n")
        approvals = repo / "specs" / name / "approvals"
        approvals.mkdir(exist_ok=True)
        (approvals / "review.md").write_text(
            "# Contract review\n\nDocset fingerprint: "
            f"{freeze.docset_fingerprint(repo / 'specs' / name)}\n\n"
            "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none\n",
            encoding="utf-8")
        r = subprocess.run([sys.executable, str(FREEZE),
                            str(repo / "specs" / name), "--record"],
                           capture_output=True, text=True, cwd=repo)
        assert r.returncode == 0, f"freeze --record: {r.stdout}{r.stderr}"
    index = repo / "specs" / "INDEX.md"
    if index.is_file():
        index.write_text(index.read_text(encoding="utf-8") + "".join(lines),
                         encoding="utf-8")
    else:
        index.parent.mkdir(exist_ok=True)
        index.write_text("# Specs index\n" + "".join(lines), encoding="utf-8")
    constitution = repo / "specs" / "CONSTITUTION.md"
    if not constitution.is_file():
        constitution.write_text(CONSTITUTION_MD, encoding="utf-8")


def make_repo(specs=None, outside: int = 0, tag: str | None = None,
              remote: bool = False) -> tuple[Path, str]:
    """A pinned temp repo: calculator code on the base commit, an optional
    tag on it, optional delivered specs (specs may be a callable taking the
    base short sha), optional outside commits, optional bare remote.
    Returns (repo, base_short_sha)."""
    tmp = Path(tempfile.mkdtemp(prefix="rel-suite-"))
    repo = tmp / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    for key, value in (("user.name", "tester"), ("user.email", "t@example.com"),
                       ("commit.gpgsign", "false"), ("tag.gpgsign", "false"),
                       ("tag.forceSignAnnotated", "false"),
                       ("diff.noprefix", "false"), ("diff.mnemonicPrefix", "false")):
        git(repo, "config", key, value)
    if tag:
        git(repo, "commit", "--allow-empty", "-qm", "chore: before the last release")
        git(repo, "tag", "-a", tag, "-m", tag)
    (repo / "calc.py").write_text(CALC_PY, encoding="utf-8")
    (repo / "test_calc.py").write_text(TEST_CALC_PY, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "feat: calculator module")
    base = git(repo, "rev-parse", "HEAD").stdout.strip()[:12]
    if callable(specs):
        specs = specs(base)
    if specs:
        add_specs(repo, specs)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: delivered specs")
    for i in range(outside):
        (repo / f"README-{i}.md").write_text(f"# notes {i}\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", f"docs: outside note {i}")
    if remote:
        git(tmp, "init", "--bare", "-b", "main", "remote.git")
        git(repo, "remote", "add", "origin", str(tmp / "remote.git"))
        git(repo, "push", "-u", "origin", "main")
    return repo, base


def delivered_specs(*names: str, tiny: bool = False, smoke: bool = False,
                    sha: str = ""):
    if not sha:
        raise ValueError("pass the repo's real base sha — a delivery record "
                         "that git cannot resolve reads as unreachable")
    out = {}
    for name in names:
        if tiny:
            out[name] = {"spec.md": tiny_spec(name, sha, smoke=smoke)}
        else:
            out[name] = full_spec(name, sha)
    return out


def cut_release(repo: Path, version: str = "0.1.0") -> str:
    tag = f"v{version}"
    r = rel(repo, "notes", version, "--write")
    if r.returncode != 0:
        assert "already has a" in r.stderr, r.stdout + r.stderr
    r = rel(repo, "cut", version, "--confirm", tag)
    assert r.returncode == 0, r.stdout + r.stderr
    return tag


class CollectTests(unittest.TestCase):
    def test_first_release_collects_specs_and_outside_commits(self):
        repo, base = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha),
            outside=1)
        r = rel(repo, "collect")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("range: HEAD (last tag: none)", r.stdout)
        self.assertIn(f"spec  tiny-rel — feature · delivered @ {base}", r.stdout)
        self.assertIn("outside the spec flow: 1 commit(s)", r.stdout)
        self.assertIn("first release", r.stdout)

    def test_collect_without_specs_says_nothing_to_release(self):
        tmp = Path(tempfile.mkdtemp(prefix="rel-empty-"))
        repo = tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-b", "main")
        git(repo, "config", "user.name", "tester")
        git(repo, "config", "user.email", "t@example.com")
        git(repo, "commit", "--allow-empty", "-qm", "chore(release): v0.0.1")
        r = rel(repo, "collect")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("nothing to release", r.stdout)
        self.assertIn("no specs/ dir", r.stdout)

    def test_second_release_excludes_released_and_ranges_since_tag(self):
        def specs(sha):
            out = delivered_specs("tiny-rel", tiny=True, sha=sha)
            out["tiny-rel"]["spec.md"] = out["tiny-rel"]["spec.md"].replace(
                f"Delivered: commit @ {sha}",
                f"Delivered: commit @ {sha}\nReleased: v0.9.0 @ {sha}")
            return out
        repo, _ = make_repo(specs)
        git(repo, "tag", "-a", "v0.9.0", "-m", "v0.9.0")
        (repo / "README-0.md").write_text("# notes\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "docs: outside note")
        r = rel(repo, "collect")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("range: v0.9.0..HEAD", r.stdout)
        self.assertNotIn("spec  tiny-rel", r.stdout)
        self.assertIn("outside the spec flow: 1 commit(s)", r.stdout)

    def test_archived_delivered_spec_is_included(self):
        repo, base = make_repo()
        archive = repo / "specs" / "archive" / f"{TODAY}-old-calc"
        archive.mkdir(parents=True)
        (archive / "spec.md").write_text(
            tiny_spec("old-calc", base), encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: archive old-calc")
        r = rel(repo, "collect")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"spec  old-calc — feature · delivered @ {base}", r.stdout)
        self.assertIn("· archived", r.stdout)

    def test_unreachable_delivery_record_fails_collect(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha="deadbee000"))
        r = rel(repo, "collect")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("FAIL  tiny-rel: Delivered @ deadbee000 is not reachable",
                      r.stdout)

    def test_in_flight_spec_warns(self):
        repo, base = make_repo()
        spec_dir = repo / "specs" / "wip-rel"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(
            tiny_spec("wip-rel", base)
            .replace("**Status**: done", "**Status**: active")
            .replace(f"Delivered: commit @ {base}\n", ""),
            encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat(wip-rel): start the spec")
        r = rel(repo, "collect")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("WARN  wip-rel: not delivered, yet 1 commit(s)", r.stdout)

    def test_untraceable_spec_is_listed_never_included(self):
        def specs(sha):
            out = delivered_specs("tiny-rel", tiny=True, sha=sha)
            out["tiny-rel"]["spec.md"] = out["tiny-rel"]["spec.md"].replace(
                f"Delivered: commit @ {sha}", "Delivered: commit @ -")
            return out
        repo, _ = make_repo(specs)
        r = rel(repo, "collect")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("WARN  tiny-rel: delivered without git", r.stdout)
        self.assertNotIn("spec  tiny-rel", r.stdout)

    def test_several_tag_families_are_named_and_ruled(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha),
            outside=1)
        git(repo, "commit", "--allow-empty", "-qm", "docs: bump work")
        git(repo, "tag", "-a", "v0.9.0", "-m", "v0.9.0", "HEAD~1")
        git(repo, "commit", "--allow-empty", "-qm", "docs: more work")
        git(repo, "tag", "-a", "pkg-v0.9.0", "-m", "pkg-v0.9.0", "HEAD~1")
        r = rel(repo, "collect")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("several tag families", r.stdout)
        self.assertIn("using 'pkg-v'", r.stdout)
        r = rel(repo, "collect", "--tag-prefix", "v")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("range: v0.9.0..HEAD", r.stdout)


class VersionTests(unittest.TestCase):
    def propose(self, specs=None, outside=(), tag=None, existing=None) -> dict:
        repo, base = make_repo(tag=tag)
        if specs is None:
            specs = delivered_specs("tiny-rel", tiny=True, sha=base)
        elif callable(specs):
            specs = specs(base)
        if specs:
            add_specs(repo, specs)
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "feat: delivered specs")
        if existing:
            for name, text in existing.items():
                (repo / name).write_text(text, encoding="utf-8")
            git(repo, "add", "-A")
        for subject in outside:
            git(repo, "commit", "--allow-empty", "-qm", subject)
        r = rel(repo, "version", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout)

    def test_feature_spec_proposes_minor(self):
        d = self.propose(lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        self.assertEqual(d["level"], "minor")
        self.assertIn("feature spec tiny-rel", " ".join(d["reasons"]))

    def test_bugfix_spec_proposes_patch(self):
        def specs(sha):
            out = delivered_specs("tiny-rel", tiny=True, sha=sha)
            out["tiny-rel"]["spec.md"] = out["tiny-rel"]["spec.md"].replace(
                "**Status**: done", "**Status**: done\n**Type**: bugfix")
            return out
        d = self.propose(specs)
        self.assertEqual(d["level"], "patch")

    def test_breaking_marker_proposes_major(self):
        def specs(sha):
            out = delivered_specs("tiny-rel", tiny=True, sha=sha)
            out["tiny-rel"]["spec.md"] = out["tiny-rel"]["spec.md"].replace(
                "## What", "**Breaking**: the multiply signature changes.\n\n## What")
            return out
        d = self.propose(specs)
        self.assertEqual(d["level"], "major")
        self.assertTrue(d["tag"].startswith("v"))

    def test_pre_1_0_breaking_bumps_minor_with_the_semver_note(self):
        def specs(sha):
            out = delivered_specs("tiny-rel", tiny=True, sha=sha)
            out["tiny-rel"]["spec.md"] = out["tiny-rel"]["spec.md"].replace(
                "## What", "**Breaking**: the multiply signature changes.\n\n## What")
            return out
        d = self.propose(specs, tag="v0.3.0")
        self.assertEqual(d["level"], "major")
        self.assertEqual(d["effective_level"], "minor")
        self.assertIn("pre-1.0", " ".join(d["notes"]))
        self.assertEqual(d["proposed"], "0.4.0")

    def test_outside_feat_commit_proposes_minor_and_bang_major(self):
        d = self.propose(specs={}, outside=["feat: grow the api"])
        self.assertEqual(d["level"], "minor")
        d = self.propose(specs={}, outside=["feat!: change the api"])
        self.assertEqual(d["level"], "major")

    def test_pre_release_tag_proposes_its_final_version(self):
        d = self.propose(specs={}, tag="v1.2.0-rc.1")
        self.assertEqual(d["proposed"], "1.2.0")
        self.assertIn("pre-release", " ".join(d["notes"]))

    def test_no_tag_proposes_the_written_version(self):
        d = self.propose(specs={}, existing={"VERSION": "1.4.2\n"})
        self.assertEqual(d["proposed"], "1.4.2")
        self.assertIn("already written", " ".join(d["notes"]))

    def test_every_version_source_is_listed(self):
        repo, _ = make_repo()
        (repo / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        (repo / "package.json").write_text(
            '{\n  "name": "x",\n  "version": "0.1.0"\n}\n', encoding="utf-8")
        (repo / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0.1.0"\n',
                                             encoding="utf-8")
        pkg = repo / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: version files")
        r = rel(repo, "version", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        files = {s["file"] for s in json.loads(r.stdout)["sources"]}
        self.assertEqual(files, {"VERSION", "package.json", "pyproject.toml",
                                 "pkg/__init__.py"})


class BumpTests(unittest.TestCase):
    def test_dry_run_writes_nothing_and_write_updates_every_source(self):
        repo, _ = make_repo()
        (repo / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        (repo / "package.json").write_text(
            '{\n  "name": "x",\n  "version": "0.1.0"\n}\n', encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: version files")
        r = rel(repo, "bump", "1.2.3")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("(dry run)", r.stdout)
        self.assertEqual((repo / "VERSION").read_text(), "0.1.0\n")
        r = rel(repo, "bump", "1.2.3", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((repo / "VERSION").read_text(), "1.2.3\n")
        self.assertIn('"version": "1.2.3"', (repo / "package.json").read_text())

    def test_dirty_tree_refuses_the_write(self):
        repo, _ = make_repo()
        (repo / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: version file")
        (repo / "README.md").write_text("# stray\n", encoding="utf-8")
        r = rel(repo, "bump", "1.2.3", "--write")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("dirty outside the release files", r.stderr)
        self.assertEqual((repo / "VERSION").read_text(), "0.1.0\n")

    def test_only_limits_the_files_written(self):
        repo, _ = make_repo()
        (repo / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        (repo / "package.json").write_text(
            '{\n  "name": "x",\n  "version": "0.1.0"\n}\n', encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: version files")
        r = rel(repo, "bump", "1.2.3", "--write", "--only", "VERSION")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((repo / "VERSION").read_text(), "1.2.3\n")
        self.assertIn('"version": "0.1.0"', (repo / "package.json").read_text())


CHANGELOG = """# Changelog

## [Unreleased]
### Fixed
- hand-written fix note

## [0.9.0] - 2026-01-01
### Added
- the first thing (old-spec)

[Unreleased]: https://github.com/o/r/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/o/r/compare/v0.8.0...v0.9.0
"""


class NotesTests(unittest.TestCase):
    def test_write_creates_changelog_from_template_when_absent(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        r = rel(repo, "notes", "0.1.0", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [0.1.0]", text)
        self.assertIn("(tiny-rel)", text)
        self.assertIn("Unreleased", text)

    def test_write_merges_unreleased_and_rewrites_the_footer(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha),
            tag="v0.9.0")
        (repo / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
        r = rel(repo, "notes", "1.0.0", "--write", "--date", "2026-02-02")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("moved 2 Unreleased line(s)", r.stdout)
        text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [1.0.0] - 2026-02-02", text)
        self.assertIn("hand-written fix note", text)
        self.assertIn("[Unreleased]: https://github.com/o/r/compare/v1.0.0...HEAD",
                      text)
        self.assertIn("[1.0.0]: https://github.com/o/r/compare/v0.9.0...v1.0.0",
                      text)

    def test_write_refuses_an_existing_section(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        (repo / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [0.1.0] - 2026-01-01\n- old\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "docs: changelog")
        r = rel(repo, "notes", "0.1.0", "--write")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("already has a 0.1.0 section", r.stderr)

    def test_check_passes_on_the_generated_section_and_fails_on_edits(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        self.assertEqual(rel(repo, "notes", "0.1.0", "--write").returncode, 0)
        r = rel(repo, "notes", "0.1.0", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)
        text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        (repo / "CHANGELOG.md").write_text(
            text.replace("(tiny-rel)", "(other-spec)"), encoding="utf-8")
        r = rel(repo, "notes", "0.1.0", "--check")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("FAIL  changelog", r.stdout)
        self.assertIn("but not in the section", r.stdout)

    def test_body_renders_the_release_notes(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        self.assertEqual(rel(repo, "notes", "0.1.0", "--write").returncode, 0)
        r = rel(repo, "notes", "0.1.0", "--body")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Delivered specs in v0.1.0", r.stdout)
        self.assertIn("tiny-rel — delivered @", r.stdout)

    def test_hotfix_groups_under_its_declared_lineage(self):
        def specs(sha):
            out = delivered_specs("tiny-rel", tiny=True, sha=sha)
            out["crash-fix"] = {"spec.md": tiny_spec("crash-fix", sha).replace(
                "**Tier**: tiny",
                "**Tier**: tiny\n**Type**: hotfix"
                "\n**Hotfix for**: v1.2.2\n**Fixes spec**: tiny-rel")}
            return out
        repo, _ = make_repo(specs, tag="v1.2.2")
        r = rel(repo, "notes", "1.2.3", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("(crash-fix) — patches v1.2.2 — fixes tiny-rel", text)
        r = rel(repo, "notes", "1.2.3", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class PreflightTests(unittest.TestCase):
    def green(self, specs=None) -> tuple[Path, str]:
        repo, base = make_repo()
        if callable(specs):
            specs = specs(base)
        if specs:
            add_specs(repo, specs)
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "feat: delivered specs")
        r = rel(repo, "notes", "0.1.0", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return repo, "0.1.0"

    def test_green_gate_names_every_row_and_exits_zero(self):
        repo, version = self.green(
            lambda sha: delivered_specs("calc-flow", sha=sha))
        r = rel(repo, "preflight", version)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS  tree", r.stdout)
        self.assertIn("PASS  branch", r.stdout)
        self.assertIn("SKIP  ci", r.stdout)
        self.assertIn("PASS  changelog", r.stdout)
        self.assertIn("rollback path stated", r.stdout)
        self.assertTrue(r.stdout.rstrip().endswith("PASS"), r.stdout)

    def red_case(self, repo: Path, version: str, line: str):
        r = rel(repo, "preflight", version)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(line, r.stdout)

    def test_red_rows_stop_the_gate(self):
        repo, version = self.green(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        (repo / "README.md").write_text("# stray\n", encoding="utf-8")
        self.red_case(repo, version, "FAIL  tree")
        (repo / "README.md").unlink()
        git(repo, "checkout", "-qb", "feature/elsewhere")
        self.red_case(repo, version, "FAIL  branch")
        git(repo, "checkout", "-q", "main")
        git(repo, "branch", "-q", "-D", "feature/elsewhere")
        git(repo, "tag", "-a", f"v{version}", "-m", "taken")
        self.red_case(repo, version, "already exists")
        git(repo, "tag", "-d", f"v{version}")
        (repo / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        self.red_case(repo, version, f"not yet {version}")
        (repo / "VERSION").unlink()
        text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        (repo / "CHANGELOG.md").write_text(
            text.replace("(tiny-rel)", "(elsewhere)"), encoding="utf-8")
        self.red_case(repo, version, "FAIL  changelog")
        (repo / "CHANGELOG.md").write_text(text, encoding="utf-8")
        ghost = repo / "specs" / "ghost"
        ghost.mkdir()
        (ghost / "spec.md").write_text(
            tiny_spec("ghost", "deadbee000"), encoding="utf-8")
        self.red_case(repo, version, "not reachable from HEAD")

    def test_ci_rows_read_a_stubbed_gh(self):
        repo, version = self.green()
        runs = {
            "green": '[{"name":"validate","status":"completed","conclusion":"success"}]',
            "red": '[{"name":"validate","status":"completed","conclusion":"failure"}]',
            "pending": '[{"name":"validate","status":"in_progress","conclusion":null}]',
            "none": "[]",
        }
        expected = {"green": ("PASS  ci", 0), "red": ("FAIL  ci", 1),
                    "pending": ("FAIL  ci", 1), "none": ("WARN  ci", 0)}
        for name, canned in runs.items():
            with self.subTest(case=name):
                with gh_stub(canned) as env:
                    r = rel(repo, "preflight", version, env=env)
                want = expected[name][1]
                self.assertEqual(r.returncode, want,
                                 f"{name}: {r.stdout}{r.stderr}")
                self.assertIn(expected[name][0], r.stdout)

    def test_rollback_row_needs_a_stated_path(self):
        def specs(sha):
            out = delivered_specs("calc-flow", sha=sha)
            out["calc-flow"]["notes/delivery.md"] = "# Delivery\n\nno note here\n"
            return out
        repo, version = self.green(specs)
        r = rel(repo, "preflight", version)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("no rollback path is stated", r.stdout)
        (repo / "specs" / "calc-flow" / "notes" / "delivery.md").write_text(
            "# Delivery\n\nRollback: revert the release commit.\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "docs: state the rollback")
        r = rel(repo, "preflight", version)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("rollback path stated", r.stdout)

    def test_must_fix_backlog_item_needs_a_ruling_or_known_issues(self):
        repo, version = self.green(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        (repo / "specs" / "BACKLOG.md").write_text(
            "- tiny-rel — must-fix: division rounds wrong (source: QA review)\n",
            encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "docs: park the must-fix item")
        r = rel(repo, "preflight", version)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("needs a ruling", r.stdout)
        text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        (repo / "CHANGELOG.md").write_text(
            text + "\n### Known issues\n\n- must-fix: division rounds wrong\n",
            encoding="utf-8")
        r = rel(repo, "preflight", version)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ruled ship-with", r.stdout)


class CutTests(unittest.TestCase):
    def test_plan_shows_the_steps_and_writes_nothing(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        r = rel(repo, "cut", "0.1.0")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("cut plan for v0.1.0 (local only", r.stdout)
        self.assertIn("(nothing — bump and notes not written yet)", r.stdout)
        self.assertEqual(git(repo, "rev-list", "--count", "HEAD").stdout.strip(), "2")
        self.assertNotEqual(git(repo, "rev-parse", "-q", "--verify",
                                "refs/tags/v0.1.0", check=False).returncode, 0)

    def test_confirm_mismatch_and_red_gate_refuse(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        r = rel(repo, "cut", "0.1.0", "--confirm", "v9.9.9")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("does not match the planned tag", r.stderr)
        r = rel(repo, "cut", "0.1.0", "--confirm", "v0.1.0")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("refused: the gate is red — nothing was written", r.stdout)
        self.assertNotEqual(git(repo, "rev-parse", "-q", "--verify",
                                "refs/tags/v0.1.0", check=False).returncode, 0)

    def test_confirmed_cut_commits_tags_and_records_both_tiers_green(self):
        repo, base = make_repo(
            lambda sha: delivered_specs("calc-flow", sha=sha))
        add_specs(repo, delivered_specs("tiny-rel", tiny=True, smoke=True,
                                        sha=base))
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: add the tiny spec")
        r = rel(repo, "notes", "0.1.0", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = rel(repo, "cut", "0.1.0", "--confirm", "v0.1.0")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("committed", r.stdout)
        self.assertIn("recorded Released on 2 spec(s)", r.stdout)
        self.assertEqual(git(repo, "rev-parse", "-q", "--verify",
                             "refs/tags/v0.1.0", check=False).returncode, 0)
        release_subject = git(repo, "log", "-1", "--format=%s",
                              "refs/tags/v0.1.0").stdout.strip()
        self.assertTrue(release_subject.startswith("chore(release): v0.1.0"))
        full_task = (repo / "specs" / "calc-flow" / "task.md").read_text(encoding="utf-8")
        self.assertIn("**Released**: v0.1.0 @", full_task)
        self.assertLess(full_task.index("**Delivered**"),
                        full_task.index("**Released**"))
        tiny_spec_md = (repo / "specs" / "tiny-rel" / "spec.md").read_text(encoding="utf-8")
        self.assertIn("## Evidence", tiny_spec_md)
        self.assertIn("Released: v0.1.0 @", tiny_spec_md)
        record_commit = git(repo, "log", "-1", "--format=%s").stdout.strip()
        self.assertIn("record v0.1.0", record_commit)
        for name in ("calc-flow", "tiny-rel"):
            c = subprocess.run([sys.executable, str(CHECK),
                                str(repo / "specs" / name)],
                               capture_output=True, text=True, cwd=repo)
            self.assertEqual(c.returncode, 0,
                             f"check.py {name}: {c.stdout}{c.stderr}")
            self.assertIn("PASS", c.stdout)


class PublishTests(unittest.TestCase):
    def cut_with_remote(self) -> tuple[Path, str]:
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha),
            remote=True)
        return repo, cut_release(repo)

    def test_plan_names_the_pushes_and_the_manual_gh_route(self):
        repo, tag = self.cut_with_remote()
        r = rel(repo, "publish", tag)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("publish plan for v0.1.0 (outward", r.stdout)
        self.assertIn("git push origin main   (never --force)", r.stdout)
        self.assertIn("git push origin refs/tags/v0.1.0", r.stdout)
        self.assertIn("gh not installed", r.stdout)
        self.assertEqual(git(repo, "ls-remote", "origin",
                             "refs/tags/v0.1.0").stdout.strip(), "")

    def test_confirm_pushes_branch_and_tag_to_a_bare_remote(self):
        repo, tag = self.cut_with_remote()
        r = rel(repo, "publish", tag, "--confirm", tag)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"pushed main and {tag} to origin", r.stdout)
        self.assertTrue(git(repo, "ls-remote", "origin",
                            f"refs/tags/{tag}").stdout.strip())
        self.assertTrue(git(repo, "ls-remote", "origin",
                            "refs/heads/main").stdout.strip())

    def test_gh_stub_creates_the_github_release(self):
        repo, tag = self.cut_with_remote()
        with gh_stub("https://github.com/o/r/releases/tag/v0.1.0") as env:
            r = rel(repo, "publish", tag, "--confirm", tag, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("GitHub release: https://github.com/o/r/releases/tag/v0.1.0",
                      r.stdout)

    def test_rejected_push_stops_and_never_forces(self):
        repo, tag = self.cut_with_remote()
        bare = Path(git(repo, "remote", "get-url", "origin").stdout.strip())
        remote_main = git(repo, "ls-remote", "origin", "refs/heads/main").stdout
        hook = bare / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\necho 'no pushes in this fixture' >&2\nexit 1\n",
                        encoding="utf-8")
        hook.chmod(0o755)
        r = rel(repo, "publish", tag, "--confirm", tag)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("push origin main failed", r.stderr)
        self.assertIn("never forced", r.stderr)
        self.assertEqual(git(repo, "ls-remote", "origin", "refs/heads/main").stdout,
                         remote_main)
        self.assertEqual(git(repo, "ls-remote", "origin",
                             f"refs/tags/{tag}").stdout.strip(), "")

    def test_publish_refuses_dirty_trees_and_detached_heads_and_missing_remotes(self):
        repo, tag = self.cut_with_remote()
        (repo / "README.md").write_text("# stray\n", encoding="utf-8")
        r = rel(repo, "publish", tag, "--confirm", tag)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("working tree is dirty", r.stderr)
        (repo / "README.md").unlink()
        git(repo, "checkout", "-q", "--detach", "HEAD")
        r = rel(repo, "publish", tag, "--confirm", tag)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("detached HEAD", r.stderr)
        git(repo, "checkout", "-q", "main")
        git(repo, "remote", "remove", "origin")
        r = rel(repo, "publish", tag, "--confirm", tag)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("no git remote", r.stderr)


class VerifyAndStatusTests(unittest.TestCase):
    def released(self) -> tuple[Path, str]:
        repo, base = make_repo()
        add_specs(repo, {**delivered_specs("calc-flow", sha=base),
                         **delivered_specs("tiny-rel", tiny=True, smoke=True,
                                           sha=base)})
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: delivered specs")
        return repo, cut_release(repo)

    def test_checklist_lists_rollout_and_smoke_items_and_records_the_outcome(self):
        repo, tag = self.released()
        r = rel(repo, "verify", tag)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("calc-flow (plan § Rollout): `python3 test_calc.py` green",
                      r.stdout)
        self.assertIn("tiny-rel (T003): `python3 calc.py multiply 6 7` prints 42",
                      r.stdout)
        r = rel(repo, "verify", tag, "--outcome", "fail",
                "--note", "500s on /multiply", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("recorded `Post-release check:", r.stdout)
        self.assertIn("hotfix", r.stdout)
        full_task = (repo / "specs" / "calc-flow" / "task.md").read_text(encoding="utf-8")
        self.assertLess(full_task.index("**Released**"),
                        full_task.index("**Post-release check**"))
        tiny_spec_md = (repo / "specs" / "tiny-rel" / "spec.md").read_text(encoding="utf-8")
        self.assertLess(tiny_spec_md.index("Released:"),
                        tiny_spec_md.index("Post-release check:"))

    def test_verify_write_is_idempotent(self):
        repo, tag = self.released()
        r = rel(repo, "verify", tag, "--outcome", "pass", "--note", "ok", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = rel(repo, "verify", tag, "--outcome", "pass", "--note", "ok", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for holder in ("specs/calc-flow/task.md", "specs/tiny-rel/spec.md"):
            text = (repo / holder).read_text(encoding="utf-8")
            self.assertEqual(text.count("Post-release check"), 1, holder)

    def test_status_names_the_next_step(self):
        repo, _ = make_repo(
            lambda sha: delivered_specs("tiny-rel", tiny=True, sha=sha))
        (repo / "README.md").write_text("# stray\n", encoding="utf-8")
        r = rel(repo, "status")
        self.assertIn("next: refuse: commit or stash the stray changes first",
                      r.stdout)
        (repo / "README.md").unlink()
        self.assertEqual(rel(repo, "notes", "0.1.0", "--write").returncode, 0)
        r = rel(repo, "status")
        self.assertIn("next: preflight <version>, then cut <version>", r.stdout)
        tag = cut_release(repo)
        r = rel(repo, "status")
        self.assertIn(f"next: verify {tag}", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
