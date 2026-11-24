#!/usr/bin/env python3
"""Ruled-proof tests for spec-ship's ship.py: the delivery block's
`- Proof: TC-### — <ruling>` lines (spec-build D-047) reach the PR
body's Proof section as `Owner to test after merge:` lines (D-007) —
read from the delivery block, `notes/delivery.md` only as the
archived-history fallback — and never as passes.

Same drivers as test_ship.py — real temp git repos; `pr-body` reads
git and the docs only. Every assertion keys on the body text and the
JSON facts the contract names, at the values the fixture docset says.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_ship import PR_URL, git, ship

TODAY = "2026-01-15"
RULING = "no docker engine this session; stack proven in staging CI (D-047)"
TEST_MD = "## TC-001 multiply\n## TC-002 error\n## TC-003 stack\n"
SPEC_MD = (
    "# Spec: demo\n\n"
    "**Status**: done\n**Tier**: full\n**Type**: feature\n"
    f"**Created**: {TODAY}\n**Branch**: `ship-demo`\n\n"
    "## What\nThe calculator gains integer multiplication.\n\n"
    "## Why\nProducts need no repeated-addition workaround.\n\n"
    "## Requirements\n"
    "- **FR-001**: Multiply two integers and print the product.\n\n")


class ProofRulingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ship-proof-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q", "-b", "main")
        (self.root / "README").write_text("seed\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        git(self.root, "checkout", "-q", "-b", "ship-demo")
        git(self.root, "commit", "-q", "--allow-empty", "-m", "multiply lands")
        self.sha = git(self.root, "rev-parse", "HEAD")

    def deliver_full(self, ruled: bool = True) -> None:
        """A delivered full-tier spec: three ticked tasks, three TCs, and
        a delivery block whose Proof line rules TC-003 unless `ruled` is
        false."""
        spec = self.root / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "spec.md").write_text(SPEC_MD, encoding="utf-8")
        (spec / "test.md").write_text(TEST_MD, encoding="utf-8")
        block = ("- Docs impact: none — no doc surface in the diff\n"
                 + (f"- Proof: TC-003 — {RULING}\n" if ruled else ""))
        (spec / "task.md").write_text(
            "# Tasks: demo\n\n"
            "- [x] T001 Multiply lands (FR-001) [P]\n"
            "  Touches: `calc.py`\n"
            f"  done {TODAY} — pytest green, 2 tests\n"
            "- [x] T002 Error path proven (NFR-001) [P]\n"
            "  Touches: `calc.py`\n"
            f"  done {TODAY} — bad input exits 1\n"
            "- [x] T003 Stack proven (NFR-001) [P]\n"
            "  Touches: `calc.py`\n"
            f"  done {TODAY} — not run here: the engine never came up\n\n"
            f"**Delivered**: commit @ {self.sha}\n"
            + block, encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: record the delivery")

    def deliver_tiny(self) -> None:
        """A delivered tiny spec whose holder predates the delivery
        block: spec.md's Delivered field carries no fact lines."""
        spec = self.root / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "spec.md").write_text(
            "# Spec: demo\n\n"
            "**Status**: done\n**Tier**: tiny\n**Type**: feature\n"
            f"**Created**: {TODAY}\n**Branch**: `ship-demo`\n\n"
            "## What\nThe calculator gains integer multiplication.\n\n"
            "## Why\nProducts need no repeated-addition workaround.\n\n"
            "## Requirements\n"
            "- **FR-001**: Multiply two integers and print the product.\n\n"
            "## Tasks\n"
            "- [x] T001 Multiply lands (FR-001) [P]\n"
            "  Touches: `calc.py`\n"
            "  Accept: `python3 calc.py multiply 6 7` prints 42\n"
            f"  done {TODAY} — `python3 calc.py multiply 6 7` prints 42\n\n"
            f"Delivered: commit @ {self.sha}\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: record the delivery")

    def write_note(self, *lines: str) -> None:
        notes = self.root / "specs" / "demo" / "notes"
        notes.mkdir(parents=True)
        (notes / "delivery.md").write_text("".join(l + "\n" for l in lines),
                                           encoding="utf-8")

    def body(self) -> dict:
        r = ship(self.root, "pr-body", "demo", "--base", "main", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout)

    def test_a_ruled_proof_renders_as_owner_to_test_after_merge(self):
        self.deliver_full()
        result = self.body()
        self.assertIn(f"- Owner to test after merge: TC-003 — {RULING}",
                      result["body"])
        proof = result["proof"]
        self.assertEqual(proof["ruled_proofs"],
                         [{"tc": "TC-003", "ruling": RULING}])
        # not a pass: the ruled proof is no task's proof note, and the
        # counts stay the holder's own (3 ticked, 3 TCs in the contract)
        self.assertNotIn("TC-003", json.dumps(proof["notes"]))
        self.assertEqual(proof["tasks_ticked"], 3)
        self.assertEqual(proof["tc_total"], 3)
        # the same block feeds the other owner facts — one source
        self.assertIn("no doc surface in the diff", result["body"])
        human = ship(self.root, "pr-body", "demo", "--base", "main")
        self.assertIn("- Owner to test after merge: TC-003 —", human.stdout)

    def test_the_delivery_block_outranks_the_archived_note(self):
        self.deliver_full()
        self.write_note("Proof: TC-009 — a ruling from retired history\n")
        result = self.body()
        self.assertIn(f"- Owner to test after merge: TC-003 — {RULING}",
                      result["body"])
        self.assertNotIn("TC-009", result["body"])
        self.assertEqual(result["proof"]["ruled_proofs"],
                         [{"tc": "TC-003", "ruling": RULING}])

    def test_the_archived_note_fallback_still_carries_rulings(self):
        self.deliver_tiny()
        # the note file predates the block: bare fact lines, no bullets
        self.write_note(f"Proof: TC-001 — {RULING}\n")
        result = self.body()
        self.assertIn(f"- Owner to test after merge: TC-001 — {RULING}",
                      result["body"])
        self.assertEqual(result["proof"]["ruled_proofs"],
                         [{"tc": "TC-001", "ruling": RULING}])
        # the fallback feeds the other reads too — the shared source
        self.assertIn("not recorded — the delivery note has no "
                      "`Docs impact:` line", result["body"])

    def test_no_ruled_proof_renders_nothing_extra(self):
        self.deliver_full(ruled=False)
        result = self.body()
        self.assertEqual(result["proof"]["ruled_proofs"], [])
        self.assertNotIn("Owner to test after merge", result["body"])
        # the section itself is never dropped: its own lines render
        self.assertIn("3/3 tasks ticked", result["body"])
        self.assertIn("Delivery pass complete", result["body"])

    def test_a_ruled_proof_is_not_counted_as_passing(self):
        self.deliver_full()
        with_ruling = self.body()
        holder = self.root / "specs" / "demo" / "task.md"
        holder.write_text(
            holder.read_text(encoding="utf-8")
            .replace(f"- Proof: TC-003 — {RULING}\n", ""),
            encoding="utf-8")
        without = self.body()
        a, b = with_ruling["proof"], without["proof"]
        for key in ("tc_total", "tc_kind", "tasks_total", "tasks_ticked",
                    "notes"):
            self.assertEqual(a[key], b[key], f"the ruling changed {key}")
        self.assertEqual(b["ruled_proofs"], [])
        self.assertEqual(a["ruled_proofs"],
                         [{"tc": "TC-003", "ruling": RULING}])
        added = [line for line in with_ruling["body"].splitlines()
                 if line not in without["body"].splitlines()]
        self.assertEqual(added,
                         [f"- Owner to test after merge: TC-003 — {RULING}"])

    def test_the_block_still_reads_after_the_shipped_record_lands(self):
        # `record` writes the Shipped line directly under Delivered: (run.md
        # Records) — the block steps over it, so a post-record re-draft
        # still carries every owner fact the block holds, and never falls
        # back to a note the block-era spec does not have
        self.deliver_full()
        r = ship(self.root, "record", "demo", "--pr", PR_URL)
        self.assertEqual(r.returncode, 0, r.stdout)
        holder = (self.root / "specs" / "demo" / "task.md").read_text()
        self.assertIn(f"**Delivered**: commit @", holder)
        self.assertIn(f"**Shipped**: PR {PR_URL}\n- Docs impact:", holder)
        self.assertFalse(
            (self.root / "specs" / "demo" / "notes" / "delivery.md").exists())
        result = self.body()
        self.assertIn(f"- Owner to test after merge: TC-003 — {RULING}",
                      result["body"])
        self.assertEqual(result["proof"]["ruled_proofs"],
                         [{"tc": "TC-003", "ruling": RULING}])
        self.assertIn("no doc surface in the diff", result["body"])
        self.assertNotIn("not recorded — the delivery note has no "
                         "`Docs impact:` line", result["body"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
