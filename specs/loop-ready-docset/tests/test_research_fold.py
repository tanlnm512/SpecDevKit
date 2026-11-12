"""FR-010's acceptance tests — the research fold cutover (T017).

The research gate's artifact lives as the `## Questions & options`
section of tech-spec.md; research.md is no longer scaffolded, and a
leftover research.md beside a folded docset is inert to the runtime
readers (specstate's parser and the graph engine).
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / "skills" / "spec-design"
SCAFFOLD = SKILL / "scripts" / "scaffold.sh"
GRAPH = SKILL / "scripts" / "graph.py"

_marker_spec = importlib.util.spec_from_file_location(
    "t017_specstate", SKILL / "scripts" / "specstate.py")
specstate = importlib.util.module_from_spec(_marker_spec)
_marker_spec.loader.exec_module(specstate)

MARKER = "not applicable — no open questions at Stage 0"


def scaffold(tmp: Path, *flags: str) -> Path:
    r = subprocess.run(
        ["bash", str(SCAFFOLD), *flags, "demo", str(tmp)],
        capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return tmp / "specs" / "demo"


def graph_state(spec_dir: Path) -> dict:
    r = subprocess.run(
        [sys.executable, str(GRAPH), str(spec_dir), "--state-json"],
        capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    import json
    return json.loads(r.stdout)


class ResearchFoldTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="t017-fold-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_questions_live_in_tech_spec_and_file_not_scaffolded(self):
        # the shipped template carries the folded section in its skip
        # form, and scaffold.sh writes no research.md at any tier
        for skill in ("spec-design", "spec-build", "spec-define"):
            templates = REPO / "skills" / skill / "templates"
            self.assertFalse(
                (templates / "research.md").exists(),
                f"{skill} still ships templates/research.md")
            tech = (templates / "tech-spec.md").read_text(encoding="utf-8")
            self.assertIn("## Questions & options", tech)
            self.assertIn("### Questions", tech)
            self.assertIn("### Options summary", tech)
            questions = tech.split("\n### Questions\n", 1)[1].split(
                "\n### Options summary", 1)[0]
            self.assertIn(MARKER, questions,
                          f"{skill}'s template ships the skip form")
        fresh = scaffold(self._tmp / "a", "--tier", "full")
        self.assertFalse((fresh / "research.md").exists())
        self.assertIn("## Questions & options",
                      (fresh / "tech-spec.md").read_text(encoding="utf-8"))
        self.assertEqual(specstate.research_state(fresh), "skip")
        tiny = scaffold(self._tmp / "b", "--tier", "tiny")
        self.assertFalse((tiny / "research.md").exists())
        # a full-tier draft from an intent keeps the section open
        intent_root = self._tmp / "c"
        (intent_root / "specs" / "demo").mkdir(parents=True)
        (intent_root / "specs" / "demo" / "intent.md").write_text(
            "# Intent: demo\n", encoding="utf-8")
        r = subprocess.run(
            ["bash", str(SCAFFOLD), "--tier", "full", "--into-existing",
             "demo", str(intent_root)], capture_output=True, text=True,
            timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        from_intent = intent_root / "specs" / "demo"
        tech = (from_intent / "tech-spec.md").read_text(encoding="utf-8")
        self.assertIn("## Questions & options", tech)
        self.assertNotIn(MARKER, tech)
        self.assertEqual(specstate.research_state(from_intent), "pending")

    def test_leftover_research_file_inert_to_runtime_readers(self):
        # a docset whose section is resolved reads the same node states
        # whether or not a pre-migration research.md sits beside it, and
        # the parser never consults the leftover file
        folded = scaffold(self._tmp / "a", "--tier", "full")
        (folded / "spec.md").write_text(
            "# Spec: demo\n\n**Status**: draft\n\n## What\nw\n\n"
            "## Why\nw\n\n## Requirements\n"
            "- **FR-001**: The system shall work.\n",
            encoding="utf-8")
        clean = graph_state(folded)
        leftover = scaffold(self._tmp / "b", "--tier", "full")
        (leftover / "spec.md").write_text(
            (folded / "spec.md").read_text(encoding="utf-8"),
            encoding="utf-8")
        (leftover / "research.md").write_text(
            f"# Research: demo\n\n{MARKER}\n\nStale skip record.\n",
            encoding="utf-8")
        self.assertEqual(specstate.research_state(leftover), "skip")
        for name in ("research-gate", "research"):
            self.assertEqual(
                clean["nodes"][name], graph_state(leftover)["nodes"][name],
                f"the leftover research.md moved the {name} node")
        # and a resolved section wins over the leftover's content
        write = leftover / "tech-spec.md"
        write.write_text(write.read_text(encoding="utf-8").replace(
            MARKER, "- Q1 — answered with real findings"),
            encoding="utf-8")
        self.assertEqual(specstate.research_state(leftover), "done")


if __name__ == "__main__":
    unittest.main(verbosity=2)
