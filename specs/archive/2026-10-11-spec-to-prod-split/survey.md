# Survey: spec-to-prod-split

**Created**: 2026-10-10 | **Baseline**: 2.0-leap @ `3640b098f3921bc2b54d080a6bc4b36eb3c33aa3`
The survey node's output — the single source of truth for code state. Every citation
in the other four docs must trace to a line here. Evidence is pasted
verbatim from grep/read output in the session that wrote it.

## Items

```
item FR-001: "spec-intent skill invocable alone (survey lens + grilling → intent.md)"
  evidence:   ls skills/ → "spec-brainstorming spec-code-review spec-to-prod" — no spec-intent skill exists.
              Ingredients do exist: agents/scout.md + agents/_lenses.md (ls skills/spec-to-prod/agents/: "_lenses.md _shared-protocol.md builder.md designer.md qa.md reviewer.md scout.md"); the grilling primitive — references/grilling.md:1 "# Grilling — the clarify-pass primitive" and :3 "The model-invoked interview discipline the spec-to-prod clarify node runs (extracted from the playbook, D-039 — one home, invoked by the orchestrator…)".
              No intent.md template: ls skills/spec-to-prod/templates/ → "constitution.md plan.md post-delivery.md release-handoff.md research.md spec-tiny.md spec.md survey.md task.md tech-spec.md test.md".
  status:     TODO
  verify:     ls skills/ (three skills only, pasted above)
  gap:        the entire skill — no skills/spec-intent/, no intent.md artifact, no standalone invocation path; only its two named mechanisms (survey lens, grilling reference) pre-exist inside spec-to-prod.

item FR-002: "intent checker refuses placeholders / open clarify markers / baseline mismatch"
  evidence:   No intent artifact or checker profile exists (templates listing above). All three refusal families pre-exist in scripts/check.py for the current docset — check.py:11 "placeholders, vague plan phrases (TBD, \"handle edge cases\"…)"; tiny_check check.py:599 "in-file contract only — placeholders, open clarify markers, task" and :612 "fails.append(\"spec.md is unfilled or carries template placeholders\")"; clarify markers check.py:1013 "clarify: spec.md still holds open clarify markers but task.md" (marker vocabulary); placeholders check.py:1069 "# 6. leftover template placeholders and vague plan phrases."; baseline check.py:1116 "# 8. survey staleness: baseline hash vs the repo's HEAD" (diagnosis branches :1126–:1203).
  status:     TODO
  verify:     python3 skills/spec-to-prod/tests/test_check.py → "Ran 32 tests in 0.597s / OK" (proves the refusal primitives, not an intent checker)
  gap:        no intent.md contract profile in check.py — the checks exist only for spec.md/task.md/survey.md shapes; nothing refuses a malformed intent artifact.

item FR-003: "spec-shape gated on intent, authoring waves + verify, stop at approve"
  evidence:   No spec-shape skill (ls skills/, above). The authoring waves + verify + approve hard stop all exist in the monolith: scripts/contract.py NODE_TABLE rows — ("survey", "agent", "spec.md done", "survey.md filled AND `check.py <spec-dir> --survey-only` exits 0"), ("plan", "agent", "spec + survey done", "plan.md exists, non-empty, filled"), ("tech", "agent", …); graph.py:156 '("verify", "approve"), ("approve", "execute"),'; graph.py:948 'if n["approve"]["state"] == READY:' / :949 'return "approve", (n["approve"]["reason"]' (a --run judgment stop). No intent node exists — NODE_TABLE's first row is ("spec", "entry", "always (entry node)", …).
  status:     PARTIAL
  verify:     bash skills/spec-to-prod/tests/run.sh → "Ran 12 tests in 1.240s / OK" (includes test_graph.py + test_thin_floor.py over the node table)
  gap:        no standalone spec-shape skill and no intake gate — graph.py has no node that refuses to start when an intent artifact is absent/stale; approve-gating lives only inside the one monolithic run.

item FR-004: "spec-execute refuses non-approved / red check, else waves + delivery + ticks + commit gates"
  evidence:   Gating exists in the monolith: graph.py:147 'APPROVED_AND_LATER = ("approved", "active", "done")'; graph.py:1366 "# -- approve (HUMAN) ---" :1368 'nodes["approve"] = {"state": BLOCKED,' :1371 'nodes["approve"] = {"state": DONE, "reason": f"Status: {status}"},' :1381 'if not approve_done:' :1383 'f"waiting on: approve (spec Status: "'; verify gate graph.py:83 "and the verify node runs `check.py <spec-dir>` — skill-owned contract". Delivery/ticks/commit gates: SKILL.md:616 "proof-and-delivery pass runs after every task in task.md across every" :618 "task in the plan is done and the delivery pass has proven it.** Ticks are"; SKILL.md:693 "The moment execute lands its last task, the tick-commit gate opens. One"; graph.py:157 '("execute", "tick-commit"),'; scripts/tick.py:3 "Ticks `- [ ] T###` entries to `- [x]`, inserts one `done <date> — <proof>`".
  status:     PARTIAL
  verify:     bash skills/spec-to-prod/tests/run.sh → "Ran 12 tests in 1.240s / OK"
  gap:        no standalone spec-execute skill; the refusal is a mid-graph blocked node, not an invocation-time gate on a separately-invocable skill.

item FR-005: "core trio byte-identical in all three skills, pinned by kit parity test"
  evidence:   The parity precedent exists and passes — tools/tests/test_telemetry.py:4 "1. Parity — the module is byte-identical across all three skills (the" :5 "kit's self-contained-packaging duplication, pinned like the workflow" :6 "copies used to be).", :38 "def test_modules_are_byte_identical(self):" :39 "shas = {(REPO_ROOT / "skills" / s / "scripts" / "telemetry.py")" :41 "self.assertEqual(len(shas), 1)". The core trio exists in exactly one skill: ls skills/spec-to-prod/scripts/ → "graph.py specstate.py contract.py telemetry.py check.py …"; ls skills/spec-brainstorming/scripts/ → "check.py skill-dir.sh telemetry.py"; ls skills/spec-code-review/scripts/ → "gate.sh review_orchestrator.py skill-dir.sh telemetry.py" — no second copy to diff. contract.py:3 "One table owns every node's identity, readiness, done-signal, and spawn wiring. `graph.py` imports its READY_WHEN/DONE_WHEN from here"; specstate.py:9 "check.py, audit.py, and graph.py import from this module instead".
  status:     PARTIAL
  verify:     python3 tools/tests/test_telemetry.py → "Ran 7 tests in 0.083s / OK" (proves the parity pattern; no core-trio test exists)
  gap:        no parity test covers graph.py/specstate.py/contract.py (the trio is single-copy today); spec-intent/spec-shape/spec-execute do not exist to hold copies.

item FR-006: "sync.sh installs the three skills + commands to every harness root incl. Kilo native"
  evidence:   The install mechanism is skill-count-agnostic — tools/sync.sh:92 "# A skill opts into this topology just by existing at skills/<name>/ with" :93 "# a SKILL.md — no registration step, no list to edit here."; roots sync.sh:130–134 'SKILLS_ROOTS=( "$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.zcode/skills" "$HOME/.omp/agent/skills"'; Kilo native root sync.sh:57 "-> ~/.config/kilo/skills/<name>/ too" :58 "(OPTIONAL root, gated on ~/.config/kilo" :59 "existing — Kilo's native skills scan"; sync.sh:148 'KILO_HOME="$HOME/.config/kilo"'; D-040 decisions/040-kilo-native-skills-root.md:9 "**Decision**: `tools/sync.sh` installs the full skill tree to `~/.config/kilo/skills/<name>/` — Kilo's DOCUMENTED skills surface".
  status:     PARTIAL
  verify:     python3 tools/tests/test_sync.py → "Ran 32 tests in 50.527s / OK" (includes Kilo gating: test_sync.py:477 'self.assertIn("skip  kilo skills", r.stdout)')
  gap:         skills/spec-intent|spec-shape|spec-execute do not exist, so nothing installs them yet — the topology itself needs no change (opt-in by existing).

item FR-007: "per-skill telemetry events under own name in ~/.spec-dev-kit/telemetry/"
  evidence:   Scheme ships today in all three skills — ls shows scripts/telemetry.py in spec-to-prod, spec-brainstorming, spec-code-review; telemetry.py:6 "JSONL line per event under per-skill telemetry .jsonl file," :55 "def record(skill: str, event: str, **payload) -> None:". The engine already records under its own skill name — graph.py:1097 '_record("spec-to-prod", "gate_pause", node=pause[0],' :1103 '_record("spec-to-prod", "run_end", waves=waves_done,' :1112 '_record("spec-to-prod", "wave", wave=wave,'.
  status:     PARTIAL
  verify:     python3 tools/tests/test_telemetry.py → "Ran 7 tests in 0.083s / OK" (behavior + off-switch + fire-and-forget contracts)
  gap:        no events can exist for spec-intent/spec-shape/spec-execute until those skills ship; the per-skill file naming is already parameterized by the skill argument.

item FR-008: "existing on-disk spec dirs stay valid without migration"
  evidence:   The docset contract is unchanged and enforced — contracts/docset.md present (ls skills/spec-to-prod/contracts/); the canonical existing-dir probe passes: python3 skills/spec-to-prod/scripts/check.py skills/spec-to-prod/examples/mini-spec/specs/mini-spec → "PASS (0 fail, 0 warn)" with "IDs: 2 FR · 0 NFR · 2 AC · 1 US · 2 T · 2 TC · 1 D". check.py's full check is contract-shaped, not provenance-shaped (check.py:13 ".py), survey-baseline staleness, survey.md evidence reality (every" — nothing keys on which skill authored the dir).
  status:     PARTIAL
  verify:     python3 skills/spec-to-prod/scripts/check.py skills/spec-to-prod/examples/mini-spec/specs/mini-spec → PASS (pasted above)
  gap:        "shape and execute accept any dir that satisfies it" is untestable until those skills exist; today only the monolith's graph/check accept the contract.

item FR-009: "spec-to-prod retires same release (sync rows, commands, def installs, marketplace) + one ADR"
  evidence:   Nothing is retired — the monolith is fully live: .claude-plugin/marketplace.json:35 '"name": "spec-to-prod",' :41 '"source": "./skills/spec-to-prod",' (a generate-only surface of tools/plugin-manifest.py); sync.sh installs it implicitly (the :92–93 opt-in rule); its commands + agent briefs install per roots (sync.sh:34 "skills/<name>/agents/*.md -> ~/.claude/agents/ (as-is; the harness"). No retirement ADR: ls skills/spec-to-prod/decisions/ ends "035-one-engine-no-dialects.md 036-five-archetypes-lens-payloads.md 037-thin-floor.md 038-contract-table.md 039-primitives.md 040-kilo-native-skills-root.md" (39 files, none a retirement).
  status:     TODO
  verify:     ls skills/spec-to-prod/decisions/ | tail -3 → "038-contract-table.md 039-primitives.md 040-kilo-native-skills-root.md"
  gap:        the whole retirement — no removal of sync/marketplace/command/def surfaces, no retirement ADR; FR-008 keeps existing dirs valid.

item FR-010: "lifecycle commands move under spec-execute; /spec-to-prod router stays one release as alias"
  evidence:   The objects to move exist and install today: ls skills/spec-to-prod/commands/ → "extra.txt spec-build.md spec-plan.md spec-review.md spec-ship.md spec-test.md spec-to-prod.md spec.md"; commands/extra.txt → "spec spec-plan spec-build spec-test spec-review spec-ship"; the verb router commands/spec-to-prod.md:3 "argument-hint: <scaffold|bugfix|survey|research|plan|tech|tasks|qa|review|check|freeze|converge|graph|run|resume|implement|archive> <spec-name> [T###]". No alias mode, no spec-execute commands dir.
  status:     TODO
  verify:     ls skills/spec-to-prod/commands/ (pasted above)
  gap:        no skills/spec-execute/commands/ to move into; the router is the full monolith router, not a thin alias; no one-release retirement timeline recorded anywhere.

item NFR-001: "no per-skill workflow dialect or engine fork — one engine (graph.py --run)"
  evidence:   Holds today: D-035 decisions/035-one-engine-no-dialects.md:19 "- **Decision**: delete the dialects. `skills/*/workflows/`, `tools/ workflow-defs.py`, `tools/install-workflow.sh`, both `test_workflow_copies.py` suites … are removed; … `graph.py --run` is the one engine on every harness". Confirmed on disk: ls skills/spec-to-prod/workflows skills/spec-brainstorming/workflows skills/spec-code-review/workflows → "ls: skills/spec-to-prod/workflows: No such file or directory" (×3). The one engine: graph.py:69 "--run          the auto-trigger loop: compute the frontier; pause".
  status:     DONE
  verify:     bash skills/spec-to-prod/tests/run.sh → "Ran 12 tests in 1.240s / OK" (engine suite) + the workflow-dir ls above (absent)
  gap:        none today — the FR-005 parity test that enforces it across the future trio is the open FR-005 gap, not a dialect.

item NFR-002: "every divergence lands as its own ADR; split ships one ADR per surface + retirement ADR"
  evidence:   The discipline is live and append-only — specs/CONSTITUTION.md:20 "- **C-05**: decisions are append-only (D-###); nothing rewrites a recorded"; skills/spec-to-prod/decisions/ holds 39 files 001–040 (034 absent from the numbering). No split ADRs exist yet (no decisions file names the split; brainstorms/spec-to-prod-split.md is untracked brainstorm input, not an ADR).
  status:     PARTIAL
  verify:     ls skills/spec-to-prod/decisions/ | wc -l → 39
  gap:        zero of the split's ADRs exist — one per affected surface plus the FR-009 retirement ADR are all still to write.

item NFR-003: "each skill carries its own suite; kit parity suite fails on copy divergence"
  evidence:   Own suites exist and pass: ls skills/spec-to-prod/tests/ → "run.sh test_archive.py test_audit.py test_check.py test_git_degradation.py test_graph.py test_migrate.py test_specstate.py test_thin_floor.py test_tick.py fixtures"; bash skills/spec-to-prod/tests/run.sh → "Ran 12 tests in 1.240s / OK"; bash skills/spec-brainstorming/tests/run.sh → "Ran 10 tests in 0.733s / OK"; bash skills/spec-code-review/tests/run.sh → "Ran 23 tests in 5.999s / OK". The kit-level parity suite covers telemetry.py only (tools/tests/test_telemetry.py:38 test_modules_are_byte_identical); no parity test diffs any core-trio file.
  status:     PARTIAL
  verify:     bash skills/spec-to-prod/tests/run.sh && bash skills/spec-brainstorming/tests/run.sh && bash skills/spec-code-review/tests/run.sh (all OK, pasted above)
  gap:        no kit parity suite entry for graph.py/specstate.py/contract.py copies; no suites exist for the three unbuilt skills.
```

## Supporting evidence

- Telemetry scheme (FR-007 substrate): telemetry.py:37 "SCHEMA = 1",
  :43 'str(Path.home() / ".spec-dev-kit" / "telemetry")))',
  :83 "def summary(skill: str, since: str | None = None) -> str:".
  test_telemetry.py:20–21 'SKILLS = sorted(p.name for p in (REPO_ROOT / "skills").iterdir() if (p / "scripts" / "telemetry.py").exists())' — the
  parity test auto-discovers skills, so a fourth/fifth skill joins the pin
  by existing.
- Install topology (FR-006 substrate): sync.sh:2 "# Sync every skill in
  this repo (master source) to every install root," :5 "# Topology — N
  skills (per skills dir) x the harness roots below:", :152–160
  extra_commands() reads "commands/extra.txt" per skill ("the skill that
  pays for it, and a second skill wanting the same bare" name is refused).
- Def-install tooling is skill-agnostic (FR-006/FR-009 substrate):
  tools/agent-defs.py:3 "Shared, skill-agnostic tool (same contract as
  omp-defs.py): every role under each skill dir's agents/*.md carrying
  Claude-style frontmatter gets a target-dialect twin"; tools/omp-defs.py:6
  "adding a second skill's roles needs no edit here, only a new";
  tools/kit-rules.py:3 "The rules text lives ONCE in
  rules/engineering-rules.md … injected verbatim" into the carrier files.
- Engine/contract/state split (FR-005 substrate): graph.py:178 "Single
  source: scripts/contract.py owns every node's identity," :182 "from
  contract import DONE_WHEN, READY_WHEN  # noqa: E402"; graph.py:127
  "# contractual: CROSS-001 compares them against SKILL.md's table.";
  contract.py --render regenerates SKILL.md's node table (contract.py:8–10),
  drift-pinned by tools/drift-check.py.
- Eval cases for the pipeline (C-10 anchors): skills/spec-to-prod/evals/cases.md
  headers "## E1 — Feature pipeline, small spec (happy path)" (:17), "## E2 —
  Bugfix spec" (:36), "## E3 — Researcher gate, negative branch" (:48),
  "## E4 — Resume mid-implementation" (:59), "## E5 — Single-agent repair
  run" (:71), "## E6 — Delivery pass, red" (:80). No eval case yet names
  spec-intent/spec-shape/spec-execute.
- Baseline tree state: git status shows M AGENTS.md, M tools/sync.sh,
  M skills/spec-to-prod/SKILL.md, M skills/spec-to-prod/commands/*, ?? skills/
  spec-to-prod/decisions/040-kilo-native-skills-root.md, ?? specs/
  spec-to-prod-split/ — the survey cites the working tree, not HEAD alone.
- specs/context/ delta (load-bearing, not rewritten): structure.md:27–28
  still maps "`workflows/` — generated dynamic-workflow dialects
  (regenerate-only; see tools/workflow-defs.py)" and :73 "tools/
  install-workflow.sh (workflows only, per harness)"; tech.md:12–13 "the
  two workflow dialects are TypeScript / JavaScript emitted as text by
  `tools/workflow-defs.py`" and :30 "Install: `tools/sync.sh` (everything),
  `tools/install-workflow.sh`". All those surfaces are deleted per D-035
  (verified absent above) — later docs must not cite context's workflow
  rows.

## Rules
- Every `file:line` pasted from grep/read in this survey — never from memory.
  Can't find it → write `unknown — verify`, don't guess.
- Status derives from evidence, not intent. Run every verify command.
- A number in an old doc is a claim, not evidence — re-count it.
