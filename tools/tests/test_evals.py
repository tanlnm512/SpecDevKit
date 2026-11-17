"""tools/evals.py — the eval runner's contract.

The real corpus is read-only here: discovery and criteria enumeration
run against the repo's actual case files, while every write-path test
(list/run/validate results, atomicity, the overwrite guard) runs on a
synthetic skills tree in a temp dir with the module's ROOT repointed —
no test may plant files in the repo's own evals/results/ evidence.
"""

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "evals.py"
_spec = importlib.util.spec_from_file_location("evals", TOOL)
evals = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evals)

FIXTURE = """\
# Eval cases — fakeskill

Standing cases for the synthetic fixture.

## M1 — mechanical pass
- **Pass criteria**: the command exits zero; output says ok
- **Run**: true && echo ok

## M2 — mechanical fail
- **Pass criteria**: the command exits zero
- **Run**: false

## C1 — conversational case
- **Run**: session: do the thing in a session; judge from the transcript against the criteria above
- **Pass criteria**: first criterion holds; second criterion holds

## H1 — hybrid case
- **Pass criteria**: the file exists; the marker line holds; the session judged the flow
- **Check C1**: test -f prepared.txt
- **Check C2**: grep -q marker prepared.txt
- **Run**: session: do the hybrid thing in a session; judge the flow against the criteria above

## C2 — held-out case
- **Held-out**: yes
- **Pass criteria**: first criterion holds; second criterion holds
- **Run**: session: held-out procedure; judge from the transcript
"""

COMPLETE_TRANSCRIPT = """\
# Session transcript — fakeskill/c1

The session ran; the observer judged.

## Verdicts

- C1: pass — the transcript shows the first criterion holding at turn 3
- C2: fail — the transcript shows the second criterion breaking at turn 7
"""

INCOMPLETE_TRANSCRIPT = """\
# Session transcript — fakeskill/c1

## Verdicts

- C1: pass — the transcript shows the first criterion holding at turn 3
"""


class RealCorpusTests(unittest.TestCase):
    def setUp(self):
        self.cases = evals.load_cases()

    def test_discovers_every_conversational_case(self):
        self.assertEqual(len(self.cases), 34)
        self.assertTrue(all(c.conversational for c in self.cases))
        selectors = {c.selector for c in self.cases}
        self.assertIn("spec-review/e2", selectors)
        self.assertIn("spec-discover/b5", selectors)
        self.assertIn("spec-define/i1", selectors)
        # skill-prefixed selectors name each case's home skill
        self.assertIn("spec-design/e1", selectors)
        self.assertIn("spec-design/e7", selectors)
        self.assertIn("spec-design/e8", selectors)
        self.assertIn("spec-build/e4", selectors)
        self.assertIn("spec-build/e6", selectors)

    def test_criteria_enumerate_from_pass_bullets(self):
        by_sel = {c.selector: c for c in self.cases}
        # semicolon-chained criteria enumerate separately
        self.assertGreater(len(by_sel["spec-review/e2"].criteria), 1)
        # a single-clause bullet parses to exactly one
        self.assertGreaterEqual(len(by_sel["spec-review/e1"].criteria), 1)

    def test_corpus_split_pins_the_held_out_set(self):
        # the ~40% adversarial/negative-path split is a recorded contract (D-061)
        held = sorted(c.selector for c in self.cases if c.held_out)
        self.assertEqual(len(held), 15)
        for sel in ("spec-ship/s2", "spec-ship/s4", "spec-ship/s5",
                    "spec-build/e5", "spec-build/e6", "spec-build/e9",
                    "spec-define/i2", "spec-design/e3", "spec-discover/b5",
                    "spec-release/r2", "spec-review/e1"):
            self.assertIn(sel, held)

    def test_pilot_checks_live_on_spec_build_e8_and_e9(self):
        checked = sorted(c.selector for c in self.cases if c.checks)
        self.assertEqual(checked, ["spec-build/e8", "spec-build/e9"])
        for c in self.cases:
            ns = [n for n, _ in c.checks]
            self.assertTrue(all(1 <= n <= len(c.criteria) for n in ns),
                            f"{c.selector} has out-of-range checks")


class FixtureTests(unittest.TestCase):
    """Write-path contract on a synthetic skills tree (ROOT repointed)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cases = self.tmp / "skills" / "fakeskill" / "evals"
        cases.mkdir(parents=True)
        (cases / "cases.md").write_text(FIXTURE, encoding="utf-8")
        self.orig_root = evals.ROOT
        evals.ROOT = self.tmp

    def tearDown(self):
        evals.ROOT = self.orig_root
        shutil.rmtree(self.tmp)

    def test_run_mechanical_pass_records_and_exits_zero(self):
        rc = evals.main(["run", "fakeskill/m1"])
        self.assertEqual(rc, 0)
        text = self.any_result("m1")
        self.assertIn("- C1: pass", text)
        self.assertIn("exited 0", text)
        self.assertNotIn("## Contract-bent", text)

    def test_run_fail_refuses_overwrite_and_exits_nonzero(self):
        evals.main(["run", "fakeskill/m2", "--overwrite"])
        first = self.any_result("m2")
        rc = evals.main(["run", "fakeskill/m2"])  # no --overwrite
        self.assertEqual(rc, 1)
        self.assertEqual(self.any_result("m2"), first)  # evidence intact
        rc = evals.main(["run", "fakeskill/m2", "--overwrite"])
        self.assertEqual(rc, 1)  # failing command, but the record refreshed

    def test_validate_incomplete_rejected_writes_nothing(self):
        bad = self.tmp / "t.md"
        bad.write_text(INCOMPLETE_TRANSCRIPT, encoding="utf-8")
        rc = evals.main(["validate", "fakeskill/c1", str(bad)])
        self.assertEqual(rc, 1)
        self.assertIsNone(self.any_result("c1"))

    def test_validate_complete_records_findings_and_contract_bent(self):
        good = self.tmp / "t.md"
        good.write_text(COMPLETE_TRANSCRIPT, encoding="utf-8")
        rc = evals.main(["validate", "fakeskill/c1", str(good),
                         "--contract-bent", "the session bent rule X to finish"])
        self.assertEqual(rc, 0)
        text = self.any_result("c1")
        self.assertIn("- C1: pass", text)
        self.assertIn("- C2: fail", text)
        self.assertIn("## Findings", text)
        self.assertIn("- C2: the transcript shows", text)
        self.assertIn("## Contract-bent", text)
        self.assertIn("the session bent rule X to finish", text)
        self.assertIn("kind: conversational", text)

    def test_result_is_fresh_until_the_skill_surface_changes(self):
        case = evals.find_case(evals.load_cases(), "fakeskill/m1")
        self.assertEqual(evals.latest_result(case)[0], "none")
        evals.main(["run", "fakeskill/m1"])
        self.assertEqual(evals.latest_result(case)[0], "fresh")
        skill = self.tmp / "skills" / "fakeskill"
        # evidence and case files are not the surface a run reads
        (skill / "evals" / "cases.md").write_text(FIXTURE + "\n", encoding="utf-8")
        self.assertEqual(evals.latest_result(case)[0], "fresh")
        (skill / "SKILL.md").write_text("# changed\n", encoding="utf-8")
        self.assertEqual(evals.latest_result(case)[0], "stale")

    def test_result_without_a_stamp_is_never_fresh(self):
        case = evals.find_case(evals.load_cases(), "fakeskill/m1")
        d = self.tmp / "skills" / "fakeskill" / "evals" / "results"
        d.mkdir()
        (d / "2026-01-01-m1.md").write_text("- C1: pass — old\n", encoding="utf-8")
        self.assertEqual(evals.latest_result(case)[0], "unstamped")

    def test_validate_without_transcript_prints_procedure(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = evals.main(["validate", "fakeskill/c1"])
        self.assertEqual(rc, 0)
        self.assertIn("session procedure", buf.getvalue())
        self.assertIn("do the thing in a session", buf.getvalue())

    def test_run_conversational_prints_procedure_not_results(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = evals.main(["run", "fakeskill/c1"])
        self.assertEqual(rc, 0)
        self.assertIn("conversational", buf.getvalue())
        self.assertIsNone(self.any_result("c1"))

    def test_run_hybrid_prints_sheet_records_nothing(self):
        import contextlib, io, os
        repo = self.tmp / "repo"
        repo.mkdir()
        (repo / "prepared.txt").write_text("the marker line\n", encoding="utf-8")
        cwd = os.getcwd()
        os.chdir(repo)
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = evals.main(["run", "fakeskill/h1"])
        finally:
            os.chdir(cwd)
        self.assertEqual(rc, 0)
        self.assertIn("C1: pass", buf.getvalue())
        self.assertIn("C3", buf.getvalue())  # the criterion no check covers
        self.assertIsNone(self.any_result("h1"))

    def test_run_hybrid_failing_check_exits_nonzero(self):
        import os
        (self.tmp / "repo").mkdir()  # no prepared.txt: C1, C2 fail
        cwd = os.getcwd()
        os.chdir(self.tmp / "repo")
        try:
            rc = evals.main(["run", "fakeskill/h1"])
        finally:
            os.chdir(cwd)
        self.assertEqual(rc, 1)
        self.assertIsNone(self.any_result("h1"))

    def test_validate_hybrid_merges_checks_with_transcript(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        (repo / "prepared.txt").write_text("the marker line\n", encoding="utf-8")
        t = self.tmp / "h1.md"
        t.write_text("# t\n\n- C3: pass — the session judged the flow at turn 2\n",
                     encoding="utf-8")
        rc = evals.main(["validate", "fakeskill/h1", str(t), "--repo", str(repo)])
        self.assertEqual(rc, 0)
        text = self.any_result("h1")
        self.assertIn("- C1: pass — check `test -f prepared.txt` exited 0", text)
        self.assertIn("- C2: pass", text)
        self.assertIn("- C3: pass — the session judged the flow", text)
        self.assertIn("None — every criterion passed.", text)

    def test_validate_hybrid_check_beats_observer_verdict(self):
        repo = self.tmp / "repo"
        repo.mkdir()  # prepared.txt missing: checks fail, observer claims pass
        t = self.tmp / "h1.md"
        t.write_text("# t\n\n- C1: pass — observer claims the file exists\n"
                     "- C3: fail — the flow broke at turn 4\n", encoding="utf-8")
        rc = evals.main(["validate", "fakeskill/h1", str(t), "--repo", str(repo)])
        self.assertEqual(rc, 0)
        text = self.any_result("h1")
        self.assertIn("- C1: fail — check `test -f prepared.txt` exited 1", text)
        self.assertIn("- C2: fail", text)
        self.assertIn("contradicts the check", text)
        self.assertIn("- C3: the flow broke at turn 4", text)

    def test_validate_hybrid_observer_fail_on_green_check_stays_a_finding(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        (repo / "prepared.txt").write_text("the marker line\n", encoding="utf-8")
        t = self.tmp / "h1.md"
        t.write_text("# t\n\n- C1: fail — the observer saw the file missing mid-session\n"
                     "- C3: pass — the flow held\n", encoding="utf-8")
        rc = evals.main(["validate", "fakeskill/h1", str(t), "--repo", str(repo)])
        self.assertEqual(rc, 0)
        text = self.any_result("h1")
        self.assertIn("- C1: pass — check `test -f prepared.txt` exited 0", text)
        self.assertIn("- C1: observer verdict (fail) contradicts the check", text)
        self.assertIn("- C2: pass", text)  # green check, no observer verdict

    def test_validate_hybrid_still_requires_unchecked_verdicts(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        (repo / "prepared.txt").write_text("the marker line\n", encoding="utf-8")
        t = self.tmp / "h1.md"
        t.write_text("# t\n\nonly checks ran, the observer said nothing about C3\n",
                     encoding="utf-8")
        rc = evals.main(["validate", "fakeskill/h1", str(t), "--repo", str(repo)])
        self.assertEqual(rc, 1)
        self.assertIsNone(self.any_result("h1"))

    def test_malformed_check_bullets_are_a_usage_error(self):
        d2 = self.tmp / "skills" / "badchecks" / "evals"
        d2.mkdir(parents=True)
        (d2 / "cases.md").write_text(
            "# Eval cases\n\n## X1 — bad checks\n"
            "- **Pass criteria**: it holds; it also holds\n"
            "- **Check C9**: true\n"
            "- **Check C2**: true\n"
            "- **Check C2**: true\n"
            "- **Run**: session: do it\n", encoding="utf-8")
        self.assertEqual(evals.main(["run", "badchecks/x1"]), 2)
        good = self.tmp / "x.md"
        good.write_text("- C1: pass — seen\n", encoding="utf-8")
        self.assertEqual(evals.main(["validate", "badchecks/x1", str(good)]), 2)
        self.assertIsNone(self.any_result("x1"))

    def test_held_out_procedure_notes_withholding(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = evals.main(["procedure", "fakeskill/c2"])
        self.assertEqual(rc, 0)
        self.assertIn("held-out case", buf.getvalue())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = evals.main(["procedure", "fakeskill/c1"])
        self.assertEqual(rc, 0)
        self.assertNotIn("held-out", buf.getvalue())

    def test_report_counts_split_and_verdicts(self):
        import contextlib, io
        evals.main(["run", "fakeskill/m1"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = evals.main(["report"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("heldout", out)
        self.assertIn("fakeskill", out)
        self.assertIn("2/2", out)  # m1's two criteria, both stamped pass
        self.assertIn("corpus", out)

    def test_runless_case_is_malformed_never_a_pass(self):
        # a missing Run: bullet is a parse failure, never a run that fabricates a pass
        d2 = self.tmp / "skills" / "runless" / "evals"
        d2.mkdir(parents=True)
        (d2 / "cases.md").write_text(
            "# Eval cases\n\n## X1 — no run bullet\n"
            "- **Pass criteria**: it holds\n", encoding="utf-8")
        self.assertEqual(evals.main(["list"]), 2)
        self.assertEqual(evals.main(["run", "runless/x1"]), 2)
        self.assertEqual(evals.main(["validate", "runless/x1"]), 2)
        self.assertIsNone(self.any_result("x1"))

    def test_unknown_selector_is_a_usage_error(self):
        self.assertEqual(evals.main(["run", "nope/nope"]), 2)
        self.assertEqual(evals.main(["validate", "nope/nope"]), 2)

    def any_result(self, cid):
        d = self.tmp / "skills" / "fakeskill" / "evals" / "results"
        if not d.is_dir():
            return None
        hits = sorted(d.glob(f"*-{cid}.md"))
        return hits[-1].read_text(encoding="utf-8") if hits else None


if __name__ == "__main__":
    unittest.main(verbosity=2)
