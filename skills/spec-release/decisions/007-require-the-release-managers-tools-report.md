# D-007 — The release manager's reply opens with a tools report that must hold Read

**Status**: accepted (2026-11-26)

## Context

D-006 made the session validate the release manager's digest against
its grammar. The grammar asks what came back, not what the spawn could
do: under omp a spawned subagent's reachable surface is narrower than
its frontmatter (HARNESS-FACTS.md), and a release manager holding no
file reader tightens a section and traces facts it never read.
spec-design D-076 makes the capability handshake a kit-wide rule.

## Decision

1. **The reply opens with the report.** The first line of the release
   manager's reply — above the digest — is `tools: <the tools you
   actually hold, comma-separated>`; the rule is stated once in
   `agents/release-manager.md` § Digest.
2. **Read is the one required tool.** `scripts/digests.py`
   `REQUIRED_TOOLS` asks the release manager for Read and nothing
   more; the grammar ignores the `tools:` line.
3. **The session validates with `--require-tools` and treats exit 3
   as a failed spawn**: `python3 <skill_dir>/scripts/digests.py
   validate release-manager --require-tools` — exit 0 valid, exit 1
   with the problems, exit 3 when the `tools:` line lacks Read. A
   malformed digest is a fix and run again; exit 3 is not — no
   section, trace, `dropped:` or `watch:` line is read, nothing is
   replaced in the notes, and the release manager is spawned again on
   a type or harness that holds Read. The sentence sits in
   `contracts/run.md` § The release manager, pinned by
   `tests/test_digests.py`.

## Consequences

The user is never shown a tightened section from a spawn that could
not read what it tightened. Cost if wrong: a release manager that held
Read under another name is re-spawned — a read-only re-run — and the
cure is a name in `REQUIRED_TOOLS`, an edit in the spec-design master,
replicated.
