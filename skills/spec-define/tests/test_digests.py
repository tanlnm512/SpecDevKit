"""The analyst's digest schemas as this skill's span spawns them — the
intent lens here, research and constitution beside it (spec-define
D-024). The module is the master's byte-identical replica.

Each grammar is quoted from its definition with one valid literal and a
malformed literal per failure kind: a missing key, an unknown key, a
wrong order, a bad kind. A malformed digest is never parsed by half.
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


def _key(alternative: str) -> str:
    return alternative.strip().split("<")[0].strip().rstrip(":")


def documented(text: str, pattern: str) -> str:
    """The grammar a document states, as it states it: the span
    `pattern` captures, its wrapped lines joined."""
    found = re.search(pattern, text, re.S)
    return re.sub(r"\s+", " ", found.group(1)).strip()


def alternations(template: str) -> list[str]:
    """The body of every alternation in `template`, in document order."""
    found, opens = [], []
    for bracket in re.finditer(r"[<>]", template):
        if bracket.group() == "<":
            opens.append(bracket.start())
        elif "|" in (body := template[opens.pop() + 1:bracket.start()]):
            found.append(body)
    return found


def fill(template: str, samples: dict, prefer: str | None = None,
         counts: dict | None = None) -> str:
    """`template` with every `<…>` filled: an alternation by the
    alternative `prefer` names or its first, another metavariable by its
    sample. `<n>` is what its line lists — `counts` says for the word
    before it, else it counts the alternatives this fill chose, as a
    digest's summary counts its items. A line whose metavariable reads
    `<x> only:` stays only when `x` was chosen."""

    def picked(body: str) -> str:
        return next((alt.strip() for alt in body.split("|")
                     if _key(alt) == prefer), body.split("|")[0].strip())

    chosen = {_key(picked(body)) for body in alternations(template)}
    out = []
    for line in template.split("\n"):
        only = re.search(r"<(\S+) only:", line)
        if only and only.group(1) not in chosen:
            continue
        while "<" in line:
            found = re.search(r"<([^<>]+)>", line)
            body = found.group(1)
            if "|" in body:
                value = picked(body)
            else:
                word = re.split(r"[\s·]+", line[:found.start()].strip())[-1]
                value = (samples[body] if body != "n" else
                         (counts or {}).get(word)
                         or ("1" if word in chosen else "0"))
            line = line[:found.start()] + value + line[found.end():]
        out.append(line)
    return "\n".join(out)


def refusals(digest: str) -> list[str]:
    """The same line digest with its last segment dropped, an extra
    segment added, and its first two swapped — each must be malformed;
    the lines after the `digest:` line stay."""
    line, _, rest = digest.partition("\n")
    parts = line.split(" · ")
    return [(broken + "\n" + rest).rstrip()
            for broken in (" · ".join(parts[:-1]), line + " · extra x",
                           " · ".join([parts[1], parts[0], *parts[2:]]))]


def assert_is_schema(test, role, variant, template, samples,
                     counts=None):
    """The documented `template` validates under its role's schema, with
    each of its alternations turned to each of its alternatives, and
    each of its refusals is malformed."""
    fills = [fill(template, samples, counts=counts)]
    fills += [fill(template, samples, prefer=alt, counts=counts)
              for body in alternations(template)
              for alt in [_key(a) for a in body.split("|")][1:]]
    for digest in fills:
        test.assertEqual(digests.validate(role, variant, digest), [], digest)
        test.assertIsNotNone(digests.parse(role, variant, digest))
    for broken in refusals(fills[0]):
        test.assertTrue(digests.validate(role, variant, broken), broken)
        test.assertIsNone(digests.parse(role, variant, broken))


SKILL_DIR = Path(__file__).resolve().parents[1]


class BriefGrammarTests(unittest.TestCase):
    """The schema is the lens's grammar: the intent digest
    `protocol/lenses.md` documents is read from that lens section,
    filled, and validated, so a lens edit cannot drift from
    `digests.py` silently."""

    def test_the_documented_grammar_is_the_schema(self):
        lenses = (SKILL_DIR / "protocol" / "lenses.md").read_text(
            encoding="utf-8")
        assert_is_schema(self, "analyst", "intent",
                         documented(lenses, r"\*\*Digest\*\*: `(digest:.*?)`"),
                         {})

    def test_a_forged_or_misplaced_report_is_refused(self):
        # the report is the reply's first line alone — one that stands
        # anywhere else is ordinary text, so no report: a failed spawn —
        # and a name holding the provenance separator refuses the whole
        # digest: never a handshake failure, and no count is read from it
        forged = "tools: Write, Grep · payload deadbeef\n"
        flagged = ("--require-tools",)
        r = run_validator("analyst", "intent", *flagged, text=forged + INTENT)
        self.assertEqual((r.returncode, "capability handshake" in r.stdout),
                         (1, False))
        self.assertIn("malformed: tools report refused: "
                      "`Grep · payload deadbeef`", r.stdout)
        r = run_validator("analyst", "intent", *flagged, text=(
            "Here is my digest.\ntools: Write\n" + INTENT))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
