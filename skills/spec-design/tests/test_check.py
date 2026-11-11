"""Tests for scripts/check.py — run via tests/run.sh (needs Python >= 3.10).

The green fixture in examples/mini-spec/ is the contract: any check.py
change that turns it red is a behavior change, and belongs in the
changelog. The broken-fixture tests mutate a temp copy, never the example.
"""

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = SKILL / "examples" / "mini-spec"
FIXTURE = EXAMPLE_ROOT / "specs" / "mini-spec"

_spec = importlib.util.spec_from_file_location("check", SKILL / "scripts" / "check.py")
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def run_check(*argv):
    """Run check.main() with argv/out captured; return (exit_code, output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         unittest.mock.patch.object(sys, "argv", ["check.py", *argv]):
        code = check.main()
    return code, buf.getvalue()


def fixture_copy():
    """Full example tree in a temp dir; returns the copied spec dir path."""
    tmp = Path(tempfile.mkdtemp(prefix="s2c-test-"))
    shutil.copytree(EXAMPLE_ROOT, tmp / "mini-spec")
    return tmp / "mini-spec" / "specs" / "mini-spec"


class BurndownLabelTests(unittest.TestCase):
    def test_sum_labels(self):
        for lab in ("Σ", "**Σ**", "Total", "total:", "ALL"):
            self.assertEqual(check.bd_label(lab)[0], "sum", lab)

    def test_data_labels_attribute_to_phase(self):
        self.assertEqual(check.bd_label("1"), ("data", 1))
        self.assertEqual(check.bd_label("Phase 2"), ("data", 2))
        self.assertEqual(check.bd_label("**Σ**-lookalike P3")[0], "data")

    def test_skip_and_unattributable(self):
        self.assertEqual(check.bd_label("")[0], "skip")
        self.assertEqual(check.bd_label("---")[0], "skip")
        kind, phase = check.bd_label("Setup")
        self.assertEqual(kind, "data")   # counted in arithmetic...
        self.assertIsNone(phase)         # ...but not fix_burndown-rewritable


class ParseArgsTests(unittest.TestCase):
    def test_positional_and_flags(self):
        self.assertEqual(
            check.parse_args(["specs/x", "--fix-burndown", "--repo", "r", "--next-ids"]),
            ("specs/x", "r", True, True, False, False, False, False),
        )
        self.assertEqual(check.parse_args(["specs/x", "--survey-only"]),
                         ("specs/x", None, False, False, True, False, False, False))
        self.assertEqual(check.parse_args(["specs/x", "--intent-only"]),
                         ("specs/x", None, False, False, False, True, False, False))
        self.assertEqual(check.parse_args(["specs/x", "--constitution"]),
                         ("specs/x", None, False, False, False, False, True, False))
        self.assertEqual(check.parse_args(["specs/x", "--checklist"]),
                         ("specs/x", None, False, False, False, False, False, True))

    def test_bad_args_return_none(self):
        self.assertIsNone(check.parse_args([]))
        self.assertIsNone(check.parse_args(["a", "b"]))
        self.assertIsNone(check.parse_args(["--repo"]))  # missing value


class HelperTests(unittest.TestCase):
    def test_pytest_target_exists(self):
        root = EXAMPLE_ROOT
        self.assertTrue(check._pytest_target_exists(root, "test_calc.py"))
        self.assertTrue(check._pytest_target_exists(root, "repo/test_calc.py"))
        self.assertFalse(check._pytest_target_exists(root, "test_missing.py"))

    def test_symbol_def_lines(self):
        text = "x = 1\n\ndef add(a, b):\n    return a\n\nclass Bag:\n    pass\n"
        self.assertEqual(check._symbol_def_lines(text, "add"), [3])
        self.assertEqual(check._symbol_def_lines(text, "Bag"), [6])
        self.assertEqual(check._symbol_def_lines(text, "missing"), [])


class EvidenceIntegrityTests(unittest.TestCase):
    def test_fabricated_lifecycle_sha_fails(self):
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        task = spec / "task.md"
        task.write_text(
            "**Delivered**: commit @ deadbeef\n" + task.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        code, out = run_check(str(spec), "--repo", str(Path.cwd()))
        self.assertEqual(code, 1)
        self.assertIn("delivered: commit 'deadbeef' not found", out)
        # rewritten history is the usual cause: the fix is named
        self.assertIn("tick.py <spec-dir> --redeliver <new-sha>", out)

    def test_non_git_dash_inside_a_git_repo_fails(self):
        # the Delivered record's `-` skip form is the explicit non-git
        # escape hatch — recording it while --repo names a working git
        # repository is a lie the integrity check must catch
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        task = spec / "task.md"
        task.write_text(
            "**Delivered**: commit @ -\n" + task.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        code, out = run_check(str(spec), "--repo", str(Path.cwd()))
        self.assertEqual(code, 1)
        self.assertIn("delivered: explicit non-git dash recorded inside a git repo", out)

    def approved_copy(self):
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        set_text = spec.joinpath("spec.md")
        set_text.write_text(
            set_text.read_text(encoding="utf-8").replace(
                "**Status**: draft", "**Status**: approved"
            ), encoding="utf-8")
        return spec

    def record_review(self, spec):
        (spec / "approvals").mkdir(exist_ok=True)
        (spec / "approvals" / "review.md").write_text(
            "# Contract review\n\nDocset fingerprint: "
            f"{check.freeze.docset_fingerprint(spec)}\n\n"
            "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none\n",
            encoding="utf-8")

    def record_freeze(self, spec):
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            code = check.freeze.record(spec, Path.cwd())
        return code, err.getvalue()

    def test_approved_status_without_a_freeze_fails(self):
        # a hand-flipped Status is not an approval, whatever task.md's
        # header lines say
        spec = self.approved_copy()
        code, out = run_check(str(spec), "--repo", str(Path.cwd()))
        self.assertEqual(code, 1, out)
        self.assertIn("Status approved but no approvals/approval.md", out)

    def test_freeze_refuses_without_the_current_contract_review(self):
        spec = self.approved_copy()
        code, err = self.record_freeze(spec)
        self.assertEqual(code, 1)
        self.assertIn("contract review not recorded", err)
        self.assertFalse((spec / "approvals" / "approval.md").exists())

        # a review of the docset as it stood before a repair backs nothing
        self.record_review(spec)
        plan = spec / "plan.md"
        plan.write_text(plan.read_text(encoding="utf-8") + "\nrepaired\n",
                        encoding="utf-8")
        code, err = self.record_freeze(spec)
        self.assertEqual(code, 1)
        self.assertIn("reviews a different docset", err)

        self.record_review(spec)
        self.assertEqual(self.record_freeze(spec)[0], 0)

    def test_freeze_refuses_a_review_record_without_digest_or_rulings(self):
        spec = self.approved_copy()
        review = spec / "approvals" / "review.md"
        review.parent.mkdir()
        fingerprint = check.freeze.docset_fingerprint(spec)
        blocked = (
            f"Docset fingerprint: {fingerprint}\n\ndigest: BLOCK 1 · WARN 0 "
            "· NIT 0 · worst untestable FR\n"
            '1. BLOCK · spec.md · "shall be fast" · name a bound\n')
        refused = (
            # the fingerprint alone proves no auditor ever ran
            (f"{fingerprint}\n", "no auditor digest"),
            (blocked, "BLOCK 1 but 0 ruling line(s)"),
        )
        for text, why in refused:
            with self.subTest(why):
                review.write_text(text, encoding="utf-8")
                code, err = self.record_freeze(spec)
                self.assertEqual(code, 1)
                self.assertIn(why, err)
                self.assertFalse((spec / "approvals" / "approval.md").exists())
        review.write_text(
            blocked + 'ruling: 1 — user: "ship it, the bound comes later"\n',
            encoding="utf-8")
        self.assertEqual(self.record_freeze(spec)[0], 0)

    def test_a_delivered_docset_survives_a_rewritten_approval_anchor(self):
        # a squash-merge or rebase replaces the Approved-at commit; once
        # delivery is recorded the anchor is history
        spec = self.approved_copy()
        root = spec.parents[1]

        def git(*args):
            return subprocess.run(
                ["git", "-C", str(root), "-c", "user.name=kit",
                 "-c", "user.email=kit@example.com", *args],
                check=True, capture_output=True, text=True).stdout.strip()

        git("init", "-q")
        git("add", "-A")
        git("commit", "-qm", "base")
        head = git("rev-parse", "--short", "HEAD")
        self.record_review(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check.freeze.record(spec, root), 0)
        approval = spec / "approvals" / "approval.md"
        approval.write_text(
            approval.read_text(encoding="utf-8").replace(head, "0123abc"),
            encoding="utf-8")
        lost = "Approved-at commit '0123abc' not found"
        self.assertIn(lost, run_check(str(spec), "--repo", str(root))[1])
        task = spec / "task.md"
        task.write_text(
            f"**Delivered**: commit @ {head}\n"
            + task.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertNotIn(lost, run_check(str(spec), "--repo", str(root))[1])

    def test_coverage_gaps_only_warn_once_the_contract_is_frozen(self):
        # a docset approved before a coverage rule existed must not go
        # red mid-execution: repairing it would break its freeze
        spec = self.approved_copy()
        plan = spec / "plan.md"
        plan.write_text(plan.read_text(encoding="utf-8").split(
            "### Rollout")[0], encoding="utf-8")
        self.record_review(spec)
        self.assertEqual(self.record_freeze(spec)[0], 0)
        code, out = run_check(str(spec), "--repo", str(Path.cwd()))
        self.assertEqual(code, 0, out)
        self.assertIn("WARN  structure: plan.md has no `### Rollout`", out)

    def test_record_by_names_each_approver(self):
        spec = self.approved_copy()
        self.record_review(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            code = check.freeze.main([
                str(spec), "--record", "--by", "Ana Lim", "--by", "Raj P",
                "--repo", str(Path.cwd())])
        self.assertEqual(code, 0)
        record = (spec / "approvals" / "approval.md").read_text(
            encoding="utf-8")
        self.assertIn("**Approved-by**: Ana Lim\n**Approved-by**: Raj P\n",
                      record)
        self.assertEqual(check.freeze.verify(spec, Path.cwd()), [])
        # --by signs an approval; it is not a verify option
        self.assertIsNone(check.freeze.parse_args(
            [str(spec), "--verify", "--by", "Ana Lim"]))

    def test_approved_freeze_detects_contract_mutation(self):
        spec = self.approved_copy()
        self.record_review(spec)
        self.assertEqual(self.record_freeze(spec)[0], 0)
        self.assertEqual(self.record_freeze(spec)[0], 1)
        code, out = run_check(str(spec), "--repo", str(Path.cwd()))
        self.assertEqual(code, 0, out)

        test = spec / "test.md"
        test.write_text(test.read_text(encoding="utf-8") + "\nmutated\n",
                       encoding="utf-8")
        code, out = run_check(str(spec), "--repo", str(Path.cwd()))
        self.assertEqual(code, 1)
        self.assertIn("test.md changed after approval", out)


class QualityRequirementTests(unittest.TestCase):
    def test_applicable_nfr_requires_task_and_test(self):
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        path = spec / "spec.md"
        path.write_text(path.read_text(encoding="utf-8") + (
            "\n- **NFR-002**: Security — applicable: The system shall reject "
            "forged requests.\n"
        ), encoding="utf-8")
        code, out = run_check(str(spec), "--repo", str(spec.parents[1]))
        self.assertEqual(code, 1)
        self.assertIn("NFR-002 has no task", out)
        self.assertIn("NFR-002 has no test case", out)

    def test_inapplicable_nfr_needs_reason_but_not_coverage(self):
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        path = spec / "spec.md"
        path.write_text(path.read_text(encoding="utf-8") + (
            "\n- **NFR-002**: Accessibility — not applicable: no user-facing "
            "surface changes.\n"
        ), encoding="utf-8")
        _, out = run_check(str(spec), "--repo", str(spec.parents[1]))
        self.assertNotIn("NFR-002 has no task", out)
        self.assertNotIn("NFR-002 has no test case", out)


def rewrite(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new), encoding="utf-8")


TINY_REFACTOR = """# Spec: tidy

**Status**: draft
**Tier**: tiny
**Type**: refactor

## What
Fold the two arithmetic helpers into one table without changing results.

## Requirements
- **FR-001**: The system shall return the same sums and differences as
  before the restructure.

## Tasks

- [ ] T001 fold add and sub into a dispatch table (FR-001) [P]
  - Touches: `repo/calc.py`
"""


class SdlcCoverageTests(unittest.TestCase):
    """Each full-tier coverage rule fails a draft that lacks the thing."""

    def copy(self):
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        return spec

    def test_a_draft_lacking_each_coverage_item_fails(self):
        cases = (
            ("spec.md", "Observability,\n  Accessibility", "Observability",
             "quality: Accessibility is not triaged"),
            ("tech-spec.md", "## Interfaces & data", "## Interfaces",
             "tech-spec.md has no `## Interfaces & data` section"),
            ("plan.md", "### Rollout", "### Rollout plan",
             "plan.md has no `### Rollout` section"),
            ("spec.md", "**Type**: feature", "**Type**: refactor",
             "a refactor spec needs a behavior-preservation test case"),
            ("spec.md", "**Type**: feature", "**Type**: chore",
             "`**Type**: chore` — the work types are feature | bugfix"),
            ("spec.md", "**Type**: feature",
             "**Type**: feature\n**Depends on**: ghost-spec",
             "depends: `ghost-spec`"),
        )
        for doc, old, new, message in cases:
            with self.subTest(message):
                spec = self.copy()
                rewrite(spec / doc, old, new)
                code, out = run_check(str(spec))
                self.assertEqual(code, 1, out)
                self.assertIn(message, out)

    def test_a_preserves_case_satisfies_a_refactor(self):
        spec = self.copy()
        rewrite(spec / "spec.md", "**Type**: feature", "**Type**: refactor")
        rewrite(spec / "test.md", "- **Given** the calculator module loaded\n"
                "- **When** the multiply operation is called with 6",
                "- **Preserves**: sums and differences are unchanged\n"
                "- **Given** the calculator module loaded\n"
                "- **When** the multiply operation is called with 6")
        rewrite(spec.parent / "INDEX.md", "feature", "refactor")
        code, out = run_check(str(spec))
        self.assertEqual(code, 0, out)
        self.assertIn("PASS (0 fail, 0 warn)", out)

    def test_tiny_refactor_needs_an_accept_command(self):
        spec = self.copy()
        for name in ("plan.md", "tech-spec.md", "task.md", "test.md",
                     "survey.md", "research.md"):
            (spec / name).unlink()
        (spec / "spec.md").write_text(TINY_REFACTOR, encoding="utf-8")
        code, out = run_check(str(spec))
        self.assertEqual(code, 1, out)
        self.assertIn("a refactor spec needs a task with an `Accept:`", out)
        with (spec / "spec.md").open("a", encoding="utf-8") as fh:
            fh.write("  - Accept: `python3 -m pytest test_calc.py`\n")
        code, out = run_check(str(spec))
        self.assertEqual(code, 0, out)

    def test_intent_type_is_held_to_the_same_vocabulary(self):
        fails, _ = check.intent_failures(
            "**Type**: chore\n" + IntentOnlyTests.GOOD, Path.cwd())
        self.assertTrue(any("the work types are" in f for f in fails), fails)


class CrossSpecTests(unittest.TestCase):
    def setUp(self):
        self.spec = fixture_copy()
        self.addCleanup(shutil.rmtree, self.spec.parents[1],
                        ignore_errors=True)

    def sibling(self, status):
        other = self.spec.parent / "other"
        other.mkdir(exist_ok=True)
        (other / "spec.md").write_text(
            f"# Spec: other\n\n**Status**: {status}\n**Tier**: tiny\n\n"
            "## Tasks\n\n- [ ] T001 rework the module (FR-001) [P]\n"
            "  - Touches: `repo/`\n", encoding="utf-8")

    def depend_on_other(self):
        rewrite(self.spec / "spec.md", "**Type**: feature",
                "**Type**: feature\n**Depends on**: other")
        with contextlib.redirect_stdout(io.StringIO()):
            check.index.main([str(self.spec)])

    def test_in_flight_overlap_warns_until_the_specs_are_ordered(self):
        self.sibling("approved")
        code, out = run_check(str(self.spec))
        self.assertEqual(code, 0, out)
        self.assertIn("overlap: in-flight spec other (approved) also "
                      "touches `repo/calc.py`", out)
        self.depend_on_other()
        code, out = run_check(str(self.spec))
        self.assertIn("PASS (0 fail, 0 warn)", out)

    def test_a_draft_spec_neither_overlaps_nor_backs_a_dependency(self):
        self.sibling("draft")
        _, out = run_check(str(self.spec))
        self.assertNotIn("overlap:", out)
        self.depend_on_other()
        code, out = run_check(str(self.spec))
        self.assertEqual(code, 0, out)
        self.assertIn("depends: other is still draft", out)


class IndexTests(unittest.TestCase):
    def test_the_index_line_is_rendered_and_a_stale_one_warns(self):
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        index_md = spec.parent / "INDEX.md"
        rewrite(spec / "spec.md", "**Type**: feature", "**Type**: bugfix")
        _, out = run_check(str(spec))
        self.assertIn("index: INDEX.md line for mini-spec is stale", out)

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check.index.main([str(spec)]), 0)
        self.assertEqual(
            index_md.read_text(encoding="utf-8"),
            "# Specs index\n"
            "- [mini-spec](mini-spec/spec.md) — draft · bugfix · full\n")
        _, out = run_check(str(spec))
        self.assertNotIn("index:", out)

        # an archived spec keeps its one line, repointed
        archived = spec.parent / "archive" / "2026-01-02-mini-spec"
        archived.parent.mkdir()
        spec.rename(archived)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                check.index.main(["--all", str(archived.parents[1])]), 0)
        self.assertEqual(
            index_md.read_text(encoding="utf-8"),
            "# Specs index\n- [mini-spec](archive/2026-01-02-mini-spec/"
            "spec.md) — draft · bugfix · full\n")


class FixBurndownTests(unittest.TestCase):
    def test_rewrites_numbers_keeps_labels(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "task.md"
            path.write_text(
                "| Phase | Total | Done |\n"
                "|-------|-------|------|\n"
                "| 1     | 9     | 9    |\n"
                "| **Σ** | 9     | 9    |\n",
                encoding="utf-8",
            )
            out = check.fix_burndown(path.read_text(encoding="utf-8"), path, {1: 2}, {1: 0})
            self.assertIn("| 1 | 2 | 0 |", out)
            self.assertIn("| **Σ** | 2 | 0 |", out)  # label cell kept verbatim
            self.assertIn("| Phase | Total | Done |", out)  # header untouched


class GreenFixtureTests(unittest.TestCase):
    def test_full_check_passes_clean(self):
        code, out = run_check(str(FIXTURE))
        self.assertEqual(code, 0, out)
        self.assertIn("PASS (0 fail, 0 warn)", out)

    def test_unreadable_sibling_is_skipped_not_fatal(self):
        # CI's shared /tmp holds root-owned mode-700 dirs (systemd
        # private mounts) beside the runner's temp trees; repo_root
        # defaults to an ancestor that enumerates them. A probe into an
        # unreadable sibling must skip it, never crash the checker.
        spec = fixture_copy()
        hostile = spec.parent.parent / "systemd-private-hostile"
        hostile.mkdir()
        (hostile / "keep").write_text("x")
        os.chmod(hostile, 0o000)
        try:
            if os.access(hostile, os.R_OK):
                self.skipTest("running as root — chmod 000 does not bite")
            code, out = run_check(str(spec))
            self.assertEqual(code, 0, out)
            self.assertIn("PASS (0 fail, 0 warn)", out)
        finally:
            os.chmod(hostile, 0o700)
            shutil.rmtree(hostile, ignore_errors=True)

    def test_survey_only_passes(self):
        code, out = run_check(str(FIXTURE), "--survey-only")
        self.assertEqual(code, 0, out)

    def test_next_ids(self):
        code, out = run_check(str(FIXTURE), "--next-ids")
        self.assertEqual(code, 0, out)
        self.assertIn("FR-003", out)
        self.assertIn("T003", out)


class ConstitutionTests(unittest.TestCase):
    def test_filled_constitution_passes_standalone(self):
        code, out = run_check(str(FIXTURE), "--constitution")
        self.assertEqual(code, 0, out)
        self.assertIn("PASS", out)

    def test_missing_constitution_fails_standalone(self):
        spec_dir = fixture_copy()
        try:
            (spec_dir.parent / "CONSTITUTION.md").unlink()
            code, out = run_check(str(spec_dir), "--constitution")
            self.assertEqual(code, 1, out)
        finally:
            shutil.rmtree(spec_dir.parent.parent)

    def test_missing_constitution_warns_when_only_spec(self):
        spec_dir = fixture_copy()
        try:
            (spec_dir.parent / "CONSTITUTION.md").unlink()
            code, out = run_check(str(spec_dir))
            self.assertEqual(code, 0, out)
            self.assertIn("WARN  constitution:", out)
        finally:
            shutil.rmtree(spec_dir.parent.parent)

    def test_missing_constitution_fails_when_another_spec_exists(self):
        spec_dir = fixture_copy()
        try:
            (spec_dir.parent / "CONSTITUTION.md").unlink()
            other = spec_dir.parent / "other-spec"
            other.mkdir()
            (other / "spec.md").write_text("placeholder", encoding="utf-8")
            code, out = run_check(str(spec_dir))
            self.assertEqual(code, 1, out)
            self.assertIn("FAIL  constitution:", out)
        finally:
            shutil.rmtree(spec_dir.parent.parent)


class ChecklistTests(unittest.TestCase):
    def test_writes_checklist_mirroring_task_state(self):
        spec_dir = fixture_copy()
        try:
            code, out = run_check(str(spec_dir), "--checklist")
            self.assertEqual(code, 0, out)
            self.assertIn("wrote", out)
            checklist = (spec_dir / "checklist.md").read_text(encoding="utf-8")
            self.assertIn("## Functional requirements", checklist)
            self.assertIn("- [ ] **FR-001**", checklist)  # T001/T002 unticked
            self.assertIn("## Acceptance criteria", checklist)
            self.assertIn("AC1", checklist)
        finally:
            shutil.rmtree(spec_dir.parent.parent)


class BrokenFixtureTests(unittest.TestCase):
    def test_dangling_fr_fails(self):
        spec_dir = fixture_copy()
        try:
            spec = (spec_dir / "spec.md").read_text(encoding="utf-8")
            lines = [l for l in spec.splitlines(True)
                     if not l.startswith("- **FR-")]
            (spec_dir / "spec.md").write_text("".join(lines), encoding="utf-8")
            code, out = run_check(str(spec_dir))
            self.assertEqual(code, 1, out)
            self.assertIn("dangling: FR-001", out)
        finally:
            shutil.rmtree(spec_dir.parent.parent)

    def test_status_bleed_fails(self):
        spec_dir = fixture_copy()
        try:
            with (spec_dir / "test.md").open("a", encoding="utf-8") as f:
                f.write("\n- [ ] a stray checkbox\n")
            code, out = run_check(str(spec_dir))
            self.assertEqual(code, 1, out)
            self.assertIn("status bleed", out)
        finally:
            shutil.rmtree(spec_dir.parent.parent)

    def test_missing_contract_file_fails(self):
        spec_dir = fixture_copy()
        try:
            (spec_dir / "plan.md").unlink()
            code, out = run_check(str(spec_dir))
            self.assertEqual(code, 1, out)
            self.assertIn("missing/empty: plan.md", out)
        finally:
            shutil.rmtree(spec_dir.parent.parent)

    def test_unmapped_ac_fails(self):
        spec_dir = fixture_copy()
        try:
            test_md = (spec_dir / "test.md").read_text(encoding="utf-8")
            (spec_dir / "test.md").write_text(
                test_md.replace("**Traces to**: FR-002, AC2",
                                "**Traces to**: FR-002"),
                encoding="utf-8",
            )
            code, out = run_check(str(spec_dir))
            self.assertEqual(code, 1, out)
            self.assertIn("traceability: AC2 has no test case", out)
        finally:
            shutil.rmtree(spec_dir.parent.parent)

    def test_ac_match_is_token_exact(self):
        spec_dir = fixture_copy()
        try:
            # AC10 names a different criterion: it must not stand in for AC1.
            test_md = (spec_dir / "test.md").read_text(encoding="utf-8")
            (spec_dir / "test.md").write_text(
                test_md.replace("**Traces to**: FR-001, AC1",
                                "**Traces to**: FR-001, AC10"),
                encoding="utf-8",
            )
            code, out = run_check(str(spec_dir))
            self.assertEqual(code, 1, out)
            self.assertIn("traceability: AC1 has no test case", out)
        finally:
            shutil.rmtree(spec_dir.parent.parent)


class IntentOnlyTests(unittest.TestCase):
    GOOD = (
        "# Intent: demo\n"
        "\n"
        "**Baseline**: intent v1 @ {sha}\n"
        "\n"
        "## Problem\n"
        "Users cannot multiply integers.\n"
        "\n"
        "## Audience\n"
        "- Calculator users chaining add calls.\n"
        "\n"
        "## Constraints\n"
        "- Stdlib only.\n"
        "\n"
        "## Questions\n"
        "- who is the audience — answered: calculator users.\n"
        "\n"
        "## FR seeds\n"
        "- **FR-001**: The system shall multiply two integers.\n"
    )

    def _commit(self, root, message, path="note.txt"):
        (root / path).write_text(message, encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "-A"],
                       check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=kit",
             "-c", "user.email=kit@example.com", "commit", "-qm", message],
            check=True, capture_output=True)
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    def _intent_root(self):
        root = Path(tempfile.mkdtemp(prefix="s2c-intent-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        subprocess.run(["git", "-C", str(root), "init", "-q"],
                       check=True, capture_output=True)
        spec = root / "specs" / "demo"
        spec.mkdir(parents=True)
        return root, spec

    def test_well_formed_intent_passes(self):
        root, spec = self._intent_root()
        sha = self._commit(root, "first")
        (spec / "intent.md").write_text(
            self.GOOD.format(sha=sha), encoding="utf-8")
        code, out = run_check(str(spec), "--intent-only")
        self.assertEqual(code, 0, out)
        self.assertIn("intent-only check:", out)
        self.assertIn("PASS (0 fail)", out)

    def test_placeholder_survivor_fails(self):
        root, spec = self._intent_root()
        sha = self._commit(root, "first")
        (spec / "intent.md").write_text(
            self.GOOD.format(sha=sha)
            + "\nAudience: <target users> everywhere.\n",
            encoding="utf-8")
        code, out = run_check(str(spec), "--intent-only")
        self.assertEqual(code, 1)
        self.assertIn("intent.md: 1 line(s) with unfilled placeholder(s)", out)
        self.assertIn("<target users>", out)

    def test_open_clarify_marker_fails(self):
        root, spec = self._intent_root()
        sha = self._commit(root, "first")
        (spec / "intent.md").write_text(
            self.GOOD.format(sha=sha)
            + "\n- [NEEDS CLARIFICATION: who funds the work?]\n",
            encoding="utf-8")
        code, out = run_check(str(spec), "--intent-only")
        self.assertEqual(code, 1)
        self.assertIn(
            "intent.md: 1 NEEDS CLARIFICATION marker(s) still open", out)

    def test_baseline_mismatch_fails(self):
        root, spec = self._intent_root()
        base = self._commit(root, "first")
        head = self._commit(root, "second")
        (spec / "intent.md").write_text(
            self.GOOD.format(sha=base), encoding="utf-8")
        code, out = run_check(str(spec), "--intent-only")
        self.assertEqual(code, 1)
        self.assertIn(f"intent.md baseline {base}, HEAD {head}", out)
        self.assertIn("re-run the analyst", out)

    def test_committing_the_kits_doc_trees_keeps_the_baseline_fresh(self):
        # committing intent.md itself — or the discover handoff it was
        # seeded from — moves HEAD past the baseline it records; only a
        # code change stales the analyst's facts
        for doc in ("specs/demo/notes.md", "brainstorms/demo.md"):
            with self.subTest(doc):
                root, spec = self._intent_root()
                base = self._commit(root, "first")
                (spec / "intent.md").write_text(
                    self.GOOD.format(sha=base), encoding="utf-8")
                (root / doc).parent.mkdir(exist_ok=True)
                head = self._commit(root, "the intake", doc)
                self.assertNotEqual(base, head)
                code, out = run_check(str(spec), "--intent-only")
                self.assertEqual(code, 0, out)
                self.assertIn("only the kit's doc trees", out)

    def test_baseline_the_repo_cannot_resolve_fails(self):
        root, spec = self._intent_root()
        self._commit(root, "first")
        (spec / "intent.md").write_text(
            self.GOOD.format(sha="0123abc"), encoding="utf-8")
        code, out = run_check(str(spec), "--intent-only")
        self.assertEqual(code, 1, out)
        self.assertIn("baseline 0123abc is not a commit in this repo", out)

    def test_full_check_notes_a_lost_or_stale_baseline(self):
        # a squash, rebase, or shallow clone loses the baseline commit,
        # and a teammate's commit moves the code, under a docset whose
        # intake already passed
        def lost(root):
            self._commit(root, "first")
            return "0123abc", "intent staleness: SKIPPED"

        def stale(root):
            base = self._commit(root, "first")
            self._commit(root, "second")
            return base, "intent staleness: stale"

        for arrange in (lost, stale):
            with self.subTest(arrange.__name__):
                spec = fixture_copy()
                root = spec.parents[1]
                self.addCleanup(shutil.rmtree, root, ignore_errors=True)
                subprocess.run(["git", "-C", str(root), "init", "-q"],
                               check=True, capture_output=True)
                sha, note = arrange(root)
                (spec / "intent.md").write_text(
                    self.GOOD.format(sha=sha), encoding="utf-8")
                code, out = run_check(str(spec), "--repo", str(root))
                self.assertEqual(code, 0, out)
                self.assertIn(note, out)

    def test_empty_required_section_and_missing_fr_seed_fail(self):
        root, spec = self._intent_root()
        sha = self._commit(root, "first")
        (spec / "intent.md").write_text(
            self.GOOD.format(sha=sha)
            .replace("- Stdlib only.\n", "<!-- none yet -->\n")
            .replace("- **FR-001**: The system shall multiply two "
                     "integers.\n", "Multiplication, somehow.\n"),
            encoding="utf-8")
        code, out = run_check(str(spec), "--intent-only")
        self.assertEqual(code, 1, out)
        self.assertIn("section `## Constraints` is missing or empty", out)
        self.assertIn("`## FR seeds` holds no `- **FR-###**:` seed", out)

    def test_baseline_mismatch_passes_once_delivered(self):
        root, spec = self._intent_root()
        base = self._commit(root, "first")
        head = self._commit(root, "second")
        (spec / "intent.md").write_text(
            self.GOOD.format(sha=base), encoding="utf-8")
        (spec / "task.md").write_text(
            f"# Task\n\n- [x] T001 do it (FR-001)\n\n"
            f"Delivered: commit @ {head}\n",
            encoding="utf-8")
        code, out = run_check(str(spec), "--intent-only")
        self.assertEqual(code, 0, out)
        self.assertIn(
            "intent staleness: SKIPPED — delivery recorded", out)

    def test_empty_intent_fails(self):
        root, spec = self._intent_root()
        (spec / "intent.md").write_text("", encoding="utf-8")
        code, out = run_check(str(spec), "--intent-only")
        self.assertEqual(code, 1)
        self.assertIn("intent.md is unfilled or empty", out)

    def test_missing_intent_fails(self):
        root, spec = self._intent_root()
        code, out = run_check(str(spec), "--intent-only")
        self.assertEqual(code, 1)
        self.assertIn("FAIL: intent.md missing", out)

    def test_full_docset_ignores_absent_intent(self):
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        code, out = run_check(str(spec))
        self.assertEqual(code, 0, out)
        self.assertNotIn("intent", out)

    def test_full_docset_checks_present_intent(self):
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        (spec / "intent.md").write_text(
            "# Intent: mini-calc\n"
            "\n"
            "**Baseline**: intent v1 @ 3fa9c21\n"
            "\n"
            "Audience: <target users> everywhere.\n",
            encoding="utf-8")
        code, out = run_check(str(spec))
        self.assertEqual(code, 1, out)
        self.assertIn("intent.md: 1 line(s) with unfilled placeholder(s)", out)

    def test_full_docset_stale_intent_passes_once_delivered(self):
        spec = fixture_copy()
        self.addCleanup(shutil.rmtree, spec.parents[1], ignore_errors=True)
        root = spec.parents[1]
        subprocess.run(["git", "-C", str(root), "init", "-q"],
                       check=True, capture_output=True)

        def commit(message):
            (root / "note.txt").write_text(message, encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "-A"],
                           check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "-c", "user.name=kit",
                 "-c", "user.email=kit@example.com", "commit", "-qm", message],
                check=True, capture_output=True)
            return subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()

        base = commit("first")
        head = commit("second")
        (spec / "intent.md").write_text(
            IntentOnlyTests.GOOD.format(sha=base), encoding="utf-8")
        task = spec / "task.md"
        task.write_text(
            task.read_text(encoding="utf-8")
            + f"\nDelivered: commit @ {head}\n",
            encoding="utf-8")
        code, out = run_check(str(spec), "--repo", str(root))
        self.assertEqual(code, 0, out)
        self.assertIn("delivery recorded", out)


class SurveyStalenessTests(unittest.TestCase):
    """A survey baseline goes stale when code moved under it, never when
    only the specs tree was committed."""

    def test_only_a_code_change_stales_the_survey_baseline(self):
        spec = fixture_copy()
        root = spec.parents[1]
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        subprocess.run(["git", "-C", str(root), "init", "-q"],
                       check=True, capture_output=True)

        def commit(rel):
            (root / rel).write_text("moved\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "-A"],
                           check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "-c", "user.name=kit",
                 "-c", "user.email=kit@example.com", "commit", "-qm", rel],
                check=True, capture_output=True)
            return subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()

        base = commit("seed.txt")
        survey = spec / "survey.md"
        survey.write_text(
            survey.read_text(encoding="utf-8").replace("3fa9c21", base),
            encoding="utf-8")
        stale = "re-survey before trusting statuses"

        commit("specs/mini-spec/notes.md")
        code, out = run_check(str(spec))
        self.assertEqual(code, 0, out)
        self.assertNotIn(stale, out)
        self.assertIn("only the kit's doc trees", out)

        commit("repo/extra.py")
        code, out = run_check(str(spec))
        self.assertIn(stale, out)


class MainArgvTests(unittest.TestCase):
    """main(argv) accepts args directly, no sys.argv patch needed — so a
    persistent process (an orchestrator's eval kernel, importing this
    module once and calling main() across many recomputes instead of
    paying a fresh interpreter + import per invocation) can drive
    check.py in-process. The CLI path (argv=None) must keep reading
    sys.argv exactly as before."""

    def test_direct_argv_matches_cli_path(self):
        spec_dir = fixture_copy()
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = check.main([str(spec_dir)])
            cli_code, cli_out = run_check(str(spec_dir))
        finally:
            shutil.rmtree(spec_dir.parent.parent)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertEqual(code, cli_code)
        self.assertEqual(buf.getvalue(), cli_out)

    def test_direct_argv_ignores_ambient_sys_argv(self):
        spec_dir = fixture_copy()
        try:
            # A leaking implementation (main reading sys.argv despite a
            # passed-in argv) would misparse this bogus ambient argv and
            # return 2 instead of running the real check.
            with unittest.mock.patch.object(
                    sys, "argv", ["check.py", "--not-a-real-flag"]):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    code = check.main([str(spec_dir)])
        finally:
            shutil.rmtree(spec_dir.parent.parent)
        self.assertEqual(code, 0, buf.getvalue())

    def test_none_argv_still_reads_sys_argv(self):
        with unittest.mock.patch.object(sys, "argv", ["check.py"]):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = check.main()
        self.assertEqual(code, 2)
        self.assertIn("Usage:", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
