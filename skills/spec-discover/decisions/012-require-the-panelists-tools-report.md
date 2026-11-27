# D-012: ask every panelist for a tools report, and refuse a digest whose report lacks Read

D-011 pinned the panelist's digest grammar and made the session
validate it before Stage 5 reads a field. It asks what came back, not
what the spawn could do: under omp a spawned subagent's reachable
surface is narrower than its frontmatter (HARNESS-FACTS.md), and a
panelist holding no file reader argues a lens it could not ground.
spec-design D-076 makes the capability handshake a kit-wide rule.

**Decision**:

1. **The reply opens with the report.** The first line of every
   panelist's reply — above the digest — is `tools: <the tools you
   actually hold, comma-separated>`; the rule is stated once in
   `protocol/panel-protocol.md` § Digest only, never edit, the file
   every panelist reads by path.
2. **Read is the one required tool.** `scripts/digests.py`
   `REQUIRED_TOOLS` asks the panelist for Read and nothing more — the
   grammar ignores the `tools:` line, and no other tool voids a
   digest.
3. **The session validates with `--require-tools` and treats exit 3
   as a failed spawn.** `python3 <skill_dir>/scripts/digests.py
   validate panelist <lens> --require-tools`: exit 0 valid, exit 1
   malformed, exit 3 when the `tools:` line lacks Read. A malformed
   digest is a fix and run again; exit 3 is not — no round burns, no
   field is read, and the lens is spawned again on a type or harness
   that holds Read. `contracts/run.md` carries the sentence, pinned by
   `tests/test_digests.py`.

**Consequences**: Stage 5 never maps a dealbreaker or a kill criterion
from a digest a spawn without a file reader wrote. The cost if this is
wrong: a panelist that held Read under another name is re-spawned — a
read-only re-run — and the cure is a name in `REQUIRED_TOOLS`, an
edit in the spec-design master, replicated.
