# Eval cases — spec-shape

The authoring phase's standing eval scenarios. Mechanics — the
intake gate's refusal families, the span bounds — are proven by the
skill's own `tests/run.sh`; these prove the *authoring orchestration*
works: the gated intake, the survey → plan ∥ tech ∥ qa → tasks waves,
verify, and the hard stop at the approve handoff with zero execution.
The E1–E3/E7 classes moved here from spec-to-prod's corpus with the
split (the resume/repair/delivery classes moved to spec-execute's);
bodies bound to the shape span. Corpus lineage, kept from the
monolith's retired pointer: the orchestration was validated live
end-to-end against the graph workflow in the 1.7.0 mission (two full
pipeline runs, evidence in that mission's validation dir) — history
moves, never deletes.

Judging: run the case in a scratch repo, transcript + `specs/` output
against the criteria. A criterion failed = a finding with the transcript
line; aggregate findings per case, don't average. Frontier terms per
SKILL.md: `graph.py` (report or `--state-json`) is consulted before and
after every wave and gate action, and the captured snapshot sequence is
part of the evidence — the frontier is the only scheduler being judged.

## E1 — Feature authoring, small spec (happy path)

- **Setup**: scratch repo with a real test runner and a validated
  `specs/<name>/intent.md` (a /spec-intent run or a planted green
  artifact); ask: "shape <small feature, 2–3 FRs>" via
  `/spec-gen <feature>`.
- **Pass criteria**: the intake gate passes (intent node DONE on
  entry); the frontier is correct at every step (`--state-json`
  snapshots before/after each action): survey as a solo analysis wave
  in ONE message, then plan ∥ tech ∥ qa in ONE message (qa spawned
  implementation-blind), then tasks; `check.py` verify runs mechanically
  and its failures route to the responsible agent, never a wave redo;
  the run stops at the approve handoff (`span drained — approve
  handoff` / `AWAITING HUMAN: approve`) BEFORE any implementer exists —
  no execute-node payload is ever written; every digest matches its
  brief's shape; graph.py never auto-satisfies a gate.
- **Run**: session: scratch repo per **Setup**; run the authoring span in a session; judge the `--state-json` snapshot sequence and docs against the pass criteria above

## E2 — Bugfix spec

- **Setup**: scratch repo with a planted bug + its test suite and a
  validated intent; ask: "shape this bug" (bugfix deltas).
- **Pass criteria**: bug narrative + unchanged-behavior FRs in spec.md;
  researcher gated off (skip marker in research.md — zero research
  spawns); the repro test runs red inside plan.md's first phase — the
  regression milestone — planned before any fix work is tasked; one
  regression TC per unchanged FR; the run stops at the approve handoff
  with no fix implemented (execution is /spec-execute's).
- **Run**: session: scratch repo with a planted bug per **Setup**; run the bugfix authoring span in a session; judge against the pass criteria above

## E3 — Researcher gate, negative branch

- **Setup**: feature whose approach is already obvious (single
  known-pattern internal change), validated intent.
- **Pass criteria**: zero spawns beyond the needed waves; research.md
  contains the exact `not applicable — no open questions at Stage 0`
  line; no manufactured research questions; the analysis wave is a solo
  surveyor (`--state-json`: research skipped via the marker, tech READY
  on the either-form resolution); under `--span shape` the researcher
  never runs even when the gate is revisited.
- **Run**: session: feature whose approach is obvious per **Setup**; run the authoring span in a session; judge the gate's skip branch against the pass criteria above

## E7 — Thin floor: one-file contract to the approve handoff

- **Setup**: `scaffold.sh --tier tiny demo` (the default); fill
  spec.md (What/Why/ACs/FR-001 + two § Tasks entries with Touches and
  Accept lines); no intent.md (the FR-008 legacy path).
- **Pass criteria**: the intent-absent path passes the intake gate
  (SKIPPED, not BLOCKED); `check.py` passes in tiny mode (task grammar,
  FR citations, proof-note ticks enforced); `graph.py` shows
  survey/plan/tech/qa/tasks SKIPPED with `tier: tiny` reasons and
  verify done from spec.md alone; the span stops at the approve
  handoff with no authoring spawn ever made; `migrate.py grow` moves
  both blocks verbatim into task.md Phase 1 with ids preserved, Tier
  flips to full, and the authoring nodes are READY again. A docset
  with no Tier header behaves exactly as before (no "tier: tiny"
  anywhere in its graph).
- **Run**: session: the thin-floor suite (`tests/`, the mechanical half) plus a real small fix authored end-to-end at tiny tier to the approve handoff and judged against the pass criteria above
