"""A delivery record survives rewritten history: after C1/C2 a
squash-merge orphans the commit `Delivered: commit @ <sha>` names;
`tick.py --redeliver` re-points the record and check.py goes green
again."""

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
EXAMPLE = SKILL / "examples" / "mini-spec"

_freeze_spec = importlib.util.spec_from_file_location(
    "freeze", SCRIPTS / "freeze.py")
freeze = importlib.util.module_from_spec(_freeze_spec)
_freeze_spec.loader.exec_module(freeze)


def run_script(name: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "KIT_TELEMETRY": "off"})


class RedeliverTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="redeliver-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copytree(EXAMPLE / "repo", self.root / "repo")
        self.spec = self.root / "specs" / "mini-spec"
        shutil.copytree(EXAMPLE / "specs" / "mini-spec", self.spec)
        self.git("init", "-q")
        self.base = self.commit("base")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=kit",
             "-c", "user.email=kit@example.com", *args],
            check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "--short", "HEAD")

    def edit(self, name: str, old: str, new: str) -> None:
        path = self.spec / name
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def deliver(self) -> str:
        """Approve, land, tick, C1, then the C2 delivery record."""
        (self.spec / "approvals").mkdir()
        (self.spec / "approvals" / "review.md").write_text(
            f"Docset fingerprint: {freeze.docset_fingerprint(self.spec)}\n"
            "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none\n",
            encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(freeze.record(self.spec, self.root), 0)
        self.edit("spec.md", "**Status**: draft", "**Status**: approved")
        self.edit("task.md", "T001 [P] Implement",
                  "T001 [P] (implemented) Implement")
        ticked = run_script("tick.py", self.spec,
                            "--note", "T001 :: pytest green",
                            "--note", "T002 :: pytest green")
        self.assertEqual(ticked.returncode, 0, ticked.stderr)
        self.assertNotIn("(implemented)",
                         (self.spec / "task.md").read_text(encoding="utf-8"))
        c1 = self.commit("C1")
        self.edit("task.md", "\n## Burndown",
                  f"\n**Delivered**: commit @ {c1}\n\n## Burndown")
        self.edit("spec.md", "**Status**: approved", "**Status**: done")
        self.commit("C2")
        return c1

    def test_a_squashed_delivery_is_repointed_and_checks_green(self):
        c1 = self.deliver()
        self.assertEqual(run_script("check.py", self.spec).returncode, 0)

        self.git("reset", "-q", "--soft", self.base)
        squash = self.commit("squash-merge")
        red = run_script("check.py", self.spec)
        self.assertEqual(red.returncode, 1, red.stdout)
        self.assertIn(f"delivered: commit '{c1}'", red.stdout)
        self.assertIn("tick.py <spec-dir> --redeliver <new-sha>", red.stdout)

        task = self.spec / "task.md"
        before = task.read_bytes()
        refused = run_script("tick.py", self.spec, "--redeliver", "deadbeef")
        self.assertEqual(refused.returncode, 1, refused.stdout)
        self.assertIn("not a commit", refused.stderr)
        self.assertEqual(task.read_bytes(), before)

        moved = run_script("tick.py", self.spec, "--redeliver", squash)
        self.assertEqual(moved.returncode, 0, moved.stderr)
        self.assertIn(f"**Delivered**: commit @ {squash} (was {c1})",
                      task.read_text(encoding="utf-8"))
        green = run_script("check.py", self.spec)
        self.assertEqual(green.returncode, 0, green.stdout)

        # an intact record is never rewritten
        again = run_script("tick.py", self.spec, "--redeliver", squash)
        self.assertEqual(again.returncode, 1, again.stdout)
        self.assertIn("nothing to re-point", again.stderr)

    def test_help_prints_the_invocation_syntax(self):
        shown = run_script("tick.py", "-h")
        self.assertEqual(shown.returncode, 0)
        self.assertIn("Usage: tick.py <spec-dir> --note", shown.stdout)
        self.assertIn("--redeliver <new-sha>", shown.stdout)

        migrate_help = run_script("migrate.py", "-h")
        self.assertEqual(migrate_help.returncode, 0)
        self.assertIn("migrate.py <spec-dir> upgrade [--apply]",
                      migrate_help.stdout)
        self.assertIn("--apply", migrate_help.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
