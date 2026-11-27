"""Run budgets for unattended spans — spec-build D-059.

A headless `graph.py --run` and `mark.py claim` count two budgets from
the spec's run ledger — implementer spawns, over the run and again
over the spec's whole ledger, and wall-clock minutes over the run
alone — and a spent one parks
`AWAITING HUMAN: run budget — <what> used <n> of <n>`:

  - the run stops at the wave boundary and claims nothing further: the
    next task is never claimed and its wave never emitted, the
    `run_end` row says `run_budget`, and the stop says why it matters
    and the two ways on;
  - the per-spec spawn budget outlives a new run id, 0 lifts a budget,
    and a spec resumed days after its first claim is held to its spawn
    count under a new run id, never to minutes;
  - a budget the run raised rides the claim command;
  - `mark.py claim` by hand refuses with the same line, exit 1, and
    writes nothing — no marker, no registry change, no ledger row, no
    telemetry event;
  - the minutes run from the first claim to the kit's clock
    (`specstate.utc_now`), which one test moves — nothing sleeps;
  - the budget is a ceiling: a wave whose claims would take a spawn
    budget past its limit is refused whole — exit 1, the lines naming
    the wave's need, what remains and the shortfall — and the run parks
    before that wave with the same lines, never emitting or claiming
    it; a wave that fits to the last spawn is claimed whole;
  - a budget refusal that still meets the claim inside a headless wave
    is the budget stop, exit 0, never a runner failure;
  - the flags are claim's and --run's alone, and refuse a negative
    number.

Fixtures are one hand-authored docset in a scratch git repository —
T001, then T002 after it — landed by the worktree tests' headless
developer in the shared tree.
"""

import contextlib
import datetime
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from test_claim_registry import (  # noqa: E402
    DIGEST,
    MARK,
    record_approval,
    run,
    wave,
)
from test_execute_gates import (  # noqa: E402
    run_graph,
    telemetry_events,
    write,
)
from test_worktrees import RUNNER, scratch_repo  # noqa: E402
import graph  # noqa: E402
import mark  # noqa: E402
import specstate  # noqa: E402

T0 = datetime.datetime(2026, 1, 1, 10, 0, tzinfo=datetime.timezone.utc)
MINUTE = datetime.timedelta(minutes=1)
RUN_LINE = "AWAITING HUMAN: run budget — spawns in this run used 1 of 1"
SPEC_LINE = "AWAITING HUMAN: run budget — spawns in this spec used 1 of 1"
WAVE_LINE = ("AWAITING HUMAN: run budget — spawns in this run would use "
             "4 of 2")
NEED_LINE = "   this wave needs 4 spawns of the 2 remaining: 2 short"


def four_tasks(task_md: str) -> str:
    """The scratch repo's two-task holder as four runnable tasks on four
    disjoint files: one wave, four spawns."""
    return task_md.replace("| 1     | 2     | 0    |          |",
                           "| 1     | 4     | 0    |          |") \
        .replace("| **Σ** | 2     | 0    |          |",
                 "| **Σ** | 4     | 0    |          |") \
        .replace(
            "- [ ] T002 (after T001) pin punctuation behavior with a test (FR-002)",
            "- [ ] T002 pin punctuation behavior with a test (FR-002)\n"
            "  - Touches:\n    - `src/other.py`\n"
            "- [ ] T003 document the shout helper (FR-001)\n"
            "  - Touches:\n    - `docs/shout.md`\n"
            "- [ ] T004 guard the shout helper (FR-002)\n"
            "  - Touches:\n    - `src/guard.py`")


def seed(spec_dir: Path, *rows: dict,
         at: datetime.datetime | None = None) -> Path:
    """Claim rows appended to the spec's run ledger, stamped `at` or
    now."""
    path = spec_dir / "runs" / "ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = (at or datetime.datetime.now(datetime.timezone.utc)).isoformat()
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({"ts": stamp, "skill": "spec-build",
                                 "event": "claim", "role": "implementer",
                                 **row}) + "\n")
    return path


class RunBudgetTests(unittest.TestCase):

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="run-budget-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = scratch_repo(self._tmp)
        self.runner = write(self._tmp / "runner.py", RUNNER)
        self.ledger = self.spec / "runs" / "ledger.jsonl"
        self.registry = self.spec.parent / ".claims" / "registry.json"

    def run_loop(self, run_id: str,
                 *budgets: str) -> subprocess.CompletedProcess:
        return run_graph(self.spec, "--span", "execute", "--run",
                         "--run-id", run_id, "--runner",
                         f"{sys.executable} {self.runner} {{prompt_file}}",
                         *budgets, tel=self.tel)

    def tasks(self) -> str:
        return (self.spec / "task.md").read_text(encoding="utf-8")

    def rows(self) -> list[dict]:
        if not self.ledger.is_file():
            return []
        return [json.loads(line) for line in self.ledger.read_text(
            encoding="utf-8").splitlines()]

    def claims(self) -> list[dict]:
        return [row for row in self.rows() if row["event"] == "claim"]

    def payloads(self) -> list[str]:
        return sorted(p.name for p in
                      (self.spec / "spawns").rglob("implementer-T*.md"))

    def test_a_small_budget_parks_the_run_at_the_wave_boundary(self):
        r = self.run_loop("r-aaaa", "--budget-spawns", "1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("claimed 1: T001", r.stdout)
        self.assertIn(RUN_LINE, r.stdout)
        self.assertIn("   also spent: spawns in this spec used 1 of 1",
                      r.stdout)
        self.assertIn("why it matters (medium)", r.stdout)
        self.assertIn("ways on: raise a budget with --budget-spawns N / "
                      "--budget-minutes N", r.stdout)
        self.assertNotIn("AWAITING HUMAN: tick-commit", r.stdout)
        self.assertEqual(self.tasks().count("(implemented)"), 1)
        self.assertNotIn("(in-progress)", self.tasks())
        self.assertEqual([row["task"] for row in self.claims()], ["T001"])
        self.assertEqual(self.payloads(), ["implementer-T001.md"])
        end = self.rows()[-1]
        self.assertEqual((end["event"], end["outcome"], end["run"]),
                         ("run_end", "run_budget", "r-aaaa"))

    def test_the_spec_budget_outlives_a_new_run_id_and_a_hand_claim_refuses(
            self):
        self.assertEqual(self.run_loop("r-aaaa", "--budget-spawns", "1")
                         .returncode, 0)

        again = self.run_loop("r-bbbb", "--budget-spawns", "1")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn(SPEC_LINE, again.stdout)
        self.assertNotIn("in this run used", again.stdout)
        self.assertNotIn("claimed ", again.stdout)
        self.assertEqual(self.payloads(), ["implementer-T001.md"])

        # by hand: the emit shows the wave, the claim refuses on the
        # same line and leaves everything as it was
        r = run_graph(self.spec, "--emit-spawns", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        payload = next((self.spec / "spawns").rglob("implementer-T002.md"))
        before_rows = self.rows()
        before_registry = self.registry.read_bytes()

        def task_claims() -> list[dict]:
            return [e for e in telemetry_events(self.tel)
                    if e["event"] == "task_claim"]

        before_events = task_claims()
        r = run(MARK, "claim", self.spec, "--wave", payload.parent,
                "--run-id", "r-cccc", "--budget-spawns", "1", tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual([ln for ln in r.stdout.splitlines()
                          if ln.startswith("AWAITING HUMAN: run budget")],
                         [SPEC_LINE])
        self.assertIn("refused: the run budget is spent (nothing claimed)",
                      r.stdout)
        self.assertNotIn("(in-progress)", self.tasks())
        self.assertEqual(self.rows(), before_rows)
        self.assertEqual(self.registry.read_bytes(), before_registry)
        self.assertEqual(task_claims(), before_events)

    def test_zero_lifts_the_budgets(self):
        self.assertEqual(self.run_loop("r-aaaa", "--budget-spawns", "1")
                         .returncode, 0)
        r = self.run_loop("r-bbbb", "--budget-spawns", "0",
                          "--budget-minutes", "0")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        self.assertNotIn("run budget", r.stdout)
        self.assertEqual(self.tasks().count("(implemented)"), 2)
        self.assertEqual([row["task"] for row in self.claims()],
                         ["T001", "T002"])

    def test_a_spec_resumed_days_later_is_held_to_its_spawns_never_minutes(
            self):
        now = datetime.datetime.now(datetime.timezone.utc)
        seed(self.spec, {"run": "r-old", "task": "T001"},
             at=now - datetime.timedelta(days=3))
        r = run(MARK, "claim", self.spec, "--wave", wave(self.spec, "T001"),
                "--run-id", "r-new", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("claimed 1: T001", r.stdout)
        self.assertNotIn("run budget", r.stdout)

        later = scratch_repo(self._tmp / "later")
        seed(later, {"run": "r-old", "task": "T001"},
             at=now - datetime.timedelta(days=3))
        r = run(MARK, "claim", later, "--wave", wave(later, "T001"),
                "--run-id", "r-new", "--budget-spawns", "1", tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual([ln for ln in r.stdout.splitlines()
                          if ln.startswith("AWAITING HUMAN: run budget")],
                         [SPEC_LINE])
        self.assertNotIn("also spent", r.stdout)
        self.assertNotIn("(in-progress)", (later / "task.md").read_text(
            encoding="utf-8"))

    def test_the_runs_budget_rides_the_claim_command(self):
        # 31 claims already on the run: past the default, inside the
        # budget the second run raises
        seed(self.spec, *({"run": "r-aaaa", "task": f"T{i:03}"}
                          for i in range(31)))
        r = self.run_loop("r-aaaa")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AWAITING HUMAN: run budget — spawns in this run "
                      "used 31 of 30", r.stdout)
        self.assertIn("   also spent: spawns in this spec used 31 of 30",
                      r.stdout)
        self.assertEqual(len(self.claims()), 31)

        r = self.run_loop("r-aaaa", "--budget-spawns", "40")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("claimed 1: T001", r.stdout)
        self.assertIn("claimed 1: T002", r.stdout)
        self.assertIn("AWAITING HUMAN: tick-commit", r.stdout)
        self.assertNotIn("run budget", r.stdout)
        self.assertEqual(len(self.claims()), 33)

    def test_the_minutes_run_from_the_first_claim_to_the_kit_clock(self):
        clock = {"now": T0}
        said = io.StringIO()
        with unittest.mock.patch.object(specstate, "utc_now",
                                        lambda: clock["now"]), \
                unittest.mock.patch.dict(os.environ,
                                         {"KIT_TELEMETRY": "off"}), \
                contextlib.redirect_stdout(said):
            def claim() -> int:
                return mark.claim(self.spec, wave(self.spec, "T001"),
                                  "r-aaaa", budget_minutes=120)

            self.assertEqual(claim(), 0)
            clock["now"] = T0 + 119 * MINUTE
            self.assertEqual(
                mark.release(self.spec, "T001", "orphan: the test"), 0)
            self.assertEqual(claim(), 0)
            self.assertEqual(
                mark.release(self.spec, "T001", "orphan: the test"), 0)
            clock["now"] = T0 + 121 * MINUTE
            self.assertEqual(claim(), 1)
        out = said.getvalue()
        self.assertEqual(out.count("AWAITING HUMAN: run budget"), 1)
        self.assertIn("AWAITING HUMAN: run budget — minutes in this run "
                      "used 121 of 120", out)
        self.assertNotIn("(in-progress)", self.tasks())
        self.assertEqual(len(self.claims()), 2)
        self.assertEqual([row["ts"] for row in self.claims()],
                         [T0.isoformat(), (T0 + 119 * MINUTE).isoformat()])

    def wide(self) -> None:
        """The spec's tasks as four runnable ones on disjoint files,
        approved afresh so the execute span opens."""
        holder = self.spec / "task.md"
        write(holder, four_tasks(holder.read_text(encoding="utf-8")))
        record_approval(self.spec)

    def test_a_wave_past_the_budget_is_refused_whole(self):
        self.wide()
        before = self.registry.read_bytes() if self.registry.exists() else None
        r = run(MARK, "claim", self.spec, "--wave",
                wave(self.spec, "T001", "T002", "T003", "T004"),
                "--run-id", "r-aaaa", "--budget-spawns", "2", tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual([ln for ln in r.stdout.splitlines()
                          if ln.startswith("AWAITING HUMAN: run budget")],
                         [WAVE_LINE])
        self.assertIn("   also over: spawns in this spec would use 4 of 2",
                      r.stdout)
        self.assertIn(NEED_LINE, r.stdout)
        self.assertIn("ways on: raise a budget", r.stdout)
        self.assertIn("refused: the wave would spend past the run budget "
                      "(nothing claimed)", r.stdout)
        self.assertNotIn("(in-progress)", self.tasks())
        self.assertEqual(self.claims(), [])
        self.assertEqual(
            self.registry.read_bytes() if self.registry.exists() else None,
            before)

        # a wave that fits — to the last spawn — is claimed whole
        r = run(MARK, "claim", self.spec, "--wave",
                wave(self.spec, "T001", "T002", "T003", "T004"),
                "--run-id", "r-aaaa", "--budget-spawns", "4", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("claimed 4: T001, T002, T003, T004", r.stdout)
        self.assertNotIn("run budget", r.stdout)
        self.assertEqual([row["task"] for row in self.claims()],
                         ["T001", "T002", "T003", "T004"])

    def test_the_run_stops_before_a_wave_past_the_budget(self):
        self.wide()
        r = self.run_loop("r-aaaa", "--budget-spawns", "2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(WAVE_LINE, r.stdout)
        self.assertIn(NEED_LINE, r.stdout)
        self.assertEqual(self.payloads(), [])
        self.assertEqual(self.claims(), [])
        self.assertEqual([row["event"] for row in self.rows()],
                         ["run_start", "run_end"])
        self.assertEqual(self.rows()[-1]["outcome"], "run_budget")

    def test_a_budget_refusal_inside_a_headless_wave_is_the_budget_stop(
            self):
        # the loop counts before the wave; a budget crossed while the
        # wave was written still meets the claim's refusal, which the
        # loop reports as the budget stop — never as a runner failure
        self.assertEqual(self.run_loop("r-aaaa", "--budget-spawns", "1")
                         .returncode, 0)
        ran = self._tmp / "runner-ran"
        runner = write(self._tmp / "runner.py",
                       f"from pathlib import Path\nPath({str(ran)!r})"
                       ".write_text('ran')\n")
        r = run_graph(self.spec, "--emit-spawns", tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        payload = next((self.spec / "spawns").rglob("implementer-T002.md"))

        said, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(said), \
                contextlib.redirect_stderr(errors):
            rc, reason = graph._headless_execute_wave(
                self.spec, [graph.WrittenPayload(payload, "implementer",
                                                 "execute", "sonnet")],
                f"{sys.executable} {runner}", 1, "r-aaaa",
                budget_spawns=1)
        self.assertEqual((rc, reason), (0, "run_budget"), said.getvalue())
        self.assertIn(RUN_LINE, said.getvalue())
        self.assertNotIn("claim was refused", said.getvalue())
        self.assertFalse(ran.exists())
        self.assertNotIn("(in-progress)", self.tasks())
        self.assertEqual(len(self.claims()), 1)

    def test_the_flags_are_claims_alone_and_take_no_negative_number(self):
        r = run(MARK, "land", self.spec, "T001", "--digest", DIGEST,
                "--budget-spawns", "3", tel=self.tel)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("--budget-spawns/--budget-minutes are claim's flags",
                      r.stderr)

        r = run(MARK, "claim", self.spec, "--wave", wave(self.spec, "T001"),
                "--budget-spawns", "-1", tel=self.tel)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("--budget-spawns needs a whole number >= 0",
                      r.stderr)
        self.assertNotIn("(in-progress)", self.tasks())

        for flag in ("--budget-spawns", "--budget-minutes"):
            r = run_graph(self.spec, "--run", flag, "-1", tel=self.tel)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("--budget-spawns/--budget-minutes must be >= 0",
                          r.stderr)

        r = run_graph(self.spec, "--emit-spawns", "--budget-minutes", "5",
                      tel=self.tel)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("--budget-spawns/--budget-minutes require --run",
                      r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
