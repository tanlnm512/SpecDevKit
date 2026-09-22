"""Tests for scripts/audit.py — run via tests/run.sh (needs Python >= 3.10).

Covers the four TESTCOV contract groups assigned to audit.py:
- parse_survey_items: item/status extraction incl. malformed and empty
  surveys (TESTCOV-001).
- git-path degradation one layer below audit.git: subprocess.run itself is
  mocked so every git call returns non-zero (rc 128 non-git, rc 127 absent
  binary) and the SKIPPED paths execute without raising (TESTCOV-002).
- proofs parsing: auto (runnable command) vs manual (observation)
  classification, mixed list + empty (TESTCOV-003).
- dod gate presence/absence: all ten gates on a green sample, plus the
  representative mechanical failures — proofs (gate 1), completeness
  (gate 4), contract health (gate 5) (TESTCOV-004).
- dod gate 4 delegation (SPECSTATE-003, graph-engine user-testing round 1):
  completeness totals flow through specstate.task_entries and no second
  copy of the task-entries parser survives in audit.py.
- dod fail-closed checker handling (FR-007 / TC-007): a checker that
  cannot start, times out, or delivers no verdict line fails its gate
  with a diagnostic instead of reading as green, and every failed proof
  is named.
- dry/live proof separation (FR-004 / TC-004, audit half): classify_proofs
  and `dod --dry-run` execute no test.md command — a mutating pass
  condition leaves no canary — while plain dod still executes it.

No test invokes git for real: every git path runs with subprocess.run
patched (the sibling test_git_degradation.py additionally exercises the
genuinely non-git workspace at CLI level).
"""

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
FIXTURE = SKILL / "examples" / "mini-spec" / "specs" / "mini-spec"

_audit_spec = importlib.util.spec_from_file_location("audit", SKILL / "scripts" / "audit.py")
audit = importlib.util.module_from_spec(_audit_spec)
_audit_spec.loader.exec_module(audit)

# audit.py's import-time sys.path setup pulls specstate in as a normal
# module; this import binds that same instance, so the spy below wraps the
# exact parser object audit.py's gate 4 is required to call.
import specstate  # noqa: E402 - valid only after the audit load above


def run_audit(*argv):
    """Run audit.main() with argv/stdout captured; return (exit_code, output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         unittest.mock.patch.object(sys, "argv", ["audit.py", *argv]):
        code = audit.main()
    return code, buf.getvalue()


class CommentSuspectTests(unittest.TestCase):
    """clean's comment guardrails: essay comments (≥120-char comment
    lines) and comment walls (≥8 consecutive) are suspects; short
    constraint comments, URLs, and markdown headings are not."""

    @staticmethod
    def findings(lines, path="src/app.py"):
        with unittest.mock.patch.object(
                audit, "added_lines",
                return_value=iter((path, i, t) for i, t in enumerate(lines, 1))):
            return audit.clean_findings(Path("/repo"), None)

    def test_short_comment_is_not_a_suspect(self):
        self.assertEqual(
            self.findings(["# retry: the API is eventually consistent"]), [])

    def test_essay_comment_flagged(self):
        kinds = [k for _, _, k, _ in self.findings(["# " + "x" * 130])]
        self.assertIn("essay comment", kinds)

    def test_long_comment_with_url_not_flagged(self):
        kinds = [k for _, _, k, _ in
                 self.findings(["# see https://example.com/" + "a" * 130])]
        self.assertNotIn("essay comment", kinds)

    def test_comment_wall_at_threshold(self):
        kinds = [k for _, _, k, _ in
                 self.findings([f"# note {i}" for i in range(8)])]
        self.assertEqual(kinds.count("comment wall"), 1)

    def test_seven_lines_no_wall(self):
        kinds = [k for _, _, k, _ in
                 self.findings([f"# note {i}" for i in range(7)])]
        self.assertNotIn("comment wall", kinds)

    def test_code_line_resets_the_wall(self):
        lines = ["# a", "# b", "# c", "x = 1", "# d", "# e", "# f", "# g"]
        kinds = [k for _, _, k, _ in self.findings(lines)]
        self.assertNotIn("comment wall", kinds)

    def test_markdown_headings_ignored(self):
        lines = [f"# heading {i}" for i in range(10)]
        self.assertEqual(self.findings(lines, path="README.md"), [])


class ArchivedModeTests(unittest.TestCase):
    """audit.py archived — the OpenSpec-style archive gate: every dir
    under specs/archive/ holds a fully-closed task.md (ticked or struck);
    no unticked entry survives into the as-built record."""

    @staticmethod
    def archive(tmp, name, entries):
        d = Path(tmp) / "specs" / "archive" / name
        d.mkdir(parents=True)
        (d / "task.md").write_text(
            "# Tasks\n\n## Phase 1\n\n" + "\n".join(entries) + "\n")
        return d

    def run_archived(self, tmp):
        return run_audit("archived", "--repo", str(tmp))

    def test_fully_closed_archive_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.archive(tmp, "2026-01-01-alpha", [
                "- [x] T001 add parser (FR-001)",
                "- [ ] ~~T005~~ dropped (D-003)",  # struck counts as closed
            ])
            code, out = self.run_archived(tmp)
            self.assertEqual(code, 0)
            self.assertIn("PASS  2026-01-01-alpha", out)
            self.assertIn("fully closed", out)

    def test_open_entry_fails_and_names_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.archive(tmp, "2026-02-02-beta", [
                "- [x] T001 add parser (FR-001)",
                "- [ ] T002 wire the CLI (FR-001)",
            ])
            code, out = self.run_archived(tmp)
            self.assertEqual(code, 1)
            self.assertIn("FAIL  2026-02-02-beta", out)
            self.assertIn("T002", out)

    def test_missing_task_md_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "specs" / "archive" / "2026-03-03-gamma").mkdir(parents=True)
            code, out = self.run_archived(tmp)
            self.assertEqual(code, 1)
            self.assertIn("no task.md", out)

    def test_no_archive_yet_is_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self.run_archived(tmp)
            self.assertEqual(code, 0)
            self.assertIn("no archive yet", out)


def fake_run(git_rc=128, git_stderr="fatal: not a git repository",
             check_stdout=None, check_rc=0, check_stderr="",
             check_raises=None, proof_raises=None):
    """subprocess.run stand-in mediating every call audit.py makes: git
    commands get a failing CompletedProcess (never a real git process), an
    optional check.py invocation gets check_stdout/rc/stderr or raises
    check_raises, proof shell commands raise proof_raises when given, and
    anything else (proofs' shell commands) reaches the real subprocess.run."""
    real = subprocess.run

    def fake(cmd, *a, **k):
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "git":
            return subprocess.CompletedProcess(cmd, git_rc, "", git_stderr)
        if (isinstance(cmd, list) and len(cmd) >= 2
                and Path(cmd[1]).name == "check.py"):
            if check_raises is not None:
                raise check_raises
            if check_stdout is not None:
                return subprocess.CompletedProcess(cmd, check_rc, check_stdout, check_stderr)
            return real(cmd, *a, **k)
        if proof_raises is not None:
            raise proof_raises
        return real(cmd, *a, **k)

    return fake


def make_spec(tmp, files):
    """Write `files` ({name: text}) into <tmp>/specs/demo/; returns the dir."""
    spec_dir = tmp / "specs" / "demo"
    spec_dir.mkdir(parents=True)
    for name, text in files.items():
        (spec_dir / name).write_text(text, encoding="utf-8")
    return spec_dir


SURVEY_SAMPLE = """# Survey: demo

## Items

```
item S1: "add function exists"
  evidence:   repo/calc.py:add — read output, pasted verbatim
  status:     DONE
  verify:     grep -n "def add" repo/calc.py

item S2: "multiply handles floats"
  evidence:   unknown — verify
  status:     PARTIAL
  gap:        only the int path is proven

item S3: "stream results"
  evidence:   repo/calc.py:stream — grep output
  status:     TODO
```
"""

TICKED_TASK = """## Phase 1

- [x] T001: prove the thing

| Phase | Total | Done |
|-------|-------|------|
| 1 | 1 | 1 |
| **Σ** | 1 | 1 |
"""

UNTICKED_TASK = TICKED_TASK.replace("- [x] T001", "- [ ] T001")

PASSING_TC = '### TC-001 — add\n**Pass condition**: `python3 -c "print(2 + 2)"` exits 0.\n'
FAILING_TC = '### TC-001 — add\n**Pass condition**: `python3 -c "import sys; sys.exit(9)"`\n'
CANARY_TC = ('### TC-001 — side effect\n'
             '**Pass condition**: `python3 -c "open(\'canary.txt\', \'w\')"` '
             'exits 0.\n')
GREEN_CHECK = "spec: ok\nsurvey: ok\nPASS (0 fail, 0 warn)\n"
EMPTY_PROOFS = {"auto": [], "manual": [], "ok": {}, "errors": [], "failed": 0}


class SurveyItemsParseTests(unittest.TestCase):
    """TESTCOV-001: the survey-item parser converge diffs with."""

    def test_extracts_descriptions_and_statuses(self):
        items = audit.parse_survey_items(SURVEY_SAMPLE)
        self.assertEqual(items, {
            "S1": ("add function exists", "DONE"),
            "S2": ("multiply handles floats", "PARTIAL"),
            "S3": ("stream results", "TODO"),
        })

    def test_item_without_status_line_reads_unknown(self):
        text = 'item S9: "status never filled in"\n  evidence:   repo/x.py:1\n'
        self.assertEqual(audit.parse_survey_items(text),
                         {"S9": ("status never filled in", "unknown")})

    def test_malformed_item_blocks_are_skipped_not_raised(self):
        text = ('item this line has no quoted description\n'
                'item S4: "fine"\nstatus: TODO\n')
        self.assertEqual(audit.parse_survey_items(text), {"S4": ("fine", "TODO")})

    def test_empty_survey_parses_to_no_items(self):
        self.assertEqual(audit.parse_survey_items(""), {})
        self.assertEqual(audit.parse_survey_items("# Survey: empty\n\n## Items\n"), {})


class GitMockedDegradationTests(unittest.TestCase):
    """TESTCOV-002: the SKIPPED paths, proven one layer below audit.git —
    subprocess.run itself returns non-zero for git, so no git process is
    ever spawned and every git-derived mode degrades without raising."""

    def test_availability_probe_reads_mocked_run(self):
        with unittest.mock.patch.object(audit.subprocess, "run", fake_run()):
            self.assertFalse(audit.git_available(FIXTURE))

    def test_changed_paths_helper_degrades_to_empty(self):
        with unittest.mock.patch.object(audit.subprocess, "run", fake_run()):
            self.assertEqual(audit.changed_paths(FIXTURE, None), [])

    def test_added_lines_helper_degrades_to_no_findings(self):
        with unittest.mock.patch.object(audit.subprocess, "run", fake_run()):
            self.assertEqual(list(audit.added_lines(FIXTURE, None)), [])

    def test_scope_takes_skipped_path(self):
        with unittest.mock.patch.object(audit.subprocess, "run", fake_run()):
            code, out = run_audit("scope", str(FIXTURE))
        self.assertEqual(code, 0)
        self.assertIn("scope: SKIPPED (not a git repo) — no scope verdict", out)
        self.assertNotIn("changed file(s)", out)  # no count-based verdict either

    def test_clean_takes_skipped_path(self):
        with unittest.mock.patch.object(audit.subprocess, "run", fake_run()):
            code, out = run_audit("clean", "--repo", str(SKILL))
        self.assertEqual(code, 0)
        self.assertIn("clean: SKIPPED (not a git repo) — no cleanliness verdict", out)
        self.assertNotIn("no debug prints", out)  # the false all-clear

    def test_converge_takes_no_repository_branch(self):
        with unittest.mock.patch.object(audit.subprocess, "run", fake_run()):
            code, out = run_audit("converge", str(FIXTURE))
        self.assertEqual(code, 0)
        self.assertIn("no git repository", out)
        self.assertNotIn("no committed baseline", out)  # the other branch's wording
        self.assertNotIn("NEW GAP", out)  # no diff noise without a baseline

    def test_missing_git_binary_degrades_like_non_git(self):
        """FileNotFoundError-equivalent: what the shell reports for an
        absent git binary (rc 127, 'command not found') must land on the
        same SKIPPED path — a missing binary is not a clean tree."""
        mock = fake_run(git_rc=127, git_stderr="git: command not found")
        with unittest.mock.patch.object(audit.subprocess, "run", mock):
            self.assertFalse(audit.git_available(FIXTURE))
            code, out = run_audit("scope", str(FIXTURE))
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED (not a git repo)", out)

    def test_raising_git_call_degrades_like_non_git(self):
        """The FileNotFoundError itself: a git binary absent from PATH makes
        subprocess.run raise, and the choke point must absorb that exactly
        like check.py's staleness guard does — SKIPPED path, no traceback."""
        def raising(cmd, *a, **k):
            if cmd and cmd[0] == "git":
                raise FileNotFoundError(2, "No such file or directory", "git")
            raise AssertionError("unexpected non-git call")

        with unittest.mock.patch.object(audit.subprocess, "run", raising):
            self.assertFalse(audit.git_available(FIXTURE))
            code, out = run_audit("scope", str(FIXTURE))
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED (not a git repo)", out)

    def test_every_spawned_process_call_is_git(self):
        """The mock mediates all of audit.py's subprocess traffic on this
        path: calls happen, and each one is a git call the mock answered —
        none reached the real git binary."""
        calls = []
        real = subprocess.run

        def spy(cmd, *a, **k):
            calls.append(cmd)
            if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "git":
                return subprocess.CompletedProcess(
                    cmd, 128, "", "fatal: not a git repository")
            return real(cmd, *a, **k)

        with unittest.mock.patch.object(audit.subprocess, "run", spy):
            run_audit("scope", str(FIXTURE))
        self.assertTrue(calls)
        self.assertTrue(
            all(isinstance(c, (list, tuple)) and c[0] == "git" for c in calls))


class ScopeIntegrityTests(unittest.TestCase):
    def test_uses_before_audit_base_and_flags_foreign_spec_path(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            spec = repo / "specs" / "demo"
            spec.mkdir(parents=True)
            task = spec / "task.md"
            task.write_text(
                "# Tasks\n\n## Phase 1\n"
                "- [ ] T001 change `src/app.py` (FR-001)\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "add", "specs/demo/task.md"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "-c", "user.name=Test",
                 "-c", "user.email=test@example.invalid", "commit", "-qm", "base"],
                check=True,
            )
            base = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            task.write_text(
                task.read_text(encoding="utf-8").replace(
                    "# Tasks\n",
                    f"# Tasks\n\n**Before-audit**: passed @ {base}\n",
                ),
                encoding="utf-8",
            )
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("x = 1\n")
            (repo / "specs" / "rogue.md").write_text("rogue\n")

            self.assertEqual(audit.effective_base(spec, None), base)
            paths, unmentioned = audit.scope_data(spec, repo, None)
            self.assertIn("src/app.py", paths)
            self.assertIn("specs/demo/task.md", paths)
            self.assertIn("specs/rogue.md", paths)
            self.assertIn("specs/rogue.md", unmentioned)
            self.assertNotIn("src/app.py", unmentioned)
            self.assertNotIn("specs/demo/task.md", unmentioned)


class EvidenceModeTests(unittest.TestCase):
    def test_missing_freeze_fails_without_running_tests(self):
        with tempfile.TemporaryDirectory() as td:
            spec = make_spec(Path(td), {
                "task.md": "**Before-audit**: passed @ -\n",
            })
            code, out = run_audit("evidence", str(spec), "--repo", str(Path(td)))
            self.assertEqual(code, 1)
            self.assertIn("approval freeze missing", out)


class ProofsClassificationTests(unittest.TestCase):
    """TESTCOV-003: proofs parsing — auto vs manual, dry run (run=False)
    never executes anything."""

    def test_mixed_list_classifies_auto_vs_manual(self):
        test_md = (
            PASSING_TC
            + "\n### TC-002 — greeting\n**Pass condition**: the greeting appears on screen.\n"
            + "\n### TC-003 — lint\n**Pass condition**: `./scripts/lint.sh --all` exits 0.\n"
            + "\n### TC-004 — unrecorded\nNo pass-condition line at all.\n"
        )
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(Path(td), {"test.md": test_md})
            d = audit.proofs_data(spec_dir, Path(td), run=False)
        self.assertEqual([tc for tc, _ in d["auto"]], ["TC-001", "TC-003"])
        self.assertEqual(
            d["manual"],
            [("TC-002", "(observation only)"),
             ("TC-004", "(no pass-condition line)")])
        self.assertEqual(d["ok"], {})
        self.assertEqual(d["failed"], 0)

    def test_dry_run_never_executes_the_failing_command(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(Path(td), {"test.md": FAILING_TC})
            d = audit.proofs_data(spec_dir, Path(td), run=False)
        self.assertEqual([tc for tc, _ in d["auto"]], ["TC-001"])
        self.assertEqual(d["ok"], {})
        self.assertEqual(d["failed"], 0)

    def test_empty_test_md_classifies_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            missing = make_spec(Path(td), {})
            d_missing = audit.proofs_data(missing, Path(td), run=False)
        with tempfile.TemporaryDirectory() as td:
            blank = make_spec(Path(td), {"test.md": ""})
            d_blank = audit.proofs_data(blank, Path(td), run=False)
        for d in (d_missing, d_blank):
            self.assertEqual(d["auto"], [])
            self.assertEqual(d["manual"], [])


class DodDryRunTests(unittest.TestCase):
    """FR-004 (TC-004, audit half): the dry DoD classification is separate
    from proof execution — classify_proofs and `dod --dry-run` run no
    test.md command (a mutating pass condition leaves no canary), gate 1
    reads DRY, and plain dod still executes."""

    def test_classify_proofs_spawns_no_process(self):
        calls = []
        real = subprocess.run

        def spy(cmd, *a, **k):
            calls.append(cmd)
            return real(cmd, *a, **k)

        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(Path(td), {"test.md": CANARY_TC})
            with unittest.mock.patch.object(audit.subprocess, "run", spy):
                d = audit.classify_proofs(spec_dir)
        self.assertEqual([tc for tc, _ in d["auto"]], ["TC-001"])
        self.assertEqual(calls, [])

    def test_proofs_data_dry_is_classification_plus_empty_execution(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(Path(td), {"test.md": CANARY_TC})
            d = audit.proofs_data(spec_dir, Path(td), run=False)
            cls = audit.classify_proofs(spec_dir)
        self.assertEqual(d["auto"], cls["auto"])
        self.assertEqual(d["manual"], cls["manual"])
        self.assertEqual((d["ok"], d["errors"], d["failed"]), ({}, [], 0))

    def test_dry_dod_never_executes_the_mutating_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_dir = make_spec(root, {"task.md": TICKED_TASK,
                                        "test.md": CANARY_TC})
            with unittest.mock.patch.object(
                    audit.subprocess, "run",
                    fake_run(check_stdout=GREEN_CHECK)):
                code, out = run_audit("dod", str(spec_dir), "--dry-run")
            self.assertEqual(code, 0, out)
            self.assertFalse((root / "canary.txt").exists())
        self.assertIn("DRY", find_gate_row(out, 1, "PROOF auto"))
        self.assertIn("1 auto TC(s) classified, not executed", out)
        self.assertNotIn("TCs green", out)  # no verdict from commands never run
        self.assertIn("VERDICT: MECHANICAL PASS — gate(s) 1 classified, "
                      "not executed (dry run); git gates 6, 7 SKIPPED", out)

    def test_dry_dod_still_measures_the_other_mechanical_gates(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(Path(td), {"task.md": UNTICKED_TASK,
                                            "test.md": CANARY_TC})
            with unittest.mock.patch.object(
                    audit.subprocess, "run",
                    fake_run(check_stdout=GREEN_CHECK)):
                code, out = run_audit("dod", str(spec_dir), "--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("0/1 ticked, 0/1 landed, 0 in-progress", out)
        self.assertIn("VERDICT: MECHANICAL FAIL — gate(s) 4;", out)

    def test_plain_dod_still_executes_proofs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_dir = make_spec(root, {"task.md": TICKED_TASK,
                                        "test.md": CANARY_TC})
            with unittest.mock.patch.object(
                    audit.subprocess, "run",
                    fake_run(check_stdout=GREEN_CHECK)):
                code, out = run_audit("dod", str(spec_dir))
            self.assertEqual(code, 0, out)
            self.assertTrue((root / "canary.txt").exists())
        self.assertIn("1/1 TCs green", out)


def find_gate_row(out, num, name):
    """The one gate-row locator — shared by every dod test class."""
    lines = [l for l in out.splitlines()
             if l.strip().startswith(f"{num} ") and name in l]
    assert len(lines) == 1, f"gate {num} ({name}) row not found in:\n{out}"
    return lines[0]


class DodGateTests(unittest.TestCase):
    """TESTCOV-004: gate presence (all ten gates on a green sample) and the
    representative missing-gate detections. check.py's subprocess is
    stubbed (its verdict parsing is gate 5's unit under test) and git is
    faked; proofs classification/execution runs for real."""

    def gate_row(self, out, num, name):
        return find_gate_row(out, num, name)

    def test_all_ten_gates_present_and_mechanical_pass(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(
                Path(td), {"task.md": TICKED_TASK, "test.md": PASSING_TC})
            with unittest.mock.patch.object(
                    audit.subprocess, "run", fake_run(check_stdout=GREEN_CHECK)):
                code, out = run_audit("dod", str(spec_dir))
        self.assertEqual(code, 0)
        expected = [
            (1, "PROOF auto", "PASS"), (2, "PROOF manual", "MANUAL"),
            (3, "REGRESSION", "MANUAL"), (4, "COMPLETENESS", "PASS"),
            (5, "CONTRACT", "PASS"), (6, "SCOPE", "SKIPPED"),
            (7, "HYGIENE", "SKIPPED"), (8, "REVIEW", "MANUAL"),
            (9, "RULINGS", "MANUAL"), (10, "SIGN-OFF", "MANUAL"),
        ]
        for num, name, status in expected:
            self.assertIn(status, self.gate_row(out, num, name))
        self.assertIn("1/1 TCs green", out)
        self.assertIn("1/1 ticked, 1/1 landed, 0 in-progress", out)
        self.assertIn("VERDICT: MECHANICAL PASS — git gates 6, 7 SKIPPED", out)

    def test_unticked_tasks_fail_completeness_gate_4(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(
                Path(td), {"task.md": UNTICKED_TASK, "test.md": ""})
            with unittest.mock.patch.object(
                    audit.subprocess, "run", fake_run(check_stdout=GREEN_CHECK)), \
                 unittest.mock.patch.object(
                     audit, "proofs_data", return_value=EMPTY_PROOFS):
                code, out = run_audit("dod", str(spec_dir))
        self.assertEqual(code, 1)
        self.assertIn("0/1 ticked, 0/1 landed, 0 in-progress", out)
        self.assertIn("VERDICT: MECHANICAL FAIL — gate(s) 4;", out)

    def test_implemented_unticked_passes_completeness_gate_4(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(Path(td), {
                "task.md": UNTICKED_TASK.replace(
                    "- [ ] T001", "- [ ] T001 (implemented)"),
                "test.md": ""})
            with unittest.mock.patch.object(
                    audit.subprocess, "run", fake_run(check_stdout=GREEN_CHECK)), \
                 unittest.mock.patch.object(
                     audit, "proofs_data", return_value=EMPTY_PROOFS):
                code, out = run_audit("dod", str(spec_dir))
        self.assertEqual(code, 0)
        self.assertIn("0/1 ticked, 1/1 landed, 0 in-progress", out)

    def test_failing_auto_proof_fails_gate_1(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(
                Path(td), {"task.md": TICKED_TASK, "test.md": FAILING_TC})
            with unittest.mock.patch.object(
                    audit.subprocess, "run", fake_run(check_stdout=GREEN_CHECK)):
                code, out = run_audit("dod", str(spec_dir))
        self.assertEqual(code, 1)
        self.assertIn("0/1 TCs green", out)
        self.assertIn("VERDICT: MECHANICAL FAIL — gate(s) 1;", out)

    def test_broken_contract_fails_gate_5(self):
        bad = ("  FAIL  missing/empty: spec.md\n"
               "  FAIL  missing/empty: plan.md\n"
               "PASS (2 fail, 1 warn)\n")
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(
                Path(td), {"task.md": TICKED_TASK, "test.md": ""})
            with unittest.mock.patch.object(
                    audit.subprocess, "run", fake_run(check_stdout=bad)), \
                 unittest.mock.patch.object(
                     audit, "proofs_data", return_value=EMPTY_PROOFS):
                code, out = run_audit("dod", str(spec_dir))
        self.assertEqual(code, 1)
        self.assertIn("FAIL", self.gate_row(out, 5, "CONTRACT"))
        self.assertIn("check.py: 2 fail, 1 warn", out)
        self.assertIn("VERDICT: MECHANICAL FAIL — gate(s) 5;", out)

    def test_absent_proofs_read_as_no_auto_tcs(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(Path(td), {"task.md": TICKED_TASK})  # no test.md
            with unittest.mock.patch.object(
                    audit.subprocess, "run", fake_run(check_stdout=GREEN_CHECK)):
                code, out = run_audit("dod", str(spec_dir))
        self.assertEqual(code, 0)
        self.assertIn("no auto TCs (n/a)", out)
        self.assertIn("0 observation TC(s)", out)


class DodFailClosedTests(unittest.TestCase):
    """FR-007 / TC-007: a checker that cannot start, times out, or
    delivers no verdict line fails its gate closed — exit 1 plus a
    concise diagnostic — instead of reading its own silence as a green
    gate, and every failed proof is named: id in the gate row, verdict
    line under the table. Proof-side timeout/crash/nonzero ride gate 1."""

    def run_dod(self, files=None, check_stdout=GREEN_CHECK, **run_kw):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(
                Path(td),
                files or {"task.md": TICKED_TASK, "test.md": PASSING_TC})
            with unittest.mock.patch.object(
                    audit.subprocess, "run", fake_run(check_stdout=check_stdout,
                                                      **run_kw)):
                return run_audit("dod", str(spec_dir))

    def test_checker_cannot_start_fails_gate_closed(self):
        code, out = self.run_dod(
            check_raises=OSError(2, "No such file or directory"))
        self.assertEqual(code, 1)
        self.assertIn("FAIL", find_gate_row(out, 5, "CONTRACT"))
        self.assertIn("check.py could not start", out)

    def test_checker_timeout_fails_gate_closed(self):
        code, out = self.run_dod(
            check_raises=subprocess.TimeoutExpired("check.py", 120))
        self.assertEqual(code, 1)
        self.assertIn("FAIL", find_gate_row(out, 5, "CONTRACT"))
        self.assertIn("timed out", out)

    def test_crashed_checker_without_verdict_fails_gate_closed(self):
        code, out = self.run_dod(check_stdout="", check_rc=1,
                                 check_stderr="TypeError: bad doc shape\n")
        self.assertEqual(code, 1)
        self.assertIn("FAIL", find_gate_row(out, 5, "CONTRACT"))
        self.assertIn("no verdict", out)
        self.assertIn("TypeError: bad doc shape", out)
        self.assertNotIn("check.py: 0 fail, 0 warn", out)  # the green read of silence

    def test_zero_rc_without_verdict_line_also_fails_closed(self):
        code, out = self.run_dod(check_stdout="unexpected shape\n", check_rc=0)
        self.assertEqual(code, 1)
        self.assertIn("FAIL", find_gate_row(out, 5, "CONTRACT"))
        self.assertIn("no verdict", out)

    def test_failing_proof_named_in_gate_row_and_under_table(self):
        code, out = self.run_dod(
            files={"task.md": TICKED_TASK, "test.md": FAILING_TC})
        self.assertEqual(code, 1)
        self.assertIn("failed: TC-001", find_gate_row(out, 1, "PROOF auto"))
        self.assertIn("TC-001  python3", out)  # verdict line: id + command

    def test_proof_timeout_fails_closed_and_names_tc(self):
        code, out = self.run_dod(
            proof_raises=subprocess.TimeoutExpired("proof", 120))
        self.assertEqual(code, 1)
        self.assertIn("FAIL", find_gate_row(out, 1, "PROOF auto"))
        self.assertIn("TIMEOUT", out)
        self.assertIn("TC-001", out)

    def test_proof_cannot_start_fails_closed_and_names_tc(self):
        code, out = self.run_dod(proof_raises=OSError(8, "Exec format error"))
        self.assertEqual(code, 1)
        self.assertIn("FAIL", find_gate_row(out, 1, "PROOF auto"))
        self.assertIn("ERROR", out)
        self.assertIn("Exec format error", out)
        self.assertIn("TC-001", out)


class DodGate4DelegationTests(unittest.TestCase):
    """SPECSTATE-003 (graph-engine user-testing round 1): dod gate 4 must
    compute its totals through specstate.task_entries — the one canonical
    task parser check.py also reads with — never a second inline copy of
    the '## '-split / phase-filter / checkbox-block parse shape."""

    def test_gate4_feeds_the_file_through_specstate_task_entries(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(
                Path(td), {"task.md": TICKED_TASK, "test.md": PASSING_TC})
            calls = []

            def spy(task_md):
                calls.append(task_md)
                return specstate.task_entries(task_md)

            with unittest.mock.patch.object(
                    audit.subprocess, "run", fake_run(check_stdout=GREEN_CHECK)), \
                 unittest.mock.patch.object(audit, "task_entries", spy):
                code, out = run_audit("dod", str(spec_dir))
        self.assertEqual(calls, [TICKED_TASK])  # the file's exact text, once
        self.assertEqual(code, 0)
        self.assertIn("1/1 ticked, 1/1 landed, 0 in-progress", out)

    def test_gate4_counts_come_from_the_entries_not_a_reparse(self):
        """The detail line and gate status reflect the entries task_entries
        returned, even when they disagree with a re-parse of the file —
        proof the totals are derived from the shared parser's return value."""
        with tempfile.TemporaryDirectory() as td:
            spec_dir = make_spec(Path(td), {"task.md": UNTICKED_TASK})
            synthetic = [specstate.TaskEntry(
                id="T001", phase=1, block="- [x] T001: synthetic",
                first_line="- [x] T001: synthetic", done=True, claimed=False,
                struck=False, parallel=False, after=[], fix_round=None)]
            with unittest.mock.patch.object(
                    audit.subprocess, "run", fake_run(check_stdout=GREEN_CHECK)), \
                 unittest.mock.patch.object(
                     audit, "proofs_data", return_value=EMPTY_PROOFS), \
                 unittest.mock.patch.object(
                     audit, "task_entries", return_value=synthetic):
                code, out = run_audit("dod", str(spec_dir))
        self.assertEqual(code, 0)
        self.assertIn("1/1 ticked, 1/1 landed, 0 in-progress", out)  # the file is UNTICKED
        self.assertNotIn("0/1 ticked", out)

    def test_no_second_task_entries_parser_in_audit_source(self):
        """SPECSTATE-003's literal contract: the extracted parser exists
        only in specstate.py — audit.py keeps none of its parse signatures."""
        source = (SKILL / "scripts" / "audit.py").read_text(encoding="utf-8")
        self.assertNotIn('re.split(r"^## "', source)          # phase-section scan
        self.assertNotIn('startswith("phase")', source)       # phase filter
        self.assertNotIn('re.split(r"^(?=- \\[)"', source)    # checkbox-block split


class MainArgvTests(unittest.TestCase):
    """main(argv) accepts args directly — the same in-process capability
    check.py's main() gained (see its MainArgvTests for the shared
    rationale). The CLI path (argv=None, reading sys.argv) must keep
    behaving identically. No git call runs for real (file docstring):
    every case here runs under fake_run, like the rest of this file."""

    def test_direct_argv_matches_cli_path(self):
        with unittest.mock.patch.object(audit.subprocess, "run", fake_run()):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = audit.main(["clean"])
            cli_code, cli_out = run_audit("clean")
        self.assertEqual(code, 0, buf.getvalue())
        self.assertEqual(code, cli_code)
        self.assertEqual(buf.getvalue(), cli_out)

    def test_direct_argv_ignores_ambient_sys_argv(self):
        # A leaking implementation (main reading sys.argv despite a
        # passed-in argv) would misparse this dangling ambient --repo
        # (no value follows) and return 2 instead of running "clean".
        with unittest.mock.patch.object(audit.subprocess, "run", fake_run()), \
             unittest.mock.patch.object(
                 sys, "argv", ["audit.py", "clean", "--repo"]):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = audit.main(["clean"])
        self.assertEqual(code, 0, buf.getvalue())

    def test_none_argv_still_reads_sys_argv(self):
        with unittest.mock.patch.object(sys, "argv", ["audit.py"]):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = audit.main()
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
