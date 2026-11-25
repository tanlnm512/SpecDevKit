# Kit hardening plan — skills, agents, and the anonymous-agent SDLC

Source: a review of the seven `SKILL.md` files and thirteen agent
briefs (definition quality), then a gap analysis for running the kit
with anonymous agents — interchangeable, stateless, of unknown model
and harness, whose output is trusted for what can be checked, never
for who produced it.

Every item that changes a doc contract lands with its own D-### in
the owning skill's `decisions/` (C-05). Generated surfaces are edited
at their source and regenerated (`tools/agent-defs.py`,
`tools/kit-rules.py`, `tools/plugin-manifest.py`). Done for every
item means: all seven skill suites, `tools/tests/run.sh`, and
`python3 tools/drift-check.py` green.

## Phase 1 — Fix what the definitions promise but do not do (small, mechanical)

### 1.1 Wire the round-4 model escalation
- **Gap**: `agents/developer.md` pins `model: sonnet`; `mark.py` prints
  `round 4: spawn one tier up`, but no payload carries a model, so a
  `--native-agents` spawn runs on the frontmatter model.
- **Do**: `graph.py --emit-spawns` writes a `Model:` line (and the
  emit line names it) on a round-4 payload; SKILL.md § Fix rounds says
  how to honor it per harness (spawn-time override, or general agent).
- **Accept**: a test emits a round-4 payload and asserts the line;
  `HARNESS-FACTS.md` gains an assumption row per harness that cannot
  override a registered agent's model.

### 1.2 Make the fix-cap arithmetic say one thing
- **Gap**: "at most 5 per task" (`rules/agent-limits.md`), but round 4
  failing writes `(fix 5/5)` and the engine never re-spawns — four
  attempts run.
- **Do**: pick one — "4 attempts; `5/5` is the stop marker" in the
  budget text, or let round 5 run. Update `agent-limits.md`, spec-build
  SKILL.md, `mark.py` docstring together.
- **Accept**: wording and `graph.FIX_CAP` behavior agree; a test pins
  the number of spawns before the cap stop.

### 1.3 Disambiguate "tier"
- **Gap**: `Tier: tiny|full` (spec size) and "capability tier" (model
  strength) share a word.
- **Do**: rename the model sense (e.g. "model step") in briefs,
  SKILL.md, `mark.py` output; add both terms to `GLOSSARY.md`.

### 1.4 Namespace the review agents
- **Gap**: `review-correctness|security|quality|scout|fixer` lack the
  `spec-` prefix every other agent carries; generic names collide with
  other plugins' agents.
- **Do**: rename to `spec-review-*` in `skills/spec-review/agents/`,
  the oracle's role table, `commands/`, and regenerate root `agents/`.
- **Accept**: parity and drift checks green; sync's ledger removes the
  old installed names (verify with `bash tools/sync.sh --check`).

### 1.5 Declare or drop optional external skills
- **Gap**: briefs reference skills the kit does not ship —
  `paper-fetch`, `semanticscholar` (analyst), `browser-use:web-gui-tester`,
  `agent-native-design` (tester).
- **Do**: list them as optional integrations in `HARNESS-FACTS.md`
  (open assumptions) with a fallback stated in the brief, or remove.

### 1.6 Trim skill descriptions
- **Gap**: descriptions load into every session; spec-release 938,
  spec-discover 835, spec-ship 814 chars against the 1024 loader cap.
- **Do**: reduce each to trigger phrases + the "not for" boundary,
  target ≤ 600 chars; add a drift-check warning above that budget.

## Phase 2 — Close the trust gaps (highest risk)

### 2.1 Approval only a human can grant
- **Gap**: approval is `approvals/approval.md` + `Status: approved`;
  any write-capable agent can author both, and `freeze.py --by` takes a
  free-text name. The approve gate is only as strong as its writer.
- **Do**:
  1. A generated PreToolUse hook (per harness, under `tools/`, C-03)
     denying spawned agents writes to `specs/**/approvals/**` and to
     `Status:` lines.
  2. Bind the record to something agents cannot forge: `freeze.py`
     records the approving human's commit identity / signed commit, or
     verifies a PR approval; `check.py` and spec-build's invocation gate
     reject a record without it.
  3. Recommend CODEOWNERS on `specs/**/approvals/` in the scaffold.
- **Accept**: a test where a simulated agent-written approval is
  refused by spec-build's gate (exit 4).

### 2.2 Enforce read-only and blindness mechanically
- **Gap**: the four `review-*` readers hold `Bash`, so "read-only" is
  prose; the tester's blindness to tech-spec/plan/task is "enforced
  only by you".
- **Do**: give readers the diff as a file (as the auditor already gets
  `reviewer-diff.patch`) and drop `Bash`, or keep it behind a hook that
  denies mutating commands; a hook denying the tester `Read` on
  `tech-spec.md|plan.md|task.md`.
- **Accept**: generated defs/hooks tested per harness that supports
  them; unsupported harnesses listed in `HARNESS-FACTS.md`.

### 2.3 Brief the spec-review roles that carry independence
- **Gap**: triage editor, confirmer, fix verifier, and fresh-eyes fix
  reviewer exist only in `contracts/` — no agent def, so no
  tool restriction and no parity pin.
- **Do**: add `spec-review-confirmer.md` and `spec-review-verifier.md`
  (read-only tools); the oracle's asks point at them.

### 2.4 Provenance ledger
- **Gap**: no record of which role, model, harness, and payload
  produced an artifact — outputs cannot be audited, reproduced, or
  compared across models.
- **Do**: every digest file carries a provenance line (role, lens,
  model, harness, payload sha, input fingerprint, run id); an
  append-only `specs/<name>/runs/` ledger written by the orchestrator
  scripts, never by agents.

### 2.5 Strict digest validation
- **Gap**: `mark.py` reads a digest's status; the rest of each grammar
  is loosely parsed.
- **Do**: one schema per digest grammar (developer, architect, tester,
  analyst, auditor, panelist, integrator, release-manager); a malformed
  digest is a "fix and run again" refusal, never half-parsed.

### 2.6 Capability handshake
- **Gap**: a spawned agent's real tool surface can be narrower than
  its def (recorded for omp); a degraded agent returns a degraded result.
- **Do**: the payload asks for a first-line `tools:` report; the
  orchestrator refuses on a missing required tool.

## Phase 3 — Coordination across agents and specs

### 3.1 Cross-spec claim registry
- **Gap**: `Touches:` overlap is checked within one spec only; two specs
  executing at once can edit the same files.
- **Do**: `mark.py claim` checks and writes a repo-level registry
  (e.g. `specs/.claims`) under a lock; overlap defers the task.

### 3.2 Optional worktree-per-task execution
- **Gap**: wave-mates share one working tree (hence the brief's ban on
  `git stash/reset/checkout`); a bad agent's work is hard to discard.
- **Do**: opt-in `--isolate worktree` — each task in its own worktree,
  merged by the orchestrator on land, dropped on release.

### 3.3 Run budgets for unattended spans
- **Gap**: telemetry counts events only; no ceiling on an unattended
  execute run.
- **Do**: per-run and per-spec limits (spawns, wall-clock, tokens where
  the harness reports them) that park `AWAITING HUMAN`.

## Phase 4 — Prompt weight and drift surface

### 4.1 Slim the large SKILL.md bodies
- **Gap**: spec-build (405 lines) and spec-review (337) restate the
  contracts they say arbitrate, and cite ADR numbers (9 and 8) the
  executing model cannot act on.
- **Do**: SKILL.md keeps entry gate, happy path, pointers; edge cases
  (resume, cap adjudication, marker table) move to `contracts/`, read
  on demand; drop inline D-### references from instructions.
- **Accept**: live evals in `evals/cases.md` re-recorded green.

### 4.2 Normalize `rules/engineering-rules.md` formatting
- § Refusals and failed calls uses unwrapped long lines unlike the
  rest; rewrap and regenerate the carriers.

## Phase 5 — SDLC coverage

| Item | New surface | Feeds |
|---|---|---|
| 5.1 `/spec` status router | one command reading graph/ship/release state, naming the next skill | all |
| 5.2 Async human gates | gate preview posted as a PR/issue comment; resume on a verified approval (builds on 2.1) | approve, tick-commit, ship, release |
| 5.3 `spec-incident` | alert/log/postmortem → hotfix `intent.md` with evidence attached | spec-define |
| 5.4 Maintenance flow | dependency/CVE audit output → `Type: upgrade` intents | spec-define |
| 5.5 `spec-triage` | rank, merge, promote `BACKLOG.md` parked items | spec-define / spec-discover |
| 5.6 Routing evals | cases where similar wording must land in different skills (discover vs define vs design) | descriptions (1.6) |

## Phase 6 — Learning loop

### 6.1 Repo lessons injected into payloads
- `retro.py` proposes entries to `specs/LESSONS.md`; a human accepts
  them at a gate; payloads carry the accepted lessons through the same
  injection path `kit-rules.py` uses.

### 6.2 Per-role, per-model scorecard
- From the provenance ledger (2.4): fix-round rate, BLOCK rate,
  pending-proof rate by role and model — the evidence for model
  choice per role and for the escalation in 1.1.

## Order

1. Phase 1 (one PR, mechanical).
2. 2.1 approval hardening — the gap that lets an agent unlock execution.
3. 2.4 + 2.5 provenance and digest validation; then 2.2, 2.3, 2.6.
4. Phase 3, then 4.1.
5. Phases 5 and 6 — each new skill enters through `/spec-discover` or
   `/spec-define`.
