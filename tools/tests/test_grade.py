#!/usr/bin/env python3
"""Contract tests for the kit grading rubric (rubrics/kit-grading-rubric.md)
and its mechanical half (tools/grade.py).

Serves eval case: none yet mechanical — this suite IS the gate for the
grading tooling itself (C-07); the rubric's own session protocol is the
conversational half.
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import grade  # noqa: E402


RUBRIC = ROOT / "rubrics" / "kit-grading-rubric.md"


class RubricContractTests(unittest.TestCase):
    """The rubric doc and the grader must name the same dimensions,
    weights, and mechanical/judgment splits — the doc-tool pair is
    drift-checked exactly like the kit's other contract surfaces."""

    def test_rubric_exists_and_pins_every_dimension(self):
        text = RUBRIC.read_text(encoding="utf-8")
        for dims in (grade.SKILL_DIMS, grade.AGENT_DIMS, grade.WORKFLOW_DIMS):
            for did, name, weight, mech in dims:
                self.assertIn(did, text)
                self.assertIn(name, text)
                self.assertIn(f"| {did} | {name} | {weight} | {mech} |", text)

    def test_weights_sum_to_one_hundred_per_unit_type(self):
        for dims in (grade.SKILL_DIMS, grade.AGENT_DIMS, grade.WORKFLOW_DIMS):
            self.assertEqual(sum(d[2] for d in dims), 100)

    def test_mechanical_points_never_exceed_dimension_weight(self):
        for dims in (grade.SKILL_DIMS, grade.AGENT_DIMS, grade.WORKFLOW_DIMS):
            for _, _, weight, mech in dims:
                self.assertLessEqual(mech, weight)

    def test_rubric_carries_anchors_protocol_and_revision_log(self):
        text = RUBRIC.read_text(encoding="utf-8")
        for anchor in ("Score anchors", "Grading-session protocol",
                       "Mechanical inventory", "Judgment checklist", "Maintenance"):
            self.assertIn(anchor, text)


class HelperTests(unittest.TestCase):
    def test_hardcoded_model_detection(self):
        hit = "---\nmodel: sonnet\n---\nbody"
        miss = "---\nmodel: inherit\n---\nbody"
        self.assertEqual(grade.HARDCODED_MODEL.findall(hit), ["sonnet"])
        self.assertEqual(grade.HARDCODED_MODEL.findall(miss), [])

    def test_agent_sections_accept_both_brief_grammars(self):
        spec_style = "---\nname: x\ndescription: y\n---\n# X\n\n**Mission**: m\n\n## Method\n\n## Done when\n\ndigest: task T001\n\n## Guardrails\n"
        panel_style = "---\nname: x\ndescription: y\n---\n# X\n\n**Mission**: m\n\n## How to work\n\n## Output\n\nA findings list.\n\n## Readers never edit\n"
        for text in (spec_style, panel_style):
            missing = [n for n, rx, _ in grade.AGENT_SECTIONS if not rx.search(text)]
            self.assertEqual(missing, [], f"sections missed in brief grammar: {missing}")

    def test_bucket_boundaries(self):
        self.assertEqual(grade.bucket(300, [(300, 5), (600, 4)], 2), 5)
        self.assertEqual(grade.bucket(301, [(300, 5), (600, 4)], 2), 4)
        self.assertEqual(grade.bucket(9999, [(300, 5), (600, 4)], 2), 2)

    def test_runtime_detection_requires_execution_not_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp) / "tools" / "tests"
            tests_dir.mkdir(parents=True)
            fake = tests_dir / "test_workflow_runtime.py"
            fake.write_text("executes the workflow against stubs", encoding="utf-8")
            orig_root = grade.ROOT
            grade.ROOT = Path(tmp)
            try:
                # No skills dir here: discovery degrades to empty, the
                # single candidate file is what the check must find.
                self.assertEqual(
                    grade.workflow_runtime_test_exists(),
                    "tools/tests/test_workflow_runtime.py",
                )
            finally:
                grade.ROOT = orig_root


class RepoSmokeTests(unittest.TestCase):
    """Grader runs against the real repo (fast checks only) and its
    report names every unit the kit actually ships."""

    @classmethod
    def setUpClass(cls):
        cls.rc, cls.report = cls._run()

    @staticmethod
    def _run():
        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = grade.main(["--skip-suites", "--skip-sync"])
        return rc, buf.getvalue()

    def test_grader_exits_clean_and_reports_every_unit(self):
        self.assertEqual(self.rc, 0)
        for unit in ("skill:spec-to-prod", "skill:spec-code-review",
                     "skill:spec-brainstorming", "agent:spec-surveyor",
                     "agent:code-review-correctness", "agent:brainstorm-cynic",
                     "workflow:spec-to-prod", "workflow:spec-code-review",
                     "workflow:spec-brainstorming"):
            self.assertIn(unit, self.report)

    def test_report_discloses_skipped_checks_and_judgment_worksheet(self):
        self.assertIn("skipped (--skip-suites)", self.report)
        self.assertIn("Judgment (fill, with verbatim evidence):", self.report)
        self.assertIn("Defects found this session", self.report)

    def test_mechanical_composites_land_in_range(self):
        scores = re.findall(r"mechanical ([\d.]+)/10", self.report)
        self.assertTrue(scores, "no mechanical composites rendered")
        for s in scores:
            self.assertGreaterEqual(float(s), 0.0)
            self.assertLessEqual(float(s), 10.0)


if __name__ == "__main__":
    unittest.main()
