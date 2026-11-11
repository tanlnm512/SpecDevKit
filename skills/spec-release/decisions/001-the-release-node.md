# D-001 — spec-release is the release node D-014 deferred

**Status**: accepted (2026-11-11)

## Context

spec-build's D-014 ends the flow at a verified commit: push, PR,
deploy, and publish stay human or CI actions, and "a `release` HUMAN
node (done-signal: a `Released:` marker)" is named as the shape any
future release step must take. Delivered specs piled up with nothing
that turned them into a version, a changelog, and a tag; the facts a
release needs (work type, docs impact, rollout, parked items) already
sat in each spec's records.

## Decision

- A separate skill, `spec-release`, owns the release phase. Its one
  command is `/spec-release`; its one role is `spec-release-manager`.
- It starts from merged, delivered work on the default or a release
  branch. The pull request and everything before the merge belong to
  `/spec-ship`; delivery belongs to `/spec-build`.
- Every step that leaves the machine or rewrites history is a human
  gate — the two yeses of `gates/cut.md`. The node's done-signal is
  the `Released:` record on each spec it carries (D-002).
- It never deploys and never integrates with monitoring. Post-release
  verification is a checklist a human runs; a failure re-enters the
  loop as a hotfix spec through `/spec-define`.
- It is not a node in graph.py: release spans many specs, while the
  graph schedules one spec's docset. The record is doc state any
  reader can see; the graph may learn it later.

## Consequences

The kit gains a sixth skill and a tail to its lifecycle. D-014's
argument still holds for deployment: what runs in production is
decided by CI, environments, and permissions this skill cannot see,
so it stops at the published tag.
