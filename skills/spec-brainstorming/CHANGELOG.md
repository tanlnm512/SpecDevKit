# Changelog — spec-brainstorming

Release history. The skill began life 2026-09-29 as the third
resident skill of the SpecDevKit repo: the pre-spec front door —
five rigid stages from a raw idea to a durable design
specification that feeds spec-to-prod's `/spec` intake.


## 0.4.0 — 2026-10-01

External evidence grounding for the panel. A brainstorm that
argues only from the idea-owner's repo inherits the repo's own
blind spots — the 0.3.0 panel proved it in the field, reasoning
from source code and stale internal snapshots while the outside
world moved. Stage 2 now gathers an **evidence pack** before the
lenses spawn: one neutral researcher (never a lens seat — the
pack is shared input, the digests stay independent) searches
GitHub for prior art and competing tools (stars, activity,
maintenance signals) and the web for 2–4 authoritative sources,
each finding returned with its URL and access date. The pack
rides the stage-2 payload (`contracts/run.md` item 4); a failed
gather is logged and the payload says so — the lenses then treat
every external claim as an assumption and never invent a source.

Deep thinking is pinned, not hoped for: the shared panel protocol
gains two rules — **Ground outside the payload too** (cite
`file:line` for in-repo claims, URL + access date for external;
unsourced claims are stated as assumptions; "searched and found
nothing" is a finding) and **Falsify once, then argue** (each
lens attacks its own strongest point once before writing the
digest, then argues what survives at full conviction).

Both workflow dialects carry the change in parity: a new
"Gather external evidence from GitHub and the web" phase, the
evidence section and citation/self-falsification sentences in the
shared payload ask, and the degrade honesty in verified/notCovered
— all pinned by extended anchors in `tests/test_workflow_copies.py`.
Args are unchanged; the workflow form gathers the pack itself,
the inline form's session gathers it before spawning.

Fixed: the zcode master's empty-payload early exit inferred
`never[]` for its `angles`/`verified` report fields and failed
the run's typecheck before any lens spawned; the fields are now
typed.

Migration: none required — dispatch args are unchanged; sessions
running the inline form should gather the evidence pack before
spawning (SKILL.md says how).


## 0.3.0 — 2026-10-01

Kit-wide engineering rules scoping (D-005): the suite's new
engineering rules (test discipline, backgrounded-job discipline,
strict code commenting — canonical in spec-to-prod's
`agents/_shared-protocol.md` § Engineering rules) deliberately do
NOT ride into the lens briefs — the three lenses are read-only
(digests + the stage-5 artifact, no code, no tests, no commands),
so none of the rules' actions can occur here; the rules bind
downstream, when the chosen direction becomes a spec and then
code. What binds at this skill is the session-level
backgrounded-job discipline, recorded in a new SKILL.md
§ Operator rules for the orchestrator running stages 1, 3, 4 and
5. If a future stage starts running commands or generating code,
D-005 is revisited, not silently extended.

Migration: none required — no agent brief, contract, or workflow
master changed; the new SKILL.md section is orchestrator-facing
prose.


## 0.2.0 — 2026-09-29

Structural parity with the sibling skills — the standard
directories every resident skill carries, each with a real job:

- **contracts/run.md** — the canonical run contract (stage
  shapes, the stage-2 payload, the digest grammar, the artifact
  rules, the workflow's scope). SKILL.md summarizes; it
  arbitrates.
- **gates/handoff.md** — the handoff gate: observer-checkable
  stop conditions and readiness criteria before `/spec` is
  named.
- **workflows/** — the panel wave, a workflow form scoped to
  stage 2 ONLY (D-004): both dialects
  (`spec-brainstorming.dwf.ts` for zcode, `spec-brainstorming.js`
  for Claude Code) load the briefs and protocol from the skill
  dir at run time, spawn the three lenses fresh and in parallel,
  and return the digests verbatim. The interactive stages are
  always the session's — a stop is not a question.
- **tests/** — the skill's own suite: `test_flow_contracts.py`
  pins the rigid flow contract (five stages in order, the lens
  briefs' digest contract, the template's pinned sections, the
  green fixture satisfying the handoff gate) and
  `test_workflow_copies.py` pins dialect parity (phases, payload
  anchors, digest grammar, runtime invariants, briefs loaded
  never embedded). 15 tests, wired into CI.
- **examples/decision-tracker/** — the green fixture: a
  completed design spec (the B1–B3 reference output) that
  satisfies every handoff-gate criterion.
- **diagrams/** — the five-stage flow (`spec-brainstorming-flow.mmd`
  + the styled HTML render).

Migration: none required — the inline flow is unchanged; the
workflow form is additive, and no artifact or command surface
moved.


## 0.1.0 — 2026-09-29

First release. The five-stage contract:

- **Context discovery** — exactly ONE clarifying question (no
  lists, one follow-up max), aimed at whichever of problem /
  audience / constraints is fuzziest (D-001).
- **Perspective multiplication** — a fresh, parallel three-lens
  panel — the Visionary, the Cynic, the Minimalist — spawned from
  one payload, none seeing another's output (D-002).
- **Trade-off matrix** — one table: pros, cons, implementation
  speed, best-when per angle; no recommendation.
- **Socratic refinement** — single sequential questions (one per
  turn, soft cap five) to select or blend a direction; the panel
  never picks the winner.
- **Handoff** — a Markdown Design Specification (direction,
  problem statement, user personas, core MVP features, risk
  mitigations) written to `brainstorms/<name>.md` from the pinned
  template (D-003), with `/spec <name>` named as the next step.

Rigid by design: the stages always run in order, none is
skippable, and nothing is ever written under `specs/`.

Migration: none required (new skill — first release).

