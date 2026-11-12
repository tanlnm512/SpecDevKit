"""TC-004/TC-005 — the ship-time retro and its archive reuse (FR-003).

Run: python3 specs/loop-ready-docset/tests/test_retro_delivery.py
RetroDeliveryTests.<method>
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "spec-build" / "scripts"
_RETRO = _SCRIPTS / "retro.py"
_ARCHIVE = _SCRIPTS / "archive.sh"
ENV = {**os.environ, "KIT_TELEMETRY": "off"}

APPROVED = "## Decisions\n### D-001: Pure function\n- why\n"
TASK_MD = (
    "## Phase 1: Multiply\n"
    "- [x] T001 Multiply (FR-001) (fixed 2/5)\n"
    "  - fix 1 — ParseError on a blank spec line\n"
    "  - fixed 1 — blank lines skipped before parse — make test\n"
    "  - fix 2 — unicode crash on BOM input\n"
    "  - fixed 2 — utf-8-sig decoding everywhere — make test\n"
    "- [x] T002 Tests (FR-001)\n"
    "Delivered: commit @ abc1234\n"
)
ROUND_1 = ("- T001 fix 1 — ParseError on a blank spec line"
           " — fixed: blank lines skipped before parse — proof: make test")
ROUND_2 = ("- T001 fix 2 — unicode crash on BOM input"
           " — fixed: utf-8-sig decoding everywhere — proof: make test")


def run(*argv, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([*map(str, argv)], cwd=str(cwd), env=ENV,
                          capture_output=True, text=True)


def make_spec(root: Path, name: str = "demo") -> Path:
    spec = root / "specs" / name
    (spec / "notes").mkdir(parents=True)
    (spec / "approvals").mkdir()
    (spec / "spec.md").write_text("# Spec: demo\n\n**Status**: done\n", encoding="utf-8")
    (spec / "tech-spec.md").write_text(APPROVED + "### D-002: Cache dropped mid-build\n",
                                       encoding="utf-8")
    (spec / "approvals" / "approval.md").write_text(
        f"- `tech-spec.md`: prefix sha256:{'0' * 64} length:{len(APPROVED.encode())}\n",
        encoding="utf-8")
    (spec / "task.md").write_text(TASK_MD, encoding="utf-8")
    (spec / "notes" / "delivery.md").write_text("Docs impact: README.md\n", encoding="utf-8")
    (root / "specs" / "BACKLOG.md").write_text(
        "# Backlog\n\n- demo — jitter untested (source: auditor WARN 2)\n"
        "- other — not ours (source: deviation)\n", encoding="utf-8")
    return spec


class RetroDeliveryTests(unittest.TestCase):
    def test_retro_written_at_ship_names_rounds_deviations_parked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec = make_spec(root)
            r = run(sys.executable, _RETRO, spec, "demo", root, cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            retro = (spec / "retro.md").read_text(encoding="utf-8")
            self.assertIn(ROUND_1, retro)
            self.assertIn(ROUND_2, retro)
            self.assertIn("| T001 | ticked | 2 |", retro)
            self.assertIn("Fix rounds: 2 across 2 task(s).", retro)
            self.assertIn("- D-002: Cache dropped mid-build (deviation, after approval)", retro)
            self.assertIn("- demo — jitter untested", retro)
            self.assertNotIn("not ours", retro)

    def test_archive_reuses_existing_retro_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec = make_spec(root)
            r = run(sys.executable, _RETRO, spec, "demo", root, cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            shipped = (spec / "retro.md").read_bytes()
            # A record lands after ship; a second write would fold it in.
            with open(spec / "tech-spec.md", "a", encoding="utf-8") as fh:
                fh.write("### D-003: Parked after ship\n")
            r = run("bash", _ARCHIVE, "demo", root, cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            archived = next((root / "specs" / "archive").glob("*-demo/retro.md"))
            self.assertEqual(archived.read_bytes(), shipped)
            self.assertNotIn("D-003", archived.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
