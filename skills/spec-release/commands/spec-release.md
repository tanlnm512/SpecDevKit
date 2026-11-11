---
description: Cut a release from merged, delivered work - collect what landed since the last tag, propose the version bump, write the changelog and release notes from facts, gate, then commit+tag and publish only on the user's yes; never deploys
argument-hint: "[collect|notes|preflight|cut|verify|status] [version|tag]"
skills: spec-release
---

Run the spec-release skill (auto-mounted) for this request: $ARGUMENTS

Verb routing. `$1` is a verb when it is one of `collect`, `notes`,
`preflight`, `cut`, `verify`, `status`; a bare version (`1.4.0` or
`v1.4.0`) is the default run aimed at that version.

- *(no verb)* → run from the current state: `release.py status` names
  the next step, and the run continues from there through collect,
  version, notes, preflight, and cut — stopping at each decision the
  user owns (the version, the section, every red gate row, both
  yeses).
- `collect` → `release.py collect` and `release.py version`: what is
  releasable since the last tag and the proposed bump, with its
  reasons. Read-only.
- `notes [version]` → confirm the version, `bump --write`, `notes
  --write`, the release manager's tightening pass, `notes --check`.
  Writes only the changelog and the version files.
- `preflight [version]` → `release.py preflight`: every gate row
  (`gates/preflight.md`). Read-only.
- `cut [version]` → the cut plan, the user's yes, the local release
  commit, annotated tag, and `Released:` records; then the publish
  plan, a second yes, the pushes and the GitHub release
  (`gates/cut.md`). Never forced; never deployed.
- `verify [tag]` → the post-release checklist for the human to run,
  then the outcome recorded on each spec (asked first). A failure
  routes to `/spec-define <name>` with `**Type**: hotfix`.
- `status` → where the release stands and the next step. Read-only.

Merged work only: an open branch or pull request is `/spec-ship`'s,
an undelivered spec is `/spec-build`'s.
