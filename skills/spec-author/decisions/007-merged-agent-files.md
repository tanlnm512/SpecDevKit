# D-007: One file per agent — frontmatter + brief merged

agents/spec-*.md carries the harness frontmatter (tools, readonly, model)
on top of the full brief body; there is no separate thin-pointer def and
no separate brief file. Claude Code installs copies where it reads agent
defs; the fallback spawn strips the frontmatter and uses the body as the
system prompt.

**Why**: two representations of every role (30-line pointer def + brief)
had already drifted once (the surveyor def contradicted its brief after a
brief edit — caught in the 2026-08-25 review round 6). Merging removes the
drift class entirely, makes the def-spawn self-contained (the body IS the
system prompt — no brief re-read step), and finishes the v1.4.0
self-contained-skill-dir job. Supersedes D-005, whose anti-fork rationale
(one portable canon) is preserved: there is exactly one body.

**Cost if wrong**: fallback prompt construction gains a trivial
frontmatter-strip step; a harness that honors frontmatter but injects only
a truncated body would under-brief its agents — none observed.
