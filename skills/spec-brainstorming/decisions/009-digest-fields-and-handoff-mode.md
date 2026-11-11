# D-009: The digest carries what stage 5 reads; compile-only `handoff` has no panel

Stage 5 maps "the Cynic's dealbreakers" and kill criteria into the
artifact, but the digest grammar (`angle · pitch · points · watch`)
had no field for either, and `handoff` mode runs no panel at all.
Two contract changes close the gap.

**Digest fields.** The Cynic's digest gains `kill:` (the observable
evidence that should stop the project) and the Minimalist's gains
`proof:` (the cheapest test of the core value). A **dealbreaker** is
defined as a line of the Cynic's `points:`; its `watch:` supplies a
risk's early warning where one fits, `kill:` seeds the kill criteria,
`proof:` becomes the first-week check when the Minimalist cut is
chosen. A load-bearing external claim ends its line with an inline
`[source]`. `points:` is the one multi-line field; every other field
is one line. Each lens section in `protocol/lenses.md` is delimited
by its `## Lens:` heading alone (inner headings are `###`), so "one
section verbatim" is well-defined.

**Handoff mode.** The compile-only `handoff` entry is the one defined
exception to "none skippable": it begins at stage 5 and no panel
runs, so no digest exists. The risk table then carries the risks and
objections raised in the discussion, each marked "(from the
discussion)", and the dealbreaker-mapping judgment applies to those.
Panel digests are never persisted: a resume that reopens the
direction restarts at stage 2 from the artifact's problem statement.

**Why**: running the Cynic alone in handoff mode would add a spawn
for a path whose point is to compile what was already explored; the
mark keeps the provenance honest instead. Persisting digests would
add a second artifact for a rare path.

**What's preserved**: the panel never picks (Principle 4), digests
stay independent (D-002, D-007), one panelist archetype, nothing
under `specs/` (D-003). The checker's mechanical criteria are
unchanged except that placeholders are now derived from
`templates/design-spec.md` instead of a hand-kept stem list, a path
under `specs/` is refused, and `Rejected: none — blended …` is
accepted when the user blended all three angles.

**Cost if wrong**: a lens that omits `kill:` or `proof:` leaves the
session to derive it from `points:`/`watch:`; the checker does not
gate digests, so nothing breaks mechanically.
