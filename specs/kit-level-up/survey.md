# Survey: kit-level-up

**Created**: 2026-10-04 | **Baseline**: worktree @ 3cfc8f1
(first survey; payload baseline: none recorded. Working tree at survey time: `brainstorms/`
and `specs/kit-level-up/` untracked, `specs/INDEX.md` modified — the spec and brainstorm
this survey reads are themselves uncommitted. Baseline recorded as the short sha the
graph's converge probe compares against; full sha `3cfc8f1b0bcbc80360fa565872fc7fdb012e804d`.)
The survey node's output — the single source of truth for code state. Every citation
in the other four docs must trace to a line here. Evidence is pasted
verbatim from grep/read output in the session that wrote it.

## Items

```
item FR-001: "run every in-scope eval case live once, file transcript + per-criterion verdicts at `<skill>/evals/results/<date>-<case>.md`"
  evidence:   the three case files exist with 15 case headings total:
              `skills/spec-code-review/evals/cases.md:12` E1, `:21` E2, `:34` E3, `:44` E4
              `skills/spec-brainstorming/evals/cases.md:14` B1, `:26` B2, `:39` B3, `:52` B4, `:64` B5
              `skills/spec-to-prod/evals/cases.md:17` E1, `:35` E2, `:46` E3, `:56` E4, `:67` E5, `:75` E6
              no results transcript exists anywhere: `find skills -type f -path '*evals/results/*' | wc -l` → 0
              the `<skill>/evals/results/` convention is named only by this spec (specs/kit-level-up/spec.md:108),
              by no skill doc
  status:     TODO
  verify:     find skills -type f -path '*evals/results/*' | wc -l
  gap:        zero live runs filed; also FR-001's in-scope set names "the spec-to-prod
              pipeline case" (spec.md:108-111, one case) while the case file holds six
              standing cases (E1–E6) — the in-scope count is unresolved against the case
              inventory; unknown — verify which spec-to-prod cases are in scope
item FR-002: "failed criterion records criterion + transcript evidence + finding; never average"
  evidence:   the judging rule the FR relies on is already stated verbatim in all three case files:
              skills/spec-code-review/evals/cases.md:9-10 — "a failed criterion is a finding
              naming the report line. Never average — aggregate."
              skills/spec-brainstorming/evals/cases.md:11-12 — "a failed criterion is a finding
              naming the moment it broke. Never average — aggregate."
              skills/spec-to-prod/evals/cases.md:11-12 — "A criterion failed = a finding with
              the transcript line; aggregate findings per case, don't average."
              no results file exists to carry any verdict (FR-001 evidence: find count 0)
  status:     TODO
  verify:     rg -n "Never average|don't average" skills/spec-code-review/evals/cases.md skills/spec-brainstorming/evals/cases.md skills/spec-to-prod/evals/cases.md
  gap:        the results-file recording behavior does not exist; only the stated judging
              rule (the FR's premise) is on disk
item FR-003: "unmeetable case records the contract bent as a kill-criterion finding — no silent workaround"
  evidence:   the brainstorm's kill criteria already state the fixture-only fallback:
              brainstorms/kit-level-up.md:125-129 — "Kill criteria: (1) an eval case cannot
              complete on a real repository inside the skill's own contracts without
              improvisation — the self-proving thesis is dead; record the failure, fall
              back to fixture-only evals, re-scope to the axes directly."
              the E2 mechanical fixture exists: skills/spec-code-review/examples/review-target/
              contains EXPECTED.md, README.md, base/, change.diff (ls output)
              no run has recorded a contract bent (results-file count 0, FR-001 evidence)
  status:     TODO
  verify:     rg -n "Kill criteria" brainstorms/kit-level-up.md && ls skills/spec-code-review/examples/review-target/
  gap:        no run exists to exercise the kill path; the recording behavior is unbuilt
item FR-004: "stdlib-only runner at tools/evals.py: list / execute mechanical case / record / exit nonzero on failure"
  evidence:   ls: tools/evals.py: No such file or directory
              tools/ inventory (ls output): agent-defs.py, drift-check.py, install-workflow.sh,
              kit-rules.py, omp-defs.py, ownership.py, plugin-manifest.py, sync.sh, tests/,
              workflow-defs.py — no evals runner among them
  status:     TODO
  verify:     test ! -e tools/evals.py && echo absent
  gap:        the runner does not exist; no test references any eval runner (rg "cases.md"
              across skills/*/tests/ and tools/ → no match)
item FR-005: "conversational case: print session procedure; validate+record an existing transcript"
  evidence:   tools/evals.py does not exist (FR-004 evidence); no validate/record mode exists
              anywhere under tools/
  status:     TODO
  verify:     ls tools/evals.py
  gap:        both modes (print-procedure, validate-and-record) are unbuilt with their carrier
item FR-006: "each in-scope case file carries a Run: line naming its execution procedure"
  evidence:   rg -n '^.*Run:' skills/spec-code-review/evals/cases.md
              skills/spec-brainstorming/evals/cases.md skills/spec-to-prod/evals/cases.md
              → no match (exit 1); the case files name Setup/Ask/Pass criteria only
  status:     TODO
  verify:     rg -n "Run:" skills/spec-code-review/evals/cases.md skills/spec-brainstorming/evals/cases.md skills/spec-to-prod/evals/cases.md
  gap:        no case file carries a Run: line — 15 cases would need one added (16 counting
              spec-to-prod E1–E6 if all are in scope, see FR-001 gap)
item FR-007: "constitution article C-10 (scoping rule) + one AGENTS.md pointer line"
  evidence:   specs/CONSTITUTION.md ends at C-09 — article list spans
              specs/CONSTITUTION.md:10 (C-01) through specs/CONSTITUTION.md:31-32 (C-09)
              rg -n "C-10" specs/CONSTITUTION.md AGENTS.md → no match (exit 1)
              AGENTS.md:54 documents the current article range: "specs/CONSTITUTION.md —
              articles C-01…C-09" — the line a pointer would sit beside
  status:     TODO
  verify:     rg -n "C-10" specs/CONSTITUTION.md AGENTS.md
  gap:        neither the article nor the pointer line exists
item FR-008: "phase-0 baseline verdict roll-up (per skill: run/passed/failed/contract-bent) in the delivery summary"
  evidence:   specs/kit-level-up/task.md:6 — "**Delivered**: pending — delivery evidence; the
              orchestrator writes `commit @ <sha>` here"; no delivery summary or roll-up
              exists in spec.md (rg "Delivery summary" → no match)
  status:     TODO
  verify:     rg -n "Delivered" specs/kit-level-up/task.md
  gap:        no baseline pass has run, so no roll-up number exists to record
item NFR-001: "Security — not applicable"
  evidence:   spec.md:145-147 declares it not applicable; no network surface exists in the
              repo tooling or skill scripts today: rg -n "urlopen|import socket|import requests"
              tools/*.py skills/*/scripts/*.py → no match (exit 1)
  status:     DONE
  verify:     rg -n "urlopen|import socket|import requests" tools/agent-defs.py tools/drift-check.py tools/kit-rules.py tools/omp-defs.py tools/ownership.py tools/plugin-manifest.py tools/workflow-defs.py
  gap:        none — N/A per spec; nothing to build (re-check when tools/evals.py lands)
item NFR-002: "Privacy — not applicable"
  evidence:   spec.md:148-150 declares it not applicable; no telemetry/upload path exists:
              rg -in "telemetry|upload" tools/*.py skills/*/scripts/*.py → no match (exit 1)
  status:     DONE
  verify:     rg -in "telemetry|upload" tools/agent-defs.py tools/drift-check.py tools/kit-rules.py tools/omp-defs.py tools/ownership.py tools/plugin-manifest.py tools/workflow-defs.py
  gap:        none — N/A per spec; transcripts will be local markdown files only
item NFR-003: "runner lists all cases in under a second, no agent spawned"
  evidence:   tools/evals.py does not exist (FR-004 evidence); the listing path is unbuilt
  status:     TODO
  verify:     test ! -e tools/evals.py && echo absent
  gap:        nothing to time yet; a listing-path implementation is the missing piece
item NFR-004: "failed execution leaves prior results files intact, exits nonzero"
  evidence:   no runner and no results files exist (FR-001/FR-004 evidence) — nothing can
              clobber or exit yet
  status:     TODO
  verify:     ls tools/evals.py
  gap:        the write-then-commit results-file discipline is unbuilt with the runner
item NFR-005: "every runner execution prints case, verdicts, results path"
  evidence:   tools/evals.py does not exist (FR-004 evidence); no console-receipt behavior exists
  status:     TODO
  verify:     ls tools/evals.py
  gap:        the print-receipt path is unbuilt with the runner
item NFR-006: "Accessibility — not applicable"
  evidence:   spec.md:162-163 declares it not applicable; the touched surfaces are CLI scripts
              and markdown only — no UI toolkit anywhere: rg -in "tkinter|pyqt|electron"
              tools/*.py skills/*/scripts/*.py → no match (exit 1)
  status:     DONE
  verify:     rg -in "tkinter|pyqt|electron" tools/agent-defs.py tools/drift-check.py tools/kit-rules.py tools/omp-defs.py tools/ownership.py tools/plugin-manifest.py tools/workflow-defs.py
  gap:        none — N/A per spec
```

## Supporting evidence

**Case inventory (re-counted from the files, not from the spec's claims)** — 15 standing
case headings across three files: spec-code-review E1–E4 (4), spec-brainstorming B1–B5 (5),
spec-to-prod E1–E6 (6). The spec's in-scope set (spec.md:106-111) says "all spec-code-review
cases (E1–E4)" and "all spec-brainstorming cases (B1–B5)" — both match the files — but names
only one spec-to-prod "pipeline case" against six on disk. Spec-to-prod cases.md:17-84 heads:
E1 happy path, E2 bugfix, E3 researcher-gate negative, E4 resume, E5 single-agent repair,
E6 delivery-pass red.

**Judging rule** — stated per case file (verbatim under FR-002). The spec-to-prod file adds
that `graph.py` snapshots are part of the evidence: skills/spec-to-prod/evals/cases.md:12-15
— "the captured snapshot sequence is part of the evidence — the frontier is the only
scheduler being judged."

**Kill criteria + fixture** — brainstorms/kit-level-up.md:125-131 states all three kill
criteria (unmeetable case → fixture-only fallback; two increments without a served case →
stop; clean baseline → success ending). The mechanical fixture for the cheapest in-scope
case (spec-code-review E2) exists at skills/spec-code-review/examples/review-target/
(EXPECTED.md, README.md, base/, change.diff). The base/ subtree carries untracked
`__pycache__/` debris (not in git — `git ls-files ... | rg __pycache__` → no match).

**Runner absence** — tools/ holds ten entries (ls output under FR-004), none an eval runner;
no test file in skills/*/tests/ or tools/tests/ references cases.md (rg → no match), so no
existing suite pins eval-case content.

**Eval surfaces are drift-unguarded** — tools/drift-check.py and tools/ownership.py mention
neither "evals" nor "cases.md" (rg → no match, exit 1): the case files are not a guarded
generated surface today.

**Surveyor self-check machinery exists** — the skill's checker has the survey-only mode this
survey ran: skills/spec-to-prod/scripts/check.py:survey_only_check:278, selected by the
`--survey-only` argv flag (check.py:252), with the citation-reality contract documented at
check.py:162-166.

**Constitution + AGENTS.md state** — articles C-01…C-09 (specs/CONSTITUTION.md:10-32;
rationale 34-53); AGENTS.md:54 summarizes the same range for agents. No C-10 anywhere.

**1.7.0 pipeline-evidence claim, re-counted** — skills/spec-to-prod/evals/cases.md:3-4
claims the orchestration was "validated live end-to-end ... in the 1.7.0 mission (two full
pipeline runs, evidence in that mission's validation dir)". Re-count in this session: no
path matching `*1.7.0*` exists in the working tree (`find . -iname "*1.7.0*" -not -path
"./.git/*"` → no match), no commit message mentions 1.7.0 (`git log --oneline | rg -i
"1\.7\.0"` → no match), and skills/spec-to-prod/CHANGELOG.md:721 carries only the release
line "## 1.7.0 — 2026-09-09". The mission's validation evidence is not findable in-tree —
unknown — verify (supports the spec's own "zero live runs in evidence" premise).

## Rules
- Every `file:line` pasted from grep/read in this survey — never from memory.
  Can't find it → write `unknown — verify`, don't guess.
- Status derives from evidence, not intent. Run every verify command.
- A number in an old doc is a claim, not evidence — re-count it.
