"""The cross-spec claim registry — spec-build D-057.

schedule_wave reads one spec's doc state, so two specs executing at once
could edit one file. mark.py now registers every claim it makes in
`specs/.claims/registry.json` under one repo-level lock and drops from a
wave any task whose Touches: overlap a live claim of another spec.

  - a wave task overlapping another spec's live claim is dropped and
    printed `deferred: T### (shares <path> with <spec>/T###)`; the rest
    of the wave is claimed, and once that task lands the same claim
    succeeds;
  - a stale row — its task no longer (in-progress) — is swept and defers
    nothing;
  - a task naming no files defers against another spec's open task that
    names none;
  - land, release, drop and tick remove the spec's row;
  - a held registry lock exits 5, a damaged one exits 1 naming the file,
    and neither writes anything;
  - the lock order: the registry lock is taken outside the spec's
    .task.lock and never inside it;
  - graph.py's emit and explain show the deferral the claim will make.

Fixtures are hand-authored docsets whose TC pass conditions are
deterministic one-liners, two specs under one specs/ tree.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from test_execute_gates import (  # noqa: E402
    HAND_PLAN,
    HAND_RESEARCH,
    HAND_SPEC,
    HAND_TASKS,
    HAND_TECH,
    HAND_TEST,
    record_approval,
    run_graph,
    write,
)
import graph  # noqa: E402 - the replica closure shares the master's behavior
import mark  # noqa: E402
import specstate  # noqa: E402

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
MARK = SCRIPTS / "mark.py"
TICK = SCRIPTS / "tick.py"
CONSTITUTION = SKILL / "examples" / "mini-spec" / "specs" / "CONSTITUTION.md"

DIGEST = ("digest: task T001 · status implemented · files 1 · "
          "commit-line x")
BARE_T001 = ("- [ ] T001 implement the shout helper in the module "
             "(FR-001)\n  - Proves: TC-001\n")
TOUCHING_T001 = BARE_T001.replace(
    "  - Proves", "  - Touches:\n    - `src/greet.py`\n  - Proves")
# two disjoint runnable tasks: T001 shares alpha's file, T002 names another
DISJOINT_TASKS = HAND_TASKS.replace(BARE_T001, TOUCHING_T001).replace(
    "- [ ] T002 (after T001) pin punctuation behavior with a test (FR-002)",
    "- [ ] T002 pin punctuation behavior with a test (FR-002)\n"
    "  - Touches:\n    - `src/other.py`")


def spec_at(specs: Path, name: str, task_md: str) -> Path:
    """An approved hand-authored docset under specs/<name>."""
    d = specs / name
    d.mkdir()
    write(d / "spec.md", HAND_SPEC.format(status="approved"))
    for fname, text in (("research.md", HAND_RESEARCH),
                        ("plan.md", HAND_PLAN),
                        ("tech-spec.md", HAND_TECH),
                        ("task.md", task_md),
                        ("test.md", HAND_TEST)):
        write(d / fname, text)
    record_approval(d)
    return d


def two_specs(tmp: Path, first: str = TOUCHING_T001,
              second: str = TOUCHING_T001) -> tuple[Path, Path]:
    """specs/alpha and specs/beta in one repo, each with T001 runnable
    and task.md's T001 entry as given."""
    specs = tmp / "specs"
    specs.mkdir(parents=True)
    shutil.copy(CONSTITUTION, specs / "CONSTITUTION.md")
    return (spec_at(specs, "alpha", HAND_TASKS.replace(BARE_T001, first)),
            spec_at(specs, "beta", HAND_TASKS.replace(BARE_T001, second)))


def wave(spec_dir: Path, *task_ids: str) -> Path:
    d = spec_dir / "spawns" / "wave-1"
    d.mkdir(parents=True, exist_ok=True)
    for tid in task_ids:
        (d / f"implementer-{tid}.md").write_text("payload\n", encoding="utf-8")
    return d


def run(script: Path, *args, tel: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, KIT_TELEMETRY_DIR=str(tel), KIT_TELEMETRY="on")
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True, timeout=300,
                          env=env)


def ledger_events(spec_dir: Path) -> list[str]:
    path = spec_dir / "runs" / "ledger.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line)["event"]
            for line in path.read_text(encoding="utf-8").splitlines()]


def holder(lock: str, spec_dir: Path, release: Path) -> str:
    """A python -c body holding `specstate.<lock>(spec_dir)` until
    `release` appears, and saying `held` once it does."""
    return ("import sys, time\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "import specstate\n"
            f"with specstate.{lock}({str(spec_dir)!r}):\n"
            "    print('held', flush=True)\n"
            f"    while not __import__('pathlib').Path({str(release)!r})"
            ".exists():\n"
            "        time.sleep(0.02)\n")


class ClaimRegistryTests(unittest.TestCase):

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="claim-registry-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.registry = self._tmp / "specs" / ".claims" / "registry.json"

    def rows(self) -> dict:
        return json.loads(self.registry.read_text(encoding="utf-8"))

    def claim(self, spec_dir: Path, run_id: str) -> subprocess.CompletedProcess:
        return run(MARK, "claim", spec_dir, "--wave", wave(spec_dir, "T001"),
                   "--run-id", run_id, tel=self.tel)

    def test_a_claim_registers_its_task_under_the_specs_tree(self):
        a, _ = two_specs(self._tmp)
        r = self.claim(a, "r-aaaa")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], "claimed 1: T001")
        row = self.rows()["alpha/T001"]
        self.assertEqual(row["run"], "r-aaaa")
        self.assertRegex(row["at"], r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
        self.assertEqual(row["paths"], ["src/greet.py"])
        folder = self.registry.parent
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         [".gitignore", "registry.json"])
        self.assertEqual((folder / ".gitignore").read_text(encoding="utf-8"),
                         "*\n")
        self.assertEqual(ledger_events(a), ["claim"])

    def test_another_specs_live_claim_defers_the_task_until_it_lands(self):
        a, b = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        w = wave(b, "T001")

        r = run(MARK, "claim", b, "--wave", w, "--run-id", "r-bbbb",
                tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("deferred: T001 (shares src/greet.py with alpha/T001)",
                      r.stdout)
        self.assertIn("nothing claimed", r.stdout)
        self.assertNotIn("(in-progress)", (b / "task.md").read_text(
            encoding="utf-8"))
        self.assertEqual(sorted(self.rows()), ["alpha/T001"])
        self.assertEqual(ledger_events(b), [])

        r = run(MARK, "land", a, "T001", "--digest", DIGEST, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(), {})

        r = run(MARK, "claim", b, "--wave", w, "--run-id", "r-bbbb",
                tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("claimed 1: T001", r.stdout)
        self.assertNotIn("deferred", r.stdout)
        self.assertEqual(sorted(self.rows()), ["beta/T001"])
        rows = [json.loads(line) for line in
                (b / "runs" / "ledger.jsonl").read_text(
                    encoding="utf-8").splitlines()]
        self.assertEqual([(row["event"], row["task"], row["run"])
                          for row in rows], [("claim", "T001", "r-bbbb")])

    def test_the_rest_of_the_wave_is_claimed_without_the_task(self):
        a, b = two_specs(self._tmp, second=DISJOINT_TASKS)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        r = run(MARK, "claim", b, "--wave", wave(b, "T001", "T002"),
                "--run-id", "r-bbbb", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("deferred: T001 (shares src/greet.py with alpha/T001)",
                      r.stdout)
        self.assertIn("claimed 1: T002", r.stdout)
        self.assertEqual(sorted(self.rows()), ["alpha/T001", "beta/T002"])
        entries = {e.id: e for e in specstate.task_entries(
            (b / "task.md").read_text(encoding="utf-8"))}
        self.assertTrue(entries["T002"].claimed)
        self.assertFalse(entries["T001"].claimed)

    def test_a_stale_row_is_swept_and_defers_nothing(self):
        a, b = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        # released by hand: the marker and the stamp go, the row stays
        lines = (a / "task.md").read_text(encoding="utf-8").splitlines()
        write(a / "task.md", "\n".join(
            ln.replace(" (in-progress)", "", 1) for ln in lines
            if not specstate.CLAIM_NOTE.match(ln)) + "\n")
        self.assertEqual(sorted(self.rows()), ["alpha/T001"])

        r = self.claim(b, "r-bbbb")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("claimed 1: T001", r.stdout)
        self.assertNotIn("deferred", r.stdout)
        self.assertEqual(sorted(self.rows()), ["beta/T001"])

    def test_a_task_naming_no_files_defers_against_one_naming_none(self):
        a, b = two_specs(self._tmp, first=BARE_T001, second=BARE_T001)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        self.assertEqual(self.rows()["alpha/T001"]["paths"], [])
        r = self.claim(b, "r-bbbb")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("deferred: T001 (alpha/T001 has no parseable "
                      "Touches: and runs alone)", r.stdout)
        self.assertIn("nothing claimed", r.stdout)
        self.assertEqual(sorted(self.rows()), ["alpha/T001"])

    def test_release_removes_the_row(self):
        a, _ = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        r = run(MARK, "release", a, "T001", "--reason", "orphan: dead run",
                tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(), {})

    def test_drop_removes_the_row(self):
        a, _ = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        r = run(MARK, "drop", a, "T001", "--decision", "D-001", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(), {})

    def test_tick_removes_the_row(self):
        a, _ = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        r = run(TICK, a, "--note", "T001 :: pytest green", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(), {})

    def test_a_held_registry_lock_exits_five_and_writes_nothing(self):
        a, b = two_specs(self._tmp)
        release = self._tmp / "release"
        p = subprocess.Popen([sys.executable, "-c",
                              holder("claims_lock", b, release)],
                             stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(p.stdout.readline().strip(), "held")
            r = self.claim(b, "r-bbbb")
            self.assertEqual(r.returncode, 5, r.stdout + r.stderr)
            self.assertIn("lock busy", r.stderr)
            self.assertIn(".claims.lock", r.stderr)
        finally:
            p.kill()
            p.wait()
        self.assertNotIn("(in-progress)", (b / "task.md").read_text(
            encoding="utf-8"))
        self.assertFalse(self.registry.exists())

    def test_a_damaged_registry_exits_one_naming_the_file(self):
        a, b = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        for damage in ("{not json", "[]", '{"alpha/T001": "claimed"}',
                       '{"alpha/T001": {"run": "r-aaaa"}}'):
            with self.subTest(damage=damage):
                write(self.registry, damage)
                r = self.claim(b, "r-bbbb")
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn(str(self.registry), r.stderr)
                self.assertIn("remove or repair it", r.stderr)
                self.assertEqual(self.registry.read_text(encoding="utf-8"),
                                 damage)
        self.assertNotIn("(in-progress)", (b / "task.md").read_text(
            encoding="utf-8"))

    def test_release_refuses_on_a_damaged_registry_before_writing(self):
        a, _ = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        write(self.registry, "{not json")
        r = run(MARK, "release", a, "T001", "--reason", "orphan: dead run",
                tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("remove or repair it", r.stderr)
        self.assertIn("(in-progress)", (a / "task.md").read_text(
            encoding="utf-8"))

    def test_a_damaged_registry_never_undoes_a_landing(self):
        a, _ = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        write(self.registry, "{not json")
        r = run(MARK, "land", a, "T001", "--digest", DIGEST, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)
        self.assertIn("warning: claim registry not updated", r.stderr)
        self.assertIn("remove or repair it", r.stderr)

    def test_a_held_spec_lock_is_a_busy_exit_not_a_deadlock(self):
        a, _ = two_specs(self._tmp)
        w = wave(a, "T001")
        quiet = (unittest.mock.patch.dict(os.environ,
                                          {"KIT_TELEMETRY": "off"}),
                 specstate.task_lock(a),
                 unittest.mock.patch.object(mark, "LOCK_TIMEOUT", 0.3),
                 contextlib.redirect_stdout(io.StringIO()))
        err = io.StringIO()
        with contextlib.ExitStack() as stack:
            for ctx in quiet:
                stack.enter_context(ctx)
            stack.enter_context(contextlib.redirect_stderr(err))
            started = time.monotonic()
            rc = mark.claim(a, w, "r-held")
        self.assertEqual(rc, 5, err.getvalue())
        self.assertLess(time.monotonic() - started, 4)
        self.assertIn("lock busy", err.getvalue())
        # the registry lock was given up with the busy exit
        self.assertFalse((self._tmp / "specs" / ".claims.lock").exists())
        self.assertFalse(self.registry.parent.exists())
        self.assertNotIn("(in-progress)", (a / "task.md").read_text(
            encoding="utf-8"))

    def test_the_registry_lock_is_taken_before_the_spec_lock(self):
        a, _ = two_specs(self._tmp)
        w = wave(a, "T001")
        release = self._tmp / "release"
        p = subprocess.Popen([sys.executable, "-c",
                              holder("claims_lock", a, release)],
                             stdout=subprocess.PIPE, text=True)
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.tel),
                   KIT_TELEMETRY="on")
        claim = subprocess.Popen(
            [sys.executable, str(MARK), "claim", str(a), "--wave", str(w),
             "--run-id", "r-wait"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=env)
        try:
            self.assertEqual(p.stdout.readline().strip(), "held")
            time.sleep(1.0)
            # blocked on the registry lock, the spec lock is not held
            self.assertIsNone(claim.poll())
            self.assertFalse((a / ".task.lock").exists())
            release.touch()
            out, err = claim.communicate(timeout=60)
        finally:
            release.touch()
            p.kill()
            p.wait()
            claim.kill()
            claim.wait()
        self.assertEqual(claim.returncode, 0, out + err)
        self.assertIn("claimed 1: T001", out)
        self.assertEqual(sorted(self.rows()), ["alpha/T001"])

    def test_land_frees_the_spec_lock_before_it_touches_the_registry(self):
        a, _ = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        release = self._tmp / "release"
        p = subprocess.Popen([sys.executable, "-c",
                              holder("claims_lock", a, release)],
                             stdout=subprocess.PIPE, text=True)
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.tel),
                   KIT_TELEMETRY="on")
        land = subprocess.Popen(
            [sys.executable, str(MARK), "land", str(a), "T001", "--digest",
             DIGEST], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=env)
        try:
            self.assertEqual(p.stdout.readline().strip(), "held")
            # land takes the spec lock for its proofs and gives it back
            took = False
            deadline = time.monotonic() + 20
            while land.poll() is None and time.monotonic() < deadline:
                if (a / ".task.lock").exists():
                    took = True
                elif took:
                    break
                time.sleep(0.005)
            self.assertTrue(took, "land never took the spec lock")
            # landed, the spec lock is free, the registry wait is outside it
            self.assertIsNone(land.poll())
            self.assertFalse((a / ".task.lock").exists())
            self.assertIn("(implemented)", (a / "task.md").read_text(
                encoding="utf-8"))
            self.assertEqual(sorted(self.rows()), ["alpha/T001"])
            release.touch()
            out, err = land.communicate(timeout=60)
        finally:
            release.touch()
            p.kill()
            p.wait()
            land.kill()
            land.wait()
        self.assertEqual(land.returncode, 0, out + err)
        self.assertIn("landed T001 (implemented)", out)
        self.assertNotIn("claim registry not updated", err)
        self.assertEqual(self.rows(), {})

    def test_the_emit_and_the_explain_show_the_deferral_the_claim_makes(self):
        a, b = two_specs(self._tmp)
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        r = run_graph(b, "--explain", "execute", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("T001   runnable    deps satisfied — ready for an "
                      "implementer  [deferred: shares src/greet.py with "
                      "alpha/T001]", r.stdout)

        r = run_graph(b, "--state-json", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tasks = {t["id"]: t for t in json.loads(r.stdout)["nodes"]["execute"]
                 ["tasks"]}
        self.assertEqual(tasks["T001"]["state"], "runnable")
        self.assertEqual(tasks["T001"]["deferred"],
                         "shares src/greet.py with alpha/T001")
        self.assertEqual(tasks["T001"]["held_by"], "alpha/T001")

        r = run_graph(b, "--emit-spawns", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AWAITING ORCHESTRATOR: execute", r.stdout)
        self.assertIn("deferred: T001 (shares src/greet.py with alpha/T001)",
                      r.stdout)
        self.assertFalse(list((b / "spawns").rglob("implementer-T*.md")))

    def test_a_headless_wave_runs_only_what_the_claim_took(self):
        a, b = two_specs(self._tmp)
        # the emit saw no other claim; alpha's claim lands before ours
        r = run_graph(b, "--emit-spawns", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        payloads = sorted((b / "spawns").rglob("implementer-T*.md"))
        self.assertEqual([p.name for p in payloads], ["implementer-T001.md"])
        self.assertEqual(self.claim(a, "r-aaaa").returncode, 0)
        ran = self._tmp / "runner-ran"
        runner = write(self._tmp / "runner.py",
                       f"from pathlib import Path\nPath({str(ran)!r})"
                       ".write_text('ran')\n")

        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            rc = graph._headless_execute_wave(
                b, [graph.WrittenPayload(payloads[0], "implementer",
                                         "execute", "sonnet")],
                f"{sys.executable} {runner}", 1, "r-head")
        self.assertIsNone(rc)
        self.assertFalse(ran.exists())
        self.assertNotIn("(in-progress)", (b / "task.md").read_text(
            encoding="utf-8"))
        self.assertNotIn("claim", ledger_events(b))


if __name__ == "__main__":
    unittest.main(verbosity=2)
