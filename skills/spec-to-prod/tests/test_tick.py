"""Tests for scripts/tick.py — run via tests/run.sh (needs Python >= 3.10).

The mechanical-tick contract: entry bodies and checkpoint comments survive
byte-identical; only the ticked first line, one inserted done-line, and the
burndown Done column change. Validation is atomic (no partial application),
and check.py stays green on the ticked copy.
"""

import contextlib
import difflib
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest

from pathlib import Path
SKILL = Path(__file__).resolve().parents[1]
FIXTURE = SKILL / "examples" / "mini-spec" / "specs" / "mini-spec"

_spec = importlib.util.spec_from_file_location("tick", SKILL / "scripts" / "tick.py")
tick = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tick)

_cspec = importlib.util.spec_from_file_location("check", SKILL / "scripts" / "check.py")
check = importlib.util.module_from_spec(_cspec)
_cspec.loader.exec_module(check)


def run_tick(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = tick.main(list(argv))
    return rc, buf.getvalue()


class TickTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.spec = Path(self.tmp) / "mini-spec"
        shutil.copytree(FIXTURE, self.spec)
        self.before = (self.spec / "task.md").read_text(encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_check(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            return check.main([str(self.spec)]), buf.getvalue()

    def test_tick_t001_t002_and_burndown(self):
        rc, out = run_tick(
            str(self.spec),
            "--note", "T001 :: pytest repo/ passed",
            "--note", "T002 :: two tests added",
        )
        self.assertEqual(rc, 0, out)
        after = (self.spec / "task.md").read_text(encoding="utf-8")
        self.assertRegex(after, r"\| \*\*Σ\*\* \| 2 \| 2 \|")
        # bodies survive: only tick lines, done lines, and burndown rows change
        diff = list(difflib.unified_diff(self.before.splitlines(),
                                         after.splitlines(), lineterm=""))
        changed = [l for l in diff if l[:1] in "+-" and l[:3] not in ("---", "+++")]
        self.assertEqual(len(changed), 10, changed)  # 2 tick + 2 done + 4 burndown (--fix-burndown also normalizes padding)
        # a fully-ticked spec must sit past the approve gate for check.py
        # (progress gate: ticked tasks under Status: draft = skipped approval)
        spec_md = self.spec / "spec.md"
        spec_md.write_text(
            spec_md.read_text(encoding="utf-8").replace(
                "**Status**: draft", "**Status**: done", 1),
            encoding="utf-8")
        crc, cout = self._run_check()
        self.assertEqual(crc, 0, cout)

    def test_unknown_task_writes_nothing(self):
        rc, out = run_tick(str(self.spec), "--note", "T009 :: nope")
        self.assertEqual(rc, 1, out)
        self.assertEqual((self.spec / "task.md").read_text(encoding="utf-8"), self.before)

    def test_double_tick_refused(self):
        rc, _ = run_tick(str(self.spec), "--note", "T001 :: one")
        self.assertEqual(rc, 0)
        before2 = (self.spec / "task.md").read_text(encoding="utf-8")
        rc, out = run_tick(str(self.spec), "--note", "T001 :: again")
        self.assertEqual(rc, 1, out)
        self.assertEqual((self.spec / "task.md").read_text(encoding="utf-8"), before2)

    def test_claimed_marker_stripped_on_tick(self):
        task = self.spec / "task.md"
        text = task.read_text(encoding="utf-8").replace(
            "- [ ] T001 [P] Implement", "- [ ] T001 [P] (in-progress) Implement")
        task.write_text(text, encoding="utf-8")
        rc, out = run_tick(str(self.spec), "--note", "T001 :: done thing")
        self.assertEqual(rc, 0, out)
        after = task.read_text(encoding="utf-8")
        self.assertIn("- [x] T001 [P] Implement", after)
        self.assertNotIn("(in-progress)", [l for l in after.splitlines() if l.startswith("- [x] T001")][0])

    def test_dry_run_writes_nothing(self):
        rc, out = run_tick(str(self.spec), "--note", "T001 :: preview", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertEqual((self.spec / "task.md").read_text(encoding="utf-8"), self.before)

    def test_note_shape_enforced(self):
        rc, out = run_tick(str(self.spec), "--note", "no double colon here")
        self.assertEqual(rc, 2, out)


if __name__ == "__main__":
    unittest.main()
