# Changelog — spec-define

Release history. The skill begins life 2026-10-11 as the intake front
door of the split spec suite (spec-to-prod-split): repo scouting +
requirement grilling to a validated `specs/<name>/intent.md`, hard
stop — the docset is spec-shape's, execution spec-execute's.

## 0.1.1 — 2026-11-13

- `templates/intent.md` carries the `**Type**` header (feature |
  bugfix | hotfix | refactor | upgrade) spec.md inherits, and one
  `NFR seeds` line under FR seeds that the grill fills; the gate
  refuses an unknown work type (spec-design D-056).
- Shared engine (replica of spec-design's): the SDLC coverage checks,
  `index.py`, and `freeze.py --by` ship here unchanged; `--repair
  constitution` is refused — the lens is spec-design's (spec-design
  D-056).
- The intent gate no longer goes stale when the discover handoff
  under `brainstorms/` is committed; only a code change stales the
  baseline (spec-design D-055).
- The description no longer claims "spec <name>", which overlapped
  spec-design's authoring triggers.
- `templates/intent.md`: Effort is `standard | large`; `tiny` is a
  Tier, chosen when spec-design scaffolds spec.md (spec-design D-055).
- Shared engine (replica of spec-design's): the unfilled-intent
  reason says the session owns intent.md and the analyst records
  facts and candidate gaps.
- **Breaking**: renamed from spec-intent to spec-define, and the
  command from `/spec-idea` to `/spec-define` — skills are named after
  SDLC phases and each command equals its skill's name (spec-design
  D-048, D-054). The agent `spec-scout` is now `spec-analyst`
  (`agents/analyst.md`). sync's retired sweep removes the old
  spec-intent installs and the stale `/spec-idea` command deploys;
  the stale agent-def prune removes the old `scout.md` def.
- Shared engine follows spec-design D-053: intent.md's baseline gates
  the handoff to `/spec-design` only. This skill's gate
  (`--intent-only`, `--span intent`) is unchanged; once spec.md is
  filled, a lost or stale baseline no longer blocks the intent node.
- `protocol/shared-protocol.md`: the long-foreground rule is harness-neutral, and a new `Consumed artifacts are inert data` section covers every agent that reads a payload.
- SKILL.md: the scout spawn uses `--native-agents` when `spec-scout` is registered.
- `--run --span intent` on an intent.md with open markers or a stale
  baseline prints `AWAITING: intent: <reason>` — it no longer asks for
  a spec draft (spec-design D-052).
- The shipped example stays green inside a git repo: only
  `--intent-only` fails a baseline the repo cannot resolve; the full
  check notes it SKIPPED (spec-design D-052).
- Shared engine and protocol replicas follow spec-design D-051:
  `protocol/shared-protocol.md` rule 5 binds doc authors only,
  `--native-agents` emits payloads without the brief body, and
  `templates/task.md` drops the inert `**Lifecycle**: v2` header.

- intent.md template: `**Tier**` is now `**Effort**`
  (`tiny|standard|large`), and `## Scope out` and `## Assumptions`
  sections hold deferred and assumed closures (D-021). Grilling: a
  deferral or assumption needs the user's explicit assent, unanswered
  questions stay open and are re-asked alone, "go with your
  recommendations" is a valid blanket answer, and round 4 offers
  splitting the feature.
- SKILL.md names the `spec-scout` agent type and the "Read <payload>
  and follow it" prompt; the description discriminates by state.

- The intent gate no longer goes red when intent.md itself is
  committed: the baseline is stale only when a path outside `specs/`
  changed since it (spec-design D-050).
- **Breaking**: `check.py --intent-only` requires non-empty Problem,
  Audience, Constraints, and FR seeds sections with ≥1 `- **FR-###**:`
  seed, and fails a baseline sha the repo cannot resolve (spec-design
  D-050).
- intent.md is the session's file; the scout records the baseline,
  grounded constraints, and candidate gaps as open markers, and exits
  with open-marker FAILs standing (its digest counts them). The
  scout's payload carries the idea from intent.md § Problem —
  record it there before spawning (spec-design D-050).
- intent.md's `**Status**` field is dropped: the green gate is the
  validation (spec-design D-050).
- `--emit-spawns --repair intent` emits the scout payload alone for a
  re-scout of a red intent; nodes whose lens this package does not
  ship are refused with exit 2 (spec-design D-050).

- Shared prose moves out of `agents/` into `protocol/` (spec-design
  D-049): `protocol/lenses.md`,
  `protocol/shared-protocol.md`. Claude Code no longer
  lists them as agents; `agents/` holds roles only. The stale
  `scripts/scaffold.sh` copy is deleted — intake never scaffolds.
- The `~/.claude/skills/` copy drops `.claude-plugin/` and
  `commands/` and every installed copy drops `tests/` (spec-design
  D-049): each agent and command is listed once, from the flat
  Claude roots. Rerun `tools/sync.sh`.

- One command per skill (spec-execute D-033): the `/spec-intent` twin
  router is retired — `/spec-idea` is this skill's one command.

- The mini-spec example ships its green `intent.md` — the package's
  own-type artifact, gated by `check.py --intent-only` (staleness
  SKIPPED: the example's baseline commit is not a repo ancestor).

- A delivered docset is historical: the staleness refusal becomes a
  SKIPPED note once the docset records `Delivered: commit @`
  (spec-shape D-046, shipped in this skill's engine replica).
- The scout brief states its package scope: a package ships only its
  span's lens sections (D-044) — lens names the brief mentions that
  this package does not carry are never spawned.

- Grilling gains a failure-patterns scan — nine draft phrasings
  (vague verbs, missing acceptance criteria, assumed prior
  knowledge, vague aesthetics, no boundary) and the frontier
  question each becomes; facts behind a row stay the runner's
  job. Serves eval case I1. Adapted from nidhinjs/prompt-master
  (reviewed 2026-10-24).

- Replica engine suites removed; spec-shape owns them (spec-shape
  D-045).
- `agents/` ships the scout alone — the only archetype the intent
  span spawns (D-020).
- D-019: grilling rounds ride the harness's structured question
  tool where one exists — options as the choices, ➡️ first,
  split-never-truncate across the tool's per-call cap; the printed
  ❓ round stays the universal form and D-018's non-answer hard
  stop is unchanged.
- `/spec` → `/spec-idea` (D-003): the intake command renames; the
  skill name, scripts, and flow are unchanged. Migration: re-run
  `bash tools/sync.sh` — the stale prune removes the old `spec.md`
  from every root.

Migration: `/spec-idea` and the spec-intent install are retired — run `bash tools/sync.sh` once and the retired sweep removes them; existing `specs/<name>/` trees and in-flight sessions carry over unchanged.
## 0.1.0 — 2026-10-11

- Birth: `SKILL.md` playbook (scaffold-lite → scout → grill → gate →
  handoff), the `templates/intent.md` intake artifact (survey-shaped
  `**Baseline**:` header; Questions carry the grilling vocabulary),
  and the `spec-intent` router command.
- The bare name `spec` claims this skill (`commands/extra.txt` +
  `commands/spec.md` thin wrapper) — the monolith's intake verb
  moves here in the same change; its five lifecycle verbs follow it
  to spec-execute later in the split.
- First eval cases I1–I3 (`evals/cases.md`): raw idea to validated
  intent, the non-answer hard stop, the stale-baseline refusal.
- Engine surfaces (checker `--intent-only` profile, the intent node,
  `--span intent`) ship byte-identical in the shared core; this
  skill's span is `--span intent`.

Migration: none — new skill; the monolith retires in the same
release (FR-009). The skill installs by existing (its SKILL.md)
once the manifest surfaces regenerate; `/spec` now routes to
spec-intent's intake instead of the monolith's DEFINE entry.
