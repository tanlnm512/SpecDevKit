"""Tests for tools/omp-defs.py — the shared, skill-agnostic omp-frontmatter
generator. Run via tools/tests/run.sh (needs Python >= 3.10).

omp-defs.py derives everything (tools/model/thinking-level) by parsing
each source role's own Claude-style frontmatter directly — there is no
per-role table in the tool to test in isolation, so these tests exercise
it against spec-to-prod's real shipped agents/*.md, the same files
tools/sync.sh feeds it. A second skill added to this repo is covered by
the same code path with no new test needed here — see
test_second_skill_needs_no_new_code, which proves that on a synthetic
skill directory instead.
"""
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_TO_CODE = REPO_ROOT / "skills" / "spec-to-prod"

_spec = importlib.util.spec_from_file_location(
    "omp_defs", REPO_ROOT / "tools" / "omp-defs.py")
omp_defs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(omp_defs)

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)

# Every shipped role's Claude-side model/tools/effort, read once from the
# real frontmatter for the tiering assertions below — the source of
# truth is the shipped file, never a hand-duplicated table.
_ROLE_FIELDS = {}
for _f in sorted((SPEC_TO_CODE / "agents").glob("*.md")):
    if _f.name.startswith("_"):
        continue
    _name, _desc, _fields, _body = omp_defs.parse(_f)
    _ROLE_FIELDS[_name] = _fields


def fm_lines(name: str) -> list:
    """A role's rendered frontmatter lines, via the real parse()+render()
    on its actual shipped source file — never hand-built."""
    source = SPEC_TO_CODE / "agents" / f"{name}.md"
    n, d, fields, body = omp_defs.parse(source)
    text = omp_defs.render(n, d, fields, body)
    return FRONTMATTER.match(text).group(1).splitlines()


class ModelTierTests(unittest.TestCase):
    def test_tiered_set_matches_decisions_012_and_016(self):
        """decisions/012 + 016: a real `model:` value other than
        `inherit` in the Claude-side frontmatter IS the tiering signal
        — read from the shipped files, not a hand-maintained name list."""
        tiered = {n for n, f in _ROLE_FIELDS.items()
                  if f.get("model") and f["model"] != "inherit"}
        self.assertEqual(tiered, {"spec-surveyor", "spec-researcher",
                                  "spec-task-breaker",
                                  "spec-implementer"})

    def test_reviewer_never_tiered(self):
        """The one safety-critical role left above the cheap tier:
        reviewer's adversarial judgment is its own deliverable with no
        mechanical backstop — it must not run cheaper without an
        explicit, reviewed decision (decisions/012; 016 lifted the
        implementer half of this lock)."""
        self.assertEqual(_ROLE_FIELDS["spec-reviewer"]["model"], "inherit")

    def test_model_alias_is_quoted(self):
        """`@`-prefixed values are not valid unquoted YAML plain scalars
        (`@` is a reserved indicator) — an unquoted line is a parse
        hazard, not just a style nit."""
        model_line = next(l for l in fm_lines("spec-surveyor")
                           if l.startswith("model:"))
        self.assertEqual(model_line, 'model: "@smol"')

    def test_non_tiered_roles_have_no_model_line(self):
        for name in ("spec-reviewer", "spec-planner", "spec-tech",
                     "spec-qa"):
            self.assertFalse(
                any(l.startswith("model:") for l in fm_lines(name)), name)

    def test_thinking_level_unaffected_by_model_tier(self):
        """spec-surveyor and spec-task-breaker get both (cheap model +
        low effort); spec-researcher gets model only (its Claude-side
        def has no `effort: low`); spec-implementer gets the model
        override with no thinking-level cap (D-016 tiers the model, not
        the reasoning-depth setting it never had)."""
        self.assertIn("thinking-level: low", fm_lines("spec-surveyor"))
        self.assertFalse(any(l.startswith("thinking-level:")
                              for l in fm_lines("spec-researcher")))
        self.assertIn("thinking-level: low", fm_lines("spec-task-breaker"))
        self.assertTrue(any(l.startswith("model:")
                            for l in fm_lines("spec-task-breaker")))
        self.assertTrue(any(l.startswith("model:")
                            for l in fm_lines("spec-implementer")))
        self.assertFalse(any(l.startswith("thinking-level:")
                              for l in fm_lines("spec-implementer")))



class ToolMappingTests(unittest.TestCase):
    """omp_tools(): the Claude tool-name -> omp tool-name derivation the
    module docstring describes, exercised directly plus against every
    real shipped role as a parity guard."""

    def test_maps_and_lowercases_known_tools(self):
        self.assertEqual(
            omp_defs.omp_tools("Read, Grep, Glob, Bash, Write, Edit"),
            "read, grep, glob, bash, write, edit")

    def test_websearch_renamed_others_dropped(self):
        self.assertEqual(
            omp_defs.omp_tools("Read, WebSearch, WebFetch, Skill, NotebookEdit"),
            "read, web_search")

    def test_every_shipped_role_tools_line_matches_expected(self):
        expected = {
            "spec-surveyor": "read, grep, glob, bash, write, edit",
            "spec-researcher": "read, grep, glob, bash, write, edit, web_search",
            "spec-planner": "read, grep, glob, bash, write, edit",
            "spec-tech": "read, grep, glob, bash, write, edit",
            "spec-qa": "read, grep, glob, bash, write, edit",
            "spec-task-breaker": "read, grep, glob, bash, write, edit",
            "spec-implementer": "read, grep, glob, bash, write, edit",
            "spec-reviewer": "read, grep, glob",
        }
        for name, want in expected.items():
            tools_line = next(l for l in fm_lines(name) if l.startswith("tools:"))
            self.assertEqual(tools_line, f"tools: {want}", name)


class RolePrefixTests(unittest.TestCase):
    """Stale-cleanup scoping — a shared --out dir (e.g.
    ~/.omp/agent/agents) can hold other skills' own generated files;
    cleanup must never guess ownership of a file this run didn't
    produce."""

    def test_spec_to_code_roles_share_the_spec_prefix(self):
        names = [f"{n}.md" for n in _ROLE_FIELDS]
        self.assertEqual(omp_defs.role_prefix(names), "spec-")

    def test_no_shared_separator_prefix_returns_empty(self):
        self.assertEqual(omp_defs.role_prefix(["alpha.md", "beta.md"]), "")

    def test_empty_input_returns_empty(self):
        self.assertEqual(omp_defs.role_prefix([]), "")


class GenerationEndToEndTests(unittest.TestCase):
    """main()'s file-generation + scoped stale-removal loop."""

    def test_generates_one_file_per_source_role(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            omp_defs.main(["--skill-dir", str(SPEC_TO_CODE), "--out", str(out)])
            produced = sorted(p.name for p in out.glob("*.md"))
            source = sorted(p.name for p in (SPEC_TO_CODE / "agents").glob("*.md")
                             if not p.name.startswith("_"))
            self.assertEqual(produced, source)

    def test_stale_output_role_is_removed(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            stale = out / "spec-nonexistent-role.md"
            stale.write_text("---\nname: spec-nonexistent-role\n---\nbody\n")
            omp_defs.main(["--skill-dir", str(SPEC_TO_CODE), "--out", str(out)])
            self.assertFalse(stale.exists())

    def test_stale_removal_never_touches_another_skills_files(self):
        """A shared --out dir may already hold a second skill's own
        generated roles — regenerating spec-to-prod's must not delete
        them, since their name shares no prefix with spec-to-prod's."""
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            other = out / "foo-flow-planner.md"
            other.write_text("---\nname: foo-flow-planner\n---\nbody\n")
            omp_defs.main(["--skill-dir", str(SPEC_TO_CODE), "--out", str(out)])
            self.assertTrue(other.exists())

    def test_second_skill_needs_no_new_code(self):
        """A skill whose agents/ dir shares no naming convention with
        spec-to-prod still generates correctly through the same parse()
        / render() path — the tool has no spec-to-prod-specific branch."""
        with tempfile.TemporaryDirectory() as td:
            skill = Path(td) / "other-skill"
            (skill / "agents").mkdir(parents=True)
            (skill / "agents" / "other-role.md").write_text(
                "---\nname: other-role\ndescription: does a thing\n"
                "model: inherit\ntools: Read, Grep\n---\nbody\n")
            out = Path(td) / "out"
            omp_defs.main(["--skill-dir", str(skill), "--out", str(out)])
            rendered = (out / "other-role.md").read_text()
            self.assertIn("tools: read, grep", rendered)
            self.assertNotIn("model:", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
