# D-005 — telemetry names itself by derivation, not by branch

- **Context**: FR-007 requires each skill's mechanical
  chokepoints to record telemetry under its own name in the
  existing `~/.spec-dev-kit/telemetry/` scheme — but the engine
  hardcoded the literal `_record("spec-to-prod", …)` at its
  `gate_pause`/`run_end`/`wave` chokepoints, and the file must
  stay byte-identical across the trio (FR-005). A per-skill
  conditional would fork the bytes; a scheme change would break
  the 30-day tripwire substrate.
- **Decision**: the three literals are replaced by the engine's
  own resolved skill root name — the same `skill_dir` resolution
  every payload already carries. `telemetry.py` stays untouched
  (`def record(skill: str, event: str, **payload)` was already
  parameterized); no per-skill branch exists anywhere in the
  file. The two new span-entry gate refusals (D-003 here) are
  chokepoints too: each records an `intake_refusal` event under
  the refusing skill's derived name.
- **Consequences**: FR-007 holds — the same bytes record under
  spec-intent/spec-shape/spec-execute as each copy runs, giving
  per-skill JSONL files with zero scheme change. The spec's
  business-value tripwire (solo-phase invocations within 30 days
  of shipping) and the brainstorm's kill criterion 3 read those
  streams directly. The kit's telemetry exact-set pin grew to
  the full shipper set in the same change.
