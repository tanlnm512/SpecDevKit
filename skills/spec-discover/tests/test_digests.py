"""The panelist's digest, validated through its schema before Stage 5
reads a field from it (spec-discover D-011). The module ships
byte-identical with the other digest-grammar skills.

The grammar is quoted from contracts/run.md `## The digest grammar`:
one valid block per lens and a malformed one per failure kind — a
missing field, an unknown field, a wrong order, a bad kind.
"""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import digests  # noqa: E402

VALIDATOR = SCRIPTS / "digests.py"
PANEL = ("angle: The {lens}\npitch: one sentence — the idea through this "
         "lens\npoints:\n- first point [source](https://example.com/a, "
         "2026-11-01)\n- second point\nwatch: what must stay true\n{tail}")
KILL = "kill: signups stay at zero after the first-week check\n"
PROOF = "proof: a one-page signup → 10 signups\n"

# (lens, valid text, then (malformed text, the problem it is refused
# with) for each failure kind)
PANELS = [
    ("visionary", PANEL.format(lens="Visionary", tail=""),
     (PANEL.format(lens="Visionary", tail="").replace(
         "watch: what must stay true\n", ""), "missing field `watch`"),
     (PANEL.format(lens="Visionary", tail="").replace(
         "pitch: one sentence", "verdict: yes\npitch: one sentence"),
      "not a field of the digest — `verdict: yes`"),
     (PANEL.format(lens="Visionary", tail="").replace(
         "angle: The Visionary\npitch", "pitch").replace(
         "lens\npoints:", "lens\nangle: The Visionary\npoints:"),
      "`angle` out of order"),
     (PANEL.format(lens="Cynic", tail=""), "`angle` expects The Visionary")),
    ("cynic", PANEL.format(lens="Cynic", tail=KILL),
     (PANEL.format(lens="Cynic", tail=""), "missing field `kill`"),
     (PANEL.format(lens="Cynic", tail=PROOF),
      "not a field of the digest — `proof:"),
     (PANEL.format(lens="Cynic", tail=KILL).replace(
         "watch: what must stay true\n" + KILL, KILL + "watch: x\n"),
      "`watch` out of order"),
     (PANEL.format(lens="Cynic", tail=KILL).replace(
         "- first point [source](https://example.com/a, 2026-11-01)\n"
         "- second point\n", "- only one point\n"),
      "carries 1 line(s) — 2–3 expected")),
    ("minimalist", PANEL.format(lens="Minimalist", tail=PROOF),
     (PANEL.format(lens="Minimalist", tail=""), "missing field `proof`"),
     (PANEL.format(lens="Minimalist", tail=KILL),
      "not a field of the digest — `kill:"),
     (PANEL.format(lens="Minimalist", tail=PROOF).replace(
         "watch: what must stay true\n" + PROOF, PROOF + "watch: x\n"),
      "`watch` out of order"),
     (PANEL.format(lens="Visionary", tail=PROOF),
      "`angle` expects The Minimalist")),
]


def run_validator(*args, text):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", *args],
        input=text, capture_output=True, text=True, timeout=60)


class PanelDigestTests(unittest.TestCase):
    def test_every_lens_valid_and_malformed_by_kind(self):
        for lens, valid, *malformed in PANELS:
            with self.subTest(lens=lens):
                self.assertEqual(digests.validate("panelist", lens, valid),
                                 [])
                self.assertEqual(
                    digests.parse("panelist", None, valid)["variant"], lens)
                for text, why in malformed:
                    with self.subTest(text=text):
                        problems = digests.validate("panelist", lens, text)
                        self.assertIn(why, " ".join(problems))
                        self.assertIsNone(
                            digests.parse("panelist", lens, text))

    def test_a_dealbreaker_line_reads_back_through_its_field(self):
        cynic = digests.parse("panelist", "cynic",
                              PANELS[1][1].replace(
                                  "- second point\n",
                                  "- second point: no buyer [source](x)\n"))
        self.assertEqual(cynic["points"][1],
                         "second point: no buyer [source](x)")
        self.assertEqual(cynic["kill"],
                         KILL[len("kill: "):].strip())

    def test_the_validator_exit_codes(self):
        # the orchestrator pipes each returned digest through this
        for lens, valid, first, *_ in PANELS:
            with self.subTest(lens=lens):
                r = run_validator("panelist", lens, text=valid)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(r.stdout.strip(), f"valid: panelist {lens}")
                r = run_validator("panelist", lens, text=first[0])
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertEqual(r.stdout.strip(),
                                 f"malformed: {lens}: {first[1]}")
        # without a lens each of the three is accepted
        for lens, valid, *_ in PANELS:
            with self.subTest(lens=lens):
                r = run_validator("panelist", text=valid)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(r.stdout.strip(), f"valid: panelist {lens}")
        r = run_validator("panelist", "visionary",
                          text=PANEL.format(lens="Cynic", tail=KILL))
        self.assertEqual(r.returncode, 1)
        self.assertIn("not a field of the digest — `kill:", r.stdout)
        for args in (("panelist", "sceptic"), ("panelist", "x", "y")):
            with self.subTest(args=args):
                r = run_validator(*args, text=PANELS[0][1])
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_require_tools_exits_three_on_a_digest_without_read(self):
        # the capability handshake (spec-discover D-012): the reply opens
        # with `tools: <what it holds>` — a line no grammar counts as a
        # field, and one the orchestrator checks before it reads a field
        lens, valid, *_ = PANELS[0]
        self.assertEqual(digests.REQUIRED_TOOLS["panelist"], (("Read",),))
        for report, code in (("tools: Read, Grep, Glob\n", 0),
                             ("tools: read\n", 0),
                             ("tools: Grep, Glob\n", 3),
                             ("", 3)):
            with self.subTest(report=report):
                r = run_validator("panelist", lens, "--require-tools",
                                  text=report + valid)
                self.assertEqual(r.returncode, code, r.stdout + r.stderr)
                self.assertEqual(
                    "capability handshake failed: panelist reported tools"
                    in r.stdout, code == 3)
        r = run_validator("panelist", lens, "--require-tools",
                          text="tools: Grep\n" + valid)
        self.assertEqual(r.stdout.strip(), "capability handshake failed: "
                         "panelist reported tools `Grep` — the panelist role "
                         "requires `Read` — spawn again on a type or harness "
                         "that holds `Read`; a failed spawn, not a fix round")
        # unflagged, the same digest is valid: the line is no field
        r = run_validator("panelist", lens, text="tools: Grep\n" + valid)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
