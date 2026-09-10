# D-009: Clarify pass adopts the "grilling" round/frontier model

Stage 0's clarify pass no longer asks its derived questions **one decision
at a time**, serially. It now maps them as a **design tree** (every open
decision branches into the decisions that hang off it) and works the tree
in **rounds**: the **frontier** — every question whose prerequisites are
already settled — goes out as one batched, numbered round with a
recommended answer per question; the next round is computed from that
round's answers, not asked up front. The pass ends when the frontier is
empty, not at a fixed question count. It also makes explicit what was
previously implicit: a question that is really a fact ("does X already
exist") is the orchestrator's to look up (grep, or a scoped surveyor
probe), never the user's to be asked.

Adapted from Matt Pocock's `grilling` skill (MIT,
github.com/mattpocock/skills, `skills/productivity/grilling/SKILL.md`),
surfaced via its one-line `grill-me` pointer skill in the same repo. The
technique — not the skill itself — is vendored into SKILL.md's prose, the
same way `references/mermaid-cheatsheet.md` is vendored rather than
required at runtime: a repo running this pipeline should not need
Matt Pocock's plugin installed for Stage 0 to work.

**Why**: "one decision at a time" was adopted wholesale from ai-devkit in
1.3.0 with no dedicated rationale on record (CHANGELOG 1.3.0 §3) — it
serializes every question into its own round-trip even when three of them
have no dependency on each other and could be answered in the same
breath. The "≤5" cap was an arbitrary ceiling standing in for "don't
overwhelm the user," a job the frontier already does structurally: a round
only ever contains the questions answerable *right now*, typically a
handful, never the whole tree at once. Batching what's independent is
strictly faster without being denser per round.

**What's preserved, not overridden**: the tri-state closure rule (answered
/ deferred / named assumption, never left open), "an ambiguity caught here
never reaches Stage 2," and "do not proceed until the user confirms shared
understanding" — grilling's own termination condition ("do not act on it
until the user confirms") already matched these, so nothing here was
softened to adopt it.

**Cost if wrong**: a badly-decomposed tree could still front-load an
unbatchable pile of independent questions into round 1 — no worse than
today's "up to 5" in the worst case, and self-correcting once the user
pushes back (a tree "that keeps sprouting new branches instead of
closing" is called out explicitly as the split-the-feature signal, not a
round to push through). No script depends on the round shape, so this is
a prose-only change: nothing in `check.py` gates on it.
