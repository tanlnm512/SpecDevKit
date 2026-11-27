#!/usr/bin/env python3
"""Unit tests for the shared review oracle.

Real temp git repos, not mocks: the oracle's contract is repo state in,
JSON out. Error paths must fail loudly (exit 1 + status error), never
silently proceed."""

import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "review_orchestrator.py"


def run(args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


def ok(args):
    r = run(args)
    assert r.returncode == 0, f"expected ok, got {r.returncode}: {r.stdout}{r.stderr}"
    return json.loads(r.stdout)


def err(args):
    r = run(args)
    assert r.returncode == 1, f"expected exit 1, got {r.returncode}: {r.stdout}"
    d = json.loads(r.stdout)
    assert d["status"] == "error", f"expected status error: {d}"
    return d["error"]


def refused(args):
    r = run(args)
    assert r.returncode == 1, f"expected exit 1, got {r.returncode}: {r.stdout}{r.stderr}"
    d = json.loads(r.stdout)
    assert d["status"] == "error", f"expected status error: {d}"
    assert not {"tracked", "reply"} & set(d), f"a refusal carries nothing to read: {d}"
    return d


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def make_repo():
    d = tempfile.TemporaryDirectory(prefix="oracle-")
    repo = Path(d.name)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "T")
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    return d, repo


class ScopeTests(unittest.TestCase):
    def test_diff_scope_reads_files_added_and_clean(self):
        holder, repo = make_repo()
        with holder:
            (repo / "app.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            (repo / "new.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            d = ok(["scope", "--target", "diff", "--base", "HEAD", "--repo", str(repo)])
            self.assertEqual(d["mode"], "diff")
            self.assertEqual(d["files"], ["app.py", "new.py"])
            self.assertEqual(d["untracked"], ["new.py"])
            self.assertEqual(d["added"], 3)
            self.assertFalse(d["clean"])

    def test_default_diff_scope_sees_staged_changes_with_a_concrete_base(self):
        holder, repo = make_repo()
        with holder:
            (repo / "app.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            git(repo, "add", "-A")
            d = ok(["scope", "--target", "diff", "--repo", str(repo)])
            self.assertEqual(d["base"], "HEAD")
            self.assertEqual(d["files"], ["app.py"])
            run_dir = ok(["run-init", "--target", "diff", "--repo", str(repo)])["run_dir"]
            ask = ok(["ask", "--kind", "review", "--ctx", json.dumps(
                {"base": d["base"], "run_dir": run_dir, "files_n": 1, "lines": 1, "over_cap": False,
                 "lens": {"label": "correctness", "focus": "f."}, "gate_line": "ok"})])["ask"]
            # the base the ask is rendered against decides what the reader reads
            diff = Path(run_dir) / "reader-files" / "diff.patch"
            self.assertIn(f"`{diff}`", ask)
            self.assertIn("+y = 2\n", diff.read_text(encoding="utf-8"))

    def test_untracked_cache_and_binary_files_stay_out_of_scope(self):
        holder, repo = make_repo()
        with holder:
            (repo / "__pycache__").mkdir()
            (repo / "__pycache__" / "app.cpython-312.pyc").write_bytes(b"\x00\x01")
            (repo / "node_modules" / "dep").mkdir(parents=True)
            (repo / "node_modules" / "dep" / "index.js").write_text("a = 1\n", encoding="utf-8")
            (repo / "logo.png").write_bytes(b"\x89PNG\x00\x00")
            (repo / "new.py").write_text("a = 1\n", encoding="utf-8")
            d = ok(["scope", "--target", "diff", "--repo", str(repo)])
            self.assertEqual(d["untracked"], ["new.py"])
            self.assertEqual(d["files"], ["new.py"])
            self.assertEqual(d["untracked_skipped"], ["node_modules/dep/index.js"])

    def test_branch_scope_no_base_stage(self):
        holder, repo = make_repo()
        with holder:
            # no main/master anywhere and no origin: nothing resolves
            git(repo, "branch", "-m", "feature-x")
            r = run(["scope", "--target", "branch", "--repo", str(repo)])
            d = json.loads(r.stdout)
            self.assertEqual(d.get("stage"), "branch-no-base")

    def test_branch_scope_resolves_merge_base_and_count(self):
        holder, repo = make_repo()
        with holder:
            git(repo, "checkout", "-qb", "feature")
            (repo / "new.py").write_text("print('hi')\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "feature work")
            d = ok(["scope", "--target", "branch", "--repo", str(repo)])
            self.assertEqual(d["mode"], "branch")
            self.assertEqual(d["base"], "main")
            self.assertEqual(d["commit_count"], 1)
            self.assertEqual(d["files"], ["new.py"])

    def test_bad_base_fails_loudly_with_a_stage(self):
        holder, repo = make_repo()
        with holder:
            r = run(["scope", "--target", "diff", "--base", "no-such-ref",
                     "--repo", str(repo)])
            self.assertEqual(r.returncode, 1)
            d = json.loads(r.stdout)
            self.assertEqual(d["status"], "error")
            self.assertEqual(d["stage"], "base-unresolved")
            self.assertEqual(d["base"], "no-such-ref")

    def test_project_scope_filters_and_shards(self):
        holder, repo = make_repo()
        with holder:
            (repo / "pkg").mkdir()
            for i in range(4):
                (repo / "pkg" / f"m{i}.py").write_text("x = 1\n", encoding="utf-8")
            (repo / "pkg" / "skip.lock").write_text("", encoding="utf-8")
            (repo / "vendor").mkdir()
            (repo / "vendor" / "v.py").write_text("", encoding="utf-8")
            (repo / "dist").mkdir()
            (repo / "dist" / "bundle.js").write_text("", encoding="utf-8")
            (repo / "src" / "redist").mkdir(parents=True)
            (repo / "src" / "redist" / "core.py").write_text("y = 2\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "files")
            d = ok(["scope", "--target", "project", "--repo", str(repo)])
            names = [f for f in d["files"]]
            self.assertNotIn("pkg/skip.lock", names)
            self.assertNotIn("vendor/v.py", names)
            self.assertIn("app.py", names)
            # exclusion matches whole path segments: dist/ never swallows src/redist/
            self.assertIn("src/redist/core.py", names)
            self.assertEqual(sorted(d["excluded"]), ["dist/bundle.js", "vendor/v.py"])
            self.assertFalse(d["confirm_before_spawn"])
            self.assertEqual(d["candidates"], len(names))
            self.assertTrue(all(isinstance(p, list) for p in d["parts"]))

    def test_include_gate_folds_gate_rows_into_scope(self):
        holder, repo = make_repo()
        with holder:
            d = ok(["scope", "--target", "diff", "--base", "HEAD",
                    "--repo", str(repo), "--include-gate"])
            self.assertIn("gate", d)
            self.assertIn("rows", d["gate"])
            self.assertIn("note", d["gate"])


class GateTests(unittest.TestCase):
    def test_gate_green_on_repo_with_no_detected_checks(self):
        holder, repo = make_repo()
        with holder:
            d = ok(["gate", "--repo", str(repo), "--base", "HEAD"])
            self.assertEqual(d["rows"], [])
            self.assertTrue(d["green"])
            self.assertIn("no mechanical floor", d["note"].lower())

    def test_builtin_rows_alone_are_no_mechanical_floor(self):
        holder, repo = make_repo()
        with holder:
            (repo / "pom.xml").write_text("<project/>\n", encoding="utf-8")
            (repo / "Main.java").write_text("class Main {}\n", encoding="utf-8")
            d = ok(["gate", "--repo", str(repo), "--base", "HEAD"])
            self.assertTrue(d["rows"])  # the built-in secret scan still ran
            self.assertIn("No repo checks were detected", d["note"])
            self.assertNotIn("all passed", d["note"])
            self.assertEqual(d["repo_checks"], 0)

    def test_gate_red_when_a_detected_check_fails(self):
        holder, repo = make_repo()
        with holder:
            (repo / "Makefile").write_text("test:\n\texit 1\n", encoding="utf-8")
            (repo / "t.py").write_text("x = 1\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "red gate")
            d = ok(["gate", "--repo", str(repo), "--base", "HEAD"])
            self.assertFalse(d["green"])
            self.assertIn("did NOT all pass", d["note"])

    def test_pr_ci_checks_are_gate_rows_and_red_ci_fails_the_gate(self):
        holder, repo = make_repo()
        with holder, tempfile.TemporaryDirectory() as bindir:
            gh = Path(bindir) / "gh"
            gh.write_text(
                "#!/bin/sh\n"
                'if [ "$1 $2" = "run view" ]; then\n'
                "  echo '{\"jobs\": [{\"name\": \"lint\", \"conclusion\": \"failure\", "
                "\"steps\": [{\"name\": \"Set up job\", \"number\": 1, \"conclusion\": \"success\"}, "
                "{\"name\": \"Run lint\", \"number\": 2, \"conclusion\": \"failure\"}]}]}'\n"
                "  exit 0\n"
                "fi\n"
                "echo '[{\"name\":\"build\",\"bucket\":\"pass\",\"link\":\"\"},"
                "{\"name\":\"lint\",\"bucket\":\"fail\","
                "\"link\":\"https://github.com/acme/widget/actions/runs/4123\"}]'\n")
            gh.chmod(0o755)
            env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}
            r = subprocess.run([sys.executable, str(SCRIPT), "gate", "--repo", str(repo),
                                "--base", "HEAD", "--pr", "7"],
                               capture_output=True, text=True, env=env)
            d = json.loads(r.stdout)
            ci = {g["name"]: g["status"] for g in d["rows"] if g["source"] == "ci"}
            self.assertEqual(ci, {"CI: build": "pass", "CI: lint": "fail"})
            lint = next(g for g in d["rows"] if g["name"] == "CI: lint")
            self.assertEqual(lint["class"], "code")
            self.assertEqual(lint["failedStep"], "Run lint")
            self.assertFalse(d["green"])
            self.assertIn("CI did NOT pass — failing: CI: lint", d["note"])

    def test_pr_ci_cancelled_run_is_infrastructure_and_stands(self):
        holder, repo = make_repo()
        with holder, tempfile.TemporaryDirectory() as bindir:
            gh = Path(bindir) / "gh"
            # no run view behind it either — the class comes from the bucket
            gh.write_text(
                "#!/bin/sh\n"
                "echo '[{\"name\":\"build\",\"bucket\":\"cancel\","
                "\"link\":\"https://github.com/acme/widget/actions/runs/4123\"},"
                "{\"name\":\"lint\",\"bucket\":\"fail\",\"link\":\"\"}]'\n")
            gh.chmod(0o755)
            env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}
            r = subprocess.run([sys.executable, str(SCRIPT), "gate", "--repo", str(repo),
                                "--base", "HEAD", "--pr", "7"],
                               capture_output=True, text=True, env=env)
            d = json.loads(r.stdout)
            by_name = {g["name"]: g for g in d["rows"] if g["source"] == "ci"}
            build = by_name["CI: build"]
            self.assertEqual(build["status"], "infrastructure")
            self.assertEqual(build["class"], "infrastructure")
            self.assertEqual(build["exit_code"], 0)
            self.assertEqual(build["rerun"], "gh run rerun 4123 --failed")
            lint = by_name["CI: lint"]
            self.assertEqual(lint["class"], "unknown")
            self.assertEqual(lint["status"], "unknown")
            self.assertIsNone(lint.get("rerun"))
            # neither row fails the gate — but neither is green-washed
            self.assertTrue(d["green"])
            self.assertIn("standing red, not failing the gate: "
                          "CI: build; CI: lint", d["note"])
            self.assertIn("merge floors at human", d["note"])

    def test_pr_ci_setup_failure_is_infrastructure_test_failure_is_code(self):
        holder, repo = make_repo()

        def stub_with(steps_json):
            return ("#!/bin/sh\n"
                    'if [ "$1 $2" = "run view" ]; then\n'
                    "  echo '{\"jobs\": [{\"name\": \"ci\", \"conclusion\": \"failure\", "
                    "\"steps\": [" + steps_json + "]}]}'\n"
                    "  exit 0\n"
                    "fi\n"
                    "echo '[{\"name\":\"ci\",\"bucket\":\"fail\","
                    "\"link\":\"https://github.com/acme/widget/actions/runs/4123\"}]'\n")

        setup = ('{"name": "Set up job", "number": 1, "conclusion": "failure"}, '
                 '{"name": "Run tests", "number": 2, "conclusion": "skipped"}')
        tests = ('{"name": "Set up job", "number": 1, "conclusion": "success"}, '
                 '{"name": "Run tests", "number": 2, "conclusion": "failure"}')
        for steps_json, want in ((setup, "infrastructure"), (tests, "code")):
            with self.subTest(first_failure=want), \
                 tempfile.TemporaryDirectory() as bindir:
                gh = Path(bindir) / "gh"
                gh.write_text(stub_with(steps_json))
                gh.chmod(0o755)
                env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}
                r = subprocess.run([sys.executable, str(SCRIPT), "gate",
                                    "--repo", str(repo), "--base", "HEAD",
                                    "--pr", "7"],
                                   capture_output=True, text=True, env=env)
                d = json.loads(r.stdout)
                ci = next(g for g in d["rows"] if g["source"] == "ci")
                self.assertEqual(ci["class"], want)
                self.assertEqual(ci["failedStep"],
                                 "Set up job" if want == "infrastructure"
                                 else "Run tests")
                self.assertEqual(d["green"], want == "infrastructure")

    def test_gate_on_this_kit_repo_detects_its_checks(self):
        kit_root = SCRIPT.parents[2]  # CWD-independent: run.sh cds into the skill
        # --tree scans every tracked *.sh, so detection is provable on a
        # clean checkout; --base HEAD sees an empty diff there (zero rows).
        d = ok(["gate", "--tree", "--repo", str(kit_root)])
        self.assertTrue(any("bash -n" in g["name"] or "secret" in g["name"]
                            for g in d["rows"]))
        self.assertTrue(d["green"])


class FixGuardTests(unittest.TestCase):
    def test_fix_check_flags_test_weakening_and_aborts_on_moved_head(self):
        holder, repo = make_repo()
        with holder:
            (repo / "tests").mkdir()
            (repo / "tests" / "test_app.py").write_text(
                "def test_x():\n    assert 1 == 1\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "tests")
            git(repo, "config", "diff.noprefix", "true")
            snap = ok(["fix-snapshot", "--repo", str(repo)])
            (repo / "tests" / "test_app.py").write_text(
                "import pytest\n@pytest.mark.skip\ndef test_x():\n    pass\n", encoding="utf-8")
            check = ["fix-check", "--repo", str(repo), "--head", snap["head"],
                     "--stash-count", str(snap["stash_count"]), "--tree", snap["tree"]]
            hunks = ok(check)["test_hunks"]
            self.assertEqual(hunks[0]["path"], "tests/test_app.py")
            self.assertEqual(hunks[0]["removed_asserts"], ["assert 1 == 1"])
            self.assertEqual(hunks[0]["added_skips"], ["@pytest.mark.skip"])
            git(repo, "commit", "-qam", "fixer committed")
            d = json.loads(run(check).stdout)
            self.assertEqual(d["stage"], "fixer-moved-head")

    def test_fix_check_sees_a_fixer_edit_inside_an_untracked_test_file(self):
        holder, repo = make_repo()
        with holder:
            (repo / "test_new.py").write_text(
                "def test_x():\n    assert 1 == 1\n", encoding="utf-8")
            snap = ok(["fix-snapshot", "--repo", str(repo)])
            (repo / "test_new.py").write_text(
                "def test_x():\n    pass\n", encoding="utf-8")
            hunks = ok(["fix-check", "--repo", str(repo), "--head", snap["head"],
                        "--stash-count", str(snap["stash_count"]),
                        "--tree", snap["tree"]])["test_hunks"]
            self.assertEqual(hunks[0]["path"], "test_new.py")
            self.assertEqual(hunks[0]["removed_asserts"], ["assert 1 == 1"])


class ShardTests(unittest.TestCase):
    def test_sharding_is_deterministic_and_directory_coherent(self):
        files = [f"src/a/{i}.py" for i in range(5)] + [f"src/b/{i}.py" for i in range(5)]
        sizes = {f: 10 for f in files}
        d1 = ok(["shard", "--files-json", json.dumps(files),
                 "--sizes-json", json.dumps(sizes), "--max-files", "3"])
        d2 = ok(["shard", "--files-json", json.dumps(files),
                 "--sizes-json", json.dumps(sizes), "--max-files", "3"])
        self.assertEqual(d1["parts"], d2["parts"])
        # path-sorted contiguous runs; a tiny trailing run merges into the
        # previous part, so the last part may exceed max_files
        self.assertEqual(sorted(sum(d1["parts"], [])), sorted(files))
        self.assertTrue(all(len(p) <= 3 for p in d1["parts"][:-1]))
        self.assertTrue(d1["part_labels"])

    def test_tiny_tail_merges_into_previous_part(self):
        files = ["a.py", "b.py", "c.py"]
        sizes = {"a.py": 1000, "b.py": 1000, "c.py": 10}
        d = ok(["shard", "--files-json", json.dumps(files),
                "--sizes-json", json.dumps(sizes), "--budget", "1000"])
        self.assertEqual(len(d["parts"]), 2)
        self.assertIn("c.py", d["parts"][1])


class IdTests(unittest.TestCase):
    def test_id_next_sequence(self):
        self.assertEqual(ok(["id-next", "--prefix", "F", "--used", "0"])["id"], "F-1")
        self.assertEqual(ok(["id-next", "--prefix", "F", "--used", "4"])["id"], "F-5")

    def test_negative_used_fails(self):
        err(["id-next", "--prefix", "F", "--used", "-1"])


FINDINGS_MD = """# Code review — HEAD (2 files, ~10 added lines)

### [F-1 · HIGH · verified · correctness] off-by-one in loop
- where: `src/app.py:14`
- evidence: `for i in range(n)` but the list has n+1 items
- impact: crashes on the last element

### [LOW · unconfirmed · quality · fix: fixed] stale comment
- where: `src/app.py:2`
- evidence: comment mentions removed function

### [F-2 · MEDIUM · verified · security · fix: pending] sql string built from input
- where: `src/db.py:21`
- evidence: `cursor.execute("... " + uid)`
"""

# a saved report goes in declared as one
SAVED = ["findings-parse", "--saved-report", "--text"]


class FindingsParseTests(unittest.TestCase):
    def test_markdown_report_parses_ids_statuses_and_fixes(self):
        d = ok([*SAVED, FINDINGS_MD])
        tracked = d["tracked"]
        self.assertEqual(len(tracked), 2)  # the fixed one is dropped
        self.assertEqual(tracked[0]["finding"]["id"], "F-1")  # high sorts first
        self.assertEqual(tracked[0]["finding"]["severity"], "high")
        self.assertEqual(tracked[1]["finding"]["id"], "F-2")
        self.assertEqual(tracked[1]["finding"]["severity"], "medium")
        self.assertEqual(tracked[1]["fix"], "pending")

    def test_legacy_heading_mints_carried_ids(self):
        legacy = "### [MEDIUM · verified · quality] bad name\n- where: `a.py:1`\n- evidence: x\n"
        d = ok([*SAVED, legacy])
        self.assertEqual(d["tracked"][0]["finding"]["id"], "carried-1")

    def test_json_payload_normalizes_and_drops_fixed(self):
        payload = json.dumps([
            {"id": "F-9", "where": "a.py:1", "what": "x", "severity": "high"},
            {"id": "F-8", "where": "b.py:1", "what": "y", "severity": "low",
             "fixStatus": "fixed"},
        ])
        d = ok([*SAVED, payload])
        self.assertEqual(len(d["tracked"]), 1)
        self.assertEqual(d["tracked"][0]["finding"]["id"], "F-9")
        self.assertEqual(d["tracked"][0]["finding"]["severity"], "high")
        # no recorded confirmation is never promoted to verified
        self.assertEqual(d["tracked"][0]["finding"]["confirmation"]["status"], "unconfirmed")

    def test_a_reply_is_parsed_only_after_its_tools_report_checks_out(self):
        # every reply opens with its tools report: handed over with its
        # role, the report is checked against the brief before a finding
        # is read, and one that holds parses exactly as the bare payload
        payload = json.dumps([{"id": "F-9", "where": "a.py:1", "what": "x",
                               "severity": "high"}])
        parse = ["findings-parse", "--role", "correctness", "--text"]
        bare = ok([*SAVED, payload])
        for lead in ("tools: Read, Grep, Glob\n", "> tools: read, grep, glob\n",
                     "Tools: `Read`, `Grep`, `Glob`.\n"):
            with self.subTest(lead=lead):
                self.assertEqual(ok([*parse, lead + payload]), bare)
        self.assertEqual(ok([*parse, "tools: Read, Grep, Glob\n" + FINDINGS_MD]),
                         ok([*SAVED, FINDINGS_MD]))
        for lead, reported, missing in (("tools: Read\n", ["Read"], ["Grep", "Glob"]),
                                        ("tools: \n", [], ["Read", "Grep", "Glob"]),
                                        ("", [], ["Read", "Grep", "Glob"])):
            with self.subTest(lead=lead):
                d = refused([*parse, lead + FINDINGS_MD])
                self.assertEqual((d["role"], d["reported"], d["missing"]),
                                 ("correctness", reported, missing))
                for named in ("correctness", *missing):
                    self.assertIn(named, d["error"])

    def test_a_reply_handed_over_without_its_role_is_refused(self):
        # declared a saved report, a reply that opens with a tools report is
        # still a reply: nothing is read until its role is named
        d = refused(["findings-parse", "--saved-report", "--text",
                     "tools: Read, Grep, Glob\n" + FINDINGS_MD])
        self.assertEqual(d["stage"], "handshake")
        self.assertIn("--role", d["error"])
        self.assertNotIn("--saved-report", d["error"])

    def test_an_undeclared_payload_is_refused_naming_both_kinds(self):
        # a reply with no tools line and no --role is the omission the gate exists to stop
        for text in (FINDINGS_MD, json.dumps([{"id": "F-9", "where": "a.py:1", "what": "x"}])):
            with self.subTest(shape=text.lstrip()[:1]):
                d = refused(["findings-parse", "--text", text])
                self.assertEqual(d["stage"], "handshake")
                self.assertNotIn("tracked", d)
                for flag in ("--role", "--saved-report"):
                    self.assertIn(flag, d["error"])

    def test_garbage_fails_loudly(self):
        msg = err([*SAVED, "neither json nor a report"])
        self.assertIn("neither valid JSON nor a parseable review report", msg)

    def test_all_fixed_payload_fails_loudly(self):
        payload = json.dumps([{"where": "a.py:1", "what": "x", "fixStatus": "fixed"}])
        msg = err([*SAVED, payload])
        self.assertIn("no actionable findings", msg)


class ReportTests(unittest.TestCase):
    def test_report_renders_sections_fail_rows_and_findings(self):
        data = {
            "title": "# Code review — HEAD (2 files)",
            "mode_line": "Mode: full — correctness, security, quality.",
            "tracked": [{
                "finding": {"id": "F-1", "where": "a.py:1", "what": "bug",
                            "evidence": "quote", "severity": "high", "lens": "correctness",
                            "impact": "crash",
                            "confirmation": {"status": "verified", "note": ""}},
                "fix": "pending", "fixNote": "",
            }],
            "gate_rows": [{"name": "make test", "exit_code": 1, "tail": "boom"}],
            "gate_green": False,
            "assessment": {"verdict": "risky", "testGaps": ["no test for a.py"],
                           "residualRisks": ["runtime not exercised"]},
            "dropped": [{"where": "b.py:2", "what": "style", "reason": "not a finding"}],
            "checked": ["- the gate ran"],
            "fix_checked": [],
            "rounds_used": 0,
        }
        d = ok(["report", "--kind", "review", "--data", json.dumps(data)])
        md = d["markdown"]
        self.assertIn("**FAIL** — make test", md)
        self.assertIn("### [F-1 · HIGH · verified · correctness] bug", md)
        self.assertIn("- where: `a.py:1`", md)
        self.assertIn("## Dropped at triage (1)", md)
        self.assertIn("- no test for a.py", md)
        self.assertEqual(d["reported_findings"][0]["id"], "F-1")

    def test_report_header_counts_confirmation_and_names_missing_floor(self):
        def tracked(fid, status, **conf):
            return {"finding": {"id": fid, "where": "a.py:1", "what": "w", "evidence": "e",
                                "severity": "medium", "lens": "general",
                                "confirmation": {"status": status, "note": "", **conf}},
                    "fix": "pending"}
        data = {"tracked": [tracked("F-1", "verified"), tracked("F-2", "unconfirmed"),
                            tracked("F-3", "verified", self_checked=True)],
                "gate_rows": [{"name": "secrets (token patterns on the change)", "exit_code": 0,
                               "source": "builtin", "tail": ""}],
                "gate_green": True}
        d = ok(["report", "--kind", "review", "--data", json.dumps(data)])
        md = d["markdown"]
        self.assertIn("no repo checks detected — no mechanical floor", md)
        self.assertIn("## Findings (3 · 1 confirmed · 2 unconfirmed (1 self-checked)", md)
        self.assertIn("### [F-3 · MEDIUM · unconfirmed (self-checked) · general]", md)
        reparsed = ok([*SAVED, md])["tracked"]
        self.assertEqual([t["finding"]["confirmation"]["status"] for t in reparsed],
                         ["verified", "unconfirmed", "unconfirmed"])

    def test_report_defaults_a_missing_or_null_fix_to_pending(self):
        def tracked(fid, **extra):
            return {"finding": {"id": fid, "where": "a.py:1", "what": "w", "evidence": "e",
                                "severity": "low", "lens": "general",
                                "confirmation": {"status": "verified", "note": ""}}, **extra}
        data = {"tracked": [tracked("F-1", fix=None), tracked("F-2")],
                "gate_rows": [], "gate_green": True}
        d = ok(["report", "--kind", "review", "--data", json.dumps(data)])
        self.assertEqual([f["fixStatus"] for f in d["reported_findings"]], ["pending", "pending"])
        self.assertNotIn("fix:", d["markdown"])

    def test_report_shows_dependency_changes_and_offers_risks_to_an_existing_backlog(self):
        with tempfile.TemporaryDirectory() as d:
            data = {"tracked": [], "gate_green": True, "repo_abs": d, "backlog_label": "feat/x",
                    "gate_rows": [{"name": "dependency manifests (1 changed)", "exit_code": 0,
                                   "status": "info", "source": "builtin",
                                   "tail": "1 manifest(s) changed\nrequirements.txt: + left-pad==1.0"}],
                    "assessment": {"residualRisks": ["load path\n untested"]}}
            first = ok(["report", "--kind", "review", "--data", json.dumps(data)])
            self.assertIn("- info — dependency manifests (1 changed)\n  - requirements.txt: + left-pad==1.0",
                          first["markdown"])
            self.assertNotIn("backlog_offer", first)
            (Path(d) / "specs").mkdir()
            (Path(d) / "specs" / "BACKLOG.md").write_text("# Backlog\n", encoding="utf-8")
            offer = ok(["report", "--kind", "review", "--data", json.dumps(data)])["backlog_offer"]
            self.assertEqual(offer["lines"],
                             ["- feat/x — load path untested (source: spec-review residual risk)"])

    def test_bad_report_data_fails_loudly(self):
        msg = err(["report", "--kind", "review", "--data", "@/no/such/file.json"])
        self.assertIn("report data invalid", msg)

    def test_report_carries_standing_ci_rows_and_floors_merge_at_human(self):
        def tracked(fid, fix="fixed"):
            return {"finding": {"id": fid, "where": "a.py:1", "what": "w",
                                "evidence": "e", "severity": "medium",
                                "lens": "general",
                                "confirmation": {"status": "verified",
                                                 "note": ""}},
                    "fix": fix}
        base = {"tracked": [tracked("F-1")],
                "gate_rows": [
                    {"name": "make test", "exit_code": 0, "source": "repo",
                     "status": "pass", "tail": ""},
                    {"name": "CI: build", "exit_code": 0,
                     "status": "infrastructure", "source": "ci",
                     "class": "infrastructure", "failedStep": "Set up job",
                     "reason": "the job 'build' failed in the runner step "
                               "'Set up job'",
                     "rerun": "gh run rerun 4123 --failed",
                     "tail": "https://github.com/acme/widget/actions/runs/4123"}],
                "assessment": {"verdict": "v", "testGaps": [],
                               "residualRisks": []},
                "rounds_used": 2}
        # every finding is fixed and the gate is green, but a standing CI
        # row blocks merge: the rerun is the user's call, not an edit
        msg = err(["report", "--kind", "fix", "--data",
                   json.dumps({**base, "gate_green": True,
                               "conclusion": "merge"})])
        self.assertIn("below the derived floor 'human'", msg)
        self.assertIn("1 CI row(s) standing infrastructure-or-unknown", msg)
        d = ok(["report", "--kind", "fix", "--data",
                json.dumps({**base, "gate_green": True,
                            "conclusion": "human"})])
        self.assertEqual(d["derived_conclusion"], "human")
        md = d["markdown"]
        self.assertIn("- infrastructure — CI: build — the job 'build' failed "
                      "in the runner step 'Set up job'", md)
        self.assertIn("first failed step: Set up job", md)
        self.assertIn("rerun (an outward action, never run here): "
                      "`gh run rerun 4123 --failed`", md)
        self.assertIn("green after the final fix round, with 1 CI row(s) "
                      "standing (infrastructure-or-unknown — see below)", md)
        self.assertNotIn("all passed", md)
        self.assertNotIn("- pass — CI: build", md)
        # with the row resolved (rerun turned it green), merge floors again
        clear = [{**base["gate_rows"][0]},
                 {**base["gate_rows"][1], "status": "pass", "class": None,
                  "failedStep": None, "reason": None}]
        del clear[1]["rerun"]
        d = ok(["report", "--kind", "fix", "--data",
                json.dumps({**base, "gate_green": True, "gate_rows": clear,
                            "conclusion": "merge"})])
        self.assertEqual(d["derived_conclusion"], "merge")

    def test_fix_report_derives_the_floor_and_rejects_a_claim_below_it(self):
        def tracked(fid, fix="fixed", status="verified"):
            return {"finding": {"id": fid, "where": "a.py:1", "what": "w", "evidence": "e",
                                "severity": "medium", "lens": "general",
                                "confirmation": {"status": status, "note": ""}},
                    "fix": fix}
        base = {"gate_rows": [{"name": "make test", "exit_code": 0, "source": "repo", "tail": ""}],
                "assessment": {"verdict": "v", "testGaps": [], "residualRisks": []},
                "rounds_used": 2}
        # merge is derivable and claimed — stands, and is echoed as derived
        d = ok(["report", "--kind", "fix", "--data",
                json.dumps({**base, "gate_green": True, "tracked": [tracked("F-1")],
                            "conclusion": "merge"})])
        self.assertEqual(d["conclusion"], "merge")
        self.assertEqual(d["derived_conclusion"], "merge")
        # unresolved finding, merge claimed — below the floor: error naming both
        msg = err(["report", "--kind", "fix", "--data",
                   json.dumps({**base, "gate_green": True,
                               "tracked": [tracked("F-1", fix="unfixed")],
                               "conclusion": "merge"})])
        self.assertIn("below the derived floor 'fix-first'", msg)
        self.assertIn("1 unresolved finding", msg)
        # red gate, merge claimed — same rejection
        err(["report", "--kind", "fix", "--data",
             json.dumps({**base, "gate_green": False, "tracked": [tracked("F-1")],
                         "conclusion": "merge"})])
        # unconfirmed residue (unfixed) derives human; a fix-first claim is below it
        msg = err(["report", "--kind", "fix", "--data",
                   json.dumps({**base, "gate_green": True,
                               "tracked": [tracked("F-1", fix="unfixed", status="unconfirmed")],
                               "conclusion": "fix-first"})])
        self.assertIn("below the derived floor 'human'", msg)
        # an unconfirmed finding that WAS fixed is resolved — floor merge,
        # and escalating above it stays the assessor's call
        d = ok(["report", "--kind", "fix", "--data",
                json.dumps({**base, "gate_green": True,
                            "tracked": [tracked("F-1", fix="fixed", status="unconfirmed")],
                            "conclusion": "fix-first"})])
        self.assertEqual(d["derived_conclusion"], "merge")
        self.assertEqual(d["conclusion"], "fix-first")
        # escalation is always allowed: derived fix-first, claimed human
        d = ok(["report", "--kind", "fix", "--data",
                json.dumps({**base, "gate_green": True,
                            "tracked": [tracked("F-1", fix="unfixed")],
                            "conclusion": "human"})])
        self.assertEqual(d["conclusion"], "human")
        self.assertEqual(d["derived_conclusion"], "fix-first")
        # absent or unrecognized claim is filled with the floor
        d = ok(["report", "--kind", "fix", "--data",
                json.dumps({**base, "gate_green": True,
                            "tracked": [tracked("F-1", fix="unfixed")]})])
        self.assertEqual(d["conclusion"], "fix-first")
        self.assertEqual(d["derived_conclusion"], "fix-first")
        # a review-kind report never derives (review-only runs do not recommend)
        d = ok(["report", "--kind", "review", "--data",
                json.dumps({**base, "gate_green": True, "tracked": [tracked("F-1")],
                            "conclusion": "whatever the assessor said"})])
        self.assertEqual(d["conclusion"], "whatever the assessor said")
        self.assertNotIn("derived_conclusion", d)

    def test_fix_verdict_vocabulary_adjudicates_and_routes(self):
        def tracked(fid, fix, status="verified"):
            return {"finding": {"id": fid, "where": "a.py:1", "what": "w", "evidence": "e",
                                "severity": "medium", "lens": "general",
                                "confirmation": {"status": status, "note": ""}},
                    "fix": fix}
        base = {"gate_rows": [], "assessment": {"verdict": "v", "testGaps": [], "residualRisks": []},
                "rounds_used": 2}
        # rejected-valid resolves like fixed — merge is derivable with one
        d = ok(["report", "--kind", "fix", "--data",
                json.dumps({**base, "gate_green": True,
                            "tracked": [tracked("F-1", "fixed"), tracked("F-2", "rejected-valid")],
                            "conclusion": "merge"})])
        self.assertEqual(d["derived_conclusion"], "merge")
        self.assertIn("1 withdrawn", d["markdown"])
        # rejected-invalid stands — merge claim is below the fix-first floor
        msg = err(["report", "--kind", "fix", "--data",
                   json.dumps({**base, "gate_green": True,
                               "tracked": [tracked("F-1", "fixed"), tracked("F-2", "rejected-invalid")],
                               "conclusion": "merge"})])
        self.assertIn("below the derived floor 'fix-first'", msg)
        # out-of-scope floors at human — the user's widening call
        msg = err(["report", "--kind", "fix", "--data",
                   json.dumps({**base, "gate_green": True,
                               "tracked": [tracked("F-1", "out-of-scope")],
                               "conclusion": "fix-first"})])
        self.assertIn("below the derived floor 'human'", msg)
        self.assertIn("1 out-of-scope", ok(["report", "--kind", "fix", "--data",
                                            json.dumps({**base, "gate_green": True,
                                                        "tracked": [tracked("F-1", "out-of-scope")],
                                                        "conclusion": "human"})])["markdown"])
        # a withdrawn finding does not come back on a fix_from carry (JSON or
        # markdown carrier); what is carried restarts pending by design (D-005)
        carried = ok([*SAVED, json.dumps(
            {"findings": [{"id": "F-1", "where": "a.py:1", "what": "w", "fixStatus": "rejected-valid"},
                          {"id": "F-2", "where": "b.py:1", "what": "x", "fixStatus": "rejected-invalid"},
                          {"id": "F-3", "where": "c.py:1", "what": "y", "fixStatus": "out-of-scope"}]})])["tracked"]
        self.assertEqual([t["finding"]["id"] for t in carried], ["F-2", "F-3"])
        self.assertTrue(all(t["fix"] == "pending" for t in carried))
        md = ok(["report", "--kind", "fix", "--data",
                 json.dumps({**base, "gate_green": True,
                             "tracked": [tracked("F-1", "rejected-valid"), tracked("F-2", "out-of-scope")],
                             "conclusion": "human"})])["markdown"]
        reparsed = ok([*SAVED, md])["tracked"]
        self.assertEqual([t["finding"]["id"] for t in reparsed], ["F-2"])
        # the verify ask teaches the ruling, the fixer ask the channel
        self.assertIn("rejected-valid", ok(["ask", "--kind", "verify", "--ctx",
                                            json.dumps({"tracked": {"finding": {"id": "F-1", "where": "a.py:1",
                                                                                "what": "x", "severity": "high",
                                                                                "lens": "correctness"}},
                                                        "project": False, "base": "HEAD", "notes": "wrong: never nil"})])["ask"])
        def item(fid, fix=None):
            return {"finding": {"id": fid, "where": "a.py:1", "what": "x", "evidence": "e",
                                "severity": "high", "lens": "correctness"}, "fix": fix}
        ask = ok(["ask", "--kind", "fixer", "--ctx",
                  json.dumps({"round": 1, "project": False, "base": "HEAD",
                              "unresolved": [item("F-1"), item("F-8", "out-of-scope"),
                                             item("F-9", "rejected-valid")]})])["ask"]
        self.assertIn("outOfScope", ask)
        self.assertIn('"F-1"', ask)
        # off-loop items never reach the fixer, whatever the session passed
        self.assertNotIn('"F-8"', ask)
        self.assertNotIn('"F-9"', ask)
        # a fix status outside the vocabulary is an inconsistent report, never counted
        msg = err(["report", "--kind", "fix", "--data",
                   json.dumps({**base, "gate_green": True, "tracked": [tracked("F-1", "skipped")]})])
        self.assertIn("unknown fix status 'skipped'", msg)


def make_run():
    holder, repo = make_repo()
    (repo / "app.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
    git(repo, "add", "-A")
    run_dir = ok(["run-init", "--target", "diff", "--repo", str(repo)])["run_dir"]
    return holder, repo, run_dir


RUN_HOLDER, _, RUN_DIR = make_run()
atexit.register(RUN_HOLDER.cleanup)

ASK_CASES = [
    ("scout", {"base": "HEAD", "project": False, "files": ["src/a.py", "src/b.py"], "run_dir": RUN_DIR}),
    ("scout", {"base": "HEAD", "project": True, "files": [f"m{i}.py" for i in range(45)],
               "repo_abs": "/tmp/repo", "run_dir": RUN_DIR}),
    ("review", {"base": "HEAD", "files_n": 3, "lines": 120, "over_cap": False,
                "run_dir": RUN_DIR,
                "gate_line": "The repo's own checks all passed",
                "lens": {"focus": "logic errors."},
                "intent": "add caching", "scout_map": {"modules": [{"name": "m", "path": "src/m.py", "role": "r"}],
                                                        "conventions": ["c1"], "riskAreas": ["ra1"]}}),
    ("review-project", {"base": "HEAD", "files": ["a.py"], "candidates": 9, "part": 2, "parts": 3,
                        "gate_line": "checks passed", "lens": {"focus": "security."},
                        "repo_abs": "/tmp/repo", "run_dir": RUN_DIR}),
    ("triage", {"base": "HEAD", "lens_label": "correctness", "intent": "fix bug",
                "findings": [{"where": "a.py:1", "what": "x", "evidence": "q", "severity": "high"}]}),
    ("triage-project", {"lens_label": "quality", "findings": []}),
    ("cross-lens", {"base": "HEAD", "kept": [{"where": "a.py:1", "what": "x", "evidence": "q",
                                              "severity": "low", "lens": "quality"}]}),
    ("confirm", {"base": "HEAD", "run_dir": RUN_DIR,
                 "finding": {"where": "a.py:2", "what": "y", "evidence": "e",
                             "severity": "medium", "lens": "security", "impact": "i"}}),
    ("confirm-project", {"finding": {"where": "a.py:2", "what": "y", "evidence": "e", "severity": "low"}}),
    ("final", {"base": "HEAD", "run_dir": RUN_DIR, "gate_line": "checks passed",
               "summary": [{"id": "F-1"}], "intent": "x", "scout_map": None}),
    ("final-project", {"gate_line": "checks passed", "summary": [], "files": [f"f{i}.py" for i in range(12)],
                       "repo_abs": None}),
    ("fixer", {"base": "HEAD", "round": 1, "project": False, "intent": "fix",
               "unresolved": [{"finding": {"id": "F-1", "where": "a.py:1", "what": "x", "evidence": "e",
                                           "severity": "high", "lens": "correctness", "impact": "i"}}]}),
    ("fixer", {"base": "HEAD", "round": 2, "project": True, "gate_feedback": "make test FAILED",
               "repo_abs": "/tmp/r",
               "unresolved": [{"finding": {"id": "F-2", "where": "b.py:1", "what": "y", "evidence": "e2",
                                           "severity": "medium", "lens": "quality"}, "fixNote": "still bad"}]}),
    ("verify", {"base": "HEAD", "project": False, "notes": "reordered guards",
                "tracked": {"finding": {"id": "F-1", "where": "a.py:1", "what": "x",
                                        "severity": "high", "lens": "correctness"}}}),
    ("fix-review", {"base": "HEAD", "run_dir": RUN_DIR, "gate_green": True, "paths": ["a.py", "b.py"]}),
    ("fix-review", {"base": "HEAD", "gate_green": False, "paths": ["a.py"], "repo_abs": "/tmp/r",
                    "run_dir": RUN_DIR}),
    ("loop-final", {"base": "HEAD", "run_dir": RUN_DIR, "rounds_used": 2, "gate_green": False,
                    "changed_paths": ["a.py"], "project": False,
                    "tracked": [{"finding": {"id": "F-1", "where": "a.py:1", "what": "x", "evidence": "e",
                                             "severity": "high", "lens": "correctness",
                                             "confirmation": {"status": "verified", "note": ""}},
                                 "fix": "fixed", "fixNote": "n"}]}),
]

TRACKED_FIX = {"finding": {"id": "F-1", "where": "a.py:1", "what": "x", "evidence": "e",
                           "severity": "high", "lens": "correctness", "impact": "i",
                           "confirmation": {"status": "verified", "note": ""}},
               "fix": "pending", "fixNote": "carried"}


class AskRenderingTests(unittest.TestCase):
    def _oracle(self, kind, ctx):
        return ok(["ask", "--kind", kind, "--ctx", json.dumps(ctx)])["ask"]

    def test_every_ask_kind_renders_deterministically(self):
        for kind, ctx in ASK_CASES:
            with self.subTest(kind=kind, project=ctx.get("project"), base=ctx.get("base")):
                self.assertEqual(self._oracle(kind, ctx), self._oracle(kind, ctx))
        batch = ok(["ask", "--kind", "batch", "--ctx", json.dumps(
            {"batch": [{"kind": k, "ctx": c} for k, c in ASK_CASES[:4]]})])
        self.assertEqual(batch["asks"], [self._oracle(k, c) for k, c in ASK_CASES[:4]])

    def test_every_ask_opens_with_the_tools_ask(self):
        # the capability handshake (D-029): the first line of every ask is
        # the report request, once — the rule itself sits in the protocol
        ask_line = ("The first line of your reply is `tools: <the tools you "
                    "actually hold, comma-separated>`.")
        for kind, ctx in ASK_CASES:
            with self.subTest(kind=kind, project=ctx.get("project")):
                ask = self._oracle(kind, ctx)
                self.assertEqual(ask.splitlines()[0], ask_line)
                self.assertEqual(ask.count(ask_line), 1)
                self.assertTrue(ask[len(ask_line) + 1:].rstrip(), ask)
        asks = ok(["ask", "--kind", "batch", "--ctx", json.dumps(
            {"batch": [{"kind": k, "ctx": c} for k, c in ASK_CASES[:4]]})])["asks"]
        self.assertEqual([ask.splitlines()[0] for ask in asks],
                         [ask_line] * len(asks))

    def test_review_ask_carries_untracked_files_and_severity_ladder(self):
        ask = self._oracle("review", {**ASK_CASES[2][1], "untracked": ["src/new.py"]})
        self.assertIn("untracked files, which the diff file does not show", ask)
        self.assertIn(f"- {Path(RUN_DIR).parents[2]}/src/new.py", ask)
        self.assertIn("high = data loss, crash, wrong result, or security compromise", ask)

    def test_no_reader_ask_names_a_git_command(self):
        # every ask but the fixer's is run by a type that holds no shell
        for kind, ctx in ASK_CASES:
            if kind != "fixer":
                with self.subTest(kind=kind):
                    self.assertNotRegex(self._oracle(kind, ctx), GIT_COMMAND)
        fixer = next(c for k, c in ASK_CASES if k == "fixer" and c.get("repo_abs"))
        self.assertIn("Run any git command as `git -C /tmp/r ...`", self._oracle("fixer", fixer))

    def test_systems_carry_the_three_lenses(self):
        d = ok(["systems"])
        self.assertEqual([l["label"] for l in d["lenses"]], ["correctness", "security", "quality"])
        for lens in d["lenses"] + [d["general"]]:
            self.assertTrue(lens["focus"].endswith("."))

    def test_unknown_ask_kind_fails_loudly(self):
        err(["ask", "--kind", "nope", "--ctx", "{}"])


GIT_COMMAND = re.compile(r"`git |git -C|\bgit (?:diff|ls-files|status|log|show)\b")


class ReaderFileTests(unittest.TestCase):
    """A panel reader holds no shell (D-028): the oracle writes what the
    reader used a git command for into the run folder and the ask names
    the file — it exists and holds the change; what the oracle cannot
    produce is a named absence in the ask, never a crash; an ask with no
    run folder to write into is an error, never a bare ask."""

    def setUp(self):
        holder, repo = make_repo()
        self.addCleanup(holder.cleanup)
        (repo / "lib.py").write_text("z = 3\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "lib")
        (repo / "app.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
        git(repo, "add", "-A")
        self.repo = repo
        self.run_dir = ok(["run-init", "--target", "diff", "--repo", str(repo)])["run_dir"]
        self.ctx = {"base": "HEAD", "run_dir": self.run_dir}

    def named_files(self, ask):
        folder = re.escape(self.run_dir) + "/reader-files/"
        return [Path(name) for name in re.findall(r"`(" + folder + r"[^`]+)`", ask)]

    def test_reader_asks_name_a_run_folder_file_that_holds_the_change(self):
        tracked = {"finding": {"id": "F-1", "where": "app.py:1", "what": "x", "evidence": "e",
                               "severity": "high", "lens": "correctness",
                               "confirmation": {"status": "verified", "note": ""}},
                   "fix": "fixed", "fixNote": "n"}
        cases = [
            ("scout", {"project": False, "files": ["app.py"]}, 1,
             ("# target files (1)\napp.py\n", "# tracked files in the repository (2)\napp.py\nlib.py\n")),
            ("review", {"files_n": 1, "lines": 1, "over_cap": False, "lens": {"focus": "f."},
                        "gate_line": "ok"}, 1, ("+y = 2\n",)),
            ("review-project", {"files": ["app.py", "lib.py"], "part": 1, "parts": 2, "candidates": 2,
                                "lens": {"focus": "f."}, "gate_line": "ok"}, 1, ("app.py\nlib.py\n",)),
            ("confirm", {"finding": {"where": "app.py:2", "what": "y", "evidence": "e", "severity": "low"}},
             1, ("+y = 2\n",)),
            ("final", {"gate_line": "checks passed", "summary": [{"id": "F-1"}]}, 1, ("+y = 2\n",)),
            ("fix-review", {"gate_green": True, "paths": ["app.py", "lib.py"]}, 2, ("+y = 2\n",)),
            ("loop-final", {"rounds_used": 1, "gate_green": True, "changed_paths": ["app.py"],
                            "project": False, "tracked": [tracked]}, 1, ("+y = 2\n",)),
        ]
        for kind, extra, count, literals in cases:
            with self.subTest(kind=kind):
                d = ok(["ask", "--kind", kind, "--ctx", json.dumps({**self.ctx, **extra})])
                self.assertEqual(sorted(d), ["ask", "status"])
                named = self.named_files(d["ask"])
                self.assertEqual(len(named), count, d["ask"])
                for path in named:
                    self.assertTrue(path.is_file(), path)
                    self.assertTrue(str(path.resolve()).startswith(self.run_dir + "/reader-files/"), path)
                texts = [path.read_text(encoding="utf-8") for path in named]
                self.assertTrue(any(all(lit in text for lit in literals) for text in texts), literals)

    def test_confirm_ask_rules_on_what_the_hunk_shows(self):
        finding = {"where": "lib.py:1", "what": "y", "evidence": "e", "severity": "low"}
        # a path the change does not touch: an empty hunk, and the finding predates the change
        ask = ok(["ask", "--kind", "confirm", "--ctx", json.dumps({**self.ctx, "finding": finding})])["ask"]
        (hunk,) = self.named_files(ask)
        self.assertEqual(hunk.read_text(encoding="utf-8"), "")
        self.assertIn("is EMPTY", ask)
        self.assertIn("answer unconfirmed", ask)
        # an untracked path is new code in its entirety — no hunk is named for it
        ask = ok(["ask", "--kind", "confirm", "--ctx", json.dumps(
            {**self.ctx, "untracked": ["new.py"], "finding": {**finding, "where": "new.py:1"}})])["ask"]
        self.assertEqual(self.named_files(ask), [])
        self.assertIn("`new.py` is an untracked file", ask)

    def test_a_diff_that_cannot_be_produced_is_a_named_absence_never_a_crash(self):
        shutil.rmtree(self.repo / ".git")
        cases = [
            ("review", {"files_n": 1, "lines": 1, "lens": {"focus": "f."}, "gate_line": "ok"},
             "diff file ABSENT"),
            ("confirm", {"finding": {"where": "app.py:2", "what": "y", "evidence": "e", "severity": "low"}},
             "Hunk file: ABSENT"),
        ]
        for kind, extra, absent in cases:
            with self.subTest(kind=kind):
                r = run(["ask", "--kind", kind, "--ctx", json.dumps({**self.ctx, **extra})])
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                d = json.loads(r.stdout)
                self.assertEqual(d["status"], "ok")
                self.assertIn(absent, d["ask"])
                self.assertIn("not run: <why>", d["ask"])
                self.assertNotIn("`" + self.run_dir + "/reader-files/", d["ask"])
        folder = Path(self.run_dir) / "reader-files"
        self.assertEqual([f.name for f in folder.iterdir()] if folder.is_dir() else [], [])

    def test_a_reader_ask_with_no_run_folder_is_an_error_never_a_bare_ask(self):
        ctx = {"base": "HEAD", "files_n": 1, "lines": 1, "lens": {"focus": "f."}, "gate_line": "ok"}
        for run_dir in (None, str(self.repo / "nope")):
            with self.subTest(run_dir=run_dir):
                r = run(["ask", "--kind", "review", "--ctx", json.dumps({**ctx, "run_dir": run_dir})])
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                d = json.loads(r.stdout)
                self.assertEqual((d["status"], d["stage"]), ("error", "ask"))
                self.assertIn("run_dir", d["error"])
        self.assertFalse((self.repo / "nope").exists())
        # a wave carrying one bare reader ctx is refused whole, naming it
        r = run(["ask", "--kind", "batch", "--ctx", json.dumps({"batch": [
            {"kind": "triage", "ctx": {"lens_label": "correctness", "findings": []}},
            {"kind": "confirm", "ctx": {"finding": {"where": "app.py:1"}}}]})])
        d = json.loads(r.stdout)
        self.assertEqual((d["status"], d.get("kind")), ("error", "confirm"))


AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
JUDGE_BRIEFS = {"confirm": "spec-review-confirmer.md", "verify": "spec-review-verifier.md"}
JUDGE_ASKS = ("confirm", "confirm-project", "verify")
# Every brief that reads and never writes: files only — the fixer is the panel's one author.
READER_BRIEFS = ("spec-review-scout.md", "spec-review-correctness.md", "spec-review-security.md",
                 "spec-review-quality.md", "spec-review-confirmer.md", "spec-review-verifier.md")


class JudgeBriefTests(unittest.TestCase):
    """The confirm and verify stages take their system prompt from a brief
    (D-027): `systems` returns each brief's frontmatter-stripped body
    byte-verbatim and holds no second copy of it, an unreadable brief is
    an error — never a fallback — the asks keep their shape, and every
    brief that reads grants files only (D-028)."""

    def test_systems_carry_each_brief_body_byte_verbatim(self):
        d = ok(["systems"])
        oracle = SCRIPT.read_text(encoding="utf-8")
        for stage, brief in JUDGE_BRIEFS.items():
            with self.subTest(stage=stage):
                body = (AGENTS_DIR / brief).read_bytes().decode("utf-8").split("\n---\n", 1)[1]
                self.assertEqual(d[stage], body)
                self.assertTrue(body.startswith("\n# "), "frontmatter not stripped")
                # the kit's one honesty sentence is every system's, not a copy
                for line in map(str.strip, body.splitlines()):
                    if len(line) > 40 and line not in d["honesty"]:
                        self.assertNotIn(line, oracle, "a second copy in the oracle")

    def test_systems_keep_the_inline_roles(self):
        d = ok(["systems"])
        self.assertEqual(sorted(d), ["confirm", "fix_review", "fixer", "general", "honesty",
                                     "lenses", "scout", "status", "triage", "verify"])
        for key in ("triage", "fix_review"):
            self.assertTrue(d[key].startswith("You are the "), key)

    def test_judge_asks_keep_their_shape(self):
        for kind, ctx in ASK_CASES:
            if kind in JUDGE_ASKS:
                with self.subTest(kind=kind):
                    d = ok(["ask", "--kind", kind, "--ctx", json.dumps(ctx)])
                    self.assertEqual(sorted(d), ["ask", "status"])
                    self.assertTrue(d["ask"])

    def test_reader_briefs_grant_files_only(self):
        head = {}
        for brief in READER_BRIEFS:
            with self.subTest(brief=brief):
                head[brief] = (AGENTS_DIR / brief).read_text(encoding="utf-8").split("\n---\n", 1)[0]
                self.assertTrue(head[brief].startswith("---\n"))
                self.assertRegex(head[brief], r"(?m)^name: " + re.escape(brief[:-3]) + r"$")
                self.assertRegex(head[brief], r"(?m)^description:")
                self.assertRegex(head[brief], r"(?m)^model: inherit$")
                self.assertRegex(head[brief], r"(?m)^tools: Read, Grep, Glob$")
                for tool in ("Bash", "Write", "Edit"):
                    self.assertRegex(head[brief], r"(?m)^  - " + tool + r"$")
        # the list is closed: no other spec-review brief exists to hold a shell
        shipped = sorted(p.name for p in AGENTS_DIR.glob("spec-review-*.md"))
        self.assertEqual(shipped, sorted(READER_BRIEFS + ("spec-review-fixer.md",)))
        fixer = (AGENTS_DIR / "spec-review-fixer.md").read_text(encoding="utf-8").split("\n---\n", 1)[0]
        self.assertRegex(fixer, r"(?m)^tools: Read, Grep, Glob, Bash, Write, Edit$")

    def test_unreadable_brief_is_an_error_never_an_inline_fallback(self):
        skill = SCRIPT.parent.parent
        holder = tempfile.TemporaryDirectory(prefix="oracle-skill-")
        with holder:
            copy = Path(holder.name)
            shutil.copytree(skill / "scripts", copy / "scripts",
                            ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(AGENTS_DIR, copy / "agents")
            for stage, brief in JUDGE_BRIEFS.items():
                target = copy / "agents" / brief
                intact = target.read_bytes()
                for damage in ("missing", "no-frontmatter", "not-utf8"):
                    with self.subTest(brief=brief, damage=damage):
                        if damage == "missing":
                            target.unlink()
                        elif damage == "no-frontmatter":
                            target.write_text("no frontmatter here\n", encoding="utf-8")
                        else:
                            target.write_bytes(b"\xff\xfe\x00bad")
                        r = subprocess.run([sys.executable, str(copy / "scripts" / SCRIPT.name),
                                            "systems"], capture_output=True, text=True)
                        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                        d = json.loads(r.stdout)
                        self.assertEqual(d["status"], "error")
                        self.assertEqual(d["stage"], "systems")
                        self.assertIn(f"agents/{brief}", d["error"])
                        self.assertNotIn(stage, d)
                        target.write_bytes(intact)


# Each role's required set is its own brief's `tools:` line: files only
# for every reader, the shell and a file writer for the panel's one author.
READER_TOOLS = ("Read", "Grep", "Glob")
ROLE_TOOLS = {role: READER_TOOLS for role in
              ("scout", "correctness", "security", "quality", "confirmer", "verifier")}
ROLE_TOOLS["fixer"] = ("Read", "Grep", "Glob", "Bash", "Write", "Edit")
SCOUT_MAP = '{"modules": [], "conventions": [], "riskAreas": []}\n'


class HandshakeTests(unittest.TestCase):
    """The capability handshake: a reply is read only after the tools
    report it opens with holds every tool on its role's brief line — a
    short one is a failed call that hands back nothing to read and
    advances no stage."""

    def refused(self, role, lead):
        d = refused(["handshake", "--role", role, "--text", lead + SCOUT_MAP])
        self.assertEqual((d["stage"], d["role"]), ("handshake", role))
        for named in (role, *d["missing"]):
            self.assertIn(named, d["error"])
        return d

    def test_a_full_report_returns_the_reply_after_its_line(self):
        lead = "> tools: read, grep, glob\n"
        self.assertEqual(ok(["handshake", "--role", "scout", "--text", lead + SCOUT_MAP]),
                         {"status": "ok", "tools": ["read", "grep", "glob"], "reply": SCOUT_MAP})

    def test_every_brief_tool_is_required_and_nothing_more(self):
        for role, tools in ROLE_TOOLS.items():
            with self.subTest(role=role):
                ok(["handshake", "--role", role, "--text", f"tools: {', '.join(tools)}\n" + SCOUT_MAP])
            for short in tools:
                with self.subTest(role=role, without=short):
                    rest = [t for t in tools if t != short]
                    self.assertEqual(self.refused(role, "tools: " + ", ".join(rest) + "\n")["missing"],
                                     [short])

    def test_a_dialect_name_for_a_required_tool_meets_it(self):
        for names in ("Read, Grep, Glob, Execute, Create, Edit",
                      "read, grep, glob, execute, applypatch, edit"):
            with self.subTest(names=names):
                ok(["handshake", "--role", "fixer", "--text", f"tools: {names}\n" + SCOUT_MAP])
        self.assertEqual(self.refused("fixer", "tools: Read, Grep, Glob, Edit\n")["missing"],
                         ["Bash", "Write"])

    def test_an_unknown_role_is_refused_naming_the_briefs(self):
        d = refused(["handshake", "--role", "triage", "--text", "tools: Read\n" + SCOUT_MAP])
        self.assertEqual(d["stage"], "handshake")
        for role in ROLE_TOOLS:
            self.assertIn(role, d["error"])

    def test_the_brief_is_the_table(self):
        skill = SCRIPT.parent.parent
        with tempfile.TemporaryDirectory(prefix="oracle-skill-") as holder:
            copy = Path(holder)
            shutil.copytree(skill / "scripts", copy / "scripts",
                            ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(AGENTS_DIR, copy / "agents")
            call = [sys.executable, str(copy / "scripts" / SCRIPT.name),
                    "handshake", "--role", "scout", "--text"]

            def reply(lead):
                r = subprocess.run([*call, lead + SCOUT_MAP], capture_output=True, text=True)
                self.assertTrue(r.stdout.startswith('{"status":'), r.stdout + r.stderr)
                return r

            brief = copy / "agents" / "spec-review-scout.md"
            text = brief.read_text(encoding="utf-8")
            brief.write_text(text.replace("tools: Read, Grep, Glob", "tools: Read, WebFetch"),
                             encoding="utf-8")
            # a changed line moves the handshake with it
            self.assertEqual(json.loads(reply("tools: Read, Grep, Glob\n").stdout)["missing"],
                             ["WebFetch"])
            self.assertEqual(reply("tools: Read, WebFetch\n").returncode, 0)
            # a brief with no line refuses the check — it never requires nothing
            brief.write_text(text.replace("tools: Read, Grep, Glob\n", ""), encoding="utf-8")
            r = reply("tools: Read, Grep, Glob\n")
            self.assertEqual(r.returncode, 1)
            self.assertIn("agents/spec-review-scout.md", json.loads(r.stdout)["error"])

    def test_a_refused_reply_advances_no_stage(self):
        holder, repo = make_repo()
        with holder:
            run_dir = ok(["run-init", "--target", "diff", "--repo", str(repo)])["run_dir"]
            ok(["run-save", "--run-dir", run_dir, "--stage", "scope", "--data", "{}"])
            before = sorted(p.name for p in Path(run_dir).iterdir())
            self.refused("fixer", "tools: Read\n")
            refused(["findings-parse", "--role", "correctness", "--text",
                     "tools: Grep\n" + FINDINGS_MD])
            self.assertEqual(sorted(p.name for p in Path(run_dir).iterdir()), before)
            resumed = ok(["run-resume", "--run-dir", run_dir])
            self.assertEqual((resumed["completed"], resumed["next"]), (["scope"], "scout"))


class RunFolderTests(unittest.TestCase):
    """The run folder's contract (spec-review D-020): run-init records
    the target's fingerprint after scope ran; run-save stores stage
    JSON under the STAGES vocabulary; run-resume continues at `next` on
    an unchanged target and refuses a changed one; the folder carries
    its own self-ignoring .gitignore; gc prunes old runs."""

    def test_round_trip_reports_next_with_saved_data(self):
        holder, repo = make_repo()
        with holder:
            (repo / "app.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            init = ok(["run-init", "--target", "diff", "--repo", str(repo)])
            run_dir = init["run_dir"]
            self.assertEqual(init["status"], "ok")
            self.assertTrue((Path(run_dir) / ".gitignore").is_file())
            self.assertEqual(
                (Path(run_dir) / ".gitignore").read_text(encoding="utf-8"),
                "*\n")
            ok(["run-save", "--run-dir", run_dir, "--stage", "scope",
                "--data", '{"fast_mode_default": false, "files": 1}'])
            ok(["run-save", "--run-dir", run_dir, "--stage", "scout",
                "--data", '{"riskAreas": []}'])
            ok(["run-save", "--run-dir", run_dir,
                "--stage", "review-correctness", "--data", '{"findings": []}'])
            resumed = ok(["run-resume", "--run-dir", run_dir])
            self.assertEqual(resumed["completed"],
                             ["scope", "scout", "review-correctness"])
            # the saved lens was the mode's FIRST lens — the next slot
            # is the second lens's review, not a triage
            self.assertEqual(resumed["next"], "review-security")
            self.assertEqual(resumed["data"]["scout"]["data"],
                             {"riskAreas": []})
            # the saved scope data rides through verbatim — the lens set
            # for `next` read its fast_mode_default (false → the full
            # LENSES order, so review-security is the second slot)
            self.assertFalse(resumed["data"]["scope"]["data"]
                             ["fast_mode_default"])

    def test_changed_target_refuses_to_resume(self):
        holder, repo = make_repo()
        with holder:
            (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
            init = ok(["run-init", "--target", "diff", "--repo", str(repo)])
            run_dir = init["run_dir"]
            ok(["run-save", "--run-dir", run_dir, "--stage", "scope",
                "--data", "{}"])
            (repo / "new.py").write_text("b = 1\n", encoding="utf-8")
            e = err(["run-resume", "--run-dir", run_dir])
            self.assertIn("target changed", e)
            self.assertIn("fix_from", e)

    def test_resume_from_the_run_record_alone(self):
        holder, repo = make_repo()
        with holder:
            (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
            init = ok(["run-init", "--target", "diff", "--repo", str(repo)])
            run_dir = init["run_dir"]
            resumed = ok(["run-resume", "--run-dir", run_dir])
            self.assertEqual(resumed["completed"], [])
            self.assertEqual(resumed["next"], "scope")

    def test_run_save_refuses_a_stage_outside_the_vocabulary(self):
        holder, repo = make_repo()
        with holder:
            init = ok(["run-init", "--target", "diff", "--repo", str(repo)])
            e = err(["run-save", "--run-dir", init["run_dir"],
                     "--stage", "bogus", "--data", "{}"])
            self.assertIn("STAGES", e)
            # the concrete forms of every pattern save cleanly
            for stage in ("scope", "review-correctness", "triage-general",
                          "confirm-F-001", "fix-2-gate"):
                ok(["run-save", "--run-dir", init["run_dir"],
                    "--stage", stage, "--data", '{"n": 1}'])

    def test_gc_keeps_the_newest_runs(self):
        holder, repo = make_repo()
        with holder:
            root = Path(repo) / ".spec-review" / "runs"
            root.mkdir(parents=True)
            for name in ("20260101-000000-aaaa", "20260102-000000-bbbb",
                         "20260103-000000-cccc", "20260104-000000-dddd",
                         "20260105-000000-eeee", "20260106-000000-ffff"):
                (root / name).mkdir()
                (root / name / "run.json").write_text("{}", encoding="utf-8")
            d = ok(["run-gc", "--repo", str(repo), "--keep", "5"])
            self.assertEqual(d["removed"], ["20260101-000000-aaaa"])
            self.assertEqual(d["kept"], 5)
            # run-init gcs too
            ok(["run-init", "--target", "diff", "--repo", str(repo)])
            self.assertEqual(len(list(root.iterdir())), 5)

    def test_stage_order_matches_run_sequence_md(self):
        import importlib.util
        sys.path.insert(0, str(SCRIPT.parent))
        _spec = importlib.util.spec_from_file_location(
            "review_orchestrator_drift", SCRIPT)
        ro = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(ro)
        md = (Path(__file__).resolve().parent.parent / "contracts"
              / "run-sequence.md").read_text(encoding="utf-8")
        block = re.search(r"^```\n(.*?)^```", md, re.S | re.M)
        assert block, "run-sequence.md lost its STAGES block"
        tokens = re.findall(
            r"scope|scout|review-<lens>|triage-<lens>|crosslens|"
            r"confirm-<F-id>|assessment|report|fix-<n>-\{[^}]*\}",
            block.group(1))
        # the md's fix-group expands to the oracle's six fix slots
        expanded = []
        for t in tokens:
            if t.startswith("fix-<n>-{"):
                inner = t[len("fix-<n>-{"):-1]
                expanded += [f"fix-<n>-{s.strip()}"
                             for s in inner.split(",")]
            else:
                expanded.append(t)
        self.assertEqual(expanded, list(ro.STAGES),
                         "run-sequence.md's stage order drifted from the "
                         "oracle's STAGES tuple")


if __name__ == "__main__":
    unittest.main()
