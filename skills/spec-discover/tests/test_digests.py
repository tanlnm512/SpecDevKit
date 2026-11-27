"""The panelist's digest, validated through its schema before Stage 5
reads a field from it (spec-discover D-011). The module ships
byte-identical with the other digest-grammar skills.

The grammar is quoted from contracts/run.md `## The digest grammar`:
one valid block per lens and a malformed one per failure kind — a
missing field, an unknown field, a wrong order, a bad kind.
"""
import re
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


def block_refusals(digest: str) -> list[str]:
    """The same block digest with its last field dropped and its last
    field renamed to one no grammar holds — each must be malformed."""
    lines = digest.split("\n")
    last = re.match(r"\w+:", lines[-1]).group(0)
    return ["\n".join(lines[:-1]),
            "\n".join([*lines[:-1], "extra:" + lines[-1][len(last):]])]


SKILL_DIR = Path(__file__).resolve().parents[1]


class BriefGrammarTests(unittest.TestCase):
    """The schema is the lens's grammar: each lens's digest is built from
    the fields its `protocol/lenses.md` section names, in its order and
    within the line count it states, and checked against the field table
    `contracts/run.md` pins — so neither document can drift from
    `digests.py` silently."""

    SAMPLE = "what the evidence shows"

    def test_each_lens_output_is_the_schema(self):
        lenses = (SKILL_DIR / "protocol" / "lenses.md").read_text(
            encoding="utf-8")
        run = (SKILL_DIR / "contracts" / "run.md").read_text(encoding="utf-8")
        # the pinned table: (field, what the table says of it)
        pinned = re.findall(r"^ {4}([a-z]+):\s+(.*)$",
                            run.split("## The digest grammar", 1)[1], re.M)
        shared = [name for name, said in pinned if " only" not in said]
        own = {re.match(r"(\w+) only", said).group(1).lower(): name
               for name, said in pinned if " only" in said}
        for lens in ("visionary", "cynic", "minimalist"):
            with self.subTest(lens=lens):
                section = re.search(rf"(?ms)^## Lens: {lens}\n(.*?)(?=^## Lens: |\Z)",
                                    lenses).group(1)
                output = re.search(r"(?s)### Output\n(.*\n)(?=\s*\Z)",
                                   section).group(1).split("except `points:`:\n")[1]
                # (field, the angle it names, when it is `angle`)
                fields = re.findall(r"`([a-z]+):(?: (The \w+))?`", output)
                self.assertEqual([name for name, _angle in fields],
                                 shared + ([own[lens]] if lens in own else []))
                low, high = (int(n) for n in re.search(
                    r"`points:` \((\d+)[–-](\d+) lines", output).groups())

                def digest(points: int) -> str:
                    return "".join(
                        f"points:\n" + "- first point\n" * points
                        if name == "points" else
                        f"{name}: {angle or self.SAMPLE}\n"
                        for name, angle in fields).rstrip("\n")

                self.assertEqual(digests.validate("panelist", lens, digest(low)),
                                 [])
                self.assertEqual(
                    digests.parse("panelist", None, digest(high))["variant"],
                    lens)
                for broken in block_refusals(digest(low)):
                    self.assertTrue(
                        digests.validate("panelist", lens, broken), broken)
                for count, why in (
                        (low - 1, f"`points` carries {low - 1} line(s) — "
                                  f"{low}–{high} expected"),
                        (high + 1, f"`points` carries {high + 1} line(s) — "
                                   f"{low}–{high} expected")):
                    with self.subTest(points=count):
                        self.assertIn(why, " ".join(
                            digests.validate("panelist", lens, digest(count))))
                # one line per field but `points:`
                two = digest(low).replace(
                    f"watch: {self.SAMPLE}", f"watch: {self.SAMPLE}\nmore")
                self.assertIn("not a field of the digest", " ".join(
                    digests.validate("panelist", lens, two)))

    def test_a_forged_or_misplaced_report_is_refused(self):
        # the report is the reply's first line alone — one that stands
        # anywhere else is ordinary text, so no report: a failed spawn —
        # and a name holding the provenance separator refuses the whole
        # digest: never a handshake failure, and no field is read from it
        lens, valid, *_ = PANELS[0]
        flagged = ("--require-tools",)
        r = run_validator("panelist", lens, *flagged, text=(
            "tools: Read, Grep · payload deadbeef\n" + valid))
        self.assertEqual((r.returncode, "capability handshake" in r.stdout),
                         (1, False))
        self.assertIn("malformed: tools report refused: "
                      "`Grep · payload deadbeef`", r.stdout)
        r = run_validator("panelist", lens, *flagged, text=valid.replace(
            "pitch:", "tools: Read\npitch:", 1))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
