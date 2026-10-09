# Bugfix variant (deltas only)

Same graph, same waves, same IDs and rules. Only these parts change —
everything else runs as the feature flow.

## spec.md (orchestrator, with user) — § What becomes the bug narrative

```markdown
## What
**Current behavior**: <what actually happens — observed, with repro>
**Expected behavior**: <what should happen>
**Unchanged behavior**:            <!-- the regression guard -->
- **FR-0##**: The system shall still <existing behavior the fix must not alter>
```

Expected-behavior requirements are FR-### like any feature. The
unchanged-behavior clauses carry FR-### too so each traces to a regression
test case — a fix that breaks them must fail a named test, not a hunch.

The repro must be **red-capable**: one command that asserts the user's
exact symptom, goes red on this bug, and will go green on the fix — not
"runs without erroring". Deterministic where possible; a flaky bug gets
its reproduction rate raised (loop the trigger, narrow the timing window)
until the red is reliable enough to schedule around. **Minimise before
authoring**: shrink the repro to the smallest scenario that still goes
red — cut inputs, callers, config, and steps one at a time, keeping only
what is load-bearing — so the spec's cause analysis starts from the
smallest hypothesis space. No red-capable repro, no bugfix spec: a bug
that cannot be made red cannot be proven fixed.

## researcher — usually gated off

A bugfix's cause and fix are almost always already known while the spec is
still being authored — there's rarely a real open technical question to
research. Apply SKILL.md's researcher gate as written: if nothing is
genuinely uncertain, resolve the gate as skip — write the canonical skip
marker into research.md (its canonical home is `contracts/docset.md`) so
every frontier computation reads the gate as deliberately resolved, and the
analysis wave becomes a solo surveyor. Don't manufacture "research
questions" about a fix that's already obvious just to justify the wave
shape.

## surveyor — one extra item shape

Survey the bug itself: location (file:symbol, verbatim), suspected cause
evidence, existing regression coverage (there usually is none — that is the
finding). Same evidence/status/verify/gap shape; status of "bug exists" is
proven by the repro command failing — run it and paste the red output.

## tech agent — insert § Root-cause analysis before § Solution

Symptom · Location (survey evidence, verbatim) · Cause · Fix approach (why
minimal) · Regression risk (naming the unchanged-behavior FRs at risk).

The Cause is stated as **ranked falsifiable causes**: 2–4 candidates,
each with the prediction that would confirm or kill it ("if X is the
cause, then <probe> shows Y") — never a single plausible story, which
anchors on the first idea. The confirmed cause carries its proof (the
probe output or the red repro narrowing to it); the Fix approach
addresses the confirmed cause only. If the regression test cannot be
written at a seam where the real bug pattern occurs as it does at the
call site, say so in Regression risk — **no correct seam is itself a
finding** (the architecture prevents locking this bug down; a shallower
test elsewhere would be false confidence), and it belongs in the
survey gap or this section, never papered over.

## planner — plan.md's first phase is always the regression

Repro test exists and FAILS red is the first phase's checkpoint; the fix
task is done only when that test flips green.

## qa — one TC per unchanged-behavior FR

The repro itself is TC-001. Boundary cases around the bug condition. Plus,
per unchanged-behavior FR: "Given <the old flow>, When <exercised after the
fix>, Then <still works as before>."
