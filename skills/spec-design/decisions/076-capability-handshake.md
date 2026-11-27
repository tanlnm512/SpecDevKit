# D-076: ask every spawned role for a tools report, and refuse one that lacks a required tool

D-074 gave every digest a schema and D-075 recorded who produced it;
neither asks what the spawn could do. HARNESS-FACTS.md records it for
omp — a spawned subagent's reachable surface is narrower than its
frontmatter — and the kit leans on the frontmatter everywhere else,
because nothing in it knows which tools a spawn really holds. A
degraded agent returns a degraded result: a tech lens with no file
writer returns a digest for an artifact it never wrote, a developer
with no shell returns `implemented` for acceptance commands it never
ran, and both read exactly like good evidence.

**Decision** (canonical for the kit; adopted in spec-build D-056,
spec-define D-025, spec-discover D-012, spec-ship D-009, spec-release
D-007 and spec-review D-029):

1. **Every payload's first instruction asks for the report.** After
   the header facts and before the input: the first line of the reply
   — and of the digest file, above the `digest:` line — is `tools: <the
   tools you actually hold, comma-separated>`. The rule is stated once
   in `protocol/shared-protocol.md`, the trio's byte-shared carrier
   (report what you hold, never what you were told you hold; a tool
   you cannot see is absent); `graph.py` adds the ask to the payload
   and never a second copy of the rule — which is how it reaches the
   auditor too, whose payload carries no protocol.
2. **Required tools are data, per role.** `REQUIRED_TOOLS` in
   `scripts/digests.py` is the least a role needs to do its job at all,
   quoted from its brief's frontmatter and body: analyst, architect and
   tester need a file writer (Write or Edit), the developer Bash as
   well, and auditor, panelist, integrator and release-manager need
   Read. Nothing else is required — a missing WebSearch degrades
   research, it does not void the artifact. `tools_report` reads the
   first `tools:` line; every grammar ignores that line; a name matches
   whatever its case.
3. **The orchestrator refuses, and it is not a fix round.** A
   handshake failure is a failed spawn — the kit's "a spawn that did
   not answer" class (spec-build D-049): no round opens, the work is
   released or left claimed, and the remedy is "spawn again on a type
   or harness that holds `<tool>`". The refusal names the role, what
   it reported, and what was required.
   - The provenance sweep: an analyst, architect or tester digest
     file whose report lacks a required tool gets no provenance line
     and nothing reads its digest — one `capability_missing` row per
     content, the refusal printed.
   - `digests.py validate --require-tools`: exit 3 when the `tools:`
     line lacks a required tool (exit 1 stays malformed); every skill
     whose digest comes back in conversation tells its orchestrator to
     run it with that flag and to treat exit 3 as a failed spawn.
   - The contract review: the live `--review` payload's last `tools:`
     line above the last digest must hold Read, or the review is
     refused. The signed record folds the digest line as before and
     verifies without one.
   - The developer's file is `mark.py land`'s to refuse (spec-build
     D-056).
4. **The report is recorded as a claim.** The reported set rides the
   provenance line and the ledger row as `tools-reported` — what the
   agent said it held, labelled as such; never a fact the kit asserts.

**Consequences**: a spawn that cannot see a tool it needs is refused
before anything it returned is read. The costs if this is wrong: a
tool the harness names otherwise (`shell` for `Bash`) is refused as
absent — the cure is a name in `REQUIRED_TOOLS`, an edit in this
master, replicated; a digest file written before this decision carries
no report and is refused on its next read — the spawn re-runs; a kit
older than this decision reads the nine-field provenance line as
unvouched; and the handshake catches a spawn that cannot see a tool,
not one that sees it and uses it badly — whether a role can see and
name its own tools at all stays an open assumption in
HARNESS-FACTS.md.
