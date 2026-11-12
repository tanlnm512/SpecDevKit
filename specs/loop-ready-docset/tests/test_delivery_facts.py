"""TC-012 — delivery facts read from the status holder's delivery block (FR-008).

Run: python3 specs/loop-ready-docset/tests/test_delivery_facts.py
DeliveryFactsTests.<method>
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
for _skill in ("spec-build", "spec-release"):
    _scripts = str(_ROOT / "skills" / _skill / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)

import audit  # noqa: E402 - repo-relative scripts dirs prepended above
import release  # noqa: E402


class DeliveryFactsTests(unittest.TestCase):
    BLOCK = ("- Docs impact: README.md\n"
             "- Rollback: NFR-001 — revert the module commit\n"
             "- Behavior preserved: TC-001 green at approval and now\n")

    def delivered_spec(self, task_md: str) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="delivery-facts-"))
        self.addCleanup(shutil.rmtree, root, True)
        spec = root / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "spec.md").write_text(
            "# Spec: demo\n\n**Type**: refactor\n**Status**: done\n", encoding="utf-8")
        (spec / "tech-spec.md").write_text(
            "## Quality, threats, and rollback\n"
            "| Requirement | Design consequence | Rollback or verification |\n"
            "|---|---|---|\n"
            "| NFR-001 | keep the old path shippable | revert the module commit |\n",
            encoding="utf-8")
        (spec / "task.md").write_text(task_md, encoding="utf-8")
        return root, spec

    def test_facts_read_from_status_holder_by_audit_and_release(self):
        task_md = ("# Tasks: demo\n\n"
                   "**Delivered**: commit @ abc1234def\n"
                   + self.BLOCK + "\n"
                   "## Burndown\n"
                   "| Phase | Total | Done | Verified |\n"
                   "|-------|-------|------|----------|\n"
                   "| 1     | 2     | 2    | pass     |\n"
                   "| 2     | 1     | 1    |          |\n"
                   "| **Σ** | 3     | 3    |          |\n")
        root, spec = self.delivered_spec(task_md)
        gates = {name: st for name, st, _ in
                 audit.delivery_gates(spec, root, ["README.md"], True)}
        self.assertEqual(gates,
                         {"DOCS IMPACT": "PASS", "ROLLBACK": "PASS", "WORK TYPE": "PASS"})
        facts = release.spec_facts(root, spec, [])
        self.assertEqual(facts["delivery_note"], {
            "docs_impact": "README.md",
            "rollback": ["NFR-001 — revert the module commit"],
            "behavior_preserved": ["TC-001 green at approval and now"]})
        self.assertEqual(facts["verified"], {"1": "pass", "2": ""})

        root, spec = self.delivered_spec(
            task_md.replace("- Behavior preserved: TC-001 green at approval and now\n", ""))
        gates = {name: (st, dt) for name, st, dt in
                 audit.delivery_gates(spec, root, ["README.md"], True)}
        self.assertEqual(gates["DOCS IMPACT"][0], "PASS")
        self.assertEqual(gates["ROLLBACK"][0], "PASS")
        self.assertEqual(gates["WORK TYPE"][0], "FAIL")
        self.assertIn("Behavior preserved", gates["WORK TYPE"][1])
        self.assertIn("task.md delivery block", gates["WORK TYPE"][1])
        self.assertEqual(release.delivery_note(spec)["behavior_preserved"], [])

    def test_note_fallback_serves_specs_without_the_block(self):
        root, spec = self.delivered_spec(
            "# Tasks: demo\n\n**Delivered**: commit @ abc1234def\n")
        (spec / "notes").mkdir()
        (spec / "notes" / "delivery.md").write_text(
            "Docs impact: README.md\n"
            "Rollback: NFR-001 — revert the module commit\n"
            "Behavior preserved: TC-001 green at approval and now\n", encoding="utf-8")
        gates = {name: st for name, st, _ in
                 audit.delivery_gates(spec, root, ["README.md"], True)}
        self.assertEqual(gates,
                         {"DOCS IMPACT": "PASS", "ROLLBACK": "PASS", "WORK TYPE": "PASS"})
        note = release.delivery_note(spec)
        self.assertEqual(note["docs_impact"], "README.md")
        self.assertEqual(note["rollback"], ["NFR-001 — revert the module commit"])
        self.assertEqual(release.spec_facts(root, spec, [])["verified"], {})


if __name__ == "__main__":
    unittest.main()
