# Approval freeze

**Approved-at**: `-`
**Algorithm**: sha256 over UTF-8 bytes

Recorded only after explicit user approval. `spec.md` is hashed without
its volatile Status line (at tiny tier also without § Evidence and the
status markers inside § Tasks; the task list itself is frozen).
`tech-spec.md` is verified as an immutable prefix so implementation
may append D-### decisions. `task.md` is not frozen because it is the
status holder.

## Frozen contract
- `spec.md`: exact sha256:16a2ecb6d4a933d4ec3e5e7c7667d56f55c4a9e0982384993a5ace207d3d09bc length:1672

Any other change to these files requires a fresh user approval and a
new freeze record.
