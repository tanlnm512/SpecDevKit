#!/usr/bin/env python3
"""Ruling tests for spec-ship's ship.py: `rule` records the owner's
thread labels; `comments` reads them back (D-006).

Same drivers as test_ship.py — real temp git repos and a gh stub whose
canned output is chosen per subcommand. Every assertion keys on the
exit code, the ruling line `notes/rulings.md` carries, and the
`ruling` field the contract puts on a thread.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_ship import PR_URL, git, gh_stub, ship


def thread(tid: str, resolved: bool = False) -> dict:
    """One review thread in the shape the GraphQL query returns."""
    return {"id": tid, "isResolved": resolved, "isOutdated": False,
            "path": "calc.py", "line": 3, "originalLine": None,
            "comments": {"nodes": [
                {"author": {"login": "reviewer"}, "body": "look here",
                 "url": "u"}]}}


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ship-rule-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q", "-b", "main")
        (self.root / "README").write_text("seed\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        git(self.root, "checkout", "-q", "-b", "ship-demo")
        git(self.root, "commit", "-q", "--allow-empty", "-m", "multiply lands")
        sha = git(self.root, "rev-parse", "HEAD")
        spec = self.root / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "spec.md").write_text(
            f"# Spec: demo\n\n"
            f"**Status**: done\n**Tier**: tiny\n**Type**: feature\n"
            f"**Branch**: `ship-demo`\n\n"
            f"## What\nx.\n\nDelivered: commit @ {sha}\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs: record the delivery")
        self.rulings = self.root / "specs" / "demo" / "notes" / "rulings.md"

    def pr_env(self, nodes: list[dict]):
        """A gh stub canned for `comments`: one open PR, the given
        threads."""
        view = {"number": 7, "url": PR_URL, "state": "OPEN",
                "isDraft": False, "title": "feat(demo): multiply lands",
                "headRefName": "ship-demo", "baseRefName": "main",
                "mergedAt": None, "mergeCommit": None,
                "reviewDecision": "REVIEW_REQUIRED", "reviews": [],
                "headRefOid": git(self.root, "rev-parse", "HEAD")}
        files = {
            "pr_view.json": json.dumps(view),
            "api_graphql.json": json.dumps(
                {"data": {"repository": {"pullRequest": {
                    "reviewThreads": {"nodes": nodes,
                                      "pageInfo": {"hasNextPage": False}}}}}}),
        }
        return gh_stub(files)

    def comments_json(self, env) -> dict:
        r = ship(self.root, "comments", "demo", "--json", env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout)

    def test_a_recorded_ruling_reaches_its_thread_and_the_payload(self):
        r = ship(self.root, "rule", "demo", "--thread", "PRRT_a",
                 "--label", "must-fix", "--why",
                 "the null path breaks FR-001")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ruled in specs/demo/notes/rulings.md: PRRT_a — "
                      "must-fix — the null path breaks FR-001", r.stdout)
        self.assertEqual(self.rulings.read_text().splitlines(),
                         ["- PRRT_a — must-fix — "
                          "the null path breaks FR-001"])
        ship(self.root, "rule", "demo", "--thread", "PRRT_b",
             "--label", "nit")
        with self.pr_env([thread("PRRT_a"), thread("PRRT_b")]) as env:
            payload = self.comments_json(env)
            human = ship(self.root, "comments", "demo", env=env)
        ruled = {t["id"]: t for t in payload["threads"]}
        self.assertEqual(ruled["PRRT_a"]["ruling"],
                         {"label": "must-fix",
                          "why": "the null path breaks FR-001",
                          "unresolved": True})
        self.assertEqual(ruled["PRRT_b"]["ruling"],
                         {"label": "nit", "why": "no reason given",
                          "unresolved": True})
        self.assertEqual(payload["inactive_rulings"], [])
        self.assertIn("keeps its label and is not to be reclassified",
                      payload["rulings_note"])
        self.assertIn("only unruled threads are open for classification",
                      payload["rulings_note"])
        self.assertIn("ruled must-fix: the null path breaks FR-001",
                      human.stdout)
        self.assertIn("a ruled thread keeps its label", human.stdout)

    def test_ruling_a_thread_again_replaces_the_first_in_place(self):
        ship(self.root, "rule", "demo", "--thread", "PRRT_a",
             "--label", "nit")
        ship(self.root, "rule", "demo", "--thread", "PRRT_b",
             "--label", "question", "--why", "answered upstream")
        again = ship(self.root, "rule", "demo", "--thread", "PRRT_a",
                     "--label", "must-fix", "--why", "real defect")
        self.assertEqual(again.returncode, 0, again.stdout)
        self.assertIn("re-ruled in", again.stdout)
        self.assertEqual(
            self.rulings.read_text().splitlines(),
            ["- PRRT_a — must-fix — real defect",
             "- PRRT_b — question — answered upstream"])

    def test_an_unknown_label_and_an_empty_id_are_usage_errors(self):
        r = ship(self.root, "rule", "demo", "--thread", "PRRT_a",
                 "--label", "maybe")
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid choice", r.stderr)
        r = ship(self.root, "rule", "demo", "--thread", "   ",
                 "--label", "nit")
        self.assertEqual(r.returncode, 2)
        self.assertIn("USAGE", r.stdout)
        self.assertFalse(self.rulings.exists(),
                         "a usage error writes no ruling")

    def test_a_ruling_off_the_pr_is_inactive_and_the_run_succeeds(self):
        ship(self.root, "rule", "demo", "--thread", "PRRT_gone",
             "--label", "nit", "--why", "declined")
        ship(self.root, "rule", "demo", "--thread", "PRRT_old",
             "--label", "question", "--why", "settled")
        with self.pr_env([thread("PRRT_a"),
                          thread("PRRT_old", resolved=True)]) as env:
            payload = self.comments_json(env)
            human = ship(self.root, "comments", "demo", env=env)
        self.assertEqual(payload["inactive_rulings"],
                         [{"thread": "PRRT_gone", "label": "nit",
                           "why": "declined", "unresolved": False},
                          {"thread": "PRRT_old", "label": "question",
                           "why": "settled", "unresolved": False}])
        self.assertEqual([t["id"] for t in payload["threads"]], ["PRRT_a"])
        self.assertIn("ruling for PRRT_gone (nit) is inactive", human.stdout)
        self.assertIn("ruling for PRRT_old (question) is inactive",
                      human.stdout)
        self.assertIn("it stays on file", human.stdout)
        self.assertEqual(len(self.rulings.read_text().splitlines()), 2,
                         "inactive rulings are kept, not dropped")

    def test_an_unruled_thread_carries_no_ruling(self):
        with self.pr_env([thread("PRRT_a"), thread("PRRT_b")]) as env:
            payload = self.comments_json(env)
        for t in payload["threads"]:
            self.assertIsNone(t["ruling"])
        self.assertEqual(payload["inactive_rulings"], [])

    def test_rule_refuses_a_specless_branch(self):
        r = ship(self.root, "rule", "ghost", "--thread", "x",
                 "--label", "nit")
        self.assertEqual(r.returncode, 4)
        self.assertIn("ship is spec-bound", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
