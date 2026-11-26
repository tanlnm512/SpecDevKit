# D-054: validate every digest against its schema — a malformed digest is refused, never parsed by half

D-040 made the developer's digest file the primary evidence `mark.py
land` reads, and its one parser was a prefix match: six keys were
matched by their first characters, an unrecognized segment was dropped
silently, and `status` was anything up to the next middle dot. A file
that existed but held no parsable line came back as "no digest" — land
then reported "none on file under digests/" for a file that was very
much on file, and offered the `--digest` override as the way forward.
The auditor's line had a second, looser reader in `freeze.py` (a BLOCK
count), and `retro.py` skipped malformed files without counting them.

**Decision** (the schema module and the validate-before-reading rule
are canonical in spec-design's D-074; adopted here in the same words —
this skill's half is the developer and auditor grammars, land's third
state, and the resume and retro readings):

1. **`scripts/digests.py` is the one schema per digest grammar.** The
   developer's and the auditor's line grammars are quoted there as
   data, beside the roles the other skills spawn; the module ships
   byte-identical in every skill whose roles have a digest grammar, and
   `tools/tests/test_parity.py` pins every copy. `validate` returns a
   digest's problems, `parse` its fields only when there are none:
   every key present, in order, no unknown key, every value of its
   kind. A value ends where the next key begins, so free text may hold
   the separator — `deviation scope: a · b` — and a typed value may
   not.
2. **A developer digest file is valid, malformed, or absent.**
   `specstate.latest_digest` keeps its name and reads through the
   schema: the newest file for a task decides, and one that exists
   with no valid digest line for it — an empty file, a missing key, a
   line naming another task — is malformed, carrying its problems and
   its path. It is never again absent.
3. **`mark.py land` refuses a malformed file, exit 1:**
   `refused: malformed digest at <path> — <problems> — fix and run
   again: re-spawn the developer with the same payload to rewrite its
   digest file`. The `--digest` override does not talk over it: a file
   that exists is never talked over (D-040 §3). Absent keeps D-040's
   path, and the override keeps its status-only check — it is the
   orchestrator's attestation, not an agent artifact. `mark.py fail
   --digest` is unchanged.
4. **The resume view and the retro say so.** A malformed file reads
   `digest on file: malformed — fix and run again`; `retro.py` counts
   it as malformed instead of skipping it.
5. **The rule is stated once**, in `protocol/shared-protocol.md`: every
   returned digest is validated before anything is read from it; a
   malformed one is a fix-and-run-again refusal — the problems go back
   to the same agent and the spawn re-runs; it burns no fix round and
   changes no status.

**Consequences**: a developer whose digest drops a field is re-spawned
to rewrite one file rather than landed on a half-read line, and an
empty digest file is named for what it is. The cost if the schema is
wrong — a grammar quoted amiss, or a kind too strict for what the brief
asks agents to write — is a refusal loop on a correct digest: every
developer and auditor literal in `tests/` is valid under the schema
(`tests/test_digests.py`, `tests/test_mark.py`), and a grammar change
is a schema change in the one module.
