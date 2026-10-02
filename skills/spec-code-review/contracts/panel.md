# The panel contract (targets, gate, findings, report)

The canonical statement of what a spec-code-review run IS. SKILL.md
summarizes; this file arbitrates. The agent-facing subset (the flagging
bar every reviewer obeys) is canonical in `agents/_panel-protocol.md`;
this file is the orchestrator-facing complement.

## Targets

One `target` arg picks what the panel reviews. Three of the four are
the same thing — a diff against a resolved base — so one code path
serves them:

| Target | Base resolution | Notes |
|---|---|---|
| `diff` (default) | `base` arg, default `HEAD` | working tree, last commit, any ref |
| `branch` | merge-base with explicit `base`, else `origin/HEAD` → `main`/`master` (remote form first) | uncommitted work included, surfaced in the report |
| `pr` | merge-base with the PR's `baseRefOid` (GitHub's own PR-diff semantics) | `pr` arg: number, URL, `owner/repo#N`; head must be checked out — auto-checkout on a clean tree, refusal on a dirty one, unconditional (D-004) |
| `project` | no diff — the tracked source files, extension-filtered (lockfiles/generated/vendored excluded), largest first, capped at `PROJECT_MAX_FILES` (30) | leftover files named under `notCovered`; `paths` narrows |

Unknown target values fail with the valid set. `fix_from` overrides the
review stages entirely (D-005): findings carried from a previous
report, fix loop runs directly, `fix_rounds` defaults to 2.

## The mechanical gate (`scripts/gate.sh`)

Runs once before any reviewer (again after every fix round). stdout is
a JSON array, one row per detected check:

```json
{ "name": "<family label>", "exit_code": 0, "tail": "<last 8 lines>" }
```

Families: the repo's own checks (Makefile test/check/lint, npm
test/lint/typecheck, cargo test, go test, pytest/unittest — pytest
resolved PATH → repo venv → `uv run` → `python3 -m`), plus two
always-on git-gated families: `bash -n` on changed `*.sh` (every
tracked script in project mode) and the secret-shape scan over added
diff lines plus untracked files (diff mode only — D-007). A family is
skipped when its tool is absent; nothing is silently invented; an
empty detection is NOT a green light — the documented check command
(README/CI) runs instead.

Contract rules: a red gate ends a FRESH review — failing checks are
the findings, reviewers are never spent; a fix_from run deliberately
continues over a red pre-fix gate (clearing it is the fixer's job),
but the failing checks enter the tracked findings and every report
surface renders the authoritative last gate run, never a stale green.
Reviewers never re-run the suites.

## Preflight (the scout map)

After a green gate and before the first reviewer — never on a fix_from
run, whose review stages are skipped — one read-only scout explores
the codebase and the modules the target touches and returns:

- `modules` — `{name, path, role}`, the target's modules plus close
  neighbors (within two hops), at most 8;
- `conventions` — the repo patterns design fit is judged against
  (error-handling idiom, test layout, naming, module boundaries —
  AGENTS.md/CLAUDE.md folded in), at most 6;
- `riskAreas` — one-line paths deserving extra reviewer attention, at
  most 6.

Injection rules: the map rides the reviewer asks and the final
assessments as context — never as evidence, since a finding still
quotes the code; triage, confirmers and the fixer do not receive it,
so an independent confirmation inherits no scout claim. The scout
reports no findings — a suspicion travels only as a riskAreas line
with a path, and the reviewers must still find and evidence it. A
failed scout degrades to the raw target with a `notCovered` line; it
never stops the run. The step runs in fast mode too: one bounded turn
buys every reviewer the same starting ground.

## Findings

Every finding, in any representation (agent output, triage, report,
fix_from payload), carries:

- `id` — stable identity minted when the finding becomes tracked:
  `<lens>-<n>` at confirmation, `gate-N` / `fix-review-N` inside the
  loop, `carried-N` for an id-less fix_from item. Reviewers never mint
  ids — identity begins at tracking. `where` is evidence, not
  identity: lines move as fixes land, and two findings can share a
  location.
- `where` — `path:line` on the new side of the diff (current tree in
  project mode; a check name for gate-lens rows).
- `what` — one sentence: the problem and why it matters. Not the fix.
- `evidence` — the quoted lines or command output that demonstrate it.
- `severity` — `high` = data loss/crash/wrong result/security
  compromise; `medium` = a real defect the author should fix;
  `low` = minor.
- `impact` (optional) — one sentence: what the defect breaks and when
  it bites. Expected above the minor level.
- `lens` — correctness | security | quality | general | fix-review |
  gate.
- `status` — `verified` | `unconfirmed` (independent confirmation);
  after a fix round `fixStatus` — `fixed` | `unfixed` | `worse` |
  `pending`.

A finding that fails confirmation is labelled `unconfirmed`, never
dropped. Triage drops carry a one-line reason. Zero findings is the
expected answer for a clean target.

## Roles and independence (who may never be whom)

| Role | Edits files | Writes findings | Confirms | Fixes |
|---|---|---|---|---|
| Preflight scout | never | no — the map, never findings | no | no |
| Lens reviewer | never | yes (own lens) | no | no |
| Triage editor | never | drops/dedupes with reasons | no | no |
| Confirmer | never | no | yes (intent-blind) | no |
| Fixer | working tree only, never commits | no | no | yes |
| Fix verifier | never | fix verdicts only | no | no |
| Fresh-eyes fix reviewer | never | NEW defects only | no | no |

Confirmation is intent-blind on purpose: the confirmer verifies from
the code alone, with no access to the stated-intent channel.

## The report

Every run returns `{conclusion, findings[], verified[], notCovered[]}`
plus a markdown artifact. `notCovered` separates "found nothing" from
"looked nowhere" — caps left uncovered, undetected checks, test gaps,
residual risks all live there. In pr mode the header names the PR
(number, title, author, base, URL — markdown-escaped); "merge" reads
PR-ready (pr), branch-ready (branch), ready-as-is (project).
Recommendation semantics are canonical in `gates/recommendation.md`.

## Versioning

`VERSION`, SKILL.md frontmatter `version`, and the generated
`.claude-plugin/plugin.json` move together (sync.sh refuses drift);
CHANGELOG entries need their own `Migration:` paragraph. The two
workflow masters under `workflows/` are hand-maintained dialects of
this contract, pinned together by `tests/test_workflow_copies.py`
(D-006).
