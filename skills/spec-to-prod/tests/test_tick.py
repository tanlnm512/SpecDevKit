"""Tests for scripts/tick.py — run via tests/run.sh (needs Python >= 3.10).

The mechanical-tick contract: entry bodies and checkpoint comments survive
byte-identical; only the ticked first line, one inserted done-line, and the
burndown Done column change. Validation is atomic (no partial application),
and check.py stays green on the ticked copy. The transaction contract: a
failed validation, write, sync, replace, or postcheck must exit nonzero and
leave every file under the spec dir byte-identical — no stray temp file left
behind.
"""

import contextlib
import difflib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

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


def tree_snapshot(root):
    """relpath -> bytes for every file under root: the byte-identical
    guarantee covers the whole spec dir, stray temp files included."""
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


class TickTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.spec = Path(self.tmp) / "mini-spec"
        shutil.copytree(FIXTURE, self.spec)
        self.before = (self.spec / "task.md").read_text(encoding="utf-8")
        self.snapshot = tree_snapshot(self.spec)

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

    # Failure matrix for the tick transaction: every stage — validation,
    # write, sync, replace, postcheck — must exit nonzero and leave the
    # tree byte-identical. Injection seams: filesystem perms for write,
    # os.fsync / os.replace for the durable pipeline (Path.replace routes
    # through os.replace), and a real check.py failure for postcheck.

    def _assert_original(self):
        self.assertEqual(tree_snapshot(self.spec), self.snapshot)

    def _run_tick_must_fail(self, *argv):
        """A tick must fail handled (no escaping exception = no crash),
        nonzero, and without touching a byte."""
        try:
            rc, out = run_tick(*argv)
        except Exception as exc:
            self.fail(f"tick crashed instead of exiting nonzero: {exc!r}")
        self.assertNotEqual(rc, 0)
        self._assert_original()

    def test_validation_failure_is_atomic(self):
        self._run_tick_must_fail(
            str(self.spec),
            "--note", "T001 :: good", "--note", "T999 :: no such task")

    def test_duplicate_note_refused(self):
        self._run_tick_must_fail(
            str(self.spec),
            "--note", "T001 :: one", "--note", "T001 :: twice")

    def test_write_failure_preserves_original(self):
        # spec dir made unwritable: the beside-target write must fail cleanly
        os.chmod(self.spec, 0o555)
        try:
            self._run_tick_must_fail(str(self.spec), "--note", "T001 :: proof")
        finally:
            os.chmod(self.spec, 0o755)

    def test_sync_failure_preserves_original(self):
        # first fsync (the temp's durability barrier) fails; recovery may
        # still fsync
        real_fsync = os.fsync
        synced = []
        def refuse_once(fd):
            if not synced:
                synced.append(fd)
                raise OSError("injected fsync failure")
            return real_fsync(fd)
        with unittest.mock.patch("os.fsync", side_effect=refuse_once):
            self._run_tick_must_fail(str(self.spec), "--note", "T001 :: proof")

    def test_replace_failure_preserves_original(self):
        # the promotion replace fails once; a recovery replace may proceed
        real_replace = os.replace
        refused = []
        def refuse_once(src, dst):
            if Path(dst).name == "task.md" and not refused:
                refused.append(dst)
                raise OSError("injected replace failure")
            return real_replace(src, dst)
        with unittest.mock.patch("os.replace", side_effect=refuse_once), \
                unittest.mock.patch("os.rename", side_effect=refuse_once):
            self._run_tick_must_fail(str(self.spec), "--note", "T001 :: proof")

    def test_postcheck_failure_restores_original(self):
        # The replace appears to succeed but lands corrupted content: the
        # post-replace postcondition check must catch it and roll back.
        real_replace = os.replace
        promoted = []
        def corrupt_once(src, dst):
            if Path(dst).name == "task.md" and not promoted:
                promoted.append(dst)
                Path(dst).write_text("corrupted — no task entries",
                                     encoding="utf-8")
                return
            return real_replace(src, dst)
        with unittest.mock.patch("os.replace", side_effect=corrupt_once), \
                unittest.mock.patch("os.rename", side_effect=corrupt_once):
            self._run_tick_must_fail(str(self.spec), "--note", "T001 :: proof")


if __name__ == "__main__":
    unittest.main()
