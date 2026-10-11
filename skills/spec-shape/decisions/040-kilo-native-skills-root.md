# D-040 — Kilo's native skills root joins the install

- **Context**: D-033 added Kilo support with commands + agent defs
  but NO skills copy, on the strength of one live-session
  observation that Kilo scans the `~/.agents/skills` compatibility
  root. That scan is undocumented behavior — a Kilo update could
  drop it silently, and the kit's install would silently stop
  reaching the harness.
- **Decision**: `tools/sync.sh` installs the full skill tree to
  `~/.config/kilo/skills/<name>/` — Kilo's DOCUMENTED skills surface
  (`{skill,skills}/<name>/SKILL.md` inside its config directories) —
  gated on `~/.config/kilo` existing like every optional root
  (preflight plan, per-file atomic apply, SHA verify, provenance
  ledger — the identical `install_skill_tree` path every other root
  takes). The `~/.agents/skills` compatibility copy stays: harnesses
  that read it keep working, and Kilo users who never saw the
  compat scan get skills regardless.
- **Consequences**: the install no longer depends on undocumented
  scanning; Kilo coverage is the same shape as zcode/claude/omp
  (native root + compat root). One redundant copy per skill on
  Kilo machines — cheap, and the price of not betting on an
  undocumented behavior. Holds D-033's eval case
  `spec-to-prod/e1` (the router surface, now fed by Kilo's own
  root) and the sync contract; new coverage in
  `tools/tests/test_sync.py` KiloCommandsTests (skills-tree
  install + byte-equality with the master).
