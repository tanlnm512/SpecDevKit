"""Tests for tools/agent-defs.py — the opencode/droid/agy def generator.
Run via tools/tests/run.sh (needs Python >= 3.10).

Same philosophy as test_omp_defs.py: the generator derives everything
by parsing each source role's own Claude-style frontmatter — no
per-role table to test in isolation — so these exercise it against
spec-to-prod's real shipped agents/*.md, plus a synthetic scratch skill
for staging and no-deletion behavior sync.sh can't safely practice on
the live shared roots.
"""
import hashlib
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "spec-to-prod"

_spec = importlib.util.spec_from_file_location(
    "agent_defs", REPO_ROOT / "tools" / "agent-defs.py")
agent_defs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_defs)

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
DROID_NAME = re.compile(r"^[a-z0-9-_]+$")


def run(target, skill_dir, out):
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        agent_defs.main(["--target", target, "--skill-dir", str(skill_dir),
                         "--out", str(out)])
    return Path(out)


def run_rc(target, skill_dir, out):
    """(exit code, stdout) — for behavior that refuses instead of raising."""
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = agent_defs.main(["--target", target, "--skill-dir", str(skill_dir),
                              "--out", str(out)])
    return rc, buf.getvalue()


def source_roles():
    return sorted(p for p in (SKILL / "agents").glob("*.md")
                  if not p.name.startswith("_"))


LEDGER = ".spec-dev-kit-deployed"


def make_skill(tmp, names):
    agents = tmp / "sk" / "agents"
    agents.mkdir(parents=True)
    for n in names:
        (agents / f"{n}.md").write_text(
            f"---\nname: {n}\ndescription: role {n}\ntools: Read, Bash\n---\n\nbody {n}\n")
    return tmp / "sk"


def ledger_entries(out: Path) -> dict:
    lines = (out / LEDGER).read_text().splitlines()
    return {name: sha for sha, name in (l.split(" ", 1) for l in lines)}


class OpencodeDefsTests(unittest.TestCase):
    def gen(self, tmp):
        return run("opencode", SKILL, tmp / "oc")

    def test_permissions_follow_source_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.gen(Path(tmp))
            for src in source_roles():
                name, _, fields, _ = agent_defs.parse(src)
                text = (out / f"{name}.md").read_text()
                fm = FM.match(text).group(1)
                self.assertIn("mode: subagent", fm)
                have = set(agent_defs.claude_names(fields.get("tools", "")))
                for key, srcs in agent_defs.OPENCODE_PERMS.items():
                    want = "allow" if have & set(srcs) else "deny"
                    self.assertIn(f"  {key}: {want}", fm,
                                  f"{name}: {key} should be {want}")
                self.assertIn("  task: deny", fm)  # no agent spawns another

    def test_readonly_role_denies_edit_and_bash(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.gen(Path(tmp))
            reviewer = (out / "spec-reviewer.md").read_text()
            fm = FM.match(reviewer).group(1)
            self.assertIn("  edit: deny", fm)
            self.assertIn("  bash: deny", fm)
            self.assertIn("  read: allow", fm)

    def test_body_is_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.gen(Path(tmp))
            for src in source_roles():
                name, _, _, body = agent_defs.parse(src)
                self.assertTrue(
                    (out / f"{name}.md").read_text().endswith(body))



    def test_researcher_gets_web_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.gen(Path(tmp))
            researcher = (out / "spec-researcher.md").read_text()
            fm = FM.match(researcher).group(1)
            self.assertIn("  websearch: allow", fm)
            self.assertIn("  webfetch: allow", fm)
            self.assertIn("  edit: allow", fm)  # writes research.md


class DroidDefsTests(unittest.TestCase):
    def gen(self, tmp):
        return run("droid", SKILL, tmp / "dr")

    def test_readonly_set_collapses_to_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.gen(Path(tmp))
            reviewer = (out / "spec-reviewer.md").read_text()
            self.assertIn("tools: read-only", reviewer)

    def test_tool_ids_map_to_factory_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.gen(Path(tmp))
            imp = (out / "spec-implementer.md").read_text()
            for tid in ("Read", "Execute", "Create", "Edit"):
                self.assertIn(f'"{tid}"', imp)
            self.assertNotIn('"Bash"', imp)
            self.assertNotIn('"Write"', imp)

    def test_names_valid_and_model_inherits(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.gen(Path(tmp))
            for p in sorted(out.glob("spec-*.md")):
                fm = FM.match(p.read_text()).group(1)
                name = next(l.split(":", 1)[1].strip()
                            for l in fm.splitlines() if l.startswith("name:"))
                self.assertRegex(name, DROID_NAME)
                self.assertIn("model: inherit", fm)


class AgyDefsTests(unittest.TestCase):
    def test_personas_are_byte_verbatim_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = run("agy", SKILL, Path(tmp) / "ag")
            for src in source_roles():
                self.assertEqual((out / src.name).read_bytes(),
                                 src.read_bytes())

    def test_agy_writes_no_ledger(self):
        # agy output is committed repo content — git is its provenance,
        # so no destination ledger file is created beside the personas.
        with tempfile.TemporaryDirectory() as tmp:
            out = run("agy", SKILL, Path(tmp) / "ag")
            self.assertFalse((out / LEDGER).exists())


class StagingAndNoDeletionTests(unittest.TestCase):
    def test_regeneration_deletes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["spec-aaa", "spec-bbb"])
            out = run("droid", skill, tmp / "out")
            (out / "spec-stale.md").write_text("stale\n")  # same prefix, never generated
            (out / "other-skill.md").write_text("foreign\n")
            (skill / "agents" / "spec-bbb.md").unlink()  # role dropped upstream
            stale_bbb = (out / "spec-bbb.md").read_bytes()  # this tool's own old output
            run("droid", skill, tmp / "out")
            self.assertEqual((out / "spec-stale.md").read_text(), "stale\n")
            self.assertEqual((out / "other-skill.md").read_text(), "foreign\n")
            self.assertEqual((out / "spec-bbb.md").read_bytes(), stale_bbb)
            self.assertIn("name: spec-aaa", (out / "spec-aaa.md").read_text())

    def test_bad_role_aborts_before_first_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["spec-good"])
            out = run("opencode", skill, tmp / "out")
            (out / "foreign.md").write_text("foreign\n")
            before = {p.name: p.read_bytes() for p in out.iterdir()}
            # sorted after the good role: the abort must not depend on
            # the failure coming first
            (skill / "agents" / "spec-zzz.md").write_text(
                "---\nname: Bad_Name\ndescription: x\ntools: Read\n---\n\nbody\n")
            with self.assertRaises(SystemExit):
                run("droid", skill, tmp / "out")
            after = {p.name: p.read_bytes() for p in out.iterdir()}
            self.assertEqual(after, before)

    def test_apply_leaves_no_temp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["spec-aaa", "spec-bbb"])
            out = run("droid", skill, tmp / "out")
            self.assertEqual(sorted(p.name for p in out.iterdir()),
                             [LEDGER, "spec-aaa.md", "spec-bbb.md"])

    def test_rerun_output_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["spec-aaa", "spec-bbb"])
            out = run("opencode", skill, tmp / "out")
            first = {p.name: p.read_bytes() for p in out.iterdir()}
            run("opencode", skill, tmp / "out")
            self.assertEqual(
                {p.name: p.read_bytes() for p in out.iterdir()}, first)

    def test_no_shared_prefix_never_removes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["aaa", "abb"])  # no 'x-' prefix
            out = run("droid", skill, tmp / "out")
            (out / "aaa-old.md").write_text("stale?\n")
            run("droid", skill, tmp / "out")
            self.assertTrue((out / "aaa-old.md").exists())

    def test_droid_rejects_invalid_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["Bad_Name"])
            with self.assertRaises(SystemExit):
                run("droid", skill, tmp / "out")


class OwnershipLedgerTests(unittest.TestCase):
    """Deployment ownership across the opencode/droid roots (FR-003): a
    destination belongs to this generator only when its current hash
    sits in the destination's .spec-dev-kit-deployed ledger — a foreign
    file at a generated name, byte-different or byte-identical, is
    refused with nothing written, never clobbered or adopted."""

    def test_ledger_records_deployed_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["spec-aaa", "spec-bbb"])
            out = run("opencode", skill, tmp / "out")
            entries = ledger_entries(out)
            self.assertEqual(sorted(entries), ["spec-aaa.md", "spec-bbb.md"])
            for name, sha in entries.items():
                self.assertEqual(
                    hashlib.sha256((out / name).read_bytes()).hexdigest(), sha)

    def test_unledgered_same_path_file_is_refused_and_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["spec-aaa", "spec-bbb"])
            out = tmp / "out"
            out.mkdir()
            intruder = out / "spec-aaa.md"
            intruder.write_text("---\nname: spec-aaa\n---\nhand-made\n")
            rc, output = run_rc("opencode", skill, out)
            self.assertEqual(rc, 1)
            self.assertIn("REFUSE", output)
            self.assertIn("hand-made", intruder.read_text())  # never clobbered
            # planned before any write: the refusal leaves the whole
            # destination untouched, and no ledger claims anything
            self.assertFalse((out / "spec-bbb.md").exists())
            self.assertFalse((out / LEDGER).exists())

    def test_drifted_deployed_file_is_refused_and_ledger_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["spec-aaa", "spec-bbb"])
            out = run("droid", skill, tmp / "out")
            ledger_before = (out / LEDGER).read_bytes()
            dest = out / "spec-aaa.md"
            dest.write_text(dest.read_text() + "\nhand-edited\n")
            rc, output = run_rc("droid", skill, out)
            self.assertEqual(rc, 1)
            self.assertIn("REFUSE", output)
            self.assertIn("hand-edited", dest.read_text())
            self.assertEqual((out / LEDGER).read_bytes(), ledger_before)

    def test_owned_update_is_applied_and_reledgered(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["spec-aaa"])
            out = run("droid", skill, tmp / "out")
            src = skill / "agents" / "spec-aaa.md"
            src.write_text(
                "---\nname: spec-aaa\ndescription: role spec-aaa\n"
                "tools: Read, Bash\n---\n\nbody v2\n")
            rc, output = run_rc("droid", skill, out)
            self.assertEqual(rc, 0, output)
            self.assertIn("body v2", (out / "spec-aaa.md").read_text())
            self.assertEqual(
                ledger_entries(out)["spec-aaa.md"],
                hashlib.sha256((out / "spec-aaa.md").read_bytes()).hexdigest())

    def test_identical_unledgered_file_is_refused_not_adopted(self):
        # content equality is not ownership: a byte-identical file with
        # no ledger proof stays foreign, and the run writes nothing
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = make_skill(tmp, ["spec-aaa"])
            staged = run("opencode", skill, tmp / "first")
            out = tmp / "out"
            out.mkdir()
            (out / "spec-aaa.md").write_bytes(
                (staged / "spec-aaa.md").read_bytes())
            rc, output = run_rc("opencode", skill, out)
            self.assertEqual(rc, 1)
            self.assertIn("REFUSE", output)
            self.assertFalse((out / LEDGER).exists())

    def test_shared_root_ledger_merges_other_skills_deployments(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            a = make_skill(tmp, ["spec-aaa"])
            agents_b = tmp / "sk2" / "agents"
            agents_b.mkdir(parents=True)
            (agents_b / "other-role.md").write_text(
                "---\nname: other-role\ndescription: role other\n"
                "tools: Read\n---\n\nbody other\n")
            b = tmp / "sk2"
            out = run("droid", a, tmp / "out")
            rc, output = run_rc("droid", b, out)
            self.assertEqual(rc, 0, output)
            self.assertIn("name: spec-aaa", (out / "spec-aaa.md").read_text())
            self.assertTrue((out / "other-role.md").is_file())
            self.assertEqual(sorted(ledger_entries(out)),
                             ["other-role.md", "spec-aaa.md"])
            # regenerating the first skill never prunes the second's entry
            run("droid", a, out)
            self.assertEqual(sorted(ledger_entries(out)),
                             ["other-role.md", "spec-aaa.md"])


if __name__ == "__main__":
    unittest.main()
