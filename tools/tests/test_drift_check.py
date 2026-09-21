"""Tests for tools/drift-check.py — release validation of the four
generated surfaces (workflows, manifests, diagrams, examples) against
their canonical sources (FR-006).

Per surface, the same contract: a clean tree passes; a mutated generated
output fails nonzero with the canonical generator named; regeneration
(or restoration, where no generator exists) passes again. Mutation tests
run against a full repo copy — never the live tree.
"""
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIFT_CHECK = REPO_ROOT / "tools" / "drift-check.py"
MODEL = REPO_ROOT / "skills" / "spec-to-prod" / "diagrams" / "spec-to-prod-workflow.mmd"

_spec = importlib.util.spec_from_file_location("drift_check", DRIFT_CHECK)
drift_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drift_check)


def run_py(script: Path, *argv) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", str(script), *argv],
                          capture_output=True, text=True, timeout=300)


class ModelParserTests(unittest.TestCase):
    """The committed diagram's parsed model must equal graph.py's graph
    contract on today's tree — the agreement every drift report measures
    against."""

    @classmethod
    def setUpClass(cls):
        cls.graph = drift_check.load_graph_contract()
        cls.names, cls.solid, cls.dotted = drift_check.parse_model(
            MODEL.read_text(encoding="utf-8"))

    def test_node_set_equals_graph_contract(self):
        self.assertEqual(set(self.names.values()), set(self.graph.NODES))

    def test_solid_edges_equal_data_edges(self):
        self.assertEqual(self.solid, {tuple(e) for e in self.graph.DATA_EDGES})

    def test_dotted_edges_cover_conditionals_and_loops_exactly(self):
        conditional = {tuple(e) for e in self.graph.CONDITIONAL_EDGES}
        loops = {(e[0], e[1]) for e in self.graph.LOOP_EDGES}
        for a, b in conditional:
            self.assertIn((a, b), self.dotted, f"conditional {a}-.->{b}")
        for a, b in loops:
            self.assertTrue(
                (a, b) in self.dotted or (b, a) in self.dotted,
                f"loop {a}<->{b}")
        for a, b in self.dotted:
            self.assertTrue(
                (a, b) in conditional or any({a, b} == {x, y} for x, y in loops),
                f"unaccounted dotted edge {a}-.->{b}")

    def test_diagram_problems_empty_on_the_committed_tree(self):
        self.assertEqual(drift_check.diagram_problems(self.graph), [])


class DriftTests(unittest.TestCase):
    """TC-style per-surface proof on repo copies: mutate -> nonzero with
    the canonical generator named -> regenerate/restore -> green."""

    def clean_copy(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="drift-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        repo = tmp / "repo"
        shutil.copytree(REPO_ROOT, repo, ignore=shutil.ignore_patterns(
            ".git", ".DS_Store", "__pycache__"))
        # the live tree may legitimately carry in-flight drift from other
        # work; a copy made clean here isolates this suite from it
        r = run_py(repo / "tools" / "plugin-manifest.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = run_py(repo / "tools" / "workflow-defs.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return repo

    def run_drift_check(self, repo: Path) -> subprocess.CompletedProcess:
        return run_py(repo / "tools" / "drift-check.py")

    def test_clean_copy_passes_with_all_four_sections(self):
        r = self.run_drift_check(self.clean_copy())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("drift check: OK", r.stdout)
        for section in ("== workflows", "== manifests", "== diagrams",
                        "== examples"):
            self.assertIn(section, r.stdout)

    def test_workflow_drift_fails_and_regeneration_repairs(self):
        repo = self.clean_copy()
        victim = repo / "skills" / "spec-to-prod" / "workflows" / "spec-run.js"
        victim.write_text(victim.read_text() + "\n// hand edit\n")
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("workflows", r.stdout)
        self.assertIn("tools/workflow-defs.py", r.stdout)
        r = run_py(repo / "tools" / "workflow-defs.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def test_manifest_drift_fails_and_regeneration_repairs(self):
        repo = self.clean_copy()
        victim = repo / ".claude-plugin" / "marketplace.json"
        victim.write_text(victim.read_text().replace(
            '"spec-dev-kit"', '"hand-edited-catalog"'))
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("manifests", r.stdout)
        self.assertIn("tools/plugin-manifest.py", r.stdout)
        r = run_py(repo / "tools" / "plugin-manifest.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def test_model_drift_fails_and_restoration_repairs(self):
        repo = self.clean_copy()
        victim = repo / "skills" / "spec-to-prod" / "diagrams" / "spec-to-prod-workflow.mmd"
        original = victim.read_text()
        victim.write_text(original.replace("tick-commit<br/>", "commit-tick<br/>"))
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("diagrams", r.stdout)
        self.assertIn("scripts/graph.py", r.stdout)
        victim.write_text(original)
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def test_stale_render_fails_and_restoration_repairs(self):
        repo = self.clean_copy()
        victim = repo / "skills" / "spec-to-prod" / "diagrams" / "spec-to-prod-workflow-overview.html"
        original = victim.read_text()
        victim.unlink()
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("appears in no HTML render", r.stdout)
        victim.write_text(original)
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def test_example_drift_fails_and_restoration_repairs(self):
        repo = self.clean_copy()
        victim = repo / "skills" / "spec-to-prod" / "examples" / "mini-spec" / "specs" / "mini-spec" / "plan.md"
        original = victim.read_text()
        victim.write_text("")
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("examples", r.stdout)
        self.assertIn("scripts/check.py", r.stdout)
        victim.write_text(original)
        self.assertEqual(self.run_drift_check(repo).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
