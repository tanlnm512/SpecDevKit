---
description: Portable three-stage gated code review - the repo's own checks as the mechanical gate, specialist lenses with independent confirmation, optional verified fix loop
argument-hint: <review|fix|gate|plan> [diff|branch|pr|project] [args…]
skills: spec-code-review
---

Run the spec-code-review skill (auto-mounted) for this request: $ARGUMENTS

Verb routing ($1 = verb; `review` is the default when $1 is a target or
the ask is plainly a review):

- `review [target] [args…]` → the full three-stage flow (gate → panel
  with triage and independent confirmation → synthesis). Targets:
  `diff` (default; `base` names the ref — HEAD, HEAD~1, any branch),
  `branch` (current branch vs its base; uncommitted work included and
  reported), `pr <number|url|owner/repo#N>` (gh CLI; auto-checkout of
  the PR head on a clean tree, refusal on a dirty one), `project
  [paths]` (the whole tracked codebase, capped at the largest 30
  files). Extra args: `intent` (what the change is supposed to do —
  the author's stated intent), `mode fast|full|auto`, `fix_rounds N`
  (N > 0 runs the verified fix loop after the review).
- `fix <findings-json>` → the fix-only continuation (`fix_from`):
  carry a previous report's findings (file path or inline JSON) into
  the fix loop — fixer, independent verification per fix, gate re-run,
  fresh-eyes review; `fix_rounds` defaults to 2. This is the second
  half of the review-then-ask flow: review first, present the
  findings, let the user decide, then fix from the report.
- `gate [--base <ref>|--tree]` → run `scripts/gate.sh` alone and show
  the JSON verdict per detected check (the same floor the panel uses).
- `plan` → `gate.sh --plan`: what the gate would run, nothing executed.

On a harness with a dynamic-workflow runtime, an ask that names the
workflow dispatches the installed `spec-code-review` workflow with the
same args; otherwise the stages run inline per SKILL.md. The gate is
always `scripts/gate.sh` — plain bash + python3, no other dependency.
Fixes are never committed by the panel; the commit is the user's.
