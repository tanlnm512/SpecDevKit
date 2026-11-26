"""The analyst's digest schemas as this skill's span spawns them — the
intent lens here, research and constitution beside it (spec-define
D-024). The module is the master's byte-identical replica.

Each grammar is quoted from its definition with one valid literal and a
malformed literal per failure kind: a missing key, an unknown key, a
wrong order, a bad kind. A malformed digest is never parsed by half.
"""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import digests  # noqa: E402

VALIDATOR = SCRIPTS / "digests.py"
INTENT = ("digest: intent grounded 12 facts · markers 2 open · session "
          "FAILs 0 · unknowns 1")

# (variant, valid literal, then (malformed literal, the problem it is
# refused with) for each failure kind)
GRAMMARS = [
    ("intent", INTENT,
     ("digest: intent grounded 12 facts · session FAILs 0 · unknowns 1",
      "`markers` missing"),
     ("digest: extra x · " + INTENT[len("digest: "):],
      "unknown segment `extra x`"),
     ("digest: markers 2 open · intent grounded 12 facts · session FAILs "
      "0 · unknowns 1", "unknown segment `markers 2 open` before `intent "
      "grounded`"),
     ("digest: intent grounded twelve facts · markers 2 open · session "
      "FAILs 0 · unknowns 1", "`intent grounded` expects")),
    ("research",
     "digest: questions 3 answered / 1 open · options Q1: sqlite → "
     "postgres, needs a migration",
     ("digest: questions 3 answered / 1 open", "`options` missing"),
     ("digest: extra x · questions 3 answered / 1 open · options Q1: a",
      "unknown segment `extra x`"),
     ("digest: options Q1: a · questions 3 answered / 1 open",
      "unknown segment `options Q1: a` before `questions`"),
     ("digest: questions 3 / 1 · options Q1: a", "`questions` expects")),
    ("constitution",
     "digest: constitution 2 proposed · areas auth, storage · "
     "contradicted D-014 · unknowns 0",
     ("digest: constitution 2 proposed · areas auth, storage · "
      "unknowns 0", "`contradicted` missing"),
     ("digest: extra x · constitution 2 proposed · areas a · "
      "contradicted none · unknowns 0", "unknown segment `extra x`"),
     ("digest: areas a · constitution 2 proposed · contradicted none · "
      "unknowns 0", "unknown segment `areas a` before `constitution`"),
     ("digest: constitution two proposed · areas a · contradicted none · "
      "unknowns 0", "`constitution` expects")),
]


def run_validator(*args, text):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", *args],
        input=text, capture_output=True, text=True, timeout=60)


class AnalystDigestTests(unittest.TestCase):
    def test_every_lens_valid_and_malformed_by_kind(self):
        for variant, valid, *malformed in GRAMMARS:
            with self.subTest(variant=variant):
                self.assertEqual(
                    digests.validate("analyst", variant, valid), [])
                self.assertEqual(
                    digests.parse("analyst", None, valid)["variant"],
                    variant)
                for literal, why in malformed:
                    with self.subTest(literal=literal):
                        self.assertIn(why, " ".join(
                            digests.validate("analyst", variant, literal)))
                        self.assertIsNone(
                            digests.parse("analyst", variant, literal))

    def test_the_validator_exit_codes(self):
        for variant, valid, first, *_ in GRAMMARS:
            with self.subTest(variant=variant):
                r = run_validator("analyst", variant, text=valid)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(r.stdout.strip(), f"valid: analyst {variant}")
                r = run_validator("analyst", variant, text=first[0])
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn(f"malformed: {variant}: {first[1]}", r.stdout)
        r = run_validator("analyst", text=INTENT)
        self.assertEqual((r.returncode, r.stdout.strip()),
                         (0, "valid: analyst intent"))
        r = run_validator("analyst", "intent", text="no digest here")
        self.assertEqual(r.returncode, 1)
        self.assertIn("malformed: no `digest:` line", r.stdout)
        # one argument that is not a lens names the file, so a typo in
        # the lens is refused as an unreadable file, never as a digest
        r = run_validator("analyst", "shape", text=INTENT)
        self.assertEqual(r.returncode, 2)
        self.assertIn("cannot read shape", r.stderr)
        r = run_validator("analyst", "shape", "x", text=INTENT)
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown analyst variant `shape`", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
