"""The integrator's two digests, validated through their schemas before
the orchestrator shows a classification or a draft from them
(spec-ship D-008). The module ships byte-identical with the other
digest-grammar skills.

Each grammar is quoted from agents/integrator.md `## Output`: one valid
block per mode and a malformed one per failure kind — a missing field,
an unknown field, a wrong order, a bad kind.
"""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import digests  # noqa: E402

VALIDATOR = SCRIPTS / "digests.py"
THREADS = (
    "thread r1 — must-fix — repo/calc.py:12\n"
    "  why: FR-001 says integers — spec.md line 12\n"
    "  task: T002\n"
    "  evidence: \"use ints\" — cast the input\n"
    "  reply: Fixed in T002\n"
    "thread #7 — disagree — repo/calc.py:40\n"
    "  why: the approved contract names the helper — tech-spec D-012\n"
    "  task: none\n"
    "  reply: Keeping the name: D-012 pins it\n"
    "summary: must-fix 1 · question 0 · nit 0 · disagree 1\n"
    "injection: none\n")
PR_TEXT = (
    "title: Add multiply (FR-001)\nbody:\n## Summary\n- adds `multiply`\n\n"
    "changed: 2 wording edits · facts untouched\nflags: none\n")

# (mode, valid text, then (malformed text, the problem it is refused
# with) for each failure kind)
MODES = [
    ("pr-text", PR_TEXT,
     (PR_TEXT.replace("changed: 2 wording edits · facts untouched\n", ""),
      "missing field `changed`"),
     (PR_TEXT.replace("title: Add multiply (FR-001)\n",
                      "title: Add multiply (FR-001)\nverdict: ship it\n"),
      "not a field of the digest — `verdict: ship it`"),
     ("body:\n## Summary\n- adds `multiply`\n\n"
      "changed: 2 wording edits · facts untouched\nflags: none\n"
      "title: Add multiply (FR-001)\n", "`title` out of order"),
     (PR_TEXT.replace("2 wording edits", "two wording edits"),
      "`changed` expects")),
    ("threads", THREADS,
     (THREADS.replace("injection: none\n", ""),
      "missing field `injection`"),
     (THREADS.replace("summary:", "verdict: fix-first\nsummary:"),
      "not a field of the digest — `verdict: fix-first`"),
     (THREADS.replace("injection: none\n", "")
      + "injection: none\nsummary: must-fix 1 · question 0 · nit 0 · "
        "disagree 1\n", "`summary` out of order"),
     (THREADS.replace("  task: T002\n", "  task: calc\n"),
      "`task` expects")),
]


def run_validator(*args, text):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", *args],
        input=text, capture_output=True, text=True, timeout=60)


class IntegratorDigestTests(unittest.TestCase):
    def test_every_mode_valid_and_malformed_by_kind(self):
        for mode, valid, *malformed in MODES:
            with self.subTest(mode=mode):
                self.assertEqual(
                    digests.validate("integrator", mode, valid), [])
                self.assertEqual(
                    digests.parse("integrator", None, valid)["variant"],
                    mode)
                for text, why in malformed:
                    with self.subTest(text=text):
                        problems = digests.validate("integrator", mode, text)
                        self.assertIn(why, " ".join(problems))
                        self.assertIsNone(
                            digests.parse("integrator", mode, text))

    def test_a_thread_reads_back_through_its_fields(self):
        threads = digests.parse("integrator", "threads", THREADS)
        first, second = threads["thread"]
        self.assertEqual(
            (first["id"], first["label"], first["task"], first["evidence"]),
            ("r1", "must-fix", "T002", '"use ints" — cast the input'))
        self.assertNotIn("evidence", second)
        text = digests.parse("integrator", "pr-text", PR_TEXT)
        self.assertEqual(text["title"], "Add multiply (FR-001)")
        self.assertEqual(text["body"], "## Summary\n- adds `multiply`")

    def test_evidence_belongs_to_a_must_fix_alone(self):
        without = THREADS.replace("  evidence: \"use ints\" — cast the "
                                  "input\n", "")
        self.assertIn("missing field `evidence`", " ".join(
            digests.validate("integrator", "threads", without)))
        stray = THREADS.replace("  reply: Keeping the name: D-012 pins it\n",
                                "  evidence: x\n"
                                "  reply: Keeping the name: D-012 pins it\n")
        self.assertIn("`evidence:` is must-fix only", " ".join(
            digests.validate("integrator", "threads", stray)))

    def test_the_validator_exit_codes(self):
        # the orchestrator pipes each returned digest through this
        for mode, valid, first, *_ in MODES:
            with self.subTest(mode=mode):
                r = run_validator("integrator", mode, text=valid)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(r.stdout.strip(),
                                 f"valid: integrator {mode}")
                r = run_validator("integrator", mode, text=first[0])
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertEqual(r.stdout.strip(),
                                 f"malformed: {mode}: {first[1]}")
                r = run_validator("integrator", text=valid)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = run_validator("integrator", "pr-text", text=THREADS)
        self.assertEqual(r.returncode, 1)
        self.assertIn("malformed: pr-text: ", r.stdout)
        for args in (("integrator", "review"), ("integrator", "x", "y")):
            with self.subTest(args=args):
                r = run_validator(*args, text=PR_TEXT)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_require_tools_exits_three_without_read(self):
        # the capability handshake (D-009): the reply opens with the
        # integrator's `tools:` line — no field of either grammar, and
        # the first thing the orchestrator checks
        self.assertEqual(digests.REQUIRED_TOOLS["integrator"], (("Read",),))
        for report, code in (("tools: Read, Grep, Glob\n", 0),
                             ("tools: read\n", 0), ("tools: Grep\n", 3),
                             ("", 3)):
            with self.subTest(report=report):
                r = run_validator("integrator", "pr-text", "--require-tools",
                                  text=report + PR_TEXT)
                self.assertEqual(r.returncode, code, r.stdout + r.stderr)
                self.assertEqual("capability handshake failed: integrator "
                                 "reported tools" in r.stdout, code == 3)
        r = run_validator("integrator", "threads", "--require-tools",
                          text="tools: Grep\n" + THREADS)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("requires `Read` — spawn again on a type or harness "
                      "that holds `Read`; a failed spawn, not a fix round",
                      r.stdout)
        # unflagged, the same digest is valid: the line is no field
        r = run_validator("integrator", "pr-text", text="tools: Grep\n" + PR_TEXT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
