"""The digest schemas for the roles this skill spawns — the developer
and the auditor (spec-build D-054) — and the two consumers that read a
developer digest file: the resume column and the retro roll-up.

Each grammar is quoted from its definition with one valid literal and a
malformed literal per failure kind: a missing key, an unknown key, a
wrong order, a bad kind. A malformed digest is never parsed by half.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import digests  # noqa: E402
import retro  # noqa: E402
import specstate  # noqa: E402
from test_execute_gates import hand_docset, write  # noqa: E402

VALIDATOR = SCRIPTS / "digests.py"
DEVELOPER = ("digest: task T001 · status implemented · files 2 · "
             "commit-line feat(x): T001 shout (FR-001) · deviation none · "
             "note none")
AUDITOR = "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none"

# (role, valid literal, then (malformed literal, the problem it is
# refused with) for each failure kind)
GRAMMARS = [
    ("developer", DEVELOPER,
     ("digest: task T001 · status implemented · files 2 · deviation "
      "none · note none", "`commit-line` missing"),
     ("digest: owner me · " + DEVELOPER[len("digest: "):],
      "unknown segment `owner me`"),
     ("digest: status implemented · task T001 · files 2 · commit-line x "
      "· deviation none · note none", "unknown segment `status "
      "implemented` before `task`"),
     ("digest: task T001 · status done · files 2 · commit-line x · "
      "deviation none · note none", "`status` expects")),
    ("auditor", AUDITOR,
     ("digest: BLOCK 0 · WARN 0 · worst none", "`NIT` missing"),
     ("digest: extra 1 · " + AUDITOR[len("digest: "):],
      "unknown segment `extra 1`"),
     ("digest: NIT 0 · BLOCK 0 · WARN 0 · worst none",
      "unknown segment `NIT 0` before `BLOCK`"),
     ("digest: BLOCK two · WARN 0 · NIT 0 · worst none",
      "`BLOCK` expects a count")),
]


def run_validator(role, text):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", role],
        input=text, capture_output=True, text=True, timeout=60)


class SchemaTests(unittest.TestCase):
    def test_developer_and_auditor_valid_and_malformed_by_kind(self):
        for role, valid, *malformed in GRAMMARS:
            with self.subTest(role=role):
                self.assertEqual(digests.validate(role, None, valid), [])
                self.assertEqual(run_validator(role, valid).returncode, 0)
                for literal, why in malformed:
                    with self.subTest(literal=literal):
                        self.assertIn(why, " ".join(
                            digests.validate(role, None, literal)))
                        self.assertIsNone(
                            digests.parse(role, None, literal))
                        r = run_validator(role, literal)
                        self.assertEqual(r.returncode, 1, r.stdout)
                        self.assertIn("malformed: " + why, r.stdout)

    def test_a_digest_file_is_valid_malformed_or_absent(self):
        with tempfile.TemporaryDirectory() as td:
            spec = Path(td)
            self.assertEqual(specstate.latest_digest(spec, "T001"), None)
            folder = spec / "digests" / "wave-4"
            folder.mkdir(parents=True)
            path = folder / "implementer-T001.md"
            self.assertEqual(specstate.latest_digest(spec, "T001"), None)
            write(path, DEVELOPER + "\n")
            self.assertEqual(specstate.latest_digest(spec, "T001")["state"],
                             "valid")
            write(path, "digest: task T001 · status implemented · files 2")
            found = specstate.latest_digest(spec, "T001")
            self.assertEqual((found["state"], found["path"], found["wave"]),
                             ("malformed", str(path), 4))
            self.assertEqual(found["problems"], ["`commit-line` missing"])
            self.assertEqual(
                specstate.digests_on_file(spec), {"T001": found})


class ReaderTests(unittest.TestCase):
    """The two readers of a developer digest file: the resume column and
    the retro roll-up — each shows a malformed file as that, never as
    absent."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="digests-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.env = dict(os.environ,
                        KIT_TELEMETRY_DIR=str(self._tmp / "tel"),
                        KIT_TELEMETRY="on")

    def test_the_resume_column_reads_a_malformed_file_as_that(self):
        spec = hand_docset(self._tmp / "specs" / "a", "approved")
        wave = spec / "spawns" / "wave-4"
        wave.mkdir(parents=True)
        write(wave / "implementer-T001.md", "payload\n")
        claimed = subprocess.run(
            [sys.executable, str(SCRIPTS / "mark.py"), "claim", str(spec),
             "--wave", str(wave)], capture_output=True, text=True,
            timeout=120, env=self.env)
        self.assertEqual(claimed.returncode, 0, claimed.stdout + claimed.stderr)
        path = spec / "digests" / "wave-4" / "implementer-T001.md"
        path.parent.mkdir(parents=True)

        def column():
            r = subprocess.run(
                [sys.executable, str(SCRIPTS / "graph.py"), str(spec),
                 "--explain", "execute"], capture_output=True, text=True,
                timeout=120, env=self.env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return [ln for ln in r.stdout.splitlines() if "T001" in ln]

        self.assertIn("[digest on file: none]", "\n".join(column()))
        write(path, "digest: task T001 · status implemented · files 2\n")
        self.assertIn("[digest on file: malformed — fix and run again]",
                      "\n".join(column()))
        write(path, DEVELOPER + "\n")
        self.assertIn("[digest on file: implemented]", "\n".join(column()))
        write(path, "digest: task T001 · status blocked: no evidence · files "
              "0 · commit-line none · deviation scope: repo/eval.py · "
              "note none\n")
        shown = "\n".join(column())
        self.assertIn("[digest on file: blocked: no evidence]", shown)
        self.assertIn("[deviation scope: repo/eval.py]", shown)

    def test_the_retro_counts_a_malformed_file_instead_of_skipping_it(self):
        spec = self._tmp / "spec"
        older, newer = spec / "digests" / "wave-4", spec / "digests" / "wave-6"
        older.mkdir(parents=True)
        newer.mkdir()
        write(older / "implementer-T001.md", DEVELOPER + "\n")
        write(older / "implementer-T002.md",
              "digest: task T002 · status blocked: env · files 0 · "
              "commit-line none · deviation spec-defect: FR-003 · note none\n")
        write(newer / "implementer-T003.md", "digest: task T003 · status done")
        rows, malformed = retro.digest_rows(spec)
        self.assertEqual(rows, [
            "- T001 wave 4 — implemented",
            "- T002 wave 4 — blocked: env · deviation spec-defect: FR-003",
            "- T003 wave 6 — malformed"])
        self.assertEqual(malformed, 1)
        self.assertEqual(retro.digest_rows(self._tmp / "absent"), ([], 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
