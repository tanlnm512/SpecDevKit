# D-030 — /spec-plan and the reviewer's contract mode retire

- **Context**: after the split, `/spec-plan` still ran authoring waves
  to the approve gate from inside the skill that never authors, and
  routed to the removed `/spec-to-prod`. The reviewer brief's
  `contract` mode (review before implementation) had no spawner:
  spec-shape's verify is mechanical and the engine emits only
  `reviewer-diff.md`.
- **Decision**: `/spec-plan` is deleted — `/spec-gen` owns authoring.
  The reviewer is implementation-diff only. Delivery-pass steps are
  numbered 1–6 (proofs, regression gate, review instruments, tick, C1,
  C2) in SKILL.md and the commands. spec-execute installs four
  lifecycle commands.
- **Consequences**: one authoring entry (`/spec-gen`); the install
  total is ten commands. A contract-review pass at spec-shape's verify
  can return as its own decision with a real spawner.
