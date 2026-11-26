"""Tests for tools/drift-check.py — release validation of the generated
surfaces (manifests, diagrams, examples) against their canonical sources.

Per surface, the same contract: a clean tree passes; a mutated generated
output fails nonzero with the canonical generator named; regeneration
(or restoration, where no generator exists) passes again. Mutation tests
run against a full repo copy — never the live tree.

The descriptions set guards a budget, not a source: over budget warns,
over the loader cap fails, the live tree counts as tools/sync.sh counts
it, and every rewritten description keeps its routing cues pinned.
"""
import contextlib
import importlib.util
import io
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIFT_CHECK = REPO_ROOT / "tools" / "drift-check.py"
MODEL = REPO_ROOT / "skills" / "spec-design" / "diagrams" / "spec-workflow.mmd"
SYNC_COUNT = re.compile(
    r"python3 -c '([^']+)' \"\$skill_dir/SKILL\.md\"")

# Per skill whose description was trimmed: the phrases a user says that
# route to it, and each "not for" redirect — a later trim may not drop one.
DESCRIPTION_CUES = {
    "spec-build": (
        ('"build/execute an approved spec"', '"resume the spec"',
         "names a T### task", "a spec's proofs, scope diff, or delivery"),
        ("general code review (spec-review)",)),
    "spec-discover": (
        ('"brainstorm"',
         '"I have an idea and I\'m not sure whether / which version to build"',
         '"help me explore / validate / pressure-test this idea or feature"',
         '"help me decide what to build"', '"before we spec this"',
         "any ask where the direction is undecided"),
        ("a settled direction that needs its requirements pinned down",
         '("clarify this idea", "/spec-define <name>" — that is spec-define)')),
    "spec-release": (
        ('"cut a release"', '"bump the version"',
         '"write the release notes / changelog"', '"tag v1.4.0"',
         '"publish the release"', "for merged work"),
        ("opening, pushing, or fixing a pull request (spec-ship)",
         "building or delivering a spec (spec-build)",
         "deploying — this skill never deploys")),
    "spec-ship": (
        ("delivery commit is on record", "needs to go up",
         '"open the PR for this spec"', '"push this spec"',
         "its PR needs attention", '"CI is red on the PR"',
         '"answer the review comments"', '"it merged, what now"'),
        ("building or committing (spec-build)", "reviewing code (spec-review)",
         "tagging a release (spec-release)")),
}

_spec = importlib.util.spec_from_file_location("drift_check", DRIFT_CHECK)
drift_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drift_check)


def run_py(script: Path, *argv) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", str(script), *argv],
                          capture_output=True, text=True, timeout=300)


def sync_count(skill_md: Path) -> int:
    """tools/sync.sh's own measure of one description: the inline snippet
    its install loop runs on each SKILL.md, executed as written."""
    sync_sh = (REPO_ROOT / "tools" / "sync.sh").read_text(encoding="utf-8")
    snippet = SYNC_COUNT.search(sync_sh)
    if not snippet:
        raise AssertionError("tools/sync.sh no longer counts a description "
                             "with an inline python -c snippet")
    r = subprocess.run(["python3", "-c", snippet.group(1), str(skill_md)],
                       capture_output=True, text=True, timeout=60)
    return int(r.stdout)


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


class DriftTests(unittest.TestCase):
    """Per-surface proof on repo copies: mutate -> nonzero with
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
        return repo

    def run_drift_check(self, repo: Path) -> subprocess.CompletedProcess:
        return run_py(repo / "tools" / "drift-check.py")

    def test_clean_copy_passes_with_all_sections(self):
        r = self.run_drift_check(self.clean_copy())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("drift check: OK", r.stdout)
        for section in ("== contract", "== manifests", "== kit-rules",
                        "== parity", "== diagrams", "== examples",
                        "== personas", "== evals", "== descriptions"):
            self.assertIn(section, r.stdout)

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
        victim = repo / "skills" / "spec-design" / "diagrams" / "spec-workflow.mmd"
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
        victim = repo / "skills" / "spec-design" / "diagrams" / "spec-workflow-overview.html"
        original = victim.read_text()
        victim.unlink()
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no HTML render of the model exists", r.stdout)
        victim.write_text(original)
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def test_example_drift_fails_and_restoration_repairs(self):
        repo = self.clean_copy()
        victim = repo / "skills" / "spec-design" / "examples" / "mini-spec" / "specs" / "mini-spec" / "plan.md"
        original = victim.read_text()
        victim.write_text("")
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("examples", r.stdout)
        self.assertIn("scripts/check.py", r.stdout)
        victim.write_text(original)
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def test_persona_drift_fails_and_restoration_repairs(self):
        repo = self.clean_copy()
        victim = repo / "agents" / "developer.md"
        original = victim.read_text()
        victim.write_text(original.replace("developer", "HAND-EDIT", 1))
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("personas", r.stdout)
        self.assertIn("tools/sync.sh", r.stdout)
        victim.write_text(original)
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def test_stale_persona_fails_and_deletion_repairs(self):
        repo = self.clean_copy()
        victim = repo / "agents" / "retired-persona.md"
        victim.write_text("---\ndescription: gone\n---\n")
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("personas", r.stdout)
        self.assertIn("retired-persona.md", r.stdout)
        victim.unlink()
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def test_contract_drift_fails_and_regeneration_repairs(self):
        # scripts/contract.py is the node table's single source; graph.py
        # imports it and SKILL.md's block is generated from it
        repo = self.clean_copy()
        victim = repo / "skills" / "spec-design" / "SKILL.md"
        victim.write_text(
            victim.read_text().replace("| `spec` | entry |",
                                       "| `spec` | HAND-EDIT |", 1))
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("contract", r.stdout)
        mod = repo / "skills" / "spec-design" / "scripts" / "contract.py"
        gen = run_py(mod, "--render", "skill-table")
        self.assertEqual(gen.returncode, 0, gen.stdout + gen.stderr)
        text = victim.read_text()
        spec = importlib.util.spec_from_file_location("c", mod)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        start, end = text.find(m.BEGIN), text.find(m.END)
        victim.write_text(
            text[:start] + gen.stdout.strip("\n")
            + text[end + len(m.END):])
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def test_orphan_eval_result_fails_and_deletion_repairs(self):
        # a recorded result must cite a real case — an orphan result (as
        # after a case is renamed or its file hand-planted) is eval drift
        repo = self.clean_copy()
        victim = repo / "skills" / "spec-ship" / "evals" / "results"
        victim.mkdir(parents=True)
        (victim / "2026-11-17-s9.md").write_text(
            "# Eval result — spec-ship/s9\n\n"
            "- selector: spec-ship/s9\n- date: 2026-11-17\n"
            "- kind: conversational\n- source: skills/spec-ship/evals/cases.md\n"
            "- repo: scratch\n- surface: 0123456789abcdef\n"
            "- recorded via: validate\n\n## Verdicts\n\n"
            "- C1: pass — seen\n\n## Findings\n\nNone — every criterion passed.\n",
            encoding="utf-8")
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("evals", r.stdout)
        self.assertIn("spec-ship/s9", r.stdout)
        (victim / "2026-11-17-s9.md").unlink()
        self.assertEqual(self.run_drift_check(repo).returncode, 0)

    def write_description(self, repo: Path, skill: str, scalar: str) -> None:
        # `scalar` replaces the block after `description: `; one physical
        # line, so every measure of it is its length. The manifests follow,
        # so only the descriptions set can speak.
        victim = repo / "skills" / skill / "SKILL.md"
        victim.write_text(drift_check.FOLDED_DESCRIPTION.sub(
            lambda m: f"description: {scalar}\nmetadata:",
            victim.read_text(), count=1))
        r = run_py(repo / "tools" / "plugin-manifest.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_over_budget_description_warns_without_failing(self):
        repo = self.clean_copy()
        folded = ">-\n  "
        self.write_description(repo, "spec-release", folded + "x" * 600)
        r = self.run_drift_check(repo)
        self.assertIn("  OK   spec-release — 600 chars", r.stdout)
        self.write_description(repo, "spec-release", folded + "x" * 601)
        r = self.run_drift_check(repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("  WARN spec-release — 601 chars, over the 600-char "
                      "budget", r.stdout)
        self.assertIn("drift check: OK", r.stdout)

    def test_oversized_description_fails_and_restoration_repairs(self):
        repo = self.clean_copy()
        victim = repo / "skills" / "spec-ship" / "SKILL.md"
        original = victim.read_text()
        self.write_description(repo, "spec-ship", ">-\n  " + "x" * 1024)
        r = self.run_drift_check(repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.write_description(repo, "spec-ship", ">-\n  " + "x" * 1025)
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("  FAIL spec-ship — 1025 chars, over the 1024 loader "
                      "cap", r.stdout)
        self.assertIn("descriptions", r.stdout.splitlines()[-1])
        self.write_description(repo, "spec-ship", "x" * 1100)
        r = self.run_drift_check(repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("  FAIL spec-ship — no folded description: >- block "
                      "to count", r.stdout)
        victim.write_text(original)
        r = run_py(repo / "tools" / "plugin-manifest.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.run_drift_check(repo).returncode, 0)


class DescriptionTests(unittest.TestCase):
    """Read-only against the live tree: the printed counts are
    tools/sync.sh's own, and each trimmed description still carries every
    routing cue and "not for" redirect pinned above."""

    def test_live_tree_reads_ok_and_counts_as_sync_counts(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = drift_check.check_descriptions()
        lines = out.getvalue().splitlines()
        self.assertEqual(rc, 0, out.getvalue())
        skill_mds = sorted(REPO_ROOT.glob("skills/*/SKILL.md"))
        self.assertEqual(len(lines) - 1, len(skill_mds), out.getvalue())
        for line, skill_md in zip(lines[1:], skill_mds):
            name = skill_md.parent.name
            self.assertRegex(line, rf"^  (OK|WARN) +{name} — \d+ chars$")
            self.assertIn(f"— {sync_count(skill_md)} chars", line, name)

    def test_routing_cues_and_not_for_redirects_survive(self):
        for skill, (cues, redirects) in DESCRIPTION_CUES.items():
            with self.subTest(skill=skill):
                text = drift_check.folded_description(
                    REPO_ROOT / "skills" / skill / "SKILL.md")
                self.assertIsNotNone(text, "no folded description: >- block")
                desc = " ".join(text.split())
                for cue in cues:
                    self.assertIn(cue, desc, f"routing cue lost: {cue}")
                parts = re.split(r"[Nn]ot for ", desc, maxsplit=1)
                self.assertEqual(len(parts), 2, "no 'not for' boundary")
                for redirect in redirects:
                    self.assertIn(redirect, parts[1],
                                  f"'not for' redirect lost: {redirect}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
