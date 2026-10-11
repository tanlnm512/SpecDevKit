# D-001 — spec-intent: the intake front door ships as a skill

- **Context**: the split's driver is the phase-gating owner who
  "want[s] to run by phase, with 3 skills I can fully control
  result of spec before implementing" — the brainstorm artifact
  (`brainstorms/spec-to-prod-split.md`, direction: blend — three
  front doors, one house core) records the user overriding both
  the one-package and do-nothing alternatives. In the monolith,
  the clarify concern (scout + grilling) is the loaded surface
  that also authors and executes: "get me a clear requirement"
  cannot be invoked alone, and the intent result has no
  standalone product shape.
- **Decision**: `spec-intent` ships as the separately-invocable
  intake skill. It scouts the repo (the survey lens) and grills
  the user (the `references/grilling.md` primitive) until the
  question frontier is empty, producing `specs/<name>/intent.md`
  validated by `check.py <spec-dir> --intent-only` (split D-001)
  — then hard-stops: the docset is spec-shape's, execution
  spec-execute's. The workflow runs `graph.py --span intent`.
  Carried ingredients: `agents/scout.md`, the intent section of
  `agents/_lenses.md`, `templates/intent.md`; the bare name
  `spec` is claimed via `commands/extra.txt` with
  `commands/spec.md` as the intake verb.
- **Consequences**: FR-001 (scout + grill to a validated
  artifact, invocable alone) and FR-002 (the checker's refusal
  families) hold; serves eval cases I1 (raw idea to validated
  intent), I2 (non-answer round hard-stops), I3 (stale baseline
  refusal). spec-brainstorming stays the pre-spec idea product —
  this skill consumes its handoff when present but owns the
  repo-grounded clarify pass. Telemetry records under the skill's
  own name (split D-005), feeding the 30-day solo-phase tripwire.
