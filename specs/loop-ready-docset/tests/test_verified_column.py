"""TC-006/TC-007 — the burndown Verified column (FR-004).

Run: python3 specs/loop-ready-docset/tests/test_verified_column.py
VerifiedColumnTests.<method>
"""

import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parents[3] / "skills" / "spec-design" / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import check  # noqa: E402 - repo-relative scripts dir prepended above


class VerifiedColumnTests(unittest.TestCase):
    # Two-phase delivered plan: phase 1 finished all-green, phase 2 has
    # one red proof. The verdicts are what the delivery pass wrote —
    # `pass` only where a phase went all-green, empty otherwise.
    DELIVERED = (
        "# Tasks: demo\n\n"
        "## Burndown\n"
        "| Phase | Total | Done | Verified |\n"
        "|-------|-------|------|----------|\n"
        "| 1     | 1     | 1    | pass     |\n"
        "| 2     | 1     | 0    |          |\n"
        "| **Σ** | 2     | 1    |          |\n"
    )

    def row_verdicts(self, task: str) -> dict[str, str]:
        verdicts: dict[str, str] = {}
        for line in task.splitlines():
            m = check.BD_ROW.match(line)
            if m and check.bd_label(m.group(1))[0] == "data":
                verdicts[m.group(1).strip()] = m.group(4).strip()
        return verdicts

    def test_verdict_set_only_on_all_green_phase(self):
        self.assertEqual(self.row_verdicts(self.DELIVERED),
                         {"1": "pass", "2": ""})
        self.assertEqual(check.verified_cell_problems(self.DELIVERED), [])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "task.md"
            path.write_text(self.DELIVERED, encoding="utf-8")
            out = check.fix_burndown(self.DELIVERED, path, {1: 1, 2: 1},
                                     {1: 1, 2: 0})
            self.assertEqual(out, self.DELIVERED)

    def test_repair_preserves_recorded_verdicts(self):
        table = (
            "# Tasks: demo\n\n"
            "## Burndown\n"
            "| Phase | Total | Done | Verified |\n"
            "|-------|-------|------|----------|\n"
            "| 1     | 3     | 0    | pass     |\n"
            "| 2     | 2     | 1    |          |\n"
            "| **Σ** | 5     | 1    |          |\n"
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "task.md"
            path.write_text(table, encoding="utf-8")
            out = check.fix_burndown(table, path, {1: 2, 2: 2}, {1: 2, 2: 1})
            self.assertIn("| 1 | 2 | 2 | pass     |", out)
            self.assertIn("| 2     | 2     | 1    |          |", out)
            self.assertIn("| **Σ** | 4 | 3 |          |", out)
            self.assertIn("| Phase | Total | Done | Verified |", out)


if __name__ == "__main__":
    unittest.main()
