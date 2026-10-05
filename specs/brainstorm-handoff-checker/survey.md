# Survey: brainstorm-handoff-checker

**Created**: 2026-10-05 | **Baseline**: current @ 5b73ac078431
The survey node's output — the single source of truth for code state. Every citation
in the other four docs must trace to a line here. Evidence is pasted
verbatim from grep/read output in the session that wrote it.

## Items

```
item FR-001: "Five template sections present and non-empty"
  evidence:   skills/spec-brainstorming/templates/design-spec.md:11 "## Direction"; :21 "## Problem Statement"; :32 "## User Personas"; :43 "## Core MVP Features"; :55 "## Potential Risk Mitigations" · skills/spec-brainstorming/tests/test_flow_contracts.py:33 "TEMPLATE_SECTIONS = [" with the same five headings at :34-:38 · skills/spec-brainstorming/gates/handoff.md:20 "All five template sections present and filled — no template"
  status:     TODO
  verify:     bash skills/spec-brainstorming/tests/run.sh
  gap:        No checker CLI exists — skills/spec-brainstorming/scripts/ contains only skill-dir.sh (ls this session); section presence/non-emptiness is enforced only for the green fixture by tests/test_flow_contracts.py:test_template_pins_the_five_sections_in_order / test_fixture_carries_every_pinned_section
```

```
item FR-002: "Fail surviving template placeholders, naming stem and line"
  evidence:   skills/spec-brainstorming/tests/test_flow_contracts.py:49 "PLACEHOLDER_STEMS = (" :50-:51 '    "<Name>", "<date>", "<persona>", "<angle", "<feature", "<the ", /    "<risk", "<why", "<mitigation", "<the one",' · :158 "for stem in PLACEHOLDER_STEMS:" :159 "self.assertNotIn(stem, text, f\"template placeholder survived: {stem}\")" — fixture-only assertion, no line-number reporting, no CLI
  status:     TODO
  verify:     bash skills/spec-brainstorming/tests/run.sh
  gap:        No standalone checker; pinned stems exist but no code reports a stem with its line number and exits nonzero
```

```
item FR-003: "Direction records selection, rationale, rejected angle with reason"
  evidence:   skills/spec-brainstorming/templates/design-spec.md:15 "- Selected: <angle or blend>" :16 "- Rationale: <why this, in the user's terms>" :17 "- Rejected: <angle> — <the one-line reason it lost>" · gates/handoff.md:22 "**Direction** records the selection AND the rejection with its" :23 "reason, in the user's terms — the panel's favorite is not the" · tests/test_flow_contracts.py:144-146 regexes r"- Selected: .+", r"- Rationale: .+", r"- Rejected: .+ — .+" (run on fixture only)
  status:     TODO
  verify:     bash skills/spec-brainstorming/tests/run.sh
  gap:        Direction-content check exists only as fixture tests, not as a checker over an arbitrary artifact path
```

```
item FR-004: "Numbered feature list + explicit out-of-scope list"
  evidence:   skills/spec-brainstorming/templates/design-spec.md:48 "1. <Feature> — serves <persona>. <The one-line behavior.>" :52 "**Out of scope (day-one cut list)**: <the tempting features this" · skills/spec-brainstorming/SKILL.md:184 "  plus an explicit out-of-scope list."
  status:     TODO
  verify:     rg -n "Out of scope|numbered" skills/spec-brainstorming
  gap:        Template and prose pin the shape; no code validates numbered-list presence or non-empty out-of-scope for arbitrary artifacts
```

```
item FR-005: "Every risk row has early warning + mitigation/acceptance; section states kill criteria"
  evidence:   skills/spec-brainstorming/templates/design-spec.md:61 "| Risk (from the panel) | Early warning | Mitigation or acceptance |" :64 "**Kill criteria**: <the evidence, stated so it could actually be" · gates/handoff.md:25 "Every Cynic dealbreaker from the digest appears in the risk" :28 "Kill criteria are observable: stated so the evidence could" · tests/test_flow_contracts.py:151-152 assertIn("| Risk (from the panel) | Early warning | Mitigation or acceptance |", text) / assertIn("**Kill criteria**", text) (headers only; per-row cell checks do not exist anywhere)
  status:     TODO
  verify:     bash skills/spec-brainstorming/tests/run.sh
  gap:        No per-row cell validation exists even for the fixture; no checker for arbitrary artifacts
```

```
item FR-006: "exit 0 / exit 1 with one line per failed criterion + location"
  evidence:   no checker script exists — ls skills/spec-brainstorming/scripts this session: "skill-dir.sh" only; rg -ln "handoff" over skills/*/scripts and tools returns no matches. Existing exit-code precedents: skills/spec-to-prod/scripts/check.py:1204 "sys.exit(main())"; tools/drift-check.py:218 "sys.exit(main())"
  status:     TODO
  verify:    rg -ln "handoff" skills/spec-brainstorming/scripts tools skills/spec-to-prod/scripts
  gap:        The checker CLI itself — argument parsing, criterion evaluation, failure reporting, exit codes — is entirely missing
```

```
item FR-007: "Operator-named artifact path validated; no brainstorms/ assumption"
  evidence:   skills/spec-brainstorming/contracts/run.md:59-60 "- Default `brainstorms/<name>.md` at the repository root; a / user-named path wins." · skills/spec-brainstorming/SKILL.md:189-190 "Location rules: the default is `brainstorms/<name>.md` at the / repository root; a user-named path wins." · gates/handoff.md:30 "The artifact is at `brainstorms/<name>.md` (or the user-named"
  status:     TODO
  verify:     rg -n "user-named path|Location rules" skills/spec-brainstorming
  gap:        Path rules are documented for the writer agent, not implemented by any validator accepting an explicit path argument
```

```
item NFR-001: "Security — not applicable (file path input only)"
  evidence:   spec item verbatim: "the only input is a repository file path; no network, secrets, or privileged operations" — no implementation exists to audit
  status:     TODO
  verify:     rg -ln "handoff" skills/spec-brainstorming/scripts
  gap:        unknown — verify: confirm at implementation time that no network/secret/privileged call enters the checker
```

```
item NFR-002: "Privacy — not applicable"
  evidence:   spec item verbatim: "no personal or sensitive data is processed beyond the artifact's own content" — no implementation exists to audit
  status:     TODO
  verify:     rg -ln "handoff" skills/spec-brainstorming/scripts
  gap:        unknown — verify at implementation; checker must read only the named artifact
```

```
item NFR-003: "Performance — not applicable (single small markdown file)"
  evidence:   spec item verbatim: "a single small markdown file; no latency-sensitive path" — no implementation exists to audit
  status:     TODO
  verify:     rg -ln "handoff" skills/spec-brainstorming/scripts
  gap:        unknown — verify: single-file read at implementation; no directory walk
```

```
item NFR-004: "Reliability — deterministic, stdlib-only, no environment dependence"
  evidence:   specs/CONSTITUTION.md:22 "- **C-06**: stdlib-only Python, no new runtime dependency without a" · no checker exists to test for determinism
  status:     TODO
  verify:     rg -n "C-06" specs/CONSTITUTION.md
  gap:        Determinism must be proven by the checker's own tests once it exists
```

```
item NFR-005: "Observability — not applicable (green/red CLI is the output surface)"
  evidence:   spec item verbatim: "a green/red CLI answer is the entire output surface" — no implementation exists to audit
  status:     TODO
  verify:     rg -ln "handoff" skills/spec-brainstorming/scripts
  gap:        unknown — verify at implementation that output is limited to pass/fail lines and exit code
```

```
item NFR-006: "Accessibility — not applicable (no interactive UI)"
  evidence:   spec item verbatim: "no interactive or user-facing UI is touched" — no implementation exists to audit
  status:     TODO
  verify:     rg -ln "handoff" skills/spec-brainstorming/scripts
  gap:        unknown — verify: checker must remain non-interactive
```

```
item NFR-007: "Portability — stdlib-only, harness-neutral (C-03, C-06)"
  evidence:   specs/CONSTITUTION.md:15 "- **C-03**: the harness-neutral core (scripts/, briefs, templates) must" :22 "- **C-06**: stdlib-only Python, no new runtime dependency without a" · no checker exists yet
  status:     TODO
  verify:     rg -n "C-03|C-06" specs/CONSTITUTION.md
  gap:        Applies to the checker once written; no code to assess today
```

## Supporting evidence
- Green fixture satisfying the observable gate: skills/spec-brainstorming/examples/decision-tracker/decision-tracker.md:25 "- Selected: Minimalist core + the onboarding-adjacency hook" :29 "- Rejected: Visionary (full platform) — displaces tools the team" :90 "**Out of scope (day-one cut list)**: a server or web UI (v1 is" :102 "| Risk (from the panel) | Early warning | Mitigation or acceptance |" :110 "**Kill criteria**: fewer than ~5 records/week by week three"
- Existing test runner: skills/spec-brainstorming/tests/run.sh runs `for t in tests/test_*.py` — any new test file in that glob is picked up automatically.
- This session's run: `bash skills/spec-brainstorming/tests/run.sh` → exit 0, "Ran 32 tests in 0.014s / OK" (unittest direct run reported 32; run.sh executes the same two test files sequentially).
- Structural-contract precedent CLI: skills/spec-to-prod/scripts/check.py:41-47 usage block including "--survey-only"; check.py:1204 "sys.exit(main())".
- Canonical gate text: gates/handoff.md:19 "## Handoff-readiness criteria (ALL must hold before `/spec` is named)".
- Placeholder stems source of truth lives in test code today (tests/test_flow_contracts.py:49-52), not in the template or a shared constant module — unknown — verify whether FR-002's "pinned placeholder stems" should move to the checker or import-duplicate them.

## Rules
- Every `file:line` pasted from grep/read in this survey — never from memory.
  Can't find it → write `unknown — verify`, don't guess.
- Status derives from evidence, not intent. Run every verify command.
- A number in an old doc is a claim, not evidence — re-count it.
