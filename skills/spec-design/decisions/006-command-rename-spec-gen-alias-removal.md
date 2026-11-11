# D-006 — /spec-gen replaces the self-titled router; the /spec-to-prod alias is removed early

- **Context**: the split shipped `/spec-shape` (self-titled router)
  plus the one-release `/spec-to-prod` thin alias (FR-010's
  compatibility window). The user decided 2026-10-11: rename the
  router `/spec-shape` → `/spec-gen` (matching the idea/gen/execute
  phase vocabulary) and remove the alias NOW, ahead of its window.
- **Decision**: `commands/spec-shape.md` → `commands/spec-gen.md`;
  `commands/extra.txt` claims `spec-gen`; `commands/spec-to-prod.md`
  is deleted — the bare name has no claimant, and
  `tools/retired-skills.txt` + the stale-command prune sweep the
  removed files from every install root. A skill may now name no
  self-titled command at all (sync's mandatory-name rule treats the
  `$name` base as present-only; extra.txt claims are the truth).
- **Consequences**: eleven commands install (four routers + seven
  bare: idea, gen, plan, build, test, review, ship); every `/spec-*`
  name is a phase verb. FR-010's alias contract is satisfied early —
  recorded here as the amendment. Serves eval cases e1/e2/e7
  unchanged (flows identical; invocation names updated).
