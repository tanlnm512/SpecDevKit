#!/usr/bin/env python3
"""The delivery block reads through a `Shipped:` record: ship.py's
`record` writes the line directly under `Delivered:` (spec-ship
contracts/run.md Records), so the block's skip list steps over it —
the same read as ship.py's delivery_block, one doc state answering
identically in both skills. Without the skip, a post-record read
blanks the block and the owner facts fall through to a note the
block-era spec does not have."""

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import audit  # noqa: E402

SHA = "a177d1d38a7b8e165044f56d609885ed02847382"
PR_URL = "https://github.com/acme/widget/pull/7"
BULLETS = ("- Docs impact: none — no doc surface in the diff\n"
           "- Behavior preserved: none — additive\n"
           "- Proof: TC-002 — no docker engine this session\n"
           "- Rollback: NFR-001 — revert the module commit\n")


def spec_with(holder_tail: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix="block-shipped-"))
    spec = root / "specs" / "demo"
    spec.mkdir(parents=True)
    (spec / "spec.md").write_text(
        "# Spec: demo\n\n**Status**: done\n**Tier**: full\n", encoding="utf-8")
    (spec / "task.md").write_text(
        "# Tasks: demo\n\n"
        "- [x] T001 Lands (FR-001) [P]\n"
        "  done 2026-01-15 — pytest green\n\n"
        f"**Delivered**: commit @ {SHA}\n" + holder_tail, encoding="utf-8")
    return spec


class DeliveryBlockShippedTests(unittest.TestCase):
    def test_the_block_reads_past_the_shipped_record(self):
        # the record lands on the line after Delivered:, before the facts
        spec = spec_with(f"**Shipped**: PR {PR_URL}\n{BULLETS}")
        block, where = audit.delivery_block(spec)
        self.assertEqual(block,
                         "\n".join(line[2:] for line in BULLETS.splitlines()))
        self.assertEqual(where, "task.md delivery block")
        self.assertEqual(audit.proof_rulings(spec), {"TC-002"})

    def test_a_block_without_the_record_reads_unchanged(self):
        spec = spec_with(BULLETS)
        block, where = audit.delivery_block(spec)
        self.assertEqual(block,
                         "\n".join(line[2:] for line in BULLETS.splitlines()))
        self.assertEqual(where, "task.md delivery block")

    def test_the_record_between_the_facts_ends_the_bullet_run(self):
        # a hand-placed record after the bullets is not a fact line: the
        # block keeps the bullets it opened with
        spec = spec_with(f"{BULLETS}**Shipped**: PR {PR_URL}\n")
        block, _where = audit.delivery_block(spec)
        self.assertEqual(block,
                         "\n".join(line[2:] for line in BULLETS.splitlines()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
