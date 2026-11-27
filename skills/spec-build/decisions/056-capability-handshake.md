# D-056: refuse a landing on a digest that lacks a required tool — a capability handshake failure is a failed spawn, never a fix round

D-040 made the developer's digest file the evidence `mark.py land`
reads, D-054 gave it a schema, and D-055 records who produced it. None
of them asks what the spawn could do: HARNESS-FACTS.md records that
under omp a spawned subagent's reachable surface is narrower than its
frontmatter, and a developer holding no shell or no file writer
returns a digest that is well-formed and wrong for the work —
`implemented` from an agent that never ran the acceptance commands.
A malformed digest and a blocked digest each had a route; a degraded
spawn had none.

**Decision** (the ask, the schemas and the report reader are
canonical in spec-design D-076; this skill's half is the land gate):

1. **The developer's digest file opens with its tools report.** Every
   payload's first instruction asks for `tools: <the tools you
   actually hold, comma-separated>`; the rule sits in
   `protocol/shared-protocol.md`. The report is the agent's claim —
   recorded as `tools-reported` on the provenance line and the ledger
   row — never a fact the kit asserts.
2. **`mark.py land` refuses a file whose report lacks a required
   tool**: a file writer (Write or Edit) and Bash, the least the
   developer needs to write its task and run its acceptance commands
   (`scripts/digests.py` `REQUIRED_TOOLS`; nothing else is required).
   Exit 1, nothing written: the task stays claimed, no round opens,
   and `--digest` does not talk over it — the file exists, and the
   file is refused. The refusal names the role, what it reported, what
   was required, and the remedy: `mark.py release` with a `blocked:`
   reason, then re-emit and spawn again on a type or harness that
   holds the tool — D-049's "a spawn that did not answer" class.
3. **One content is recorded once.** The refusal appends a
   `capability_missing` row to the run ledger with the unmet
   requirement as `outcome` and the report as `tools-reported`. A
   refused verb is still no event: the row records what the verb saw,
   as `digest_malformed` does.
4. **A file written before this decision is refused too** — it
   carries no report. Release the task and spawn it again.

**Consequences**: a well-formed digest from a spawn that could not do
the work lands nothing and opens no round. The costs if this is wrong:
a developer that held the tool under another name is re-spawned — the
cure is a name in `REQUIRED_TOOLS`, an edit in the spec-design master,
replicated; and `land --digest` with no file on disk stays what it
was, the orchestrator's attestation — it is not a handshake.
