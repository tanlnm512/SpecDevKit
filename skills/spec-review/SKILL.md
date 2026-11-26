---
name: spec-review
description: >-
  Gated code review for any git repository — a diff, a pull request, a
  branch, or the whole project. Costlier than a plain review: it runs
  the repo's own checks as a mechanical gate, then a multi-lens
  specialist panel (correctness, security, quality & tests),
  independent confirmation of every kept finding, and an optional
  verified fix loop — several subagent turns per run. Use for "review
  the diff", "review PR 12", "review this branch", "review the
  project", or "review and fix" when the verdict must hold up; for a
  quick look, use a plain review. Not a spec's delivery review
  (spec-build).
metadata:
  owner: platform-core
  version: "0.1.1"
---

# spec-review — gated, confirmed code review (with optional fix loop)

Review a git change the way a strict panel would: the repo's own checks
decide everything mechanical first, specialist reviewers own what only a
reader can see, no finding reaches the user without independent
confirmation, and — when asked — an author agent fixes what the panel
confirmed, with every fix re-verified.

## When to use

The user asks to review a change ("review the diff", "review the last
commit", "look over my working tree before I commit"), a pull request
("review PR 12"), a branch ("review what's on this branch"), the whole
codebase ("review the project") — or to review AND fix any of these
("review and fix the findings").

## Principles

The panel's contract, in priority order. When two rules collide, the
higher number wins; when a change would violate any of them, the
change is wrong — not the rule.

1. **Machine-decidable before human attention.** Everything a
   deterministic check can decide (tests, syntax, secret shapes) is
   decided by the gate; reviewers own only what requires reading.
2. **Evidence or it does not exist.** Every finding carries `path:line`
   and the quoted lines a reader can re-derive it from.
3. **Independence beats volume.** The reviewer, the confirmer, the
   fixer and the fresh-eyes fix reviewer are different agents;
   precision over recall.
4. **Zero findings is success.** Clean targets get empty lists, and
   style/formatting is never a finding (the repo's checks own it).
5. **Stated intent is context, not a waiver.** The author's words steer
   triage of deliberate choices; they never excuse a demonstrable
   defect.
6. **AI advises, the human decides.** The run ends in a recommendation
   and uncommitted fixes; judgment calls route to `human`, and the
   commit is always the user's.
7. **Honesty about coverage.** `notCovered` separates "looked and
   clean" from "never looked"; unconfirmed findings are labelled, never
   dropped; triage drops come with reasons.
8. **The repo owns its standards.** The gate runs the repo's OWN
   checks; rules live in `AGENTS.md`/`CLAUDE.md`; fixes follow the
   repo's style.

## Review targets

One `target` picks what the panel reviews; `contracts/panel.md`
§ Targets is the canonical resolution table:

- **diff** (default) — the change against a base ref: the working
  tree (`base: HEAD`), the last commit (`HEAD~1`), or any ref/branch.
- **branch** — the merge-base diff against a base branch (explicit
  `base`, else the remote's default); uncommitted work is included
  and noted in the report.
- **pr** — a GitHub pull request (`pr`: number, URL, or
  `owner/repo#N`, resolved with the gh CLI).
- **project** — the codebase as it stands; in a multi-repo workspace
  pass `repo`: the sub-repo directory, resolved to its absolute
  toplevel before anything runs (see panel.md § Targets for the
  resolution and sharding rules). `repo` is supported for `project`
  only.

Stage 1 always runs first with the resolved base: `--base
<merge-base>` in diff/branch/pr mode, `--tree` in project mode.

## The three stages (and the optional fourth)

### Stage 1 — the mechanical gate, always first

```bash
bash <skill-dir>/scripts/gate.sh --base HEAD        # working-tree changes
bash <skill-dir>/scripts/gate.sh --base HEAD~1      # the last commit
bash <skill-dir>/scripts/gate.sh --base <merge-base>  # branch / PR mode
bash <skill-dir>/scripts/gate.sh --tree             # project mode
bash <skill-dir>/scripts/gate.sh --plan             # what it would run
```

It detects and runs the repo's OWN checks (Makefile targets, npm
scripts, cargo/go, pytest or unittest discover, and a dependency
audit the repo's config names — `source: repo`), plus built-in
hygiene (`source: builtin`): `bash -n` on changed `*.sh`, a
secret-shape scan of the change (hits name `path:line` and the
pattern, never the token), and an informational row listing changed
dependency-manifest lines — name every new dependency in the report.
It prints a JSON array — one `{name, source, status, exit_code, tail}`
per check, `status` pass/fail/timed_out (each repo check is killed
after `GATE_CHECK_TIMEOUT`, default 600 s).

Rules: a red gate ends a fresh review — report the failing checks with
their tails as the findings, and stop (exception: a project audit
continues, each failing check a high-severity gate finding — panel.md
§ The mechanical gate). No `repo` row is NOT a green light, whatever
the built-in rows say: ask the repo for its documented check command
and run that, or say "no repo checks detected". Reviewers never re-run
the suites.

### Whole-project mode (target: project)

The gate runs `--tree`; the review target is every tracked source
file (extension-filtered; lockfiles, generated code and vendored/build
directories excluded), sharded when too large for one turn (bounds in
panel.md § Targets — every lens reads every part, so coverage is
complete). There is no diff: the flagging bar's "introduced by this
change" becomes "present in the code as it stands", and confirmation
drops the introduced-by clause. The fix loop is unchanged; `merge`
reads "the code is ready as it stands". Narrow the target with
explicit `paths`.

### Preflight (stage 1.5) — the scout maps the ground

Between a green gate and the first reviewer, one read-only scout
returns `modules` / `conventions` / `riskAreas` — bounded, and riding
the reviewer asks and final assessment as context, never as evidence
(confirmers never see it, so a scout error cannot rubber-stamp a
finding). A scout that fails degrades to the raw target (named under
`notCovered`); `fix_from` runs skip the step. Canonical: panel.md
§ Preflight; the brief is `agents/spec-review-scout.md`.

### Stage 2 — specialist review with triage and confirmation

Review the change — the diff file the oracle writes into the run
folder, plus the untracked files scope lists, read in full —
through separate lenses, in parallel where you can:

- **correctness** — logic errors, edge cases, error handling,
  concurrency, caller/callee contracts;
- **security** — untrusted input paths, injection, secrets and tokens,
  permissions, destructive operations;
- **quality & tests** — complexity the next reader pays for,
  misleading names, doc drift, design fit (against a labelled
  design-smell baseline — always judgement calls, the repo
  overriding), and tests: changed behavior with no covering test,
  tests that cannot fail.

Each lens is an agent brief carrying its full checklist —
`agents/spec-review-correctness.md`, `spec-review-security.md`,
`spec-review-quality.md` — over the shared
`protocol/panel-protocol.md`. With subagent dispatch, spawn one
brief per lens rather than simulating a lens yourself; without it,
cover the lenses inline from the briefs' rubric sections, never from
memory. `mode` (§ Run sequence) picks between one general reviewer and
the full three-lens panel.

Every reviewer follows the panel contract (`protocol/panel-protocol.md` is
canonical): read the FULL target and the surrounding files, following
call sites when a defect depends on them; read the repo's rules
(`AGENTS.md`/`CLAUDE.md`) first and cite any rule a finding violates;
the flagging bar — discrete, in-target, demonstrable, fixable; an
impact sentence above the minor level; the exclusions (speculation,
style/formatting, intentional behavior changes, pre-existing problems
the change does not worsen); the severity ladder; `path:line` on the
new side; zero findings is the expected answer for a clean target.

**Stated intent.** The `intent` arg (or the PR description in pr mode)
reaches reviewers and triage verbatim and judges against it: a
deliberate choice stated up front is an intentional behavior change,
not a finding — the author's rebuttal channel for unattended runs,
which never waives a demonstrable defect. Confirmation stays
intent-blind on purpose.

One **triage editor** dedupes across lenses and drops style nits,
speculation and pre-existing issues (with a one-line reason each) —
stingy, but never suppressing a real defect. Then every KEPT finding
is **independently confirmed** by someone who did not write it.
Findings that fail confirmation are kept and labelled `unconfirmed`,
never silently dropped. Confirmation run inline — no subagent
dispatch, or `mode fast` — is not independent: mark each such finding
`confirmation.self_checked: true` so the report labels it
`unconfirmed (self-checked)`; a session never labels its own check
`verified`. The confirmer is a brief of its own
(`agents/spec-review-confirmer.md`), as the fix verifier is
(`agents/spec-review-verifier.md`, stage 4) — each brief's body is its
stage's system prompt (`contracts/run-sequence.md` § Who runs each
role).

### Stage 3 — synthesis

One assessment (the triage editor, for a consistent scale) produces:
overall **risk** (low/medium/high), **test gaps**, **residual
risks**, and a verdict — reporting what was checked (the gate's
commands) and what was not. A change over the split bounds (panel.md
§ The report) also earns a one-line recommendation to split it.

### Stage 4 (optional) — the fix loop

When the user asked to fix as well, run bounded rounds (default 2):

1. An **author/fixer** (`agents/spec-review-fixer.md`) fixes the
   confirmed findings in the working tree: repo rules first, minimal,
   repo style, NEVER commits, never weakens a test to make a finding
   go away (pin corrected behavior instead). That brief carries the
   kit-wide engineering rules (§ Engineering rules: test discipline,
   backgrounded-job discipline, code commenting) — they bind the fix
   loop's every edit.
2. Every attempted fix is verified by an independent reader: `fixed` /
   `unfixed` / `worse` — a fix that weakens a test is `worse`. A
   fixer **skip is ruled on, not counted**: `rejected-valid` (the
   reason holds — the finding is withdrawn) or `rejected-invalid`
   (the finding stands); an unruled skip stands.
3. A fixer **out-of-scope** item (the sound fix needs paths or
   behavior this change must not touch) burns no round: it leaves the
   loop and is surfaced in the report as the user's widening call.
4. The gate re-runs; failures become findings the fixer must clear.
5. A fresh-eyes reviewer scans the diff of exactly the paths the fixer
   touched, for NEW defects the fixes introduce.
6. Loop until everything is resolved or rounds run out.

**The review-then-ask flow.** An unattended run cannot pause mid-run
to ask, so the decision gate is a second run: run a review first
(`fix_rounds: 0`), present the findings, and if the user fixes, run
again with `fix_from` — the previous report's markdown, or its
findings JSON (schema: `templates/fix-from-findings.json`) — plus
`fix_rounds`. That run skips the review stages entirely and ends with
the recommendation.

End with a **recommendation**: `merge` (everything fixed, gate green,
nothing new, and no standing infrastructure-or-unknown CI row),
`fix-first` (ordinary findings remain), or `human`
(judgment calls, unconfirmed residue, or a standing CI row whose
rerun is the user's call). The oracle derives the floor
from the report's own state and rejects a claim below it — escalating
on judgment is always allowed (`gates/recommendation.md`).
When the verdict is `human`, or a spent fix loop leaves findings
unresolved, the report also carries the **stop ask** (`stopAsk`):
its content and the runs that carry one — `gates/recommendation.md`
§ Consequential stops. Put it to the user through the harness's
structured question tool where one exists (the options as choices, a
recommended one first and marked), otherwise print it — and stop: an
unanswered ask is not an answer. Fixes stay uncommitted — the commit
decision and message are the user's.

## Run sequence (driving the oracle)

`O` = `python3 <skill-dir>/scripts/review_orchestrator.py`; every call
prints one JSON object, and `status: error` stops the run.
`contracts/run-sequence.md` is canonical — commands, ask ctx keys,
report data, role table, order: read it before the first `O` call.
Phases: `O scope … --include-gate` → `O run-init` (the checkpoint
starts) → `O systems` → the scout ask → the review wave
(`O ask`) → triage per lens → cross-lens → confirm each kept finding →
the final ask → `O report --kind review`; when fixing, per round
`O fix-snapshot` → fixer → `O fix-check` → `O gate` → verify →
fix-review, then `O report --kind fix`. `O run-save --run-dir D
--stage <stage> --data @F.json` after EVERY stage — the stage names
are the oracle's `STAGES` tuple. A failed call is not a round:
re-run the same stage, three tries, then stop and tell the owner
(`contracts/run-sequence.md` § A failed call is not a round).

**Resume** — a crash restarts nothing: `O run-resume --run-dir D`
(`contracts/run-sequence.md` § Resume).

**Mode** — `auto` (default) is `fast` when scope's `fast_mode_default`
holds (≤ 400 added lines, ≤ 5 files), else `full`: three lenses, each
kept finding confirmed independently. `fast` findings are self-checked.

## Launch discipline

- **Any harness** (one shape): the `/spec-review` router command
  (`commands/spec-review.md`) routes review/fix/gate/plan asks into
  this skill; the session executes the stages as written, and the
  shared review oracle (`scripts/review_orchestrator.py`) resolves
  targets, runs the gate plan, parses findings and assembles the report
  (args: `base`, `target`, `pr`, `intent`, `fix_from`, `paths`, `mode`,
  `fix_rounds`). A repo's own project-scoped copy, tuned to its CI set,
  wins there.
- **Long foreground calls** (a fix loop may run them) may be
  auto-backgrounded by the harness; NEVER poll a backgrounded job — do
  other work or end your reply; you will be woken with its output.

## Reading the result

Findings carry `path:line`, evidence, severity, lens, and a
verified/unconfirmed status (or, after a fix round, a fix verdict:
`fixed`/`unfixed`/`worse`, a skip ruling `rejected-valid`/
`rejected-invalid`, or `out-of-scope`). Triage drops are
listed with reasons — "dropped at triage"
means judged out of scope, not missed. A `human` verdict — or a spent
fix loop with findings left — renders the stop ask in the markdown
under `## Recommendation` and as `stopAsk` in the report result: work
from its options, not from a re-run. `notCovered` distinguishes
"found nothing" from "looked nowhere": read it before trusting a
clean report. Field semantics: panel.md § Findings and § The report.

## Resource map

`contracts/panel.md` is the canonical contract (this file summarizes;
it arbitrates). `gates/recommendation.md` arbitrates stop conditions
and recommendation criteria. `references/quickstart.md` is navigation,
not a second contract. `evals/cases.md` + `examples/review-target/`
are the standing live-eval scenarios with a seeded-bug answer key;
`templates/fix-from-findings.json` is the continuation payload
template; `decisions/` holds the panel's ADRs, `diagrams/` the flow
graph, `observations/open-items.md` the living open-items list;
`scripts/skill-dir.sh` prints the active skill dir: the first installed
copy across the harness roots, project roots before home.
