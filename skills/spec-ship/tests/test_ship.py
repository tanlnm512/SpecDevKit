#!/usr/bin/env python3
"""Unit tests for spec-ship's ship.py, driven at its command line.

Real temp git repos, a bare local disk remote, and no gh on PATH except
where a stub serves canned per-subcommand output. Every assertion keys
on the exit code and the line the contract acts on: a preflight row, a
stage in contracts/run.md's table, the record line, the evidence block.
The outward guarantee is asserted too: the commands that would leave
the machine appear only as preview text, and the remote's refs never
move (D-004).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SHIP = REPO_ROOT / "skills" / "spec-ship" / "scripts" / "ship.py"
SKILL_DIR_SH = REPO_ROOT / "skills" / "spec-ship" / "scripts" / "skill-dir.sh"

TODAY = "2026-01-15"
PR_URL = "https://github.com/acme/widget/pull/7"

CALC = "def multiply(a, b):\n    return a * b\n"

STUB = """#!/bin/sh
key="$1_$2"
if [ -f "$GH_STUB_DIR/$key.json" ]; then exec /bin/cat "$GH_STUB_DIR/$key.json"; fi
if [ -f "$GH_STUB_DIR/$key.err" ]; then /bin/cat "$GH_STUB_DIR/$key.err" >&2; exit 1; fi
echo "gh stub: no canned output for $key" >&2
exit 1
"""


def git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=kit",
         "-c", "user.email=kit@example.com", *args],
        capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: "
                             f"{done.stderr.strip() or done.stdout.strip()}")
    return done.stdout.strip()


_BIN: str | None = None


def _git_bindir() -> str:
    """A private bin dir exposing only git: gh can sit beside git on some
    runners, so gh-absence needs a PATH holding nothing else."""
    global _BIN
    if _BIN is None:
        _BIN = tempfile.mkdtemp(prefix="ship-bin-")
        (Path(_BIN) / "git").symlink_to(Path(shutil.which("git")).resolve())
    return _BIN


def env_no_gh() -> dict:
    return {**os.environ, "PATH": _git_bindir()}


@contextmanager
def gh_stub(files: dict[str, str]):
    """A gh whose canned output is chosen per subcommand: `<a>_<b>.json`
    is served for `gh <a> <b> …` (`pr_view.json`, `pr_checks.json`,
    `api_graphql.json`, `run_view.json`); the `.err` variant is served on
    stderr with exit 1. Usable several times inside the block."""
    bindir = tempfile.mkdtemp(prefix="gh-stub-")
    stub_dir = Path(bindir) / "canned"
    stub_dir.mkdir()
    for name, body in files.items():
        (stub_dir / name).write_text(body, encoding="utf-8")
    gh = Path(bindir) / "gh"
    gh.write_text(STUB, encoding="utf-8")
    gh.chmod(0o755)
    (Path(bindir) / "git").symlink_to(Path(shutil.which("git")).resolve())
    try:
        yield {**os.environ, "PATH": bindir, "GH_STUB_DIR": str(stub_dir)}
    finally:
        shutil.rmtree(bindir, ignore_errors=True)


def ship(repo: Path, *argv: str, env: dict | None = None,
         stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SHIP), *argv],
                          capture_output=True, text=True, timeout=120,
                          cwd=repo, input=stdin,
                          env=env or env_no_gh())


def remote_refs(bare: Path) -> set[str]:
    return set(git(bare, "for-each-ref", "--format=%(refname)"))


class ShipTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ship-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q", "-b", "main")
        (self.root / "README").write_text("seed\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        self.bare = Path(tempfile.mkdtemp(prefix="ship-bare-")) / "origin.git"
        self.bare.mkdir(parents=True)
        git(self.bare, "init", "-q", "--bare", "-b", "main")
        git(self.root, "remote", "add", "origin", str(self.bare))
        git(self.root, "push", "-q", "origin", "main")

    # -- fixtures ----------------------------------------------------------

    def deliver(self, name: str = "demo", tier: str = "tiny",
                branch: str = "ship-demo", subject: str = "multiply lands",
                docs: dict | None = None) -> str:
        """A delivered spec on its branch: the code commit is the delivery,
        the docs commit records it. Returns the delivered sha."""
        git(self.root, "checkout", "-q", "-b", branch)
        (self.root / "calc.py").write_text(CALC, encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--allow-empty", "-m", subject)
        sha = git(self.root, "rev-parse", "HEAD")
        spec = self.root / "specs" / name
        spec.mkdir(parents=True)
        if tier == "tiny":
            (spec / "spec.md").write_text(
                f"# Spec: {name}\n\n"
                f"**Status**: done\n**Tier**: tiny\n**Type**: feature\n"
                f"**Created**: {TODAY}\n**Branch**: `{branch}`\n\n"
                f"## What\nThe calculator gains integer multiplication.\n\n"
                f"## Why\nProducts need no repeated-addition workaround.\n\n"
                f"## Requirements\n"
                f"- **FR-001**: Multiply two integers and print the product.\n\n"
                f"## Tasks\n"
                f"- [x] T001 Multiply lands (FR-001) [P]\n"
                f"  Touches: `calc.py`\n"
                f"  Accept: `python3 calc.py multiply 6 7` prints 42\n"
                f"  done {TODAY} — `python3 calc.py multiply 6 7` prints 42\n\n"
                f"Delivered: commit @ {sha}\n", encoding="utf-8")
        else:
            (spec / "spec.md").write_text(
                f"# Spec: {name}\n\n"
                f"**Status**: done\n**Tier**: full\n**Type**: feature\n"
                f"**Created**: {TODAY}\n**Branch**: `{branch}`\n\n"
                f"## What\nThe calculator gains integer multiplication.\n\n"
                f"## Why\nProducts need no repeated-addition workaround.\n\n"
                f"## Requirements\n"
                f"- **FR-001**: Multiply two integers and print the product.\n"
                f"- **NFR-001**: Errors are one line and exit nonzero.\n"
                f"- **NFR-002**: Telemetry (not applicable on this tier).\n\n",
                encoding="utf-8")
            (spec / "task.md").write_text(
                f"# Tasks: {name}\n\n"
                f"- [x] T001 Multiply lands (FR-001) [P]\n"
                f"  Touches: `calc.py`\n"
                f"  done {TODAY} — pytest green, 2 tests\n"
                f"- [x] T002 Error path proven (NFR-001) [P]\n"
                f"  Touches: `calc.py`\n"
                f"  done {TODAY} — bad input exits 1\n\n"
                f"**Delivered**: commit @ {sha}\n", encoding="utf-8")
        for rel, body in (docs or {}).items():
            path = spec / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: record the delivery")
        return sha

    def undelivered(self, name: str = "demo") -> None:
        spec = self.root / "specs" / name
        spec.mkdir(parents=True)
        (spec / "spec.md").write_text(
            f"# Spec: {name}\n\n**Status**: done\n**Tier**: tiny\n\n"
            f"## What\nSomething.\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: a spec mid-build")

    def stage(self, name: str, *argv: str, env=None):
        return ship(self.root, "status", name, *argv, env=env)

    def pr_env(self, pr: dict | None = None, head_oid: str | None = None,
               checks: str | None = None, checks_err: str | None = None,
               threads: dict | str | None = None,
               run_view: str | None = None):
        """A gh stub canned for the PR-reading subcommands. Returns the
        context manager; every call inside it sees the same responses."""
        if head_oid is None:
            head_oid = git(self.root, "rev-parse", "HEAD")
        view = {**self.OPEN_PR, **(pr or {}), "headRefOid": head_oid}
        files: dict[str, str] = {"pr_view.json": json.dumps(view)}
        if checks is not None:
            files["pr_checks.json"] = checks
        if checks_err is not None:
            files["pr_checks.err"] = checks_err
        if threads is None:
            threads = {"nodes": [], "pageInfo": {"hasNextPage": False}}
        value = json.loads(threads) if isinstance(threads, str) else threads
        files["api_graphql.json"] = json.dumps(
            {"data": {"repository": {"pullRequest":
                                         {"reviewThreads": value}}}})
        if run_view is not None:
            files["run_view.json"] = run_view
        return gh_stub(files)

    def assertStage(self, r, stage: str) -> None:
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(r.stdout.startswith("status: specs/"), r.stdout)
        self.assertIn(f"— {stage}", r.stdout.splitlines()[0], r.stdout)

    # -- preflight ---------------------------------------------------------

    def test_preflight_passes_and_previews_the_push_without_running_it(self):
        self.deliver()
        refs_before = remote_refs(self.bare)
        r = ship(self.root, "preflight", "demo", "--base", "main")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("delivered: Delivered: commit @", r.stdout)
        self.assertIn("working tree clean", r.stdout)
        self.assertIn("next (on the user's yes): "
                      "git push --set-upstream origin ship-demo", r.stdout)
        self.assertEqual(remote_refs(self.bare), refs_before,
                         "the remote moved")
        result = json.loads(ship(self.root, "preflight", "demo", "--base",
                                 "main", "--json").stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["sync"]["state"], "unpushed")
        self.assertEqual(result["push"],
                         "git push --set-upstream origin ship-demo")

    def test_preflight_lists_manual_commands_when_gh_is_absent(self):
        self.deliver()
        git(self.root, "remote", "set-url", "origin",
            "https://github.com/acme/widget.git")
        r = ship(self.root, "preflight", "demo", "--base", "main",
                 "--json", env=env_no_gh())
        result = json.loads(r.stdout)
        gh_row = next(row for row in result["rows"] if row["name"] == "gh")
        self.assertEqual(gh_row["status"], "degraded")
        self.assertEqual(result["manual"][0],
                         "git push --set-upstream origin ship-demo")
        self.assertTrue(any("pr-body demo" in step for step in result["manual"]))
        self.assertIn("compare/main...ship-demo", result["manual"][-1])

    def test_preflight_refuses_a_specless_branch(self):
        r = ship(self.root, "preflight", "ghost", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("ship is spec-bound", r.stdout)
        self.assertIn("use your normal PR flow", r.stdout)

    def test_preflight_refuses_the_delivery_record_rows(self):
        self.undelivered()
        r = ship(self.root, "preflight", "demo", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("has no `Delivered: commit @ <sha>` record", r.stdout)
        self.assertIn("/spec-build ship demo", r.stdout)

        sha = self.deliver(name="status-demo", branch="ship-status")
        spec_md = self.root / "specs" / "status-demo" / "spec.md"
        spec_md.write_text(spec_md.read_text(encoding="utf-8")
                           .replace("**Status**: done", "**Status**: building"),
                           encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: mid-flight")
        r = ship(self.root, "preflight", "status-demo", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("Status is `building`, not `done`", r.stdout)

        self.deliver(name="skip", branch="ship-skip")
        skip_md = self.root / "specs" / "skip" / "spec.md"
        skip_sha = git(self.root, "rev-parse", "HEAD~1")
        skip_md.write_text(skip_md.read_text(encoding="utf-8")
                           .replace(f"Delivered: commit @ {skip_sha}",
                                    "Delivered: commit @ -"),
                           encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: non-git skip")
        r = ship(self.root, "preflight", "skip", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("non-git skip", r.stdout)

    def test_preflight_refuses_a_delivered_commit_off_the_branch(self):
        self.deliver()
        spec_md = self.root / "specs" / "demo" / "spec.md"
        spec_md.write_text(spec_md.read_text(encoding="utf-8").replace(
            git(self.root, "rev-parse", "HEAD~1"), "0" * 40), encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: bogus sha")
        r = ship(self.root, "preflight", "demo", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("does not resolve in this repo", r.stdout)

        git(self.root, "checkout", "-q", "--orphan", "elsewhere")
        (self.root / "orphan.txt").write_text("x\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "orphan")
        orphan = git(self.root, "rev-parse", "HEAD")
        git(self.root, "checkout", "-q", "ship-demo")
        spec_md.write_text(spec_md.read_text(encoding="utf-8").replace(
            "0" * 40, orphan), encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: off-branch sha")
        r = ship(self.root, "preflight", "demo", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("is not on this branch", r.stdout)

    def test_preflight_refuses_a_dirty_tree_and_the_default_branch(self):
        self.deliver()
        (self.root / "stray.txt").write_text("uncommitted\n", encoding="utf-8")
        r = ship(self.root, "preflight", "demo", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("the working tree is dirty", r.stdout)
        self.assertIn("ship never publishes around uncommitted work", r.stdout)
        (self.root / "stray.txt").unlink()

        git(self.root, "checkout", "-q", "main")
        git(self.root, "cherry-pick", "ship-demo")
        r = ship(self.root, "preflight", "demo", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("ship never pushes it", r.stdout)

    def test_preflight_refuses_a_missing_remote(self):
        no_remote = Path(tempfile.mkdtemp(prefix="ship-norem-"))
        self.addCleanup(shutil.rmtree, no_remote, ignore_errors=True)
        git(no_remote, "init", "-q", "-b", "main")
        git(no_remote, "checkout", "-q", "-b", "ship-demo")
        spec = no_remote / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "spec.md").write_text(
            f"# Spec: demo\n\n**Status**: done\n**Tier**: tiny\n\n"
            f"## What\nx.\n\nDelivered: commit @ -\n", encoding="utf-8")
        git(no_remote, "add", "-A")
        git(no_remote, "commit", "-qm", "docs only")
        r = ship(no_remote, "preflight", "demo", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("no git remote", r.stdout)

    def test_preflight_refuses_when_diverged(self):
        self.deliver()
        git(self.root, "push", "-q", "-u", "origin", "ship-demo")
        twin = self.twin()
        (twin / "remote.txt").write_text("x\n", encoding="utf-8")
        git(twin, "add", "-A")
        git(twin, "commit", "-qm", "remote commit")
        git(twin, "push", "-q", "origin", "ship-demo")
        git(self.root, "fetch", "-q", "origin")
        r = ship(self.root, "preflight", "demo", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("commit(s) this branch lacks", r.stdout)
        self.assertIn("ship never force-pushes", r.stdout)

    def twin(self) -> Path:
        """A second clone of the bare remote, for remote-side commits."""
        twin = Path(tempfile.mkdtemp(prefix="ship-twin-"))
        self.addCleanup(shutil.rmtree, twin, ignore_errors=True)
        subprocess.run(["git", "clone", "-q", str(self.bare), str(twin)],
                       check=True)
        git(twin, "checkout", "-q", "ship-demo")
        return twin

    # -- pr-body -----------------------------------------------------------

    def test_pr_body_renders_every_contract_section(self):
        sha = self.deliver(tier="full", subject="feat(demo): multiply lands",
                           docs={
                               "test.md": "## TC-001 multiply\n## TC-002 error\n",
                               "notes/delivery.md":
                                   "Docs impact: README updated\n"
                                   "Rollback: Exposure — 10% of tenants first\n",
                               "tech-spec.md":
                                   "## Quality, threats, and rollback\n"
                                   "| Requirement | Design consequence | "
                                   "Rollback or verification |\n|---|---|---|\n"
                                   "| NFR-001 | one-line errors | "
                                   "revert the module commit |\n"
                                   "| NFR-002 | telemetry | — |\n",
                               "plan.md":
                                   "## Delivery\n### Rollout\n"
                                   "- **Exposure**: 10% of tenants\n",
                           })
        (self.root / "requirements.txt").write_text("left-pad==1.0\n",
                                                    encoding="utf-8")
        (self.root / "specs" / "BACKLOG.md").write_text(
            "# Backlog\n\n- demo — jitter untested (source: auditor WARN 2)\n"
            "- other — not ours\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: ship inputs")
        r = ship(self.root, "pr-body", "demo", "--base", "main")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("title: feat(demo): multiply lands", r.stdout)
        self.assertIn("next (on the user's yes to this preview): "
                      "gh pr create --base main --head ship-demo", r.stdout)
        body = json.loads(ship(self.root, "pr-body", "demo", "--base",
                               "main", "--json").stdout)["body"]
        self.assertIn(f"Delivered: commit @ {sha[:7]}", body)
        self.assertIn("**FR-001**:", body)
        self.assertNotIn("NFR-002", body, "not-applicable NFRs are dropped")
        self.assertIn("2/2 tasks ticked", body)
        self.assertIn("2 test cases in the contract", body)
        self.assertIn("pytest green, 2 tests", body)
        self.assertIn("## Docs impact", body)
        self.assertIn("README updated", body)
        self.assertIn("Independent `/spec-review`: none on record.", body)
        self.assertIn("`requirements.txt`", body)
        self.assertIn("added: `left-pad==1.0`", body)
        self.assertIn("**Exposure**: 10% of tenants", body)
        self.assertIn("NFR-001: revert the module commit", body)
        self.assertIn("Ruling — Exposure — 10% of tenants first", body)
        self.assertIn("jitter untested", body)
        self.assertNotIn("not ours", body)

    def test_pr_body_renders_the_tiny_fallbacks(self):
        self.deliver()
        r = ship(self.root, "pr-body", "demo", "--base", "main")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("1 Accept commands in the contract", r.stdout)
        self.assertIn("not recorded — the delivery note has no "
                      "`Docs impact:` line", r.stdout)
        self.assertIn("none — tiny tier: reverting the delivery commit "
                      "is the rollback", r.stdout)
        self.assertIn("none — no dependency manifest changed", r.stdout)

    def test_pr_body_refuses_an_undelivered_spec(self):
        self.undelivered()
        r = ship(self.root, "pr-body", "demo", "--base", "main")
        self.assertEqual(r.returncode, 4)
        self.assertIn("not delivered", r.stdout)

    # -- record ------------------------------------------------------------

    def test_record_writes_beside_delivered_in_the_same_bold_form(self):
        self.deliver(tier="full")
        r = ship(self.root, "record", "demo", "--pr", PR_URL)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(f"recorded in specs/demo/task.md: Shipped: PR {PR_URL}",
                      r.stdout)
        holder = (self.root / "specs" / "demo" / "task.md").read_text()
        self.assertRegex(
            holder, r"\*\*Delivered\*\*: commit @ \S+\n\*\*Shipped\*\*: "
                    rf"PR {re.escape(PR_URL)}\n")

    def test_record_is_idempotent_and_replaces_an_older_url(self):
        self.deliver()
        r = ship(self.root, "record", "demo", "--pr", PR_URL)
        self.assertEqual(r.returncode, 0, r.stdout)
        again = ship(self.root, "record", "demo", "--pr", PR_URL, "--json")
        self.assertEqual(json.loads(again.stdout)["changed"], False)
        other = "https://github.com/acme/widget/pull/9"
        replaced = ship(self.root, "record", "demo", "--pr", other, "--json")
        self.assertEqual(json.loads(replaced.stdout)["changed"], True)
        holder = (self.root / "specs" / "demo" / "spec.md").read_text()
        self.assertEqual(holder.count("Shipped: PR"), 1)
        self.assertIn(f"Shipped: PR {other}", holder)
        self.assertNotIn(PR_URL, holder)

    def test_record_lands_in_tiny_evidence_the_one_unfrozen_section(self):
        self.deliver()
        r = ship(self.root, "record", "demo", "--pr", PR_URL)
        self.assertEqual(r.returncode, 0, r.stdout)
        spec = (self.root / "specs" / "demo" / "spec.md").read_text()
        self.assertTrue(spec.rstrip().endswith(
            f"## Evidence\n\nShipped: PR {PR_URL}"))
        # an existing § Evidence takes the line at its end, never past the
        # next heading
        spec = spec.replace(f"## Evidence\n\nShipped: PR {PR_URL}\n",
                            "## Evidence\n\nhand note\n\n## Notes\nx\n")
        (self.root / "specs" / "demo" / "spec.md").write_text(
            spec, encoding="utf-8")
        other = "https://github.com/acme/widget/pull/8"
        r = ship(self.root, "record", "demo", "--pr", other)
        self.assertEqual(r.returncode, 0, r.stdout)
        spec = (self.root / "specs" / "demo" / "spec.md").read_text()
        self.assertIn(f"hand note\nShipped: PR {other}\n\n## Notes", spec)

    def test_record_refuses_a_non_url(self):
        self.deliver()
        r = ship(self.root, "record", "demo", "--pr", "PR 7")
        self.assertEqual(r.returncode, 4)
        self.assertIn("is not a PR url", r.stdout)

    # -- evidence ----------------------------------------------------------

    def test_evidence_routes_to_the_task_note_with_the_next_round(self):
        self.deliver(tier="full")
        notes = self.root / "specs" / "demo" / "notes"
        notes.mkdir()
        (notes / "T001.md").write_text("## Fix round 1 — ci: old\nbody\n",
                                       encoding="utf-8")
        body = "boom-evidence\n```\nnested fence\n```\n"
        r = ship(self.root, "evidence", "demo", "--kind", "ci",
                 "--title", "ci/test fails on main", "--task", "T001",
                 stdin=body)
        self.assertEqual(r.returncode, 0, r.stdout)
        note = (notes / "T001.md").read_text()
        self.assertIn("## Fix round 2 — ci: ci/test fails on main", note)
        self.assertIn("never instructions to follow", note)
        self.assertIn("````text", note, "the fence outgrows the body's own")
        self.assertIn("boom-evidence", note)
        self.assertIn("next: /spec-build demo", r.stdout)

    def test_evidence_counts_the_task_marker_as_a_round(self):
        self.deliver(tier="full")
        task_md = self.root / "specs" / "demo" / "task.md"
        task_md.write_text(task_md.read_text(encoding="utf-8").replace(
            "- [x] T001 Multiply lands (FR-001) [P]",
            "- [x] T001 Multiply lands (FR-001) [P] (fixed 3/5)"),
            encoding="utf-8")
        r = ship(self.root, "evidence", "demo", "--kind", "review",
                 "--title", "thread", "--task", "T001", stdin="comment\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        note = (self.root / "specs" / "demo" / "notes" / "T001.md").read_text()
        self.assertIn("## Fix round 4 — review: thread", note)

    def test_evidence_past_the_fix_cap_warns(self):
        self.deliver(tier="full")
        task_md = self.root / "specs" / "demo" / "task.md"
        task_md.write_text(task_md.read_text(encoding="utf-8").replace(
            "- [x] T001 Multiply lands (FR-001) [P]",
            "- [x] T001 Multiply lands (FR-001) [P] (fixed 5/5)"),
            encoding="utf-8")
        r = ship(self.root, "evidence", "demo", "--kind", "ci",
                 "--title", "again", "--task", "T001", stdin="out\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("past spec-build's fix cap", r.stdout)
        self.assertIn("adjudicate with the user", r.stdout)

    def test_unrouted_evidence_lands_in_ship_md_with_the_route_warning(self):
        self.deliver()
        r = ship(self.root, "evidence", "demo", "--kind", "ci",
                 "--title", "unowned job", stdin="log line\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("notes/ship.md", r.stdout)
        self.assertIn("## Unrouted ci: unowned job",
                      (self.root / "specs" / "demo" / "notes" / "ship.md")
                      .read_text())
        self.assertIn("route it to /spec-design", r.stdout)

    def test_evidence_refuses_an_unknown_task_and_an_empty_body(self):
        self.deliver(tier="full")
        r = ship(self.root, "evidence", "demo", "--kind", "ci",
                 "--title", "x", "--task", "T999", stdin="out\n")
        self.assertEqual(r.returncode, 4)
        self.assertIn("T999 is not a live task", r.stdout)
        r = ship(self.root, "evidence", "demo", "--kind", "ci",
                 "--title", "x", stdin="   \n")
        self.assertEqual(r.returncode, 4)
        self.assertIn("no evidence given", r.stdout)

    # -- status: the local-only stages --------------------------------------

    def test_status_stages_the_specless_and_not_delivered_states(self):
        r = self.stage("ghost")
        self.assertEqual(r.returncode, 4)
        self.assertIn("ship is spec-bound", r.stdout)

        self.undelivered()
        r = self.stage("demo")
        self.assertStage(r, "not-delivered")
        self.assertIn("next: /spec-build ship demo", r.stdout)

    def test_status_stages_off_branch_dirty_unpushed_diverged_shipped(self):
        self.deliver()

        git(self.root, "checkout", "-q", "main")
        git(self.root, "cherry-pick", "ship-demo")
        r = self.stage("demo")
        self.assertStage(r, "off-branch")
        self.assertIn("no PR on record", r.stdout)
        git(self.root, "checkout", "-q", "ship-demo")
        git(self.root, "branch", "-q", "-D", "main")

        (self.root / "stray.txt").write_text("dirty\n", encoding="utf-8")
        r = self.stage("demo")
        self.assertStage(r, "dirty-tree")
        self.assertIn("1 uncommitted path(s)", r.stdout)
        (self.root / "stray.txt").unlink()

        r = self.stage("demo")
        self.assertStage(r, "unpushed")
        self.assertIn("preflight", r.stdout)

        git(self.root, "push", "-q", "-u", "origin", "ship-demo")
        twin = self.twin()
        (twin / "remote.txt").write_text("x\n", encoding="utf-8")
        git(twin, "add", "-A")
        git(twin, "commit", "-qm", "remote commit")
        git(twin, "push", "-q", "origin", "ship-demo")
        git(self.root, "fetch", "-q", "origin")
        r = self.stage("demo")
        self.assertStage(r, "diverged")
        self.assertIn("ship never force-pushes", r.stdout)

        # integrate the remote's commits yourself, then keep going
        git(self.root, "pull", "--rebase", "-q", "origin", "ship-demo")

        ship(self.root, "record", "demo", "--pr", PR_URL)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: the shipped record")
        git(self.root, "push", "-q", "origin", "ship-demo")
        r = self.stage("demo")
        self.assertStage(r, "shipped")
        self.assertIn(f"open {PR_URL}", r.stdout)

        git(self.root, "push", "-q", "origin", "ship-demo:main")
        r = self.stage("demo")
        self.assertStage(r, "merged")
        self.assertIn("the delivered commit is on `origin/main`", r.stdout)

    def test_status_stages_merged_via_the_delivered_commit_on_the_base(self):
        self.deliver()
        git(self.root, "push", "-q", "origin", "ship-demo:main")
        r = self.stage("demo")
        self.assertStage(r, "merged")
        self.assertIn("the record stands", r.stdout)

    # -- status: the PR lifecycle through gh stubs --------------------------

    OPEN_PR = {
        "number": 7, "url": PR_URL, "state": "OPEN", "isDraft": False,
        "title": "feat(demo): multiply lands", "headRefName": "ship-demo",
        "baseRefName": "main", "mergedAt": None, "mergeCommit": None,
        "reviewDecision": "REVIEW_REQUIRED", "reviews": [],
    }

    def test_status_reads_an_open_green_pr_as_awaiting_merge(self):
        self.deliver()
        git(self.root, "push", "-q", "-u", "origin", "ship-demo")
        with self.pr_env(checks='[{"name": "ci", "bucket": "pass"}]') as env:
            r = self.stage("demo", env=env)
        self.assertStage(r, "awaiting-merge")
        self.assertIn("checks: green · unresolved threads: 0 · "
                      "review decision: REVIEW_REQUIRED", r.stdout)
        self.assertIn("the merge is the human's", r.stdout)
        self.assertIn("not on record: ship.py record demo --pr " + PR_URL,
                      r.stdout)

    def test_status_stages_ci_red_pending_and_closed(self):
        self.deliver()
        git(self.root, "push", "-q", "-u", "origin", "ship-demo")
        with self.pr_env(checks='[{"name": "ci", "bucket": "fail"}]') as env:
            r = self.stage("demo", env=env)
        self.assertStage(r, "ci-red")
        self.assertIn("next: /spec-ship checks demo", r.stdout)

        with self.pr_env(checks='[{"name": "ci", "bucket": "pending"}]') as env:
            r = self.stage("demo", env=env)
        self.assertStage(r, "ci-pending")
        self.assertIn("wait for CI", r.stdout)

        with self.pr_env(pr={"state": "CLOSED"}) as env:
            r = self.stage("demo", env=env)
        self.assertStage(r, "pr-closed")
        self.assertIn("closed without merging", r.stdout)

    def test_status_after_merge_reads_intact_and_rewritten_history(self):
        self.deliver()
        git(self.root, "push", "-q", "-u", "origin", "ship-demo")
        merge_commit = git(self.root, "commit-tree", "HEAD^{tree}",
                           "-p", "HEAD", "-m", "merge")
        with self.pr_env(pr={"state": "MERGED",
                             "mergeCommit": {"oid": merge_commit}}) as env:
            r = self.stage("demo", env=env)
        self.assertStage(r, "merged")
        self.assertIn("merged as " + merge_commit[:12], r.stdout)
        self.assertIn("the record stands", r.stdout)

        # a squash-style rewrite: the twin lands on the base, the delivered
        # sha does not. The tree differs from the delivery's (the squash
        # touches the README), so the twin is its own commit even in the
        # same second.
        subject = git(self.root, "log", "-1", "--format=%s", "HEAD~1")
        git(self.root, "checkout", "-q", "-b", "squashed", "origin/main")
        (self.root / "calc.py").write_text(CALC, encoding="utf-8")
        (self.root / "README").write_text("seed\n\nsquashed on main\n",
                                          encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", subject)
        git(self.root, "commit", "--allow-empty", "-qm", "docs on main")
        squash_tip = git(self.root, "rev-parse", "HEAD")
        git(self.root, "checkout", "-q", "ship-demo")
        with self.pr_env(pr={"state": "MERGED",
                             "mergeCommit": {"oid": squash_tip}}) as env:
            r = self.stage("demo", env=env)
        self.assertStage(r, "merged-record-stale")
        self.assertIn("merged by rebase as", r.stdout)
        self.assertIn("--redeliver", r.stdout)

    # -- checks -------------------------------------------------------------

    def test_checks_maps_buckets_to_verdicts_and_routes(self):
        self.deliver()
        git(self.root, "push", "-q", "-u", "origin", "ship-demo")

        with self.pr_env(checks='[{"name": "ci", "bucket": "pass"}]') as env:
            r = ship(self.root, "checks", "demo", env=env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("— GREEN", r.stdout)
        self.assertIn("next: /spec-ship comments demo", r.stdout)

        red = ('[{"name": "ci", "bucket": "fail", "link": '
               '"https://github.com/acme/widget/actions/runs/4123"}]')
        with self.pr_env(checks=red) as env:
            r = ship(self.root, "checks", "demo", env=env)
        self.assertIn("— RED", r.stdout)
        self.assertIn("never fix code here", r.stdout)
        self.assertIn("ship.py evidence demo --kind ci", r.stdout)
        self.assertIn("/spec-build demo", r.stdout)
        self.assertIn("untrusted", r.stdout)

        with self.pr_env(checks='[{"name": "ci", "bucket": "pending"}]') as env:
            r = ship(self.root, "checks", "demo", env=env)
        self.assertIn("— PENDING", r.stdout)
        self.assertIn("CI is still running", r.stdout)

        with self.pr_env(checks_err="no checks reported on this PR") as env:
            r = ship(self.root, "checks", "demo", env=env)
        self.assertIn("— NONE", r.stdout)
        self.assertIn("that is not a pass; say so", r.stdout)

    def test_checks_flags_a_stale_pr_head_and_tails_failed_logs(self):
        self.deliver()
        git(self.root, "push", "-q", "-u", "origin", "ship-demo")
        stale = "0123456789abcdef" * 2 + "01234567"
        red = ('[{"name": "ci", "bucket": "fail", "link": '
               '"https://github.com/acme/widget/actions/runs/4123"}]')
        run_view = "error: boom\nmid line\nlast failing line\n"
        with self.pr_env(checks=red, head_oid=stale,
                         run_view=run_view) as env:
            r = ship(self.root, "checks", "demo", "--logs", env=env)
            self.assertIn("local HEAD is", r.stdout)
            self.assertIn("these checks describe", r.stdout)
            self.assertIn("what was pushed", r.stdout)
            # run_view is served for `gh run view 4123 --log-failed`
            result = json.loads(ship(self.root, "checks", "demo", "--logs",
                                     "--json", env=env).stdout)
            self.assertEqual(result.get("verdict"), "red", result)
            self.assertTrue(result["stale"], result)
            self.assertIn("boom", result["rows"][0]["log_tail"])
            self.assertEqual(result["rows"][0]["log_tail"].splitlines()[-1],
                             "last failing line")

    # -- comments -----------------------------------------------------------

    def test_comments_lists_unresolved_threads_with_task_candidates(self):
        self.deliver()
        threads = {"nodes": [
            {"id": "T1", "isResolved": True, "isOutdated": False,
             "path": "calc.py", "line": 1, "originalLine": None,
             "comments": [{"author": {"login": "reviewer"},
                           "body": "resolved already", "url": "u"}]},
            {"id": "T2", "isResolved": False, "isOutdated": False,
             "path": "calc.py", "line": 3, "originalLine": None,
             "comments": {"nodes": [
                 {"author": {"login": "reviewer"},
                  "body": "this breaks negative products\nnit: doc",
                  "url": "u2"}]}},
            {"id": "T3", "isResolved": False, "isOutdated": True,
             "path": "deleted.py", "line": None, "originalLine": 9,
             "comments": {"nodes": [
                 {"author": None, "body": "ghost", "url": "u3"}]}},
        ], "pageInfo": {"hasNextPage": False}}
        pr = {"reviewDecision": "CHANGES_REQUESTED",
              "reviews": [{"author": {"login": "reviewer"},
                           "state": "CHANGES_REQUESTED", "body": "please"}]}
        with self.pr_env(pr=pr, threads=threads) as env:
            r = ship(self.root, "comments", "demo", env=env)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("2 unresolved thread(s), review decision: "
                          "CHANGES_REQUESTED", r.stdout)
            self.assertIn("T2 calc.py:3 [T001]", r.stdout)
            self.assertIn("T3 deleted.py:9 [no task touches it] (outdated)",
                          r.stdout)
            self.assertIn("| reviewer: this breaks negative products", r.stdout)
            self.assertIn("addPullRequestReviewThreadReply", r.stdout)
            self.assertIn("on the user's yes to its shown text", r.stdout)
            result = json.loads(ship(self.root, "comments", "demo",
                                     "--json", env=env).stdout)
        self.assertEqual(len(result["threads"]), 2)
        self.assertEqual(result["reviews"],
                         [{"author": "reviewer",
                           "state": "CHANGES_REQUESTED", "body": "please"}])

    def test_comments_reports_truncation(self):
        self.deliver()
        threads = {"nodes": [], "pageInfo": {"hasNextPage": True}}
        with self.pr_env(threads=threads) as env:
            r = ship(self.root, "comments", "demo", env=env)
        self.assertIn("more than 100 threads", r.stdout)

    # -- the outward guarantee ----------------------------------------------

    def test_the_run_never_touches_the_remote_or_the_history(self):
        self.deliver()
        refs_before = remote_refs(self.bare)
        log_before = git(self.root, "reflog", "--format=%H")
        for argv in (("preflight", "demo", "--base", "main"),
                     ("pr-body", "demo", "--base", "main"),
                     ("status", "demo"),
                     ("checks", "demo"),
                     ("comments", "demo")):
            ship(self.root, *argv)
        self.assertEqual(remote_refs(self.bare), refs_before)
        self.assertEqual(git(self.root, "reflog", "--format=%H"), log_before)


class SkillDirTests(unittest.TestCase):
    def test_resolves_its_own_skill_dir(self):
        r = subprocess.run(["bash", str(SKILL_DIR_SH)], capture_output=True,
                           text=True, cwd=str(REPO_ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(Path(r.stdout.strip()), SKILL_DIR_SH.parent.parent)

    def test_honors_claude_plugin_root(self):
        plugin = Path(tempfile.mkdtemp(prefix="ship-plugin-"))
        self.addCleanup(shutil.rmtree, plugin, ignore_errors=True)
        (plugin / "SKILL.md").write_text("stub\n", encoding="utf-8")
        alone = Path(tempfile.mkdtemp(prefix="ship-alone-"))
        self.addCleanup(shutil.rmtree, alone, ignore_errors=True)
        script = alone / "skill-dir.sh"
        shutil.copy(SKILL_DIR_SH, script)
        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin)}
        r = subprocess.run(["bash", str(script)], capture_output=True,
                           text=True, env=env, cwd=str(alone))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(Path(r.stdout.strip()), plugin)

    def test_fails_loudly_when_no_skill_dir_exists(self):
        alone = Path(tempfile.mkdtemp(prefix="ship-alone-"))
        self.addCleanup(shutil.rmtree, alone, ignore_errors=True)
        script = alone / "skill-dir.sh"
        shutil.copy(SKILL_DIR_SH, script)
        env = {**os.environ, "HOME": str(alone)}
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        r = subprocess.run(["bash", str(script)], capture_output=True,
                           text=True, env=env, cwd=str(alone))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no spec-ship skill dir", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
