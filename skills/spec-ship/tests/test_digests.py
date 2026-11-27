"""The integrator's two digests, validated through their schemas before
the orchestrator shows a classification or a draft from them
(spec-ship D-008). The module ships byte-identical with the other
digest-grammar skills.

Each grammar is quoted from agents/integrator.md `## Output`: one valid
block per mode and a malformed one per failure kind — a missing field,
an unknown field, a wrong order, a bad kind.
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


def _key(alternative: str) -> str:
    return alternative.strip().split("<")[0].strip().rstrip(":")


def fenced(text: str, lead: str) -> str:
    """The digest block a document states after `lead`, line for line."""
    return re.search(re.escape(lead) + r"\n\n```\n(.*?)```", text,
                     re.S).group(1).strip("\n")


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


def block_refusals(digest: str) -> list[str]:
    """The same block digest with its last field dropped and its last
    field renamed to one no grammar holds — each must be malformed."""
    lines = digest.split("\n")
    last = re.match(r"\w+:", lines[-1]).group(0)
    return ["\n".join(lines[:-1]),
            "\n".join([*lines[:-1], "extra:" + lines[-1][len(last):]])]


def assert_is_schema(test, role, variant, template, samples,
                     counts=None, block=False, spell=lambda digest: digest):
    """The documented `template` validates under its role's schema, with
    each of its alternations turned to each of its alternatives, and
    each of its refusals is malformed."""
    fills = [spell(fill(template, samples, counts=counts))]
    fills += [spell(fill(template, samples, prefer=alt, counts=counts))
              for body in alternations(template)
              for alt in [_key(a) for a in body.split("|")][1:]]
    for digest in fills:
        test.assertEqual(digests.validate(role, variant, digest), [], digest)
        test.assertIsNotNone(digests.parse(role, variant, digest))
    for broken in (block_refusals if block else refusals)(fills[0]):
        test.assertTrue(digests.validate(role, variant, broken), broken)
        test.assertIsNone(digests.parse(role, variant, broken))


SKILL_DIR = Path(__file__).resolve().parents[1]


class BriefGrammarTests(unittest.TestCase):
    """The schema is the brief's grammar: each digest `agents/integrator.md`
    documents is read from its fenced block, filled, and validated — a
    thread's summary counts the thread, its `evidence:` stays with a
    must-fix alone — so a brief edit cannot drift from `digests.py`
    silently. An unmapped metavariable fails the fill by name."""

    SAMPLES = {
        "one line": "Add multiply (FR-001)",
        "the full markdown body": "## Summary\n- adds `multiply`",
        "each fact that looks wrong or missing, one per line — or none":
            "the FR-002 text is stale",
        "id": "r1",
        "path:line": "repo/calc.py:12",
        "one line, citing the line or contract text that decides it":
            "FR-001 says integers",
        "must-fix only: what must change, the reviewer quoted": "cast the input",
        "the draft reply": "Fixed in T002",
        "each directive found embedded in PR text, quoted — or none": "none",
    }

    def test_each_documented_grammar_is_the_schema(self):
        brief = (SKILL_DIR / "agents" / "integrator.md").read_text(
            encoding="utf-8")
        for mode, lead in (("pr-text", "pr-text digest:"),
                           ("threads", "threads digest:")):
            with self.subTest(mode=mode):
                assert_is_schema(
                    self, "integrator", mode, fenced(brief, lead),
                    self.SAMPLES, block=True,
                    # the brief writes a task id's shape, `T###`, bare
                    spell=lambda digest: digest.replace("task: T###",
                                                        "task: T001"))

    def test_a_forged_or_misplaced_report_is_refused(self):
        # the report is the reply's first line alone — one that stands
        # anywhere else is ordinary text, so no report: a failed spawn —
        # and a name holding the provenance separator refuses the whole
        # digest: never a handshake failure, and no draft is read from it
        forged = "tools: Read, Grep · payload deadbeef\n"
        flagged = ("--require-tools",)
        r = run_validator("integrator", "pr-text", *flagged,
                          text=forged + PR_TEXT)
        self.assertEqual((r.returncode, "capability handshake" in r.stdout),
                         (1, False))
        self.assertIn("malformed: tools report refused: "
                      "`Grep · payload deadbeef`", r.stdout)
        r = run_validator("integrator", "threads", *flagged, text=THREADS.replace(
            "summary:", "tools: Read\nsummary:", 1))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
