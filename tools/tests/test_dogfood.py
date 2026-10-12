#!/usr/bin/env python3
"""Kit dogfood gate: every skill's checker must pass over every
in-repo artifact of its own type.

The grader (tools/grade.py) scores this; this suite GATES it — a kit
artifact drifting past its own checker fails CI instead of waiting for
the next grading session (rubrics/kit-grading-rubric.md principle 3).
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS = ROOT / "skills"


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


class BrainstormDogfoodTests(unittest.TestCase):
    def test_every_brainstorm_artifact_passes_the_handoff_checker(self):
        artifacts = [SKILLS / "spec-brainstorming" / "examples"
                     / "decision-tracker" / "decision-tracker.md"]
        artifacts += sorted(ROOT.glob("brainstorms/*.md"))
        self.assertTrue(artifacts, "no brainstorm artifacts found to gate")
        checker = SKILLS / "spec-brainstorming" / "scripts" / "check.py"
        for art in artifacts:
            with self.subTest(artifact=art.name):
                r = run([sys.executable, str(checker), str(art)])
                self.assertEqual(
                    r.returncode, 0,
                    f"{art} fails spec-brainstorming's own handoff checker:\n"
                    f"{r.stdout}\n{r.stderr}",
                )


class SpecDogfoodTests(unittest.TestCase):
    def test_every_live_specset_passes_check_py(self):
        # the docset checker's master home is spec-shape (the split's
        # parity master, D-004); the fixture ships beside it
        checker = SKILLS / "spec-shape" / "scripts" / "check.py"
        dirs = [SKILLS / "spec-shape" / "examples" / "mini-spec" / "specs" / "mini-spec"]
        dirs += [
            p.parent
            for p in sorted((ROOT / "specs").glob("*/spec.md"))
            if p.parent.name not in ("context", "archive")
        ]
        self.assertTrue(dirs, "no spec docsets found to gate")
        for d in dirs:
            with self.subTest(spec=d.name):
                r = run([sys.executable, str(checker), str(d)])
                self.assertEqual(
                    r.returncode, 0,
                    f"{d} fails spec-shape's own docset checker:\n"
                    f"{r.stdout}\n{r.stderr}",
                )


if __name__ == "__main__":
    unittest.main()
