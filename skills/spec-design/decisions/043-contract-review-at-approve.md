# D-043 — Contract review at the approve stop

- **Context**: check.py cannot see vacuous test cases, over-promised
  acceptance, untestable requirements, or wording drift, and the only
  reviewer pass ran after implementation. spec-execute D-030 removed the
  reviewer's contract mode because nothing spawned it.
- **Decision**: when the approve gate is READY, `--emit-spawns --span
  shape` prepares `reviewer-contract.md` (role reviewer, Mode: contract)
  and the drained-span handoff names it. The orchestrator spawns the
  read-only reviewer before presenting the digest and carries the
  BLOCK/WARN/NIT findings into it; a BLOCK is resolved (repair run) or
  explicitly ruled before the user is asked. `reviewer.md` carries both
  modes, byte-shared across the spec trio.
- **Consequences**: the human approves with the adversarial findings in
  front of them. The run itself still never spawns the reviewer; the
  payload is an instrument, like `reviewer-diff.md` at tick-commit.
