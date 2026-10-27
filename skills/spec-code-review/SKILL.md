---
name: spec-code-review
description: >-
  Portable three-stage code review for any git repository — a change, a
  pull request, a branch, or the whole project: the repo's own checks as
  the mechanical gate, a preflight scout, specialist lenses (correctness,
  security, quality & tests) with independent confirmation of every kept
  finding, and an optional verified fix loop. Use when the user asks to
  review a change — "review the diff", "review and fix" — a pull request
  ("review PR 12"), a branch's recent changes ("review what's on this
  branch"), or the codebase as a whole ("review the project"). Not a
  spec's delivery review (spec-execute).
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-code-review — gated, confirmed code review (with optional fix loop)

Review a git change the way a strict panel would: the repo's own checks
decide everything mechanical first, specialist reviewers own what only a
reader can see, no finding reaches the user without independent
confirmation, and — when asked — an author agent fixes what the panel
confirmed, with every fix re-verified.

## When to use

The user asks to review a change: "review the diff", "review this
change", "review the last commit", "look over my working tree before I
commit" — a pull request: "review PR 12", "review this pull request" —
a branch's recent changes: "review what's on this branch", "review the
recent changes on this branch" — the whole codebase: "review the
project" — or to review AND fix any of these:
"review and fix the findings". The default change scope is a diff base:
the working tree (default), `HEAD~1` for the last commit, or any
ref/branch.

## Principles

The panel's contract, in priority order. When two rules collide, the
higher number wins; when a change would violate any of them, the
change is wrong — not the rule.

1. **Machine-decidable before human attention.** Everything a
   deterministic check can decide (tests, syntax, secret shapes) is
   decided by the gate before a reviewer spends a turn; reviewers own
   only what requires reading.
2. **Evidence or it does not exist.** Every finding carries `path:line`
   and the quoted lines that demonstrate it. A finding a reader cannot
   re-derive from its evidence is not a finding.
3. **Independence beats volume.** The reviewer, the confirmer, the
   fixer and the fresh-eyes fix reviewer are different agents. One
   verified finding is worth five unverified ones: precision, not
   recall, is what makes an AI reviewer trustworthy.
4. **Zero findings is success.** Clean targets get empty lists; noise
   is never manufactured to seem busy, and style/formatting is never a
   finding (the repo's checks own it).
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
   repo's style. The panel imposes nothing of its own beyond this
   contract.

## Review targets

One `target` picks what the panel reviews; `contracts/panel.md`
§ Targets is the canonical resolution table:

- **diff** (default) — the change against a base ref: the working
  tree (`base: HEAD`), the last commit (`HEAD~1`), or any ref/branch.
- **branch** — the merge-base diff against a base branch (explicit
  `base`, else the remote's default); uncommitted work is included
  and noted in the report.
- **pr** — a GitHub pull request (`pr`: number, URL, or
  `owner/repo#N`, resolved with the gh CLI). The panel reads the
  working tree: on a clean tree the review checks the head out itself
  (announced); on a dirty tree it refuses rather than hide
  uncommitted work.
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
scripts, cargo/go, pytest or unittest discover), plus `bash -n` on
changed `*.sh` and a secret-shape scan of the change's added lines,
and prints a JSON array — one `{name, exit_code, tail}` per check.
Rules: a red gate ends a fresh review — report the failing checks
with their tails as the findings, and stop; an empty detection is NOT
a green light (ask the repo for its documented check command and run
that instead; say so if none exists); reviewers never re-run the
suites. The one exception — a project audit continues past a red gate,
each failing check becoming a high-severity gate finding (panel.md
§ The mechanical gate).

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
§ Preflight; the brief is `agents/code-review-scout.md`.

### Stage 2 — specialist review with triage and confirmation

Review the diff (`git diff <base>`) through separate lenses, in
parallel where you can:

- **correctness** — logic errors, edge cases, error handling,
  concurrency, caller/callee contracts;
- **security** — untrusted input paths, injection, secrets and tokens,
  permissions, destructive operations;
- **quality & tests** — complexity the next reader pays for,
  misleading names, doc drift, design fit (against a labelled
  design-smell baseline — always judgement calls, the repo
  overriding), and tests: changed behavior with no covering test,
  tests that cannot fail.

Each side of this rubric is materialized as an agent brief inside the
skill — `agents/code-review-correctness.md`, `-security.md`,
`-quality.md` (each carrying the full checklist for its side) over the
shared `agents/_panel-protocol.md`; the fix loop's author role is
`agents/code-review-fixer.md`. Where the harness supports subagent
dispatch, spawn one brief per lens instead of simulating a lens
yourself: same rubric, same bar, real independence. Where it does not,
cover the lenses inline — the briefs' rubric sections are the
checklist, so a lens is never covered from memory alone. Small diffs
(roughly ≤400 added lines and ≤5 files) may collapse to one general
reviewer covering all three lenses.

Every reviewer follows the panel contract (`_panel-protocol.md` is
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
never silently dropped.

### Stage 3 — synthesis

One assessment (the triage editor, for a consistent scale) produces:
overall **risk** (low/medium/high), **test gaps**, **residual
risks**, and a verdict — reporting what was checked (the gate's
commands) and what was not. A change over the split bounds (panel.md
§ The report) also earns a one-line recommendation to split it.

### Stage 4 (optional) — the fix loop

When the user asked to fix as well, run bounded rounds (default 2):

1. An **author/fixer** (`agents/code-review-fixer.md`) fixes the
   confirmed findings in the working tree: repo rules first, minimal,
   repo style, NEVER commits, never weakens a test to make a finding
   go away (pin corrected behavior instead). That brief carries the
   kit-wide engineering rules (§ Engineering rules: test discipline,
   backgrounded-job discipline, code commenting) — they bind the fix
   loop's every edit.
2. Every attempted fix is verified by an independent reader: `fixed` /
   `unfixed` / `worse`.
3. The gate re-runs; failures become findings the fixer must clear.
4. A fresh-eyes reviewer scans the diff of exactly the paths the fixer
   touched, for NEW defects the fixes introduce.
5. Loop until everything is fixed or rounds run out.

**The review-then-ask flow.** An unattended run cannot pause mid-run
to ask, so the decision gate is a second run: run a review first
(`fix_rounds: 0`), present the findings, and if the user fixes, run
again with `fix_from` — the previous report's markdown, or its
findings JSON (schema: `templates/fix-from-findings.json`) — plus
`fix_rounds`. That run skips the review stages entirely and ends with
the recommendation.

End with a **recommendation**: `merge` (everything fixed, gate green,
nothing new), `fix-first` (ordinary findings remain), or `human`
(judgment calls or unconfirmed residue). Fixes stay uncommitted — the
commit decision and message are the user's.

## Launch discipline

- **Any harness** (one shape): the `/spec-code-review` router command
  (`commands/spec-code-review.md`) routes review/fix/gate/plan asks
  into this skill, and the session executes the stages inline as
  written — the shared review oracle
  (`scripts/review_orchestrator.py`) resolves targets, runs the gate
  plan, parses findings and assembles the report for any caller
  (args: `base`, `target`, `pr`, `intent`, `fix_from`, `paths`,
  `mode`, `fix_rounds`). A repo may keep its own project-scoped copy
  tuned to its exact CI set; the project copy wins there. Harnesses
  with subagent dispatch spawn the panel briefs; harnesses without
  run the lenses inline from the same briefs' rubric sections.
- **Long foreground calls** (this skill runs none itself, but a fix
  loop may) may be auto-backgrounded by the harness; NEVER poll a
  backgrounded job — do other work or end your reply; you will be
  woken with its output.

## Reading the result

Findings carry `path:line`, evidence, severity, lens, and a
verified/unconfirmed status (or fixed/unfixed/worse after a fix
round). Triage drops are listed with reasons — "dropped at triage"
means judged out of scope, not missed. `notCovered` distinguishes
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
`scripts/skill-dir.sh` prints the active skill dir per the launch
priority order.
