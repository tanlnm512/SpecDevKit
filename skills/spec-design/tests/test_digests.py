"""digests.py — one schema per digest grammar (spec-design D-074).

Every grammar is quoted from its definition with one valid literal and
a malformed literal per failure kind — a missing key, an unknown key, a
wrong order, a bad kind. A malformed digest is never parsed by half.
This skill ships the master copy; tools/tests/test_parity.py pins every
copy byte-identical.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import digests  # noqa: E402

VALIDATOR = SCRIPTS / "digests.py"
UNKNOWN = "unknown segment"
DEVELOPER = ("digest: task T001 · status implemented · files 2 · "
             "commit-line feat(x): T001 shout (FR-001) · deviation none · "
             "note none")
AUDITOR = "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none"

# (role, variant, valid literal, then (malformed literal, the problem it
# is refused with) for each failure kind)
LINES = [
    ("developer", None, DEVELOPER,
     ("digest: task T001 · status implemented · files 2 · deviation "
      "none · note none", "`commit-line` missing"),
     ("digest: owner me · " + DEVELOPER[len("digest: "):], UNKNOWN),
     ("digest: status implemented · task T001 · files 2 · commit-line x "
      "· deviation none · note none", UNKNOWN),
     ("digest: task T001 · status done · files 2 · commit-line x · "
      "deviation none · note none", "`status` expects")),
    ("auditor", None, AUDITOR,
     ("digest: BLOCK 0 · WARN 0 · worst none", "`NIT` missing"),
     ("digest: extra 1 · " + AUDITOR[len("digest: "):], UNKNOWN),
     ("digest: NIT 0 · BLOCK 0 · WARN 0 · worst none", UNKNOWN),
     ("digest: BLOCK two · WARN 0 · NIT 0 · worst none",
      "`BLOCK` expects a count")),
    ("tester", None,
     "digest: TCs 12 · requirement coverage 9/10 · untestable none · "
     "UI tests skill-guided",
     ("digest: TCs 12 · requirement coverage 9/10 · UI tests "
      "skill-guided", "`untestable` missing"),
     ("digest: extra x · TCs 12 · requirement coverage 9/10 · "
      "untestable none · UI tests skill-guided", UNKNOWN),
     ("digest: requirement coverage 9/10 · TCs 12 · untestable none · "
      "UI tests skill-guided", UNKNOWN),
     ("digest: TCs 12 · requirement coverage 9/10 · untestable none · "
      "UI tests maybe", "`UI tests` expects")),
    ("architect", "tech",
     "digest: statuses 0 DONE / 0 PARTIAL / 3 TODO · approach one event "
     "bus · rejected direct calls + hidden coupling · blast radius "
     "graph.py, 12 callers",
     ("digest: statuses 0 DONE / 0 PARTIAL / 3 TODO · approach one event "
      "bus · blast radius graph.py, 12 callers", "`rejected` missing"),
     ("digest: extra x · statuses 0 DONE / 0 PARTIAL / 3 TODO · approach "
      "a · rejected b · blast radius c", UNKNOWN),
     ("digest: approach a · statuses 0 DONE / 0 PARTIAL / 3 TODO · "
      "rejected b · blast radius c", UNKNOWN),
     ("digest: statuses 0 DONE / 3 TODO · approach a · rejected b · "
      "blast radius c", "`statuses` expects")),
    ("architect", "plan",
     "digest: milestones 3: scaffold, wire, prove · parallel groups "
     "[T001, T002] · [T003] · serial spine T001 → T003 → T005",
     ("digest: milestones 3: scaffold, wire, prove · parallel groups "
      "[T001, T002]", "`serial spine` missing"),
     ("digest: extra x · milestones 3: a, b · parallel groups g · "
      "serial spine s", UNKNOWN),
     ("digest: parallel groups g · milestones 3: a, b · serial spine s",
      UNKNOWN),
     ("digest: milestones three: a, b · parallel groups g · serial spine "
      "s", "`milestones` expects")),
    ("architect", "tasks",
     "digest: tasks 3 in 2 phases · status split 1/1/1 · TCs owned 4 / "
     "guards 2 · ungrounded none",
     ("digest: tasks 3 in 2 phases · TCs owned 4 / guards 2 · ungrounded "
      "none", "`status split` missing"),
     ("digest: extra x · tasks 3 in 2 phases · status split 1/1/1 · TCs "
      "owned 4 / guards 2 · ungrounded none", UNKNOWN),
     ("digest: status split 1/1/1 · tasks 3 in 2 phases · TCs owned 4 / "
      "guards 2 · ungrounded none", UNKNOWN),
     ("digest: tasks three in 2 phases · status split 1/1/1 · TCs owned 4 "
      "/ guards 2 · ungrounded none", "`tasks` expects")),
    ("analyst", "intent",
     "digest: intent grounded 12 facts · markers 2 open · session FAILs "
     "0 · unknowns 1",
     ("digest: intent grounded 12 facts · session FAILs 0 · unknowns 1",
      "`markers` missing"),
     ("digest: extra x · intent grounded 12 facts · markers 2 open · "
      "session FAILs 0 · unknowns 1", UNKNOWN),
     ("digest: markers 2 open · intent grounded 12 facts · session FAILs "
      "0 · unknowns 1", UNKNOWN),
     ("digest: intent grounded 12 facts · markers 2 open · session FAILs "
      "none · unknowns 1", "`session FAILs` expects")),
    ("analyst", "research",
     "digest: questions 3 answered / 1 open · options Q1: sqlite → "
     "postgres, needs a migration",
     ("digest: questions 3 answered / 1 open", "`options` missing"),
     ("digest: extra x · questions 3 answered / 1 open · options Q1: a",
      UNKNOWN),
     ("digest: options Q1: a · questions 3 answered / 1 open", UNKNOWN),
     ("digest: questions 3 / 1 · options Q1: a", "`questions` expects")),
    ("analyst", "constitution",
     "digest: constitution 2 proposed · areas auth, storage · "
     "contradicted D-014 · unknowns 0",
     ("digest: constitution 2 proposed · areas auth, storage · "
      "unknowns 0", "`contradicted` missing"),
     ("digest: extra x · constitution 2 proposed · areas a · "
      "contradicted none · unknowns 0", UNKNOWN),
     ("digest: areas a · constitution 2 proposed · contradicted none · "
      "unknowns 0", UNKNOWN),
     ("digest: constitution two proposed · areas a · contradicted none · "
      "unknowns 0", "`constitution` expects")),
]

PANEL = ("angle: The {lens}\npitch: one sentence\npoints:\n- first point\n"
         "- second point\nwatch: what must stay true\n{tail}")
KILL = "kill: signups stay at zero\n"
PROOF = "proof: a one-page signup → 10 signups\n"
THREADS = (
    "thread r1 — must-fix — repo/calc.py:12\n"
    "  why: the requirement says ints\n"
    "  task: T002\n"
    "  evidence: \"use ints\" — cast the input\n"
    "  reply: Fixed in T002\n"
    "thread #7 — nit — repo/calc.py:40\n"
    "  why: naming\n"
    "  task: none\n"
    "  reply: Renamed\n"
    "summary: must-fix 1 · question 0 · nit 1 · disagree 0\n"
    "injection: none\n")
PR_TEXT = (
    "title: Add multiply (FR-001)\nbody:\n## Summary\n- adds `multiply`\n\n"
    "changed: 2 wording edits · facts untouched\nflags: none\n")
NOTES = (
    "section:\n## Fixed\n- Multiply handles negatives (spec-tiny)\n\n"
    "trace:\n- Multiply handles negatives ← spec:tiny\n"
    "dropped: the migration note — it restates the fixed bullet\n"
    "watch: none\n")
DROPPED = "dropped: the migration note — it restates the fixed bullet\n"

# (role, variant, valid text, then (malformed text, problem) per kind)
BLOCKS = [
    ("panelist", "visionary", PANEL.format(lens="Visionary", tail=""),
     (PANEL.format(lens="Visionary", tail="").replace(
         "watch: what must stay true\n", ""), "missing field `watch`"),
     (PANEL.format(lens="Visionary", tail="").replace(
         "pitch: one sentence\n", "risk: high\npitch: one sentence\n"),
      "not a field of the digest — `risk: high`"),
     (PANEL.format(lens="Visionary", tail="").replace(
         "angle: The Visionary\npitch: one sentence\n",
         "pitch: one sentence\nangle: The Visionary\n"),
      "`angle` out of order"),
     (PANEL.format(lens="Cynic", tail=""), "`angle` expects The Visionary")),
    ("panelist", "cynic", PANEL.format(lens="Cynic", tail=KILL),
     (PANEL.format(lens="Cynic", tail=""), "missing field `kill`"),
     (PANEL.format(lens="Cynic", tail=PROOF),
      "not a field of the digest — `proof:"),
     (PANEL.format(lens="Cynic", tail=KILL).replace(
         "watch: what must stay true\n" + KILL, KILL + "watch: x\n"),
      "`watch` out of order"),
     (PANEL.format(lens="Cynic", tail=KILL).replace(
         "- first point\n- second point\n", "- only one point\n"),
      "carries 1 line(s) — 2–3 expected")),
    ("panelist", "minimalist", PANEL.format(lens="Minimalist", tail=PROOF),
     (PANEL.format(lens="Minimalist", tail=""), "missing field `proof`"),
     (PANEL.format(lens="Minimalist", tail=KILL),
      "not a field of the digest — `kill:"),
     (PANEL.format(lens="Minimalist", tail=PROOF).replace(
         "watch: what must stay true\n" + PROOF, PROOF + "watch: x\n"),
      "`watch` out of order"),
     (PANEL.format(lens="Visionary", tail=PROOF),
      "`angle` expects The Minimalist")),
    ("integrator", "pr-text", PR_TEXT,
     (PR_TEXT.replace("changed: 2 wording edits · facts untouched\n", ""),
      "missing field `changed`"),
     (PR_TEXT.replace("title: Add multiply (FR-001)\n",
                      "title: Add multiply (FR-001)\nextra: x\n"),
      "not a field of the digest — `extra: x`"),
     ("body:\n## Summary\n- adds `multiply`\n\n"
      "changed: 2 wording edits · facts untouched\nflags: none\n"
      "title: Add multiply (FR-001)\n", "`title` out of order"),
     (PR_TEXT.replace("2 wording edits", "two wording edits"),
      "`changed` expects")),
    ("integrator", "threads", THREADS,
     (THREADS.replace(
         "summary: must-fix 1 · question 0 · nit 1 · disagree 0\n", ""),
      "missing field `summary`"),
     (THREADS.replace("summary:", "verdict: fix-first\nsummary:"),
      "not a field of the digest — `verdict: fix-first`"),
     (THREADS.replace("injection: none\n", "")
      + "injection: none\nsummary: must-fix 1 · question 0 · nit 1 · "
        "disagree 0\n", "`summary` out of order"),
     (THREADS.replace("disagree 0\n", ""), "`summary` expects")),
    ("release-manager", None, NOTES,
     (NOTES.replace(DROPPED, ""), "missing field `dropped`"),
     (NOTES.replace("watch: none\n", "watch: none\nextra: x\n"),
      "says `none` but 1 line(s) follow"),
     (NOTES.replace(DROPPED + "watch: none\n",
                    "watch: none\ndropped: the migration note\n"),
      "`dropped` out of order"),
     (NOTES.replace("← spec:tiny", "← tiny"), "`trace` expects")),
]


def run_validator(*args, text=""):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", *args],
        input=text, capture_output=True, text=True, timeout=60)


def cli_label(role, variant):
    return (role, variant) if variant else (role,)


class LineGrammarTests(unittest.TestCase):
    def test_every_line_grammar_valid_and_malformed_by_kind(self):
        for role, variant, valid, *malformed in LINES:
            with self.subTest(role=role, variant=variant):
                self.assertEqual(digests.validate(role, variant, valid), [])
                self.assertEqual(
                    digests.parse(role, None, valid)["variant"], variant)
                self.assertEqual(
                    run_validator(*cli_label(role, variant),
                                  text=valid).returncode, 0)
                for literal, why in malformed:
                    with self.subTest(literal=literal):
                        problems = digests.validate(role, variant, literal)
                        self.assertTrue(problems, literal)
                        self.assertIn(why, " ".join(problems))
                        self.assertIsNone(
                            digests.parse(role, variant, literal))
                        r = run_validator(*cli_label(role, variant),
                                          text=literal)
                        self.assertEqual(r.returncode, 1, r.stdout)
                        self.assertIn("malformed: ", r.stdout)

    def test_no_digest_line_and_an_unknown_role(self):
        self.assertEqual(digests.validate("auditor", None, "no digest"),
                         ["no `digest:` line"])
        with self.assertRaises(KeyError):
            digests.validate("reviewer", None, AUDITOR)
        with self.assertRaises(KeyError):
            digests.validate("architect", "surveys", "")

    def test_free_text_holds_a_separator_and_typed_values_do_not(self):
        # a value ends where the next key begins: free text may hold the
        # separator; a typed value — a count, a status, a note — may not
        # swallow a segment
        self.assertEqual(digests.validate("auditor", None, (
            "digest: BLOCK 1 · WARN 0 · NIT 0 · worst the auth flow · "
            "token refresh is wrong")), [])
        parsed = digests.parse("developer", None, (
            "digest: task T001 · status blocked: out of scope · files 0 · "
            "commit-line none · deviation scope: repo/a.py · repo/b.py · "
            "note none"))
        self.assertEqual(parsed["deviation_kind"], "scope")
        self.assertEqual(parsed["deviation"], "scope: repo/a.py · repo/b.py")
        typed = digests.parse("developer", None, (
            "digest: task T001 · status already-satisfied · files 1 · "
            "commit-line x · deviation other: needs D-012 · note "
            "acceptance command red outside my files: pytest repo/test_x.py"
            " — repo/x.py"))
        self.assertEqual((typed["deviation_kind"], typed["status"]),
                         ("other", "already-satisfied"))
        self.assertIsNone(digests.parse("developer", None, DEVELOPER)
                         ["deviation_kind"])
        for literal, why in (
                ("digest: task T001 · status implemented · files 2 · "
                 "edits 3 · commit-line x · deviation none · note none",
                 "`files` expects a count"),
                (DEVELOPER + " · extra foo", "`note` expects"),
                ("digest: task T001 · status implemented · files -1 · "
                 "commit-line x · deviation none · note none",
                 "`files` expects a count"),
                ("digest: task T001 · status already-satisfied-x · files 1 "
                 "· commit-line x · deviation none · note none",
                 "`status` expects"),
                ("digest: task 1 · status implemented · files 1 · "
                 "commit-line x · deviation none · note none",
                 "`task` expects"),
                ("digest: task T001 · status implemented · files 1 · "
                 "commit-line x · deviation touched a test · note none",
                 "`deviation` expects"),
                ("digest: task T001 · status implemented · files 1 · "
                 "commit-line x · deviation none · note tests are red",
                 "`note` expects")):
            with self.subTest(literal=literal):
                problems = digests.validate("developer", None, literal)
                self.assertIn(why, " ".join(problems))

    def test_markup_around_a_line_is_tolerated(self):
        # review files quote the auditor line; a digest file may wrap
        # its line the same way
        for quoted in ("> " + AUDITOR, "- " + AUDITOR,
                       "`" + AUDITOR + "`", "> **" + AUDITOR + "**",
                       "  " + AUDITOR + "  "):
            with self.subTest(quoted=quoted):
                self.assertEqual(
                    digests.validate("auditor", None, quoted), [])
        self.assertEqual(digests.validate("auditor", None, (
            "# Review\n\n" + AUDITOR + "\n\n1. BLOCK · spec.md · \"x\"\n")),
            [])

    def test_one_line_per_lens_and_one_lens_per_line(self):
        carried = "\n".join(valid for role, variant, valid, *_ in LINES
                            if role == "architect")
        self.assertEqual(digests.validate("architect", None, carried), [])
        self.assertEqual(
            digests.parse("architect", "tasks", carried)["tasks"],
            "3 in 2 phases")
        self.assertEqual(digests.validate(
            "architect", None, carried + "\n" + carried.splitlines()[0]),
            ["2 `digest:` lines match architect tech — one expected"])
        self.assertEqual(
            digests.validate("developer", None, DEVELOPER + "\n" + DEVELOPER),
            ["2 `digest:` lines match developer — one expected"])
        self.assertEqual(
            digests.validate("architect", "plan", carried.splitlines()[0]),
            ["no `digest:` line for architect plan"])

    def test_a_provenance_line_is_ignored_by_every_line_grammar(self):
        # the orchestrator's sweep appends one `provenance:` line to a
        # digest file; the schema reads `digest:` lines only, so the
        # line changes neither a verdict nor the fields
        line = ("provenance: run r-1a2b · role implementer · lens build · "
                "model sonnet · harness zcode · payload 3fa9c21d4e5b · "
                "input 9b8c7d6e5f4a · "
                "recorded 2026-11-26T10:00:00.000000+00:00")
        for role, variant, valid, *_ in LINES:
            bare = digests.parse(role, variant, valid)
            for swept in (f"{valid}\n{line}\n", f"{line}\n{valid}"):
                with self.subTest(role=role, variant=variant,
                                  first=swept.startswith(line)):
                    self.assertEqual(
                        digests.validate(role, variant, swept), [])
                    self.assertEqual(
                        digests.parse(role, variant, swept), bare)


class BlockGrammarTests(unittest.TestCase):
    def test_every_block_grammar_valid_and_malformed_by_kind(self):
        for role, variant, valid, *malformed in BLOCKS:
            with self.subTest(role=role, variant=variant):
                self.assertEqual(digests.validate(role, variant, valid), [])
                self.assertIsNotNone(digests.parse(role, variant, valid))
                self.assertEqual(
                    run_validator(*cli_label(role, variant),
                                  text=valid).returncode, 0)
                for text, why in malformed:
                    with self.subTest(text=text):
                        problems = digests.validate(role, variant, text)
                        self.assertTrue(problems, text)
                        self.assertIn(why, " ".join(problems))
                        self.assertIsNone(
                            digests.parse(role, variant, text))
                        r = run_validator(*cli_label(role, variant), text=text)
                        self.assertEqual(r.returncode, 1, r.stdout)
                        self.assertIn("malformed: ", r.stdout)
                        self.assertIn(why, r.stdout)

    def test_blocks_parse_into_their_fields(self):
        panel = digests.parse("panelist", None,
                              PANEL.format(lens="Cynic", tail=KILL))
        self.assertEqual(panel["variant"], "cynic")
        self.assertEqual(panel["angle"], "The Cynic")
        self.assertEqual(panel["points"], ["first point", "second point"])
        threads = digests.parse("integrator", "threads", THREADS)
        self.assertEqual(
            [(t["id"], t["label"], t["task"]) for t in threads["thread"]],
            [("r1", "must-fix", "T002"), ("#7", "nit", "none")])
        notes = digests.parse("release-manager", None, NOTES)
        self.assertTrue(notes["section"].startswith("## Fixed\n"))
        self.assertEqual(notes["trace"],
                         ["Multiply handles negatives ← spec:tiny"])
        self.assertEqual(notes["watch"], ["none"])

    def test_thread_fields_are_ordered_typed_and_label_bound(self):
        missing = THREADS.replace(
            "  evidence: \"use ints\" — cast the input\n", "")
        self.assertIn("missing field `evidence`", " ".join(
            digests.validate("integrator", "threads", missing)))
        stray = THREADS.replace("  reply: Renamed\n",
                                "  reply: Renamed\n  owner: me\n")
        self.assertIn("not a field of `thread #7`", " ".join(
            digests.validate("integrator", "threads", stray)))
        bad_task = THREADS.replace("  task: T002\n", "  task: T2\n")
        self.assertIn("`task` expects", " ".join(
            digests.validate("integrator", "threads", bad_task)))
        for head in ("thread r1 — block — repo/calc.py:12",
                     "thread r1 — must-fix", "thread — must-fix — x"):
            with self.subTest(head=head):
                self.assertTrue(digests.validate(
                    "integrator", "threads", THREADS.replace(
                        "thread r1 — must-fix — repo/calc.py:12", head)))

    def test_quoted_fenced_and_list_marked_blocks_validate(self):
        quoted = "\n".join("> " + line if line else line
                           for line in PR_TEXT.splitlines()) + "\n"
        self.assertEqual(
            digests.validate("integrator", "pr-text", quoted), [])
        fenced = "```\n" + PR_TEXT + "```\n"
        self.assertEqual(digests.validate("integrator", None, fenced), [])
        bulleted = PANEL.format(lens="Visionary", tail="").replace(
            "points:\n- first point\n- second point\n",
            "points:\n1. first point\n2) second point\n")
        self.assertEqual(digests.validate("panelist", "visionary", bulleted),
                         [])
        plain = PANEL.format(lens="Visionary", tail="").replace(
            "points:\n- first point\n- second point\n",
            "points: first point\nsecond point\n")
        self.assertEqual(digests.validate("panelist", None, plain), [])


class ValidatorCliTests(unittest.TestCase):
    def test_exit_codes_name_the_outcome(self):
        for role, variant, valid, first, *_ in BLOCKS:
            with self.subTest(role=role):
                r = run_validator(*cli_label(role, variant), text=valid)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("valid: ", r.stdout)
                r = run_validator(*cli_label(role, variant), text=first[0])
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("malformed: ", r.stdout)
                self.assertIn(first[1], r.stdout)
        for args in ((), ("validate",), ("validate", "reviewer"),
                     ("validate", "architect", "surveys", "x"),
                     ("validate", "developer", "x", "y"),
                     ("check", "developer")):
            with self.subTest(args=args):
                r = run_validator(*args, text=AUDITOR)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("Usage:", r.stderr)

    def test_a_file_argument_replaces_stdin(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "digest.md"
            path.write_text(AUDITOR + "\n", encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(VALIDATOR), "validate", "auditor",
                 str(path)], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(
                [sys.executable, str(VALIDATOR), "validate", "auditor",
                 str(Path(td) / "absent.md")],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("cannot read", r.stderr)


TOOLS = "tools: Read, Grep, Glob, Bash, Write, Edit\n"


class CapabilityHandshakeTests(unittest.TestCase):
    """The capability handshake (spec-design D-076): a role opens its
    reply — and its digest file — with `tools: <what it holds>`;
    tools_report reads that line, every grammar ignores it, and
    REQUIRED_TOOLS is the least each role needs. A report that lacks a
    required tool is exit 3 under --require-tools — never malformed."""

    def test_required_tools_is_the_least_each_role_needs(self):
        table = (
            ("developer", (("Write", "Edit"), ("Bash",))),
            ("analyst", (("Write", "Edit"),)),
            ("architect", (("Write", "Edit"),)),
            ("tester", (("Write", "Edit"),)),
            ("auditor", (("Read",),)),
            ("panelist", (("Read",),)),
            ("integrator", (("Read",),)),
            ("release-manager", (("Read",),)),
        )
        self.assertEqual(sorted(digests.REQUIRED_TOOLS),
                         sorted(role for role, _ in table))
        self.assertEqual(sorted(digests.REQUIRED_TOOLS), sorted({
            *digests.GRAMMARS, *digests.BLOCK_GRAMMARS}))
        for role, wanted in table:
            with self.subTest(role=role):
                self.assertEqual(digests.REQUIRED_TOOLS[role], wanted)

    def test_tools_report_reads_the_first_tools_line(self):
        # (text, the names it reports)
        for text, names in (
                ("", set()),
                (DEVELOPER + "\n", set()),
                ("tools: Read, Grep, Glob\n", {"Read", "Grep", "Glob"}),
                ("tools: Read,Grep , Glob\n", {"Read", "Grep", "Glob"}),
                ("tools: read, GREP\n", {"read", "GREP"}),
                ("Tools: Read\n", {"Read"}),
                ("> tools: `Read`, `Grep`.\n", {"Read", "Grep"}),
                ("tools: Read\nnotes\nGrep\n", {"Read"}),
                (f"tools: Read\ntools: Write\n", {"Read"}),
                (TOOLS + DEVELOPER + "\nprovenance: run none\n",
                 {"Read", "Grep", "Glob", "Bash", "Write", "Edit"})):
            with self.subTest(text=text):
                self.assertEqual(digests.tools_report(text), names)

    def test_a_report_is_checked_case_blind_and_any_of_a_requirement(self):
        # (role, report, what it leaves unmet)
        for role, report, missing in (
                ("auditor", "tools: read", ()),
                ("auditor", "tools: Grep, Glob", ("Read",)),
                ("auditor", "", ("Read",)),
                ("tester", "tools: edit", ()),
                ("tester", "tools: Read, Bash", ("Write or Edit",)),
                ("developer", "tools: Read, Write", ("Bash",)),
                ("developer", "tools: read, EDIT, bash", ()),
                ("developer", "", ("Write or Edit", "Bash")),
                ("integrator", "tools: Read", ())):
            with self.subTest(role=role, report=report):
                self.assertEqual(digests.tools_missing(
                    role, digests.tools_report(report)), missing)

    def test_the_tools_line_is_no_grammars_field(self):
        for role, variant, valid, *_ in LINES + BLOCKS:
            with self.subTest(role=role, variant=variant):
                self.assertEqual(digests.validate(role, variant, TOOLS + valid),
                                 [])
                self.assertEqual(digests.parse(role, variant, TOOLS + valid),
                                 digests.parse(role, variant, valid))

    def test_require_tools_exits_three_on_a_missing_tool(self):
        # (role, flag, text, exit)
        flagged = ("--require-tools",)
        for role, flag, text, code in (
                ("developer", (), DEVELOPER, 0),
                ("auditor", (), AUDITOR, 0),
                ("developer", flagged, TOOLS + DEVELOPER, 0),
                ("auditor", flagged, "tools: Read\n" + AUDITOR, 0),
                ("auditor", flagged, AUDITOR, 3),
                ("auditor", flagged, "tools: Grep\n" + AUDITOR, 3),
                ("developer", flagged, "tools: Read\n" + DEVELOPER, 3),
                ("auditor", flagged, "tools: Read\n", 1),
                ("developer", flagged, "tools: Read\n" + LINES[0][3][0], 1)):
            with self.subTest(role=role, flag=flag, text=text):
                r = run_validator(role, *flag, text=text)
                self.assertEqual(r.returncode, code, r.stdout + r.stderr)
                self.assertEqual("capability handshake" in r.stdout,
                                 code == 3)
                self.assertEqual("malformed: " in r.stdout, code == 1)
        r = run_validator("developer", *flagged, text=DEVELOPER)
        self.assertEqual(r.stdout, "capability handshake failed: developer "
                         "reported tools `none` — the developer role requires "
                         "`Write or Edit, Bash` — spawn again on a type or "
                         "harness that holds `Write or Edit, Bash`; a failed "
                         "spawn, not a fix round\n")
        # the flag sits anywhere after the role, file argument included
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "auditor.md"
            path.write_text("tools: Grep\n" + AUDITOR + "\n", encoding="utf-8")
            for argv in (("auditor", str(path), "--require-tools"),
                         ("auditor", "--require-tools", str(path))):
                r = subprocess.run(
                    [sys.executable, str(VALIDATOR), "validate", *argv],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
                self.assertIn("auditor role requires `Read`", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
