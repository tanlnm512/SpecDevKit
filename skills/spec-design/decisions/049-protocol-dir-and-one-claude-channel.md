# D-049: protocol/ holds the shared prose; Claude gets one channel

Claude Code registers every `.md` under a plugin's `agents/` as an
agent. The lens tables and shared protocols (`_lenses.md`,
`_shared-protocol.md`, `_panel-protocol.md`) sat in `agents/`, so every
plugin install listed them as spawnable, description-less, all-tools
agents (`spec-author:_lenses`, `spec-code-review:_panel-protocol`, …).
No manifest field can exclude a file from that scan.

Separately, `tools/sync.sh` copied each whole skill dir — including
`.claude-plugin/plugin.json`, `agents/` and `commands/` — into
`~/.claude/skills/<name>/`. Claude Code loads a skills-dir entry that
carries a plugin manifest as a plugin, so every agent and command was
listed twice: once flat (`spec-scout`, from `~/.claude/agents/`) and
once per shipping skill (`spec-author:spec-scout`,
`spec-intake:spec-scout`).

**Decision**:

1. Shared prose a brief points at lives in a per-skill `protocol/`
   dir, never `agents/`: `protocol/lenses.md`,
   `protocol/shared-protocol.md`, `protocol/panel-protocol.md` (the
   leading underscore is dropped — the dir now says "not a role").
   `agents/*.md` holds roles only; `tools/tests/test_manifests.py`
   pins that every file there carries `name` + `description`
   frontmatter. graph.py reads lenses and the shared protocol from
   `SKILL_DIR / "protocol"`; byte-sharing across the graph trio stays
   pinned by `tools/tests/test_parity.py`.
2. The flat roots (`~/.claude/agents/`, `~/.claude/commands/`) are the
   one Claude Code channel. sync installs `~/.claude/skills/<name>/`
   without `.claude-plugin/` and `commands/`, so the copy loads as a
   plain skill. `agents/` and `protocol/` stay in the copy: graph.py
   embeds brief bodies and protocol text into spawn payloads by path,
   and the SKILL.md spawn mechanics read them from `skill_dir`.
3. Every skills-tree install drops `tests/` — dev-only, read by
   nothing at runtime. `decisions/`, `evals/` and `observations/`
   stay: spec-code-review's resource map points the session at them.

Each protocol header now states how it actually reaches the agent:
graph.py (spec trio) and the brainstorming session carry it verbatim
in the spawn payload; spec-code-review's review agents read it by path
through their briefs' Shared rules pointer.

**Not changed**: the marketplace route (`/plugin install` from
marketplace.json) still installs each `skills/<name>/` as a plugin —
that route has no flat copies, so its namespaced listing is the only
one. Other harness roots (`~/.agents/skills`, omp, Kilo) keep the
manifest and `commands/`: no double listing is known there, so
the change stays on the Claude path.

**Migration**: rerun `tools/sync.sh`. The old `.claude-plugin/`,
`commands/` and `tests/` files in installed skill trees are
ledger-proven deploys, so sync deletes them (and the dirs they leave
empty); anything foreign there is refused as before.
