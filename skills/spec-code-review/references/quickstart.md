# Quickstart

This is navigation, not a second contract. `SKILL.md`,
`contracts/panel.md`, and the panel briefs remain canonical.

## Pick the target

| You want | Invoke |
|---|---|
| The working tree / last commit | `review` (default `target: diff`; `base: HEAD~1` for the last commit) |
| What's on this branch | `review target branch` (optional `base`) |
| A pull request | `review target pr, pr: 12` (gh CLI; clean tree auto-checkout, dirty tree refused) |
| The whole codebase | `review target project` (+ `paths: src` on big repos) |
| Fix what a review found | `fix <report.md or findings.json>` — the `fix_from` continuation |
| Just the mechanical floor | `gate` (or `gate --tree` for project scope) |

## Pick the harness

- **zcode / Claude Code**: ask for the workflow by name — "run the
  spec-code-review workflow, target pr, pr 12" — or the `/spec-code-review`
  router command. The workflow is the background, artifact-producing
  form; inline stages are identical in behavior.
- **Any other agent**: the skill inline; `scripts/gate.sh` is the only
  executable it needs (bash + python3).

## The review-then-ask flow (fixing is a decision, not a default)

1. Review with `fix_rounds: 0` (the default) — you get findings,
   severity, impact, risk and a verdict; a recommendation only comes
   with the fix loop (`gates/recommendation.md` arbitrates).
2. Present them; the user decides.
3. If fixing: `fix <report.md or findings JSON>` (+ `fix_rounds`,
   default 2) — the carried findings go straight to the verified fix
   loop; nothing is re-reviewed.
4. Fixes land uncommitted; the commit is the user's.

## Reading a report

Findings first (`path:line`, evidence, severity, verified/unconfirmed,
impact), then test gaps and residual risks — then `notCovered`, which
separates "found nothing" from "looked nowhere". Read it before
trusting a clean report.
