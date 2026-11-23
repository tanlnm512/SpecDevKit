"""migrate.py upgrade folds a retired survey.md into tech-spec.md's
`## Code state`: dry by default, check.py green after --apply, and a
second apply changes nothing."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
EXAMPLE = SKILL / "examples" / "mini-spec"

LEGACY_SURVEY = """# Survey: mini-calc

**Created**: 2026-09-08 | **Baseline**: mini-calc v1 @ 3fa9c21

## Items

```
item S1: "arithmetic module exposes add and subtract — both green"
  evidence:   repo/calc.py:add:3
  status:     DONE
  verify:     python3 -m pytest test_calc.py -k "add or sub"
```
"""


def run_script(name: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "KIT_TELEMETRY": "off"})


class SurveyFoldTests(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp(prefix="migrate-survey-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        shutil.copytree(EXAMPLE / "repo", root / "repo")
        self.spec = root / "specs" / "mini-spec"
        shutil.copytree(EXAMPLE / "specs" / "mini-spec", self.spec)
        tech = self.spec / "tech-spec.md"
        text = tech.read_text(encoding="utf-8")
        text = re.sub(r"\*\*Baseline\*\*:[^\n]*\n", "", text)
        text = re.sub(r"## Code state\n.*?(?=## Architecture)", "", text,
                      flags=re.S)
        tech.write_text(text, encoding="utf-8")
        (self.spec / "survey.md").write_text(LEGACY_SURVEY, encoding="utf-8")

    def test_upgrade_folds_survey_into_code_state(self):
        before = run_script("check.py", self.spec, "--code-state-only")
        self.assertEqual(before.returncode, 1, before.stdout)
        self.assertIn("migrate.py <spec-dir> upgrade --apply", before.stdout)

        dry = run_script("migrate.py", self.spec, "upgrade")
        self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
        self.assertIn("survey: fold survey.md", dry.stdout)
        self.assertTrue((self.spec / "survey.md").exists())

        applied = run_script("migrate.py", self.spec, "upgrade", "--apply")
        self.assertEqual(applied.returncode, 0,
                         applied.stdout + applied.stderr)
        self.assertFalse((self.spec / "survey.md").exists())
        tech = (self.spec / "tech-spec.md").read_text(encoding="utf-8")
        self.assertIn("## Code state", tech)
        self.assertIn("**Baseline**: mini-calc v1 @ 3fa9c21", tech)
        self.assertIn("### Items", tech)
        after = run_script("check.py", self.spec, "--code-state-only")
        self.assertEqual(after.returncode, 0, after.stdout)

        again = run_script("migrate.py", self.spec, "upgrade", "--apply")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn("already upgraded", again.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
