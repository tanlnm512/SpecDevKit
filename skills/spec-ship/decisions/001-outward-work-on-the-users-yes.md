# D-001 — Ship does the outward work, on the user's yes

**Status**: accepted (2026-11-11)

## Context

spec-build D-014 ends the flow at a verified commit: push, PR,
deploy, and publish "remain human/CI actions by design", because a
node whose done-signal is a marker string adds contract surface
without adding verification. That left the integration phase to the
user's own typing — the branch pushed by hand, a PR body retyped from
memory, CI and review comments handled outside the kit, and after a
squash-merge a delivery record pointing at a commit no longer on the
default branch.

The spec's docs already hold everything a PR must say: the
requirements, the proofs, the docs impact, the rollout and rollback,
the parked items.

## Decision

A separate skill, spec-ship, covers the span from the delivered
commit to the merged PR. It extends D-014 without reversing it:

- **The gates stay human.** Push, PR create or edit, a posted reply,
  and a re-requested review each wait for the user's explicit yes to
  a preview showing exactly what will leave. The yes covers what was
  shown and nothing else.
- **The work moves to the session.** On that yes the session runs the
  command. The user decides; they no longer type.
- **Four actions are out of reach whatever the answer**: a force-push,
  a merge (or auto-merge, or approval), a push to the default branch,
  and any outward action from a dirty tree.
- **The script only reads.** `ship.py` derives state and assembles
  facts; toward the remote it runs nothing and prints the command for
  each action. Its two writers touch only `specs/<name>/`.
- **No graph node.** spec-build's graph still ends at tick-commit and
  archive. Ship's stage is derived from git, the PR, and the docs on
  every call — D-014's objection to a marker-driven release node
  stands.
- **Deploy and publish stay outside.** The span ends at the merge and
  the re-pointed record; the release belongs to spec-release.

## Consequences

The delivery pass's closing message can name `/spec-ship` instead of
"push and PR are the user's". The outward-action gate is prose plus a
read-only script: nothing mechanical verifies the yes (open item 5).
PR text, comments, and CI logs enter the session as untrusted input,
so the inert-data rule is part of the protocol from the first
version.
