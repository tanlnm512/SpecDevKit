# D-004 — The suite pins the run contract

**Status**: accepted (2026-11-12)

## Context

spec-ship shipped with `tests/run.sh` admitting it proved nothing — the
TODO branch printed "nothing was run, nothing is proven" and exited 0.
Meanwhile `contracts/run.md` makes claims that are purely behavioral:
the stage table (`status`), the refusal rows (`preflight`), the write
surface of `record` and `evidence`, and the headline guarantee —
toward the remote the script only reads, and every outward command
appears as preview text, never executed. None of that was mechanically
checked; a refactor of `scripts/ship.py` could have drifted any of it
silently.

## Decision

`tests/test_ship.py` pins the run contract at the script's command
line, in the suite idiom the sibling skills already use (real temp git
repos, a bare local-disk remote, `gh` absent except where a stub serves
canned per-subcommand output):

- the refusal rows and their exact blocking reasons;
- the full stage table, both the local-only stages and the PR lifecycle
  read through stubs (open, ci-red, ci-pending, closed, merged intact,
  merged-record-stale with the rebase twin, awaiting-merge);
- the record shapes (beside `**Delivered**` in the same bold form at
  full tier, inside tiny § Evidence, idempotent, url replaced in place);
- the evidence shapes (fix-round routing, the fix-cap warning, the
  unrouted `ship.md` note, the untrusted banner, the growing fence);
- the outward guarantee itself: `preflight`'s push appears only as
  preview text and the bare remote's refs never move; the reflog never
  grows across a battery of read commands.

The gh stub is chosen per subcommand (`<a>_<b>.json` for
`gh <a> <b> …`, `.err` for stderr + exit 1), so one stub serves the
view/checks/graphql/log sequence. Fixtures commit the delivery and the
docs that record it as separate commits, so a delivered sha exists that
is an ancestor of HEAD; the squash-rewrite fixture deliberately changes
the tree, because a same-second commit with the same parent, tree, and
message would be byte-identical to the delivery commit and the twin
detection would never see a rewrite.

## Consequences

`run.sh`'s TODO branch goes dormant (it stays as the honest fallback
should the tests ever be removed). Contract changes now fail the suite
instead of drifting quietly — updating `ship.py` without updating
`contracts/run.md` and this suite together is visible in the ordinary
gate run. The suite is dev-only (never installed), so it adds nothing
to any harness root.
