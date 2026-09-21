"""Tests for tools/sync.sh — the shared installer's safety behavior.

sync.sh installs into real dotfile roots, so these tests never run it
against the live HOME: each test builds a bounded repo fixture (the
files sync.sh actually consumes — SYNC_CORPUS below) in a temp dir and
points HOME at a fresh temp dir, then exercises the provenance
guarantees against the copy — fresh install, idempotence, foreign-file
refusal (skills trees and command roots), stale-own cleanup via the
ledger, absent-harness skips, version-drift detection, zero-write
on a late collision (the all-root preflight, FR-002), and the no-write
--dry-run/--check modes (FR-009).
"""
import hashlib
import io
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER = ".spec-dev-kit-deployed"

# Bounded corpus: exactly what sync.sh consumes, so a run costs spawns
# not bytes. The invoked tools; the skill's consumable surfaces (tree
# files the tests reference, the allowlisted command set, one role plus
# its shared prose, the workflow masters); the committed agy persona
# the verify pass byte-compares. Behavior fidelity is per-file; corpus
# size is not load-bearing.
SKILL = "skills/spec-to-prod"
SYNC_CORPUS = (
    "tools/sync.sh",
    "tools/ownership.py",
    "tools/omp-defs.py",
    "tools/agent-defs.py",
    "tools/workflow-defs.py",
    "tools/install-workflow.sh",
    f"{SKILL}/SKILL.md",
    f"{SKILL}/VERSION",
    f"{SKILL}/scripts/tick.py",
    f"{SKILL}/scripts/graph.py",
    f"{SKILL}/commands/extra.txt",
    f"{SKILL}/commands/spec-to-prod.md",
    f"{SKILL}/commands/spec.md",
    f"{SKILL}/commands/plan.md",
    f"{SKILL}/commands/build.md",
    f"{SKILL}/commands/test.md",
    f"{SKILL}/commands/review.md",
    f"{SKILL}/commands/ship.md",
    f"{SKILL}/agents/spec-surveyor.md",
    f"{SKILL}/agents/_shared-protocol.md",
    f"{SKILL}/workflows/spec-run.dwf.ts",
    f"{SKILL}/workflows/spec-run.js",
    "agents/spec-surveyor.md",
)


class SyncShBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="syncsh-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        for rel in SYNC_CORPUS:
            dest = self.repo / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            # copy2 keeps modes — the X_OK assertions ride on them
            shutil.copy2(REPO_ROOT / rel, dest)
        self.home = self.tmp / "home"
        self.home.mkdir()

    def run_sync(self, *argv):
        return subprocess.run(
            ["bash", str(self.repo / "tools" / "sync.sh"), *argv],
            env=dict(os.environ, HOME=str(self.home)),
            capture_output=True, text=True, timeout=300)

    def skill_root(self, *parts):
        return self.home.joinpath(".claude", "skills", "spec-to-prod", *parts)

    def home_snapshot(self):
        """relpath -> sha256 for every file under the temp HOME."""
        return {
            str(p.relative_to(self.home)):
                hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(self.home.rglob("*")) if p.is_file()
        }

    def plan_kinds(self, out):
        """Decision kinds from a --dry-run's `plan  <kind> <path>` lines."""
        return [line.split()[1] for line in out.splitlines()
                if line.startswith("plan  ")]


class SyncShTests(SyncShBase):
    def test_fresh_install_is_clean_and_idempotent(self):
        r1 = self.run_sync()
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        self.assertTrue((self.skill_root("SKILL.md")).is_file())
        # extra.txt bare name landed in a command root
        self.assertTrue(
            (self.home / ".agents" / "commands" / "build.md").is_file())
        # skills-tree provenance ledger exists and is excluded from verify
        self.assertTrue(self.skill_root(LEDGER).is_file())
        # atomic replacement preserves the shipped executable bits
        self.assertTrue(
            os.access(self.skill_root("scripts", "tick.py"), os.X_OK))
        r2 = self.run_sync()
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        # FR-007: no installer scratch survives a completed apply
        self.assertEqual(list(self.home.rglob(f"{LEDGER}.tmp*")), [])

    def test_installer_scratch_leftover_is_not_a_foreign_file(self):
        # Atomic replacement (FR-007) stages through LEDGER_NAME-prefixed
        # scratch in the destination's own directory; a leftover from a
        # killed run sits in the namespace every classifier excludes, so
        # it can never wedge the next sync as a "foreign file".
        self.assertEqual(self.run_sync().returncode, 0)
        scratch = self.skill_root(f"{LEDGER}.tmp-SKILL.md.tmp")
        scratch.write_text("partial bytes from a killed run\n")
        deep = self.skill_root("scripts", f"{LEDGER}.tmp-graph.py.tmp")
        deep.write_text("partial bytes\n")
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("REFUSE", r.stdout)
        self.assertIn("partial bytes", scratch.read_text())  # inert, not adopted

    def test_command_update_replaces_content_and_ledger_atomically(self):
        self.assertEqual(self.run_sync().returncode, 0)
        root = self.home / ".agents" / "commands"
        dest = root / "build.md"
        master = (self.repo / "skills" / "spec-to-prod"
                  / "commands" / "build.md")
        master.write_text(
            master.read_text() + "\n<!-- touched by master -->\n")
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("touched by master", dest.read_text())
        entries = [line for line in (root / LEDGER).read_text().splitlines()
                   if line.endswith(" build")]
        self.assertEqual(
            entries,
            [f"{hashlib.sha256(dest.read_bytes()).hexdigest()} build"])

    def test_foreign_file_in_skills_tree_is_refused_and_kept(self):
        self.assertEqual(self.run_sync().returncode, 0)
        foreign = self.skill_root("scripts", "zzz-foreign.py")
        foreign.write_text("# not ours\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertTrue(foreign.is_file())  # never clobbered

    def test_same_path_foreign_file_in_skills_tree_is_refused_and_kept(self):
        self.assertEqual(self.run_sync().returncode, 0)
        dest = self.skill_root("scripts", "graph.py")
        dest.write_text(dest.read_text() + "# hand-edited\n")
        ledger_before = self.skill_root(LEDGER).read_text()
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("hand-edited", dest.read_text())  # never clobbered
        # the refused tree's ledger is not rewritten either
        self.assertEqual(self.skill_root(LEDGER).read_text(), ledger_before)

    def test_same_path_owned_update_is_applied(self):
        self.assertEqual(self.run_sync().returncode, 0)
        master = (self.repo / "skills" / "spec-to-prod"
                  / "scripts" / "tick.py")
        master.write_text(master.read_text() + "# touched by master\n")
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dest = (self.home / ".zcode" / "skills" / "spec-to-prod"
                / "scripts" / "tick.py")
        self.assertIn("# touched by master", dest.read_text())

    def test_stale_delete_refused_when_current_hash_drifted(self):
        # deletion authority is the CURRENT hash matching the ledgered
        # deployed hash — a post-deploy hand-edit makes it foreign
        self.assertEqual(self.run_sync().returncode, 0)
        (self.repo / "skills" / "spec-to-prod"
         / "scripts" / "tick.py").unlink()
        dest = (self.home / ".zcode" / "skills" / "spec-to-prod"
                / "scripts" / "tick.py")
        dest.write_text(dest.read_text() + "# hand-edited after deploy\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("hand-edited after deploy", dest.read_text())

    def test_foreign_file_blocks_stale_removal_in_same_tree(self):
        # a foreign file anywhere in the tree defers every removal too
        self.assertEqual(self.run_sync().returncode, 0)
        (self.repo / "skills" / "spec-to-prod"
         / "scripts" / "tick.py").unlink()
        zcode_skill = (self.home / ".zcode" / "skills" / "spec-to-prod")
        foreign = zcode_skill / "scripts" / "graph.py"
        foreign.write_text(foreign.read_text() + "# hand-edited\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        # stale-own tick.py survives: nothing is removed from a tree
        # that holds a foreign file
        self.assertTrue((zcode_skill / "scripts" / "tick.py").is_file())
        self.assertIn("hand-edited", foreign.read_text())

    def test_stale_own_file_is_cleaned_via_ledger(self):
        self.assertEqual(self.run_sync().returncode, 0)
        dest = (self.home / ".zcode" / "skills" / "spec-to-prod"
                / "scripts" / "tick.py")
        self.assertTrue(dest.is_file())
        # master (the repo copy) drops the file: ledger proves we shipped
        # it, so the next sync removes it instead of refusing
        (self.repo / "skills" / "spec-to-prod" / "scripts" / "tick.py").unlink()
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("clean", r.stdout)
        self.assertFalse(dest.exists())

    def test_foreign_file_in_commands_root_is_refused(self):
        self.assertEqual(self.run_sync().returncode, 0)
        cmd = self.home / ".claude" / "commands" / "plan.md"
        cmd.write_text("# a hand-written note, not the wrapper\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("hand-written note", cmd.read_text())

    def test_foreign_def_in_claude_agents_root_is_refused(self):
        self.assertEqual(self.run_sync().returncode, 0)
        dest = self.home / ".claude" / "agents" / "spec-surveyor.md"
        dest.write_text("---\nname: spec-surveyor\n---\nhand-edited\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("hand-edited", dest.read_text())

    def test_absent_harness_homes_are_skipped_not_created(self):
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("skip", r.stdout)
        self.assertFalse((self.home / ".config" / "opencode").exists())
        self.assertFalse((self.home / ".factory").exists())

    def test_version_drift_fails_the_sync(self):
        (self.repo / "skills" / "spec-to-prod" / "VERSION").write_text("9.9.9\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DRIFT", r.stdout)

    def test_oversized_description_fails_the_sync(self):
        # zcode/claude loaders reject descriptions over 1024 chars — the
        # skill silently fails to register; sync must catch it first
        sk = self.repo / "skills" / "spec-to-prod" / "SKILL.md"
        sk.write_text(sk.read_text().replace(
            "\nmetadata:", "\n  " + "x" * 1100 + "\nmetadata:", 1))
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("1024", r.stdout)

    def test_late_skills_root_collision_writes_nothing_anywhere(self):
        # A pending master update plus a hand-edit collision in the LAST
        # skills root must not half-update the earlier roots: the
        # preflight plans all roots first, so the whole HOME — content
        # and ledgers — stays byte-identical and the run exits nonzero.
        self.assertEqual(self.run_sync().returncode, 0)
        master = (self.repo / "skills" / "spec-to-prod"
                  / "scripts" / "tick.py")
        master.write_text(master.read_text() + "# touched by master\n")
        late = (self.home / ".omp" / "agent" / "skills" / "spec-to-prod"
                / "scripts" / "tick.py")
        late.write_text(late.read_text() + "# hand-edited\n")
        before = self.home_snapshot()
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("PREFLIGHT FAILED", r.stdout)
        self.assertIn("hand-edited", late.read_text())
        first = (self.home / ".agents" / "skills" / "spec-to-prod"
                 / "scripts" / "tick.py")
        self.assertNotIn("touched by master", first.read_text())
        self.assertEqual(self.home_snapshot(), before)

    def test_late_omp_def_collision_writes_nothing_anywhere(self):
        # Same zero-write contract through the omp defs root, whose
        # per-skill manifest is that plan's ledger: a hand-edited def
        # there refuses before any other destination is touched.
        self.assertEqual(self.run_sync().returncode, 0)
        master = (self.repo / "skills" / "spec-to-prod"
                  / "scripts" / "tick.py")
        master.write_text(master.read_text() + "# touched by master\n")
        late = self.home / ".omp" / "agent" / "agents" / "spec-surveyor.md"
        late.write_text(late.read_text() + "\nhand-edited\n")
        before = self.home_snapshot()
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("PREFLIGHT FAILED", r.stdout)
        self.assertIn("hand-edited", late.read_text())
        self.assertEqual(self.home_snapshot(), before)

    def test_late_collision_on_fresh_install_creates_nothing(self):
        # A foreign file in the last-planned command root (droid, gated
        # on ~/.factory existing) must cost zero writes on a fresh
        # install: not even the first skill root gets created.
        (self.home / ".factory" / "commands").mkdir(parents=True)
        foreign = self.home / ".factory" / "commands" / "build.md"
        foreign.write_text("# a hand-written note, not the wrapper\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("PREFLIGHT FAILED", r.stdout)
        self.assertIn("hand-written note", foreign.read_text())
        for root in (".agents", ".claude", ".zcode", ".omp"):
            self.assertFalse((self.home / root).exists(), root)

    def test_dry_run_reports_the_plan_and_writes_nothing(self):
        # FR-009: --dry-run prints the planner's create/update/unchanged/
        # delete/refuse decisions and touches no destination — a fresh
        # HOME stays completely empty.
        r = self.run_sync("--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        kinds = self.plan_kinds(r.stdout)
        self.assertIn("create", kinds)
        self.assertNotIn("refuse", kinds)
        self.assertEqual(list(self.home.rglob("*")), [])
        # once installed, the same plan reports unchanged and nothing
        # else — plan-level idempotence, still zero writes
        self.assertEqual(self.run_sync().returncode, 0)
        before = self.home_snapshot()
        r2 = self.run_sync("--dry-run")
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertEqual(set(self.plan_kinds(r2.stdout)), {"unchanged"})
        self.assertEqual(self.home_snapshot(), before)

    def test_dry_run_reports_update_delete_refuse_and_writes_nothing(self):
        self.assertEqual(self.run_sync().returncode, 0)
        master = (self.repo / "skills" / "spec-to-prod"
                  / "scripts" / "tick.py")
        master.write_text(master.read_text() + "# touched by master\n")
        (self.repo / "skills" / "spec-to-prod"
         / "scripts" / "graph.py").unlink()
        foreign = self.skill_root("scripts", "zzz-foreign.py")
        foreign.write_text("# not ours\n")
        before = self.home_snapshot()
        r = self.run_sync("--dry-run")
        self.assertNotEqual(r.returncode, 0)
        kinds = self.plan_kinds(r.stdout)
        self.assertIn("update", kinds)
        self.assertIn("delete", kinds)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("PREFLIGHT FAILED", r.stdout)
        # nothing the plan describes was applied
        self.assertNotIn("touched by master",
                         self.skill_root("scripts", "tick.py").read_text())
        self.assertTrue(self.skill_root("scripts", "graph.py").is_file())
        self.assertTrue(foreign.is_file())
        self.assertEqual(self.home_snapshot(), before)

    def test_check_reports_drift_and_writes_nothing(self):
        # nothing installed yet: every destination is MISSING, and the
        # check creates none of them
        r = self.run_sync("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("MISSING", r.stdout)
        self.assertEqual(list(self.home.rglob("*")), [])
        # installed and current: clean, twice, zero writes
        self.assertEqual(self.run_sync().returncode, 0)
        before = self.home_snapshot()
        for _ in range(2):
            ok = self.run_sync("--check")
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertIn("OK", ok.stdout)
            self.assertEqual(self.home_snapshot(), before)
        # a master that moved on is DRIFT — reported, never applied
        master = (self.repo / "skills" / "spec-to-prod"
                  / "scripts" / "tick.py")
        master.write_text(master.read_text() + "# touched by master\n")
        r2 = self.run_sync("--check")
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn("DRIFT", r2.stdout)
        self.assertNotIn("touched by master",
                         self.skill_root("scripts", "tick.py").read_text())
        self.assertEqual(self.home_snapshot(), before)
        # a hand-edited owned file is refused by the preflight and kept
        dest = self.skill_root("scripts", "tick.py")
        edited = dest.read_text() + "# hand-edited\n"
        dest.write_text(edited)
        after_edit = self.home_snapshot()
        r3 = self.run_sync("--check")
        self.assertNotEqual(r3.returncode, 0)
        self.assertIn("REFUSE", r3.stdout)
        self.assertEqual(dest.read_text(), edited)
        self.assertEqual(self.home_snapshot(), after_edit)

    def test_mode_flags_are_validated_before_anything_runs(self):
        self.assertEqual(self.run_sync("--bogus").returncode, 2)
        self.assertEqual(
            self.run_sync("--dry-run", "--check").returncode, 2)
        self.assertEqual(list(self.home.rglob("*")), [])


class DroidCommandsTests(SyncShBase):
    """Factory Droid's own command root (~/.factory/commands) — gated on
    the harness home existing (never fabricated), same provenance-ledger
    discipline as the other command roots, kept as a separate sync.sh
    block (D-017)."""

    def test_absent_factory_home_skips_loudly(self):
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("skip  droid commands", r.stdout)
        self.assertFalse((self.home / ".factory" / "commands").exists())

    def test_commands_install_when_factory_home_exists(self):
        (self.home / ".factory").mkdir()
        r1 = self.run_sync()
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        for base in ("spec", "plan", "build", "test", "review", "ship",
                     "spec-to-prod"):
            self.assertTrue(
                (self.home / ".factory" / "commands" / f"{base}.md").is_file(),
                base)
        self.assertTrue(
            (self.home / ".factory" / "commands" / LEDGER).is_file())
        r2 = self.run_sync()
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

    def test_foreign_file_in_droid_commands_is_refused(self):
        (self.home / ".factory").mkdir()
        self.assertEqual(self.run_sync().returncode, 0)
        dest = self.home / ".factory" / "commands" / "build.md"
        dest.write_text("# a hand-written note, not the wrapper\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("hand-written note", dest.read_text())


def _run_one(task):
    """Run one (ClassName, method) case; return (ClassName, method, ok,
    runner output). Module-level for spawn pickling; the child re-imports
    this file, where the __main__ guard keeps it side-effect free."""
    cls_name, method = task
    buf = io.StringIO()
    try:
        case = globals()[cls_name]
        suite = unittest.TestLoader().loadTestsFromName(method, case)
        result = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
        ok = result.wasSuccessful()
    except Exception:
        ok = False
        buf.write(traceback.format_exc())
    return cls_name, method, ok, buf.getvalue()


if __name__ == "__main__":
    # The suite is spawn-bound — each sync run is hundreds of process
    # spawns — and every test owns a private repo+HOME temp pair, so the
    # cases are order-independent: fan them out one worker per case and
    # aggregate in loader order.
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    tasks = []
    for cls_suite in suite:
        for case in cls_suite:
            cls_name, method = case.id().split(".")[-2:]
            tasks.append((cls_name, method))

    started = time.monotonic()
    workers = min(len(tasks), os.cpu_count() or 1)
    results = None
    if workers > 1:
        try:
            ctx = multiprocessing.get_context("spawn")
            with ctx.Pool(processes=workers) as pool:
                results = pool.map(_run_one, tasks)
        except OSError:
            results = None  # fall through to the serial run
    if results is None:
        results = [_run_one(task) for task in tasks]

    failed = []
    for cls_name, method, ok, out in results:
        if ok:
            lines = out.splitlines()
            print(lines[0] if lines else f"{method} (no runner output)")
        else:
            failed.append(f"{cls_name}.{method}")
            print(out.rstrip())
    print("-" * 70)
    print(f"Ran {len(results)} tests in {time.monotonic() - started:.3f}s")
    if failed:
        print("FAILED (" + ", ".join(failed) + ")")
        raise SystemExit(1)
    print("OK")
