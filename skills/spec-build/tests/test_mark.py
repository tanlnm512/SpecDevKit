"""mark.py's transition table — D-034's marker table made executable
(spec-build D-039).

The table test owns the state machine: one table of (starting entry,
verb, args) → expected entry text | refusal, covering every D-034 row
plus the claim stamp's life (written on claim, removed on land/release/
tick, never history). Beyond the table:

  - claim --wave refuses a stale wave: a hand-written claim on T001
    makes a wave holding T001 refuse everything, task.md unchanged;
  - lock contention: a held task_lock exits 5; a 60s+-old lock file is
    broken and the claim succeeds;
  - land refuses on red proofs (a deterministically red TC) and on
    zero runnable proofs;
  - tick strips the stamp sub-line of exactly the ticked entry;
  - the tiny tier: a stamped claim keeps the frozen spec verifiable,
    and drop refuses outright.

Fixtures are mutated copies of examples/mini-spec (claims, fail rounds,
drops — no TC execution) and a hand-authored docset whose TC pass
conditions are deterministic one-liners (land's proofs gate). Every CLI
run gets its own telemetry dir.
"""

import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from test_execute_gates import (  # noqa: E402
    T1,
    T2,
    TINY_SPEC,
    copy_fixture,
    edit_tasks,
    facts,
    freeze,
    hand_docset,
    record_approval,
    run_graph,
    set_status,
    write,
)
import _approval  # noqa: E402
import digests  # noqa: E402
import specstate  # noqa: E402

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
MARK = SCRIPTS / "mark.py"

EM = "\u2014"
# a developer digest file opens with its capability handshake report
TOOLS = "tools: Read, Write, Bash\n"
REPORTED = "Bash, Read, Write"

# The fixture entries' FULL first lines (T1/T2 from test_execute_gates are
# prefixes — a prefix replace would glue a stamp mid-line)
T1F = ("- [ ] T001 [P] Implement multiply in `repo/calc.py` "
       "(FR-001, FR-002)")
T2F = ("- [ ] T002 [P] Add multiply tests to `repo/test_calc.py` "
       "(FR-001, FR-002)")


def run_mark(spec_dir: Path, *args: str, tel: Path) -> subprocess.CompletedProcess:
    """mark.py <verb> <spec-dir> … as the CLI — args[0] is the verb, the
    spec dir rides behind it."""
    env = dict(os.environ, KIT_TELEMETRY_DIR=str(tel), KIT_TELEMETRY="on")
    return subprocess.run(
        [sys.executable, str(MARK), args[0], str(spec_dir), *args[1:]],
        capture_output=True, text=True, timeout=300, env=env)


def mark_events(tel: Path) -> list[dict]:
    p = tel / "spec-build.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in
            p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def entry_text(spec_dir: Path, task_id: str) -> str:
    """The entry's block as the file holds it: the first line plus its
    sub-lines up to the blank line — what a refusal or a write shapes.
    Matches the struck form too (a dropped entry keeps its T-id)."""
    holder = spec_dir / "task.md"
    lines = holder.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines)
                 if re.match(rf"^- \[[x ]\] (?:~~)?{task_id}\b", ln))
    end = start + 1
    while end < len(lines) and lines[end].strip() \
            and not lines[end].startswith("- ["):
        end += 1
    return "\n".join(lines[start:end])


def make_wave(spec_dir: Path, *task_ids: str, wave: int = 4) -> Path:
    """A fresh wave dir: a wave emit clears its dir first, so the claim
    sees exactly this wave's payloads."""
    d = spec_dir / "spawns" / f"wave-{wave}"
    d.mkdir(parents=True, exist_ok=True)
    for stale in d.glob("implementer-T*.md"):
        stale.unlink()
    for tid in task_ids:
        (d / f"implementer-{tid}.md").write_text("payload\n", encoding="utf-8")
    return d


def hand_fixture(tmp: Path, name: str = "hand", *, fail_tc: bool = False) -> Path:
    """An approved hand-authored docset whose T001 proof is a
    deterministic one-liner — green, or deterministically red for the
    land-refusal test."""
    d = hand_docset(tmp / name, "approved")
    if fail_tc:
        test = d / "test.md"
        write(test, test.read_text(encoding="utf-8").replace(
            "`python3 -c 'print(\"HI\")'`",
            "`python3 -c 'import sys; sys.exit(1)'`"))
    return d


class TransitionTableTests(unittest.TestCase):
    """One table row per D-034 transition: starting entry → verb → the
    written entry, or the refusal. Every write is lock-and-atomic; every
    refusal changes nothing."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="mark-table-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = copy_fixture(self._tmp, "demo")
        set_status(self.spec, "approved")

    def fresh(self, *edits: tuple[str, str]) -> Path:
        root = self._tmp / f"r{time.monotonic_ns()}"
        spec = copy_fixture(root)
        set_status(spec, "approved")
        if edits:
            edit_tasks(spec, *edits)
        return spec

    def test_table_claim_writes_in_progress_and_stamp(self):
        r = run_mark(self.spec, "claim", "--wave", str(make_wave(self.spec, "T001", "T002")),
                     "--run-id", "r-table", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("claimed 2: T001, T002", r.stdout)
        for tid in ("T001", "T002"):
            block = entry_text(self.spec, tid)
            self.assertIn("(in-progress)", block.splitlines()[0])
            stamp = [ln for ln in block.splitlines()[1:]
                     if specstate.CLAIM_NOTE.match(ln)]
            self.assertEqual(len(stamp), 1, block)
            self.assertRegex(stamp[0],
                             r"^  - claimed \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
                             rf" {EM} run r-table$")
        events = [e for e in mark_events(self.tel) if e["event"] == "task_claim"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["tasks"], 2)

    def test_table_claim_without_run_id_prints_a_generated_one(self):
        r = run_mark(self.spec, "claim", "--wave", str(make_wave(self.spec, "T001")),
                     tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("claimed 1: T001", r.stdout)
        self.assertRegex(r.stdout, r"run id: r-[0-9a-f]{4}")

    def test_table_land_writes_implemented_and_drops_the_stamp(self):
        make_wave(self.spec, "T001")
        run_mark(self.spec, "claim", "--wave",
                 str(self.spec / "spawns" / "wave-4"), tel=self.tel)
        r = run_mark(self.spec, "land", "T001",
                     "--digest", "digest: task T001 · status implemented · "
                     "files 1 · commit-line x", tel=self.tel)
        # the fixture's proofs run its real TC commands; this machine has
        # no pytest, so the red path is exercised below on a deterministic
        # red TC — here we only pin the refusal shape when proofs run
        self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)
        if r.returncode == 0:
            block = entry_text(self.spec, "T001")
            self.assertIn("(implemented)", block.splitlines()[0])
            self.assertNotIn("(in-progress)", block.splitlines()[0])
            self.assertFalse(specstate.CLAIM_NOTE.search(block))

    def test_table_land_refuses_a_pending_entry(self):
        r = run_mark(self.spec, "land", "T001",
                     "--digest", "digest: task T001 · status implemented",
                     tel=self.tel)
        self.assertEqual(r.returncode, 1)
        self.assertIn("allowed from: (in-progress)", r.stdout)
        self.assertNotIn("(implemented)", entry_text(self.spec, "T001"))

    def test_table_land_refuses_without_a_digest(self):
        make_wave(self.spec, "T001")
        run_mark(self.spec, "claim", "--wave",
                 str(self.spec / "spawns" / "wave-4"), tel=self.tel)
        r = run_mark(self.spec, "land", "T001", tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("digest", r.stdout + r.stderr)

    def test_table_release_clears_claim_and_stamp(self):
        edit_tasks(self.spec, (T1F, T1F.replace("[P]", "[P] (in-progress)")
                               + f"\n  - claimed 2026-11-13T10:00:00Z "
                                 f"{EM} run r-dead"))
        r = run_mark(self.spec, "release", "T001",
                     "--reason", "orphan: dead session", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        block = entry_text(self.spec, "T001")
        self.assertNotIn("(in-progress)", block)
        self.assertFalse(specstate.CLAIM_NOTE.search(block))
        self.assertIn("orphan", r.stdout)
        events = [e for e in mark_events(self.tel)
                  if e["event"] == "task_release"]
        self.assertEqual(events[0]["payload"]["reason"], "orphan")

    def test_table_release_refuses_a_pending_entry(self):
        r = run_mark(self.spec, "release", "T001",
                     "--reason", "orphan", tel=self.tel)
        self.assertEqual(r.returncode, 1)
        self.assertIn("nothing to release", r.stdout)

    def test_table_fail_opens_round_one_from_a_claim(self):
        edit_tasks(self.spec, (T1, T1.replace("[P]", "[P] (in-progress)")))
        evidence = self._tmp / "ev.txt"
        digest = "E   AssertionError: multiply(2, 3) returned 5"
        write(evidence, f"$ pytest -k multiply\n{digest}\n")
        r = run_mark(self.spec, "fail", "T001", "--evidence", str(evidence),
                     "--digest", digest, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        block = entry_text(self.spec, "T001")
        self.assertIn("(fix 1/5)", block.splitlines()[0])
        self.assertNotIn("(in-progress)", block)
        self.assertIn(f"  - fix 1 {EM} {digest}", block)
        note = (self.spec / "notes" / "T001.md").read_text(encoding="utf-8")
        self.assertIn("## Fix round 1", note)
        self.assertIn(digest, note)  # verbatim, not summarized
        events = [e for e in mark_events(self.tel)
                  if e["event"] == "task_fail"]
        self.assertEqual(events[0]["payload"]["round"], 1)

    def test_table_fail_opens_beside_implemented(self):
        edit_tasks(self.spec, (T1, T1.replace("[P]", "[P] (implemented)")))
        evidence = self._tmp / "ev.txt"
        digest = "BLOCK: the error branch has no test"
        write(evidence, digest)
        r = run_mark(self.spec, "fail", "T001", "--evidence", str(evidence),
                     "--digest", digest, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        first = entry_text(self.spec, "T001").splitlines()[0]
        self.assertIn("(implemented)", first)
        self.assertIn("(fix 1/5)", first)

    def test_table_fail_supersedes_the_in_flight_round(self):
        edit_tasks(self.spec, (T1, T1.replace(
            "[P]", "[P] (in-progress) (fix 2/5)")
            + f"\n  - fix 2 {EM} previous failure digest"))
        evidence = self._tmp / "ev.txt"
        digest = "E   TypeError: multiply(None, 3) crashed"
        write(evidence, digest)
        r = run_mark(self.spec, "fail", "T001", "--evidence", str(evidence),
                     "--digest", digest, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        block = entry_text(self.spec, "T001")
        self.assertIn("(fix 3/5)", block.splitlines()[0])
        self.assertNotIn("(in-progress)", block)
        self.assertIn(f"  - fixed 2 {EM} failed again {EM} superseded by "
                      "round 3", block)
        self.assertIn(f"  - fix 3 {EM} {digest}", block)

    def test_table_fail_refuses_a_digest_not_in_the_evidence(self):
        edit_tasks(self.spec, (T1, T1.replace("[P]", "[P] (in-progress)")))
        evidence = self._tmp / "ev.txt"
        write(evidence, "$ pytest -k multiply\nE   something else\n")
        r = run_mark(self.spec, "fail", "T001", "--evidence", str(evidence),
                     "--digest", "E   invented failure", tel=self.tel)
        self.assertEqual(r.returncode, 1)
        self.assertIn("verbatim", r.stderr)
        self.assertNotIn("(fix", entry_text(self.spec, "T001"))

    def frontier_state(self, spec_dir: Path, task_id: str) -> str:
        """The engine's view of one task — what decides whether the next
        emit re-spawns it."""
        import graph  # the replica closure shares the master's behavior
        tasks = graph.task_frontier(specstate.task_entries(
            (spec_dir / "task.md").read_text(encoding="utf-8")))
        return next(t["state"] for t in tasks if t["id"] == task_id)

    def test_table_fail_refuses_past_the_cap(self):
        # the engine's arithmetic end to end: each of the first four
        # failures leaves a round the engine re-spawns, the fifth writes
        # the stop marker, and nothing above it is a round
        edit_tasks(self.spec, (T1, T1.replace("[P]", "[P] (in-progress)")))
        evidence = self._tmp / "ev.txt"
        after_fail = []
        for n in range(1, 6):
            write(evidence, f"$ pytest -k multiply\nE   failure {n}\n")
            r = run_mark(self.spec, "fail", "T001", "--evidence", str(evidence),
                         "--digest", f"E   failure {n}", tel=self.tel)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            after_fail.append(self.frontier_state(self.spec, "T001"))
            self.assertIn(f"(fix {n}/5)",
                          entry_text(self.spec, "T001").splitlines()[0])
            if n < 5:
                # the round's re-spawn: the next wave claims the task
                claim = run_mark(self.spec, "claim", "--wave",
                                 str(make_wave(self.spec, "T001")),
                                 tel=self.tel)
                self.assertEqual(claim.returncode, 0,
                                 claim.stdout + claim.stderr)
        self.assertEqual(after_fail, ["runnable"] * 4 + ["at-fix-cap"])
        claim = run_mark(self.spec, "claim", "--wave",
                         str(make_wave(self.spec, "T001")), tel=self.tel)
        self.assertEqual(claim.returncode, 1, claim.stdout + claim.stderr)
        self.assertIn("stale wave: T001: at-fix-cap", claim.stdout)
        write(evidence, "E   yet another failure")
        r = run_mark(self.spec, "fail", "T001", "--evidence", str(evidence),
                     "--digest", "E   yet another failure", tel=self.tel)
        self.assertEqual(r.returncode, 1)
        self.assertIn("above the cap", r.stderr)

    def test_table_fail_announces_round_guidance(self):
        for start, n, fragment in (
                (2, 3, "/spec-design before round 4"),
                (3, 4, "spawn one model step up"),
                (4, 5, "the cap")):
            spec = self.fresh(
                (T1F, T1F.replace(
                    "[P]",
                    f"[P] (in-progress) (fix {start}/5)")
                 + f"\n  - fix {start} {EM} d{start}"))
            evidence = self._tmp / f"ev{n}.txt"
            digest = f"E   failure {n}"
            write(evidence, digest)
            r = run_mark(spec, "fail", "T001", "--evidence", str(evidence),
                         "--digest", digest, tel=self.tel)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn(fragment, r.stdout, n)
            self.assertIn(f"(fix {n}/5)", entry_text(spec, "T001"))

    def test_table_drop_strikes_with_the_decision(self):
        r = run_mark(self.spec, "drop", "T002", "--decision", "D-001",
                     tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        block = entry_text(self.spec, "T002")
        self.assertRegex(block.splitlines()[0],
                         r"^- \[ \] ~~T002~~ dropped \d{4}-\d{2}-\d{2} "
                         r"\(D-001\)$")
        events = [e for e in mark_events(self.tel) if e["event"] == "task_drop"]
        self.assertEqual(events[0]["payload"]["decision"], "D-001")

    def test_table_drop_refuses_an_undefined_decision(self):
        before = (self.spec / "task.md").read_bytes()
        r = run_mark(self.spec, "drop", "T002", "--decision", "D-042",
                     tel=self.tel)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not defined in tech-spec.md", r.stderr)
        self.assertEqual((self.spec / "task.md").read_bytes(), before)

    def test_table_drop_refuses_a_ticked_entry(self):
        edit_tasks(self.spec, (T1, T1.replace("- [ ]", "- [x]")))
        r = run_mark(self.spec, "drop", "T001", "--decision", "D-001",
                     tel=self.tel)
        self.assertEqual(r.returncode, 1)
        self.assertIn("delivered work", r.stdout)

    def test_table_refusals_leave_the_entry_unchanged(self):
        before = (self.spec / "task.md").read_bytes()
        evidence = self._tmp / "ev-refuse.txt"
        write(evidence, "$ pytest\nE   real output\n")
        for verb, args in (("land", ("T002",)),
                           ("release", ("T002", "--reason", "orphan")),
                           ("fail", ("T002", "--evidence", str(evidence),
                                     "--digest", "x")),
                           ("drop", ("T002", "--decision", "D-042"))):
            r = run_mark(self.spec, verb, *args, tel=self.tel)
            self.assertEqual(r.returncode, 1, (verb, r.stdout, r.stderr))
            self.assertIn("refused", r.stdout + r.stderr, verb)
        self.assertEqual((self.spec / "task.md").read_bytes(), before)


class LandProofGateTests(unittest.TestCase):
    """land's two gates on a docset whose proofs are deterministic:
    a red TC refuses (entry still claimed), a task with no runnable
    proof refuses, and a green run lands."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="mark-land-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def land(self, spec: Path, task: str, *extra: str):
        make_wave(spec, task)
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        return run_mark(spec, "land", task, *extra, tel=self.tel)

    def test_red_proofs_refuse_and_the_fail_command_is_printed(self):
        spec = hand_fixture(self._tmp, "red", fail_tc=True)
        r = self.land(spec, "T001",
                      "--digest", "digest: task T001 · status implemented")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("FAIL", r.stdout)
        self.assertIn("fail", r.stdout)  # the exact next command
        self.assertIn("(in-progress)", entry_text(spec, "T001"))

    def test_green_proofs_land(self):
        spec = hand_fixture(self._tmp, "green")
        r = self.land(spec, "T001",
                      "--digest", "digest: task T001 · status implemented "
                      "· files 1 · commit-line x")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)
        block = entry_text(spec, "T001")
        self.assertIn("(implemented)", block.splitlines()[0])
        self.assertFalse(specstate.CLAIM_NOTE.search(block))
        events = [e for e in mark_events(self.tel)
                  if e["event"] == "task_land"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["task"], "T001")

    def test_a_task_with_no_runnable_proof_refuses(self):
        spec = hand_fixture(self._tmp, "noproof")
        # T001 lands green first, which makes T002 runnable; T002 then
        # loses its runnable proof (its TC degrades to a MANUAL
        # observation), so land has nothing to execute
        green = self.land(spec, "T001",
                          "--digest", "digest: task T001 · status "
                          "implemented")
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)
        test = spec / "test.md"
        write(test, test.read_text(encoding="utf-8").replace(
            "- **Pass condition**: `python3 -c 'print(\"HI!\")'`",
            "- **Pass condition**: observed by hand — no command"))
        r = self.land(spec, "T002",
                      "--digest", "digest: task T002 · status implemented")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("no auto proof ran", r.stderr)
        self.assertIn("(in-progress)", entry_text(spec, "T002"))

    def test_a_digest_file_lands_without_the_override(self):
        spec = hand_fixture(self._tmp, "file")
        make_wave(spec, "T001")
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        digests = spec / "digests" / "wave-4"
        digests.mkdir(parents=True)
        write(digests / "implementer-T001.md",
              TOOLS + "digest: task T001 · status implemented · files 2 · "
              "commit-line feat(x): T001 shout (FR-001) · deviation none · "
              "note none\n")
        r = run_mark(spec, "land", "T001", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("override", r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)

    def test_a_blocked_digest_file_refuses_toward_release(self):
        spec = hand_fixture(self._tmp, "blocked")
        make_wave(spec, "T001")
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        digests = spec / "digests" / "wave-4"
        digests.mkdir(parents=True)
        write(digests / "implementer-T001.md",
              TOOLS + "digest: task T001 · status blocked: no failure evidence · "
              "files 0 · commit-line none · deviation none · note none\n")
        r = run_mark(spec, "land", "T001",
                     "--digest", "digest: task T001 · status implemented",
                     tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("blocked digest", r.stderr)
        self.assertIn("release", r.stderr)
        self.assertIn("(in-progress)", entry_text(spec, "T001"))

    def test_a_typed_deviation_digest_names_its_route(self):
        # D-043: the deviation prefix routes mechanically — scope widens
        # Touches, spec-defect goes to /spec-design; an untyped value is
        # a malformed digest (D-054), never parsed by half
        def digest_file(spec, deviation):
            digests = spec / "digests" / "wave-4"
            digests.mkdir(parents=True, exist_ok=True)
            write(digests / "implementer-T001.md",
                  TOOLS + "digest: task T001 · status blocked: cannot finish · "
                  f"files 0 · commit-line none · deviation {deviation} · "
                  "note none\n")
        parsed = digests.parse(
            "developer", None,
            "digest: task T001 · status blocked: cannot finish · files 0 · "
            "commit-line none · deviation spec-defect: FR-003 contradicts "
            "tech-spec.md § Code state · note none")
        self.assertEqual(parsed["deviation_kind"], "spec-defect")
        untyped = ("digest: task T001 · status blocked · deviation needs a "
                   "ruling")
        self.assertIsNone(digests.parse("developer", None, untyped))
        self.assertEqual(digests.validate("developer", None, untyped), [
            "`status` expects `implemented`, `already-satisfied` or "
            "`blocked:<why>`, got `blocked`", "`files` missing"])
        for deviation, route in (
                ("scope: repo/calc.py needs repo/eval.py too",
                 "widen the entry's Touches"),
                ("spec-defect: FR-003 contradicts tech-spec.md § Code state",
                 "route to /spec-design")):
            with self.subTest(deviation=deviation):
                spec = hand_fixture(self._tmp, "typed-" + deviation[:5])
                make_wave(spec, "T001")
                run_mark(spec, "claim", "--wave",
                         str(spec / "spawns" / "wave-4"), tel=self.tel)
                digest_file(spec, deviation)
                r = run_mark(spec, "land", "T001", tel=self.tel)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("blocked digest", r.stderr)
                self.assertIn(route, r.stderr)

    def test_a_malformed_digest_file_refuses_and_no_override_talks_over_it(self):
        # a digest file is valid, malformed, or absent: one that exists
        # but fails the schema is refused by name and its problems —
        # never read as absent, never talked over by --digest (D-054)
        spec = hand_fixture(self._tmp, "malformed")
        make_wave(spec, "T001")
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        path = spec / "digests" / "wave-4" / "implementer-T001.md"
        path.parent.mkdir(parents=True)
        write(path, "digest: task T001 · status implemented · files 2 · "
              "note none\n")
        for extra in ((), ("--digest", "digest: task T001 · status implemented")):
            with self.subTest(override=bool(extra)):
                r = run_mark(spec, "land", "T001", *extra, tel=self.tel)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn(f"refused: malformed digest at {path} — "
                              "`commit-line` missing — fix and run again: "
                              "re-spawn the developer with the same payload "
                              "to rewrite its digest file", r.stderr)
                self.assertNotIn("override", r.stderr)
                self.assertIn("(in-progress)", entry_text(spec, "T001"))

        # an empty file and a wrong task are the same refusal
        write(path, "")
        r = run_mark(spec, "land", "T001", tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("malformed digest at", r.stderr)
        self.assertIn("no `digest:` line", r.stderr)
        write(path, "digest: task T002 · status implemented · files 1 · "
              "commit-line none · deviation none · note none\n")
        r = run_mark(spec, "land", "T001", tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("names task T002, not T001", r.stderr)
        self.assertNotIn("none on file", r.stderr)
        self.assertIn("(in-progress)", entry_text(spec, "T001"))

        # repaired, the same file lands with no override
        write(path, TOOLS + "digest: task T001 · status implemented · files 1 · "
              "commit-line feat(x): T001 shout (FR-001) · deviation "
              "none · note none\n")
        r = run_mark(spec, "land", "T001", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)

    def test_the_newest_digest_file_decides_even_when_malformed(self):
        # a fix-round file in a later wave is the current digest: an
        # earlier wave's green one never lands over it
        spec = hand_fixture(self._tmp, "newest")
        make_wave(spec, "T001")
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        earlier = spec / "digests" / "wave-4" / "implementer-T001.md"
        earlier.parent.mkdir(parents=True)
        write(earlier, "digest: task T001 · status implemented · files 1 · "
              "commit-line x · deviation none · note none\n")
        later = spec / "digests" / "wave-6" / "implementer-T001.md"
        later.parent.mkdir(parents=True)
        write(later, "digest: task T001 · status implemented · files 1\n")
        r = run_mark(spec, "land", "T001", tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(f"malformed digest at {later}", r.stderr)
        self.assertIn("(in-progress)", entry_text(spec, "T001"))

    def test_an_open_round_needs_a_resolution(self):
        spec = hand_fixture(self._tmp, "round")
        edit_tasks(spec, ("- [ ] T001 implement",
                          "- [ ] T001 (in-progress) (fix 1/5) implement"
                          f"\n  - fix 1 {EM} it failed"))
        make_wave(spec, "T001")
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        r = run_mark(spec, "land", "T001",
                     "--digest", "digest: task T001 · status implemented",
                     tel=self.tel)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        r = run_mark(spec, "land", "T001",
                     "--digest", "digest: task T001 · status implemented",
                     "--resolution", "guard the empty case",
                     tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        block = entry_text(spec, "T001")
        self.assertIn("(implemented)", block.splitlines()[0])
        self.assertIn("(fixed 1/5)", block.splitlines()[0])
        self.assertRegex(block, rf"- fixed 1 {EM} guard the empty case "
                         rf"{EM} audit\.py proofs --task T001 green")


class ClaimWaveTests(unittest.TestCase):
    """claim --wave's own contract: exactly the wave's files, the
    frontier re-run refusing a stale wave, and nothing written on a
    refusal."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="mark-wave-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = copy_fixture(self._tmp)
        set_status(self.spec, "approved")

    def test_claims_exactly_the_waves_files(self):
        make_wave(self.spec, "T001")
        r = run_mark(self.spec, "claim", "--wave",
                     str(self.spec / "spawns" / "wave-4"), tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("claimed 1: T001", r.stdout)
        self.assertIn("(in-progress)", entry_text(self.spec, "T001"))
        self.assertNotIn("(in-progress)", entry_text(self.spec, "T002"))

    def test_a_stale_wave_is_refused_whole(self):
        # T001 claimed by hand (no stamp — an older docset's shape), so
        # the wave holding T001 no longer matches the frontier
        edit_tasks(self.spec, (T1, T1.replace("[P]", "[P] (in-progress)")))
        before = (self.spec / "task.md").read_bytes()
        r = run_mark(self.spec, "claim", "--wave",
                     str(make_wave(self.spec, "T001", "T002")), tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("stale wave: T001", r.stdout)
        self.assertIn("nothing claimed", r.stdout)
        self.assertEqual((self.spec / "task.md").read_bytes(), before)

    def test_a_wave_naming_an_unknown_task_is_refused(self):
        r = run_mark(self.spec, "claim", "--wave",
                     str(make_wave(self.spec, "T009")), tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("no such entry", r.stdout)

    def test_a_wave_dir_without_payloads_is_usage(self):
        d = self.spec / "spawns" / "wave-empty"
        d.mkdir(parents=True)
        r = run_mark(self.spec, "claim", "--wave", str(d), tel=self.tel)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_a_fix_round_wave_claims_again(self):
        edit_tasks(self.spec, (T1, T1.replace("[P]", "[P] (fix 1/5)")
                               + f"\n  - fix 1 {EM} it failed"))
        r = run_mark(self.spec, "claim", "--wave",
                     str(make_wave(self.spec, "T001")), tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        first = entry_text(self.spec, "T001").splitlines()[0]
        self.assertIn("(fix 1/5)", first)
        self.assertIn("(in-progress)", first)


class LockTests(unittest.TestCase):
    """The shared lock: a held lock exits 5, a stale one is broken."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="mark-lock-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = copy_fixture(self._tmp)
        set_status(self.spec, "approved")

    def test_a_held_lock_exits_five(self):
        make_wave(self.spec, "T001")
        holder = (
            "import sys, time\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "import specstate\n"
            f"with specstate.task_lock({str(self.spec)!r}):\n"
            "    print('held', flush=True)\n"
            "    time.sleep(8)\n")
        hpath = self._tmp / "holder.py"
        write(hpath, holder)
        p = subprocess.Popen([sys.executable, str(hpath)],
                             stdout=subprocess.PIPE, text=True)
        self.addCleanup(p.wait)
        try:
            self.assertEqual(p.stdout.readline().strip(), "held")
            r = run_mark(self.spec, "claim", "--wave",
                         str(self.spec / "spawns" / "wave-4"), tel=self.tel)
            self.assertEqual(r.returncode, 5, r.stdout + r.stderr)
            self.assertIn("lock busy", r.stderr)
        finally:
            p.kill()

    def test_a_stale_lock_is_broken(self):
        make_wave(self.spec, "T001")
        lock = self.spec / ".task.lock"
        write(lock, "12345 2026-11-13T10:00:00")
        old = time.time() - 120
        os.utime(lock, (old, old))
        r = run_mark(self.spec, "claim", "--wave",
                     str(self.spec / "spawns" / "wave-4"), tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("stale task lock", r.stderr)
        self.assertFalse(lock.exists())


class TickStampTests(unittest.TestCase):
    """tick.py strips exactly the ticked entry's stamp — another claimed
    entry's stamp survives."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="mark-tick-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = copy_fixture(self._tmp)
        set_status(self.spec, "approved")

    def test_tick_strips_the_ticked_entrys_stamp_only(self):
        make_wave(self.spec, "T001")
        r = run_mark(self.spec, "claim", "--wave",
                     str(self.spec / "spawns" / "wave-4"), tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # T002 keeps a hand stamp of its own — it must survive T001's tick
        edit_tasks(self.spec, (T2F, T2F.replace("[P]", "[P] (in-progress)")
                               + f"\n  - claimed 2026-11-13T10:00:00Z "
                                 f"{EM} run r-hand"))
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "tick.py"), str(self.spec),
             "--note", "T001 :: pytest green"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t001 = entry_text(self.spec, "T001")
        self.assertIn("- [x]", t001.splitlines()[0])
        self.assertFalse(specstate.CLAIM_NOTE.search(t001))
        # the untouched claim keeps its stamp
        self.assertTrue(specstate.CLAIM_NOTE.search(entry_text(self.spec, "T002")))


class TinyTierTests(unittest.TestCase):
    """The tiny tier: a stamped claim keeps the frozen spec verifiable
    (the hard ordering rule behind freeze.py's claimed alternative), and
    drop refuses outright."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="mark-tiny-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = self._tmp / "specs" / "tiny"
        self.spec.mkdir(parents=True)
        write(self.spec / "spec.md", TINY_SPEC)
        _approval.approve(self.spec, self._tmp)

    def test_a_stamped_claim_keeps_the_freeze_verifiable(self):
        r = run_mark(self.spec, "claim", "--wave",
                     str(make_wave(self.spec, "T001", wave=2)), tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(specstate.CLAIM_NOTE.search(
            (self.spec / "spec.md").read_text(encoding="utf-8")))
        rc = subprocess.run(
            [sys.executable, str(SCRIPTS / "freeze.py"), str(self.spec),
             "--verify"], capture_output=True, text=True, timeout=120)
        self.assertEqual(rc.returncode, 0, rc.stdout + rc.stderr)

    def test_drop_refuses_outright_at_tiny_tier(self):
        r = run_mark(self.spec, "drop", "T001", "--decision", "D-001",
                     tel=self.tel)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Tier: tiny", r.stderr)


class SameSignatureTests(unittest.TestCase):
    """D-044: the failing command recurring across a task's fix rounds —
    the trailing run specstate.failure_signature_run counts, mark.py's
    advisory at 3, and the at-cap reason naming the repeated command."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="mark-sig-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def test_the_run_counts_trailing_identical_commands(self):
        sig = specstate.failure_signature_run
        self.assertEqual(sig(""), (None, 0))
        self.assertEqual(sig("# Notes: T001\n\n## Fix round 1\nno command\n"),
                         (None, 0))
        note = ("# Notes: T001\n\n"
                "## Fix round 1\n$ pytest -k mul\nE   AssertionError: 5\n"
                "## Fix round 2\n$ go test ./...\nFAIL: TestMul\n"
                "## Fix round 3\n$ go test ./...\nFAIL: TestMul\n")
        self.assertEqual(sig(note), ("$ go test ./...", 2))
        self.assertEqual(sig("## Fix round 1\n$ a\n## Fix round 2\n$ a\n"
                              "## Fix round 3\n$ a\n"), ("$ a", 3))
        # a round with no command breaks the run; the newest without one reads none
        self.assertEqual(sig("## Fix round 1\n$ a\n## Fix round 2\nno cmd\n"
                              "## Fix round 3\n$ a\n"), ("$ a", 1))
        self.assertEqual(sig("## Fix round 1\n$ a\n## Fix round 2\nno cmd\n"),
                         (None, 0))
        # a developer-appended section is not part of the round above it
        self.assertEqual(sig("## Fix round 1\n$ a\n## Fix round 2\nno cmd\n"
                              "## Developer notes\n$ a\n"), (None, 0))

    def _seed_two_rounds(self, spec, cmd):
        edit_tasks(spec, ("- [ ] T001 implement",
                          "- [ ] T001 (fix 2/5) implement"
                          f"\n  - fix 1 {EM} first\n  - fix 2 {EM} second"))
        notes = spec / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        write(notes / "T001.md",
              f"# Notes: T001\n\n## Fix round 1\n{cmd}\nE   one\n"
              f"## Fix round 2\n{cmd}\nE   two\n")

    def test_fail_advises_at_three_repeats_of_one_command(self):
        spec = hand_fixture(self._tmp, "sig3")
        self._seed_two_rounds(spec, "$ pytest -k mul")
        evidence = spec / "ev.txt"
        write(evidence, "$ pytest -k mul\nE   AssertionError: 5 again\n")
        r = run_mark(spec, "fail", "T001", "--evidence", str(evidence),
                     "--digest", "E   AssertionError: 5 again", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("same-signature: $ pytest -k mul has failed 3 "
                      "consecutive round(s)", r.stdout)
        self.assertIn("D-044", r.stdout)

    def test_fail_stays_quiet_when_the_command_varies(self):
        spec = hand_fixture(self._tmp, "sig0")
        self._seed_two_rounds(spec, "$ pytest -k mul")
        evidence = spec / "ev.txt"
        write(evidence, "$ go test ./...\nFAIL: TestMul\n")
        r = run_mark(spec, "fail", "T001", "--evidence", str(evidence),
                     "--digest", "FAIL: TestMul", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("same-signature", r.stdout)

    def test_the_at_cap_reason_names_a_repeated_signature(self):
        spec = hand_fixture(self._tmp, "sigcap")
        edit_tasks(spec, ("- [ ] T001 implement",
                          f"- [ ] T001 (fix 5/5) implement\n  - fix 5 {EM} "
                          "cap"))
        notes = spec / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        write(notes / "T001.md",
              "# Notes: T001\n\n"
              "## Fix round 3\n$ pytest -k mul\nE   c\n"
              "## Fix round 4\n$ pytest -k mul\nE   d\n"
              "## Fix round 5\n$ pytest -k mul\nE   e\n")
        import graph  # the replica closure shares the master's behavior
        per_task = graph.task_frontier(
            specstate.task_entries(
                (spec / "task.md").read_text(encoding="utf-8")),
            None, spec)
        cap = next(t for t in per_task if t["state"] == "at-fix-cap")
        self.assertIn("same failing command has failed 3 rounds "
                      "($ pytest -k mul)", cap["reason"])
        self.assertIn("/spec-design", cap["reason"])


GREEN_DIGEST = (TOOLS + "digest: task T001 · status implemented · files 2 · "
                "commit-line feat(x): T001 shout (FR-001) · deviation none · "
                "note none")
BROKEN_DIGEST = ("digest: task T001 · status implemented · files 2 · "
                 "note none\n")
TS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00"
LINE = ("provenance: run {run} · role implementer · lens {lens} · "
        "model {model} · harness {harness} · payload {payload} · "
        "input {input} · recorded {ts} · tools-reported " + REPORTED + "\n")
UNJOINED = dict(run="none", lens="none", model="none", payload="none",
                input="none", harness="unknown")
REQUEST = dict(run="r-ab12", lens="build", model="sonnet", harness="zcode",
               payload="3fa9c21d4e5b", input="9b8c7d6e5f4a")


def sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def digest_file(spec: Path, wave: int, text: str) -> Path:
    path = spec / "digests" / f"wave-{wave}" / "implementer-T001.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, text)
    return path


class RunLedgerTests(unittest.TestCase):
    """The run ledger (D-055): specs/<name>/runs/ledger.jsonl takes one
    row per orchestrator event — every verb, inside the lock hold that
    wrote the marker — and is never status. Before land and fail read a
    digest, the provenance sweep gives every valid digest file the one
    line a ledger row vouches for, built from the wave row that recorded
    the payload; a malformed file, or one whose line no row vouches for,
    is left as it is and recorded as `digest_malformed`."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="mark-ledger-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def claim(self, spec: Path, *tids: str, harness: str = "") -> Path:
        wave = make_wave(spec, *tids)
        extra = ("--harness", harness) if harness else ()
        r = run_mark(spec, "claim", "--wave", str(wave), "--run-id",
                     "r-ab12", *extra, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return wave

    def rows(self, spec: Path) -> list[dict]:
        return specstate.ledger_rows(spec)

    def test_claim_appends_one_row_per_task_with_the_requests_facts(self):
        spec = copy_fixture(self._tmp, "claim")
        set_status(spec, "approved")
        self.assertFalse((spec / "runs").exists())
        self.claim(spec, "T001", "T002", harness="claude-code")
        rows = self.rows(spec)
        self.assertEqual([row["event"] for row in rows], ["claim", "claim"])
        for row, tid in zip(rows, ("T001", "T002")):
            self.assertRegex(row["ts"], TS)
            self.assertEqual(facts(row), {
                "skill": "spec-build", "event": "claim", "run": "r-ab12",
                "wave": 4, "task": tid, "role": "implementer",
                "lens": "build", "stem": f"implementer-{tid}",
                "payload": sha12("payload\n"), "model": "sonnet",
                "harness": "claude-code"})
        self.assertEqual(list(rows[0]), [
            "ts", "skill", "event", "run", "wave", "task", "role", "lens",
            "stem", "payload", "model", "harness"])

        # ungiven, the harness is `unknown`; the flag is claim's alone
        spec = hand_fixture(self._tmp, "unknown")
        self.claim(spec, "T001")
        self.assertEqual(self.rows(spec)[0]["harness"], "unknown")
        r = run_mark(spec, "land", "T001", "--harness", "zcode",
                     tel=self.tel)
        self.assertEqual(r.returncode, 2)
        self.assertIn("--harness is claim's flag", r.stderr)

    def test_land_appends_its_row_beside_the_digest_row_the_sweep_wrote(self):
        # the sha is the digest's own, taken before the line was appended
        for body, hashed in ((GREEN_DIGEST, GREEN_DIGEST + "\n"),
                             (GREEN_DIGEST + "\n", GREEN_DIGEST + "\n")):
            with self.subTest(trailing_newline=body.endswith("\n")):
                spec = hand_fixture(self._tmp, f"land{len(body)}")
                self.claim(spec, "T001")
                path = digest_file(spec, 4, body)
                r = run_mark(spec, "land", "T001", tel=self.tel)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                rows = self.rows(spec)
                self.assertEqual([row["event"] for row in rows],
                                 ["claim", "digest", "land"])
                self.assertEqual(facts(rows[1]), {
                    "skill": "spec-build", "event": "digest", "wave": 4,
                    "task": "T001", "role": "implementer",
                    "stem": "implementer-T001", "harness": "unknown",
                    "digest": sha12(hashed), "outcome": "implemented",
                    "tools-reported": REPORTED})
                self.assertEqual(facts(rows[2]), {
                    "skill": "spec-build", "event": "land", "run": "r-ab12",
                    "wave": 4, "task": "T001", "role": "implementer",
                    "stem": "implementer-T001", "digest": sha12(hashed),
                    "outcome": "implemented"})
                self.assertEqual(path.read_text(encoding="utf-8"), (
                    hashed + LINE.format(ts=rows[1]["ts"], **UNJOINED)))

    def test_land_refuses_a_digest_whose_report_lacks_a_required_tool(self):
        # D-056: the file must report a file writer and Bash. Without
        # them it is a failed spawn — the task stays claimed, no round
        # opens, --digest does not talk over it, one content is recorded
        # once — and a report that covers them lands with no marker
        green = GREEN_DIGEST.split("\n", 1)[1]
        cases = (("tools: Read, Write\n", "Read, Write", "Bash"),
                 ("tools: Read, Bash\n", "Bash, Read", "Write or Edit"),
                 ("", None, "Write or Edit, Bash"))
        for n, (report, names, required) in enumerate(cases):
            for extra in ((), ("--digest",
                              "digest: task T001 · status implemented")):
                with self.subTest(report=report, override=bool(extra)):
                    spec = hand_fixture(self._tmp, f"handshake{n}{len(extra)}")
                    self.claim(spec, "T001")
                    path = digest_file(spec, 4, report + green)
                    refusal = (
                        "refused: capability handshake failed: developer "
                        f"reported tools `{names or 'none'}` — the developer "
                        f"role requires `{required}` — spawn again on a type "
                        f"or harness that holds `{required}`; a failed spawn, "
                        f"not a fix round — the digest file at {path} lands "
                        "nothing: `mark.py release` T001 --reason \"blocked: "
                        "capability handshake failed\", then re-emit and "
                        "spawn it again\n")
                    for _ in range(2):
                        r = run_mark(spec, "land", "T001", *extra, tel=self.tel)
                        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                        self.assertIn(refusal, r.stderr)
                    block = entry_text(spec, "T001")
                    self.assertIn("(in-progress)", block)
                    self.assertNotIn("(implemented)", block)
                    self.assertNotIn("(fix ", block)
                    rows = self.rows(spec)
                    self.assertEqual([row["event"] for row in rows],
                                     ["claim", "digest", "capability_missing"])
                    row = rows[-1]
                    wanted = {
                        "skill": "spec-build", "event": "capability_missing",
                        "run": "r-ab12", "wave": 4, "task": "T001",
                        "role": "implementer", "stem": "implementer-T001",
                        "digest": sha12(report + green + "\n"),
                        "outcome": required}
                    if names:
                        wanted["tools-reported"] = names
                    self.assertEqual(facts(row), wanted)
                    self.assertEqual(rows[1].get("tools-reported"), names)

        # a report that covers both requirements lands, whatever its case
        # and whichever writer it names — with no fix-round marker
        spec = hand_fixture(self._tmp, "handshake-green")
        self.claim(spec, "T001")
        digest_file(spec, 4, "tools: read, bash, edit, grep\n" + green)
        r = run_mark(spec, "land", "T001", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("landed T001 (implemented)", r.stdout)
        self.assertNotIn("(fix ", entry_text(spec, "T001"))
        self.assertEqual([row["event"] for row in self.rows(spec)],
                         ["claim", "digest", "land"])

    def test_the_line_is_built_from_the_wave_row_that_recorded_the_payload(
            self):
        spec = hand_fixture(self._tmp, "joined")
        specstate.ledger_event(spec, specstate.ledger_row(
            "spec-build", "wave", wave=4, node="execute", role="implementer",
            stem="implementer-T001", **REQUEST))
        self.claim(spec, "T001")
        path = digest_file(spec, 4, GREEN_DIGEST + "\n")
        r = run_mark(spec, "land", "T001", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = self.rows(spec)
        self.assertEqual([row["event"] for row in rows],
                         ["wave", "claim", "digest", "land"])
        self.assertEqual(facts(rows[2]), dict(
            REQUEST, skill="spec-build", event="digest", wave=4, task="T001",
            role="implementer", stem="implementer-T001",
            digest=sha12(GREEN_DIGEST + "\n"), outcome="implemented",
            **{"tools-reported": REPORTED}))
        self.assertEqual(path.read_text(encoding="utf-8"), (
            GREEN_DIGEST + "\n"
            + LINE.format(ts=rows[2]["ts"], **REQUEST)))

        # swept once: a later report appends neither a line nor a row
        run_graph(spec, tel=self.tel)
        self.assertEqual(path.read_text(encoding="utf-8").count("provenance:"),
                         1)
        self.assertEqual(len(self.rows(spec)), 4)

    def test_the_ledger_is_append_only_under_repeated_verbs(self):
        spec = hand_fixture(self._tmp, "repeat")
        so_far = b""
        for _ in range(2):
            self.claim(spec, "T001")
            r = run_mark(spec, "release", "T001", "--reason",
                         "orphan: dead session", tel=self.tel)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            raw = specstate.ledger_path(spec).read_bytes()
            self.assertTrue(raw.startswith(so_far), "an earlier row changed")
            so_far = raw
        rows = self.rows(spec)
        self.assertEqual([row["event"] for row in rows],
                         ["claim", "release", "claim", "release"])
        self.assertEqual(facts(rows[1]), {
            "skill": "spec-build", "event": "release", "run": "r-ab12",
            "task": "T001", "role": "implementer",
            "stem": "implementer-T001", "outcome": "orphan"})
        self.assertEqual(facts(rows[3]), facts(rows[1]))

    def test_fail_and_drop_append_their_rows(self):
        spec = copy_fixture(self._tmp, "verbs")
        set_status(spec, "approved")
        self.claim(spec, "T001")
        line = ("digest: task T001 · status blocked: pytest red · files 1 · "
                "commit-line none · deviation none · note none")
        evidence = self._tmp / "ev.txt"
        write(evidence, f"$ pytest\n{line}\n")
        r = run_mark(spec, "fail", "T001", "--evidence", str(evidence),
                     "--digest", line, tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = run_mark(spec, "drop", "T002", "--decision", "D-001",
                     tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = self.rows(spec)
        self.assertEqual([row["event"] for row in rows],
                         ["claim", "fail", "drop"])
        self.assertEqual(facts(rows[1]), {
            "skill": "spec-build", "event": "fail", "run": "r-ab12",
            "task": "T001", "role": "implementer",
            "stem": "implementer-T001", "outcome": "blocked"})
        self.assertEqual(facts(rows[2]), {
            "skill": "spec-build", "event": "drop", "task": "T002",
            "role": "implementer", "stem": "implementer-T002"})

    def test_a_malformed_digest_is_left_untouched_and_recorded_once(self):
        spec = hand_fixture(self._tmp, "malformed")
        self.claim(spec, "T001")
        path = digest_file(spec, 4, BROKEN_DIGEST)
        for _ in range(2):
            r = run_mark(spec, "land", "T001", tel=self.tel)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("refused: malformed digest at " + str(path),
                          r.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), BROKEN_DIGEST)
        # a refused verb is no event, and one content is recorded once
        rows = self.rows(spec)
        self.assertEqual([row["event"] for row in rows],
                         ["claim", "digest_malformed"])
        self.assertEqual(facts(rows[1]), {
            "skill": "spec-build", "event": "digest_malformed", "wave": 4,
            "task": "T001", "role": "implementer",
            "stem": "implementer-T001", "harness": "unknown",
            "digest": sha12(BROKEN_DIGEST), "outcome": "malformed"})

    def test_a_forged_provenance_line_is_treated_as_malformed(self):
        spec = hand_fixture(self._tmp, "forged")
        self.claim(spec, "T001")
        forged = (GREEN_DIGEST + "\n"
                  + LINE.format(run="r-ffff", lens="build", model="opus",
                                harness="claude-code", payload="3fa9c21d4e5b",
                                input="9b8c7d6e5f4a",
                                ts="2026-11-26T00:00:00.000000+00:00"))
        path = digest_file(spec, 4, forged)
        r = run_mark(spec, "land", "T001", tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(f"refused: malformed digest at {path} — its "
                      "`provenance:` line is not one the run ledger records "
                      "— the line is the orchestrator's to write — fix and "
                      "run again", r.stderr)
        self.assertEqual(path.read_text(encoding="utf-8"), forged)
        self.assertIn("(in-progress)", entry_text(spec, "T001"))
        rows = self.rows(spec)
        self.assertEqual([row["event"] for row in rows],
                         ["claim", "digest_malformed"])
        # the row's sha is the content without the provenance line —
        # the agent's own bytes, whoever wrote the line above them
        self.assertEqual((rows[1]["outcome"], rows[1]["digest"]),
                         ("unverified", sha12(GREEN_DIGEST + "\n")))
        # the resume view reads it as malformed, never as none
        state = json.loads(run_graph(spec, "--state-json", tel=self.tel).stdout)
        task = next(t for t in state["nodes"]["execute"]["tasks"]
                    if t["id"] == "T001")
        self.assertEqual(task["digest"], "malformed — fix and run again")

    def test_a_vouched_line_does_not_travel_to_another_file(self):
        # the line verifies against a row for ITS wave and stem: copied
        # whole to a later wave, it is no row's and the file is malformed
        spec = hand_fixture(self._tmp, "travel")
        self.claim(spec, "T001")
        swept = digest_file(spec, 4, GREEN_DIGEST + "\n")
        run_graph(spec, tel=self.tel)
        moved = digest_file(spec, 6, swept.read_text(encoding="utf-8"))
        seen = specstate.latest_digest(spec, "T001")
        self.assertEqual(seen["path"], str(moved))
        self.assertEqual(seen["state"], specstate.DIGEST_MALFORMED)
        r = run_graph(spec, tel=self.tel)
        self.assertIn(f"digest: malformed at {moved} — its `provenance:` "
                      "line is not one the run ledger records", r.stderr)
        self.assertEqual([row["event"] for row in self.rows(spec)],
                         ["claim", "digest", "digest_malformed"])
        self.assertEqual(self.rows(spec)[-1]["outcome"], "unverified")
        self.assertEqual(moved.read_text(encoding="utf-8"),
                         swept.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
