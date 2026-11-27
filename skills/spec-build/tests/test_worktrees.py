"""Opt-in worktree-per-task execution — spec-build D-058.

With `graph.py --emit-spawns --isolate worktree` each implementer
works in its own detached worktree, a snapshot of the main tree, and
mark.py closes the task from there:

  - the payload's `- repo:` line is the worktree, under one line making
    it the developer's only working tree;
  - land runs the task's proofs in the worktree, folds the worktree's
    whole delta into the main tree byte-for-byte — working tree only: a
    file staged before stays staged and the index is untouched — and
    removes the worktree;
  - a delta the main tree will not take clean is refused with the
    conflicting paths and both trees named; nothing is written, the
    worktree stays and the task stays claimed, and a later land goes
    through once the tree is settled;
  - release removes the worktree with the claim and the next emit
    builds a fresh one; fail keeps it, and the round's payload reuses
    it;
  - a headless `--run --isolate worktree` lands every task from its
    worktree — a later wave's cut from the tree the earlier landing
    changed — and parks at tick-commit;
  - land proves the worktree, so it refuses while the main tree holds
    an uncommitted change the proofs never saw — one made there since
    the cut, outside what this spec landed; what the tree held at the
    cut, a wave-mate's landed delta and run state never refuse.

Fixtures are one hand-authored docset in a scratch git repository whose
main tree holds uncommitted work and one staged file; T001's proof is
green only in a tree that holds its work.
"""

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from test_claim_registry import (  # noqa: E402
    BARE_T001,
    CONSTITUTION,
    DIGEST,
    DISJOINT_TASKS,
    HAND_PLAN,
    HAND_RESEARCH,
    HAND_SPEC,
    HAND_TASKS,
    HAND_TECH,
    HAND_TEST,
    MARK,
    TOUCHING_T001,
    ledger_events,
    record_approval,
    run,
    run_graph,
    write,
)
import mark  # noqa: E402

IDENTITY = ("-c", "user.name=kit", "-c", "user.email=kit@example.com",
            "-c", "commit.gpgsign=false")
GREET = "def whisper(text):\n    return text.lower()\n"
LANDED = GREET + "\n\ndef wave(s):\n    return s\n"
TREE_PROOF = HAND_TEST.replace(
    "- **Pass condition**: `python3 -c 'print(\"HI\")'` exits 0",
    "- **Pass condition**: `grep -q shout src/greet.py` exits 0")

# The headless developer: it works in the tree the payload names, and
# its second task records, in the spec's run state, whether that tree
# holds the first one's work.
RUNNER = """import re, sys
from pathlib import Path

prompt = Path(sys.argv[1]).read_text(encoding="utf-8")


def head(key):
    return re.search(rf"^- {key}: (.+)$", prompt, re.M).group(1).strip()


spec_dir, worktree = Path(head("spec_dir")), Path(head("repo"))
tid = re.search(r"implementer-(T\\d{3})", prompt).group(1)
wave = re.search(r"# Spawn payload .*? wave (\\d+)", prompt).group(1)
greet = worktree / "src" / "greet.py"
if tid == "T001":
    greet.write_text(greet.read_text(encoding="utf-8")
                     + "\\n\\ndef shout(text):\\n    return text.upper()\\n",
                     encoding="utf-8")
else:
    (spec_dir / f".saw-shout-{tid}").write_text(
        str("def shout" in greet.read_text(encoding="utf-8")),
        encoding="utf-8")
digests = spec_dir / "digests" / f"wave-{wave}"
digests.mkdir(parents=True, exist_ok=True)
(digests / f"implementer-{tid}.md").write_text(
    "tools: Read, Grep, Glob, Bash, Write, Edit\\n"
    f"digest: task {tid} · status implemented · files 1 · commit-line "
    "feat: T### · deviation none · note none\\n", encoding="utf-8")
"""


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *IDENTITY, *args], check=True,
        capture_output=True, text=True).stdout.rstrip("\n")


def scratch_repo(tmp: Path) -> Path:
    """An approved hand-authored docset under specs/alpha in a git
    repository whose main tree then takes uncommitted work — a tracked
    edit, an untracked file, a deletion — and one staged file."""
    repo = tmp / "repo"
    (repo / "specs").mkdir(parents=True)
    shutil.copy(CONSTITUTION, repo / "specs" / "CONSTITUTION.md")
    spec = repo / "specs" / "alpha"
    spec.mkdir()
    write(spec / "spec.md", HAND_SPEC.format(status="approved"))
    for fname, text in (("research.md", HAND_RESEARCH),
                        ("plan.md", HAND_PLAN),
                        ("tech-spec.md", HAND_TECH),
                        ("task.md", HAND_TASKS.replace(BARE_T001,
                                                       TOUCHING_T001)),
                        ("test.md", TREE_PROOF)):
        write(spec / fname, text)
    record_approval(spec)
    (repo / "src").mkdir()
    write(repo / "src" / "greet.py", GREET)
    write(repo / "stale.txt", "deleted before the wave\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "the approved docset")
    write(repo / "src" / "greet.py", LANDED)
    write(repo / "untracked.md", "landed by an earlier task, not committed\n")
    (repo / "stale.txt").unlink()
    write(repo / "staged.txt", "staged before the landing\n")
    git(repo, "add", "staged.txt")
    return spec


class IsolatedWorktreeTests(unittest.TestCase):

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="isolated-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = scratch_repo(self._tmp)
        self.repo = self._tmp / "repo"
        self.worktree = self.repo / ".spec-kit" / "worktrees" / "alpha" / "T001"
        self.greet = self.repo / "src" / "greet.py"

    def land(self) -> subprocess.CompletedProcess:
        return run(MARK, "land", self.spec, "T001", "--digest", DIGEST,
                   tel=self.tel)

    def claimed(self) -> Path:
        """The wave emitted under isolation and claimed — T001
        `(in-progress)`, its worktree on disk; the payload's path."""
        r = run_graph(self.spec, "--emit-spawns", "--isolate", "worktree",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        payload = next((self.spec / "spawns").rglob("implementer-T001.md"))
        r = run(MARK, "claim", self.spec, "--wave", payload.parent,
                "--run-id", "r-aaaa", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.worktree.is_dir())
        return payload

    def develop(self) -> dict[str, bytes | None]:
        """The developer's work in the worktree: {path: bytes} for every
        path it touched, None for the one it deleted."""
        wt = self.worktree
        write(wt / "src" / "greet.py", LANDED
              + "\n\ndef shout(text):\n    return text.upper()\n")
        write(wt / "src" / "shout.py", "from greet import shout\n")
        os.chmod(wt / "src" / "shout.py", 0o755)
        (wt / "docs").mkdir()
        write(wt / "docs" / "guide.md", "# Shout\n")
        (wt / "src" / "blob.bin").write_bytes(bytes(range(256)) * 4
                                             + b"\x00\xff")
        (wt / "untracked.md").unlink()
        return {"src/greet.py": (wt / "src" / "greet.py").read_bytes(),
                "src/shout.py": (wt / "src" / "shout.py").read_bytes(),
                "docs/guide.md": (wt / "docs" / "guide.md").read_bytes(),
                "src/blob.bin": (wt / "src" / "blob.bin").read_bytes(),
                "untracked.md": None}

    def test_land_merges_the_delta_into_the_main_tree_and_spares_the_index(
            self):
        payload = self.claimed()
        text = payload.read_text(encoding="utf-8")
        self.assertIn(f"- spec_dir: {self.spec}\n- repo: {self.worktree}\n"
                      "- isolated worktree: ", text)
        self.assertEqual(sum(ln.startswith("- isolated worktree: ")
                             for ln in text.splitlines()), 1)
        self.assertIn("is your ONLY working tree", text)
        done = self.develop()
        head, refs = git(self.repo, "rev-parse", "HEAD"), git(
            self.repo, "for-each-ref")
        index = (self.repo / ".git" / "index").read_bytes()

        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"worktree {self.worktree}: 5 path(s) merged into "
                      f"{self.repo} — working tree only: nothing staged, "
                      "nothing committed; worktree removed", r.stdout)
        self.assertIn("landed T001 (implemented)", r.stdout)

        # byte-for-byte, the executable bit with it
        for rel, content in done.items():
            path = self.repo / rel
            if content is None:
                self.assertFalse(path.exists(), rel)
            else:
                self.assertEqual(path.read_bytes(), content, rel)
        shout = self.repo / "src" / "shout.py"
        self.assertEqual(stat.S_IMODE(shout.stat().st_mode), 0o755)

        # the working tree alone: what was staged is staged as it was
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), index)
        status = git(self.repo, "status", "--porcelain").splitlines()
        self.assertIn("A  staged.txt", status)
        self.assertIn(" M src/greet.py", status)
        self.assertIn("?? src/shout.py", status)
        self.assertFalse([ln for ln in status if ".spec-kit" in ln], status)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), head)
        self.assertEqual(git(self.repo, "for-each-ref"), refs)

        # the worktree is gone, the self-ignore stays
        self.assertFalse((self.repo / ".spec-kit" / "worktrees").exists())
        self.assertEqual((self.repo / ".spec-kit" / ".gitignore")
                         .read_text(encoding="utf-8"), "*\n")
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain")
                         .count("worktree "), 1)

    def test_land_proves_the_worktree_however_the_main_tree_reads(self):
        self.claimed()
        # TC-001 (`grep -q shout src/greet.py`) is red in both trees
        r = self.land()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(f"proofs for T001: running its TC commands in the "
                      f"worktree {self.worktree}", r.stdout)
        self.assertIn("proofs red for T001", r.stdout)
        self.assertNotIn("(implemented)", (self.spec / "task.md")
                         .read_text(encoding="utf-8"))

        # fixed in the main tree alone: refused before the proofs —
        # work the worktree's proofs never ran on does not land
        write(self.greet, LANDED + "\n\ndef shout(text):\n"
                  "    return text.upper()\n")
        r = self.land()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("proofs never ran on it — 1 path(s):\n  src/greet.py",
                      r.stderr)
        self.assertNotIn("proofs for T001", r.stdout)
        self.assertTrue(self.worktree.is_dir())

        # fixed where the developer works: green there, landed from there
        write(self.greet, LANDED)
        write(self.worktree / "src" / "greet.py",
              LANDED + "\n\ndef shout(text):\n    return text.upper()\n")
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)
        self.assertIn("def shout", self.greet.read_text(encoding="utf-8"))
        self.assertFalse(self.worktree.exists())

    def test_a_conflicting_delta_is_refused_with_its_paths_and_keeps_the_tree(
            self):
        self.claimed()
        done = self.develop()
        # the main tree moved on two of the delta's paths since the
        # snapshot — committed by someone else, so the refusal is the
        # delta's, not the unproven work's
        write(self.greet, "def whisper(text):\n    return text\n")
        write(self.repo / "src" / "shout.py", "someone else's shout\n")
        git(self.repo, "add", "src/greet.py", "src/shout.py")
        git(self.repo, "commit", "-qm", "someone else's shout")
        index = (self.repo / ".git" / "index").read_bytes()

        r = self.land()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("refused: T001's worktree delta does not apply to the "
                      "main tree — 2 conflicting path(s):\n"
                      "  src/greet.py\n  src/shout.py\n", r.stderr)
        self.assertIn(f"  worktree: {self.worktree}\n"
                      f"  main tree: {self.repo}\n"
                      "nothing was written; the worktree stays and the task "
                      "stays claimed — settle by hand, then land again or "
                      "release", r.stderr)
        self.assertNotIn("landed", r.stdout)

        # nothing was written on either side
        self.assertEqual(self.greet.read_text(encoding="utf-8"),
                         "def whisper(text):\n    return text\n")
        self.assertEqual((self.repo / "src" / "shout.py")
                         .read_text(encoding="utf-8"),
                         "someone else's shout\n")
        self.assertTrue((self.repo / "untracked.md").exists())
        self.assertFalse((self.repo / "docs").exists())
        for rel, content in done.items():
            path = self.worktree / rel
            if content is None:
                self.assertFalse(path.exists(), rel)
            else:
                self.assertEqual(path.read_bytes(), content, rel)
        self.assertIn("(in-progress)", (self.spec / "task.md")
                      .read_text(encoding="utf-8"))
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), index)

        # settled by hand — the main tree gives up its two edits — and
        # the same landing goes through
        write(self.greet, LANDED)
        (self.repo / "src" / "shout.py").unlink()
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)
        self.assertFalse(self.worktree.exists())

    def test_release_discards_the_worktree_and_the_next_emit_builds_a_fresh_one(
            self):
        self.claimed()
        self.develop()

        r = run(MARK, "release", self.spec, "T001", "--reason",
                "orphan: dead run", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"released T001 — claim cleared (orphan); its "
                      f"worktree {self.worktree} is removed with the work "
                      "in it — the next emit re-spawns it in a fresh one",
                      r.stdout)
        self.assertFalse(self.worktree.exists())
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain")
                         .count("worktree "), 1)
        self.assertNotIn("shout", self.greet.read_text(encoding="utf-8"))
        self.assertFalse((self.repo / "src" / "shout.py").exists())

        self.claimed()
        self.assertNotIn("shout", (self.worktree / "src" / "greet.py")
                         .read_text(encoding="utf-8"))
        self.assertFalse((self.worktree / "src" / "shout.py").exists())

    def test_fail_keeps_the_worktree_and_the_rounds_payload_reuses_it(self):
        self.claimed()
        self.develop()
        digest = "E   AssertionError: shout('hi') == 'hi'"
        evidence = write(self._tmp / "ev.txt",
                         f"$ python3 -m pytest\n{digest}\n")

        r = run(MARK, "fail", self.spec, "T001", "--evidence", str(evidence),
                "--digest", digest, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"worktree kept: {self.worktree} — the round "
                      "continues there", r.stdout)
        self.assertTrue((self.worktree / "src" / "shout.py").is_file())

        r = run_graph(self.spec, "--emit-spawns", "--isolate", "worktree",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("worktree: kept — it holds uncommitted work; the "
                      f"round continues there: {self.worktree}", r.stdout)
        payload = next((self.spec / "spawns").rglob("implementer-T001.md"))
        self.assertIn(f"- repo: {self.worktree}\n",
                      payload.read_text(encoding="utf-8"))

    def test_an_unchanged_worktree_merges_nothing_and_says_so(self):
        self.claimed()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            refused = mark._merge_worktree("T001", self.repo, self.worktree)
        self.assertIsNone(refused)
        self.assertIn(f"worktree {self.worktree}: nothing to merge — the "
                      "worktree holds no change (the task needed none: "
                      "already-satisfied, or a proof green without an "
                      "edit); worktree removed",
                      out.getvalue())
        self.assertFalse(self.worktree.exists())
        self.assertEqual(self.greet.read_text(encoding="utf-8"), LANDED)

    def test_land_refuses_the_work_left_in_the_main_tree(self):
        # green where the proofs run: only the main tree's edit tells
        # this landing from an unproven one
        shout = LANDED + "\n\ndef shout(text):\n    return text.upper()\n"
        write(self.greet, shout)
        self.claimed()
        write(self.greet, shout.replace("upper()", "upper() + '!'"))

        r = self.land()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("landed", r.stdout)
        self.assertIn(
            "refused: T001 cannot land — the main tree changed since its "
            "worktree was cut, outside what this spec landed, so its "
            "proofs never ran on it — 1 path(s):\n"
            "  src/greet.py\n"
            f"  worktree: {self.worktree}\n  main tree: {self.repo}\n"
            "nothing was written; the worktree stays and the task stays "
            "claimed — move the work into the worktree, or commit or stash "
            "what is not this task's, and land again", r.stderr)
        self.assertIn("(in-progress)", (self.spec / "task.md")
                      .read_text(encoding="utf-8"))
        self.assertTrue(self.worktree.is_dir())
        self.assertNotIn("land", ledger_events(self.spec))

        # the main tree as it was cut: the worktree holds no change and
        # the landing needs no delta
        write(self.greet, shout)
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)

    def test_land_refuses_a_main_tree_edited_since_the_cut(self):
        self.claimed()
        self.develop()
        # someone else's uncommitted work beside the task's — untracked
        # and tracked
        write(self.repo / "notes-unrelated.md", "a note\n")
        write(self.repo / "stale.txt", "back\n")

        r = self.land()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("proofs never ran on it — 2 path(s):\n"
                      "  notes-unrelated.md\n  stale.txt\n", r.stderr)
        self.assertIn("commit or stash", r.stderr)
        self.assertNotIn("landed", r.stdout)
        self.assertNotIn("shout", self.greet.read_text(encoding="utf-8"))
        self.assertIn("(in-progress)", (self.spec / "task.md")
                      .read_text(encoding="utf-8"))
        self.assertTrue(self.worktree.is_dir())

        # settled — committed — and the same landing goes through
        git(self.repo, "add", "notes-unrelated.md", "stale.txt")
        git(self.repo, "commit", "-qm", "an unrelated note")
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)
        self.assertIn("def shout", self.greet.read_text(encoding="utf-8"))

    def test_a_wave_mates_landing_does_not_refuse_the_next_one(self):
        # two file-disjoint tasks in one wave: both worktrees are cut
        # before either lands, so the first landing's delta sits in the
        # main tree when the second lands — work this spec proved
        write(self.spec / "task.md", DISJOINT_TASKS)
        record_approval(self.spec)
        runner = write(self._tmp / "runner.py", RUNNER)

        r = run_graph(self.spec, "--span", "execute", "--run", "--isolate",
                      "worktree", "--runner",
                      f"{sys.executable} {runner} {{prompt_file}}",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("cannot land", r.stderr)
        self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        tasks = (self.spec / "task.md").read_text(encoding="utf-8")
        self.assertEqual(tasks.count("(implemented)"), 2, tasks)
        self.assertIn("def shout", self.greet.read_text(encoding="utf-8"))
        landed = json.loads((self.repo / ".spec-kit" / "landed" / "alpha.json")
                            .read_text(encoding="utf-8"))
        blob = git(self.repo, "hash-object", "src/greet.py")
        self.assertEqual(landed["T001"], {"src/greet.py": f"100644 {blob}"})

    def test_land_reads_the_digest_written_in_the_main_tree(self):
        payload = self.claimed()
        self.develop()
        folder = self.spec / "digests" / payload.parent.name
        folder.mkdir(parents=True)
        digest = write(folder / "implementer-T001.md",
                       "tools: Read, Grep, Glob, Bash, Write, Edit\n"
                       "digest: task T001 · status implemented · files 2 · "
                       "commit-line feat: T001 · deviation none · note "
                       "none\n")
        # run state the round leaves in the main tree's spec dir
        (self.spec / "notes").mkdir()
        write(self.spec / "notes" / "T001.md", "# Notes: T001\n")

        r = run(MARK, "land", self.spec, "T001", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)
        # the file on disk was the evidence — not a --digest override —
        # so the sweep's line is on it
        self.assertEqual(digest.read_text(encoding="utf-8").count(
            "provenance:"), 1)
        self.assertFalse(self.worktree.exists())

    def test_drop_discards_the_worktree_with_the_task(self):
        self.claimed()
        self.develop()

        r = run(MARK, "drop", self.spec, "T001", "--decision", "D-001",
                tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"dropped T001 (D-001) — struck in task.md, the "
                      f"decision stays visible; its worktree {self.worktree} "
                      "is removed with the work in it", r.stdout)
        self.assertIn("~~T001~~ dropped", (self.spec / "task.md")
                      .read_text(encoding="utf-8"))
        self.assertFalse(self.worktree.exists())
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain")
                         .count("worktree "), 1)
        self.assertNotIn("shout", self.greet.read_text(encoding="utf-8"))
        self.assertFalse((self.repo / "src" / "shout.py").exists())

    def test_a_worktree_git_will_not_remove_does_not_undo_the_drop(self):
        self.claimed()
        self.develop()
        git(self.repo, "worktree", "lock", str(self.worktree))

        r = run(MARK, "drop", self.spec, "T001", "--decision", "D-001",
                tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("~~T001~~ dropped", (self.spec / "task.md")
                      .read_text(encoding="utf-8"))
        self.assertIn(f"dropped T001 (D-001) — struck in task.md, the "
                      "decision stays visible; its worktree "
                      f"{self.worktree} is NOT removed", r.stdout)
        self.assertIn(f"warning: the worktree was NOT removed — ", r.stderr)
        self.assertIn(f"git worktree remove --force {self.worktree}",
                      r.stderr)
        self.assertTrue(self.worktree.is_dir())

    def test_a_headless_run_lands_every_task_from_its_worktree(self):
        runner = write(self._tmp / "runner.py", RUNNER)

        r = run_graph(self.spec, "--span", "execute", "--run", "--isolate",
                      "worktree", "--runner",
                      f"{sys.executable} {runner} {{prompt_file}}",
                      tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        self.assertEqual(r.stdout.count("worktree: created"), 2, r.stdout)
        tasks = (self.spec / "task.md").read_text(encoding="utf-8")
        self.assertEqual(tasks.count("(implemented)"), 2, tasks)
        self.assertNotIn("(in-progress)", tasks)
        self.assertIn("def shout", self.greet.read_text(encoding="utf-8"))
        # the second wave's worktree was cut from a main tree that
        # already held the first landing, still uncommitted
        self.assertEqual((self.spec / ".saw-shout-T002")
                         .read_text(encoding="utf-8"), "True")
        self.assertFalse((self.repo / ".spec-kit" / "worktrees").exists())
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain")
                         .count("worktree "), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
