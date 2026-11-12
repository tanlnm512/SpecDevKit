"""TC-001/TC-002/TC-003 — fix-round history on the task (FR-001, FR-002,
NFR-004, NFR-005).

Run: python3 specs/loop-ready-docset/tests/test_fix_round_history.py
FixRoundHistoryTests.<method>
"""

import contextlib
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
_SCRIPTS = str(REPO / "skills" / "spec-design" / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import check  # noqa: E402 - repo-relative scripts dir prepended above
import specstate  # noqa: E402
import freeze  # noqa: E402

_graph_spec = importlib.util.spec_from_file_location(
    "graph", Path(_SCRIPTS) / "graph.py")
graph = importlib.util.module_from_spec(_graph_spec)
_graph_spec.loader.exec_module(graph)

FIXTURE = REPO / "skills" / "spec-design" / "examples" / "mini-spec"


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def scratch_docset(tmp: Path, name: str = "demo") -> Path:
    """The mini-spec docset plus the repo it cites, copied so the survey's
    evidence stays real under the tmp root."""
    (tmp / "specs").mkdir(parents=True, exist_ok=True)
    dst = tmp / "specs" / name
    shutil.copytree(FIXTURE / "specs" / "mini-spec", dst)
    shutil.copytree(FIXTURE / "repo", tmp / "repo")
    return dst


def approve(spec_dir: Path) -> None:
    """The approve gate's two records as the current flow leaves them, so
    execute's per-task frontier is reachable."""
    approvals = spec_dir / "approvals"
    approvals.mkdir(exist_ok=True)
    write(approvals / "review.md",
          "# Contract review\n\nDocset fingerprint: "
          f"{freeze.docset_fingerprint(spec_dir)}\n\n"
          "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none\n")
    with contextlib.redirect_stdout(io.StringIO()):
        rc = freeze.record(spec_dir, spec_dir.parent.parent, force=True)
    assert rc == 0, "freeze.py --record refused the fixture"
    write(spec_dir / "spec.md", (spec_dir / "spec.md").read_text(
        encoding="utf-8").replace("**Status**: draft", "**Status**: approved"))


class FixRoundHistoryTests(unittest.TestCase):
    # Two landed rounds plus the third just opened — digest at open,
    # resolution and proof at close, one sub-line pair per round.
    THREE_ROUNDS = (
        "## Phase 1: rescue the parser (FR-001)\n"
        "- [ ] T001 (fix 3/5) third round on the flaky parser (FR-001)\n"
        "  - fix 1 — pytest test_parse fails on empty input\n"
        "  - fixed 1 — guard the empty case — pytest test_parse green\n"
        "  - fix 2 — pytest test_parse fails on unicode paths\n"
        "  - fixed 2 — normalize paths before parse — pytest green twice\n"
        "  - fix 3 — pytest test_parse fails on bom headers\n")

    def test_next_round_payload_carries_prior_rounds_verbatim(self):
        entry = specstate.task_entries(self.THREE_ROUNDS)[0]
        with tempfile.TemporaryDirectory() as td:
            spec_dir = Path(td) / "specs" / "demo"
            spec_dir.mkdir(parents=True)
            (spec_dir / "notes").mkdir()
            write(spec_dir / "notes" / "T001.md",
                  "## Fix round 3\n$ pytest -k parse\nattempted a cache "
                  "bust; the bom header still strips badly\n")
            payload = "\n".join(graph.fix_evidence_lines(spec_dir, entry))
        for line in ("fix 1 — pytest test_parse fails on empty input",
                     "fixed 1 — guard the empty case — pytest test_parse green",
                     "fix 2 — pytest test_parse fails on unicode paths",
                     "fixed 2 — normalize paths before parse — pytest green twice"):
            self.assertIn(line, payload)
        self.assertIn("attempted a cache bust", payload)
        self.assertEqual(
            entry.rounds[-1],
            specstate.FixRound(3, "pytest test_parse fails on bom headers",
                               "", "", False))

    def test_round_sublines_are_parsed_and_counted(self):
        entries = specstate.task_entries(self.THREE_ROUNDS)
        entry = entries[0]
        self.assertEqual([r.n for r in entry.rounds], [1, 2, 3])
        self.assertEqual(entry.fix_round, 3)
        self.assertTrue(entry.rounds[0].closed)
        self.assertFalse(entry.rounds[2].closed)
        self.assertEqual(check.fix_round_problems(entries), [])

    def test_task_at_five_round_cap_is_surfaced_not_retried(self):
        at_cap = ("## Phase 1: rescue the parser (FR-001)\n"
                  "- [ ] T001 (fix 5/5) rescue the stalled parser "
                  "(FR-001, FR-002)\n"
                  + "".join(
                      f"  - fix {i} — d{i}\n  - fixed {i} — r{i} — p{i}\n"
                      for i in range(1, 5))
                  + "  - fix 5 — pytest fails on bom headers\n")
        self.assertEqual(check.fix_round_problems(specstate.task_entries(at_cap)), [])
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            spec_dir = scratch_docset(tmp)
            approve(spec_dir)
            write(spec_dir / "task.md",
                  "# Tasks: demo\n\n"
                  "**Spec**: [spec.md](spec.md) | "
                  "**Plan**: [plan.md](plan.md)\n"
                  "Status reflects code state per [survey.md](survey.md), "
                  "not intent.\n\n"
                  "## Burndown\n"
                  "| Phase | Total | Done |\n"
                  "|-------|-------|------|\n"
                  "| 1     | 1     | 0    |\n"
                  "| **Σ** | 1     | 0    |\n\n" + at_cap)
            state = graph.compute_state(spec_dir, tmp)
            tasks = {t["id"]: t for t in state["nodes"]["execute"]["tasks"]}
            self.assertEqual(tasks["T001"]["state"], "at-fix-cap")
            self.assertIn("5/5", tasks["T001"]["reason"])
            self.assertEqual(state["counts"]["at-fix-cap"], 1)
            items = graph.frontier_payloads(state, spec_dir, tmp)
            self.assertEqual(
                [i["filename"] for i in items if i["node"] == "execute"], [])


if __name__ == "__main__":
    unittest.main()
