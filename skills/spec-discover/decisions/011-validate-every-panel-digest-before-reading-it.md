# D-011: validate every panel digest against the pinned grammar before reading it

The digest grammar (`contracts/run.md`, § The digest grammar) was
pinned in prose and read by the session alone: a digest with a field
missing, a lens's extra field in the wrong seat, or one point where
the grammar asks for two was as readable as a good one — and Stage 5
maps dealbreakers and kill criteria from those fields. spec-design
D-074 ships one schema module for every digest grammar.

**Decision**:

1. **The panelist's block is a schema, not prose alone.**
   `scripts/digests.py` carries the grammar quoted from
   `contracts/run.md` — `angle`, `pitch`, `points` (2–3 lines),
   `watch`, plus `kill` for the Cynic and `proof` for the Minimalist —
   shipped byte-identical with the other digest-grammar skills and
   pinned by `tools/tests/test_parity.py`.
2. **Every returned digest is validated before anything is read from
   it**: `python3 <skill_dir>/scripts/digests.py validate panelist
   <visionary | cynic | minimalist>` — exit 0 valid, exit 1 with the
   problems. A field that is missing, unknown, or out of order makes
   the whole digest malformed. A malformed digest is a fix and run
   again: the problems go back to the same panelist and it is
   re-spawned; it burns no round, and no field of it is read.
3. **The rule is stated once**, in `contracts/run.md` beside the
   grammar it governs, with one sentence for the panelist in
   `protocol/panel-protocol.md`; SKILL.md carries a pointer alone.

**Consequences**: a dealbreaker or a kill criterion is never mapped
from a half-shaped digest. The cost if the schema is wrong — stricter
than what a panelist writes for `points:` — is a re-spawned lens, never
a misread digest, and the cure is a schema edit in the spec-design
master, replicated.
