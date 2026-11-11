# Preflight gate: what may ship

The canonical criteria for whether a spec's branch may leave the
workspace. SKILL.md summarizes; this file arbitrates. Every criterion
is mechanical — `scripts/ship.py preflight <spec>` decides it,
read-only, and an onlooker can re-run it.

```sh
python3 <skill_dir>/scripts/ship.py preflight <spec> [--base <branch>] [--remote <name>]
```

Exit 0 = may ship. Exit 4 = refused: every failing row is printed,
the first as the one-line reason. The gate runs before every push
and before a PR is created — not once per session; a pass does not
outlive the next commit.

## Rows

| Row | Passes when | Refusal routes to |
|---|---|---|
| `delivered` | the spec exists; its status holder carries `Delivered: commit @ <sha>`; spec.md reads `Status: done`; the sha resolves and is an ancestor of HEAD | no spec → "ship is spec-bound — use your normal PR flow"; not delivered → `/spec-build ship <name>`; sha off this branch → the delivering branch, or spec-build's `tick.py --redeliver` after a rewrite; `commit @ -` (a non-git delivery) → nothing to ship |
| `tree` | `git status --porcelain` is empty | commit or stash — the user's |
| `remote` | a git remote exists (`--remote`, else the branch's configured remote, else `origin`, else the only one) | `git remote add` — the user's |
| `default-branch` | the default branch resolves (`--base`, else `<remote>/HEAD`, else `main` or `master` on the remote, else locally) | pass `--base` |
| `branch` | HEAD is on a branch, that branch is not the default branch, and it equals spec.md's `**Branch**:` when the header is set (an unfilled `<type>/<name>` placeholder reads unset) | check out the spec's branch; on the default branch, move the delivery to a branch first; a wrong header is corrected through `/spec-design` |
| `commits` | the branch has commits beyond the default branch | nothing to ship |
| `sync` | the remote-tracking branch has no commits this branch lacks | integrate them — the user's; never a force-push |
| `gh` | the `gh` CLI is on PATH | not a refusal — `degraded`: the push proceeds, and the gate prints the manual commands for opening the PR |

## Stop conditions

| Condition | Result |
|---|---|
| Any `refuse` row | exit 4; the run reports the reason and stops — nothing leaves the workspace |
| `gh` missing | degraded pass: after the push (on yes), give the user the printed `manual` commands; `checks`, `comments`, and the after-merge read need `gh` and refuse without it |
| Not a git repository | refused — a non-git delivery has no commit to ship |
| Remote-tracking refs stale | the gate reads them "as of the last fetch" and says so; a push the remote rejects is reported, never retried with force |

The gate decides only whether shipping may start. What leaves, and
on whose word, is `gates/outward-actions.md`.
