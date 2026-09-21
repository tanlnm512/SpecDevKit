"""Tests for scripts/check.py — run via tests/run.sh (needs Python >= 3.10).

The green fixture in examples/mini-spec/ is the contract: any check.py
change that turns it red is a behavior change, and belongs in the
changelog. The broken-fixture tests mutate a temp copy, never the example.
"""

import contextlib
import importlib.util
import io
import shutil
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


class DefinitionTests(unittest.TestCase):
    def test_defined_families(self):
        text = (
            "### US1 — Story\n"
            "- AC1: Given x\n"
            "- **FR-001**: The system shall x\n"
            "## TC-001 — Case\n"
            "### D-001: Decision\n"
        )
        self.assertEqual(check.defined(text, "US"), {"US1"})
        self.assertEqual(check.defined(text, "AC"), {"AC1"})
        self.assertEqual(check.defined(text, "FR"), {"FR-001"})
        self.assertEqual(check.defined(text, "TC"), {"TC-001"})
        self.assertEqual(check.defined(text, "D"), {"D-001"})

    def test_defined_ignores_mentions(self):
        text = "a mention of FR-002 in prose is not a definition\n"
        self.assertEqual(check.defined(text, "FR"), set())


class ParseArgsTests(unittest.TestCase):
    def test_positional_and_flags(self):
        self.assertEqual(
            check.parse_args(["specs/x", "--fix-burndown", "--repo", "r", "--next-ids"]),
            ("specs/x", "r", True, True, False, False, False),
        )
        self.assertEqual(check.parse_args(["specs/x", "--survey-only"]),
                         ("specs/x", None, False, False, True, False, False))
        self.assertEqual(check.parse_args(["specs/x", "--constitution"]),
                         ("specs/x", None, False, False, False, True, False))
        self.assertEqual(check.parse_args(["specs/x", "--checklist"]),
                         ("specs/x", None, False, False, False, False, True))

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
