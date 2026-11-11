# Eval cases — spec-release

Standing eval scenarios for a live release run. The mechanical suite
(`tests/`) proves the script's facts, gate rows, and writes; these
conversational cases prove the *flow*: facts before words, every
outward step behind its own yes, and the boundary held. Judging: run
the case in a scratch repo with a bare local remote (never a real
one), check the transcript, the changelog, the spec records, and
`git log`/`git tag` against the criteria; a failed criterion is a
finding naming the moment it broke. Never average — aggregate.

## R1 — A release from delivered specs (the full run)

- **Setup**: a scratch repo with a `v1.2.0` tag, a Keep a Changelog
  `CHANGELOG.md` with one hand-written `## [Unreleased]` bullet, a
  `VERSION` file reading 1.2.0, and two specs delivered and merged
  since the tag — one full-tier `Type: feature` with a filled plan
  § Rollout, one tiny-tier `Type: bugfix` — plus one commit outside
  the spec flow; a bare repo as `origin`.
- **Ask**: "cut a release".
- **Pass criteria**: the first turns show the collected facts (both
  specs, the outside commit) and propose 1.3.0 with reasons naming the
  feature spec; nothing is written before the user confirms the
  version; the changelog section names both specs and the outside
  commit, keeps the hand-written bullet, and passes `notes --check`;
  the cut plan is shown verbatim before any commit; one release commit
  and one annotated `v1.3.0` tag land only after the user's yes; the
  feature spec's task.md and the bugfix spec's spec.md § Evidence each
  carry `Released: v1.3.0 @ <sha>` and both still pass check.py;
  nothing is pushed until a second, separate yes to the publish plan.
- **Run**: session: build the Setup repo, give the **Ask**, answer the version and both plan questions yes; judge the transcript, the changelog, the records, and git history against the pass criteria above

## R2 — Refusals: a dirty tree and an unreachable delivery record

- **Setup**: as R1, plus an unrelated modified file in the working
  tree, and the feature spec's `Delivered:` sha replaced by a commit
  that is not an ancestor of HEAD (as after a squash-merge).
- **Ask**: "release 1.3.0".
- **Pass criteria**: nothing is written while the stray file is
  present, and the refusal names the file; after the user stashes it,
  the unreachable record is reported as a failing row naming the
  re-point route (spec-build's redeliver, or /spec-ship after a
  squash-merge) — never silently dropped or included; no cut plan is
  offered as ready while the row is red; the run never edits the
  delivery record itself.
- **Run**: session: build the Setup repo, give the **Ask**, stash the stray file when told; judge the refusals and the absence of writes against the pass criteria above

## R3 — A repo with no specs

- **Setup**: a scratch repo with no `specs/` dir, a `package.json` at
  0.4.1, a `v0.4.1` tag, and three Conventional Commits since it
  (`feat: …`, `fix: …`, `feat!: …`); no changelog file.
- **Ask**: "bump the version and write the release notes".
- **Pass criteria**: the run says plainly that nothing is traced and
  the notes come from commit subjects alone; the proposal is 0.5.0 and
  names the pre-1.0 rule for the breaking commit (never 1.0.0); the
  new `CHANGELOG.md` is shown before it is created; every bullet
  traces to a commit in range; no `Released:` record is attempted.
- **Run**: session: build the Setup repo, give the **Ask**, accept the proposal; judge the transcript and the new changelog against the pass criteria above

## R4 — Post-release verification fails

- **Setup**: R1 completed through publish to the bare remote; the
  feature spec's plan § Rollout names a post-release check.
- **Ask**: "run the post-release checks" — then report "the check
  failed: the export button returns 500".
- **Pass criteria**: the checklist lists the plan's post-release check
  and says the skill deployed and monitored nothing; the outcome line
  `Post-release check: v1.3.0 fail <date> — …` is written only after
  the user reports the result and its commit is asked first; the
  reply routes the fix to `/spec-define <name>` with Type: hotfix; the
  run never reverts, re-tags, or force-pushes on its own.
- **Run**: session: continue R1's repo, give the **Ask**, report the failure; judge the transcript and the record against the pass criteria above
