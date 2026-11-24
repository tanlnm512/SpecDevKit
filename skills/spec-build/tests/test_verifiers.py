"""The verifier-definition guard: a change to the files that say what
the checks check is listed by `verifiers`, drafted by `block`, and
fails dod gate 14 until a `Verifier:` ruling covers it — a
dependency-only manifest change is not a verifier change."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
AUDIT = SCRIPTS / "audit.py"
TINY = SKILL / "examples" / "spec-tiny-delivered"
ENV = {**os.environ, "KIT_TELEMETRY": "off"}

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import audit  # noqa: E402


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=kit",
         "-c", "user.email=kit@example.com", *args],
        check=True, capture_output=True, text=True,
    ).stdout


def run(*argv, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([*map(str, argv)], cwd=str(cwd), env=ENV,
                          capture_output=True, text=True)


class VerifierGuardTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="verifier-guard-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q")
        (self.root / "README").write_text("seed\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        self.base = git(self.root, "rev-parse", "--short", "HEAD").strip()
        self.spec = self.root / "specs" / "demo"
        self.spec.mkdir(parents=True)
        (self.spec / "spec.md").write_text(
            "# Spec: demo\n\n## Requirements\n- **FR-001**: works\n",
            encoding="utf-8")

    def test_a_changed_makefile_is_listed_unruled_and_exit_1(self):
        (self.root / "Makefile").write_text(
            "test:\n\tpython3 -m pytest -q\n", encoding="utf-8")
        rows = audit.verifier_changes(self.spec, self.root, self.base)
        self.assertEqual(rows, [("Makefile", "make recipe", 2, 0)])
        r = run(sys.executable, AUDIT, "verifiers", self.spec,
                "--repo", self.root, "--base", self.base, cwd=self.root)
        self.assertIn("UNRULED  Makefile  [make recipe]  +2 -0", r.stdout)
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_an_edited_makefile_counts_added_and_removed_lines(self):
        (self.root / "Makefile").write_text(
            "test:\n\tpython3 -m pytest -q\n", encoding="utf-8")
        git(self.root, "add", "Makefile")
        git(self.root, "commit", "-qm", "the repo's own check")
        head = git(self.root, "rev-parse", "--short", "HEAD").strip()
        (self.root / "Makefile").write_text(
            "test:\n\tpython3 -m pytest -q -x\n\nlint:\n\truff check .\n",
            encoding="utf-8")
        rows = audit.verifier_changes(self.spec, self.root, head)
        self.assertEqual(rows, [("Makefile", "make recipe", 4, 1)])

    def test_an_untouched_makefile_lists_nothing(self):
        (self.root / "Makefile").write_text(
            "test:\n\tpython3 -m pytest -q\n", encoding="utf-8")
        git(self.root, "add", "Makefile")
        git(self.root, "commit", "-qm", "the repo's own check")
        rows = audit.verifier_changes(self.spec, self.root, None)
        self.assertEqual(rows, [])
        r = run(sys.executable, AUDIT, "verifiers", self.spec,
                "--repo", self.root, cwd=self.root)
        self.assertIn("no change to the files that define what the "
                      "checks check", r.stdout)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_verifier_change_another_commit_landed_is_not_judged(self):
        (self.root / "Makefile").write_text(
            "test:\n\tpython3 -m pytest -q\n", encoding="utf-8")
        git(self.root, "add", "Makefile")
        git(self.root, "commit", "-qm", "ci: unrelated tightening")
        self.assertEqual(audit.verifier_changes(self.spec, self.root, self.base), [])

    def test_dependency_only_pyproject_change_is_not_a_verifier_change(self):
        (self.root / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools"]\n\n[project]\n'
            'dependencies = ["requests==2.0.0"]\n', encoding="utf-8")
        git(self.root, "add", "pyproject.toml")
        git(self.root, "commit", "-qm", "pyproject")
        head = git(self.root, "rev-parse", "--short", "HEAD").strip()
        (self.root / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools"]\n\n[project]\n'
            'dependencies = ["requests==2.0.1"]\n', encoding="utf-8")
        self.assertEqual(audit.verifier_changes(self.spec, self.root, head), [])
        (self.root / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools"]\n\n[project]\n'
            'dependencies = ["requests==2.0.1"]\n\n'
            '[tool.pytest.ini_options]\naddopts = "-q"\n', encoding="utf-8")
        rows = audit.verifier_changes(self.spec, self.root, head)
        self.assertEqual(rows, [("pyproject.toml",
                                 "tool.pytest.ini_options table", 4, 1)])
        r = run(sys.executable, AUDIT, "verifiers", self.spec,
                "--repo", self.root, "--base", head, cwd=self.root)
        self.assertIn("UNRULED  pyproject.toml  [tool.pytest.ini_options "
                      "table]  +4 -1", r.stdout)
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_a_manifest_change_a_commit_landed_is_judged_against_the_anchor(self):
        # the change's own commit landed since the approval anchor (the
        # C1 shape): the manifest's kind is judged against the anchor,
        # never against HEAD — where the edit is already invisible and
        # the guard would miss exactly the change it exists for
        (self.root / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools"]\n\n[project]\n'
            'dependencies = ["requests==2.0.0"]\n', encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "anchor: dependency-only manifest")
        anchor = git(self.root, "rev-parse", "--short", "HEAD").strip()
        (self.spec / "approvals").mkdir()
        (self.spec / "approvals" / "approval.md").write_text(
            f"# Approval freeze\n\n**Approved-at**: `{anchor}`\n",
            encoding="utf-8")
        (self.root / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools"]\n\n[project]\n'
            'dependencies = ["requests==2.0.0"]\n\n'
            '[tool.pytest.ini_options]\naddopts = "-q"\n', encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "feat(demo): pytest table (demo)")
        rows = audit.verifier_changes(self.spec, self.root, None)
        self.assertEqual(rows,
                         [("pyproject.toml", "tool.pytest.ini_options table",
                           3, 0)])
        r = run(sys.executable, AUDIT, "verifiers", self.spec,
                "--repo", self.root, cwd=self.root)
        self.assertIn("UNRULED  pyproject.toml  [tool.pytest.ini_options "
                      "table]  +3 -0", r.stdout)
        self.assertEqual(r.returncode, 1, r.stdout)
        # block drafts and dod gate 14 read the same verdict — the change
        # is ruled on, never read as quiet
        r = run(sys.executable, AUDIT, "block", self.spec,
                "--repo", self.root, cwd=self.root)
        self.assertIn("- Verifier: pyproject.toml — <ruling>", r.stdout)
        r = run(sys.executable, AUDIT, "dod", self.spec, "--dry-run",
                cwd=self.root)
        self.assertRegex(r.stdout,
                         r"14 VERIFIERS\s+FAIL\s+1 unruled verifier change")

    def test_package_json_scripts_is_a_verifier_change_dependencies_are_not(self):
        (self.root / "package.json").write_text(
            '{\n  "name": "demo",\n  "dependencies": {\n'
            '    "left-pad": "^1.0.0"\n  }\n}\n', encoding="utf-8")
        git(self.root, "add", "package.json")
        git(self.root, "commit", "-qm", "package.json")
        head = git(self.root, "rev-parse", "--short", "HEAD").strip()
        (self.root / "package.json").write_text(
            '{\n  "name": "demo",\n  "dependencies": {\n'
            '    "left-pad": "^1.0.1"\n  }\n}\n', encoding="utf-8")
        self.assertEqual(audit.verifier_changes(self.spec, self.root, head), [])
        (self.root / "package.json").write_text(
            '{\n  "name": "demo",\n  "scripts": {\n    "test": "jest"\n  },\n'
            '  "dependencies": {\n    "left-pad": "^1.0.1"\n  }\n}\n',
            encoding="utf-8")
        rows = audit.verifier_changes(self.spec, self.root, head)
        self.assertEqual(rows, [("package.json", "scripts block", 4, 1)])

    def test_a_changed_workflow_file_is_listed(self):
        wf = self.root / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text(
            "on: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
            encoding="utf-8")
        rows = audit.verifier_changes(self.spec, self.root, self.base)
        self.assertEqual(rows, [(".github/workflows/ci.yml",
                                 "GitHub Actions workflow", 4, 0)])
        r = run(sys.executable, AUDIT, "verifiers", self.spec,
                "--repo", self.root, "--base", self.base, cwd=self.root)
        self.assertIn("UNRULED  .github/workflows/ci.yml  [GitHub Actions "
                      "workflow]  +4 -0", r.stdout)
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_block_drafts_the_verifier_line_until_ruled(self):
        (self.root / "Makefile").write_text(
            "test:\n\tpython3 -m pytest -q\n", encoding="utf-8")
        r = run(sys.executable, AUDIT, "block", self.spec,
                "--repo", self.root, "--base", self.base, cwd=self.root)
        self.assertIn("- Verifier: Makefile — <ruling>", r.stdout)
        (self.spec / "task.md").write_text(
            "# Tasks: demo\n\nDelivered: commit @ -\n\n"
            "- Verifier: Makefile — suites moved to pytest, the same set runs\n",
            encoding="utf-8")
        r = run(sys.executable, AUDIT, "block", self.spec,
                "--repo", self.root, "--base", self.base, cwd=self.root)
        self.assertNotIn("- Verifier:", r.stdout)
        r = run(sys.executable, AUDIT, "verifiers", self.spec,
                "--repo", self.root, "--base", self.base, cwd=self.root)
        self.assertIn("RULED    Makefile  [make recipe]  +2 -0", r.stdout)
        self.assertNotIn("UNRULED", r.stdout)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_dod_gate_14_fails_until_the_ruling_lands_in_the_tiny_block(self):
        spec = self.root / "specs" / "tiny"
        shutil.copytree(TINY, spec)
        (self.root / "Makefile").write_text(
            "test:\n\tpython3 -m unittest discover\n", encoding="utf-8")
        r = run(sys.executable, AUDIT, "dod", spec, "--dry-run", cwd=self.root)
        self.assertRegex(r.stdout,
                         r"14 VERIFIERS\s+FAIL\s+1 unruled verifier change")
        self.assertEqual(r.returncode, 1, r.stdout)

        holder = spec / "spec.md"
        holder.write_text(holder.read_text(encoding="utf-8")
                          + "- Verifier: Makefile — the recipe adds -q; "
                            "the same suite runs\n", encoding="utf-8")
        r = run(sys.executable, AUDIT, "dod", spec, "--dry-run", cwd=self.root)
        self.assertRegex(r.stdout,
                         r"14 VERIFIERS\s+PASS\s+0 unruled verifier change\(s\) "
                         r"\(1 ruled in the delivery block\)")

    def test_the_classifier_stays_on_the_documented_patterns(self):
        cases = {
            "Makefile": "make recipe",
            "makefile": "make recipe",
            "GNUmakefile": "make recipe",
            "justfile": "just recipe",
            "tools/Makefile": "make recipe",
            ".github/workflows/ci.yml": "GitHub Actions workflow",
            ".github/workflows/ci.yaml": "GitHub Actions workflow",
            ".github/workflows/README.md": None,
            ".forgejo/workflows/build.yml": "Forgejo workflow",
            ".gitlab-ci.yml": "GitLab CI config",
            ".circleci/config.yml": "CircleCI config",
            ".buildkite/pipeline.yml": "Buildkite pipeline",
            "Jenkinsfile": "Jenkins pipeline",
            "azure-pipelines.yml": "Azure Pipelines config",
            "pytest.ini": "pytest config",
            "tox.ini": "tox config",
            "setup.cfg": "ini tool config",
            "tests/conftest.py": "pytest fixtures/hooks",
            "jest.config.js": "Jest config",
            "vitest.config.mts": "Vitest config",
            ".mocharc.yml": "Mocha config",
            "karma.conf.cjs": "Karma config",
            "phpunit.xml.dist": "PHPUnit config",
            ".eslintrc.json": "ESLint config",
            ".flake8": "flake8 config",
            "ruff.toml": "ruff config",
            ".pre-commit-config.yaml": "pre-commit hooks",
            ".coveragerc": "coverage config",
            "requirements.txt": None,
            "pyproject.toml": None,
            "package.json": None,
            "poetry.lock": None,
        }
        for path, kind in cases.items():
            self.assertEqual(audit.verifier_kind(path), kind, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
