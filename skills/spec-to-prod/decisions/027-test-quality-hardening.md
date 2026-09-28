# D-027: Test-quality hardening — mutation testing, coverage floor, property TCs, qa independence at every tier

Four upgrades to what "the suite is green" proves, one theme: the
pipeline's evidence was honest about requirements (traceability,
freshness) but said nothing about the tests themselves — a vacuous or
gappy suite passed every proof gate just as cleanly as a rigorous one.

**Decision**: (1) **Mutation testing** — `audit.py mutate <spec-dir>`
(D-027's centerpiece): a stdlib-only AST engine flips comparison /
boolean / arithmetic operators and bumps small-int constants, ONE mutant
at a time, in every changed non-test `.py` file vs the approval-freeze
base, re-running the auto TC commands from test.md after each. KILLED =
some test distinguishes the mutant; SURVIVED = a test gap for the
orchestrator to adjudicate. Mutants are written in place and
byte-verified-restored; timeouts count as killed; `--max-mutants`
(default 40) and a 10-minute wall budget bound the run. No dependency:
the engine is ~100 lines of `ast`, honoring constitution C-06 — mutmut
& co. stay out of the tree. (2) **Coverage floor** —
`audit.py coverage <spec-dir>` runs the repo suite once under the
repo's OWN pytest-cov (detected at runtime, optional instrument, never
installed by us; absent → explicit SKIPPED) and checks every task.md
`Touches:` path against spec.md's `**Coverage**: <int>` floor (default
80, `--threshold` overrides per run); a red suite or an unmeasured
touched file fails the mode. (3) **Property-based TCs** — the qa brief
now prefers ONE bounded property TC (hypothesis et al., only when the
repo already ships the library) over fixed examples where the contract
is a property (thresholds, round-trips, monotonicity, no-collision);
still inside the parser-exact `**Pass condition**:` command shape and
the 120 s cap; adding a dependency for testability stays a tech-spec
D-### decision, never qa's call. (4) **qa independence at every tier**
— amends D-024: at `Effort: standard` the merged designer now carries
plan/tech/tasks (three briefs) and qa runs as its own
implementation-blind spawn in the same wave; test.md always comes from
qa alone. The old tier's recorded trade-off (test.md sharing its author
with plan/tech) is retired — a standard-tier design stretch is two
spawns (designer ∥ qa) instead of one, still half of large's four.

**Consequences**: a green suite now carries three kinds of evidence
about itself — mutants killed, coverage floor met, properties searched —
on top of traceability and freshness; delivery-pass step 9 gains the
mutation instrument and step 8 the coverage floor (dod.md's rules carry
both). Cost: mutate re-runs the suite per mutant (bounded; opt-in per
delivery, not per task); coverage needs the repo's own pytest-cov;
standard-tier authoring costs one extra spawn. What is deliberately NOT
done: no mutation score gate (survivors are adjudicated, never
auto-failed — a mutation gate would force weak "kill-all" tests), and no
new dependencies anywhere.
