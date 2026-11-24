# GLOSSARY — the kit's shared language

One term, one meaning. Use these words exactly in briefs, SKILL.md
bodies, contracts, docs, and commit messages; when a new term
stabilizes, add it here instead of redefining it inline. Each entry
names its canonical home — this file routes, it does not arbitrate;
on any conflict the canonical file wins.

## Terms

### Orchestration

| Term | Means | Canonical home |
|------|-------|----------------|
| orchestrator | the main agent session running a skill's pipeline; owns statuses, synthesis, and spawn discipline — never a role agent's artifact | each skill's SKILL.md rules |
| role agent | a spawned sub-agent with exclusive artifact ownership, named for its job role (`spec-<role>` in the spec suite and discovery, `review-<role>` in spec-review; installed as native subagent types where the harness has them) | `skills/<name>/agents/*.md` |
| brief | an agent-definition markdown file in `skills/<name>/agents/`; its frontmatter-stripped body IS the system prompt | same |
| generated view | a root `agents/*.md` file, regenerated from a skill brief by `tools/agent-defs.py` — never hand-edited | `AGENTS.md` house rules |
| panel | a concurrent wave of role agents, one lens each, over a shared protocol (`protocol/panel-protocol.md`) (spec-discover: Visionary / Cynic / Minimalist; spec-review: correctness / security / quality) | `contracts/panel.md`, `contracts/run.md` |
| payload | the self-contained spawn input — skill_dir, problem restatement, brief body, lens section, protocol text, evidence pack | `skills/spec-discover/contracts/run.md` |
| digest | the only return value a spawned lens or panel agent produces; its grammar is fixed per skill | same |
| evidence pack | the external context gathered before a brainstorm panel spawns | `skills/spec-discover/SKILL.md` (stage 2) |
| idea brief | spec-discover's durable output at `brainstorms/<name>.md` — the chosen direction, problem, personas, MVP cut, risks, and kill criteria, ready to feed `/spec-define`; never a spec and never a design | `skills/spec-discover/templates/idea-brief.md` |
| consequential stop | a stop whose next move is the owner's judgment, not an edit — a task at the fix cap, a review that hands a decision over, a ruling a gate waits on; its ask shows what stopped (with the evidence), why it matters (a risk level), two to four options each with its consequence, a recommendation only when a rule or the evidence picks one, and what the answer covers | `skills/spec-build/contracts/delivery-pass.md` § Consequential stops (D-050); `skills/spec-review/gates/recommendation.md` adopts the same words |
| stop ask | the ask a consequential stop renders — `whatStops` (one line naming the gate and the ids with their evidence), `whyItMatters` (a risk level and its reason), two to four `options` each a label and a consequence, a `recommendation` only when a criterion picks one (else `noRecommendationReason`), and what the answer covers; `report --kind fix` derives it from the report's own state, never a claim, and the markdown renders it under `## Recommendation` | `skills/spec-review/contracts/panel.md` (D-024); `skills/spec-review/gates/recommendation.md` § Consequential stops |
| Refusals and failed calls | the kit-wide rule: every refusal or failed call is one of three kinds, named before acting on it — Fix and run again, Wait then retry, Stop and report — and a check is reported only when the agent saw it run | `rules/engineering-rules.md` § Refusals and failed calls |
| Fix and run again | a refusal about your own output — a failing test, proof, lint, contract or schema check, a gate that says what to change; fix what it names and run the same command again; not final, do not stop on it | `rules/engineering-rules.md` |
| Wait, then retry | a call the tool itself did not answer — a rate limit, a timeout, a dropped connection, a prompt nobody answered; nothing in the work is wrong; run the same call again up to three times, then report `blocked: <tool> did not answer: <error>` — never turn it into a result | `rules/engineering-rules.md` |
| Stop and report | a refusal by policy — permission denied, a guard, a hook, the boundary of your scope; never work around it, report its exact text and stop | `rules/engineering-rules.md` |
| not run | the honest report for a check the agent did not see run — `not run: <why>`; a failed call is never a failed check, and no unobserved failure, pass or verdict is ever reported | `rules/engineering-rules.md` |

### Scheduling and state (the spec suite: spec-define · spec-design · spec-build)

| Term | Means | Canonical home |
|------|-------|----------------|
| doc-set | the five contract files under `specs/<name>/` at `Tier: full` (plus intent.md when intake ran) — the canonical statement of what a spec dir IS; at `Tier: tiny` the doc-set is ONE file (spec.md with § Tasks) | `skills/spec-design/scripts/check.py` (the docset discipline) |
| contract file / evidence file | the two doc-set classes: spec / plan / tech-spec / task / test are Contract; intent.md is Evidence. The code-state evidence lives inside tech-spec.md as § Code state, the research record as § Questions & options | same (check discipline) |
| Code state | tech-spec.md's `## Code state` section — one `item` block per requirement (evidence pasted verbatim, DONE/PARTIAL/TODO status, verify command, gap) under the doc's `**Baseline**:`; the only source of task statuses and code citations. The tech lens writes it first; `check.py --code-state-only` is its self-check. Avoid: survey, survey.md (retired; `migrate.py upgrade` folds an old survey.md in) | `skills/spec-design/protocol/lenses.md` (tech lens) |
| TC ownership | every test case in test.md has one owner in task.md — a `Proves: TC-###` sub-line on the task that writes its test, or a `- TC-###` line under `## Regression guards` when Code state already reads its requirement DONE; check.py fails an unowned case | `skills/spec-design/templates/task.md` |
| contract tier | `**Tier**: tiny \| full` on spec.md — one-file contract vs the five-file docset (D-037); absent reads full | `skills/spec-design/decisions/037` |
| work type | `**Type**: feature \| bugfix \| hotfix \| refactor \| upgrade` on spec.md (intent.md seeds it); absent reads feature. bugfix adds the red repro and root-cause deltas, hotfix is a bugfix at `Tier: tiny`, refactor and upgrade preserve behavior — stories and ACs optional, a `**Preserves**:` test case required | `skills/spec-design/decisions/056-sdlc-coverage-in-define-and-design.md` |
| `**Depends on**` | optional spec.md header naming the specs this one builds on; check.py refuses a name that is no spec, warns while one is unapproved, and warns when another in-flight spec's `Touches:` overlap this spec's | same |
| `specs/INDEX.md` line | the cross-spec view's one line per spec — `- [<name>](<path>/spec.md) — <status> · <type> · <tier>[ · depends on …]` — rendered by `scripts/index.py`, its only writer; never hand-edited | `skills/spec-design/scripts/index.py` (the parity master) |
| Interfaces & data | the tech-spec.md section naming API shapes, data-model changes, migrations, and compatibility; required at full tier, `none — <reason>` allowed; a user-facing UI adds its `### UX` subsection (flows, empty/error/loading states, accessibility) | `skills/spec-design/decisions/056-sdlc-coverage-in-define-and-design.md` |
| Rollout | plan.md § Delivery's `### Rollout` subsection — exposure, migration order, rollback trigger, post-release check, or `none — <reason>`; it must agree with the tech-spec's rollback column | same |
| archetype | one of the five spec-suite agent briefs (the outward phases add integrator and release-manager, below), each named for its job role — analyst (`spec-analyst`) · architect (`spec-architect`) · tester (`spec-tester`) · developer (`spec-developer`) · auditor (`spec-auditor`); spec-discover's panelist is `spec-panelist`; harness def and brief are the same file (D-036) | `skills/spec-*/agents/` (byte-shared across the trio) |
| protocol / `protocol/` dir | a skill's shared prose its briefs point at — lens table, shared or panel protocol — kept in `protocol/`, never `agents/`, so no harness registers it as an agent (D-049) | `skills/*/protocol/` |
| lens | a specialization riding a spawn payload from `protocol/lenses.md` (intent/research/constitution on analyst; tech/plan/tasks on architect; the three panel angles) — data, not a brief file (D-036) | `skills/*/protocol/lenses.md` |
| constitution lens | the analyst lens that proposes `specs/CONSTITUTION.md` articles from the repo's observed conventions (tooling, test style, dependency policy, layering), each cited to evidence; it writes nothing — the user confirms every article. Emitted by `graph.py --emit-spawns --repair constitution` | `skills/spec-design/protocol/lenses.md` |
| primitive | a model-invoked discipline reference an orchestrator composes — grilling, diagnosing, domain-language (D-039) | `skills/spec-define/references/` (grilling; the monolith's tree is retired) |
| status holder | the one file that carries status: task.md at full tier, spec.md § Tasks at tiny — no other file holds status (C-01, amended by D-037) | `skills/spec-design/decisions/037-thin-floor.md` |
| frontier | every graph node that is ready and not done; the only scheduler — nothing schedules by stage number | `skills/spec-design/SKILL.md` (the generated node table) |
| wave | one concurrent run of the whole frontier; recompute after each wave | same |
| tick | the mechanical, atomic `- [ ] T###` → `- [x]` promotion with its `done <date> — <proof>` sub-line | `skills/spec-build/scripts/tick.py` |
| marker writer | the one sanctioned writer of task markers: `mark.py` for claims, landings, releases, fix rounds and drops; `tick.py` for ticks — both under the spec's `.task.lock` (D-039); hand edits remain possible but are no longer the sanctioned path | `skills/spec-build/scripts/mark.py` |
| claim stamp | the sub-line `  - claimed <UTC ISO> — run <id>` mark.py claim writes under a claimed entry — it says when and by which run; land, release and tick remove it (a claim without one stays valid; a stamp without a claim is a check.py finding) | `skills/spec-build/scripts/mark.py`; `skills/spec-design/scripts/specstate.py` (the parser) |
| digest file | the file a write-capable agent (developer, analyst, architect, tester) writes as its final action — `specs/<name>/digests/wave-<N>/<payload-stem>.md` holding its returned digest verbatim (D-040); the input `mark.py land` and the resume view read, and run scratch archive removes (counts folded into `retro.md`) | `skills/spec-build/scripts/mark.py`; `skills/spec-design/scripts/specstate.py` (`latest_digest`) |
| freeze | the approval freeze applied to the doc-set before execution; `approvals/approval.md` is its record, required at both tiers for an approved spec; at tiny tier it covers the § Tasks list less its status markers (D-050, D-051, D-052) | `skills/spec-design/scripts/freeze.py` (the parity master) |
| `**Approved-by**` | a line in `approvals/approval.md` naming one person who signed the approval, written by `freeze.py --record --by "<name>"` (repeatable); optional — a record without it is the session user's yes | `skills/spec-design/scripts/freeze.py` |
| `approvals/review.md` | full tier's record of the contract review — the findings digest, one ruling per BLOCK, and the payload's docset fingerprint (a hash of the frozen manifest plus task.md); `freeze.py --record` refuses a missing or stale one; tiny tier has none | `skills/spec-design/decisions/050-approval-records-and-payload-contracts.md` |
| `(fix n/5)` / `(fixed n/5)` | a task entry's fix-round marker: `(fix n/5)` is an OPEN round (the task is runnable again), `(fixed n/5)` the same round landed; `n` counts failures and 5/5 is the cap | `skills/spec-design/decisions/051-engine-enforces-wave-fix-and-tiny-approval.md` |
| typed deviation | the developer digest's `deviation` field with a routing prefix: `scope:<paths>` (needs files outside `Touches:` → widen under the D-### and re-emit), `spec-defect:<why>` (the task itself is wrong → `/spec-design`), `other:<summary needing D-###>`; neither typed flavor opens a fix round | `skills/spec-build/decisions/043-typed-deviations.md` |
| failure signature | a fix round's failing command — the first `$ <command>` line of its evidence in `notes/T###.md`; the same signature recurring across rounds suspects the plan, not the tier (advisory at 3 repeats, watch from 2); in the regression gate the same word is also the failing-test identity a runner output names (pytest `FAILED` lines, unittest `FAIL:`/`ERROR:`, go `--- FAIL`, jest/vitest markers, maven/gradle `[ERROR]` test lines, cargo `... FAILED`, TAP `not ok`) — the units the base comparison subset-tests (D-048) | `skills/spec-build/decisions/044-same-failure-signature.md`; `skills/spec-build/decisions/048-base-fairness.md` |
| budgets | the numeric limits the engine holds a writing agent to, stated in its brief's generated `§ Budgets` section from `rules/agent-limits.md` (fix cap, self-check reruns, fix-round bound) — an agent reads its budget, never learns it by hitting it | `rules/agent-limits.md`; `tools/kit-rules.py` |
| fast mode | `**Mode**: fast` on a `Tier: tiny` spec.md: the session implements the tasks itself instead of spawning a developer per task; claims, proofs, landing and both human gates are unchanged; ignored (with a note) at `Tier: full` | `skills/spec-design/decisions/066-fast-mode-inline-execute.md` |
| intent seed | the `INTENT SEED` block on a first grounding's tech payload (D-065): intent.md § Constraints evidence is reused for files unchanged since intent's baseline (verify re-run, no re-grep); changed files and uncovered items are grounded fresh; statuses never carry over | `skills/spec-design/decisions/065-intent-seeds-the-first-grounding.md` |
| deferred | a runnable task the engine left out of this wave because its files overlap a wave-mate or an `(in-progress)` task; printed `deferred: T### (<why>)`, emitted on a later wave | same |
| `--native-agents` | `graph.py --emit-spawns\|--run` flag for a harness with registered agent types: the payload names the type and omits the brief the type already carries; default payloads embed the brief | same |
| `reviewer-diff.patch` | the implementation-diff review's full diff, written beside its auditor payload because the auditor holds no shell; its header lists the untracked files the diff omits | `skills/spec-design/decisions/050-approval-records-and-payload-contracts.md` |
| gate | a check the flow must pass — say mechanical gate (scripts decide: `check.py`, review stage 1) or name the approval gate (verify → approve; the researcher gate); bare "gate" is ambiguous | each skill's SKILL.md |
| ENV-BLOCKED | the fifth proof outcome (spec-build D-047): a proof that never ran because its environment is missing — its program does not resolve, a variable the docset names is unset, its Docker engine does not answer, or the run ends exit 126/127 — the outcome names what is missing; not a pass and not charged as a failure, but red while it stands unruled, and the owner's `- Proof: <proof label> — <ruling>` delivery-block line turns it RULED — a FAIL is never rulable this way | `skills/spec-build/contracts/delivery-pass.md` (step 1); `skills/spec-build/decisions/047-environment-blocked-proofs-take-a-recorded-ruling.md` |
| proof ruling | the owner's `- Proof: TC-### — <ruling>` line in the delivery block — the recorded way through when an environment-blocked proof's environment cannot be supplied; it turns the proof RULED and lets dod gate 1 pass with the ruling in view; a FAIL is never rulable this way | `skills/spec-build/contracts/delivery-pass.md` (step 1); `skills/spec-build/decisions/047-environment-blocked-proofs-take-a-recorded-ruling.md` |
| automatic regression gate | delivery-pass step 2: `audit.py regression` runs the repo's own checks (spec-review's `gate.sh`, a pinned byte-identical copy) against the approved base — dod gate 3 reads PASS, FAIL, or NONE; NONE (no repo checks detected) is never a pass | `skills/spec-build/decisions/036-sdlc-rows-in-the-delivery-pass.md` |
| base fairness | a red repository check is charged to the change only when the base passes — the base's verdict comes from a detached temporary worktree of the approved base, removed after, the working tree and index never touched | `skills/spec-build/decisions/048-base-fairness.md` |
| charged FAIL | a failing repo check the change owns — the base is green at it, or the head fails where the base did not; traced to a task like a red proof, never rulable | `skills/spec-build/contracts/delivery-pass.md` (step 2); `skills/spec-build/decisions/048-base-fairness.md` |
| PREEXISTING | a failing repo check whose failures the approved base shares — listed with the base's failures in view, not charged, red until a `- Regression: <check> — <ruling>` delivery-block line rules it | `skills/spec-build/contracts/delivery-pass.md` (step 2); `skills/spec-build/decisions/048-base-fairness.md` |
| UNKNOWN (regression) | a failing repo check whose base could not be checked — no checkout of the base, no base report, or the check cannot run there; neither passed nor charged, red until ruled | `skills/spec-build/contracts/delivery-pass.md` (step 2); `skills/spec-build/decisions/048-base-fairness.md` |
| verifier definition | a file that defines what the repo's checks check — a make recipe, a CI workflow, test-runner or lint configuration, or the `[tool.*]` test/lint table or scripts block of pyproject.toml/package.json; the conservative pattern tables live in one documented place in `audit.py` | `skills/spec-build/scripts/audit.py` (`verifier_kind`); `skills/spec-build/decisions/046-verifier-changes-take-a-ruling.md` |
| verifier change | a diff to a verifier definition inside the implementation scope — reads RULED only under a `- Verifier: <path> — <ruling>` delivery-block line; `audit.py verifiers` and dod gate 14 fail while an unruled one stands; a dependency-only change is not one | `skills/spec-build/decisions/046-verifier-changes-take-a-ruling.md` |
| delivery block | the bulleted fact lines under the status holder's `**Delivered**:` field (task.md at full tier, spec.md § Evidence at tiny) — the `Docs impact:`, `Rollback:`, `Hygiene:`, `Verifier:`, `Regression:`, `Proof:`, `Behavior preserved:` rulings — drafted by `audit.py block` for the dod gates (1, 11–14) and landed by the delivery record commit C2 | `skills/spec-build/contracts/delivery-pass.md` § The delivery block |
| delivery note | the delivery block itself — the one source the owner facts read (`audit.py delivery_note`, `/spec-ship`'s `pr-body`, dod gates 1 and 11–14); `specs/<name>/notes/delivery.md` is only the archived-history fallback that predates the block | `skills/spec-build/contracts/delivery-pass.md` § The delivery block; `skills/spec-ship/decisions/007-ruled-proofs-in-the-pr-body.md` |
| docs impact | the delivery note's `Docs impact:` line — the user-facing docs the diff updates (README, API docs, CHANGELOG, migration notes), or `none — <reason>` | same |
| `specs/BACKLOG.md` | the repo's parked-work list, one date-free line each — `- <spec> — <item> (source: <source>)`; `tick.py --park` and spec-review's `backlog_offer` write it, only on the user's yes | same; `skills/spec-review/decisions/019-dependencies-ci-and-the-backlog.md` |
| `retro.md` | an archived spec's retrospective, assembled by `retro.py` at archive from its own records (tasks, fix rounds, decisions, delivery note, parked lines, telemetry counts) — facts, never prose; its D-### titles roll up to `specs/context/decisions.md` | `skills/spec-build/scripts/retro.py` |

### Outward phases (spec-ship · spec-release)

| Term | Means | Canonical home |
|------|-------|----------------|
| outward action | any step that leaves the workspace — push, PR create or edit, posted comment, tag push, GitHub release; runs only on the user's explicit yes to a shown preview, never forced, never merging, never deploying | `skills/spec-ship/gates/outward-actions.md`, `skills/spec-release/gates/cut.md` |
| `Shipped:` record | `Shipped: PR <url>` in the status holder beside `Delivered:` — written by `/spec-ship` once the PR exists; task.md's header at full tier, spec.md § Evidence at tiny | `skills/spec-ship/decisions/002-shipped-record-beside-delivered.md` |
| `Released:` record | `Released: <tag> @ <sha>` in each included spec's status holder, written in a record commit right after the tagged release commit | `skills/spec-release/decisions/002-released-record-placement.md` |
| `notes/ship.md` | `specs/<name>/notes/ship.md` — evidence no task covers (CI output, review comments) that `/spec-ship` writes for `/spec-build` fix rounds; a change outside the approved contract routes to `/spec-design` | `skills/spec-ship/SKILL.md` |
| CI triage class | the class each red check row is given from run step evidence, first hit winning — `infrastructure` (cancelled, never started, or the first failed step is the runner's own setup/wrap-up), `code` (any other failed step), `unknown` (no step data behind the status); never timing and never log text; one classifier shipped byte-identical in `ship.py` and the review oracle | `skills/spec-ship/decisions/005-ci-triage-red-checks-classed.md` |
| `ci-rerun` | spec-ship's stage for a red PR whose checks are all infrastructure or unknown — it names each check's class and reason and prints the `gh run rerun <id> --failed` commands (outward actions, run only on the user's yes) and opens no fix round; `ship.py evidence --kind ci` routes one to a fix round on purpose | `skills/spec-ship/contracts/run.md` (the stage table) |
| ruled proof | a proof the environment could not run whose gap the owner accepted with a proof ruling in the delivery block (spec-build D-047); the PR body renders each as `Owner to test after merge: TC-### — <ruling>` — never as a pass, and outside the ticked-task and TC counts | `skills/spec-ship/decisions/007-ruled-proofs-in-the-pr-body.md` |
| review-thread ruling | the owner's label (`must-fix`, `question`, `nit`, `disagree`) plus why for one PR review thread; a ruled thread keeps its label and is not reclassified by the integrator | `skills/spec-ship/contracts/run.md` (Review-thread rulings) |
| rulings file | `specs/<name>/notes/rulings.md` — where `ship.py rule` writes and `comments` reads owner rulings, at both tiers, one line each: `- <thread id> — <label> — <why>`; re-ruling a thread replaces its line in place | `skills/spec-ship/contracts/run.md` |
| inactive ruling | a ruling whose thread is resolved or no longer listed — kept on file, reported in `comments`' `inactive_rulings[]`, never a failure | `skills/spec-ship/contracts/run.md`; `skills/spec-ship/scripts/ship.py` |
| post-release check | the human-run checklist `/spec-release verify` prints; its outcome lands beside `Released:` as `Post-release check: <tag> pass\|fail <date> — <note>`; a failure routes to `/spec-define <name>` as a hotfix | `skills/spec-release/SKILL.md` |
| integrator | the `spec-integrator` agent — drafts PR wording and classifies review comments for `/spec-ship`; holds no shell and takes no outward action | `skills/spec-ship/agents/integrator.md` |
| release manager | the `spec-release-manager` agent — tightens changelog and release-notes wording from recorded facts for `/spec-release`; writes nothing | `skills/spec-release/agents/release-manager.md` |

### Review (spec-review)

| Term | Means | Canonical home |
|------|-------|----------------|
| mechanical gate | stage 1: the target repo's own checks (Makefile, npm scripts, cargo, go, pytest/unittest, shell syntax, secret shapes) | `skills/spec-review/SKILL.md`, `scripts/gate.sh` |
| finding | a kept review observation with an ID, independently confirmed before it survives triage | `skills/spec-review/contracts/panel.md` |
| verdict | a fix-loop verification outcome for one finding: `fixed`, `unfixed`, `worse` — or a skip ruling | same |
| skip ruling | the fix verifier's adjudication of a fixer skip: `rejected-valid` (the reason holds — the finding is withdrawn and resolves) or `rejected-invalid` (it stands); an unruled skip stands | `skills/spec-review/decisions/022-adjudicated-skips-and-out-of-scope.md` |
| out-of-scope | a fix disposition: the sound fix needs paths or behavior the change must not touch — it burns no round and waits on the user's widening call | same |
| standing CI row | a pr-mode `source: ci` gate row classed infrastructure or unknown — exit_code 0, so it fails neither the gate nor the reviewers, but it stands in the gate note and the report's gate section with its class, reason and rerun command, and floors the fix loop's recommendation at `human` until it clears | `skills/spec-review/decisions/023-ci-triage-in-pr-mode.md` |
| recommendation floor | the recommendation (`merge`/`fix-first`/`human`) the oracle derives from the report's own state; a claim below it errors, escalation above it always stands | `skills/spec-review/gates/recommendation.md` (D-021) |
| `changed_since` | fix-run report data naming what changed since the last fix attempt (a skip the owner overturned, a hand fix) — it alone makes another fix round an option in the stop ask | `skills/spec-review/contracts/run-sequence.md` (report data); `skills/spec-review/decisions/024-consequential-stop-ask.md` |
| A failed call is not a round | the fix loop's slice of the refusals rule: a fixer, reviewer or verifier spawn that returned nothing usable (a rate limit, a timeout, a lost session, a permission prompt nobody answered) opens no fix round and changes no finding's status — the same stage re-runs, retries bound at three per stage, then the owner is told the stage, the error and the count; a refusal by policy is final, one over produced output is fixed and re-run | `skills/spec-review/contracts/run-sequence.md` |
| shared review oracle | `review_orchestrator.py` — the single home of review state, systems, asks, finding IDs, and report assembly | D-014 |
| probe | one thin per-phase call by which any caller fetches JSON from the oracle (scope, gate, shard, ask, report) | D-014 |
| dialect twin | (retired, D-035) the per-harness workflow scripts deleted with the one-engine move — history only; the shared oracle is the one executable form | `skills/spec-review/decisions/016` |

### Kit plumbing

| Term | Means | Canonical home |
|------|-------|----------------|
| skill dir | `skills/<name>/`, self-contained by packaging (marketplace `source: ./skills/<name>`) | `AGENTS.md` |
| generated surface | any regenerate-only artifact: root `agents/`, the SKILL.md node table (`scripts/contract.py`), the plugin/marketplace manifests, the `§ Engineering rules` and `§ Budgets` sections | `AGENTS.md` house rules |
| ADR (D-###) | an append-only decision record; every divergence from a doc contract gets its own entry (C-05) | `skills/<name>/decisions/` |
| eval case | an entry in a skill's `evals/cases.md`; every increment names its served case (C-10) | `skills/<name>/evals/cases.md` |
| eval result | one recorded run of an eval case — per-criterion verdicts with evidence, date, repo, and the skill's `surface:` hash; append-only, never restamped | `skills/<name>/evals/results/` |
| held-out case | an eval case marked `Held-out: yes` whose Pass criteria are read only at judging time, never while authoring the skill (D-061) | `skills/<name>/evals/cases.md` |
| eval check | a case's `- **Check C<n>**:` shell bullet proving a criterion mechanically against the prepared scratch repo; the check's verdict wins over an observer's (D-061) | `tools/evals.py` |
| sync | `tools/sync.sh` — the one harness-neutral install pipeline to every machine harness root | `tools/` |
| telemetry | the local append-only run record (`scripts/telemetry.py` → `~/.spec-dev-kit/telemetry/*.jsonl`) — evidence for self-improvement, never status, never contents | `skills/*/scripts/telemetry.py` |
| skill command | one `/spec-*` command per skill, named for it — `/spec-discover`, `/spec-define`, `/spec-design`, `/spec-build`, `/spec-review`, `/spec-ship`, `/spec-release`; spec-build's implement/test/audit/ship ride its router as verbs (D-033) | D-029, spec-build D-033, spec-design D-048, D-054 |
| skill name / agent name | skills are named after SDLC phases (discover → define → design → build → review → ship → release); agents are named after job roles (analyst, architect, tester, developer, auditor, panelist, review-*, integrator, release-manager) | spec-design D-054 |
| lifecycle commands | the skill commands that carry a spec from idea to release, in order: `/spec-define` → `/spec-design` → `/spec-build`, then the outward phases `/spec-ship` → `/spec-release`; `/spec-discover` is the optional step before them and `/spec-review` stands outside the lifecycle | `README.md` Usage |

## Terms to avoid

- **The suite's pre-2.1.0 name** — retired and deliberately not
  spelled out anywhere in this repo; refer to it only as "the former
  name" and never reintroduce it (D-014).
- **Bare `/review`, `/plan`, `/build`, `/test`, `/ship`** — retired by
  D-029; they collide with harness modes and built-ins. Use the
  `/spec-*` forms, and say `spec-review` for standalone review.
- **Retired skill and command names** — `spec-brainstorming`,
  `spec-intent`, `spec-shape`, `spec-execute`, `spec-code-review`
  (released), `spec-intake`, `spec-author` (never released),
  `/spec-idea`, `/spec-gen` (spec-design D-048, D-054): the skills are
  `spec-discover`, `spec-define`, `spec-design`, `spec-build`,
  `spec-review`, `spec-ship`, and `spec-release`, and each command is its skill's name.
- **Retired agent names** — `spec-scout`, `spec-designer`, `spec-qa`,
  `spec-reviewer`, `spec-builder`, `brainstorm-panelist`,
  `code-review-scout`, `code-review-correctness`,
  `code-review-security`, `code-review-quality`, `code-review-fixer`
  (spec-design D-054): say analyst, architect, tester, auditor,
  developer, `spec-panelist`, and `review-*`.
- **`/spec-build build`, `/spec-build review`** — the verbs are
  `implement` and `audit` (D-054), so "build" stays the phase and
  "review" stays spec-review's word.
- **"Design specification" / "design spec"** for spec-discover's
  output — it is an idea brief; "design" names only the spec-design
  phase (D-054).
- **"Workflow dialect" / "twin"** for current surfaces — retired with
  D-035; the term now names history only. Say "the oracle"
  (spec-review) or "`graph.py --run`" (the spec suite's engine,
  shipped by the trio).
- **"Stage" for the spec suite's scheduling** — the pipeline schedules by
  frontier and waves, never by a stage ladder ("Waves, not stages").
  spec-discover and spec-review do have real stages; the word is
  theirs.
- **"Copy" for a root `agents/*.md` file** — it is a generated view;
  "copy" invites hand-editing.
- **Hedged normative verbs in contract text** — "should ideally",
  "try to", "if possible". Acceptance criteria and rule text use
  MUST / MUST NOT / NEVER; if a behavior is genuinely optional, say
  what decides the optionality instead of hedging the verb.

## Flagged ambiguities (resolved)

- **"review"** splits three ways (D-029, D-054): `/spec-build audit`
  is spec-build's implementation-diff review step, run by the
  auditor; `spec-review` is the standalone skill; harness built-ins
  keep their own names.
- **"ship"** covers two things: `/spec-build ship` is the delivery
  pass (local commits C1/C2, `Delivered:`); `/spec-ship` is the
  PR/integration skill (push, PR, CI, review comments, `Shipped:`).
  Name which.
- **"agent"** covers four things — say role agent (spawned), brief
  (the markdown), generated view (root `agents/` file), or AGENTS.md
  (the convention file).
- **"workflow"** covers two things — the workflow graph (scheduling
  semantics, `scripts/contract.py` + the spec-design SKILL.md node
  table) and a workflow run (`graph.py --run` executing one). Name
  which.
- **Byte-identical pairs** (telemetry module copies, lens sections in
  payloads) are edited in every copy at once or regenerated from
  source — the recurring mistake is editing one copy and shipping
  drift.
