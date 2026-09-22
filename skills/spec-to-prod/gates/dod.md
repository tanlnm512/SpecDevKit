# Definition of Done (the gate between Status: active and Status: done)

Conjunctive, not a score: every gate is binary, evidence-backed, and
re-runnable. No partial credit, nothing averaged — a feature at 92% is
0% shippable. `scripts/audit.py dod <spec-dir>` measures the mechanical
gates and prints the scorecard; the closing audit owns the verdict.

| # | Gate | Metric | Pass condition | Evidence |
|---|------|--------|----------------|----------|
| 1 | Proof (auto) | Auto-TC pass rate | 100% | `audit.py proofs --run` |
| 2 | Proof (manual) | Observed TCs | every MANUAL TC recorded | observation note per TC |
| 3 | Regression | Repo suite | exit 0 | suite output |
| 4 | Completeness | Landed tasks | every task ticked/implemented/struck, 0 in-progress | check.py burndown arithmetic |
| 5 | Contract & evidence integrity | check.py | 0 FAIL; approval freeze valid; closing evidence present; every WARN fixed or ruled | check.py + `audit.py evidence` |
| 6 | Scope | Unexplained files | 0 unadjudicated UNMENTIONED | `audit.py scope` |
| 7 | Hygiene | Debris | 0 unadjudicated suspects | `audit.py clean` |
| 8 | Review | Contract + implementation diff | 0 BLOCK; WARN/NIT fixed or parked | reviewer digest(s) |
| 9 | Rulings | D-### surfaced | all in the closing report | the report itself |
| 10 | Sign-off | User ack | explicit yes on the report | conversation |

Gates 2, 3, 8, 9, 10 are judgment/human gates — the scorecard lists
them MANUAL; satisfying and recording them is the orchestrator's job.
Gate 8 has two halves. Contract review may be inline for a tiny, zero-unknown
change when the orchestrator records its findings. The implementation-diff
review is required at closing: tests alone do not certify security, rollback,
maintainability, or semantic conformance.

## Rules that keep the metrics honest

- Binary, artifact-backed, re-runnable — anything else ("feels
  complete", "agent said success", "tests were written") is vanity.
- Fresh evidence only: every green in the report cites the command, exit
  code, and key output from this session's run. "Should pass", "seems
  fixed", "I ran it earlier", "the agent said it's done" are not
  evidence — cached or prior-session output is rerun, or it doesn't
  count.
- The numerator's quality is gated above it: gate 8 (vacuous TCs,
  over-promised ACs, parity risk, implementation drift, unsafe change, and
  test deception) is what makes gate 1 mean something.
- Behavioral thresholds live in the spec — an FR's own number, measured
  by its TC's command. DoD only guarantees every number the spec set was
  measured and met; it sets no thresholds of its own.
- WARNs don't block; unowned WARNs do. Each is fixed or parked with a
  D-### ruling — explicit, signed-for debt, not swept.
- Bugfix specs add the revert-proof: revert the fix, watch the repro TC
  fail, restore, watch it pass — the strongest single evidence line.
- Two levels, deliberately: a task's tick is evidence collection,
  granted retroactively at the closing audit; the DoD applies to the
  whole plan, once.
