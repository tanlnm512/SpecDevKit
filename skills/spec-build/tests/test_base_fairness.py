"""Base fairness (spec-build D-048): a red repository check is charged
to the change only when the base passes. `regression` runs the gate on
the head first; only a red repo check sends it to a detached temporary
worktree of the approved base for the same check's own run. Outcomes,
each from evidence: FAIL (charged — the base is green there, or fails
differently), PREEXISTING (the same failures at the base — not charged,
red until the owner rules `- Regression: <check> — <ruling>` in the
delivery block), UNKNOWN (the base could not be checked). A charged
FAIL is never rulable. The tests run real gate.sh in throwaway git
repos and pin the six contract cases, the worktree lifecycle, the
ruling, block's draft, dod gate 3, and the signature/volatility rules
the comparison decides by.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SKILL = HERE.parent
_SCRIPTS = SKILL / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from test_execute_gates import hand_docset, write  # noqa: E402

_spec = importlib.util.spec_from_file_location("audit", _SCRIPTS / "audit.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

AUDIT = _SCRIPTS / "audit.py"
MAKEFILE = "test:\n\tpython3 -m unittest discover -s tests -t .\n"

GREEN_A = (
    "import unittest\n\n"
    "class MathTest(unittest.TestCase):\n"
    "    def test_a(self):\n"
    '        assert 1 + 1 == 2, "a"\n'
)
RED_A = GREEN_A.replace('== 2, "a"', '== 3, "a"')
RED_AB = RED_A.replace(
    '== 3, "a"\n',
    '== 3, "a"\n\n'
    "    def test_b(self):\n"
    '        assert 2 * 2 == 5, "b"\n',
)


def git(repo: Path, *argv: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *argv],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"git {argv} failed: {r.stderr}")
    return r.stdout


def gate_repo(tmp: Path, name: str, base_tests: str,
              head_tests: str | None = None,
              head_extra: dict[str, str] | None = None) -> tuple[Path, Path, str]:
    """A real git repo whose committed base carries the check, plus its
    working-tree head: (repo, spec dir, base sha). The docset lands
    after the commit — the explicit --base, not the freeze, anchors the
    comparison."""
    repo = tmp / name
    (repo / "tests").mkdir(parents=True)
    write(repo / "Makefile", MAKEFILE)
    write(repo / "tests" / "__init__.py", "")
    write(repo / "tests" / "test_math.py", base_tests)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "fair@example.com")
    git(repo, "config", "user.name", "Fair Test")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD").strip()
    write(repo / "tests" / "test_math.py", head_tests or base_tests)
    for rel, text in (head_extra or {}).items():
        write(repo / rel, text)
    spec = hand_docset(repo, "approved")
    return repo, spec, base


def rule(spec: Path, *lines: str) -> Path:
    """Record owner lines in the status holder's delivery block — the
    text dod's gates and regression_rulings read."""
    holder = spec / "task.md"
    write(holder, holder.read_text(encoding="utf-8")
          + "\n**Delivered**: commit @ -\n" + "\n".join(lines) + "\n")
    return spec


class FairnessCliTests(unittest.TestCase):
    """The six contract cases, each against real gate.sh runs in a real
    temporary git repository."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="fair-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def audit_cli(self, spec: Path, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.tel),
                   KIT_TELEMETRY="on")
        return subprocess.run(
            [sys.executable, str(AUDIT), args[0], str(spec), *args[1:]],
            capture_output=True, text=True, timeout=300, env=env)

    def test_base_green_head_red_gives_fail(self):
        repo, spec, base = gate_repo(self._tmp, "charged", GREEN_A, RED_A)
        r = self.audit_cli(spec, "regression", "--base", base)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("base: FAIL", r.stdout)
        self.assertRegex(r.stdout, r"base: FAIL — green at \w")
        self.assertRegex(r.stdout,
                         r"regression: FAIL — failing: make test \(charged:")
        self.assertNotIn("PREEXISTING", r.stdout)
        self.assertNotIn("UNKNOWN", r.stdout)

    def test_same_failure_reads_preexisting_and_passes_ruled(self):
        repo, spec, base = gate_repo(
            self._tmp, "same", RED_A, RED_A,
            {"README.md": "docs the tests never read\n"})
        r = self.audit_cli(spec, "regression", "--base", base)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("base: PREEXISTING", r.stdout)
        self.assertIn("with the same output", r.stdout)
        self.assertIn("(preexisting — the base fails too; unruled)", r.stdout)
        # unruled, the check is drafted for the delivery block
        blk = self.audit_cli(spec, "block", "--base", base)
        self.assertIn("- Regression: make test — <ruling>", blk.stdout)
        # the owner's ruling turns the row RULED and the mode green
        rule(spec, "- Regression: make test — red before this change; "
                   "fix tracked in specs/BACKLOG.md (D-048)")
        r = self.audit_cli(spec, "regression", "--base", base)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RULED     make test", r.stdout)
        self.assertIn(
            "regression: PASS — red only where the base is red — ruled in "
            "the delivery block: make test", r.stdout)
        # and block no longer drafts the line
        blk = self.audit_cli(spec, "block", "--base", base)
        self.assertNotIn("- Regression:", blk.stdout)

    def test_dod_gate3_passes_only_once_ruled(self):
        repo, spec, base = gate_repo(
            self._tmp, "dod", RED_A, RED_A,
            {"README.md": "docs\n"})
        dod = self.audit_cli(spec, "dod", "--base", base)
        self.assertRegex(dod.stdout,
                         r"(?m)^\s+3 REGRESSION\s+FAIL\s+failing: make test")
        rule(spec, "- Regression: make test — red at the approved base too (D-048)")
        dod = self.audit_cli(spec, "dod", "--base", base)
        self.assertRegex(dod.stdout, r"(?m)^\s+3 REGRESSION\s+PASS\s")
        self.assertIn("ruled in the delivery block: make test", dod.stdout)

    def test_base_red_on_one_head_red_on_two_gives_fail(self):
        repo, spec, base = gate_repo(self._tmp, "subset", RED_A, RED_AB)
        r = self.audit_cli(spec, "regression", "--base", base)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"base: FAIL — ")
        self.assertIn("(charged:", r.stdout)
        # a charged FAIL never reads from a ruling
        rule(spec, "- Regression: make test — owner rules to proceed anyway")
        r = self.audit_cli(spec, "regression", "--base", base)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("RULED", r.stdout)
        blk = self.audit_cli(spec, "block", "--base", base)
        self.assertNotIn("- Regression:", blk.stdout)

    def test_an_uncheckable_base_reads_unknown_red_until_ruled(self):
        # the base predates the check itself: no `make test` row exists
        # there, so the base cannot be checked — neither passed nor
        # charged, red until the owner's ruling
        repo = self._tmp / "uncheckable"
        repo.mkdir()
        write(repo / "README.md", "docs\n")
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "fair@example.com")
        git(repo, "config", "user.name", "Fair Test")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "base without checks")
        base = git(repo, "rev-parse", "HEAD").strip()
        write(repo / "Makefile", MAKEFILE)
        (repo / "tests").mkdir()
        write(repo / "tests" / "test_math.py", RED_A)
        spec = hand_docset(repo, "approved")
        r = self.audit_cli(spec, "regression", "--base", base)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("base: UNKNOWN", r.stdout)
        self.assertIn("does not exist at", r.stdout)
        self.assertIn("(unknown — the base could not be checked; unruled)",
                      r.stdout)
        blk = self.audit_cli(spec, "block", "--base", base)
        self.assertIn("- Regression: make test — <ruling>", blk.stdout)
        rule(spec, "- Regression: make test — the check arrives with this "
                   "change; its red is the change's to fix next (D-048)")
        r = self.audit_cli(spec, "regression", "--base", base)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RULED     make test", r.stdout)

    def test_a_green_head_never_runs_the_base_check(self):
        repo, spec, base = gate_repo(self._tmp, "green", GREEN_A, GREEN_A)
        calls: list[str] = []
        original = audit._base_worktree

        def spy(repo_arg, ref):
            calls.append(ref)
            return original(repo_arg, ref)

        audit._base_worktree = spy
        self.addCleanup(setattr, audit, "_base_worktree", original)
        data = audit.regression_data(spec, repo, base)
        self.assertEqual(data["state"], "PASS", data["detail"])
        self.assertEqual(data["failures"], {})
        self.assertEqual(calls, [], "the base checkout must not run for a green head")
        wl = git(repo, "worktree", "list")
        self.assertEqual(len(wl.strip().splitlines()), 1, wl)

    def test_the_worktree_is_gone_after_a_failing_run(self):
        repo, spec, base = gate_repo(self._tmp, "gone", GREEN_A, RED_A)
        before = set(Path(tempfile.gettempdir()).glob("audit-base-*"))
        status_before = git(repo, "status", "--porcelain")
        r = self.audit_cli(spec, "regression", "--base", base)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        after = set(Path(tempfile.gettempdir()).glob("audit-base-*"))
        self.assertFalse(after - before, "a temporary worktree survived the run")
        wl = git(repo, "worktree", "list")
        self.assertEqual(len(wl.strip().splitlines()), 1, wl)
        # the working tree and index are never touched: the only entry a
        # run may add is the gate's own __pycache__ (pre-existing gate
        # behavior, never delivery surface — audit.CACHE_PATH)
        gained = [ln for ln in
                  set(git(repo, "status", "--porcelain").splitlines())
                  - set(status_before.splitlines())]
        self.assertFalse([ln for ln in gained
                          if not audit.CACHE_PATH.search(ln[3:].strip('"'))],
                         gained)


class OutcomeDecisionTests(unittest.TestCase):
    """The comparison decides from the outputs, never the exit codes
    alone: signature subsets, and the stripped-output fallback."""

    def row(self, code: int, tail: str, name: str = "make test") -> dict:
        return {"name": name, "exit_code": code, "tail": tail, "source": "repo"}

    def outcome(self, head: dict, base: dict | None, base_ref="abc1234"):
        return audit._outcome_vs_base(head, base, base_ref, ruled=set())

    def test_the_same_signatures_are_preexisting(self):
        sig = "FAILED tests/test_math.py::MathTest::test_a"
        oc = self.outcome(self.row(2, f"{sig} - AssertionError: 2 != 3"),
                          self.row(2, sig))
        self.assertEqual(oc["outcome"], "PREEXISTING")
        self.assertEqual(oc["base_failures"], [sig])

    def test_a_signature_the_base_lacks_is_charged(self):
        oc = self.outcome(
            self.row(2, "FAILED tests/test_math.py::MathTest::test_a\n"
                        "FAILED tests/test_math.py::MathTest::test_b"),
            self.row(2, "FAILED tests/test_math.py::MathTest::test_a"))
        self.assertEqual(oc["outcome"], "FAIL")
        self.assertIn("test_b", oc["detail"])
        self.assertEqual(oc["base_failures"],
                         ["FAILED tests/test_math.py::MathTest::test_a"])

    def test_a_green_base_row_charges(self):
        oc = self.outcome(self.row(2, "anything red"), self.row(0, "all green"))
        self.assertEqual(oc["outcome"], "FAIL")
        self.assertFalse(oc["ruled"])

    def test_a_missing_base_row_is_unknown(self):
        oc = self.outcome(self.row(2, "red"), None)
        self.assertEqual(oc["outcome"], "UNKNOWN")
        self.assertIn("does not exist at abc1234", oc["detail"])

    def test_one_readable_failure_is_unknown(self):
        oc = self.outcome(self.row(2, "FAILED a.py::t"), self.row(2, "boom"))
        self.assertEqual(oc["outcome"], "UNKNOWN")
        self.assertIn("only one output carries a readable failure", oc["detail"])

    def test_the_stripped_outputs_decide_when_no_signature_exists(self):
        head_tail = ('File "/tmp/h/repo/tests/test_math.py", line 5, in test_a\n'
                     "AssertionError: a\n\n"
                     "Ran 1 test in 0.000s\n\nFAILED (failures=1)")
        base_tail = ('File "/tmp/base-wt/tests/test_math.py", line 5, in test_a\n'
                     "AssertionError: a\n\n"
                     "Ran 1 test in 0.002s\n\nFAILED (failures=1)")
        oc = self.outcome(self.row(2, head_tail), self.row(2, base_tail))
        self.assertEqual(oc["outcome"], "PREEXISTING")
        other = self.outcome(self.row(2, head_tail.replace("test_a", "test_b")),
                             self.row(2, base_tail))
        self.assertEqual(other["outcome"], "FAIL")
        self.assertIn("output differs", other["detail"])

    def test_a_builtin_row_stays_charged_without_a_base_run(self):
        calls: list = []
        original = audit._base_worktree

        def spy(repo_arg, ref):
            calls.append(ref)
            return original(repo_arg, ref)

        audit._base_worktree = spy
        self.addCleanup(setattr, audit, "_base_worktree", original)
        outcomes = audit.base_fairness(
            None, Path("."), [{"name": "secrets (token patterns on the change)",
                               "exit_code": 1, "tail": "x", "source": "builtin"}],
            "abc1234")
        self.assertEqual(calls, [], "a builtin row has no base run")
        oc = outcomes["secrets (token patterns on the change)"]
        self.assertEqual(oc["outcome"], "FAIL")
        self.assertIn("no change to scan", oc["detail"])


class SignatureTests(unittest.TestCase):
    """One failing-test signature per runner dialect the gate detects;
    the unittest summary line is not one — the whole-output fallback
    owns the dialects it cannot read."""

    def sigs(self, text: str) -> list[str]:
        return audit.failure_signatures(text)

    def test_pytest_summary_lines(self):
        self.assertEqual(
            self.sigs("FAILED tests/test_math.py::MathTest::test_a - "
                      "AssertionError: 2 != 3\n1 failed in 0.05s"),
            ["FAILED tests/test_math.py::MathTest::test_a"])

    def test_unittest_fail_and_error_lines(self):
        self.assertEqual(
            self.sigs("FAIL: test_a (tests.test_math.MathTest)\n"
                      "ERROR: test_b (tests.test_math.MathTest)\n"
                      "FAILED (failures=2)"),
            ["FAIL tests.test_math.MathTest.test_a",
             "ERROR tests.test_math.MathTest.test_b"])

    def test_go_fail_lines_include_the_subtest_and_package(self):
        self.assertEqual(
            self.sigs("--- FAIL: TestMultiply (0.00s)\n"
                      "    math_test.go:12: nope\n"
                      "--- FAIL: TestMultiply/table_2x3 (0.00s)\n"
                      "FAIL\nFAIL pkg 0.1s"),
            ["--- FAIL: TestMultiply", "--- FAIL: TestMultiply/table_2x3",
             "FAIL pkg"])

    def test_jest_and_vitest_markers(self):
        self.assertEqual(
            self.sigs("FAIL src/math.test.js\n"
                      "  ● suite\n"
                      "  ✕ multiplies numbers (5 ms)\n"
                      "  × shouts 12ms"),
            ["FAIL src/math.test.js", "✕ multiplies numbers", "✕ shouts"])

    def test_maven_and_gradle_error_test_lines(self):
        self.assertEqual(
            self.sigs("[ERROR]   MathTest.testAdd:15 expected:<4> was:<3>\n"
                      "[ERROR] MathTest.testDiv:9 x"),
            ["[ERROR] MathTest.testAdd", "[ERROR] MathTest.testDiv"])

    def test_cargo_and_tap_lines(self):
        self.assertEqual(
            self.sigs("test math::tests::multiplies ... FAILED\n"
                      "test result: FAILED. 1 passed; 1 failed\n"
                      "not ok 3 - shouts loudly\n"
                      "not ok 12 plain failure"),
            ["test math::tests::multiplies",
             "not ok - shouts loudly",
             "not ok - plain failure"])

    def test_an_output_without_a_readable_failure_yields_none(self):
        self.assertEqual(self.sigs("make: *** [test] Error 1\n"
                                   "FAILED (failures=1)\n"
                                   "Ran 2 tests in 0.000s\n"), [])

    def test_signatures_dedupe_in_order(self):
        self.assertEqual(
            self.sigs("not ok 1 - a\nnot ok 2 - a\nnot ok 3 - b"),
            ["not ok - a", "not ok - b"])


class StripVolatileTests(unittest.TestCase):
    """What two runs of the same failure may not differ in is stripped
    before the fallback compare."""

    def test_timings_dates_paths_and_line_numbers_are_stripped(self):
        self.assertEqual(
            audit.strip_volatile(
                'File "/tmp/audit-base-x/wt/tests/test_math.py", line 5, '
                "in test_a\n"
                "Ran 2 tests in 0.001s\n"
                "--- FAIL: TestX (0.00s)\n"
                "ran at 2026-11-25T10:00:00\n"
                "took 3s total"),
            'File "test_math.py", line <ln>, in test_a\n'
            "Ran 2 tests <dur>\n"
            "--- FAIL: TestX (<dur>)\n"
            "ran at <date>\n"
            "<dur> total")

    def test_two_checkouts_of_the_same_failure_compare_equal(self):
        head = ('  File "/tmp/h/repo/tests/test_math.py", line 4, in test_a\n'
                "AssertionError: a\n")
        base = ('  File "/var/folders/T/audit-base-y/wt/tests/test_math.py",'
                " line 4, in test_a\n"
                "AssertionError: a\n")
        self.assertEqual(audit.strip_volatile(head), audit.strip_volatile(base))


class RegressionRulingTests(unittest.TestCase):
    """`- Regression: <check> — <ruling>` names the check before the
    em-dash — names carry spaces ("make test") — and a charged FAIL is
    never turned by one (decided in failure_state, not the regex)."""

    def test_the_ruling_captures_a_spaced_check_name(self):
        tmp = Path(tempfile.mkdtemp(prefix="fair-ruling-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        spec = tmp / "specs" / "hand"
        spec.mkdir(parents=True)
        write(spec / "task.md",
              "**Delivered**: commit @ -\n"
              "- Regression: make test — red before the change (D-048)\n"
              "- Regression: `pytest (.venv)` — environment-specific\n")
        self.assertEqual(
            audit.regression_rulings(spec),
            {"make test", "pytest (.venv)"})

    def test_failure_state_stays_red_on_any_charged_fail(self):
        state, detail = audit.failure_state({
            "make test": {"outcome": "PREEXISTING", "ruled": True, "detail": ""},
            "npm run lint": {"outcome": "FAIL", "ruled": False,
                             "detail": "green at abc1234"},
        })
        self.assertEqual(state, "FAIL")
        self.assertIn("npm run lint (charged: green at abc1234)", detail)
        self.assertNotIn("make test", detail)

    def test_failure_state_passes_when_every_red_is_ruled(self):
        state, detail = audit.failure_state({
            "make test": {"outcome": "PREEXISTING", "ruled": True, "detail": ""},
            "npm run lint": {"outcome": "UNKNOWN", "ruled": True, "detail": ""},
        })
        self.assertEqual(state, "PASS")
        self.assertIn("ruled in the delivery block", detail)
        self.assertIn("make test", detail)


if __name__ == "__main__":
    unittest.main(verbosity=2)
