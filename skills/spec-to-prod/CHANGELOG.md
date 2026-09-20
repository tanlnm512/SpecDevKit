# Changelog — spec-to-prod

Release history. Versions earlier than 1.2 are retrofitted from session
records — the changelog itself starts 2026-09-08.


## 2.7.1 — 2026-09-20

Workflow-run efficiency pass (D-020), same contracts: (1) the claude
dialect fetches graph state and payload emission in ONE probe agent per
wave (a single shell line running `--state-json` + `--emit-spawns`,
outputs marker-split), and the final summary reuses the last post-wave
state — ~3 agent calls per wave down to 1; the zcode dialect keeps its
direct world.run calls (local subprocesses, no agent cost). (2) Both
dialects gained a bounded re-brief round: a wave that changed no doc
state retries its failed payloads (status blocked/gap) exactly once per
run, the failure digest verbatim appended to the retry ask; if the
retry also changes nothing the run stops no-change and names rounds 2+
as the orchestrator's — the playbook's own mechanical fix-round-1
automated, judgment rounds untouched. (3) SKILL.md § Dynamic workflow
runs documents the cost/unattended levers: staged subagent-model tiering
on zcode (cheap model for analysis waves, default for execute), scheduled/
off-peak runs (safe only post-approve — the run parks at the
closing-audit ack by design), and pre-approving the probe command in
Claude permission rules so runs don't stall on prompts. Tests:
test_workflow_defs.py 26 cases — new single-probe-per-wave and bounded-
re-brief invariants on both dialects.

## 2.7.0 — 2026-09-20

Dynamic-workflow dialects: the frontier loop as generated, harness-native
workflow scripts (D-019) — the third application of the D-015 dialect
pattern (omp-defs → agent-defs → workflow-defs). `tools/workflow-defs.py`
emits two committed regenerate-only artifacts under
`skills/spec-to-prod/workflows/` — `spec-run.dwf.ts` (zcode dynamic
workflows: typed agent().ask waves, literal phases, world.run invocations
of graph.py, a published markdown run summary) and `spec-run.js` (Claude
Code dynamic workflows: `export const meta` first statement,
agent/pipeline/phase primitives, schema-validated digests, a single
graph-probe agent as the shell seam — the script itself has no fs/shell
there). Both are thin loops over the unchanged engine: state from
`graph.py --state-json`, waves spawned from `--emit-spawns` payloads, and
the exact find_pause gate set stopping the run AWAITING HUMAN (clarify ·
undetermined research-gate · before-audit · approve · closing-audit ·
tick-commit) — never auto-satisfied; a rerun resumes from doc state.
Neither dialect implements a readiness rule. New `tools/install-workflow.sh
zcode|claude|all` installs each dialect to its own root
(`~/.zcode/workflows/` · `~/.claude/workflows/`, `--project` variants),
baking the target root's own skill copy into the installed file (a runtime
skill_dir arg overrides), under sync.sh's provenance-ledger refusal
discipline, skipping loudly where a harness home is absent; `tools/sync.sh`
installs and verifies both, gated per harness home. Tests:
tools/tests/test_workflow_defs.py (generator determinism + --check,
per-dialect structural invariants, cross-dialect gate parity, installer
behavior under a fake HOME: install, foreign refusal, drift detection,
absent-home skip, sync integration). Docs: SKILL.md § Dynamic workflow
runs, README harness-table/install entries. omp keeps its documented
kernel recipe and Droid/Codex keep their orchestrator-session shapes —
a dialect is emitted only where a scriptable workflow runtime exists.

## 2.6.1 — 2026-09-16

Clarify-pass hard-stop on unanswered question rounds (D-018). A question
round put to the user is a HUMAN gate: when the harness's question tool
resolves without user answers — autonomous-run harnesses don't wait;
ZCode returns "user did not provide answers" in under a second — the
orchestrator prints the round in chat (❓ format verbatim) and ends the
turn, never adopting the ➡️ recommendations or resolving the NEEDS
CLARIFICATION markers itself. Open markers already hold the spec node
(graph.py keeps the frontier at `clarify`), so the stop is resume-clean:
the user's next message carries the answers. Execution mode's
rulings-not-stalls gains an explicit scope clause — mid-implementation
conflicts on an approved plan only, never a clarify/approve-gate
fallback. Prose-only, no script changes; motivated by an observed ZCode
run (cairn, agent-skills-output spec) where two FR rulings were
self-answered from recommendations after the question call auto-resolved
in 0.3s.


## 2.6.0 — 2026-09-13

Factory Droid spec-mode and mission-mode support, kept as a separate
surface from every other harness (D-017). (1) `references/droid-modes.md`
maps Droid's session modes onto the workflow graph: Spec Mode is the
authoring phase on paper only (Spec Mode is hard read-only and spawned
subagents clamp read-only — the spec.md draft and the researcher-gate
decision ride in the ExitSpecMode plan; scaffold + writes start in
Normal mode, and ExitSpecMode approval never writes `Status:
approved`); Mission Mode runs only from the orchestrator session
(subagents cannot spawn subagents, so mission workers can never run a
wave); mission scrutiny/user-testing default to skipped for
spec-to-prod features (the closing audit + DoD already govern); Task
`complexity` carries the cost tier — light = surveyor/researcher/
task-breaker/implementer, mirroring the briefs' `model:` frontmatter.
(2) `references/mission-brief.md` is the mission-planning skeleton:
features → specs, milestones → frontier bands, pause ledger, validation
settings. SKILL.md carries only a pointer section. (3) sync.sh installs
the router + `extra.txt` bare names to `~/.factory/commands` from a
separate `~/.factory`-gated block with its own verify pass — the
shared COMMANDS_ROOTS path is untouched; `/spec`…`/ship` now work as
native Droid slash commands where the harness is installed. (4)
test_sync.py gains DroidCommandsTests (absent-home skip, gated
install, idempotence, foreign-file refusal); the commands install/verify
logic is factored into `install_command`/`verify_command` used by both
paths.


## 2.5.1 — 2026-09-13

Install-safety and consistency hardening from the validation pass
(architecture / functionality / value audit). (1) Foreign-file refusal
now covers every install root, not just command roots: skills trees
(`~/.agents|/.claude|/.zcode/skills/<name>/`, `~/.omp/agent/skills/<name>/`)
and `~/.claude/agents/` keep a per-root provenance ledger
(`.spec-dev-kit-deployed`, hidden, inert) — a destination file absent
from the master is auto-deleted only when its hash sits in the ledger
(a stale deploy of ours) and refused loudly otherwise; `rsync
--delete`'s silent sweep is gone, and `verify_tree` excludes the
ledger. (2) omp-defs.py's stale cleanup proves ownership before
deleting: each skill writes a `.spec-dev-kit-omp-defs-<skill>` manifest
of the files it generated; only manifest-listed, hash-matching files
are removed — a foreign `spec-*.md` in the shared `~/.omp/agent/agents`
root is never touched, and a generated file edited since generation is
kept with a loud note (the prefix heuristic is gone). (3) The bare-name
allowlist moved out of sync.sh into the skill itself —
`commands/extra.txt`, one line of space-separated bare names —
replacing the hardcoded `extra_commands()` case table (ADR-013
amended). (4) New `tools/tests/test_manifests.py` locks VERSION ==
SKILL.md frontmatter version == plugin.json version per skill, and
`tools/tests/test_sync.py` runs sync.sh end-to-end on a repo copy with
a fake HOME (fresh install, idempotence, foreign refusal, stale-own
cleanup, absent-harness skips, version-drift detection) — the
installer's safety behavior is no longer untested. (5) Doc fixes from
the validation: `specs/context/` added to docset.md's derived inventory
(it is a surveyor output), ADR-010's node arithmetic corrected (16 = 6
single-agent nodes + execute + 9 orchestrator/mechanical), SKILL.md's
closing step cites DoD gates 9–10 (rulings + sign-off), and dod.md gate
8 records `reviewer not spawned — N/A` for specs that skipped the
reviewer.


## 2.5.0 — 2026-09-13

Session-hardening from a 12-task, 13-decision execution (indexing-exact-rate).
(1) New `scripts/tick.py`: the closing tick is mechanical — ticks `- [ ] T###`
to `- [x]`, inserts one `done <date> — <proof>` line, strips the
`(in-progress)` claim, and defers burndown arithmetic to `check.py
--fix-burndown`; validates atomically (unknown/duplicate/re-tick refused,
nothing written) and re-parses to prove only the intended state changed.
Hand-editing a dozen entries gutted an as-built record this session (entry
bodies and checkpoint comments must survive byte-identical into the archive).
SKILL.md step 11 now points here. (2) Verdicts carry evidence: check.py's
placeholder/vague WARNs and graph.py's unfilled-template reasons print
`token@line` (fenced-block content scanned — the recurring hiding spot);
the D-label WARN names the expected Context/Decision/Consequences shape.
(3) audit.py proofs reports TIMEOUT as its own verdict with a remediation
hint instead of a bare FAIL, and `clean` tolerates an ignored spec-dir
positional. (4) Brief rules: tech must sweep the test tree for
default-flip assertion shapes (flag / exact-count / exact-traffic /
behavior) — "kwarg-less call sites stay green" under-enumerated three
times this session; qa bounds every auto TC well under the proofs 120s cap;
implementers run acceptance after the final file write. (5) SKILL.md: the
research-gate skip marker is now given byte-exact (a prefixed form reads
as "ran"); Execution step 5 states the D-### label contract, the
literal-path rule, and the superseded-number sibling-grep; before-audit
gate 2 names the pre-existing-red-baseline path (baseline-repair commit
or D-### known-red — never start execute on unexplained red).

## 2.4.0 — 2026-09-13

Cost work, two halves. (1) D-016 extends the cheap tier to the two
volume roles: `spec-task-breaker` and `spec-implementer` briefs say
`model: sonnet` (ported to omp's `@smol` by the existing data-driven
omp-defs.py — no code change), leaving reviewer/planner/tech/qa on the
session model. The implementer's fix-round ladder now escalates from
the cheap tier: rounds 4–5's "capability tier up" is the Spawn-mechanics
step-3 fallback — the same brief body on a generic default-model agent.
The omp-defs lock test narrows to reviewer-only. (2) Converge re-surveys
go delta-scoped: a stale survey baseline gets a `DELTA RE-SURVEY` block
in its spawn payload (code files git says changed since the baseline
commit — the specs tree excluded, so a docs-only commit reads "no code
files changed" instead of forcing a re-survey; via new
`specstate.diff_paths`, a citation in an unchanged file cannot
have moved), the surveyor brief gains the merge-don't-rebuild method,
and `graph.py --emit-spawns --repair <node>` emits one non-frontier
agent node's payload — the single-agent repair-run instrument, so the
converge re-survey's payload is mechanically buildable instead of
hand-assembled. Degradations stay loud: git that can't scope the delta
says "re-survey in full", never a silent empty delta. New EXEC-011
suite (delta payload, repair emit, CLI validation) and DiffPathsTests.

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
