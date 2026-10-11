# D-005: Agent defs stay thin pointers; the brief is canonical

Harness agent defs (agents/defs/spec-*.md) carry only frontmatter
mechanically enforced by the harness (no writes for reviewer, no
spawning/commit for anyone) and point at agents/<role>.md +
agents/_shared-protocol.md via the payload's skill_dir. The brief IS the
system prompt; defs never inline method content.

**Why**: defs are install-target-specific (~/.claude/agents/); briefs
are the portable canon. Inlining method into defs forks it per harness.
Where the harness ignores def frontmatter, the fallback spawn carries
the same rules in the prompt — instruction-enforced, clearly labeled as
weaker.

**Cost if wrong**: none — defs regenerating from briefs is mechanical if
standalone agents are ever wanted (decided against for now).

**1.4.0 note**: defs moved from the package root into agents/defs/ so
the skill ships as one self-contained directory; the thin-pointer design
is unchanged.
