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

    def test_discovers_fifteen_conversational_cases(self):
        self.assertEqual(len(self.cases), 15)
        self.assertTrue(all(c.conversational for c in self.cases))
        selectors = {c.selector for c in self.cases}
        self.assertIn("spec-code-review/e2", selectors)
        self.assertIn("spec-brainstorming/b5", selectors)
        self.assertIn("spec-to-prod/e6", selectors)

    def test_criteria_enumerate_from_pass_bullets(self):
        by_sel = {c.selector: c for c in self.cases}
        # scr E2's criteria bullet is semicolon-chained; the seeded-fixture
        # case parses to more than one criterion
        self.assertGreater(len(by_sel["spec-code-review/e2"].criteria), 1)
        # a single-clause bullet parses to exactly one
        self.assertGreaterEqual(len(by_sel["spec-code-review/e1"].criteria), 1)


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

    def result_text(self, name):
        p = self.tmp / "skills" / "fakeskill" / "evals" / "results" / name
        return p.read_text(encoding="utf-8") if p.exists() else None

    def test_run_mechanical_pass_records_and_exits_zero(self):
        rc = evals.main(["run", "fakeskill/m1"])
        self.assertEqual(rc, 0)
        text = self.result_text("2099-01-01-m1.md") or self.any_result("m1")
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

    def test_validate_missing_last_criterion_rejected(self):
        # the missing-criterion check must cover the FULL enumerated range,
        # including the last criterion — a transcript carrying all but Cn
        # is as incomplete as one missing C1
        bad = self.tmp / "t2.md"
        bad.write_text(COMPLETE_TRANSCRIPT.replace(
            "- C2: fail — the transcript shows the second criterion breaking at turn 7\n",
            ""), encoding="utf-8")
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

    def test_runless_case_is_malformed_never_a_pass(self):
        # a missing Run: bullet must surface as a parse failure (D-001's
        # guard), never as a mechanical run that fabricates a pass
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
