"""Tests for scripts/gate.sh — spec-code-review's portable mechanical
gate. Fixtures are throwaway git repos; detection is asserted through
--plan JSON, execution through real runs. Tools that may be absent on a
host (npm, pytest) are asserted conditionally on their presence, the
way the gate itself degrades."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
GATE = SKILL / "scripts" / "gate.sh"


def run_gate(*argv):
    return subprocess.run(
        ["bash", str(GATE), *argv], capture_output=True, text=True, timeout=180)


class GateBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gate-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "gate@example.com")
        self.git("config", "user.name", "Gate Test")

    def git(self, *argv):
        subprocess.run(["git", "-C", str(self.repo), *argv],
                       check=True, capture_output=True)

    def commit_all(self, msg="wip"):
        self.git("add", "-A")
        self.git("commit", "-qm", msg)

    def plan_names(self):
        r = run_gate("--repo", str(self.repo), "--plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        return [c["name"] for c in json.loads(r.stdout)]

    def run_on_repo(self):
        return run_gate("--repo", str(self.repo))


class DetectionTests(GateBase):
    def test_makefile_targets_detected_per_target(self):
        (self.repo / "Makefile").write_text(
            "test:\n\t@true\ncheck:\n\t@true\n")
        self.commit_all()
        names = self.plan_names()
        self.assertTrue(any("make test" in n for n in names), names)
        self.assertTrue(any("make check" in n for n in names), names)
        self.assertFalse(any("make lint" in n for n in names), names)

    def test_npm_detected_only_with_npm_on_path(self):
        (self.repo / "package.json").write_text(
            '{"name": "x", "scripts": {"test": "node -e 0"}}')
        self.commit_all()
        names = self.plan_names()
        if shutil.which("npm"):
            self.assertTrue(any("npm run test" in n for n in names), names)
        else:
            self.assertFalse(any("npm" in n for n in names), names)

    def test_python_repo_picks_pytest_or_unittest(self):
        (self.repo / "pyproject.toml").write_text("[project]\nname='x'\n")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "test_ok.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n"
            "    def test_ok(self):\n        pass\n")
        self.commit_all()
        names = self.plan_names()
        if shutil.which("pytest"):
            self.assertTrue(any("pytest" in n for n in names), names)
        else:
            self.assertTrue(any("unittest discover" in n for n in names), names)

    def test_repo_venv_pytest_used_when_path_lacks_it(self):
        if shutil.which("pytest"):
            self.skipTest("pytest on PATH — detection prefers it, covered above")
        (self.repo / "pyproject.toml").write_text("[project]\nname='x'\n")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "test_ok.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n"
            "    def test_ok(self):\n        self.assertTrue(True)\n")
        bindir = self.repo / ".venv" / "bin"
        bindir.mkdir(parents=True)
        vpytest = bindir / "pytest"
        vpytest.write_text(
            "#!/bin/sh\nexec python3 -m unittest discover -s tests\n")
        vpytest.chmod(0o755)
        self.commit_all()
        r = self.run_on_repo()
        self.assertEqual(r.returncode, 0, r.stderr)
        entry = next(c for c in json.loads(r.stdout) if "pytest" in c["name"])
        self.assertEqual(entry["exit_code"], 0)
        self.assertIn(".venv", entry["name"])

    def test_uv_locked_repo_detected_without_venv_or_path_pytest(self):
        if shutil.which("pytest") or not shutil.which("uv"):
            self.skipTest("needs uv on PATH and no global pytest")
        (self.repo / "pyproject.toml").write_text("[project]\nname='x'\n")
        (self.repo / "uv.lock").write_text("lock = 'stub'\n")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "test_ok.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n"
            "    def test_ok(self):\n        pass\n")
        self.commit_all()
        names = self.plan_names()
        self.assertTrue(any("pytest (uv run)" in n for n in names), names)

    def test_no_markers_detect_nothing(self):
        (self.repo / "README.md").write_text("nothing here\n")
        self.commit_all()
        self.assertEqual(self.plan_names(), [])

    def test_plan_emits_null_exit_codes(self):
        (self.repo / "Makefile").write_text("test:\n\t@true\n")
        self.commit_all()
        r = run_gate("--repo", str(self.repo), "--plan")
        checks = json.loads(r.stdout)
        self.assertTrue(checks)
        for c in checks:
            self.assertIsNone(c["exit_code"])
            self.assertIn("name", c)
            self.assertIn("tail", c)


class ExecutionTests(GateBase):
    def test_green_gate_reports_json_and_zero_exit(self):
        (self.repo / "Makefile").write_text("test:\n\t@echo ok\n")
        self.commit_all()
        r = self.run_on_repo()
        self.assertEqual(r.returncode, 0, r.stderr)
        checks = json.loads(r.stdout)
        self.assertTrue(checks)
        for c in checks:
            self.assertEqual(c["exit_code"], 0)
            self.assertIn("tail", c)

    def test_failing_check_red_gate_with_exit_code(self):
        (self.repo / "Makefile").write_text("test:\n\t@exit 3\n")
        self.commit_all()
        r = self.run_on_repo()
        self.assertNotEqual(r.returncode, 0)
        entry = next(c for c in json.loads(r.stdout) if "make test" in c["name"])
        # make's own error exit (2 on BSD make, the recipe's code on GNU)
        self.assertNotEqual(entry["exit_code"], 0)

    def test_changed_shell_files_get_bash_n(self):
        (self.repo / "ok.sh").write_text("echo fine\n")
        self.commit_all("clean base")
        (self.repo / "broken.sh").write_text("if true then\n")
        r = self.run_on_repo()
        self.assertNotEqual(r.returncode, 0)
        entry = next(c for c in json.loads(r.stdout) if "bash -n" in c["name"])
        self.assertEqual(entry["exit_code"], 1)
        self.assertIn("broken.sh", entry["tail"])

    def test_unchanged_shell_files_are_out_of_scope(self):
        (self.repo / "broken.sh").write_text("if true then\n")
        self.commit_all("committed, not in the working diff")
        r = self.run_on_repo()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(any("bash -n" in c["name"] for c in json.loads(r.stdout)))

    def test_tree_mode_scans_all_tracked_scripts(self):
        (self.repo / "broken.sh").write_text("if true then\n")
        self.commit_all("committed, not in the working diff")
        r = run_gate("--repo", str(self.repo), "--tree")
        self.assertNotEqual(r.returncode, 0)
        entry = next(c for c in json.loads(r.stdout) if "bash -n" in c["name"])
        self.assertEqual(entry["exit_code"], 1)
        self.assertIn("broken.sh", entry["tail"])
        self.assertIn("tracked scripts", entry["name"])

    def test_tree_mode_green_on_valid_tracked_scripts(self):
        (self.repo / "ok.sh").write_text("echo fine\n")
        self.commit_all()
        r = run_gate("--repo", str(self.repo), "--tree")
        self.assertEqual(r.returncode, 0, r.stderr)
        entry = next(c for c in json.loads(r.stdout) if "bash -n" in c["name"])
        self.assertEqual(entry["exit_code"], 0)
        self.assertIn("tracked scripts", entry["name"])

    def test_python_unittest_path_actually_runs_tests(self):
        (self.repo / "pyproject.toml").write_text("[project]\nname='x'\n")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "test_ok.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n"
            "    def test_ok(self):\n        self.assertTrue(True)\n")
        self.commit_all()
        if shutil.which("pytest"):
            self.skipTest("pytest present — detection prefers it, covered above")
        r = self.run_on_repo()
        self.assertEqual(r.returncode, 0, r.stderr)
        entry = next(c for c in json.loads(r.stdout) if "unittest" in c["name"])
        self.assertEqual(entry["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
