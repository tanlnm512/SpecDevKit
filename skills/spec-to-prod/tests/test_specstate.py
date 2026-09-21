"""Tests for scripts/specstate.py — the shared doc-state parsers.

specstate.py is the extraction of every doc-state parser check.py's
monolithic main() and audit.py used to inline: spec Status, task entries
(including the implemented marker), the Before-audit, Closing-audit, and
Delivered header lines, the survey baseline/items, the researcher-skip
marker, next-free-ID allocation, ID definitions, and the git availability
probes. Pure functions, stdlib only, no CLI: importing the module must
produce no output and write nothing (asserted here, SPECSTATE-001), and
every parser gets a representative case plus its None/missing/empty edge
(SPECSTATE-007). check.py/audit.py rewiring is covered by the existing
suites — they must stay green unmodified.
"""

import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
FIXTURE = SKILL / "examples" / "mini-spec" / "specs" / "mini-spec"

_specstate_spec = importlib.util.spec_from_file_location(
    "specstate", SCRIPTS / "specstate.py"
)
specstate = importlib.util.module_from_spec(_specstate_spec)
_specstate_spec.loader.exec_module(specstate)


def write(tmp, name, text):
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


TASK_SAMPLE = """# Tasks: demo

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Before-audit**: pending — the orchestrator writes `passed @ <sha>` here

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1     | 2     | 0    |
| 2     | 2     | 1    |

## Phase 1: first milestone (FR-001)
- [ ] T001 [P] build the widget `src/widget.py` (FR-001)
      continuation line stays part of the entry
- [ ] T002 (after T001) wire it up (FR-001)

## Phase 2: second milestone (FR-002)
- [x] T003 polish (FR-002)
      done 2026-09-08 — pytest green
- [ ] T004 [P] (in-progress) (fix 2/5) retry the flaky bit (FR-002)
- [ ] T006 (implemented) landed, unticked until the plan-wide tick (FR-002)
- [ ] ~~T005~~ dropped 2026-09-08 (D-001)

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done
- a checkbox-shaped line outside a Phase section is not an entry
"""


class SpecStatusTests(unittest.TestCase):
    def test_reads_lifecycle_words(self):
        for word in ("draft", "approved", "active", "done"):
            self.assertEqual(specstate.spec_status(f"**Status**: {word}\n"), word)

    def test_case_is_normalized_and_backticks_tolerated(self):
        self.assertEqual(specstate.spec_status("**Status**: Draft\n"), "draft")
        self.assertEqual(specstate.spec_status("**Status**: `approved`\n"), "approved")

    def test_only_line_leading_bold_status_counts(self):
        self.assertIsNone(
            specstate.spec_status("prose mentioning **Status**: draft mid-line\n")
        )

    def test_missing_or_empty_text_reads_none(self):
        self.assertIsNone(specstate.spec_status("# Spec, no status line\n"))
        self.assertIsNone(specstate.spec_status(""))
        self.assertIsNone(specstate.spec_status("**Statusy**: draft\n"))


class TaskEntryTests(unittest.TestCase):
    def setUp(self):
        self.entries = specstate.task_entries(TASK_SAMPLE)
        self.by_id = {e.id: e for e in self.entries if e.id}

    def test_phase_sections_hold_the_entries(self):
        # The struck/dropped form (`- [ ] ~~T005~~ …`) has no plain leading
        # T-ID, so — exactly like the parser it was extracted from — its
        # id reads None while the struck flag carries the drop signal.
        self.assertEqual([e.id for e in self.entries],
                         ["T001", "T002", "T003", "T004", "T006", None])
        self.assertEqual([e.phase for e in self.entries], [1, 1, 2, 2, 2, 2])
        # The Conventions section's checkbox-shaped prose is not an entry.
        self.assertNotIn("not an entry", {e.first_line for e in self.entries})

    def test_done_claimed_struck_flags(self):
        self.assertFalse(self.by_id["T001"].done)
        self.assertTrue(self.by_id["T003"].done)
        self.assertTrue(self.by_id["T004"].claimed)
        self.assertFalse(self.by_id["T001"].claimed)
        struck = self.entries[-1]
        self.assertTrue(struck.struck)
        self.assertIsNone(struck.id)
        self.assertFalse(self.by_id["T004"].struck)

    def test_parallel_after_fix_round(self):
        self.assertTrue(self.by_id["T001"].parallel)
        self.assertTrue(self.by_id["T004"].parallel)
        self.assertFalse(self.by_id["T002"].parallel)
        self.assertEqual(self.by_id["T002"].after, ["T001"])
        self.assertEqual(self.by_id["T001"].after, [])
        self.assertEqual(self.by_id["T004"].fix_round, 2)
        self.assertIsNone(self.by_id["T002"].fix_round)

    def test_continuation_lines_belong_to_the_entry(self):
        t1 = self.by_id["T001"]
        self.assertIn("continuation line stays part of the entry", t1.block)
        self.assertNotIn("Burndown", t1.block)

    def test_unnumbered_phase_header_still_yields_entries(self):
        entries = specstate.task_entries("## Phase X: unnumbered\n- [ ] T090 go\n")
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0].phase)
        self.assertEqual(entries[0].id, "T090")

    def test_empty_and_phaseless_text_yield_no_entries(self):
        self.assertEqual(specstate.task_entries(""), [])
        self.assertEqual(specstate.task_entries("# Tasks\nsome prose\n"), [])
        self.assertEqual(specstate.task_entries("## Burndown\n| 1 | 2 | 0 |\n"), [])

    def test_fixture_entries_parse(self):
        entries = specstate.task_entries(
            (FIXTURE / "task.md").read_text(encoding="utf-8"))
        self.assertEqual([e.id for e in entries], ["T001", "T002"])
        self.assertTrue(all(e.parallel and not e.done for e in entries))


class ImplementedMarkerTests(unittest.TestCase):
    """Landed work on an unticked entry parses as implemented — never as
    todo, claimed, ticked, or struck — and entries without the marker keep
    their legacy reading, so existing task files parse unchanged."""

    def test_implemented_is_none_of_the_legacy_states(self):
        by_id = {e.id: e for e in specstate.task_entries(TASK_SAMPLE) if e.id}
        impl = by_id["T006"]
        self.assertTrue(impl.implemented)
        self.assertFalse(impl.done)
        self.assertFalse(impl.claimed)
        self.assertFalse(impl.struck)

    def test_legacy_entries_without_the_marker_stay_unimplemented(self):
        by_id = {e.id: e for e in specstate.task_entries(TASK_SAMPLE) if e.id}
        self.assertFalse(by_id["T001"].implemented)  # plain todo
        self.assertFalse(by_id["T003"].implemented)  # ticked
        self.assertFalse(by_id["T004"].implemented)  # claimed + fix round

    def test_marker_coexists_with_fix_round_and_dependency_chain(self):
        text = ("## Phase 1: p (FR-001)\n"
                "- [ ] T001 (implemented) (fix 1/5) landed, then re-briefed\n"
                "- [ ] T002 (after T001) (implemented) also landed\n")
        e = {x.id: x for x in specstate.task_entries(text)}
        self.assertTrue(e["T001"].implemented)
        self.assertEqual(e["T001"].fix_round, 1)
        self.assertTrue(e["T002"].implemented)
        self.assertEqual(e["T002"].after, ["T001"])

    def test_direct_construction_defaults_to_unimplemented(self):
        entry = specstate.TaskEntry(
            id="T001", phase=1, block="- [ ] T001", first_line="- [ ] T001",
            done=False, claimed=False, struck=False, parallel=False,
            after=[], fix_round=None)
        self.assertFalse(entry.implemented)


class BeforeAuditStateTests(unittest.TestCase):
    def test_passed_with_sha_and_with_non_git_dash(self):
        self.assertEqual(
            specstate.before_audit_state("**Before-audit**: passed @ 3fa9c21\n"),
            "passed")
        self.assertEqual(
            specstate.before_audit_state("Before-audit: passed @ -\n"), "passed")

    def test_template_pending_line_is_not_passed(self):
        pending = "**Before-audit**: pending — the orchestrator writes `passed @ <sha>` here\n"
        self.assertEqual(specstate.before_audit_state(pending), "pending")

    def test_missing_line(self):
        self.assertEqual(specstate.before_audit_state("no audit line here\n"), "missing")
        self.assertEqual(specstate.before_audit_state(""), "missing")


class ClosingAuditStateTests(unittest.TestCase):
    def test_approved_with_sha_and_with_non_git_dash(self):
        self.assertEqual(
            specstate.closing_audit_state(
                "**Closing-audit**: approved @ 3fa9c21\n"),
            "approved")
        self.assertEqual(
            specstate.closing_audit_state("Closing-audit: approved @ -\n"),
            "approved")

    def test_placeholder_and_example_text_do_not_read_approved(self):
        pending = ("**Closing-audit**: pending — the orchestrator writes "
                   "`approved @ <sha>` here\n")
        self.assertEqual(specstate.closing_audit_state(pending), "pending")

    def test_missing_line(self):
        self.assertEqual(
            specstate.closing_audit_state("no closing record here\n"),
            "missing")
        self.assertEqual(specstate.closing_audit_state(""), "missing")


class DeliveryStateTests(unittest.TestCase):
    def test_commit_sha_and_backticks_record_delivered(self):
        self.assertEqual(
            specstate.delivery_state("**Delivered**: commit @ 3fa9c21\n"),
            ("delivered", "3fa9c21"))
        self.assertEqual(
            specstate.delivery_state("Delivered: commit @ `abc1234`\n"),
            ("delivered", "abc1234"))

    def test_dash_is_the_explicit_non_git_skip(self):
        self.assertEqual(specstate.delivery_state("Delivered: commit @ -\n"),
                         ("delivered", "-"))

    def test_template_pending_line_is_not_delivered(self):
        pending = ("**Delivered**: pending — the orchestrator writes "
                   "`commit @ <sha>` here\n")
        self.assertEqual(specstate.delivery_state(pending), ("pending", None))

    def test_malformed_commit_token_reads_pending_not_delivered(self):
        for bad in ("Delivered: commit @ abc12\n",     # too short for a sha
                    "Delivered: commit @ zz9c21\n",    # not hex
                    "Delivered: commit @ 3FA9C21\n"):  # shas are lowercase
            self.assertEqual(specstate.delivery_state(bad), ("pending", None),
                             bad)

    def test_missing_line(self):
        self.assertEqual(specstate.delivery_state("no delivery record\n"),
                         ("missing", None))
        self.assertEqual(specstate.delivery_state(""), ("missing", None))


class SurveyBaselineTests(unittest.TestCase):
    def test_fixture_baseline_parses_to_version_and_sha(self):
        survey = (FIXTURE / "survey.md").read_text(encoding="utf-8")
        self.assertEqual(specstate.survey_baseline(survey), ("mini-calc v1", "3fa9c21"))

    def test_backticked_sha_and_bold_header(self):
        self.assertEqual(
            specstate.survey_baseline("**Baseline**: v2 @ `abc1234`\n"),
            ("v2", "abc1234"))

    def test_placeholder_header_and_missing_header_read_none(self):
        self.assertIsNone(
            specstate.survey_baseline("**Baseline**: <version @ commit>\n"))
        self.assertIsNone(specstate.survey_baseline("# Survey, no baseline\n"))
        self.assertIsNone(specstate.survey_baseline(""))


class SurveyItemsTests(unittest.TestCase):
    SAMPLE = (
        'item S1: "add exists"\n  status:     DONE\n'
        'item S2: "multiply missing"\n  status:     TODO\n'
        'item S3: "no status line"\n'
        'item this line has no quoted description\n'
    )

    def test_items_extracted_with_statuses(self):
        items = specstate.survey_items(self.SAMPLE)
        self.assertEqual([(i.id, i.description, i.status) for i in items], [
            ("S1", "add exists", "DONE"),
            ("S2", "multiply missing", "TODO"),
            ("S3", "no status line", "unknown"),
        ])

    def test_malformed_blocks_skipped_not_raised(self):
        items = specstate.survey_items('garbage\nitem S4: "fine"\nstatus: PARTIAL\n')
        self.assertEqual([(i.id, i.status) for i in items], [("S4", "PARTIAL")])

    def test_empty_survey_yields_no_items(self):
        self.assertEqual(specstate.survey_items(""), [])
        self.assertEqual(specstate.survey_items("# Survey\n## Items\n"), [])

    def test_fixture_items_parse(self):
        items = specstate.survey_items(
            (FIXTURE / "survey.md").read_text(encoding="utf-8"))
        self.assertEqual([i.id for i in items], ["S1", "S2", "S3"])
        self.assertEqual([i.status for i in items], ["DONE", "TODO", "DONE"])


class ResearchStateTests(unittest.TestCase):
    MARKER = "not applicable — no open questions at Stage 0"

    def test_canonical_marker_is_byte_exact_em_dash(self):
        self.assertEqual(specstate.RESEARCH_SKIP_MARKER, self.MARKER)
        self.assertIn("\u2014", specstate.RESEARCH_SKIP_MARKER)
        self.assertNotIn("-", specstate.RESEARCH_SKIP_MARKER)
        # The fixture's marker line matches byte-for-byte.
        fixture_lines = (FIXTURE / "research.md").read_text(
            encoding="utf-8").splitlines()
        self.assertIn(self.MARKER, [l.strip() for l in fixture_lines])

    def test_marker_line_reads_skip_even_with_surrounding_prose(self):
        with tempfile.TemporaryDirectory() as td:
            p = write(Path(td), "research.md",
                      f"# Research: demo\n\n{self.MARKER}\n\nSome rationale.\n")
            self.assertEqual(specstate.research_state(p), "skip")
            self.assertEqual(specstate.research_state(str(p)), "skip")

    def test_real_content_reads_done(self):
        with tempfile.TemporaryDirectory() as td:
            p = write(Path(td), "research.md",
                      "## Questions\n### Q1\n- **source**: https://x — claim\n")
            self.assertEqual(specstate.research_state(p), "done")

    def test_empty_and_template_files_read_pending(self):
        with tempfile.TemporaryDirectory() as td:
            empty = write(Path(td), "empty.md", "")
            blank = write(Path(td), "blank.md", "   \n\n")
            template = write(Path(td), "template.md",
                             "# Research: <name>\n### <research question 1>\n")
            for p in (empty, blank, template):
                self.assertEqual(specstate.research_state(p), "pending", p)

    def test_missing_file_and_none_path_read_missing(self):
        self.assertEqual(specstate.research_state(Path("/nonexistent/research.md")),
                         "missing")
        self.assertEqual(specstate.research_state(None), "missing")

    def test_fixture_research_reads_skip(self):
        self.assertEqual(specstate.research_state(FIXTURE / "research.md"), "skip")


class NextIdsTests(unittest.TestCase):
    TEXTS = {
        "spec.md": "- **FR-001**: x\n- **FR-002**: y\n- AC1: a\n### US1 — s\n",
        "task.md": "- [x] T001 a\n- [ ] T002 (after T001) b\n",
        "test.md": "## TC-001 — case\n",
        "tech-spec.md": "### D-001: decision\n",
    }

    def test_next_free_ids_per_family(self):
        self.assertEqual(specstate.next_ids(self.TEXTS), {
            "FR": "FR-003", "AC": "AC2", "US": "US2",
            "T": "T003", "TC": "TC-002", "D": "D-002",
        })

    def test_empty_texts_allocate_first_ids(self):
        self.assertEqual(specstate.next_ids({}), {
            "FR": "FR-001", "AC": "AC1", "US": "US1",
            "T": "T001", "TC": "TC-001", "D": "D-001",
        })


class DefinedIdsTests(unittest.TestCase):
    TEXT = (
        "- **FR-001**: The system shall x\n"
        "- AC1: Given x\n"
        "### US1 — Story\n"
        "## TC-001 — Case\n"
        "### D-001: Decision\n"
        "a prose mention of FR-002 is not a definition\n"
    )

    def test_all_five_families_from_one_text(self):
        ids = specstate.defined_ids(self.TEXT)
        self.assertEqual(ids, {
            "FR": {"FR-001"}, "AC": {"AC1"}, "US": {"US1"},
            "TC": {"TC-001"}, "D": {"D-001"},
        })

    def test_mentions_are_not_definitions(self):
        self.assertNotIn("FR-002", specstate.defined_ids(self.TEXT)["FR"])

    def test_empty_text_yields_empty_families(self):
        self.assertEqual(specstate.defined_ids(""),
                         {"FR": set(), "AC": set(), "US": set(),
                          "TC": set(), "D": set()})


def fake_git_run(returncode=0, stdout=""):
    real = subprocess.run

    def fake(cmd, *a, **k):
        if cmd and cmd[0] == "git":
            return subprocess.CompletedProcess(cmd, returncode, stdout, "")
        return real(cmd, *a, **k)

    return fake


class GitHelperTests(unittest.TestCase):
    def test_git_available_true_only_on_clean_probe(self):
        with unittest.mock.patch.object(specstate.subprocess, "run",
                                        fake_git_run(returncode=0)):
            self.assertTrue(specstate.git_available(Path("/some/repo")))
        with unittest.mock.patch.object(specstate.subprocess, "run",
                                        fake_git_run(returncode=128)):
            self.assertFalse(specstate.git_available(Path("/some/repo")))

    def test_git_available_swallows_missing_binary(self):
        def raising(cmd, *a, **k):
            if cmd and cmd[0] == "git":
                raise FileNotFoundError(2, "No such file or directory", "git")
            raise AssertionError("unexpected non-git call")

        with unittest.mock.patch.object(specstate.subprocess, "run", raising):
            self.assertFalse(specstate.git_available(Path("/some/repo")))

    def test_head_sha_reads_short_head(self):
        with unittest.mock.patch.object(specstate.subprocess, "run",
                                        fake_git_run(stdout="abc1234\n")):
            self.assertEqual(specstate.head_sha(Path("/some/repo")), "abc1234")

    def test_head_sha_none_on_failure_or_empty(self):
        with unittest.mock.patch.object(specstate.subprocess, "run",
                                        fake_git_run(returncode=128)):
            self.assertIsNone(specstate.head_sha(Path("/some/repo")))
        with unittest.mock.patch.object(specstate.subprocess, "run",
                                        fake_git_run(stdout="  \n")):
            self.assertIsNone(specstate.head_sha(Path("/some/repo")))

    def test_diff_paths_reads_sorted_unique_paths(self):
        out = "repo/calc.py\nspecs/demo/survey.md\nrepo/calc.py\n"
        with unittest.mock.patch.object(specstate.subprocess, "run",
                                        fake_git_run(stdout=out)):
            self.assertEqual(
                specstate.diff_paths(Path("/some/repo"), "abc1234", "def5678"),
                ["repo/calc.py", "specs/demo/survey.md"])

    def test_diff_paths_none_on_git_failure(self):
        """rc != 0 (unknown sha, not a repo) is None — callers degrade to
        a full re-survey, never an empty-delta verdict."""
        with unittest.mock.patch.object(specstate.subprocess, "run",
                                        fake_git_run(returncode=128)):
            self.assertIsNone(
                specstate.diff_paths(Path("/some/repo"), "abc1234", "def5678"))

    def test_diff_paths_real_repo_lists_changed_files(self):
        """The sanctioned real-git probe: init, two commits, the changed
        file (and only it) sits between the two shas."""
        import os
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            env = dict(os.environ, GIT_AUTHOR_NAME="t",
                       GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                       GIT_COMMITTER_EMAIL="t@t")

            def g(*args):
                return subprocess.run(
                    ["git", "-C", td, *args], capture_output=True, text=True,
                    env=env)

            g("init", "-q")
            (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n")
            g("add", "-A")
            g("commit", "-qm", "base")
            base = specstate.head_sha(repo)
            (repo / "calc.py").write_text("def add(a, b):\n    return a - b\n")
            (repo / "new.py").write_text("x = 1\n")
            g("add", "-A")
            g("commit", "-qm", "drift")
            head = specstate.head_sha(repo)
            self.assertEqual(specstate.diff_paths(repo, base, head),
                             ["calc.py", "new.py"])
            self.assertEqual(specstate.diff_paths(repo, head, head), [])


    def test_real_workspace_probe_is_non_git(self):
        # The sanctioned rc-128 probe: a workspace that is genuinely
        # non-git. A temp dir outside any repo — the in-repo fixture can
        # no longer serve (SpecDevKit itself is a git repo, so the probe
        # resolves the parent .git and the old premise stopped holding).
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(specstate.git_available(Path(td)))
            self.assertIsNone(specstate.head_sha(Path(td)))


class ModuleShapeTests(unittest.TestCase):
    """SPECSTATE-001: stdlib-only, importable, no CLI side effects."""

    def test_import_produces_no_output_and_writes_nothing(self):
        r = subprocess.run(
            [sys.executable, "-c", "import specstate; print('ok')"],
            capture_output=True, text=True, cwd=SCRIPTS, timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "ok\n")
        self.assertEqual(r.stderr, "")

    def test_imports_are_stdlib_only(self):
        source = (SCRIPTS / "specstate.py").read_text(encoding="utf-8")
        mods = set(re.findall(r"^(?:from|import)\s+([a-zA-Z_][\w.]*)", source, re.M))
        roots = {m.split(".")[0] for m in mods}
        self.assertTrue(roots)
        self.assertLessEqual(roots, {
            "__future__", "pathlib", "re", "subprocess", "sys", "typing",
        }, f"non-stdlib import found: {roots}")

    def test_tooling_scripts_import_specstate(self):
        for script in ("check.py", "audit.py"):
            source = (SCRIPTS / script).read_text(encoding="utf-8")
            self.assertRegex(source, r"from specstate import|import specstate",
                             f"{script} does not import specstate")


if __name__ == "__main__":
    unittest.main(verbosity=2)
