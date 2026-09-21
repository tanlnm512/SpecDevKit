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
import hashlib
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


def scratch_skill(root: Path, name: str, roles: list) -> Path:
    """A synthetic skill whose role set changes between test phases."""
    agents = root / name / "agents"
    if agents.is_dir():
        for f in agents.glob("*.md"):
            f.unlink()
    else:
        agents.mkdir(parents=True)
    for r in roles:
        (agents / f"{r}.md").write_text(
            f"---\nname: {r}\ndescription: does a thing\n"
            "model: inherit\ntools: Read, Grep\n---\nbody\n")
    return root / name


def run_gen(skill: Path, out: Path) -> str:
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        omp_defs.main(["--skill-dir", str(skill), "--out", str(out)])
    return buf.getvalue()


def run_gen_rc(skill: Path, out: Path):
    """(exit code, stdout) — for behavior that refuses instead of raising."""
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = omp_defs.main(["--skill-dir", str(skill), "--out", str(out)])
    return rc, buf.getvalue()


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


class ManifestProvenanceTests(unittest.TestCase):
    """Stale-cleanup ownership proof: deletion requires the skill's own
    manifest naming the file with a matching content hash. A foreign
    file in a shared --out dir — even one named like this skill's roles
    — is never touched (the old basename-prefix heuristic is gone, and
    with it the ability to delete a hand-made `spec-foo.md`)."""

    def test_first_run_removes_nothing_and_establishes_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            skill = scratch_skill(Path(td), "skill-a", ["alpha", "beta"])
            output = run_gen(skill, out)
            self.assertIn("stale-check skipped", output)
            self.assertTrue(
                omp_defs.manifest_path_for(out, skill).is_file())
            manifest = omp_defs.manifest_path_for(out, skill).read_text()
            self.assertIn(" alpha.md", manifest)
            self.assertIn(" beta.md", manifest)

    def test_role_dropped_from_source_is_removed(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            skill = scratch_skill(Path(td), "skill-a", ["alpha", "beta"])
            run_gen(skill, out)
            scratch_skill(Path(td), "skill-a", ["alpha"])  # beta is gone
            output = run_gen(skill, out)
            self.assertIn("omp def removed beta.md", output)
            self.assertFalse((out / "beta.md").exists())
            self.assertTrue((out / "alpha.md").exists())

    def test_foreign_same_prefix_file_never_touched(self):
        """A hand-made file sharing the skill's role prefix is foreign —
        the manifest is the only ownership record that counts."""
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            skill = scratch_skill(Path(td), "skill-a", ["alpha", "beta"])
            run_gen(skill, out)
            foreign = out / "beta-clone.md"
            foreign.write_text("---\nname: beta-clone\n---\nhand-made\n")
            output = run_gen(skill, out)
            self.assertTrue(foreign.exists())
            self.assertNotIn("removed beta-clone.md", output)

    def test_edited_generated_file_is_kept_with_loud_note(self):
        """A generated file edited since generation is no longer provably
        ours — kept, loudly, not silently deleted."""
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            skill = scratch_skill(Path(td), "skill-a", ["alpha", "beta"])
            run_gen(skill, out)
            (out / "beta.md").write_text(
                "---\nname: beta\n---\nhand-edited body\n")
            scratch_skill(Path(td), "skill-a", ["alpha"])
            output = run_gen(skill, out)
            self.assertIn("omp def kept beta.md", output)
            self.assertIn("changed since generation", output)
            self.assertTrue((out / "beta.md").exists())

    def test_manifest_is_per_skill_in_shared_out(self):
        """Two skills sharing one --out dir each track their own files;
        one skill's stale cleanup never deletes the other's roles."""
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            a = scratch_skill(Path(td), "skill-a", ["alpha", "beta"])
            b = scratch_skill(Path(td), "skill-b", ["gamma"])
            run_gen(a, out)
            run_gen(b, out)
            scratch_skill(Path(td), "skill-a", ["alpha"])
            run_gen(a, out)
            self.assertFalse((out / "beta.md").exists())
            self.assertTrue((out / "gamma.md").exists())
            self.assertTrue(
                omp_defs.manifest_path_for(out, b).is_file())


class WriteGateTests(unittest.TestCase):
    """FR-003 on the omp deploy root: the per-skill manifest is the
    provenance ledger, so a role destination is replaced only when its
    current hash is recorded there — a foreign file at a role name,
    byte-different or byte-identical, with or without a manifest yet, is
    refused before any write, never clobbered or silently adopted."""

    def test_unledgered_role_named_file_is_refused_and_kept(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            out.mkdir()
            intruder = out / "alpha.md"
            intruder.write_text("---\nname: alpha\n---\nhand-made\n")
            skill = scratch_skill(Path(td), "skill-a", ["alpha", "beta"])
            rc, output = run_gen_rc(skill, out)
            self.assertEqual(rc, 1)
            self.assertIn("REFUSE", output)
            self.assertIn("hand-made", intruder.read_text())
            # planned before any write: the refusal leaves the whole
            # destination untouched and establishes no manifest
            self.assertFalse((out / "beta.md").exists())
            self.assertFalse(
                omp_defs.manifest_path_for(out, skill).exists())

    def test_drifted_generated_file_is_refused_and_manifest_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            skill = scratch_skill(Path(td), "skill-a", ["alpha", "beta"])
            run_gen(skill, out)
            manifest_before = (
                omp_defs.manifest_path_for(out, skill).read_bytes())
            dest = out / "alpha.md"
            dest.write_text(dest.read_text() + "\nhand-edited\n")
            rc, output = run_gen_rc(skill, out)
            self.assertEqual(rc, 1)
            self.assertIn("REFUSE", output)
            self.assertIn("hand-edited", dest.read_text())
            self.assertEqual(
                omp_defs.manifest_path_for(out, skill).read_bytes(),
                manifest_before)

    def test_identical_unledgered_file_is_refused_not_adopted(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "first"
            skill = scratch_skill(Path(td), "skill-a", ["alpha"])
            run_gen(skill, out)
            fresh = Path(td) / "out"
            fresh.mkdir()
            (fresh / "alpha.md").write_bytes((out / "alpha.md").read_bytes())
            rc, output = run_gen_rc(skill, fresh)
            self.assertEqual(rc, 1)
            self.assertIn("REFUSE", output)
            self.assertFalse(
                omp_defs.manifest_path_for(fresh, skill).exists())

    def test_owned_update_is_applied_and_remanifested(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            skill = scratch_skill(Path(td), "skill-a", ["alpha"])
            run_gen(skill, out)
            src = skill / "agents" / "alpha.md"
            src.write_text(
                "---\nname: alpha\ndescription: does a thing\n"
                "model: inherit\ntools: Read, Grep\n---\nbody v2\n")
            rc, output = run_gen_rc(skill, out)
            self.assertEqual(rc, 0, output)
            self.assertIn("body v2", (out / "alpha.md").read_text())
            manifest = omp_defs.manifest_path_for(out, skill).read_text()
            want = hashlib.sha256((out / "alpha.md").read_bytes()).hexdigest()
            self.assertEqual(manifest, f"{want} alpha.md\n")


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

    def test_foreign_stale_file_is_never_removed_on_first_run(self):
        """First run into a root with no manifest: nothing is deletable,
        so even a role-named file this tool never made survives."""
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            stale = out / "spec-nonexistent-role.md"
            stale.write_text("---\nname: spec-nonexistent-role\n---\nbody\n")
            output = run_gen(SPEC_TO_CODE, out)
            self.assertTrue(stale.exists())
            self.assertIn("stale-check skipped", output)

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
