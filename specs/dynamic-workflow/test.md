# Test Cases: dynamic-workflow

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-20
Black-box, business-language verification traced to requirements. Each case
has an observable pass condition. No implementation details.

## TC-001 — Regeneration is deterministic and drift-free
- **Story**: US3 · **Traces to**: FR-001, FR-002, FR-006, AC5
- **Given** committed dialect files and the generator
- **When** the generator runs twice and `--check` runs
- **Then** both runs produce byte-identical files and `--check` exits 0
- **Pass condition**: `python3 tools/workflow-defs.py --check; echo exit=$?` prints `exit=0`

## TC-002 — The zcode dialect obeys its runtime's rules
- **Story**: US3 · **Traces to**: FR-001, FR-006
- **Given** the committed `skills/spec-to-prod/workflows/spec-run.dwf.ts`
- **When** the invariant suite inspects it
- **Then** it has the `/* zcode-workflow` metadata block, literal `phase(` names, a `world.run("python3", …)` call, a published run summary, the `__SKILL_DIR__` placeholder, and no `import` / `export` / `declare` token anywhere
- **Pass condition**: `python3 tools/tests/test_workflow_defs.py ZcodeDialectTests` reports OK

## TC-003 — The claude dialect obeys its runtime's rules
- **Story**: US3 · **Traces to**: FR-002, FR-006
- **Given** the committed `skills/spec-to-prod/workflows/spec-run.js`
- **When** the invariant suite inspects it
- **Then** `export const meta` is its first statement, it contains `agent(`, `pipeline(`, `phase(` and a JSON `schema`, no `import` statement, no `Date.now`/`Math.random`, and no shell/file access outside agent prompts
- **Pass condition**: `python3 tools/tests/test_workflow_defs.py ClaudeDialectTests` reports OK

## TC-004 — Both dialects mirror the same loop contract
- **Story**: US1 · **Traces to**: FR-003, AC1, AC2
- **Given** both committed dialect files
- **When** the parity suite checks them
- **Then** each names all six human gates (clarify, research-gate, before-audit, approve, closing-audit, tick-commit), the AWAITING HUMAN stop marker, all five stop conditions, and the same `--state-json` / `--emit-spawns` invocations of graph.py
- **Pass condition**: `python3 tools/tests/test_workflow_defs.py ParityTests` reports OK

## TC-005 — The installer targets each harness separately
- **Story**: US2 · **Traces to**: FR-004, AC3
- **Given** a fake HOME containing `.zcode` and `.claude` skill copies and workflow roots
- **When** `tools/install-workflow.sh all` runs
- **Then** the zcode root holds `spec-run.dwf.ts` and the claude root holds `spec-run.js`, each with the resolved skill_dir baked in and no `__SKILL_DIR__` residue
- **Pass condition**: `python3 tools/tests/test_workflow_defs.py InstallTests.test_all_installs_each_dialect_to_its_own_root` reports OK

## TC-006 — An absent harness is skipped loudly, never fabricated
- **Story**: US2 · **Traces to**: FR-004, AC4
- **Given** a fake HOME with `.claude` present and `.zcode` absent
- **When** `tools/install-workflow.sh zcode` runs
- **Then** it prints a skip line, creates no `~/.zcode`, and exits nonzero
- **Pass condition**: `python3 tools/tests/test_workflow_defs.py InstallTests.test_absent_harness_home_skips_loudly` reports OK

## TC-007 — A foreign destination file is refused, not clobbered
- **Story**: US2 · **Traces to**: FR-004
- **Given** a foreign file already sitting at a workflow destination
- **When** the installer runs for that harness
- **Then** it refuses, the foreign bytes are unchanged, and it exits nonzero
- **Pass condition**: `python3 tools/tests/test_workflow_defs.py InstallTests.test_foreign_destination_refused` reports OK

## TC-008 — Installer --check detects drift and missing installs
- **Story**: US3 · **Traces to**: FR-004, FR-006, AC5
- **Given** an installed copy that was hand-edited (or never installed)
- **When** `tools/install-workflow.sh <harness> --check` runs
- **Then** it reports DRIFT (or missing) and exits nonzero
- **Pass condition**: `python3 tools/tests/test_workflow_defs.py InstallTests.test_check_flags_drift` reports OK

## TC-009 — sync installs and verifies the workflows
- **Story**: US2 · **Traces to**: FR-005
- **Given** a repo copy and fake HOME with both harness homes present
- **When** `bash tools/sync.sh` runs
- **Then** both workflow files are installed with baked skill_dirs and the verify pass reports OK for them (exit 0 overall)
- **Pass condition**: `python3 tools/tests/test_workflow_defs.py InstallTests.test_sync_installs_and_verifies_workflows` reports OK

## TC-010 — The whole tools suite stays green
- **Story**: US3 · **Traces to**: FR-006
- **Given** the repo with the new generator, installer, and tests
- **When** the shared suite runs
- **Then** every tools/tests/test_*.py file passes
- **Pass condition**: `bash tools/tests/run.sh` exits 0

## TC-011 — The documented surface ships together at 2.7.0
- **Story**: US1 · **Traces to**: FR-007
- **Given** the built repo
- **When** the docs release-check runs
- **Then** SKILL.md has the dynamic-workflow run section, README's harness table and install list mention it, `skills/spec-to-prod/decisions/019-dynamic-workflow-dialects.md` exists, CHANGELOG's top entry is 2.7.0, and VERSION says 2.7.0
- **Pass condition**: `test "$(cat skills/spec-to-prod/VERSION)" = "2.7.0" && grep -q "Dynamic workflow runs" skills/spec-to-prod/SKILL.md && test -f skills/spec-to-prod/decisions/019-dynamic-workflow-dialects.md && grep -q "## 2.7.0" skills/spec-to-prod/CHANGELOG.md`

## TC-012 — First live run on each harness (human observation)
- **Story**: US1 · **Traces to**: FR-001, FR-002, FR-003, AC1, AC2
- **Given** the installed workflow on zcode and on Claude Code, and a scratch spec with a ready wave
- **When** the workflow runs with the spec name
- **Then** the wave spawns with a visible phase view, and at the next judgment gate the run stops with an AWAITING HUMAN message naming the gate
- **Pass condition**: manual — observe the run view and the gate stop on each harness; record both observations here when done

## Coverage matrix
<!-- Every FR appears; `check.py` fails an FR with no TC. -->
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001      | TC-001, TC-002, TC-012 | auto + manual |
| FR-002      | TC-001, TC-003, TC-012 | auto + manual |
| FR-003      | TC-004, TC-012 | auto + manual |
| FR-004      | TC-005, TC-006, TC-007, TC-008 | auto |
| FR-005      | TC-009 | auto |
| FR-006      | TC-001, TC-008, TC-010 | auto |
| FR-007      | TC-011 | auto |
