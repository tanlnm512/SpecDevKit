"""Opt-in worktree-per-task execution — spec-design D-079.

`graph.py --emit-spawns --isolate worktree` (and `--run`) gives every
implementer payload of the wave its own detached git worktree under
`<repo>/.spec-kit/worktrees/<spec>/<T###>/`, checked out at a snapshot
of the main working tree, and names it as the payload's repo:

  - the worktree holds the main tree's uncommitted work, and nothing of
    the main tree moved: no ref, no reflog entry, no index change;
  - the payload's `- repo:` line is the worktree, under one line making
    it the developer's only working tree;
  - the emit is idempotent: a worktree nothing was done in is rebuilt
    from the current tree, a dirty one is kept, and the worktrees of
    tasks no longer open are removed;
  - `--explain execute` names each worktree on disk with what it owes;
  - outside a git repository the flag refuses with exit 2, a worktree
    git cannot build refuses the wave, and without the flag nothing is
    created;
  - `--dry-run` prints the plan and creates nothing.

This package ships no developer brief, so its own CLI writes no
implementer payload (and builds no worktree — pinned below); the emit
tests stand the brief in and run the engine in-process. spec-build's
byte-identical copy runs the real thing in spec-build's tests.

Fixtures are the mini-spec docset approved in a scratch git repository
whose main tree carries uncommitted work.
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from test_graph import (  # noqa: E402
    FIXTURE,
    IMPLEMENTED_T1_TASKS,
    approved_fixture,
    claim_by_hand,
    write,
)
import graph as engine  # noqa: E402 - the master, by name

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
STOOD_IN_BRIEF = "# Developer agent (implement lens)\n\nImplement the task.\n"
IDENTITY = ("-c", "user.name=kit", "-c", "user.email=kit@example.com",
            "-c", "commit.gpgsign=false")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *IDENTITY, *args], check=True,
        capture_output=True, text=True).stdout.strip()


def scratch_repo(tmp: Path) -> Path:
    """specs/alpha approved inside a git repository whose main tree
    then takes uncommitted work: a tracked edit and an untracked file."""
    d = approved_fixture(tmp, "alpha")
    shutil.copy(FIXTURE.parent / "CONSTITUTION.md", tmp / "specs")
    git(tmp, "init", "-q", "-b", "main")
    git(tmp, "add", "-A")
    git(tmp, "commit", "-qm", "the approved docset")
    calc = tmp / "repo" / "calc.py"
    write(calc, calc.read_text(encoding="utf-8")
          + "\ndef multiply(a, b):\n    return a * b\n")
    write(tmp / "repo" / "brand_new.py", "NEW = 1\n")
    return d


def run(spec_dir: Path, tel: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, KIT_TELEMETRY_DIR=str(tel), KIT_TELEMETRY="on")
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "graph.py"), str(spec_dir), *args],
        capture_output=True, text=True, timeout=300, env=env)


def worktree_lines(out: str) -> list[str]:
    """Every `worktree:` line an emit or a run printed."""
    return [ln for ln in out.splitlines() if ln.startswith("   worktree:")]


def in_process(emit, tel: Path) -> tuple[int, str]:
    """`emit` run against the engine in this process — the developer
    brief stood in, telemetry relocated: its exit code and its output."""
    read_raw = engine.read_raw

    def stood_in(path: Path) -> str | None:
        if path.name == "developer.md" and path.parent.name == "agents":
            return STOOD_IN_BRIEF
        return read_raw(path)

    out = io.StringIO()
    with unittest.mock.patch.object(engine, "read_raw", stood_in), \
            unittest.mock.patch.dict(os.environ, {
                "KIT_TELEMETRY_DIR": str(tel), "KIT_TELEMETRY": "on"}), \
            contextlib.redirect_stdout(out):
        rc = emit()
    return rc, out.getvalue()


class IsolatedWorktreeTests(unittest.TestCase):

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="isolated-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        tel = Path(tempfile.mkdtemp(prefix="isolated-tel-"))
        self.addCleanup(shutil.rmtree, tel, ignore_errors=True)
        self.tel = tel
        self.spec = scratch_repo(self._tmp)
        self.trees = self._tmp / ".spec-kit" / "worktrees" / "alpha"
        self.t001 = self.trees / "T001"

    def emit(self) -> tuple[int, str]:
        return in_process(
            lambda: engine.emit_spawns(self.spec, None, None, span="full",
                                       isolate=True), self.tel)

    def run_loop(self, dry_run: bool) -> tuple[int, str]:
        return in_process(
            lambda: engine.run_loop(self.spec, None, engine.PRINT_RUNNER,
                                    dry_run, None, isolate=True), self.tel)

    def payload(self) -> Path:
        return next((self.spec / "spawns").rglob("implementer-T001.md"))

    def test_the_worktree_holds_the_uncommitted_main_tree_and_moved_nothing(
            self):
        head, refs = git(self._tmp, "rev-parse", "HEAD"), git(
            self._tmp, "for-each-ref")
        index = (self._tmp / ".git" / "index").read_bytes()
        reflog = (self._tmp / ".git" / "logs" / "HEAD").read_bytes()

        rc, out = self.emit()
        self.assertEqual(rc, 0)
        self.assertIn("worktree: created — a detached snapshot of the "
                      f"main tree: {self.t001}", out)
        self.assertIn("payload: ", out)
        calc = (self.t001 / "repo" / "calc.py").read_text(encoding="utf-8")
        self.assertIn("def multiply(a, b):", calc)
        self.assertEqual((self.t001 / "repo" / "brand_new.py")
                         .read_text(encoding="utf-8"), "NEW = 1\n")
        self.assertEqual(git(self.t001, "status", "--porcelain"), "")

        # a detached worktree at a commit on no branch and in no reflog
        self.assertEqual(git(self.t001, "rev-parse", "--abbrev-ref", "HEAD"),
                         "HEAD")
        snapshot = git(self.t001, "rev-parse", "HEAD")
        self.assertEqual(git(self._tmp, "branch", "--contains", snapshot),
                         "")
        self.assertEqual(git(self._tmp, "log", "-1", "--format=%s",
                             snapshot), engine.specstate.SNAPSHOT_MESSAGE)
        self.assertEqual(git(self.t001, "log", "-1", "--format=%an",
                             snapshot), "spec-kit")
        self.assertEqual(git(self._tmp, "worktree", "list", "--porcelain")
                         .count("worktree "), 2)

        # the main tree: same HEAD, refs, reflog and index; its own
        # status never shows the worktrees
        self.assertEqual(git(self._tmp, "rev-parse", "HEAD"), head)
        self.assertEqual(git(self._tmp, "for-each-ref"), refs)
        self.assertEqual((self._tmp / ".git" / "index").read_bytes(), index)
        self.assertEqual((self._tmp / ".git" / "logs" / "HEAD").read_bytes(),
                         reflog)
        self.assertEqual((self._tmp / ".spec-kit" / ".gitignore")
                         .read_text(encoding="utf-8"), "*\n")
        status = git(self._tmp, "status", "--porcelain").splitlines()
        self.assertIn("M repo/calc.py", status)
        self.assertIn("?? repo/brand_new.py", status)
        self.assertFalse([ln for ln in status if ".spec-kit" in ln], status)

    def test_the_payload_names_the_worktree_as_the_developers_only_tree(
            self):
        rc, _ = self.emit()
        self.assertEqual(rc, 0)
        text = self.payload().read_text(encoding="utf-8")
        self.assertIn(f"- spec_dir: {self.spec}\n- repo: {self.t001}\n",
                      text)
        line = next(ln for ln in text.splitlines()
                    if ln.startswith("- isolated worktree: "))
        self.assertIn(f"{self.t001} is your ONLY working tree", line)
        self.assertIn(f"the main tree ({self._tmp}) is not yours to touch",
                      line)
        # the two writes the payload and the brief ask for in the main
        # tree's spec dir are named as the line's exceptions
        self.assertIn(f"under the main tree's spec dir ({self.spec}): your "
                      "digest file", line)
        self.assertIn("notes/T###.md", line)
        self.assertIn("never in this tree's copy of it", line)
        self.assertIn("ban on stash/reset/checkout still binds", line)
        self.assertIn("`mark.py land`", line)
        self.assertIn("`mark.py release`", line)
        self.assertEqual(sum(ln.startswith("- isolated worktree: ")
                             for ln in text.splitlines()), 1)
        # the spec dir stays the main tree's: the digest is written there
        self.assertIn(f"`{self.spec}/digests/", text)

    def test_this_clis_own_emit_builds_no_worktree_without_the_brief(self):
        r = run(self.spec, self.tel, "--emit-spawns", "--isolate",
                "worktree")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("payload: SKIPPED (brief not found: "
                      "agents/developer.md)", r.stdout)
        self.assertEqual(worktree_lines(r.stdout), [])
        self.assertFalse((self._tmp / ".spec-kit").exists())

    def test_without_the_flag_nothing_is_created(self):
        rc, out = in_process(
            lambda: engine.emit_spawns(self.spec, None, None, span="full"),
            self.tel)
        self.assertEqual(rc, 0)
        self.assertEqual(worktree_lines(out), [])
        self.assertIn(f"- repo: {self._tmp}\n",
                      self.payload().read_text(encoding="utf-8"))
        self.assertNotIn("isolated worktree",
                         self.payload().read_text(encoding="utf-8"))
        self.assertFalse((self._tmp / ".spec-kit").exists())
        self.assertEqual(git(self._tmp, "worktree", "list", "--porcelain")
                         .count("worktree "), 1)

    def test_re_emit_rebuilds_a_clean_worktree_and_keeps_a_dirty_one(self):
        rc, _ = self.emit()
        self.assertEqual(rc, 0)
        base = engine.specstate.worktree_base
        self.assertEqual(base(self.t001), git(self.t001, "rev-parse", "HEAD"))
        calc = self._tmp / "repo" / "calc.py"

        # work landed in the main tree after the worktree was cut: a
        # task re-emitted (deferred at the claim, never spawned) must
        # not start from the older tree
        landed = write(self._tmp / "repo" / "landed.py", "LANDED = 1\n")
        write(calc, calc.read_text(encoding="utf-8")
              + "\ndef last(a):\n    return a[-1]\n")

        rc, out = self.emit()
        self.assertEqual(rc, 0)
        self.assertIn(f"refreshed worktree: {self.t001} (clean — rebuilt "
                      "from the current tree)", out)
        self.assertEqual((self.t001 / "repo" / "landed.py").read_bytes(),
                         landed.read_bytes())
        self.assertIn("def last(a):",
                      (self.t001 / "repo" / "calc.py").read_text(
                          encoding="utf-8"))
        fresh = git(self.t001, "rev-parse", "HEAD")
        self.assertEqual(base(self.t001), fresh)
        self.assertEqual(git(self.t001, "status", "--porcelain"), "")
        self.assertEqual(git(self._tmp, "worktree", "list", "--porcelain")
                         .count("worktree "), 2)
        status = git(self._tmp, "status", "--porcelain").splitlines()
        self.assertFalse([ln for ln in status if ".spec-kit" in ln], status)

        # a fix round re-opens the task on a worktree that holds the
        # failed round's work: it is kept as it stands, at its own
        # snapshot, whatever landed since
        edit = write(self.t001 / "repo" / "calc.py",
                     "def multiply(a, b):\n    return a + b  # wrong\n")
        content = edit.read_bytes()
        write(self._tmp / "repo" / "later.py", "LATER = 1\n")
        task = self.spec / "task.md"
        write(task, task.read_text(encoding="utf-8").replace(
            "T001 [P] implement multiply", "T001 [P] (fix 1/5) implement "
            "multiply"))

        rc, out = self.emit()
        self.assertEqual(rc, 0)
        self.assertIn("worktree: kept — it holds uncommitted work; the "
                      f"round continues there: {self.t001}", out)
        self.assertNotIn("refreshed worktree", out)
        self.assertEqual(edit.read_bytes(), content)
        self.assertEqual(git(self.t001, "rev-parse", "HEAD"), fresh)
        self.assertEqual(base(self.t001), fresh)
        self.assertFalse((self.t001 / "repo" / "later.py").exists())
        self.assertIn(f"- repo: {self.t001}\n",
                      self.payload().read_text(encoding="utf-8"))
        self.assertEqual(git(self._tmp, "worktree", "list", "--porcelain")
                         .count("worktree "), 2)

    def test_the_worktrees_of_closed_tasks_are_removed_on_the_next_emit(
            self):
        rc, _ = self.emit()
        self.assertEqual(rc, 0)
        write(self.spec / "task.md", IMPLEMENTED_T1_TASKS)

        rc, out = self.emit()
        self.assertEqual(rc, 0)
        self.assertIn(f"worktree: removed {self.t001} (T001 is no longer "
                      "open)", out)
        self.assertFalse(self.t001.exists())
        self.assertEqual(git(self._tmp, "worktree", "list", "--porcelain")
                         .count("worktree "), 2)
        self.assertTrue((self.trees / "T002").is_dir())

        # a removal git refuses is said, never taken as done
        (self.trees / "T009").mkdir()
        rc, out = self.emit()
        self.assertEqual(rc, 0)
        self.assertIn(f"worktree: NOT removed {self.trees / 'T009'} (T009 "
                      "is no longer open) — git worktree remove", out)
        self.assertTrue((self.trees / "T009").is_dir())

    def test_a_worktree_git_cannot_build_refuses_the_whole_wave(self):
        boom = engine.specstate.WorktreeError(
            "git worktree add in . exited 128: disk full")
        err = io.StringIO()
        with unittest.mock.patch.object(
                engine.specstate, "worktree_create", side_effect=boom), \
                contextlib.redirect_stderr(err):
            rc, _ = in_process(
                lambda: engine.main([str(self.spec), "--emit-spawns",
                                     "--isolate", "worktree"]), self.tel)
        self.assertEqual(rc, 2, err.getvalue())
        self.assertIn("refused: --isolate worktree — git worktree add in "
                      ". exited 128: disk full", err.getvalue())
        # refused before the wave wrote anything
        self.assertFalse((self.spec / "spawns").exists())

    def test_explain_execute_names_each_worktree_with_what_it_owes(self):
        r = run(self.spec, self.tel, "--explain", "execute")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("isolated worktrees", r.stdout)

        rc, _ = self.emit()
        self.assertEqual(rc, 0)
        claim_by_hand(self.spec, "T001")
        r = run(self.spec, self.tel, "--explain", "execute")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("it is an orphan", r.stdout)
        self.assertIn("  isolated worktrees (the next emit with "
                      "--isolate worktree removes the ones no longer open):",
                      r.stdout)
        self.assertIn(f"    T001  {self.t001} — claimed: the tree the "
                      "task's work is written in — mark.py land merges its "
                      "delta into the main tree, mark.py release discards "
                      "it; an orphaned claim is resumed from this path",
                      r.stdout)

        # only --explain lists them: the report stays as it was
        self.assertNotIn("isolated worktrees",
                         run(self.spec, self.tel).stdout)

        write(self.spec / "task.md", IMPLEMENTED_T1_TASKS)
        r = run(self.spec, self.tel, "--explain", "execute")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"    T001  {self.t001} — no longer open: removable",
                      r.stdout)

    def test_outside_a_git_repository_the_flag_refuses(self):
        plain = Path(tempfile.mkdtemp(prefix="isolated-plain-"))
        self.addCleanup(shutil.rmtree, plain, ignore_errors=True)
        spec = approved_fixture(plain, "beta")

        for mode in (["--emit-spawns"], ["--run"]):
            with self.subTest(mode=mode):
                r = run(spec, self.tel, *mode, "--isolate", "worktree")
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertEqual(r.stdout, "")
                self.assertIn("refused: --isolate worktree needs a git "
                              "repository", r.stderr)
                self.assertIn(f"{plain} is not in one", r.stderr)
                self.assertFalse((spec / "spawns").exists())
                self.assertFalse((spec / "runs").exists())
        self.assertFalse((plain / ".spec-kit").exists())

    def test_the_flag_needs_the_executor_modes(self):
        r = run(self.spec, self.tel, "--explain", "execute", "--isolate",
                "worktree")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("--isolate requires --emit-spawns or --run", r.stderr)
        self.assertFalse((self._tmp / ".spec-kit").exists())

    def test_a_dry_run_plans_the_worktrees_and_a_run_creates_them(self):
        rc, out = self.run_loop(dry_run=True)
        self.assertEqual(rc, 0)
        self.assertIn("worktree: would create — a detached snapshot of the "
                      f"main tree: {self.t001}", out)
        self.assertIn(f"- repo: {self.t001}\n",
                      self.payload().read_text(encoding="utf-8"))
        self.assertFalse((self._tmp / ".spec-kit").exists())

        rc, out = self.run_loop(dry_run=False)
        self.assertEqual(rc, 0)
        self.assertIn("worktree: created — a detached snapshot of the "
                      f"main tree: {self.t001}", out)
        self.assertIn("wave emitted", out)
        self.assertTrue(self.t001.is_dir())

        # a clean worktree is refreshed in the plan too — in the plan only
        landed = write(self._tmp / "repo" / "landed.py", "LANDED = 1\n")
        rc, out = self.run_loop(dry_run=True)
        self.assertEqual(rc, 0)
        self.assertIn(f"would refresh worktree: {self.t001} (clean — would "
                      "be rebuilt from the current tree)", out)
        self.assertNotIn("refreshed worktree: ", out)
        self.assertFalse((self.t001 / "repo" / "landed.py").exists())
        self.assertTrue(landed.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
