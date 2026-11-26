# D-024 — every returned digest is validated against its schema before it is read

- **Context**: the analyst's digest had a grammar in prose — the intent
  lens in `protocol/lenses.md` — and no reader that checked it: a
  digest with a field missing or mistyped was as readable as a good
  one, and its counts were taken as evidence. spec-design D-074 ships
  one schema module for every digest grammar, replicated into this
  skill's `scripts/` by `tools/parity.py` and pinned byte-identical by
  `tools/tests/test_parity.py`.
- **Decision**: adopt spec-design D-074's rule. The orchestrator
  validates every returned digest against its schema before anything
  is read from it — `python3 <skill_dir>/scripts/digests.py validate
  analyst intent`: exit 0 valid, exit 1 with the problems. A malformed
  digest is a fix and run again: the problems go back to the same
  analyst and the spawn re-runs; it burns no round, opens no question,
  and no count is read from it. The rule is stated once in
  `protocol/shared-protocol.md`, the trio's byte-shared carrier;
  SKILL.md carries a pointer alone. The intent grammar itself is
  unchanged — `tests/test_digests.py` quotes it from the lens section.
- **Consequences**: an intent digest with a dropped or mistyped field
  is re-run rather than counted by half. Cost if wrong: a schema
  stricter than the brief's analysts write re-runs correct digests, and
  the cure is a schema edit in the spec-design master, replicated.
