# D-015: One skill copy per machine; per-harness work is agent-def dialects

Six harnesses, one strategy: Claude Code, omp, and zcode keep their
dedicated roots; opencode and Factory Droid read
`~/.agents/skills/**/SKILL.md` as a compatibility root, so the copy
sync.sh already installs serves them — no per-harness skill copies, no
duplicate registration. Antigravity consumes the repo itself as a
plugin (root plugin.json + skills/ + committed byte-verbatim agents/
personas); agy owns its install dir (~/.gemini/config/plugins), sync
never writes there.

The per-harness surface that actually differs is the agent-def
dialect. omp-defs.py established the pattern — parse each brief's own
Claude-style frontmatter, derive the target dialect, regenerate-only —
and tools/agent-defs.py extends it to opencode (permission map derived
from `tools:`, task always deny) and droid (Factory tool IDs, read-only
sets collapsed to the `read-only` category). Droid defs never pin
models: a wrongly guessed Factory model ID is a load error, and cost
tiers already ride the Task call's `complexity` argument.

**Why**: one copy at the compatibility root beats N copies at N native
roots — same bytes, one SHA-verify, and a harness gains support by
documenting what it reads rather than by adding a copy loop. Optional
roots (~/.config/opencode, ~/.factory) install only when the harness's
own config home exists: sync must never fabricate a harness directory,
and removing a harness's config must not resurrect on the next sync.

**Cost if wrong**: a harness changing its discovery paths silently
loses the skill until its docs are re-checked — the exposure any
convention-based install has; mitigated by sync.sh's per-root verify
failing loud on drift and skill-dir.sh naming every root it checks.
The committed root agents/ is a second copy of the briefs that could
drift if hand-edited — sync.sh verifies byte-equality against a fresh
regeneration every run and fails loud.
