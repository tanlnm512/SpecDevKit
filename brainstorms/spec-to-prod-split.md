# spec-to-prod-split — design specification

> Handoff artifact of a spec-brainstorming run. Pre-spec by
> design: it records the chosen direction and the reasoning, not
> requirements. The next step is `/spec spec-to-prod-split` with
> this doc as intent input; requirements shaping happens there,
> with the user.

**Status**: handoff-ready · **Date**: 2026-10-10 ·
**Direction**: blend — three front doors, one house core (user-selected three-skill split)

## Direction

The user selected a genuine three-skill split of `spec-to-prod` —
three separately-invocable, self-contained skills, each a phase
product with a hard stop — over both the orchestrator-recommended
"three commands, one package" and the Cynic's "the gate already
serves the driver". The panel's fatal seams are mitigated by
design rather than avoided: the shared core ships as byte-identical
parity-pinned copies (the kit's self-contained-packaging pattern),
and every handoff seam gets a mechanical intake gate.

- Selected: three skills — `spec-intent` (scout + grilling →
  validated intent artifact, stops), `spec-shape` (intent →
  authoring waves + verify → docset, stops at the human approve
  gate), `spec-execute` (approved spec only → implementer waves +
  delivery) — sharing one engine, one contract table, one check
  discipline via parity-pinned copies.
- Rationale: the user's words — "I want to run by phase, with 3
  skills I can fully control result of spec before implementing",
  and on the one-package alternative: "I still want to have 3
  skills". Each phase must be a product the user can invoke, stop,
  inspect, and steer before the next phase runs.
- Rejected: Minimalist/one-package — the user overrode it: phase
  control should be first-class skills (three commands over the
  existing skill), not verb routing inside one surface.
- Rejected: Cynic/do-nothing — the driver wants phase products
  with their own sessions and stops, not the existing approve gate
  and `/spec-*` lifecycle commands; per-phase entry points are also
  where the ecosystem went (github/spec-kit, 140.7k★, accessed
  2026-10-10).
- Rejected: forking the core per skill — the retired-dialects
  failure mode (D-035/D-016); one executable form each, forever,
  no three divergent engines or contract dialects.

## Problem Statement

`spec-to-prod` is one monolithic skill: the session that clarifies
intent is the same loaded surface that authors the docset and the
one that runs implementer waves — so the user cannot invoke "get
me a clear requirement" or "implement this approved spec" alone,
and the path from idea to code reads as one run they must steer
from inside rather than three products they control between.

- Current workaround: the `/spec-*` lifecycle commands phase parts
  of the execution surface, and the human approve gate holds
  execution back — but all of it lives inside one skill's playbook
  one invocation implies.
- Cost of the status quo: phase control is implicit rather than
  owned; each phase's result has no standalone product shape;
  composing one phase with outside inputs (an intent written
  elsewhere, a spec shaped by hand) is structurally unsupported.

## User Personas

### Persona 1 — the phase-gating owner

- Who: the developer who owns what gets built and wants judgment
  checkpoints between requirement, spec, and code.
- Needs: to run intent-gathering alone, read and steer the shaped
  spec, and only then decide to let implementation run — each
  phase a separate invocation with a hard stop.
- Failed by: the monolithic skill bundles the three concerns; the
  approve gate exists but is buried inside one run's surface
  rather than being the boundary between products.

### Persona 2 — the re-driver of existing specs

- Who: a developer with an already-approved spec (shaped by hand,
  by a teammate, or in an earlier session) who wants only the
  implementation machinery.
- Needs: point an execution skill at the approved docset and get
  waves, proofs, ticks, and delivery — without loading or invoking
  the authoring pipeline.
- Failed by: today `spec-to-prod` must be invoked as a whole; its
  authoring half is dead weight for this persona.

## Core MVP Features

1. Three self-contained skills, one per phase — serves the
   phase-gating owner: `spec-intent`, `spec-shape`, `spec-execute`
   as separate installable skills, each invocable alone, each
   ending in a hard stop with its boundary artifact.
2. Validated intent artifact with its own gate — serves the
   phase-gating owner: `spec-intent` scouts the repo (survey lens)
   and grills (grilling primitive) until the frontier is empty,
   producing an intent artifact a mechanical checker accepts
   before the skill stops.
3. Shape consumes intent through an intake gate — serves the
   phase-gating owner: `spec-shape` refuses a stale, mismatched,
   or un gated intent artifact (baseline/marker checks), runs the
   authoring waves + verify, presents the docset, and stops at the
   human approve gate.
4. Execute keyed to approval only — serves both personas:
   `spec-execute` refuses any spec without `Status: approved`,
   then runs implementer waves, the delivery pass, ticks, and the
   commit gates; approval is the only key.
5. Parity-pinned shared core — serves both personas: the engine
   (graph.py --run), contract table, specstate, and check
   discipline ship as byte-identical copies in each skill, pinned
   by a kit-level parity test (the telemetry-module pattern) —
   never three dialects.

**Out of scope (day-one cut list)**: a marketplace/storefront
surface per skill (install rows come from the existing sync — no
new publishing machinery); any new engine or workflow runtime (one
engine only, D-035 holds); rewriting spec-brainstorming into
spec-intent (brainstorming stays the pre-spec idea product;
spec-intent consumes its handoff when present but owns the
repo-grounded clarify pass); migrating existing on-disk specs (the
docset contract is unchanged — every existing spec dir already
satisfies shape/execute); per-phase telemetry stores beyond the
existing `~/.spec-dev-kit/telemetry/` scheme.

## Potential Risk Mitigations

The Cynic's dealbreakers carried forward, each mapped to a
mitigation or an explicit acceptance — never dropped silently.
Kill criteria live here: the observable evidence that should stop
the project.

| Risk (from the panel) | Early warning | Mitigation or acceptance |
|---|---|---|
| Shared core copied three times drifts — every contract change lands three times or diverges (the D-035/D-016 twin failure reborn) | A parity test red on any core file differing between skills; contract edits that touch three copies by hand | Byte-identical parity-pinned copies with a kit-level test that diffs all copies on every suite run; edits land in one source and regenerate (the kit's generated-surface discipline) |
| Handoff artifacts rot between separately-invocable runs — stale intent, hand-edited spec reaching the waves unflagged, so the user approves less than before | A shape run starting from an intent whose baseline commit or marker mismatches; an execute run starting from a docset check.py no longer passes | Mechanical intake gates at both seams: shape validates the intent artifact (shape, markers, baseline) before any wave spawns; execute requires `Status: approved` AND a green check.py before the first wave — both refuse loudly, never warn-and-proceed |
| The driver is already served by the existing approve gate and `/spec-*` commands — the split re-buys control at triple surface cost | After the split ships, no session invokes intent or execute alone in real use (telemetry shows only whole-pipeline patterns) | Accepted with a tripwire: telemetry's per-skill streams are the evidence — if 30 days of real runs show no solo-phase invocations, the split failed its driver and the one-package form returns |
| Three skills grow three orchestration dialects again | Any per-skill workflow/runtime file appearing in review | One engine forever: each skill's payloads and runs go through graph.py --run's runner seam; no dialect files exist to add — enforced by the parity test pinning the engine copy byte-identical |
| The intent artifact becomes a second spec format that check.py does not gate — an ungated shape drifting from the docset contract | Intent artifacts hand-edited into shapes the checker was not built for | The intent artifact's checker is a profile of the SAME check discipline (tier-aware), and shape's intake gate is the backstop: a drifted intent never reaches a wave |

**Kill criteria**: (1) any core file (engine, contract table,
specstate, checker) diverges between the three skills in a
released tag — the parity pin failed; (2) a shape or execute run
starts from a refused-should-have-been input (stale intent or
unapproved spec) in a real session — the intake gates failed;
(3) 30 days of telemetry after shipping show zero solo-phase
invocations — the split bought surface without changing behavior;
(4) any per-skill workflow dialect file appears — the retired
failure mode returned.

---

*Next step: `/spec spec-to-prod-split` — treat this doc as
intent input. The commit is the user's.*
