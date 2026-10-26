#!/usr/bin/env python3
"""Unit tests for the shared review oracle.

Real temp git repos, not mocks: the oracle's contract is repo state in,
JSON out. Error paths must fail loudly (exit 1 + status error), never
silently proceed."""

import json
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
            d = ok(["scope", "--target", "diff", "--base", "HEAD", "--repo", str(repo)])
            self.assertEqual(d["mode"], "diff")
            self.assertEqual(d["files"], ["app.py"])
            self.assertEqual(d["added"], 1)
            self.assertFalse(d["clean"])

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
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "files")
            d = ok(["scope", "--target", "project", "--repo", str(repo)])
            names = [f for f in d["files"]]
            self.assertNotIn("pkg/skip.lock", names)
            self.assertNotIn("vendor/v.py", names)
            self.assertIn("app.py", names)
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

    def test_gate_on_this_kit_repo_detects_its_checks(self):
        kit_root = SCRIPT.parents[2]  # CWD-independent: run.sh cds into the skill
        # --tree scans every tracked *.sh, so detection is provable on a
        # clean checkout; --base HEAD sees an empty diff there (zero rows).
        d = ok(["gate", "--tree", "--repo", str(kit_root)])
        self.assertTrue(any("bash -n" in g["name"] or "secret" in g["name"]
                            for g in d["rows"]))
        self.assertTrue(d["green"])


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


class FindingsParseTests(unittest.TestCase):
    def test_markdown_report_parses_ids_statuses_and_fixes(self):
        d = ok(["findings-parse", "--text", FINDINGS_MD])
        tracked = d["tracked"]
        self.assertEqual(len(tracked), 2)  # the fixed one is dropped
        self.assertEqual(tracked[0]["finding"]["id"], "F-1")  # high sorts first
        self.assertEqual(tracked[0]["finding"]["severity"], "high")
        self.assertEqual(tracked[1]["finding"]["id"], "F-2")
        self.assertEqual(tracked[1]["finding"]["severity"], "medium")
        self.assertEqual(tracked[1]["fix"], "pending")

    def test_legacy_heading_mints_carried_ids(self):
        legacy = "### [MEDIUM · verified · quality] bad name\n- where: `a.py:1`\n- evidence: x\n"
        d = ok(["findings-parse", "--text", legacy])
        self.assertEqual(d["tracked"][0]["finding"]["id"], "carried-1")

    def test_json_payload_normalizes_and_drops_fixed(self):
        payload = json.dumps([
            {"id": "F-9", "where": "a.py:1", "what": "x", "severity": "high"},
            {"id": "F-8", "where": "b.py:1", "what": "y", "severity": "low",
             "fixStatus": "fixed"},
        ])
        d = ok(["findings-parse", "--text", payload])
        self.assertEqual(len(d["tracked"]), 1)
        self.assertEqual(d["tracked"][0]["finding"]["id"], "F-9")
        self.assertEqual(d["tracked"][0]["finding"]["severity"], "high")

    def test_garbage_fails_loudly(self):
        msg = err(["findings-parse", "--text", "neither json nor a report"])
        self.assertIn("neither valid JSON nor a parseable review report", msg)

    def test_all_fixed_payload_fails_loudly(self):
        payload = json.dumps([{"where": "a.py:1", "what": "x", "fixStatus": "fixed"}])
        msg = err(["findings-parse", "--text", payload])
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

    def test_bad_report_data_fails_loudly(self):
        msg = err(["report", "--kind", "review", "--data", "@/no/such/file.json"])
        self.assertIn("report data invalid", msg)


ASK_CASES = [
    ("scout", {"base": "HEAD", "project": False, "files": ["src/a.py", "src/b.py"]}),
    ("scout", {"base": "HEAD", "project": True, "files": [f"m{i}.py" for i in range(45)],
               "repo_abs": "/tmp/repo"}),
    ("review", {"base": "HEAD~1", "files_n": 3, "lines": 120, "over_cap": False,
                "gate_line": "The repo's own checks all passed",
                "lens": {"focus": "logic errors."},
                "intent": "add caching", "scout_map": {"modules": [{"name": "m", "path": "src/m.py", "role": "r"}],
                                                        "conventions": ["c1"], "riskAreas": ["ra1"]}}),
    ("review-project", {"base": "HEAD", "files": ["a.py"], "candidates": 9, "part": 2, "parts": 3,
                        "gate_line": "checks passed", "lens": {"focus": "security."},
                        "repo_abs": "/tmp/repo"}),
    ("triage", {"base": "HEAD", "lens_label": "correctness", "intent": "fix bug",
                "findings": [{"where": "a.py:1", "what": "x", "evidence": "q", "severity": "high"}]}),
    ("triage-project", {"lens_label": "quality", "findings": []}),
    ("cross-lens", {"base": "HEAD", "kept": [{"where": "a.py:1", "what": "x", "evidence": "q",
                                              "severity": "low", "lens": "quality"}]}),
    ("confirm", {"base": "HEAD", "finding": {"where": "a.py:2", "what": "y", "evidence": "e",
                                             "severity": "medium", "lens": "security", "impact": "i"}}),
    ("confirm-project", {"finding": {"where": "a.py:2", "what": "y", "evidence": "e", "severity": "low"}}),
    ("final", {"base": "HEAD", "gate_line": "checks passed", "summary": [{"id": "F-1"}],
               "intent": "x", "scout_map": None}),
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
    ("fix-review", {"base": "HEAD", "gate_green": True, "paths": ["a.py", "b.py"]}),
    ("fix-review", {"base": "HEAD", "gate_green": False, "paths": ["a.py"], "repo_abs": "/tmp/r"}),
    ("loop-final", {"base": "HEAD", "rounds_used": 2, "gate_green": False, "changed_paths": ["a.py"],
                    "project": False,
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

    def test_systems_carry_the_three_lenses(self):
        d = ok(["systems"])
        self.assertEqual([l["label"] for l in d["lenses"]], ["correctness", "security", "quality"])
        for lens in d["lenses"] + [d["general"]]:
            self.assertTrue(lens["focus"].endswith("."))

    def test_unknown_ask_kind_fails_loudly(self):
        err(["ask", "--kind", "nope", "--ctx", "{}"])


if __name__ == "__main__":
    unittest.main()
