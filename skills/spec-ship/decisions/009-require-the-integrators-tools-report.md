# D-009 — The integrator's reply opens with a tools report that must hold Read

**Status**: accepted (2026-11-26)

## Context

D-008 made the session validate the integrator's digest against its
mode's grammar. The grammar asks what came back, not what the spawn
could do: under omp a spawned subagent's reachable surface is narrower
than its frontmatter (HARNESS-FACTS.md), and an integrator holding no
file reader tightens wording over drafts it never read. spec-design
D-076 makes the capability handshake a kit-wide rule.

## Decision

1. **The reply opens with the report.** The first line of the
   integrator's reply — above the digest — is `tools: <the tools you
   actually hold, comma-separated>`; the rule is stated once in
   `agents/integrator.md` § Output.
2. **Read is the one required tool.** `scripts/digests.py`
   `REQUIRED_TOOLS` asks the integrator for Read and nothing more;
   both grammars ignore the `tools:` line.
3. **The session validates with `--require-tools` and treats exit 3
   as a failed spawn**: `python3 <skill_dir>/scripts/digests.py
   validate integrator <pr-text | threads> --require-tools` — exit 0
   valid, exit 1 with the problems, exit 3 when the `tools:` line
   lacks Read. A malformed digest is a fix and run again; exit 3 is
   not — no body, classification, or draft is read, and the mode is
   spawned again on a type or harness that holds Read. The sentence
   sits in `contracts/run.md` § Digests and what the orchestrator
   checks, pinned by `tests/test_digests.py`.

## Consequences

No PR body and no draft reply reaches the user from a spawn that
could not read what it tightened. Cost if wrong: an integrator that
held Read under another name is re-spawned — a read-only re-run — and
the cure is a name in `REQUIRED_TOOLS`, an edit in the spec-design
master, replicated.
