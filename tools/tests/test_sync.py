"""Tests for tools/sync.sh — the shared installer's safety behavior.

sync.sh installs into real dotfile roots, so these tests never run it
against the live HOME: each test copies the whole repo to a temp dir
and points HOME at a fresh temp dir, then exercises the provenance
guarantees against the copy — fresh install, idempotence, foreign-file
refusal (skills trees and command roots), stale-own cleanup via the
ledger, absent-harness skips, and version-drift detection.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER = ".spec-dev-kit-deployed"


class SyncShTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="syncsh-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        shutil.copytree(
            REPO_ROOT, self.repo,
            ignore=shutil.ignore_patterns(".git", ".DS_Store", "__pycache__"))
        self.home = self.tmp / "home"
        self.home.mkdir()

    def run_sync(self):
        return subprocess.run(
            ["bash", str(self.repo / "tools" / "sync.sh")],
            env=dict(os.environ, HOME=str(self.home)),
            capture_output=True, text=True, timeout=300)

    def skill_root(self, *parts):
        return self.home.joinpath(".claude", "skills", "spec-to-prod", *parts)

    def test_fresh_install_is_clean_and_idempotent(self):
        r1 = self.run_sync()
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        self.assertTrue((self.skill_root("SKILL.md")).is_file())
        # extra.txt bare name landed in a command root
        self.assertTrue(
            (self.home / ".agents" / "commands" / "build.md").is_file())
        # skills-tree provenance ledger exists and is excluded from verify
        self.assertTrue(self.skill_root(LEDGER).is_file())
        r2 = self.run_sync()
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

    def test_foreign_file_in_skills_tree_is_refused_and_kept(self):
        self.assertEqual(self.run_sync().returncode, 0)
        foreign = self.skill_root("scripts", "zzz-foreign.py")
        foreign.write_text("# not ours\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertTrue(foreign.is_file())  # never clobbered

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
