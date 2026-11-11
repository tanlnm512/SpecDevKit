# D-004 — The script writes the notes; the release manager edits words

**Status**: accepted (2026-11-11)

## Context

Release notes written freehand by a model drift from what shipped:
they inflate, omit breaking changes, or invent a feature from a commit
subject. The facts a changelog needs are all derivable: the delivered
specs and their work types, the commits in range, the dependency
diff, rollout notes, parked items.

## Decision

- `notes --write` assembles the section deterministically from the
  collect facts into the project's own changelog format: the newest
  version heading is the model, an `Unreleased` section's entries move
  in verbatim, Keep a Changelog link references stay last.
- Every bullet ends with a trace token — `(<spec-name>)` or
  `(<short-sha>)`. `notes --check` (and preflight) fails a section that
  misses an included spec or cites a spec or commit outside the range.
- One read-only role, `spec-release-manager`, tightens the wording and
  writes upgrade notes and known issues from the facts, returning a
  trace for every bullet. It cannot drop a `**Breaking**:` prefix or a
  trace token, and it writes nothing.
- The GitHub release body is the tagged changelog section, wrapped by
  `templates/release-notes.md` — one text, two surfaces.

## Consequences

The check binds structure, not meaning: a bullet that keeps its token
but misstates its fact passes. The trace and the user's review of the
tightened section own that residue.
