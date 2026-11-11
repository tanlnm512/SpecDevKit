# D-002 — intent.md is a check.py profile, not a second checker

- **Context**: FR-002's three refusal families already exist in
  the one check discipline for the docset — unfilled-template
  placeholders, open clarify markers, baseline-vs-HEAD staleness
  — and the split's spec assumption forbids "a second ungated
  format": an intent-specific sibling script would fork the
  discipline exactly the way NFR-001 forbids forking the engine.
- **Decision**: the intent artifact is validated by a new
  `check.py --intent-only` mode (a sibling of `--survey-only`,
  taking the spec dir) shipped inside the parity set — one more
  profile of the same file, byte-identical across the trio with
  the master at `skills/spec-shape/scripts/`. The profile refuses
  surviving placeholders, open clarify markers (the grilling
  vocabulary, read by the existing marker scan), and a baseline
  that mismatches the repo state it cites; the artifact reuses
  survey.md's `**Baseline**:` header shape so the existing
  staleness diagnosis reads it unchanged. In the full docset
  check, intent.md is an optional input: absent — not checked;
  present — the intent checks run and fail red.
- **Consequences**: FR-002 holds mechanically; serves eval case
  I3 (the stale-baseline refusal) and backs shape's intake gate
  (FR-003, whose exit-0 signal is this profile). One check
  discipline remains the only validation path — a future
  intent-validation desire lands as another profile of check.py,
  never a sibling script. Grown intent-profile cases live in the
  master's and the replicas' `test_check.py` (split D-004's
  regenerate-only discipline).
