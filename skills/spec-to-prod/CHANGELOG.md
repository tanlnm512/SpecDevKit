# Changelog — spec-to-prod

Release history. Versions earlier than 1.2 are retrofitted from session
records — the changelog itself starts 2026-09-08.

## 2.3.0 — 2026-09-10

Comment and duplication guardrails gain mechanical teeth. The prose
rules already bound implementers (short constraint-only comments, no
decision-log or history narrative — that's tech-spec D-### territory,
docstrings state the contract not the change); new this release:
`audit.py clean` flags **essay comments** (a single comment line ≥120
chars, URLs exempt) and **comment walls** (≥8 consecutive comment
lines, markdown excluded — '#' there is a heading) as adjudication
suspects alongside debug prints/markers/commented-out calls, so the
closing audit's hygiene gate sees what was prose-only. The implementer
brief gains the extract-on-third-use rule (the third copy of any logic
is a bug — extract to the shared home inside the task's scope; crossing
scope is a deviation to report) with a matching guardrail, and
SKILL.md's anti-patterns list names the whole class (#13). Seven new
CommentSuspectTests (38 total in the audit suite).

## 2.2.0 — 2026-09-10

Two small fixes paired in one commit. (1) `audit.py archived` — the
OpenSpec `validate --archived` gate adopted natively: every dir under
specs/archive/ must hold a task.md with no unticked, unstruck entry
(ticked or struck both close; pure doc-state, no git, no SKIPPED path),
exit 1 naming the open entries — cheap enough for a pre-push hook, and
it makes "archived incomplete" mechanically visible instead of
lurking in the as-built record. Four new ArchivedModeTests. (2) The
one standing test failure is fixed:
test_real_workspace_probe_is_non_git asserted the in-repo fixture was
outside any git repo — a premise that broke the day SpecDevKit got its
first commit; the probe now uses a temp dir (a genuinely non-git
workspace), and the suite is 40/40 for the first time since the repo
went git.

## 2.1.0 — 2026-09-10

Three more harnesses supported — opencode, Factory Droid, and
Antigravity — bringing the matrix to six (ADR-015). opencode and droid
both scan `~/.agents/skills/**` as a compatibility root sync.sh already
populates, so their skill discovery works with zero new roots; their
gap was agent defs: new `tools/agent-defs.py` (shared, skill-agnostic,
same parse-and-derive contract as omp-defs.py) regenerates the eight
role briefs as opencode subagents (`~/.config/opencode/agents/` —
filename-named, mode: subagent, a permission map derived from each
brief's own `tools:` list, task always deny) and as Factory droids
(`~/.factory/droids/` — Task-tool subagent_types, `model: inherit`
always so a wrongly guessed model ID can never become a
DroidValidator load error, tools mapped to Factory IDs with read-only
sets collapsed to the `read-only` category). Both roots are OPTIONAL:
sync installs them only when the harness's own config home already
exists — it never fabricates a harness directory; install the harness,
re-run sync. Antigravity consumes the repo itself as a plugin: root
`plugin.json` (marker + name), `skills/` as-is, and a new committed
repo-root `agents/` of byte-verbatim role personas that
`agy plugin install` ships (sync.sh regenerates and verifies them each
run); `agy plugin validate` passes with 1 skill + 8 agents processed.
`skill-dir.sh` learns the agy plugin roots (workspace
`.agents/plugins/spec-dev-kit/` and `~/.gemini/config/plugins/
spec-dev-kit/`) so an agy session resolves its live in-plugin skill
dir. New `tools/tests/test_agent_defs.py` (10 tests: permission
derivation, tool-ID mapping, read-only collapse, byte-verbatim
personas, stale-removal scoping, name rejection).

## 2.0.0 — 2026-09-10

Skill renamed spec-to-prod → spec-to-prod — directory, router command
(`/spec-to-prod` → `/spec-to-prod`), plugin manifests (regenerated:
plugin name and marketplace entry now spec-to-prod), README, agent
briefs, scripts (skill-dir.sh resolution paths, sync.sh allowlist case,
omp/plugin tool references and their tests), diagram files, and every
cross-reference; historical entries below keep the old name. The
pipeline, docs contract, and agents (`spec-*` role names were never
tied to the skill name) are unchanged — pure rename, VERSION 2.0.0
because every command and plugin name moves. The rename also pins the
name's promise (ADR-014): "prod" = production-READY — the flow ends at
a verified single commit; push/deploy/publish stay standing human/CI
gates (the rulings rule already stop-and-asks each), and the graph has
deliberately no release node. Deployed installs: sync.sh installs
forward only — the old-name skill dirs and router command in the four
skill roots and three command roots are removed by hand during this
release's deploy.

## 1.13.0 — 2026-09-10

Lifecycle command surface adopted from addyosmani/agent-skills — six thin
command files (`commands/{spec,plan,build,test,review,ship}.md`) expose
the DEFINE→PLAN→BUILD→VERIFY→REVIEW→SHIP development lifecycle, each
delegating into the workflow graph at a node: /spec = the spec node +
clarify loop (scaffold's entry), /plan = waves from current doc state
through verify + before-audit to the approve gate, /build = the execute
node (implement waves), and /test + /review + /ship = the ONE closing
audit in three portions (proof + regression · scope diff + cleanliness +
DoD scorecard · tick-commit + rulings ack + Status done). The router's
own verb space is deliberately untouched — `plan`/`tech`/`qa` keep
their single-agent repair meanings, `review` keeps meaning the docs
reviewer — so the same words never silently change meaning across the
two surfaces (ADR-013); per-task commits and per-task verification from
the source surface are explicitly NOT adopted (two audits, one commit
stands). `tools/sync.sh` installs commands through an explicit per-skill
allowlist (`extra_commands()`): the skill-named router unconditionally,
the six bare names opt-in — never a blind glob — and a destination
holding a foreign file (exists, differs from the master, not a prior
recorded deploy — per-root provenance ledger) is refused loudly instead
of clobbered;
SKILL.md gains § Lifecycle commands and the closing audit names its
three lifecycle entry points.

## 1.12.0 — 2026-09-10

Plugin packaging for GitHub distribution — the repo becomes a Claude
Code / omp plugin marketplace (`.claude-plugin/marketplace.json`, repo
root), one plugin entry per skill, generated by new
`tools/plugin-manifest.py` from each skill's own SKILL.md frontmatter
and VERSION file (derived, regenerate-only — never hand-edited, same
shape as `tools/omp-defs.py`'s output). For a skill's directory to be an
independently installable plugin, its plugin root must be the skill
root: `commands/spec-to-prod.md` moves from the package-root `commands/`
into `skills/spec-to-prod/commands/`, so the skill no longer has any
content living outside its own directory — `tools/sync.sh` updated to
install the command router from its new nested path (same install
destinations, unaffected). Both generated manifests validated against
the real `claude plugin validate` CLI, not just the online manifest
reference: the doc's `repository` object-form example
(`{type, url, directory}`) is rejected by the installed CLI version,
corrected to the string form; `_shared-protocol.md` (shared prose every
role brief points at, not a role) is confirmed to surface as a harmless
`spec-to-prod:_shared-protocol` warning in Claude Code's plugin agent
scan — the manifest reference's own "merge, never replace" resolution
order rules out fixing this with a manifest field, so it's documented as
a known cosmetic gap rather than papered over. New root-level `LICENSE`
(MIT) and `.gitignore`. README gains an "Install as a plugin" section
(the new one-command path for Claude Code, omp, and zcode — omp reads
the identical `.claude-plugin/marketplace.json` as its documented
Claude-Code-compatible fallback) ahead of the existing manual
`tools/sync.sh` path, which stays for local development and harnesses
without a marketplace system.

## 1.11.0 — 2026-09-10

Install tooling generalized for a multi-skill repo — `tools/` (sync.sh,
omp-defs.py) moves from `skills/spec-to-prod/tools/` to the repo root,
shared across every skill under `skills/*/` instead of hardcoded to this
one. `omp-defs.py` drops its per-role `MODEL`/`THINKING`/`TOOLS` tables:
it now parses each source role's own Claude-style frontmatter directly
(`tools:`, `model:`, `effort:`) and derives the omp-side frontmatter from
that — decisions/012's tiering rule ("port whatever the Claude-side
frontmatter already says") is now the literal parsing rule instead of a
hand-maintained two-entry dict, checked byte-identical against the prior
hardcoded output for all eight roles before the switch (new
`tools/tests/test_omp_defs.py`, 15 tests, up from 7). Stale-output
cleanup in a shared `--out` dir is scoped to the common basename prefix
across a skill's own role files (`spec-` for this skill); with no such
prefix, cleanup is skipped rather than guessing ownership of another
skill's file — covered by a dedicated cross-skill isolation test, and by
a synthetic second skill proving the generator needs no skill-specific
code to onboard one. `tools/sync.sh` gained a fourth harness target,
`~/.zcode/skills/` (+ `~/.zcode/commands/`): `scripts/skill-dir.sh` and
SKILL.md's own resolution order already named
`.zcode/skills/spec-to-prod/` as a valid root — sync.sh had simply never
populated it. zcode still gets no `agents/` install step (no Claude-def
copy, no omp-defs regeneration): SKILL.md's spawn mechanics already
document zcode as having no user-installable agent types, and this pass
didn't verify that claim itself, only the skills/commands gap. Root
`README.md` documents the resulting layout and how to add a new skill.

## 1.10.0 — 2026-09-10

omp model tiering — `tools/omp-defs.py` gains a `MODEL` dict, applied
only to `spec-surveyor` and `spec-researcher`: `model: "@smol"` (quoted
— `@` is a reserved YAML indicator, so unquoted would be a parse
hazard), omp's built-in zero-config fast/cheap model-role alias. Ports
forward a decision the Claude-side defs already made and omp-defs.py
previously dropped entirely (its own docstring said "No `model` field
=> inherit the parent session's model" with no exception) —
`agents/spec-surveyor.md`/`spec-researcher.md` already say `model:
sonnet`, not the flagship default, so under omp every spawn of those
two mechanical/evidence-gathering roles was silently paying the
orchestrating session's full model rate. Every other role stays
model-less (inherit), matching its own `model: inherit` — `spec-
implementer` and `spec-reviewer` explicitly excluded and locked by a
new regression test, since code correctness and adversarial judgment
shouldn't run cheaper without the same kind of explicit, reviewed
decision. New `tests/test_omp_defs.py` (7 tests) — omp-defs.py had zero
automated coverage before this. See decisions/012.

## 1.9.0 — 2026-09-10

omp native execution — 1.8.0 made the skill discoverable inside omp
(skill copy + task-agent defs); this pass makes the workflow's own
execution mechanics use omp's primitives instead of only harness-neutral
ones. New SKILL.md § "Running under omp": the wave as the `task` tool's
`tasks[]` array with shared payload in `context`; `outputSchema` as
optional mechanical enforcement of a brief's existing `digest:` shape
(fields unchanged — enforcement, not a new contract, so contracts/
docset.md's return-contract item now says so explicitly); auto-delivered
results (no polling — `hub` wait only when genuinely blocked); the
`tools/omp-defs.py`-generated defs granting no `spec-*` role a `hub` tool,
so § Independent spawns' no-peer-messaging rule is harness-enforced under
omp, not just stated; and an eval-kernel recipe that imports `specstate`/
`check`/`audit`/`graph` once per session for in-process frontier
recompute instead of a fresh `python3 scripts/graph.py` interpreter+import
per wave (the loop's actual hot path). Enabling that recipe: `check.py`/
`audit.py`'s `main()` now takes an optional `argv` (default `None` reads
`sys.argv`, byte-identical CLI behavior — `graph.py`'s own internal
check.py/audit.py probes deliberately keep shelling out via `subprocess`,
unchanged, for output isolation; this only unblocks external in-process
callers). New MainArgvTests in tests/test_check.py and tests/test_audit.py
lock the argv path against the CLI path and against ambient-sys.argv
leakage. `xd://lsp`/`ast_edit` reachability was checked empirically, not
assumed: spawning a real `spec-surveyor` and calling `write
path=xd://lsp` returned `Mounted devices: .` (empty) despite the role's
frontmatter granting `write` — device mounting is separate from the base
tool allowlist, and a default task spawn gets none. Surveyor/implementer
briefs stay scoped to what a spawned subagent can verify it has (a
repo-specific code-intelligence CLI via its own tools, when the repo
ships one); SKILL.md's omp section instead names `lsp`/`ast_edit` as the
orchestrator's own-session tools, for its own inline work, never a
subagent capability. See decisions/011.

## 1.8.0 — 2026-09-10

omp (Oh My Pi) install target — the skill now runs fully inside omp:
omp-native skill copy at ~/.omp/agent/skills/spec-to-prod/
(priority-100 provider; ~/.agents/skills would also serve omp via its
`agents` provider, but the native copy is self-sufficient and wins the
name dedup). scripts/skill-dir.sh and SKILL.md's spawn-mechanics root
order now know the .omp roots (omp-native first, mirroring omp's
provider precedence) so spawn payloads resolve skill_dir to the copy
the session actually loaded. Task agents were the other gap: omp
discovers them only from .omp/agents dirs, intentionally skipping
~/.claude/agents, and its tool registry is lowercase — new
tools/omp-defs.py regenerates the eight spec-* defs with omp
frontmatter (lowercase tool allowlists, one-line descriptions,
thinking-level for the two `effort: low` roles) over the shared brief
bodies — derived regenerate-only artifacts, never hand-edited. sync.sh
installs and verifies the skill copy and the defs; the agent-def
verify is per spec-*.md file, since ~/.omp/agent/agents is a shared
root (omp agents unpack, hand-added defs).

## 1.7.1 — 2026-09-10

Restraint adoptions from Ponytail (MIT,
github.com/dietrichgebert/ponytail) — three brief/template edits, no
pipeline mechanics touched. Most of Ponytail's ladder was already
independently present (implementer reuse-before-write, smallest-change,
new-dependency-as-deviation; audit.py's cleanliness sweep; the
already-done sweep); adopted only the missing pieces:

- Implementer brief: "smallest change" now carries an explicit
  exemption — validation, error handling, security, and accessibility
  are never the place to be small (Method step 2 + Guardrails). Ponytail's
  benchmark showed bare minimalism prompts degrade safety; the
  exemption is what keeps it.
- Reviewer brief: finding 5 widens from scope-creep tasks to
  scope-creep or over-build — speculative single-caller abstractions,
  premature configurability, defensive fallbacks beyond requirements in
  tech-spec design — with the deletion test ("what could be removed
  with no FR made worse?"); guardrail updated (over-build in scope,
  taste not). Frontmatter description aligned.
- Constitution template: new example article C-04 (reuse before
  writing; no new abstraction with a single caller).

Deliberately not adopted: a separate debt ledger (D-### rulings already
are it — decision-007 one-representation), a gain scoreboard (conflicts
with decision-004 conjunctive DoD), intensity modes/global hooks/
marketplace plumbing (per-spec pipeline, not an always-on ruleset).

## 1.7.0 — 2026-09-09

The fixed Stage 0–4 pipeline becomes a dynamic state-graph workflow —
see decisions/010, which generalizes D-002 (state-in-docs), D-006
(parallel-by-default), and D-009 (frontier grilling) and supersedes the
stage-normative wording, not the prior ADR texts. New `scripts/
specstate.py` (doc-state parsers extracted from check.py/audit.py; their
CLIs, outputs, and exit codes unchanged) and `scripts/graph.py` — the
mechanical truth the orchestrator schedules from: frontier report,
`--state-json` / `--mermaid` / `--explain`, `--emit-spawns` self-contained
spawn payloads, and the `--run` auto-trigger loop that pauses
`AWAITING HUMAN` at every judgment node (clarify, an undetermined
research-gate, before-audit, approve, the closing-audit judgment,
tick-commit — human gates are never auto-satisfied). SKILL.md and every
normative doc (contract, the 8 briefs, both gates files, templates,
bugfix reference, router, diagrams) rewritten from stage scheduling to
frontier scheduling — "run the ready frontier as one wave, recompute,
repeat"; stages survive only as one orientation note, while phases inside
plan.md/task.md stay (the implementation graph). Non-git honesty:
git-dependent checks degrade to explicit `SKIPPED (not a git repo)`
notices instead of silent all-clears (check.py's staleness line;
audit.py scope/clean/converge, which also distinguishes "no git
repository" from "no committed baseline"). Router gains `graph <spec>`
(live graph report) and `run <spec>` (continue the full pipeline from
current doc state), closing the missing continue-verb gap; `converge
--repo` semantics aligned across SKILL.md, the router, and audit.py.
Consistency findings from the agent/router audit fixed: reviewer
exempted from the `_shared-protocol.md` prepend (named in SKILL.md),
implementer denies NotebookEdit, SendMessage denies aligned across
briefs, digest budgets aligned (reviewer ≤20 the named exception),
acceptance-command wording aligned ("always for code tasks"). New
repo-root README; workflow diagram + both HTML renders regenerated as
the state graph (dropping the stale "up to 5 questions, one at a time"
note). Test suite extended for specstate parsers, graph frontier
transitions, executor payloads, git-mocked degradation, and audit
parsers.

## 1.6.0 — 2026-09-08

Stage-0 clarify pass adopts the round/frontier "grilling" model — see
decisions/009. Replaces "one decision at a time" (adopted from ai-devkit
in 1.3.0) with: map the draft's gaps as a design tree, batch every
question whose prerequisites are settled into one numbered round with a
recommended answer each, recompute the frontier from the round's answers,
repeat until the frontier is empty (no fixed question count). Makes
explicit that a fact ("does X already exist") is the orchestrator's to
look up, never the user's to be asked. Tri-state closure (answered /
deferred / named assumption) and the "no progress past a still-draft
spec" gate are unchanged. Adapted from Matt Pocock's `grilling` skill
(MIT, github.com/mattpocock/skills) — vendored as prose in SKILL.md, not
a runtime dependency on that plugin. SKILL.md § Stage 0 and
commands/spec-to-prod.md's `scaffold` verb updated.

## 1.5.0 — 2026-09-08

Second GitHub parity pass (spec-kit, BMAD-METHOD, Agent OS) — see
decisions/008. Reverse FR-coverage ("every FR has a task and a test
case") was already covered by existing traceability checks; no change.
Adopted:

- `check.py --constitution`: standalone presence/fill check for
  specs/CONSTITUTION.md; the full check now FAILs (was WARN-only) once a
  second spec exists in the repo and the constitution is still missing,
  empty, or unfilled template.
- `audit.py converge <spec-dir>`: diffs a freshly re-run survey.md against
  its last committed version (git), printing `NEW GAP`/`REGRESSED` items
  for the orchestrator to turn into tasks. New "converge" verb in
  SKILL.md § Run modes and the command router.
- `check.py --checklist`: (re)generates a derived, regenerate-only
  `specs/<name>/checklist.md` (FR/AC summary) — never hand-edited, never
  read by check.py's own status checks, task.md remains the only status
  holder.
- Implementer fix rounds (2+): one named exception to "never touch
  specs/" — `specs/<name>/notes/T###.md`, own task ID only, a scratch
  note carried into the next re-brief.
- Surveyor brief: optional `## area: <name>` tagging in
  specs/context/tech.md for large repos, so a later spec reads only the
  relevant slice.

## 1.4.1 — 2026-09-08

Agents folder merged to one file per role: `agents/spec-*.md` is now the
harness def (frontmatter: tools/readonly/model) with the full brief as its
body — the separate thin-pointer defs (`agents/defs/`) and plain briefs
are gone. Kills the def/brief drift class (already bit once in the
round-6 review); def-spawns are self-contained (body IS the system
prompt); fallback spawns strip the frontmatter. Def-only emphasis
preserved (implementer path-scoping warning, tech no-web-tool rationale,
qa/task-breaker hard rules, reviewer solo exemption from
_shared-protocol.md). Supersedes decision 005 (see decisions/007).
SKILL.md spawn mechanics + role table re-pointed; tools/sync.sh def copy
updated.

## 1.4.0 — 2026-09-08

Structure refactor to the pro-max skill layout. No pipeline behavior
changes.

- **Moved**: `assets/templates/` → `templates/`; `references/agents/*`
  (9 briefs) → `agents/`; `references/dod.md` → `gates/dod.md`; harness
  defs `agents/spec-*.md` (package root) → `agents/defs/` — the skill is
  now one self-contained directory.
- **Added**: `contracts/docset.md` (canonical doc-set/ownership/payload
  contract), `gates/before-audit.md` (detail extracted from SKILL.md),
  `VERSION`, `CHANGELOG.md`, `evals/cases.md`, `decisions/` (6 ADRs),
  `observations/open-items.md`, `examples/mini-spec/` (green fixture used
  by tests), `tests/` (unittest suite for check.py, via
  `tests/run.sh`), `tools/sync.sh` (master → ~/.agents + ~/.claude,
  SHA-verified).
- All cross-references updated (8 defs, scaffold.sh, audit.py, SKILL.md,
  command router unaffected).

## 1.3.0 — 2026-09-08

ai-devkit adoptions (github.com/codeaholicguy/ai-devkit), after a parity
pass rejected everything spec-to-prod already had:

1. Tech brief: design screens — caller-first APIs, red flags (shallow
   modules, pass-through layers, temporal decomposition, leaked
   transport/storage types, scattered validation, synchronized flags),
   subtract-before-add; kept red flags ship as D-###.
2. Implementer brief: reuse-before-write (clean fit only; stdlib/existing
   deps over new) + breaking-change discipline (in-repo atomic + delete;
   external parallel-change + deprecate).
3. Stage-0 clarify pass: one decision at a time (why it matters, 2–3
   options, recommendation); tri-state closure — answered, explicitly
   deferred, or named assumption, never left open.
4. Closing-audit proof step: fresh-evidence rule (this session's command
   + output, or it isn't a pass) + flaky-TC rule (flaky ≠ ignorable — fix
   or park with a D-###).
5. Rulings report names every irreversible/state-mutating change shipped.
6. dod.md: hedged-claim ban ("should pass", "ran it earlier" ≠ evidence).

## 1.2.0 — 2026-08-25

Seven review rounds + competitor adoptions (spec-kit, OpenSpec, Kiro,
BMAD rejected per-story gates, sweep):

- Constitution (specs/CONSTITUTION.md, before-audit gate, implementer
  payload), Stage-0 clarify pass (first version), EARS-shaped FRs with a
  check.py WARN, persistent context baseline (specs/context/), archive
  at done (archive.sh + INDEX repoint).
- DoD scorecard: conjunctive 10-gate table (gates/dod.md, then
  references/dod.md) + `audit.py dod`.
- Mechanization tier: `audit.py scope|clean|proofs`; check.py additions
  (traceability, burndown, status-bleed, citation reality, staleness,
  verify-command reality); vague-phrase WARN.

## 1.0.0 — 2026-08-24

Initial pipeline: Stage 0–4, surveyor ∥ researcher → planner ∥ tech ∥ qa
→ task-breaker, thin-pointer agent defs, check.py.
