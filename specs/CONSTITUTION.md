# Constitution: SpecDevKit

- **C-01**: Doc state is the only state — every node's readiness
  derives from the spec's own directory under specs/; no session
  ledger, no cache.
  Rationale: inferred state drifts; derived state re-computes.
- **C-02**: Every grammar element ships with a gate and a reader — no
  doc shape exists that check.py does not validate or no script
  parses. Rationale: ungated grammar rots silently (the survey found
  retro.md write-only).
- **C-03**: Generated surfaces are regenerate-only — templates,
  manifests, and shared-script replicas are never hand-edited;
  drift-check stays green. Rationale: byte-identical parity across
  skills is the kit's install contract.
- **C-04**: Nothing leaves the machine without the user's yes to a
  shown plan. Rationale: ADR-014's commit boundary — push, PR, tag,
  publish are human gates.
- **C-05**: Migration never lies — old grammar degrades loudly (one
  WARN naming the fix, then FAIL), evidence is never inferred, a
  recorded freeze is never re-opened. Rationale: silent upgrades
  manufacture false evidence; the non-git honesty precedent.

Each article binds every spec and task in this repo; amendments append
and never weaken silently.
