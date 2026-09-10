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
proven by the repro command failing.

## tech agent — insert § Root-cause analysis before § Solution

Symptom · Location (survey evidence, verbatim) · Cause · Fix approach (why
minimal) · Regression risk (naming the unchanged-behavior FRs at risk).

## planner — plan.md's first phase is always the regression

Repro test exists and FAILS red is the first phase's checkpoint; the fix
task is done only when that test flips green.

## qa — one TC per unchanged-behavior FR

The repro itself is TC-001. Boundary cases around the bug condition. Plus,
per unchanged-behavior FR: "Given <the old flow>, When <exercised after the
fix>, Then <still works as before>."
