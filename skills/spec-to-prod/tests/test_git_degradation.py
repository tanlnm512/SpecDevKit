"""Non-git degradation honesty (GITDEG assertions): audit.py and check.py
must print an explicit SKIPPED notice wherever a git-derived verdict would
otherwise silently pass off an empty diff — an empty `git diff` in a
non-git dir is not a clean tree, and converge must not conflate "no git
repository" with "no committed baseline".

Git is simulated, never invoked for real and never initialized: mocked
`audit.git` returns failing (non-git) or no-history CompletedProcess
objects; the CLI-level tests run against the genuinely non-git workspace,
which is the sanctioned test bed.
"""

import contextlib
import importlib.util
import io
import subprocess
import sys
import unittest
import unittest.mock
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
FIXTURE = SKILL / "examples" / "mini-spec" / "specs" / "mini-spec"

_check_spec = importlib.util.spec_from_file_location("check", SKILL / "scripts" / "check.py")
check = importlib.util.module_from_spec(_check_spec)
_check_spec.loader.exec_module(check)

_audit_spec = importlib.util.spec_from_file_location("audit", SKILL / "scripts" / "audit.py")
audit = importlib.util.module_from_spec(_audit_spec)
_audit_spec.loader.exec_module(audit)


def run_check(*argv):
    """Run check.main() with argv/out captured; return (exit_code, output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         unittest.mock.patch.object(sys, "argv", ["check.py", *argv]):
        code = check.main()
    return code, buf.getvalue()


def run_audit(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         unittest.mock.patch.object(sys, "argv", ["audit.py", *argv]):
        code = audit.main()
    return code, buf.getvalue()


def git_failing(repo, *args):
    """Every git call fails — the non-git shape (rc 128, fatal on stderr)."""
    return subprocess.CompletedProcess(
        ["git", "-C", str(repo), *args], 128, "", "fatal: not a git repository"
    )


def git_no_commits(repo, *args):
    """A repository exists (rev-parse succeeds) but has no history — the
    no-committed-baseline shape, distinct from no-repository."""
    if args and args[0] == "rev-parse":
        return subprocess.CompletedProcess(["git", "-C", str(repo), *args], 0, "", "")
    return subprocess.CompletedProcess(
        ["git", "-C", str(repo), *args], 128, "", "fatal: bad revision 'HEAD'"
    )


class ScopeSkipTests(unittest.TestCase):
    def test_scope_skipped_without_git(self):
        with unittest.mock.patch.object(audit, "git", git_failing):
            code, out = run_audit("scope", str(FIXTURE))
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED", out)
        self.assertIn("not a git repo", out)
        self.assertNotIn("every changed file is named", out)  # the false all-clear
        self.assertNotIn("changed file(s)", out)  # no count-based verdict either

    def test_clean_skipped_without_git(self):
        with unittest.mock.patch.object(audit, "git", git_failing):
            code, out = run_audit("clean", "--repo", ".")
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED", out)
        self.assertIn("not a git repo", out)
        self.assertNotIn("no debug prints", out)  # the false all-clear
        self.assertNotIn("scanned added lines", out)  # no scan claim either

    def test_probe_failure_degrades_like_git_absent(self):
        """The same choke-point probe covers git-broken dirs, not just
        git-absent ones: no verdict may leak either way."""
        with unittest.mock.patch.object(audit, "git", git_failing):
            _, scope_out = run_audit("scope", str(FIXTURE))
            _, clean_out = run_audit("clean", "--repo", ".")
        for out in (scope_out, clean_out):
            self.assertIn("SKIPPED (not a git repo)", out)


class ConvergeDistinctionTests(unittest.TestCase):
    def test_converge_without_git_reports_no_repository(self):
        with unittest.mock.patch.object(audit, "git", git_failing):
            code, out = run_audit("converge", str(FIXTURE))
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED", out)
        self.assertIn("no git repository", out)
        self.assertNotIn("NEW GAP", out)  # no diff noise without a baseline
        self.assertNotIn("no committed baseline", out)  # the other branch's wording

    def test_converge_with_gitless_history_reports_no_baseline(self):
        with unittest.mock.patch.object(audit, "git", git_no_commits):
            code, out = run_audit("converge", str(FIXTURE))
        self.assertEqual(code, 0)
        self.assertIn("no committed baseline", out)
        self.assertNotIn("no git repository", out)

    def test_the_two_conditions_print_distinct_output(self):
        with unittest.mock.patch.object(audit, "git", git_failing):
            _, no_git = run_audit("converge", str(FIXTURE))
        with unittest.mock.patch.object(audit, "git", git_no_commits):
            _, no_base = run_audit("converge", str(FIXTURE))
        self.assertNotEqual(no_git, no_base)


class DodDegradedTests(unittest.TestCase):
    def test_git_derived_dod_gates_skip_without_git(self):
        """dod's SCOPE/HYGIENE gates are git-derived; without git they must
        read SKIPPED, never PASS off an empty diff. (The fixture's open
        tasks keep gate 4 COMPLETENESS at FAIL — a real git-independent
        verdict — so the overall exit stays 1; the assertion is that the
        git gates are not among the failing ones.)"""
        empty_proofs = {"auto": [], "manual": [], "ok": {}, "errors": [], "failed": 0}
        with unittest.mock.patch.object(audit, "git", git_failing), \
             unittest.mock.patch.object(audit, "proofs_data", return_value=empty_proofs):
            code, out = run_audit("dod", str(FIXTURE))
        self.assertEqual(code, 1)  # gate 4 only — completeness, not git
        self.assertIn("VERDICT: MECHANICAL FAIL — gate(s) 4;", out)
        scope_line = next(l for l in out.splitlines() if "SCOPE" in l)
        hygiene_line = next(l for l in out.splitlines() if "HYGIENE" in l)
        self.assertIn("SKIPPED", scope_line)
        self.assertIn("not a git repo", scope_line)
        self.assertIn("SKIPPED", hygiene_line)
        self.assertIn("not a git repo", hygiene_line)
        self.assertNotIn("0 unmentioned of 0 changed", out)
        self.assertNotIn("0 suspect(s)", out)


class CheckStalenessTests(unittest.TestCase):
    def test_staleness_skip_visible_without_git(self):
        """The silent staleness skip becomes a visible informational line;
        the green fixture stays green (exit 0, no FAIL, warn count 0)."""
        real_run = subprocess.run

        def no_git(cmd, *a, **k):
            if cmd and cmd[0] == "git":
                raise OSError("git not found")
            return real_run(cmd, *a, **k)

        with unittest.mock.patch.object(check.subprocess, "run", no_git):
            code, out = run_check(str(FIXTURE))
        self.assertEqual(code, 0)
        self.assertIn("staleness: SKIPPED (not a git repo)", out)
        self.assertIn("(0 fail, 0 warn)", out)
        self.assertNotIn("FAIL", out)

    def test_no_staleness_note_when_no_baseline_header(self):
        """The note belongs to the baseline-present-but-gitless case only;
        a survey without any baseline keeps its existing warn, no note."""
        import shutil
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="s2c-gitdeg-"))
        try:
            spec_dir = tmp / "specs" / "demo"
            spec_dir.mkdir(parents=True)
            for f in ("spec.md", "plan.md", "tech-spec.md", "task.md", "test.md"):
                (spec_dir / f).write_text("placeholder text long enough. " * 10)
            (spec_dir / "survey.md").write_text('item S1: "x"\nstatus: DONE\n')
            code, out = run_check(str(spec_dir))
            self.assertEqual(code, 0)
            self.assertNotIn("staleness: SKIPPED", out)
        finally:
            shutil.rmtree(tmp)

    def test_staleness_skip_visible_when_git_present_but_commit_missing(self):
        """A candidate repo has .git but none contains the baseline commit
        (saw_git_dir=True, repo_hit=None): the skip must still be visible —
        an informational line, distinct from the no-git wording, never a
        silent pass or a false staleness warn. Fixture copied to temp (the
        original is never mutated); git mocked present-but-commit-less."""
        import shutil
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="s2c-nohit-"))
        try:
            root = tmp / "mini-spec"
            shutil.copytree(FIXTURE.parent.parent, root)
            spec_dir = root / "specs" / "mini-spec"
            (root / ".git").mkdir()  # candidate repo exists on disk...
            real_run = subprocess.run

            def git_commit_nohit(cmd, *a, **k):
                # git binary present, but the baseline commit isn't in it:
                # cat-file -e reports a bad object (rc 128).
                if cmd and cmd[0] == "git":
                    return subprocess.CompletedProcess(
                        cmd, 128, "", "fatal: Not a valid object name deadbee^{commit}"
                    )
                return real_run(cmd, *a, **k)

            with unittest.mock.patch.object(check.subprocess, "run", git_commit_nohit):
                code, out = run_check(str(spec_dir))
            self.assertEqual(code, 0)
            self.assertIn(
                "staleness: SKIPPED — no candidate repo contains the baseline commit",
                out,
            )
            self.assertNotIn("staleness: SKIPPED (not a git repo)", out)
            self.assertIn("(0 fail, 0 warn)", out)
            self.assertNotIn("FAIL", out)
        finally:
            shutil.rmtree(tmp)


class CliDegradedTests(unittest.TestCase):
    """Black-box runs on the real non-git workspace — the sanctioned test
    bed; no mocks. GITDEG-001/002/003/004's literal contract surface."""

    def cli(self, script, *args):
        return subprocess.run(
            [sys.executable, str(SKILL / "scripts" / script), *args],
            capture_output=True, text=True, cwd=SKILL, timeout=60,
        )

    def test_scope_cli_skipped_in_real_non_git_root(self):
        r = self.cli("audit.py", "scope", "examples/mini-spec/specs/mini-spec")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("SKIPPED", r.stdout)
        self.assertIn("not a git repo", r.stdout)
        self.assertNotIn("every changed file is named", r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    def test_clean_cli_skipped_in_real_non_git_root(self):
        r = self.cli("audit.py", "clean", "--repo", ".")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("SKIPPED", r.stdout)
        self.assertIn("not a git repo", r.stdout)
        self.assertNotIn("no debug prints", r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    def test_converge_cli_reports_no_git_repository(self):
        r = self.cli("audit.py", "converge", "examples/mini-spec/specs/mini-spec")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("SKIPPED", r.stdout)
        self.assertIn("no git repository", r.stdout)
        self.assertNotIn("no committed baseline", r.stdout)
        self.assertNotIn("NEW GAP", r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    def test_check_cli_staleness_line_visible_and_green(self):
        r = self.cli("check.py", "examples/mini-spec/specs/mini-spec")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("staleness: SKIPPED (not a git repo)", r.stdout)
        self.assertIn("(0 fail, 0 warn)", r.stdout)
        self.assertNotIn("FAIL", r.stdout)

    def test_no_positive_git_verdict_anywhere_in_degraded_output(self):
        outs = [
            self.cli("audit.py", m, "examples/mini-spec/specs/mini-spec").stdout
            for m in ("scope", "converge")
        ] + [self.cli("audit.py", "clean", "--repo", ".").stdout]
        for out in outs:
            self.assertIn("SKIPPED", out)
            for verdict in ("every changed file is named", "no debug prints",
                            "NEW GAP", "no committed baseline"):
                self.assertNotIn(verdict, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
