# D-002 — command claims redistributed; the router becomes a one-release alias

- **Context**: bare command names land in shared global roots
  only via each skill's `commands/extra.txt` opt-in — sync's
  bare-name rule refuses a second claimant. The split
  redistributes the monolith's eight names across three skills
  (FR-010), and the `/spec-to-prod` router must keep forwarding
  for exactly one release so existing muscle memory resolves
  before it retires.
- **Decision** (split D-006): spec-intent claims `spec` (today's
  intake verb, via `commands/spec.md`); spec-execute claims the
  five execution-phase lifecycle verbs — `spec-plan`,
  `spec-build`, `spec-test`, `spec-review`, `spec-ship` — with
  their command files moved out of the monolith's commands dir
  (T016); spec-shape hosts the thin `/spec-to-prod` alias router
  via its `extra.txt` (T017) — a verbs-only forwarder
  (scaffold/intake → `/spec-intent`, authoring → `/spec-shape`,
  execute verbs → `/spec-execute`, no pipeline body), deleted
  the release after. The monolith's full router file was deleted
  in the same task so the bare name has exactly one claimant,
  and its `extra.txt` dropped every moved name in lockstep.
- **Consequences**: FR-010 holds — the redistributed bare names
  install the same command set as before (the exact-set pins in
  `tools/tests/test_sync.py`, updated in T019, keep matching),
  and no bare-name collision can occur by construction. The
  alias's own retirement is a one-line `extra.txt` removal plus
  the command-file deletion, to be recorded against this ADR
  family (append-only, NFR-002). A mis-routed verb — the
  tech spec's accepted residual risk — is bounded by the alias
  staying a thin forwarder over the three new commands only.
