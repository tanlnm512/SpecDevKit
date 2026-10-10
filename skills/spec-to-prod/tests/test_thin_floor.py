#!/usr/bin/env python3
"""Tests for the thin floor (D-037): `**Tier**: tiny` makes the
contract ONE file — spec.md carries the task list in § Tasks, the
authoring nodes are SKIPPED, verify gates on the tiny checker, ticks
land inside spec.md, and migrate.py grow moves structure to the full
docset without renumbering.

Serves eval case spec-to-prod/e7 (tiny tier end-to-end).
"""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def run(*args):
    path = str(SCRIPTS / args[0])
    if path.endswith(".sh"):
        cmd = ["bash", path, *map(str, args[1:])]
    else:
        cmd = [sys.executable, path, *map(str, args[1:])]
    return subprocess.run(cmd, capture_output=True, text=True)

SPEC = """# Spec: demo

**Status**: {status}
**Tier**: tiny
**Effort**: standard
**Created**: 2026-10-09
**Branch**: `feat/demo`

## What
A demo capability proving the one-file contract.

## Why
The thin floor needs a real end-to-end case.

## User stories
### US1 — Greet (P1)
As a user, I want a greeting, so that I feel seen.

**Acceptance criteria**:
- AC1: Given a name, When greeted, Then the greeting names them.

## Requirements
- **FR-001**: The system shall greet the named user.

## Tasks

- [ ] T001 add the greeting module (FR-001) [P]
  - Touches: `src/greet.py`
  - Accept: `python3 -c "assert True"`

- [ ] T002 document it (FR-001) [P]
  - Touches: `README.md`
  - Accept: `python3 -c "assert True"`

## Evidence
"""


class ThinFloorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        r = run("scaffold.sh", "--tier", "tiny", "demo", self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.spec_dir = self.root / "specs" / "demo"

    def write_spec(self, status="draft", tasks=None):
        text = SPEC.format(status=status)
        if tasks is not None:
            text = re.sub(r"## Tasks\n.*?\n## Evidence",
                          f"## Tasks\n{tasks}\n## Evidence", text, flags=re.S)
        (self.spec_dir / "spec.md").write_text(text)
        return text

    def test_scaffold_tiny_writes_one_file(self):
        files = sorted(p.name for p in self.spec_dir.iterdir())
        self.assertEqual(files, ["research.md", "spec.md"])
        self.assertIn("**Tier**: tiny",
                      (self.spec_dir / "spec.md").read_text())

    def test_scaffold_full_writes_seven(self):
        r = run("scaffold.sh", "--tier", "full", "demo2", self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        files = sorted(p.name for p in (self.root / "specs" / "demo2").iterdir())
        self.assertEqual(files, ["plan.md", "research.md", "spec.md",
                                 "survey.md", "task.md", "tech-spec.md",
                                 "test.md"])

    def test_tiny_check_passes_and_full_contract_not_demanded(self):
        self.write_spec()
        r = run("check.py", self.spec_dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("tier: tiny", r.stdout)

    def test_tiny_check_fails_on_proofless_tick_and_uncited_task(self):
        self.write_spec(tasks="- [x] T001 do it\n")
        r = run("check.py", self.spec_dir)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("done <date>", r.stdout)
        self.assertIn("T001 cites no FR/NFR id", r.stdout)

    def test_graph_skips_authoring_and_verifies_from_spec_alone(self):
        self.write_spec()
        r = run("graph.py", self.spec_dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for node in ("survey", "plan", "tech", "qa", "tasks"):
            self.assertIn(f"{node:14} SKIPPED", r.stdout, node)
            self.assertIn("tier: tiny", r.stdout)
        self.assertRegex(r.stdout, r"verify\s+done")
        self.assertRegex(r.stdout, r"approve\s+READY")

    def test_tiny_execute_reads_spec_tasks(self):
        import json
        self.write_spec(status="approved")
        r = run("graph.py", self.spec_dir, "--state-json")
        state = json.loads(r.stdout[r.stdout.find("{"):])
        tasks = state["nodes"]["execute"]["tasks"]
        self.assertEqual([t["id"] for t in tasks], ["T001", "T002"])

    def test_tiny_tick_lands_in_spec_md(self):
        self.write_spec(status="approved")
        r = run("tick.py", self.spec_dir, "--note", "T001 :: pytest ok")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = (self.spec_dir / "spec.md").read_text()
        self.assertIn("- [x] T001 add the greeting module", text)
        self.assertIn("done 20", text)
        self.assertFalse((self.spec_dir / "task.md").exists())

    def test_grow_moves_structure_and_preserves_ids(self):
        self.write_spec()
        r = run("migrate.py", "grow", self.spec_dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        task_md = (self.spec_dir / "task.md").read_text()
        self.assertIn("- [ ] T001 add the greeting module (FR-001) [P]",
                      task_md)
        self.assertIn("| 1 | 2 | 0 |", task_md)
        spec_md = (self.spec_dir / "spec.md").read_text()
        self.assertIn("**Tier**: full", spec_md)
        self.assertNotIn("## Tasks", spec_md)
        for f in ("plan.md", "tech-spec.md", "test.md", "survey.md"):
            self.assertTrue((self.spec_dir / f).exists(), f)

    def test_full_tier_docs_unchanged_by_default(self):
        # no Tier header -> full: the authoring nodes are gated on their
        # docs exactly as before, never "tier: tiny"
        text = self.write_spec().replace("**Tier**: tiny\n", "")
        (self.spec_dir / "spec.md").write_text(text)
        r = run("graph.py", self.spec_dir)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("tier: tiny", r.stdout)
        self.assertRegex(r.stdout, r"survey\s+READY")


if __name__ == "__main__":
    unittest.main()
