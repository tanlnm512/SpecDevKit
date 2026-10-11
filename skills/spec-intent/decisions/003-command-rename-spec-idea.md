# D-003 — The intake command is /spec-idea (was /spec)

- **Context**: the split claimed the bare name `spec` for spec-intent's
  intake verb. The user renamed the surface 2026-10-11: `/spec` →
  `/spec-idea` — clearer phase naming beside `/spec-gen` and
  `/spec-execute`, and it un-occupies the bare `/spec` namespace
  entirely.
- **Decision**: `commands/spec.md` → `commands/spec-idea.md`;
  `commands/extra.txt` claims `spec-idea`. The skill's own name
  (spec-intent), scripts, and skill-dir chain are unchanged — this is
  a command-surface rename only. The stale-command prune in
  `tools/sync.sh` removes the old `spec.md` from every root on the
  next install.
- **Consequences**: `/spec-idea <name>` is the intake invocation
  everywhere; handoff docs (spec-brainstorming's template, gates,
  quickstart) name it. Serves eval cases i1–i3 (the flow is
  unchanged; invocation names updated).
