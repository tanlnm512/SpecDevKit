"""Tests for tools/agent-defs.py — the opencode/droid/agy def generator.
Run via tools/tests/run.sh (needs Python >= 3.10).

Same philosophy as test_omp_defs.py: the generator derives everything
by parsing each source role's own Claude-style frontmatter — no
per-role table to test in isolation — so these exercise it against
spec-to-prod's real shipped agents/*.md, plus a synthetic scratch skill
for scoping and rejection behavior sync.sh can't safely practice on the
live shared roots.
"""
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


def source_roles():
    return sorted(p for p in (SKILL / "agents").glob("*.md")
                  if not p.name.startswith("_"))


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


class ScopingAndRejectionTests(unittest.TestCase):
    def make_skill(self, tmp, names):
        agents = tmp / "sk" / "agents"
        agents.mkdir(parents=True)
        for n in names:
            (agents / f"{n}.md").write_text(
                f"---\nname: {n}\ndescription: role {n}\ntools: Read, Bash\n---\n\nbody {n}\n")
        return tmp / "sk"

    def test_stale_prefixed_removed_foreign_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = self.make_skill(tmp, ["spec-aaa", "spec-bbb"])
            out = run("droid", skill, tmp / "out")
            (out / "spec-stale.md").write_text("stale\n")
            (out / "other-skill.md").write_text("foreign\n")
            (skill / "agents" / "spec-bbb.md").unlink()  # role removed upstream
            run("droid", skill, tmp / "out")
            self.assertFalse((out / "spec-stale.md").exists())
            self.assertFalse((out / "spec-bbb.md").exists())
            self.assertTrue((out / "other-skill.md").exists())
            self.assertTrue((out / "spec-aaa.md").exists())

    def test_no_shared_prefix_never_removes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = self.make_skill(tmp, ["aaa", "abb"])  # no 'x-' prefix
            out = run("droid", skill, tmp / "out")
            (out / "aaa-old.md").write_text("stale?\n")
            run("droid", skill, tmp / "out")
            self.assertTrue((out / "aaa-old.md").exists())

    def test_droid_rejects_invalid_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            skill = self.make_skill(tmp, ["Bad_Name"])
            with self.assertRaises(SystemExit):
                run("droid", skill, tmp / "out")


if __name__ == "__main__":
    unittest.main()
