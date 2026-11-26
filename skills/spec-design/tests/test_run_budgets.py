"""Run budgets for unattended spans — spec-design D-080.

`graph.py --run` counts two budgets before every wave that would
claim — implementer spawns, over the run and again over the spec's
whole run ledger, and wall-clock minutes over the run alone — and a
spent one parks `AWAITING HUMAN: run budget — <what> used <n> of <n>`
before the wave: nothing is emitted, nothing claimed, the `run_end`
row says `run_budget`, and the stop says why it matters and the two
ways on.

  - both budgets are read from the ledger's `claim` rows: the run's
    are those carrying its run id, the spec's are every one, so the
    per-spec spawn budget outlives a new run id;
  - the minutes are one run's, from its first claim row to the kit's
    clock (`specstate.utc_now`), which these tests move — nothing
    sleeps — so a spec resumed hours after its first claim is never
    stopped on minutes under a new run id;
  - 0 lifts a budget, a wave that claims nothing is never stopped, and
    the flags need --run and refuse a negative number.

This package ships no mark.py, so the loop runs here on the print
runner with the developer brief stood in; spec-build's byte-identical
copy runs the real thing in spec-build's tests. The counting itself
lives in specstate and is pinned there with `now` given.
"""

import datetime
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
from test_graph import (  # noqa: E402
    approved_fixture,
    grounding_fixture,
)
from test_worktrees import in_process  # noqa: E402
import graph as engine  # noqa: E402 - the master, by name
import specstate  # noqa: E402

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
T0 = datetime.datetime(2026, 1, 1, 10, 0, tzinfo=datetime.timezone.utc)
HOUR = datetime.timedelta(hours=1)
MINUTE = datetime.timedelta(minutes=1)
CLAIM = {"skill": "spec-build", "event": "claim", "role": "implementer"}


def seed(spec_dir: Path, *rows: dict,
         at: datetime.datetime = T0) -> Path:
    """Claim rows appended to the spec's run ledger, each stamped
    `at`; a row may carry its own `ts` to stand in for a damaged one."""
    path = spec_dir / "runs" / "ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({"ts": at.isoformat(), **CLAIM, **row})
                     + "\n")
    return path


def payloads(spec_dir: Path) -> list[Path]:
    return sorted((spec_dir / "spawns").rglob("implementer-T*.md"))


def budget_line(out: str) -> str:
    """The stop's first line in a run's output, or '' when it never
    stopped on a budget."""
    return next((ln for ln in out.splitlines()
                 if ln.startswith("AWAITING HUMAN: run budget")), "")


class BudgetSpentTests(unittest.TestCase):
    """The count on its own: every ledger row is given, so is `now`."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="budget-count-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.spec = self._tmp / "specs" / "alpha"
        self.spec.mkdir(parents=True)

    def test_the_documented_defaults(self):
        self.assertEqual(specstate.BUDGET_SPAWNS, 30)
        self.assertEqual(specstate.BUDGET_MINUTES, 120)

    def test_no_ledger_has_spent_nothing(self):
        self.assertEqual(specstate.budget_spent(self.spec, "r-aaaa", T0), {
            "run": {"spawns": 0, "minutes": 0},
            "spec": {"spawns": 0}})

    def test_only_claim_rows_count_and_the_run_is_its_run_id(self):
        seed(self.spec,
             {"event": "run_start", "run": "r-aaaa"},
             {"event": "wave", "run": "r-aaaa", "payloads": 2},
             {"run": "r-aaaa", "task": "T001"},
             {"run": "r-old", "task": "T001"},
             {"event": "land", "run": "r-aaaa", "task": "T001"},
             {"run": "r-aaaa", "task": "T002"},
             {"run": "r-old", "task": "T002"})
        self.assertEqual(specstate.budget_spent(
            self.spec, "r-aaaa", T0 + 30 * MINUTE), {
            "run": {"spawns": 2, "minutes": 30},
            "spec": {"spawns": 4}})

    def test_the_minutes_are_the_runs_alone_since_its_first_claim(self):
        seed(self.spec, {"run": "r-old", "task": "T001"}, at=T0 - 5 * HOUR)
        seed(self.spec, {"run": "r-aaaa", "task": "T001"}, at=T0 - HOUR)
        seed(self.spec, {"run": "r-aaaa", "task": "T002"})
        self.assertEqual(specstate.budget_spent(self.spec, "r-aaaa", T0), {
            "run": {"spawns": 2, "minutes": 60},
            "spec": {"spawns": 3}})
        self.assertEqual(specstate.budget_spent(self.spec, "r-new", T0), {
            "run": {"spawns": 0, "minutes": 0},
            "spec": {"spawns": 3}})

    def test_without_a_run_id_the_run_has_spent_nothing(self):
        seed(self.spec, {"run": "r-aaaa", "task": "T001"})
        self.assertEqual(specstate.budget_spent(self.spec, None, T0), {
            "run": {"spawns": 0, "minutes": 0},
            "spec": {"spawns": 1}})

    def test_a_stamp_that_tells_no_time_is_still_a_spawn(self):
        seed(self.spec, {"run": "r-aaaa", "task": "T001", "ts": "yesterday"},
             {"run": "r-aaaa", "task": "T002", "ts": None},
             {"run": "r-aaaa", "task": "T003", "ts": None})
        seed(self.spec, {"run": "r-aaaa", "task": "T004"})
        self.assertEqual(specstate.budget_spent(
            self.spec, "r-aaaa", T0 + 20 * MINUTE), {
            "run": {"spawns": 4, "minutes": 20},
            "spec": {"spawns": 4}})

    def test_a_naive_stamp_reads_as_utc_and_a_late_clock_as_no_minutes(self):
        seed(self.spec, {"run": "r-old", "task": "T001",
                         "ts": "2026-01-01T09:00:00Z"},
             {"run": "r-aaaa", "task": "T001",
              "ts": "2026-01-01T09:30:00"})
        self.assertEqual(specstate.budget_spent(
            self.spec, "r-aaaa", T0 + 45 * MINUTE), {
            "run": {"spawns": 1, "minutes": 75},
            "spec": {"spawns": 2}})
        seed(self.spec, {"run": "r-late", "task": "T001"}, at=T0 + HOUR)
        late = specstate.budget_spent(self.spec, "r-late", T0)
        self.assertEqual(late["run"], {"spawns": 1, "minutes": 0})

    def test_the_default_clock_is_the_kit_clock(self):
        seed(self.spec, {"run": "r-aaaa", "task": "T001"})
        with unittest.mock.patch.object(specstate, "utc_now",
                                        lambda: T0 + 7 * MINUTE):
            spent = specstate.budget_spent(self.spec, "r-aaaa")
        self.assertEqual(spent["run"], {"spawns": 1, "minutes": 7})

    def test_every_row_is_stamped_by_the_kit_clock(self):
        with unittest.mock.patch.object(specstate, "utc_now",
                                        lambda: T0 + MINUTE):
            row = specstate.ledger_row("spec-build", "claim", run="r-aaaa")
        self.assertEqual(row["ts"], (T0 + MINUTE).isoformat())


class BudgetStopTests(unittest.TestCase):
    """The stop's lines: which budget it names first, and what it
    says after the counts."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="budget-stop-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.spec = self._tmp / "specs" / "alpha"
        self.spec.mkdir(parents=True)

    def stop(self, spawns: int, minutes: int,
             now: datetime.datetime = T0) -> list[str]:
        return specstate.budget_stop(self.spec, "r-aaaa", spawns, minutes,
                                     now)

    def test_nothing_is_printed_while_every_budget_holds(self):
        seed(self.spec, *({"run": "r-aaaa", "task": f"T{i:03}"}
                          for i in range(30)), at=T0 - 2 * HOUR)
        self.assertEqual(self.stop(31, 121), [])

    def test_the_first_line_names_the_first_budget_spent(self):
        seed(self.spec, *({"run": "r-aaaa", "task": f"T{i:03}"}
                          for i in range(30)), at=T0 - 2 * HOUR)
        lines = self.stop(30, 120)
        self.assertEqual(lines[0], "AWAITING HUMAN: run budget — spawns "
                                   "in this run used 30 of 30")
        self.assertEqual(lines[1:3], [
            "   also spent: minutes in this run used 120 of 120",
            "   also spent: spawns in this spec used 30 of 30"])
        self.assertEqual(len(lines), 11)

    def test_the_spec_is_named_when_only_its_spawns_are_spent(self):
        seed(self.spec, {"run": "r-old", "task": "T001"}, at=T0 - 3 * HOUR)
        self.assertEqual(self.stop(30, 120), [])
        lines = self.stop(1, 120)
        self.assertEqual(lines[0], "AWAITING HUMAN: run budget — spawns "
                                   "in this spec used 1 of 1")
        self.assertEqual(sum(ln.startswith("   also spent:") for ln in lines),
                         0)

    def test_the_stop_says_why_and_the_two_ways_on(self):
        seed(self.spec, {"run": "r-aaaa", "task": "T001"})
        lines = self.stop(1, 120)
        self.assertEqual(lines, [
            "AWAITING HUMAN: run budget — spawns in this run used 1 of 1",
            "   also spent: spawns in this spec used 1 of 1",
            "   why it matters (medium): the budget is the ceiling an "
            "unattended",
            "   run may spend — past it every spawn may be a task failing "
            "again,",
            "   costing time and tokens the kit cannot count; a spec with "
            "more",
            "   tasks than the budget needs a higher one",
            "   ways on: raise a budget with --budget-spawns N / "
            "--budget-minutes N",
            "   on the next run or claim (0 lifts it), or adjudicate the "
            "tasks",
            "   that keep failing (mark.py fail with the evidence, "
            "release, or",
            "   drop with a D-###) before running again"])
        for ln in lines:
            self.assertLessEqual(len(ln), 72, ln)


class RunBudgetLoopTests(unittest.TestCase):

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="run-budget-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        tel = Path(tempfile.mkdtemp(prefix="run-budget-tel-"))
        self.addCleanup(shutil.rmtree, tel, ignore_errors=True)
        self.tel = tel
        self.spec = approved_fixture(self._tmp, "alpha")
        self.ledger = self.spec / "runs" / "ledger.jsonl"

    def loop(self, run_id: str = "r-aaaa", spawns: int = 30,
             minutes: int = 120, now: datetime.datetime = T0,
             span: str = "execute") -> tuple[int, str]:
        """One `--run` on the print runner, the developer brief stood in
        and the kit's clock at `now`: its exit code and its output."""
        with unittest.mock.patch.object(specstate, "utc_now", lambda: now):
            return in_process(
                lambda: engine.run_loop(self.spec, None, engine.PRINT_RUNNER,
                                        False, None, span=span,
                                        run_id=run_id,
                                        budget_spawns=spawns,
                                        budget_minutes=minutes), self.tel)

    def rows(self) -> list[dict]:
        return [json.loads(line) for line in
                self.ledger.read_text(encoding="utf-8").splitlines()]

    def test_a_spent_budget_parks_the_run_before_the_wave(self):
        seed(self.spec, {"run": "r-aaaa", "task": "T001"})
        rc, out = self.loop(spawns=1)
        self.assertEqual(rc, 0, out)
        self.assertIn("AWAITING HUMAN: run budget — spawns in this run "
                      "used 1 of 1", out)
        self.assertIn("   also spent: spawns in this spec used 1 of 1", out)
        self.assertIn("ways on: raise a budget", out)
        self.assertEqual(payloads(self.spec), [])
        end = self.rows()[-1]
        self.assertEqual((end["event"], end["outcome"], end["run"]),
                         ("run_end", "run_budget", "r-aaaa"))
        self.assertEqual([row["event"] for row in self.rows()],
                         ["claim", "run_start", "run_end"])
        self.assertNotIn("outcome", self.rows()[-2])

    def test_a_budget_that_holds_emits_the_wave(self):
        seed(self.spec, {"run": "r-aaaa", "task": "T001"})
        rc, out = self.loop(spawns=2)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("run budget", out)
        self.assertEqual([p.name for p in payloads(self.spec)],
                         ["implementer-T001.md"])
        self.assertEqual(self.rows()[-1]["outcome"], "wave_emitted")

    def test_the_spec_budget_outlives_a_new_run_id(self):
        seed(self.spec, {"run": "r-old", "task": "T001"})
        rc, out = self.loop(run_id="r-new", spawns=1)
        self.assertEqual(rc, 0, out)
        self.assertEqual(budget_line(out), "AWAITING HUMAN: run budget — "
                                            "spawns in this spec used 1 of 1")
        self.assertNotIn("in this run used", out)
        self.assertEqual(payloads(self.spec), [])
        self.assertEqual(self.rows()[-1]["outcome"], "run_budget")

    def test_the_minutes_run_from_the_first_claim_to_the_kit_clock(self):
        seed(self.spec, {"run": "r-aaaa", "task": "T001"})
        rc, out = self.loop(now=T0 + 119 * MINUTE)
        self.assertNotIn("run budget", out, out)
        self.assertEqual(len(payloads(self.spec)), 1)

        rc, out = self.loop(now=T0 + 120 * MINUTE)
        self.assertEqual(rc, 0, out)
        self.assertEqual(budget_line(out), "AWAITING HUMAN: run budget — "
                                            "minutes in this run used 120 "
                                            "of 120")
        self.assertEqual(self.rows()[-1]["outcome"], "run_budget")

    def test_a_resumed_spec_is_held_to_its_spawns_never_minutes(self):
        seed(self.spec, {"run": "r-old", "task": "T001"}, at=T0 - 5 * HOUR)
        rc, out = self.loop(run_id="r-new", now=T0)
        self.assertEqual(rc, 0, out)
        self.assertEqual(budget_line(out), "")
        self.assertEqual(len(payloads(self.spec)), 1)

        rc, out = self.loop(run_id="r-new", spawns=1, now=T0)
        self.assertEqual(budget_line(out), "AWAITING HUMAN: run budget — "
                                            "spawns in this spec used 1 of 1")
        self.assertEqual(self.rows()[-1]["outcome"], "run_budget")

    def test_zero_lifts_only_the_budget_it_is_given_on(self):
        seed(self.spec, *({"run": "r-aaaa", "task": f"T{i:03}"}
                          for i in range(40)))
        rc, out = self.loop(spawns=0, minutes=0, now=T0 + 9 * HOUR)
        self.assertNotIn("run budget", out, out)
        self.assertEqual(len(payloads(self.spec)), 1)

        rc, out = self.loop(spawns=0, minutes=120, now=T0 + 9 * HOUR)
        self.assertEqual(budget_line(out), "AWAITING HUMAN: run budget — "
                                            "minutes in this run used 540 "
                                            "of 120")

    def test_a_wave_that_claims_nothing_is_never_stopped(self):
        self.spec = grounding_fixture(self._tmp / "bare", "demo")
        self.ledger = self.spec / "runs" / "ledger.jsonl"
        seed(self.spec, *({"run": "r-aaaa", "task": f"T{i:03}"}
                          for i in range(40)))
        rc, out = self.loop(spawns=1, minutes=1, span="shape")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("run budget", out, out)
        self.assertEqual(
            sorted(p.name for p in (self.spec / "spawns" / "wave-1")
                   .glob("*.md")), ["qa.md", "tech.md"])


class RunBudgetCliTests(unittest.TestCase):

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="run-budget-cli-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"
        self.spec = approved_fixture(self._tmp, "alpha")

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.tel),
                   KIT_TELEMETRY="on")
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "graph.py"), str(self.spec),
             *args], capture_output=True, text=True, timeout=300, env=env)

    def test_the_flags_reach_the_loop(self):
        now = specstate.utc_now()
        seed(self.spec, {"run": "r-aaaa", "task": "T001"}, at=now)
        r = self.run_cli("--run", "--span", "execute", "--run-id", "r-aaaa",
                         "--budget-spawns", "1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AWAITING HUMAN: run budget — spawns in this run "
                      "used 1 of 1", r.stdout)
        self.assertEqual(payloads(self.spec), [])

    def test_a_negative_budget_is_a_usage_error(self):
        for flag in ("--budget-spawns", "--budget-minutes"):
            r = self.run_cli("--run", flag, "-1")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("--budget-spawns/--budget-minutes must be >= 0",
                          r.stderr)

    def test_the_flags_need_a_run(self):
        seed(self.spec, *({"run": "r-aaaa", "task": f"T{i:03}"}
                          for i in range(40)))
        r = self.run_cli("--emit-spawns", "--span", "execute",
                         "--budget-spawns", "1", "--budget-minutes", "1")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("--budget-spawns/--budget-minutes require --run",
                      r.stderr)
        r = self.run_cli("--budget-spawns", "5")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("require --run", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
