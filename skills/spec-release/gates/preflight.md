# Preflight gate: may this version be cut?

The canonical criteria for `release.py preflight <version>`. SKILL.md
summarizes; this file arbitrates. Every row prints `PASS`, `FAIL`,
`WARN`, or `SKIP` with a one-line reason; any `FAIL` exits 1 and
blocks `cut`, which re-runs this gate itself before writing anything.

## Rows

| Row | PASS when | FAIL when | Otherwise |
|---|---|---|---|
| tree | nothing is changed or untracked outside the release files (the changelog and the kept version files) | anything else is | — |
| branch | HEAD is the default branch (the remote's `HEAD`, else `main`/`master`/`trunk`), a `release/*` or `releases/*` branch, or the `--branch` named | detached HEAD, or any other branch | — |
| upstream | HEAD is level with its upstream as of the last fetch | HEAD is behind it | WARN: ahead (CI has not seen those commits) or no upstream |
| ci | `gh run list --commit HEAD` shows every run completed and green | a run failed, or is still running | SKIP: gh not installed; WARN: gh cannot read CI, or no runs exist — confirm by hand |
| tag | the tag is free | the tag exists | — |
| version | every kept version source reads the version | one does not — run `bump` | WARN: no version source (the tag alone carries it) |
| changelog | `notes --check` passes on the version's section | no section, a missing spec, a stray spec or commit, a placeholder | — |
| specs | no delivery record in range is unreachable | a record names a commit HEAD cannot reach — re-point it first | WARN per in-flight spec with commits in range |
| rollback | each included spec whose plan § Rollout is filled states a rollback path: a `Rollback trigger`, a filled tech-spec rollback cell, or a delivery-note `Rollback:` line | a filled Rollout with none of the three | no row for a tiny spec or `none — <reason>` |
| backlog | each must-fix parked line of an included spec appears under `### Known issues` (its first 40 item characters verbatim) | one does not — it needs a ruling | no row for ordinary parked lines |

A parked line is must-fix when it says must-fix, BLOCK, blocker,
security, critical, or high.

## Rulings

A red row is never waved through. Each has exactly two exits:

- **Fix it** and re-run: commit or stash stray changes, switch
  branch, pull, wait for CI, `bump`, edit the section, re-point a
  delivery record (spec-build's `tick.py --redeliver`), add the
  rollback line to the spec's delivery note.
- **Rule it** in the doc state, where the gate can see it: a must-fix
  item ships as a known issue (it stays in the section, in the
  user's words around the verbatim item text), or the user resolves
  it and removes it from `specs/BACKLOG.md`.

WARN and SKIP rows are shown to the user with the cut plan; the
user's yes to the plan covers them. CI marked SKIP or WARN means the
user confirms CI by hand before saying yes.
