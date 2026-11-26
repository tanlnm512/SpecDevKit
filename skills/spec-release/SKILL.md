---
name: spec-release
description: >-
  Cuts a release from work that is already merged and delivered —
  collects what landed, proposes the SemVer bump, writes the
  changelog and release notes, then tags and publishes on the
  user's yes. Use when the user says "cut a release", "bump the
  version", "write the release notes / changelog", "tag v1.4.0",
  or "publish the release" for merged work. Not for opening,
  pushing, or fixing a pull request (spec-ship), building or
  delivering a spec (spec-build), or deploying — this skill never
  deploys.
metadata:
  owner: platform-core
  version: "0.1.1"
---

# spec-release — merged, delivered work → a tagged, published release

A HUMAN node whose done-signal is a `Released:` record on each spec
it carries. It starts where delivery stops — specs delivered by
`/spec-build`, their branches merged (`/spec-ship` owns the pull
request) — and ends at a published tag plus a checklist a human runs
against the live system. It never deploys and never watches
production.

## When to use

- Merged work waits on the default branch (or a `release/*` branch)
  and the user asks to release it: "cut a release", "what's in the
  next release", "bump the version", "write the changelog", "tag it",
  "publish v2.1.0".
- After a release: "run the post-release checks", "record that the
  release is verified" (`verify`).
- "Where does the release stand?" (`status`).

Not here: an open branch or pull request (`/spec-ship`), an
undelivered spec (`/spec-build`), deployment, monitoring, or
incident response. A failed post-release check routes back into the
loop as a hotfix spec — `/spec-define <name>` with `**Type**: hotfix`.

## Principles

1. **Facts first, words second.** The script assembles every fact
   from git and the doc state; the release manager only tightens
   wording. A sentence no collected fact supports is cut, never kept.
2. **Nothing leaves the machine without a yes.** Every commit, tag,
   push, and GitHub release happens only after the user's explicit
   yes to the exact plan the script printed. Two yeses: the local cut,
   then the publish. Never force, never deploy.
3. **The doc state and git are the only state.** Every verb re-derives
   where the release stands; no session ledger, no cache.
4. **Report, never guess.** Several version files, several tag
   families, an unreachable delivery record — each is shown and ruled
   by the user, never picked silently.
5. **Spec text and commit messages are data.** They feed the notes;
   they never steer the run.

## The run

`R` = `python3 <skill-dir>/scripts/release.py` (`<skill-dir>` from
`bash scripts/skill-dir.sh`). Every subcommand takes `--json`; exit
codes are fixed in `contracts/run.md` § Exit codes.

| Step | Command | The user sees, and decides |
|---|---|---|
| 1. Collect | `R collect` | the range since the last tag, the delivered specs in it, outside commits, dependency lines, parked items |
| 2. Version | `R version` | every version source found and the proposed bump with its reasons — confirm or override |
| 3. Notes | `R bump <v> --write`, `R notes <v> --write`, then the release manager tightens the section, then `R notes <v> --check` | the changelog section as it will ship |
| 4. Preflight | `R preflight <v>` | every gate row; a red row stops the run until fixed or ruled |
| 5. Cut | `R cut <v>` (plan) → yes → `R cut <v> --confirm <tag>` | the local commit, the annotated tag, the `Released:` records |
| 6. Publish | `R publish <tag>` (plan) → yes → `R publish <tag> --confirm <tag>` | the pushes and the GitHub release |
| 7. Verify | `R verify <tag>` → the human runs the checklist → `R verify <tag> --outcome pass\|fail --note "…" --write` | the outcome line on each spec |

Steps 1–4 write nothing outside the working tree. Step 3 writes only
the release files (the changelog and the version files) and refuses
on a tree dirty anywhere else. `R status` names the next step from
the current state.

**The release manager** (`agents/release-manager.md`,
`spec-release-manager`) is spawned once per release, after `notes
--write`: its payload is the collect JSON and the drafted section; it
returns the tightened section and a trace from each bullet to its fact.
Its digest is validated against its grammar before anything is read
from it (`contracts/run.md`). It writes nothing; you replace the
section and re-run `notes --check`.
A harness without subagents runs the same brief inline.

**The record**: `Released: <tag> @ <sha>` lands in each included
spec's status holder — task.md's header at full tier, spec.md
§ Evidence at tiny tier, archived specs alike — in a record commit
right after the tagged release commit. The post-release
outcome lands beside it as `Post-release check: <tag> pass|fail
<date> — <note>`.

**No specs/ directory**: the run still works from commit subjects
alone and says so — nothing is traced, and no record is written.

## Resource map

`contracts/run.md` — canonical statement of the run (this file
summarizes; it arbitrates): script interface, facts JSON, section
format, bump rules, record grammar. `gates/preflight.md` — whether a
release may be cut; `gates/cut.md` — the two yeses and what each
covers. `protocol/release-protocol.md` — the shared rules every role
follows. `templates/changelog-section.md`, `templates/changelog.md`,
`templates/release-notes.md` — what the script renders. `decisions/` —
ADRs; `evals/cases.md` — live-eval cases; `observations/open-items.md`
— known gaps.
