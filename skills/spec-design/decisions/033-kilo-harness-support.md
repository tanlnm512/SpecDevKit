# D-033 — Kilo harness support (extends D-015's model)

- **Context**: the kit installs to six harness surfaces; Kilo (the
  Kilo CLI, kilo.ai) was absent. Kilo's config model: commands load
  from `{command,commands}/**/*.md` inside its config directories
  (`~/.config/kilo/` global, `.kilo/` project), agents from
  `{agent,agents}/**/*.md` there (frontmatter: description, `mode:
  primary|subagent|all`, optional model as provider-prefixed ID,
  permission map over tool keys), skills from `{skill,skills}/<name>/
  SKILL.md` inside config dirs — plus the `~/.agents/skills`
  compatibility root, which a live Kilo session was verified to scan
  natively (this kit's skills register from it with no kilo.json
  configuration). Kilo has no dynamic workflow runtime; its
  "workflows" surface is legacy markdown auto-converted to commands
  and is deliberately not targeted.
- **Decision**: Kilo joins the optional-harness pattern exactly as
  opencode/droid did (D-015's model — one skill copy at
  `~/.agents/skills` feeds it; per-harness work is generated
  dialects only): `tools/agent-defs.py --target kilo` renders each
  role brief as a Kilo subagent def (description + `mode: subagent` +
  a permission map derived from the brief's own `tools:` —
  read/edit/bash/glob/grep/skill/webfetch/websearch allow iff listed,
  Write and Edit both mapping to `edit`; `task` always denied, the
  "no agent spawns another" rule made mechanical; model omitted —
  Kilo wants provider-prefixed IDs the briefs don't carry), installed
  to `~/.config/kilo/agent/`; the router and lifecycle commands
  install to `~/.config/kilo/command/` (its `$ARGUMENTS` template
  variable is the one the wrappers already use). Both gated on
  `~/.config/kilo` existing — skipped loudly, never fabricated, so a
  fresh Kilo install needs one more sync run. `skill-dir.sh` gains
  the `.kilo/` project root and `~/.config/kilo` home root for
  project-vendored copies. No workflow dialect: SKILL.md's inline
  fallback (the opencode/droid path) runs the stages.
- **Consequences**: a seventh install surface with the same
  provenance-ledger discipline, preflight planning, and SHA verify;
  read-only roles (the reviewer) stay read-only mechanically
  (`edit: deny`) where Kilo honors the permission map. Serves eval
  case `spec-to-prod/e1` (the router surface, now reachable from
  Kilo as `/spec-to-prod` and the six lifecycle commands) and holds
  the sync contract the README's harness list names — new coverage in
  `tools/tests/test_agent_defs.py` (render) and
  `tools/tests/test_sync.py` (gated install, refusal, skip).
