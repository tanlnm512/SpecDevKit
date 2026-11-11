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
- `spec.md`: exact sha256:20f459fb1cf22c187868364e04af61c45c02869a0cbe435d88460e0ff8fd9a43 length:1672

Any other change to these files requires a fresh user approval and a
new freeze record.
