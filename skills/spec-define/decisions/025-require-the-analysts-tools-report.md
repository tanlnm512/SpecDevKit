# D-025 — the analyst's reply opens with a tools report, and a digest without a file writer is refused

- **Context**: spec-design D-076 makes the capability handshake a
  rule for every spawned role: under omp a spawned subagent's
  reachable surface is narrower than its frontmatter (HARNESS-FACTS.md),
  and an analyst with no file writer returns a digest for an artifact
  it could not write. Nothing asked what the spawn held.
- **Decision**: adopt spec-design D-076. The intent payload's first
  instruction asks for the first line of the reply — and of its digest
  file, above the `digest:` line — `tools: <the tools you actually
  hold, comma-separated>`; the rule is stated once in
  `protocol/shared-protocol.md`, the trio's byte-shared carrier. The
  orchestrator refuses on a missing required tool, and it is not a fix
  round: `scripts/digests.py` `REQUIRED_TOOLS` asks the analyst for a
  file writer (Write or Edit) and nothing more; the provenance sweep
  records an `analyst.md` digest file whose report lacks one as
  `capability_missing`, prints the refusal, and gives the file no
  provenance line; a digest returned in conversation is checked with
  `python3 <skill_dir>/scripts/digests.py validate analyst intent
  --require-tools` — exit 3 is a failed spawn: spawn again on a type
  or harness that holds the tool. The reported set rides the provenance
  line and ledger row as `tools-reported`, the agent's claim. The
  scripts are the master's, replicated by `tools/parity.py`; the
  intent grammar is unchanged.
- **Consequences**: no count is taken from a digest a degraded spawn
  wrote. Cost if wrong: an analyst that held the tool under another
  name is re-spawned, and a digest file written before this decision
  is refused on its next read — the spawn re-runs; the cure for the
  first is a name in `REQUIRED_TOOLS`, an edit in the spec-design
  master, replicated.
