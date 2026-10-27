"""Tests for tools/sync.sh — the shared installer's safety behavior.

sync.sh installs into real dotfile roots, so these tests never run it
against the live HOME: each test builds a bounded repo fixture (the
files sync.sh actually consumes — SYNC_CORPUS below) in a temp dir and
points HOME at a fresh temp dir, then exercises the provenance
guarantees against the copy — fresh install, idempotence, foreign-file
refusal (skills trees and command roots), stale-own cleanup via the
ledger, absent-harness skips, version-drift detection, zero-write
on a late collision (the all-root preflight), the no-write
--dry-run/--check modes, and the retired-skills sweep:
a listed skill whose master is gone is removed from every install root
on ledger proof alone, foreign files in its paths refused.
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
# not bytes. Covers the invoked tools; the skills' consumable surfaces
# (tree files the tests reference, command routers and bare-name claims,
# one uniquely-named role brief per skill, since the def roots refuse a
# second claimant of a name); the kit-rules surfaces sync refreshes and
# drift-checks; the shared-core master whose closure parity refresh
# regenerates replica views from; and the committed root personas the
# verify pass byte-compares. Behavior fidelity is per-file; corpus size is
# not load-bearing. retired-skills.txt names a skill absent from this
# corpus, so every run also exercises the retired sweep as a no-op.
CMD_SKILL = "skills/spec-code-review"
INTENT_SKILL = "skills/spec-intent"
SHAPE_SKILL = "skills/spec-shape"
EXECUTE_SKILL = "skills/spec-execute"
# The exact flat-command set a fresh install must land in every command
# root: the skill routers plus the bare names redistributed across skills.
ROUTER_COMMANDS = (
    "spec-brainstorming", "spec-code-review", "spec-execute",
    "spec-intent",
)
BARE_COMMANDS = (
    "spec-idea", "spec-gen", "spec-build",
    "spec-test", "spec-review", "spec-ship",
)
ALL_COMMANDS = ROUTER_COMMANDS + BARE_COMMANDS
SYNC_CORPUS = (
    "tools/sync.sh",
    "tools/ownership.py",
    "tools/omp-defs.py",
    "tools/agent-defs.py",
    "tools/kit-rules.py",
    "tools/parity.py",
    "tools/retired-skills.txt",
    "rules/engineering-rules.md",
    "skills/spec-brainstorming/SKILL.md",
    "skills/spec-brainstorming/VERSION",
    "skills/spec-brainstorming/commands/spec-brainstorming.md",
    f"{CMD_SKILL}/SKILL.md",
    f"{CMD_SKILL}/VERSION",
    f"{CMD_SKILL}/commands/spec-code-review.md",
    f"{CMD_SKILL}/scripts/gate.sh",
    f"{CMD_SKILL}/scripts/review_orchestrator.py",
    "skills/spec-code-review/agents/code-review-fixer.md",
    f"{INTENT_SKILL}/SKILL.md",
    f"{INTENT_SKILL}/VERSION",
    f"{INTENT_SKILL}/commands/spec-intent.md",
    f"{INTENT_SKILL}/commands/spec-idea.md",
    f"{INTENT_SKILL}/commands/extra.txt",
    f"{INTENT_SKILL}/agents/_shared-protocol.md",
    f"{INTENT_SKILL}/agents/scout.md",
    f"{SHAPE_SKILL}/SKILL.md",
    f"{SHAPE_SKILL}/VERSION",
    f"{SHAPE_SKILL}/commands/spec-gen.md",
    f"{SHAPE_SKILL}/commands/extra.txt",
    f"{SHAPE_SKILL}/agents/_shared-protocol.md",
    f"{SHAPE_SKILL}/agents/designer.md",
    f"{SHAPE_SKILL}/agents/reviewer.md",
    f"{EXECUTE_SKILL}/SKILL.md",
    f"{EXECUTE_SKILL}/VERSION",
    f"{EXECUTE_SKILL}/commands/spec-execute.md",
    f"{EXECUTE_SKILL}/commands/spec-build.md",
    f"{EXECUTE_SKILL}/commands/spec-test.md",
    f"{EXECUTE_SKILL}/commands/spec-review.md",
    f"{EXECUTE_SKILL}/commands/spec-ship.md",
    f"{EXECUTE_SKILL}/commands/extra.txt",
    f"{EXECUTE_SKILL}/agents/_shared-protocol.md",
    f"{EXECUTE_SKILL}/agents/builder.md",
    f"{EXECUTE_SKILL}/agents/reviewer.md",
    "agents/builder.md",
    "agents/reviewer.md",
    "agents/qa.md",
    "agents/code-review-fixer.md",
    "skills/spec-shape/scripts/check.py",
    "skills/spec-shape/scripts/contract.py",
    "skills/spec-shape/scripts/freeze.py",
    "skills/spec-shape/scripts/graph.py",
    "skills/spec-shape/scripts/specstate.py",
    "skills/spec-shape/scripts/telemetry.py",
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
        return self.home.joinpath(
            ".claude", "skills", "spec-code-review", *parts)

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
        # a skill's own-name router landed in a command root
        self.assertTrue(
            (self.home / ".agents" / "commands"
             / "spec-code-review.md").is_file())
        # the skill trees and their redistributed bare names install
        # through the same loop
        self.assertTrue(
            (self.home / ".claude" / "skills" / "spec-intent"
             / "SKILL.md").is_file())
        self.assertTrue(
            (self.home / ".claude" / "skills" / "spec-shape"
             / "SKILL.md").is_file())
        self.assertTrue(
            (self.home / ".claude" / "skills" / "spec-execute"
             / "SKILL.md").is_file())
        self.assertTrue(
            (self.home / ".agents" / "commands" / "spec-idea.md").is_file())
        # skills-tree provenance ledger exists and is excluded from verify
        self.assertTrue(self.skill_root(LEDGER).is_file())
        # atomic replacement preserves the shipped executable bits
        self.assertTrue(
            os.access(self.skill_root("scripts", "gate.sh"), os.X_OK))
        r2 = self.run_sync()
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        # no installer scratch survives a completed apply
        self.assertEqual(list(self.home.rglob(f"{LEDGER}.tmp*")), [])

    def test_bare_name_redistribution_installs_the_same_total_set(self):
        # bare names map to their owning skills: ten commands, nothing
        # more, nothing less.
        self.assertEqual(self.run_sync().returncode, 0)
        for root in (".agents", ".claude", ".zcode"):
            installed = {p.name for p in
                         (self.home / root / "commands").glob("*.md")}
            self.assertEqual(
                installed, {f"{base}.md" for base in ALL_COMMANDS},
                f"~/{root}/commands vs the redistributed total set")

    def test_installer_scratch_leftover_is_not_a_foreign_file(self):
        # Atomic replacement stages through LEDGER_NAME-prefixed
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
        dest = root / "spec-code-review.md"
        master = (self.repo / CMD_SKILL
                  / "commands" / "spec-code-review.md")
        master.write_text(
            master.read_text() + "\n<!-- touched by master -->\n")
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("touched by master", dest.read_text())
        entries = [line for line in (root / LEDGER).read_text().splitlines()
                   if line.endswith(" spec-code-review")]
        self.assertEqual(
            entries,
            [f"{hashlib.sha256(dest.read_bytes()).hexdigest()}"
             " spec-code-review"])

    def test_foreign_file_in_skills_tree_is_refused_and_kept(self):
        self.assertEqual(self.run_sync().returncode, 0)
        foreign = self.skill_root("scripts", "zzz-foreign.py")
        foreign.write_text("# not ours\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertTrue(foreign.is_file())  # never clobbered

    def test_same_path_owned_update_is_applied(self):
        self.assertEqual(self.run_sync().returncode, 0)
        master = (self.repo / CMD_SKILL
                  / "scripts" / "gate.sh")
        master.write_text(master.read_text() + "# touched by master\n")
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dest = (self.home / ".agents" / "skills" / "spec-code-review"
                / "scripts" / "gate.sh")
        self.assertIn("# touched by master", dest.read_text())

    def test_foreign_file_blocks_stale_removal_in_same_tree(self):
        # a foreign file anywhere in the tree defers every removal too
        self.assertEqual(self.run_sync().returncode, 0)
        (self.repo / CMD_SKILL / "scripts" / "gate.sh").unlink()
        skill_tree = (self.home / ".agents" / "skills" / "spec-code-review")
        foreign = skill_tree / "scripts" / "review_orchestrator.py"
        foreign.write_text(foreign.read_text() + "# hand-edited\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        # stale-own gate.sh survives: nothing is removed from a tree
        # that holds a foreign file
        self.assertTrue((skill_tree / "scripts" / "gate.sh").is_file())
        self.assertIn("hand-edited", foreign.read_text())

    def test_stale_own_file_is_cleaned_via_ledger(self):
        self.assertEqual(self.run_sync().returncode, 0)
        dest = (self.home / ".agents" / "skills" / "spec-code-review"
                / "scripts" / "gate.sh")
        self.assertTrue(dest.is_file())
        # master (the repo copy) drops the file: ledger proves we shipped
        # it, so the next sync removes it instead of refusing
        (self.repo / CMD_SKILL / "scripts" / "gate.sh").unlink()
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("clean", r.stdout)
        self.assertFalse(dest.exists())

    def test_foreign_def_in_claude_agents_root_is_refused(self):
        self.assertEqual(self.run_sync().returncode, 0)
        dest = self.home / ".claude" / "agents" / "code-review-fixer.md"
        dest.write_text("---\nname: code-review-fixer\n---\nhand-edited\n")
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
        (self.repo / CMD_SKILL / "VERSION").write_text("9.9.9\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DRIFT", r.stdout)

    def test_oversized_description_fails_the_sync(self):
        # zcode/claude loaders reject descriptions over 1024 chars — the
        # skill silently fails to register; sync must catch it first
        sk = self.repo / CMD_SKILL / "SKILL.md"
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
        master = (self.repo / CMD_SKILL / "scripts" / "gate.sh")
        master.write_text(master.read_text() + "# touched by master\n")
        late = (self.home / ".omp" / "agent" / "skills" / "spec-code-review"
                / "scripts" / "gate.sh")
        late.write_text(late.read_text() + "# hand-edited\n")
        before = self.home_snapshot()
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("PREFLIGHT FAILED", r.stdout)
        self.assertIn("hand-edited", late.read_text())
        first = (self.home / ".agents" / "skills" / "spec-code-review"
                 / "scripts" / "gate.sh")
        self.assertNotIn("touched by master", first.read_text())
        self.assertEqual(self.home_snapshot(), before)

    def test_late_omp_def_collision_writes_nothing_anywhere(self):
        # Same zero-write contract through the omp defs root, whose
        # per-skill manifest is that plan's ledger: a hand-edited def
        # there refuses before any other destination is touched.
        self.assertEqual(self.run_sync().returncode, 0)
        master = (self.repo / CMD_SKILL / "scripts" / "gate.sh")
        master.write_text(master.read_text() + "# touched by master\n")
        late = (self.home / ".omp" / "agent" / "agents"
                / "code-review-fixer.md")
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
        foreign = (self.home / ".factory" / "commands"
                   / "spec-code-review.md")
        foreign.write_text("# a hand-written note, not the wrapper\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("PREFLIGHT FAILED", r.stdout)
        self.assertIn("hand-written note", foreign.read_text())
        for root in (".agents", ".claude", ".zcode", ".omp"):
            self.assertFalse((self.home / root).exists(), root)

    def test_foreign_optional_agent_defs_write_nothing_anywhere(self):
        # The optional agent-def roots (droid, opencode) are planned like
        # every other destination: a foreign file there must fail the
        # preflight before the first write — not mid-apply with the
        # skill roots already updated.
        for foreign_rel in (
                ".factory/droids/code-review-fixer.md",
                ".config/opencode/agents/code-review-fixer.md"):
            foreign = self.home / foreign_rel
            foreign.parent.mkdir(parents=True, exist_ok=True)
            foreign.write_text(
                "---\nname: code-review-fixer\nstale: old deploy\n")
            before = self.home_snapshot()
            r = self.run_sync()
            self.assertNotEqual(r.returncode, 0, foreign_rel)
            self.assertIn("REFUSE", r.stdout, foreign_rel)
            self.assertIn("PREFLIGHT FAILED", r.stdout, foreign_rel)
            self.assertIn("stale: old deploy", foreign.read_text())
            self.assertEqual(self.home_snapshot(), before, foreign_rel)
            foreign.unlink()

    def test_dry_run_reports_the_plan_and_writes_nothing(self):
        # --dry-run prints the planner's create/update/unchanged/
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
        master = (self.repo / CMD_SKILL / "scripts" / "gate.sh")
        master.write_text(master.read_text() + "# touched by master\n")
        (self.repo / CMD_SKILL / "scripts"
         / "review_orchestrator.py").unlink()
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
                         self.skill_root("scripts", "gate.sh").read_text())
        self.assertTrue(
            self.skill_root("scripts", "review_orchestrator.py").is_file())
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
        master = (self.repo / CMD_SKILL / "scripts" / "gate.sh")
        master.write_text(master.read_text() + "# touched by master\n")
        r2 = self.run_sync("--check")
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn("DRIFT", r2.stdout)
        self.assertNotIn("touched by master",
                         self.skill_root("scripts", "gate.sh").read_text())
        self.assertEqual(self.home_snapshot(), before)
        # a hand-edited owned file is refused by the preflight and kept
        dest = self.skill_root("scripts", "gate.sh")
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
    block."""

    def test_commands_install_when_factory_home_exists(self):
        (self.home / ".factory").mkdir()
        r1 = self.run_sync()
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        for base in ALL_COMMANDS:
            self.assertTrue(
                (self.home / ".factory" / "commands" / f"{base}.md").is_file(),
                base)
        self.assertTrue(
            (self.home / ".factory" / "commands" / LEDGER).is_file())
        r2 = self.run_sync()
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

class KiloCommandsTests(SyncShBase):
    """Kilo CLI's command + agent roots (~/.config/kilo/command,
    ~/.config/kilo/agent) — gated on the harness's global config dir
    existing (never fabricated), same provenance-ledger discipline as
    every other root."""

    def test_absent_kilo_home_skips_loudly(self):
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("skip  kilo commands", r.stdout)
        self.assertIn("skip  kilo defs", r.stdout)
        self.assertIn("skip  kilo skills", r.stdout)
        self.assertFalse((self.home / ".config" / "kilo").exists())

    def test_commands_defs_and_skills_install_when_kilo_home_exists(self):
        (self.home / ".config" / "kilo").mkdir(parents=True)
        r1 = self.run_sync()
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        # the full redistributed command set lands in Kilo's command root
        for base in ALL_COMMANDS:
            self.assertTrue(
                (self.home / ".config" / "kilo" / "command"
                 / f"{base}.md").is_file(), base)
        self.assertTrue(
            (self.home / ".config" / "kilo" / "command" / LEDGER).is_file())
        # and the skill trees land in Kilo's native skills root
        for skill in ("spec-brainstorming", "spec-code-review",
                      "spec-intent", "spec-shape", "spec-execute"):
            self.assertTrue(
                (self.home / ".config" / "kilo" / "skills" / skill
                 / "SKILL.md").is_file(), skill)
        # agent dialect: subagent mode + derived permission map
        surveyor = (self.home / ".config" / "kilo" / "agent"
                    / "code-review-fixer.md").read_text()
        self.assertIn("mode: subagent", surveyor)
        self.assertIn("  task: deny", surveyor)
        self.assertIn("  edit: allow", surveyor)
        r2 = self.run_sync()
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

class StaleCommandPruneTests(SyncShBase):
    """A name that leaves extra.txt must not linger in flat command
    roots; a foreign file at an unclaimed name is shared turf and stays
    untouched."""

    def test_renamed_extra_name_is_pruned_and_foreign_survives(self):
        commands = self.repo / CMD_SKILL / "commands"
        (commands / "legacy.md").write_text("# legacy wrapper\n",
                                            encoding="utf-8")
        extra = commands / "extra.txt"
        extra.write_text("legacy\n", encoding="utf-8")
        r1 = self.run_sync()
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        legacy = self.home / ".claude" / "commands" / "legacy.md"
        self.assertTrue(legacy.is_file())

        extra.unlink()
        (commands / "legacy.md").unlink()
        foreign = self.home / ".claude" / "commands" / "plan.md"
        foreign.write_text("# someone else's plan\n", encoding="utf-8")
        r2 = self.run_sync()
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertFalse(legacy.exists())
        self.assertTrue(foreign.is_file())


class KitRulesSyncTests(SyncShBase):
    """tools/kit-rules.py wiring: sync refreshes the four
    § Engineering rules carrier sections from the canonical
    rules/engineering-rules.md before installing, and --check reports a
    hand-edited carrier as DRIFT without writing anything."""

    @staticmethod
    def hand_edit(carrier):
        heading = "## Engineering rules (kit-wide)\n"
        carrier.write_text(carrier.read_text().replace(
            heading, heading + "stale hand-edit\n", 1))

    def test_sync_refreshes_a_stale_carrier_and_installs_fresh(self):
        self.assertEqual(self.run_sync().returncode, 0)
        carrier = (self.repo / "skills" / "spec-code-review" / "agents"
                   / "code-review-fixer.md")
        self.hand_edit(carrier)
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # the committed carrier was regenerated back to the source
        self.assertNotIn("stale hand-edit", carrier.read_text())
        # and the installed copies carry the fresh section too
        installed = (self.home / ".agents" / "skills" / "spec-code-review"
                     / "agents" / "code-review-fixer.md").read_text()
        self.assertNotIn("stale hand-edit", installed)

    def test_check_reports_stale_carrier_as_drift_and_writes_nothing(self):
        self.assertEqual(self.run_sync().returncode, 0)
        carrier = (self.repo / "skills" / "spec-code-review" / "agents"
                   / "code-review-fixer.md")
        self.hand_edit(carrier)
        before = self.home_snapshot()
        r = self.run_sync("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DRIFT", r.stdout)
        self.assertIn("stale hand-edit", carrier.read_text())
        self.assertEqual(self.home_snapshot(), before)



class RetiredSkillSweepTests(SyncShBase):
    """tools/retired-skills.txt + sync's retired sweep:
    a listed skill whose master is gone is swept from the install roots,
    deletion authority being the provenance ledgers alone — a foreign
    file in the retired tree is refused, never deleted; while the master
    still ships the sweep is a guarded no-op."""

    def test_master_still_shipping_is_a_guarded_no_op(self):
        # the committed list names spec-to-prod, which the repo no longer
        # ships, so the guarded no-op is staged by planting a minimal
        # master in the fixture repo — the sweep must skip the name and
        # leave a staged installed tree completely untouched
        monolith = self.repo / "skills" / "spec-to-prod"
        monolith.mkdir(parents=True)
        (monolith / "SKILL.md").write_text("# monolith deploy\n")
        tree = self.home / ".claude" / "skills" / "spec-to-prod"
        tree.mkdir(parents=True)
        (tree / "SKILL.md").write_text("# monolith deploy\n")
        (tree / LEDGER).write_text(
            f"{hashlib.sha256(b'# monolith deploy\n').hexdigest()}"
            " SKILL.md\n")
        r = self.run_sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(
            "skip retired sweep for spec-to-prod — master still ships;"
            " activate at its retirement", r.stdout)
        self.assertEqual((tree / "SKILL.md").read_text(), "# monolith deploy\n")

    def test_sweep_removes_proven_files_and_refuses_foreign(self):
        # skills/retired-skill is absent from the fixture repo; its
        # installed tree at a root holds two ledger-proven deploys plus
        # one planted foreign file
        (self.repo / "tools" / "retired-skills.txt").write_text(
            "retired-skill\n", encoding="utf-8")
        tree = self.home / ".claude" / "skills" / "retired-skill"
        deploy = {
            "SKILL.md": "# old deploy\n",
            "scripts/engine.py": "print('old')\n",
        }
        lines = []
        for rel, text in deploy.items():
            p = tree / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
            lines.append(f"{hashlib.sha256(text.encode()).hexdigest()} {rel}")
        (tree / LEDGER).write_text("\n".join(lines) + "\n")
        foreign = tree / "notes.md"
        foreign.write_text("# someone else's file\n")
        r = self.run_sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        # exactly the provenance-backed files went, nothing else
        for rel in deploy:
            self.assertFalse((tree / rel).exists(), rel)
        self.assertEqual(foreign.read_text(), "# someone else's file\n")
        self.assertTrue(
            (self.home / ".claude" / "skills" / "spec-code-review"
             / "SKILL.md").is_file())


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
