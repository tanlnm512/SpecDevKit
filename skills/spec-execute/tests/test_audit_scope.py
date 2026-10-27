"""scope_data contract: kit-owned specs surfaces are expected delivery
surface; every other unmentioned specs/ path is scope creep."""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
_SCRIPTS = SKILL / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_spec = importlib.util.spec_from_file_location("audit", _SCRIPTS / "audit.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, capture_output=True, text=True,
    ).stdout


class ScopeKitOwnedFilesTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="audit-scope-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q")
        (self.root / "seed.txt").write_text("seed\n", encoding="utf-8")
        git(self.root, "add", "-A")
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=kit",
             "-c", "user.email=kit@example.com", "commit", "-qm", "base"],
            check=True, capture_output=True)
        self.base = git(self.root, "rev-parse", "--short", "HEAD").strip()
        spec = self.root / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "task.md").write_text(
            "# Task: demo\n\n- [ ] T001 do it (FR-001)\n", encoding="utf-8")
        (self.root / "specs" / "INDEX.md").write_text(
            "# Index\n\n- demo\n", encoding="utf-8")
        (self.root / "specs" / "context").mkdir()
        (self.root / "specs" / "context" / "tech.md").write_text(
            "stack\n", encoding="utf-8")
        (self.root / "specs" / "other").mkdir()
        (self.root / "specs" / "other" / "creep.md").write_text(
            "x\n", encoding="utf-8")

    def test_kit_owned_files_expected_context_named_creep_flagged(self):
        _, unmentioned = audit.scope_data(
            self.root / "specs" / "demo", self.root, self.base)
        self.assertNotIn("specs/INDEX.md", unmentioned)
        self.assertIn("specs/context/tech.md", unmentioned)
        self.assertIn("specs/other/creep.md", unmentioned)


if __name__ == "__main__":
    unittest.main()
