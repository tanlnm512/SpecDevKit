"""TC-020 — every element the loop grammar introduces has both a checker
gate and a machine reader (no gate without a reader, no reader without a
gate); TC-021 — loop history (rounds, verdicts, lineage, delivery facts)
is machine-readable from the spec's own records by the graph payload
builder and the release collector (NFR-004, NFR-005, FR-002, FR-007,
FR-008).

Run: python3 specs/loop-ready-docset/tests/test_gate_reader_sweep.py
GateReaderSweepTests.<method>
"""

import contextlib
import importlib.util
import io
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# spec-design last so its check/specstate/freeze/graph win the shared
# module names; spec-build's audit is a parity-pinned duplicate.
for _skill in ("spec-release", "spec-build", "spec-design"):
    _scripts = str(REPO / "skills" / _skill / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)

import check  # noqa: E402 - repo-relative scripts dir prepended above
import specstate  # noqa: E402
import freeze  # noqa: E402
import audit  # noqa: E402
import release  # noqa: E402

_graph_spec = importlib.util.spec_from_file_location(
    "graph", Path(REPO / "skills" / "spec-design" / "scripts") / "graph.py")
graph = importlib.util.module_from_spec(_graph_spec)
_graph_spec.loader.exec_module(graph)

FIXTURE = REPO / "skills" / "spec-design" / "examples" / "mini-spec"
TODAY = "2026-01-15"


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


def review_payload(spec_dir: Path, blocks: int = 0) -> str:
    """The saved review payload: fingerprint line, auditor digest, one
    ruling line per BLOCK."""
    text = (f"Docset fingerprint: {freeze.docset_fingerprint(spec_dir)}\n\n"
            f"digest: BLOCK {blocks} · WARN 0 · NIT 0 · worst none\n")
    return text + "".join(
        f"ruling: {n} — repaired\n" for n in range(1, blocks + 1))


def approve(spec_dir: Path, payload: Path) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        rc = freeze.record(spec_dir, spec_dir.parent.parent,
                           review=str(payload))
    assert rc == 0, "freeze.py --record refused the fixture"
    write(spec_dir / "spec.md", (spec_dir / "spec.md").read_text(
        encoding="utf-8").replace("**Status**: draft", "**Status**: approved"))


def checked(spec_dir: Path) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = check.main([str(spec_dir)])
    return code, buf.getvalue()


def delivered_spec(root: Path, name: str, spec_md: str,
                   task_md: str) -> Path:
    spec_dir = root / "specs" / name
    spec_dir.mkdir(parents=True)
    write(spec_dir / "spec.md", spec_md)
    write(spec_dir / "task.md", task_md)
    return spec_dir


def tag_repo(root: Path, tag: str) -> None:
    for argv in (["git", "init", "-q", str(root)],
                 ["git", "-C", str(root), "config", "user.email", "t@t"],
                 ["git", "-C", str(root), "config", "user.name", "t"],
                 ["git", "-C", str(root), "add", "."],
                 ["git", "-C", str(root), "commit", "-q", "-m", "seed"],
                 ["git", "-C", str(root), "tag", "-a", tag,
                  "-m", f"release {tag}"]):
        subprocess.run(argv, check=True, capture_output=True)


class GateReaderSweepTests(unittest.TestCase):
    # The loop grammar's six elements: each row's gate list and reader
    # list must both hold callables — an element with only one side fails
    # the sweep before any live probe runs.
    ELEMENTS = [
        ("fix-round note sub-lines",
         (check.fix_round_problems,),
         (specstate.task_entries, graph.round_sublines)),
        ("Verified burndown column",
         (check.verified_cell_problems,),
         (release.burndown_verdicts,)),
        ("hotfix target headers",
         (check.hotfix_target_problems,),
         (specstate.hotfix_target, release.spec_facts,
          release.generated_section)),
        ("one approvals file",
         (freeze.verify, check.main),
         (freeze.record,)),
        ("tech-spec Questions & options",
         (check.main,),
         (specstate.research_state,)),
        ("task.md delivery block",
         (audit.delivery_gates,),
         (audit.delivery_block, release.delivery_note)),
    ]

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

    def test_every_new_element_gated_and_readable(self):
        for name, gates, readers in self.ELEMENTS:
            with self.subTest(element=name):
                for probe in gates + readers:
                    self.assertTrue(callable(probe),
                                    f"{name}: {probe} missing")
        self.assertIn(
            "## Questions & options",
            (REPO / "skills" / "spec-design" / "templates" / "tech-spec.md"
             ).read_text(encoding="utf-8"),
            "the scaffold no longer ships the research gate's artifact")

        with self.subTest(element="fix-round note sub-lines"):
            entry = specstate.task_entries(self.THREE_ROUNDS)[0]
            self.assertEqual(check.fix_round_problems(
                specstate.task_entries(self.THREE_ROUNDS)), [])
            self.assertEqual([r.n for r in entry.rounds], [1, 2, 3])
            self.assertEqual(graph.round_sublines(entry), [
                "  - fix 1 — pytest test_parse fails on empty input",
                "  - fixed 1 — guard the empty case — pytest test_parse green",
                "  - fix 2 — pytest test_parse fails on unicode paths",
                "  - fixed 2 — normalize paths before parse — pytest green twice",
                "  - fix 3 — pytest test_parse fails on bom headers"])
            orphan_marker = self.THREE_ROUNDS.replace(
                "  - fix 3 — pytest test_parse fails on bom headers\n", "")
            problems = check.fix_round_problems(
                specstate.task_entries(orphan_marker))
            self.assertTrue(problems)
            self.assertIn("pairs with no `fix 3` sub-line", problems[0])

        with self.subTest(element="Verified burndown column"):
            table = ("# Tasks: demo\n\n"
                     "## Burndown\n"
                     "| Phase | Total | Done | Verified |\n"
                     "|-------|-------|------|----------|\n"
                     "| 1     | 1     | 1    | pass     |\n"
                     "| 2     | 1     | 0    |          |\n"
                     "| **Σ** | 2     | 1    |          |\n")
            self.assertEqual(check.verified_cell_problems(table), [])
            self.assertEqual(release.burndown_verdicts(table),
                             {"1": "pass", "2": ""})
            prose = table.replace("| 2     | 1     | 0    |          |",
                                  "| 2     | 1     | 0    | mostly   |")
            self.assertEqual(check.verified_cell_problems(prose), [
                "burndown: Verified cell on `2` row is `mostly` — must be "
                "empty or `pass`"])

        with self.subTest(element="hotfix target headers"):
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                hotfix = delivered_spec(
                    tmp, "crash-fix",
                    "# Spec: crash-fix\n\n**Type**: hotfix\n**Status**: done\n"
                    f"**Hotfix for**: v1.2.2\n**Fixes spec**: cart-flow\n"
                    f"**Created**: {TODAY}\n\n"
                    "## What\nThe cart stops crashing at checkout.\n\n"
                    "## Tasks\n- [x] T001 Ship the change (FR-001)\n"
                    f"  done {TODAY} — the proof command exits 0\n\n"
                    "Delivered: commit @ abc1234def\n",
                    "# Tasks: crash-fix\n")
                feature = delivered_spec(
                    tmp, "cart-flow",
                    "# Spec: cart-flow\n\n**Type**: feature\n"
                    "**Status**: done\n"
                    f"**Created**: {TODAY}\n\n## What\n"
                    "The cart tracks quantities per line.\n\n"
                    "## Tasks\n- [x] T001 Ship the change (FR-001)\n"
                    f"  done {TODAY} — the proof command exits 0\n\n"
                    "Delivered: commit @ def5678abc\n",
                    "# Tasks: cart-flow\n")
                tag_repo(tmp, "v1.2.2")
                self.assertEqual(
                    check.hotfix_target_problems(
                        hotfix, (hotfix / "spec.md").read_text(
                            encoding="utf-8"), tmp), [])
                self.assertEqual(specstate.hotfix_target(
                    (hotfix / "spec.md").read_text(encoding="utf-8")),
                    specstate.HotfixTarget(tag="v1.2.2", spec="cart-flow"))
                stray = (feature / "spec.md").read_text(encoding="utf-8")
                problems = check.hotfix_target_problems(
                    feature, stray + "**Hotfix for**: v1.2.2\n", tmp)
                self.assertTrue(problems)
                self.assertIn("`**Type**: feature` spec carries neither",
                              problems[0])
                bare = "# Spec: bare-fix\n\n**Type**: hotfix\n"
                self.assertIn("no lineage target",
                              check.hotfix_target_problems(
                                  feature, bare, tmp)[0])
                facts = release.spec_facts(tmp, hotfix, [])
                section = release.generated_section(
                    {"included": [facts, release.spec_facts(tmp, feature, [])],
                     "deps": [], "backlog": [], "outside": []},
                    "1.2.3", TODAY, release.changelog_style(""))
                fixed = self.group(section, "Fixed")
                added = self.group(section, "Added")
                self.assertIn("- The cart stops crashing at checkout."
                              " (crash-fix) — patches v1.2.2 — fixes"
                              " cart-flow", fixed)
                self.assertNotIn("crash-fix", added)

        with self.subTest(element="one approvals file"):
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                spec = scratch_docset(tmp)
                write(spec / "spec.md", (spec / "spec.md").read_text(
                    encoding="utf-8").replace(
                    "**Status**: draft", "**Status**: approved"))
                code, out = checked(spec)
                self.assertEqual(code, 1, out)
                self.assertIn("no approvals/approval.md", out)
                approve(spec, write(tmp / "review-payload.md",
                                    review_payload(spec)))
                record = (spec / "approvals" / "approval.md").read_text(
                    encoding="utf-8")
                self.assertIn("## Contract review", record)
                self.assertIn("## Freeze", record)
                self.assertIn("digest: BLOCK 0 · WARN 0 · NIT 0 · worst none",
                              record)
                self.assertFalse((spec / "approvals" / "review.md").exists())
                self.assertEqual(freeze.verify(spec, tmp), [])
                code, out = checked(spec)
                self.assertEqual(code, 0, out)

        with self.subTest(element="tech-spec Questions & options"):
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                spec = scratch_docset(tmp)
                (spec / "research.md").unlink()
                self.assertEqual(specstate.research_state(spec), "pending")
                code, out = checked(spec)
                self.assertIn("no resolved `## Questions & options` section",
                              out)
                tech = spec / "tech-spec.md"
                write(tech, tech.read_text(encoding="utf-8") +
                      "\n## Questions & options\n\n### Questions\n"
                      "not applicable — no open questions at Stage 0\n\n"
                      "### Options summary\nNone — nothing to evaluate\n")
                self.assertEqual(specstate.research_state(spec), "skip")
                code, out = checked(spec)
                self.assertEqual(code, 0, out)
                self.assertNotIn("no resolved `## Questions & options`", out)

        with self.subTest(element="task.md delivery block"):
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                spec = delivered_spec(
                    tmp, "demo",
                    "# Spec: demo\n\n**Type**: refactor\n**Status**: done\n",
                    "# Tasks: demo\n\n**Delivered**: commit @ abc1234def\n"
                    "- Docs impact: README.md\n"
                    "- Rollback: NFR-001 — revert the module commit\n"
                    "- Behavior preserved: TC-001 green at approval and now\n"
                    "## Burndown\n"
                    "| Phase | Total | Done | Verified |\n"
                    "|-------|-------|------|----------|\n"
                    "| 1     | 2     | 2    | pass     |\n"
                    "| **Σ** | 2     | 2    |          |\n")
                write(spec / "tech-spec.md",
                      "## Quality, threats, and rollback\n"
                      "| Requirement | Design consequence | "
                      "Rollback or verification |\n"
                      "|---|---|---|\n"
                      "| NFR-001 | keep the old path shippable | "
                      "revert the module commit |\n")
                block, where = audit.delivery_block(spec)
                self.assertEqual(where, "task.md delivery block")
                self.assertIn("Rollback: NFR-001 — revert the module commit",
                              block)
                gates = {name: st for name, st, _ in
                         audit.delivery_gates(spec, tmp, ["README.md"], True)}
                self.assertEqual(gates, {"DOCS IMPACT": "PASS",
                                         "ROLLBACK": "PASS",
                                         "WORK TYPE": "PASS"})
                self.assertEqual(release.delivery_note(spec), {
                    "docs_impact": "README.md",
                    "rollback": ["NFR-001 — revert the module commit"],
                    "behavior_preserved":
                        ["TC-001 green at approval and now"]})
                write(spec / "task.md", (spec / "task.md").read_text(
                    encoding="utf-8").replace(
                    "- Behavior preserved: TC-001 green at approval and now\n",
                    ""))
                gates = {name: st for name, st, _ in
                         audit.delivery_gates(spec, tmp, ["README.md"], True)}
                self.assertEqual(gates["WORK TYPE"], "FAIL")

    def group(self, section_text: str, heading: str) -> str:
        m = re.search(rf"^### {heading}\n\n(.*?)(?=\n### |\Z)",
                      section_text, re.M | re.S)
        self.assertIsNotNone(m, f"no ### {heading} group in:\n{section_text}")
        return m.group(1)

    def test_loop_history_machine_readable_by_ship_release_payload(self):
        task_md = (
            "# Tasks: demo\n\n"
            "**Delivered**: commit @ abc1234def\n"
            "- Docs impact: README.md\n"
            "- Rollback: NFR-001 — revert the module commit\n"
            "- Behavior preserved: TC-001 green at approval and now\n"
            "## Burndown\n"
            "| Phase | Total | Done | Verified |\n"
            "|-------|-------|------|----------|\n"
            "| 1     | 1     | 1    | pass     |\n"
            "| **Σ** | 1     | 1    |          |\n"
            "## Phase 1: rescue the parser (FR-001)\n"
            "- [x] T001 (fix 2/5) stop the parser crashing on empty input "
            "(FR-001)\n"
            "  - fix 1 — pytest test_parse fails on empty input\n"
            "  - fixed 1 — guard the empty case — pytest test_parse green\n"
            "  - fix 2 — pytest test_parse fails on bom headers\n")
        sublines = (
            "  - fix 1 — pytest test_parse fails on empty input",
            "  - fixed 1 — guard the empty case — pytest test_parse green",
            "  - fix 2 — pytest test_parse fails on bom headers")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            spec = delivered_spec(
                tmp, "demo",
                "# Spec: demo\n\n**Type**: hotfix\n**Status**: done\n"
                f"**Hotfix for**: v1.2.2\n**Created**: {TODAY}\n\n"
                "## What\nThe parser no longer crashes on empty input.\n\n"
                "## Tasks\n- [x] T001 Guard the empty case (FR-001)\n\n"
                "Delivered: commit @ abc1234def\n",
                task_md)
            entry = specstate.task_entries(task_md)[0]
            self.assertEqual(entry.fix_round, 2)
            self.assertEqual([r.n for r in entry.rounds], [1, 2])
            self.assertEqual(graph.round_sublines(entry), list(sublines))
            (spec / "notes").mkdir()
            write(spec / "notes" / "T001.md",
                  "## Fix round 2\n$ pytest -k parse\nattempted a cache "
                  "bust; the bom header still strips badly\n")
            payload = "\n".join(graph.fix_evidence_lines(spec, entry))
            for line in sublines:
                self.assertIn(line, payload)
            self.assertIn("attempted a cache bust", payload)

            facts = release.spec_facts(tmp, spec, [])
            self.assertEqual(facts["status"], "done")
            self.assertTrue(facts["delivered"])
            self.assertEqual(facts["verified"], {"1": "pass"})
            self.assertEqual(facts["hotfix_target"],
                             {"tag": "v1.2.2", "spec": ""})
            self.assertEqual(facts["delivery_note"], {
                "docs_impact": "README.md",
                "rollback": ["NFR-001 — revert the module commit"],
                "behavior_preserved":
                    ["TC-001 green at approval and now"]})


if __name__ == "__main__":
    unittest.main()
