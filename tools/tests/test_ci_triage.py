"""The CI triage classifier is one function shipped twice: spec-ship and
spec-review package separately, so ship.py and review_orchestrator.py
each carry their own copy — duplicated on purpose, pinned identical
here (the model is test_parity's byte-twin pins)."""
import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TWIN_NAMES = ("RUNNER_STEPS", "is_runner_step", "first_failed_step",
              "classify_check")
TWIN_FILES = ("skills/spec-ship/scripts/ship.py",
              "skills/spec-review/scripts/review_orchestrator.py")


def segments(path: Path) -> dict[str, str]:
    src = path.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in TWIN_NAMES:
            found[node.targets[0].id] = ast.get_source_segment(src, node)
        elif isinstance(node, ast.FunctionDef) and node.name in TWIN_NAMES:
            found[node.name] = ast.get_source_segment(src, node)
    return found


class TwinIdentityTests(unittest.TestCase):
    def test_both_scripts_carry_every_twin_name(self):
        for path in TWIN_FILES:
            with self.subTest(script=path):
                found = segments(REPO_ROOT / path)
                self.assertEqual(set(found), set(TWIN_NAMES),
                                 f"{path} is missing {set(TWIN_NAMES) - set(found)}")

    def test_the_two_copies_are_byte_identical(self):
        ship, oracle = (segments(REPO_ROOT / p) for p in TWIN_FILES)
        for name in TWIN_NAMES:
            with self.subTest(name=name):
                self.assertEqual(ship[name], oracle[name],
                                 f"{name} diverged between the two skills")

    def test_the_runner_step_list_stays_narrow(self):
        src = segments(REPO_ROOT / TWIN_FILES[0])["RUNNER_STEPS"]
        self.assertIn('"Set up job"', src)
        self.assertIn('"Complete job"', src)
        self.assertIn('"actions/checkout@"', src)
        self.assertIn('"Post "', src)
        # a project setup step must never join the runner list
        self.assertNotIn("Set up Node", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
