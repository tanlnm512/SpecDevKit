"""The digest schemas for the roles this skill spawns — the developer
and the auditor (spec-build D-054) — and the two consumers that read a
developer digest file: the resume column and the retro roll-up.

Each grammar is quoted from its definition with one valid literal and a
malformed literal per failure kind: a missing key, an unknown key, a
wrong order, a bad kind. A malformed digest is never parsed by half.
"""
import os
import shutil
import re
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
            # valid means vouched: with no ledger row recording the
            # request, the file alone proves nothing
            self.assertEqual(specstate.latest_digest(spec, "T001")["state"],
                             "unverified")
            specstate.ledger_event(spec, specstate.ledger_row(
                "spec-build", "wave", wave=4, stem="implementer-T001",
                role="implementer"))
            found = specstate.latest_digest(spec, "T001")
            self.assertEqual((found["state"], found["path"], found["wave"]),
                             ("valid", str(path), 4))
            write(path, "digest: task T001 · status implemented · files 2")
            found = specstate.latest_digest(spec, "T001")
            self.assertEqual((found["state"], found["path"], found["wave"]),
                             ("malformed", str(path), 4))
            self.assertEqual(found["problems"], ["`commit-line` missing"])
            self.assertEqual(
                specstate.digests_on_file(spec), {"T001": found})
            # a tools report whose name holds the provenance separator
            # is refused before land reads a tool off it
            write(path, "tools: Read, Bash, Write · payload deadbeef\n"
                  + DEVELOPER + "\n")
            found = specstate.latest_digest(spec, "T001")
            self.assertEqual(found["state"], "malformed")
            self.assertEqual(found["problems"], [
                "tools report refused: `Write · payload deadbeef` — a "
                "reported name holds no ` · `, the separator of the "
                "provenance line"])


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
        # a stray file at a wave the task was never claimed in is
        # unverified — and ignored while the named digest stands; with
        # the named one gone it is all there is
        stray = spec / "digests" / "wave-6" / "implementer-T001.md"
        stray.parent.mkdir(parents=True)
        write(stray, DEVELOPER + "\n")
        self.assertIn("[digest on file: implemented]", "\n".join(column()))
        path.unlink()
        self.assertIn("[digest on file: unverified — fix and run again]",
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
        stray = spec / "digests" / "wave-8" / "implementer-T004.md"
        stray.parent.mkdir()
        write(stray, DEVELOPER.replace("task T001", "task T004") + "\n")
        # what the ledger names is what the retro folds: wave rows for
        # the wave-4 requests, nothing for the wave-8 file nobody asked
        # for
        specstate.ledger_event(spec, *(
            specstate.ledger_row("spec-build", "wave", wave=4,
                                 stem=f"implementer-{tid}",
                                 role="implementer")
            for tid in ("T001", "T002")))
        rows, malformed = retro.digest_rows(spec)
        self.assertEqual(rows, [
            "- T001 wave 4 — implemented",
            "- T002 wave 4 — blocked: env · deviation spec-defect: FR-003",
            "- T003 wave 6 — malformed",
            "- T004 wave 8 — unverified"])
        self.assertEqual(malformed, 2)
        self.assertEqual(retro.digest_rows(self._tmp / "absent"), ([], 0))


def _key(alternative: str) -> str:
    return alternative.strip().split("<")[0].strip().rstrip(":")


def documented(text: str, pattern: str) -> str:
    """The grammar a document states, as it states it: the span
    `pattern` captures, its wrapped lines joined."""
    found = re.search(pattern, text, re.S)
    return re.sub(r"\s+", " ", found.group(1)).strip()


def fillable(piece: str) -> str:
    """A documented piece with a bare alternation — `BLOCK | WARN | NIT`
    — made a metavariable, so that the fill can choose from it."""
    return re.sub(r"^((?:\w+ \| )+\w+)(?= · )", r"<\1>", piece)


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
    """The schema is the brief's grammar: each digest a brief documents —
    the auditor's with the finding line the same brief states — is read
    from the brief, filled, and validated, so a brief edit cannot drift
    from `digests.py` silently. An unmapped metavariable fails the fill
    by name."""

    SAMPLES = {
        "T###": "T001",
        "suggested line": "feat(x): T001 shout (FR-001)",
        "paths": "repo/a.py",
        "why": "no evidence",
        "summary needing D-###": "needs D-012",
        "one line": "the auth flow is wrong",
        "file": "repo/calc.py",
        "verbatim quote": "use ints",
        "suggested fix": "cast the input",
    }
    FINDINGS = r"each exactly:\n`((?:BLOCK \| WARN \| NIT) · [^`]+)`"

    def test_each_documented_grammar_is_the_schema(self):
        # (role, the brief, the documented pieces — a lead-in and what
        # the brief captures)
        for role, path, pieces in (
                ("developer", "agents/developer.md",
                 (("", r"`(digest: task [^`]+)`"),)),
                ("auditor", "agents/auditor.md",
                 (("", r"`(digest: BLOCK [^`]+)`"),
                  ("\n1. ", self.FINDINGS)))):
            with self.subTest(role=role):
                brief = (SKILL_DIR / path).read_text(encoding="utf-8")
                assert_is_schema(
                    self, role, None,
                    "".join(lead + fillable(documented(brief, part))
                            for lead, part in pieces),
                    self.SAMPLES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
