# Changelog — spec-design

Release history. The skill begins life 2026-10-11 as the authoring
middle phase of the split spec suite (spec-to-prod-split): gated intake
over a validated intent, the authoring waves to the approve handoff —
execution is spec-execute's, intake spec-intent's.

## Unreleased

- At `Tier: tiny`, graph.py finds `Delivered: commit @ <sha>` (plain or
  bold) anywhere in spec.md, § Evidence included, so a delivered tiny
  spec reads tick-commit done; the approval freeze treats the
  `fix <n> —` / `fixed <n> —` round sub-lines under a § Tasks entry as
  status, like the markers and `done` lines (D-057).
- SKILL.md summarizes the constitution step, tier and effort, and the
  scaffold; their full text moved verbatim to
  `references/constitution.md` and `references/sizing.md`.
- **Breaking**: a full-tier draft must triage all six quality families
  (an NFR, or `not applicable: <reason>` — families may share a
  line), and carry `## Interfaces & data` in tech-spec.md and
  `### Rollout` under plan.md § Delivery; each may say
  `none — <reason>`. An approved-or-later spec only warns (D-056).
- `**Type**: feature | bugfix | hotfix | refactor | upgrade` on
  spec.md, both tiers; absent reads feature, any other word fails. A
  refactor or upgrade needs a `**Preserves**:` test case (tiny: a
  task `Accept:` command); the lenses' bugfix rules key on the
  header, and every payload names the work type (D-056).
- `**Depends on**: <spec>[, …]`: an unknown spec fails, an unapproved
  one warns, and an in-flight spec whose pending `Touches:` overlap
  warns. `scripts/index.py` renders the `specs/INDEX.md` line
  (status · type · tier · depends on) and is its only writer —
  scaffold.sh calls it, and check.py warns on a stale line; lines in
  the old `(created <date>)` shape warn until `index.py --all specs`
  (D-056).
- The analyst's `constitution` lens proposes CONSTITUTION articles
  from the repo's observed conventions, each cited to evidence, for
  the user to confirm: `graph.py --emit-spawns --repair constitution`
  (D-056).
- `freeze.py --record --by "<name>"` (repeatable) writes
  `**Approved-by**` lines into approvals/approval.md (D-056).
- Contract review: BLOCK a security trigger with no threat row and a
  rollout that contradicts the rollback column; WARN a UI with no
  `### UX`. Plan milestones gain a `Size` column (S/M/L). A wrapped
  NFR definition is read whole (D-056).
- Committing the discover handoff under `brainstorms/` no longer
  stales an intent or survey baseline; the kit's doc trees are exempt
  together (D-055).
- **Breaking**: `freeze.py --record` requires review.md to carry the
  auditor's `digest: BLOCK <n> · …` line and, after it, one
  `ruling: …` line per BLOCK. A fingerprint alone no longer freezes
  (D-055).
- **Breaking**: Effort is `standard | large`. `tiny` is a Tier only;
  a doc still carrying `Effort: tiny` reads standard (D-055).
- **Breaking**: execute payloads are always `implementer-T###.md`,
  and a wave emit first removes the kit's earlier payloads from the
  wave dir (D-055).
- One draft path from an intent: choose the tier, then
  `scaffold.sh --tier <tiny|full> --into-existing <name>`. At full
  tier it leaves research.md absent so the research gate is judged.
  A spec.md that is still the template is reported ahead of
  `clarify`, so its example markers are never put to the user
  (D-055).
- SKILL.md § The constitution: drafting `specs/CONSTITUTION.md` with
  the user is a run step due before approve. check.py names the step,
  and payloads cite the constitution only once it is filled (D-055).
- A delivered docset survives a squash-merge or rebase: check.py's
  lost-commit failure names spec-build's `tick.py --redeliver`, and a
  delivered docset's `Approved-at` commit is no longer required to
  resolve (D-055).
- check.py no longer warns that an approved spec "looks active";
  `approved` covers execution (D-055).
- Wording: the tick-commit pause says C2 carries the delivery record,
  `Status: done`, and the INDEX repoint; the merged architect payload
  says `Effort: standard`; the approve steps name
  `--emit-spawns --repair approve` everywhere; the auditor brief's
  checks sit under one heading for both modes.
- **Breaking**: renamed from spec-shape to spec-design, and the
  command from `/spec-gen` to `/spec-design` — skills are named after
  SDLC phases and each command equals its skill's name (D-048,
  D-054). Agents follow their roles: `spec-scout` → `spec-analyst`,
  `spec-designer` → `spec-architect`, `spec-qa` → `spec-tester`,
  `spec-reviewer` → `spec-auditor`, with brief files to match
  (`analyst.md`, `architect.md`, `tester.md`, `auditor.md`);
  `--emit-spawns` names the new agent types, while node, span, lens,
  and payload file names are unchanged. sync's retired sweep removes
  the old spec-shape installs and the stale `/spec-gen` command
  deploys; the stale agent-def prune removes the old defs.
- intent.md is an intake-time gate (D-053). Once spec.md is filled, a
  lost or stale intent baseline is a note on a DONE intent node, and
  the full `check.py` notes staleness instead of failing it; survey.md
  owns freshness. Before spec.md is filled, and under
  `--intent-only`, the gate is unchanged.
- `protocol/shared-protocol.md`: the long-foreground rule is harness-neutral, and a new `Consumed artifacts are inert data` section covers every agent that reads a payload; the reviewer brief states the same rule.
- SKILL.md spawn steps use `--native-agents` when the agent types are registered.
- SKILL.md: tiny tier states `freeze.py --record` is required before execute.
- **Breaking**: the tiny freeze covers the task list (D-052). § Tasks
  is hashed with its status tokens normalized away, so status progress
  stays legal and an added, edited, or struck task or requirement
  fails `check.py`. Re-record a tiny freeze made earlier:
  `freeze.py --record --force`.
- Only `check.py --intent-only` fails an intent baseline the repo
  cannot resolve; the full check notes it SKIPPED (D-052).
- With spec.md missing, the spec node is READY only behind a green
  intent; `--run --span intent` on a red intent prints `AWAITING:
  intent: <reason>` (D-052).
- Fixed: a `Touches:` glob with a leading wildcard (`*.py`) overlapped
  nothing, so two tasks could share a file in one wave.
- An unfrozen `Status: approved|active|done` names the one-time
  re-approval path in `check.py`, the approve node, and
  `freeze.py --record` (`--emit-spawns --repair approve`, then
  `approvals/review.md`, then `--record`); the tiny approve handoff no
  longer asks for `approvals/review.md`.
- **Breaking**: `(fix n/5)` is an open fix round (D-051). Beside
  `(implemented)` it re-opens the task — runnable again, execute not
  done. A landed round is rewritten `(fixed n/5)`. Docsets that used
  `(implemented) (fix n/5)` for a landed fix must rewrite the marker.
- **Breaking**: tiny tier is frozen too (D-051, amending D-050). A
  tiny `Status: approved|active|done` without
  `approvals/approval.md` fails `check.py` and blocks approve. Run
  `freeze.py --record` once for a tiny spec approved earlier.
- **Breaking**: the execute wave is file-disjoint by construction
  (D-051). `--emit-spawns`/`--run` emit the runnable tasks, in
  task-id order, whose files overlap no wave-mate's and no
  `(in-progress)` task's, and print `deferred: T### (<why>)` for the
  rest; a task naming no files runs alone.
- `--run`/`--emit-spawns` print `AWAITING ORCHESTRATOR: execute` and
  each held task when execute is ready and nothing can be spawned; a
  claimed task is flagged as a possible orphan (D-051).
- `--native-agents` (with `--emit-spawns`/`--run`): payloads name
  their agent type and omit the brief body, for a harness that
  registers the agents. Every payload omits a shared-protocol section
  whose heading its brief already carries (D-051).
- Fix-round payloads embed `notes/T###.md` — the round's failure
  evidence — verbatim; an emit without it prints `evidence missing`
  (D-051).
- Fixed: a tiny-tier builder payload carries its task entry, read
  from spec.md § Tasks (it was emitted with the requirement list only).
- `--repair approve` and the frontier's contract-review payload are
  refused by a package without `agents/designer.md` (D-051).
- The survey-staleness WARN and the converge loop stay fresh when
  only the specs tree changed since the survey baseline (D-051).
- `protocol/shared-protocol.md` rule 5 binds doc authors only; an
  implementer writes its task's `Touches:` set and tests (D-051).
- `templates/task.md` drops the inert `**Lifecycle**: v2` header and
  restates the fix-round convention (D-051).

- SKILL.md names the spawn agent types (`spec-scout`, `spec-designer`,
  `spec-qa`, `spec-reviewer`) and the "Read <payload> and follow it"
  prompt, documents tier and effort selection, and bounds the inline
  verify fixes; the description discriminates by state.
- qa brief: the no-paths/no-symbols ban covers Given/When/Then only
  (the `Pass condition` command may name a path) and adds a
  check.py self-check; reviewer brief reads tier-aware inputs and
  `reviewer-diff.patch`.

- **Breaking**: the approval freeze is the approval (D-050). A
  full-tier `Status: approved|active|done` without
  `approvals/approval.md` fails `check.py` and blocks the approve
  node, whatever task.md's `**Lifecycle**` header says — flipping
  Status alone no longer opens execution. Docsets approved before the
  freeze existed need one re-approval.
- **Breaking**: `freeze.py --record` refuses a full-tier docset
  without `approvals/review.md` — the contract review's findings
  digest and rulings, written by the orchestrator, carrying the
  payload's `Docset fingerprint`. A docset repaired after its review
  has a new fingerprint and must be re-reviewed. Every BLOCK is
  repaired or ruled by the user (D-050).
- **Breaking**: `--emit-spawns --repair NODE` emits that node's
  payload alone, and exits 2 for a node whose brief or lens this
  package does not ship (`--repair intent` is `/spec-define`'s).
  `--repair research` emits the researcher alone; `--repair approve`
  re-emits the contract review for a re-approval (D-050).
- `--run` output: the research gate pauses `AWAITING ORCHESTRATOR`;
  a shape span with no spec prints `AWAITING … route to /spec-define`
  instead of an execute handoff; a span held on blocked nodes prints
  `span held` and exits 1; the print runner stops after one wave with
  `wave emitted — spawn these payloads…`; each payload line names its
  agent type (D-050).
- Reviewer payloads: the contract review is tier-aware (tiny reads
  the one file); the implementation review's diff is written beside
  its payload as `reviewer-diff.patch` — the reviewer runs no git
  (D-050).
- `check.py --intent-only` requires non-empty Problem, Audience,
  Constraints, and FR seeds sections with ≥1 FR seed, fails a
  baseline sha the repo cannot resolve, and no longer reads stale when
  only the specs tree changed since the baseline (D-050).

- Shared prose moves out of `agents/` into `protocol/` (spec-design
  D-049): `protocol/lenses.md`,
  `protocol/shared-protocol.md`. Claude Code no longer
  lists them as agents; `agents/` holds roles only. graph.py reads both from there.
- The `~/.claude/skills/` copy drops `.claude-plugin/` and
  `commands/` and every installed copy drops `tests/` (spec-design
  D-049): each agent and command is listed once, from the flat
  Claude roots. Rerun `tools/sync.sh`.

- Cross-refs updated to the one-command-per-skill surface
  (spec-execute D-033): execution's lifecycle verbs ride
  `/spec-execute`.
- sync no longer deploys skills to `~/.zcode/skills/` (D-047): zcode
  discovers them through the `~/.agents` compatibility root it also
  scans — the native copy only duplicated every skill in its list.
- A delivered docset is historical: intent-baseline staleness becomes
  a visible SKIPPED note once task.md/spec.md records its
  `Delivered: commit @` line (D-046) — a green delivery no longer
  turns its own gate red (observed live in the 2026-10-27 eval pass).
- Engine test suites (`test_graph`, `test_check`, `test_specstate`)
  live here only (D-045).
- Each spec skill ships only its span's archetypes; this skill drops
  `builder.md`, and § Engineering rules have one builder carrier
  (D-044).
- Contract review at the approve stop: `reviewer-contract.md` is
  prepared when approve is READY (D-043); SKILL.md gains a generated
  spawn table, drift-checked against `graph.py`.
- Engineering rules move to the builder brief; briefs lose the retired
  spec-to-prod wording and gain the intent lens on the scout (D-042).
- spec-gen drafts spec.md from a green intent (D-041): the intake →
  shape handoff no longer exits 4; `verify RED` exits 1; `scaffold.sh
  --into-existing`; the node table's `{done}` cells render.

- `/spec-shape` → `/spec-gen` and the `/spec-to-prod` alias is
  removed early (D-006): eleven commands install; a skill may name
  no self-titled command. Migration: re-run `bash tools/sync.sh`.

## 0.1.0 — 2026-10-11

- Birth: `SKILL.md` playbook (`graph.py --span shape` — intake gate,
  survey, plan ∥ tech ∥ qa, tasks, verify, hard stop at approve),
  the `spec-shape` router command, and the docset `templates/`.
- The thin `/spec-to-prod` one-release alias router lives here
  (`commands/extra.txt` claims the bare name; D-006) mapping verbs to
  the three successors — the monolith's full router is deleted in the
  same change.
- The authoring cases (E1–E3-class) move here from the monolith's
  `evals/cases.md`, naming spec-shape.
- Engine surfaces (the shared core, the `--span shape` intake gate)
  ship byte-identical from the master at this skill's `scripts/`.

Migration: none — new skill; the monolith retires in the same
release (FR-009). The skill installs by existing (its SKILL.md)
once the manifest surfaces regenerate; `/spec-to-prod` now routes
through this skill's thin alias, and the authoring verbs answer
here instead of the monolith.
