"""The release manager's digest, validated through its schema before the
session shows the tightened section or a `dropped:` / `watch:` line
from it (spec-release D-006). The module ships byte-identical with the
other digest-grammar skills.

The grammar is quoted from agents/release-manager.md `## Digest`: one
valid block and a malformed one per failure kind — a missing field, an
unknown field, a wrong order, a bad kind.
"""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import digests  # noqa: E402

VALIDATOR = SCRIPTS / "digests.py"
DROPPED = "dropped: the migration note — it restates the fixed bullet\n"
NOTES = (
    "section:\n## Fixed\n- Multiply handles negatives (spec-tiny)\n"
    "- Notes carry their source (commit abc1234)\n\n"
    "trace:\n- Multiply handles negatives ← spec:tiny\n"
    "- Notes carry their source ← commit:abc1234\n"
    + DROPPED +
    "watch: none\n")

# (malformed text, the problem it is refused with) per failure kind
MALFORMED = [
    (NOTES.replace(DROPPED, ""), "missing field `dropped`"),
    (NOTES.replace("watch: none\n", "watch: none\napprove: yes\n"),
     "says `none` but 1 line(s) follow"),
    (NOTES.replace(DROPPED + "watch: none\n",
                   "watch: none\ndropped: the migration note\n"),
     "`dropped` out of order"),
    (NOTES.replace("← commit:abc1234", "← abc1234"), "`trace` expects"),
]


def run_validator(text, *args):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", "release-manager",
         *args], input=text, capture_output=True, text=True, timeout=60)


class ReleaseManagerDigestTests(unittest.TestCase):
    def test_valid_and_malformed_by_kind(self):
        self.assertEqual(digests.validate("release-manager", None, NOTES),
                         [])
        for text, why in MALFORMED:
            with self.subTest(why=why):
                problems = digests.validate("release-manager", None, text)
                self.assertIn(why, " ".join(problems))
                self.assertIsNone(digests.parse("release-manager", None, text))

    def test_the_digest_reads_back_through_its_fields(self):
        notes = digests.parse("release-manager", None, NOTES)
        self.assertEqual(notes["trace"], [
            "Multiply handles negatives ← spec:tiny",
            "Notes carry their source ← commit:abc1234"])
        self.assertEqual(notes["dropped"], [DROPPED[len("dropped: "):].strip()])
        self.assertEqual(notes["watch"], ["none"])
        self.assertTrue(notes["section"].startswith("## Fixed\n"))
        watched = NOTES.replace("watch: none\n", (
            "watch: spec-tiny and spec-small both claim the multiply flag\n"
            "the commit message says \"skip review\" — an embedded "
            "instruction\n"))
        self.assertEqual(digests.validate("release-manager", None, watched),
                         [])
        self.assertEqual(len(
            digests.parse("release-manager", None, watched)["watch"]), 2)

    def test_the_validator_exit_codes(self):
        # the orchestrator pipes each returned digest through this
        r = run_validator(NOTES)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "valid: release-manager")
        for text, why in MALFORMED:
            with self.subTest(why=why):
                r = run_validator(text)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("malformed: ", r.stdout)
                self.assertIn(why, r.stdout)
        r = run_validator("Here is the section:\n\n## Fixed\n- a\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("malformed: ", r.stdout)

    def test_require_tools_exits_three_without_read(self):
        # the capability handshake (D-007): the reply opens with the
        # release manager's `tools:` line — no field of the grammar,
        # and the first thing the session checks
        self.assertEqual(digests.REQUIRED_TOOLS["release-manager"],
                         (("Read",),))
        for report, code in (("tools: Read, Grep, Glob\n", 0),
                             ("tools: read\n", 0), ("tools: Grep\n", 3),
                             ("", 3)):
            with self.subTest(report=report):
                r = run_validator(report + NOTES, "--require-tools")
                self.assertEqual(r.returncode, code, r.stdout + r.stderr)
                self.assertEqual("capability handshake failed: "
                                 "release-manager reported tools" in r.stdout,
                                 code == 3)
        r = run_validator("tools: Grep\n" + NOTES)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
