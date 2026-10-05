---
name: spec-code-review
description: >-
  Portable three-stage code review for any git repository — a change, a
  pull request, a branch, or the whole project. Stage 1
  runs the repo's own checks as the mechanical gate (Makefile,
  npm scripts, cargo, go, pytest/unittest, shell syntax, secret shapes).
  A preflight scout then maps the codebase and modules (roles,
  conventions, risks) so every reviewer starts from the same
  ground. Stage 2 reviews the target through separate lenses —
  correctness, security, quality & tests (one general reviewer when
  small) — one editor triages, every kept finding independently
  confirmed. Stage 3 synthesizes risk, test gaps and residual
  risks. An optional fix loop has an author agent fix the confirmed
  findings in the working tree, verify each fix, re-run the gate, and
  recommend merge / fix-first / human. Use when the user asks to review
  a change — "review the diff", "review and fix" — a pull request
  ("review PR 12"), a branch's recent changes ("review what's on this
  branch") — or the codebase as a whole ("review the project").
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
recent changes on this branch" — or to review AND fix any of these:
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
   verified finding is worth five unverified ones — the industry's
   2026 lesson: precision, not recall, is what makes an AI reviewer
   trustworthy.
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

One `target` picks what the panel reviews. The first three all resolve
to a diff, so the panel machinery, the gate and the fix loop run
identically underneath — only the resolution differs:

- **diff** (default) — the change against a base ref: the working tree
  (`base: HEAD`), the last commit (`HEAD~1`), or any ref/branch.
- **branch** — the current branch's recent changes: the merge-base diff
  against a base branch (explicit `base`, else the remote's default —
  `origin/HEAD`, then main/master). Uncommitted work on the branch is
  included and noted in the report.
- **pr** — a GitHub pull request (`pr`: number, URL or owner/repo#N,
  resolved with the gh CLI). The panel reads the working tree, so the PR
  head must be checked out: on a clean tree the review checks it out
  itself (announced, with the previous HEAD in the log); on a dirty tree
  it refuses rather than hide uncommitted work. The diff is the
  merge-base against the PR's base commit — the same PR-diff semantics
  GitHub uses — and the report names the PR (number, title, author,
  base, URL).
- **project** — the codebase as it stands (see below). In a multi-repo
  workspace whose root is not itself a git repository, pass `repo`:
  the sub-repo directory (absolute, or relative to the working
  directory), resolved to its absolute toplevel before anything runs —
  every git call, the gate's `--repo`, and the absolute file paths the
  reviewers read root there. The runtime's cwd is not guaranteed to be
  the workspace root, so nothing may rely on a relative repo path.
  `repo` is supported for `project` only; change/branch/pr targets
  refuse it — run those from inside the repository.

Stage 1 always runs first with the resolved base: `--base <merge-base>`
in diff/branch/pr mode, `--tree` in project mode.

## The three stages (and the optional fourth)

### Stage 1 — the mechanical gate, always first

Run `scripts/gate.sh` from this skill before any reviewer works:

```bash
bash <skill-dir>/scripts/gate.sh --base HEAD        # working-tree changes
bash <skill-dir>/scripts/gate.sh --base HEAD~1      # the last commit
bash <skill-dir>/scripts/gate.sh --base <merge-base>  # branch / PR mode (resolved first)
bash <skill-dir>/scripts/gate.sh --tree             # every tracked *.sh (project mode)
bash <skill-dir>/scripts/gate.sh --plan             # what it would run
```

It detects and runs the repo's OWN checks (Makefile targets, npm
scripts, cargo/go, pytest or unittest discover (pytest resolved via PATH,
the repo's venv, or `uv run` when the repo is uv-locked), plus two
always-on families when git is available: `bash -n` on every changed
`*.sh` — every tracked `*.sh` in project mode — and a high-precision
secret-shape scan (AWS/GitHub/GitLab/Stripe/Slack/Google/npm/Anthropic
key shapes, private-key headers) over the change's added lines and
untracked files; project mode skips the secret family to avoid
false-positive fixtures; a line carrying the inline marker
`spec-review:allow` is skipped — the gitleaks-style escape hatch that
lets tests for this family hold fixture tokens) and prints a JSON array — one
`{name, exit_code, tail}` per check. Rules:

- A red gate ends the review: report the failing checks with their
  tails as the findings, and stop. Mechanical failures are fixed before
  reviewer attention is spent.
- An empty detection (no markers, no git) is NOT a green light to skip
  the floor: ask the repo for its documented check command (README, CI
  config) and run that instead; say so in the report if none exists.
- Never let a reviewer re-run the suites — the gate already decided
  them; reviewers spend their turn on what only a reader can see.

### Whole-project mode (target: project)

When the ask is the codebase as a whole — "review the project",
"review the whole codebase" — the review target becomes the project
instead of a diff:

- The gate runs with `--tree` (shell syntax over every tracked
  script); everything else about the gate is unchanged — its suites
  were always project-wide. One exception to the gate-first rule: a
  project audit does not stop at a red gate — each failing check
  becomes a high-severity gate finding and the panel still reads the
  code, because for an audit the failures are themselves findings.
- The review target is every tracked source file: extension-filtered,
  with lockfiles, generated code and vendored/build directories
  excluded. A target too large for one reviewer's turn is sharded:
  contiguous runs of the path-sorted list (directories stay together),
  closed at ~240 KB or 32 files per part, byte-balanced — and every
  lens reads every part, so coverage is complete. Narrow the target
  further with explicit `paths`.
- There is no diff: reviewers read the listed files, the flagging
  bar's "introduced by this change" becomes "present in the code as it
  stands", and confirmation drops the introduced-by-the-change clause.
- The fix loop is unchanged — the fixer's edits are still an
  uncommitted diff, so fix verification and the fresh-eyes fix review
  work identically.
- In project mode the `merge` recommendation reads as "the code is
  ready as it stands".

### Preflight (stage 1.5) — the scout maps the ground

Between a green gate and the first reviewer, one read-only scout
explores the codebase and the modules the target touches and returns
the map the panel starts from:

- `modules` — the target's modules plus their close neighbors
  (name, path, one-line role; within two hops);
- `conventions` — the patterns the surrounding code establishes, the
  ones design fit is judged against (error-handling idiom, test
  layout, naming, module boundaries — AGENTS.md/CLAUDE.md folded in);
- `riskAreas` — paths in or near the target that deserve extra
  reviewer attention, one line each.

The map rides the reviewer asks and the final assessment as context —
verify against the code, never cite it as evidence. Confirmers never
see it: independent confirmation verifies from the code alone, and a
scout error must not rubber-stamp a finding. The scout reports a map,
never findings — a defect it noticed travels only as a `riskAreas`
line with a path, and the reviewers still must find it. A scout that
fails degrades to the raw target (named under `notCovered`), and
`fix_from` runs skip the step entirely (their review stages are
skipped). The step runs in fast mode too — one bounded turn (≤8
modules, ≤6 conventions, ≤6 risk areas) buys every reviewer the same
starting ground.

### Stage 2 — specialist review with triage and confirmation

Review the diff (`git diff <base>`) through separate lenses, in
parallel where you can:

- **correctness** — logic errors, edge cases, error handling,
  concurrency, caller/callee contracts;
- **security** — untrusted input paths, injection, secrets and tokens,
  permissions, destructive operations;
- **quality & tests** — complexity the next reader pays for,
  misleading names, doc drift, design fit (whether the change follows
  the patterns the surrounding code establishes instead of inventing a
  parallel way), and tests: changed behavior with no covering test,
  tests that cannot fail.

Each side of this rubric is materialized as an agent brief inside the
skill — `agents/code-review-correctness.md`, `-security.md`,
`-quality.md` (each carrying the full checklist for its side) over the
shared `agents/_panel-protocol.md`; the fix loop's author role is
`agents/code-review-fixer.md`. Where the harness supports subagent
dispatch (Claude Code, omp, opencode, Factory Droid — sync installs
the briefs as real subagent types), spawn one brief per lens instead
of simulating a lens yourself: same rubric, same bar, real
independence. Where it does not, cover the lenses inline — the briefs'
rubric sections are the checklist, so a lens is never covered from
memory alone.

Small diffs (roughly ≤400 added lines and ≤5 files) may collapse to one
general reviewer covering all three lenses.

Every reviewer follows the same contract:

1. Read the FULL target — the diff in change review, the listed files
   in project mode; open the surrounding files for context; follow call
   sites when a defect depends on them.
2. Read the repo's rules first — `AGENTS.md` / `CLAUDE.md` at the root,
   if present — and cite any rule a finding violates.
3. The flagging bar — a finding must be ALL of: discrete and
   actionable; part of the target under review (in change review:
   introduced by this change); demonstrable from the code (quote the
   deciding lines); something the author would reasonably fix.
4. Impact — one sentence on what the defect breaks and when it bites
   (which callers, what data is at risk), on every finding above the
   minor level.
5. Exclusions: speculative might-fail concerns, style/formatting (the
   gate owns those), intentional behavior changes — and, in change
   review, pre-existing problems the change does not worsen.
6. Severity: `high` = data loss, crash, wrong result, security
   compromise; `medium` = a real defect the author should fix; `low` =
   minor. Cite every finding as `path:line` in the code (on the new
   side in change review).
7. Zero findings is the expected answer for a clean target. Never
   invent one to seem busy.

**Stated intent.** When the author's intent is available — the
`intent` arg, or the PR description in pr mode — reviewers, triage and
the final assessment receive it verbatim and judge against it: a
deliberate choice the intent states up front is an intentional
behavior change, not a finding. This is the author's rebuttal channel
for unattended runs, and it never waives a demonstrable defect.
Confirmation stays intent-blind on purpose: the confirmer verifies
from the code alone.

One **triage editor** dedupes across lenses and drops style nits,
speculation and pre-existing issues (with a one-line reason each) —
stingy, but never suppressing a real defect. Then every KEPT finding is
**independently confirmed** by someone who did not write it: re-read
the location, check the change introduced it, answer verified or
unconfirmed. Findings that fail confirmation are kept and labelled
`unconfirmed`, never silently dropped.

### Stage 3 — synthesis

One assessment (the triage editor, for a consistent scale) produces:
overall **risk** (low/medium/high), **test gaps** (changed behavior no
test covers), **residual risks** (what remains unverified), and a
verdict. Report what was checked (the gate's commands) and what was
not. A change over the split bounds (`SUGGEST_SPLIT_LINES` 1000 added
lines / `SUGGEST_SPLIT_FILES` 20 files) also earns a one-line
recommendation to split it into smaller, independently reviewable
chunks — reviewers read whole targets, and coverage thins as size
grows.

### Stage 4 (optional) — the fix loop

When the user asked to fix as well, run bounded rounds (default 2):

1. An **author/fixer** fixes the confirmed findings in the working
   tree: reads the repo's AGENTS.md/CLAUDE.md first, minimal, repo
   style, NEVER commits, never weakens a test to
   make a finding go away (pin corrected behavior instead). Dispatch
   `agents/code-review-fixer.md` where the harness supports subagents.
   That brief carries the kit-wide engineering rules (§ Engineering
   rules: test discipline, backgrounded-job discipline, code
   commenting) — they bind the fix loop's every edit.
2. Every attempted fix is verified by an independent reader: `fixed` /
   `unfixed` / `worse`.
3. The gate re-runs; failures become findings the fixer must clear.
4. A fresh-eyes reviewer scans the diff of exactly the paths the fixer
   touched, for NEW defects the fixes introduce.
5. Loop until everything is fixed or rounds run out.

**The review-then-ask flow.** A dynamic workflow cannot pause mid-run
to ask the user, so the decision gate is a second run, and `fix_from`
makes it cheap: run a review first (`fix_rounds: 0`), present the
findings with their severity and impact, and let the user decide. If
they fix, run the workflow again with `fix_from` — the previous
report's markdown (the saved report file; its findings section parses
back, ids included), or its findings JSON inline or as a file path
(each item `{id, where, what, evidence, severity, lens, status,
impact, fixStatus}`; ids are optional — an id-less item gets
`carried-N`; items already marked fixed are dropped) — plus
`fix_rounds`. That run skips the review stages entirely: it loads the
carried findings, runs the fix loop on them, and ends with the
recommendation. `fix_rounds` defaults to 2 in this mode.

End with a **recommendation**: `merge` (everything fixed, gate green,
nothing new), `fix-first` (ordinary findings remain), or `human`
(judgment calls or unconfirmed residue). Fixes stay uncommitted — the
commit decision and message are the user's.

## Launch discipline

- **Any harness**: the `/spec-code-review` router command
  (`commands/spec-code-review.md`, installed by tools/sync.sh) routes
  review/fix/gate/plan asks into this skill; `scripts/skill-dir.sh`
  prints the active skill dir per this priority order.
- **zcode harness**: run the installed workflow by name —
  `spec-code-review` (args: `base`, `target` `diff`/`branch`/`pr`/
  `project`, `pr` (the pull request, pr mode), `intent` (what the
  change is supposed to do — the author's stated intent), `fix_from`
  (the previous report's markdown or its findings JSON — fix-only
  continuation),
  `paths` (project mode), `mode` fast/full/auto, `fix_rounds`, optional
  `skill_dir` override).
  A repo may keep its own
  project-scoped copy tuned to its exact CI set; the project copy wins
  there. The zcode facade has no user-installable agent types, so the
  workflow reads the panel briefs from the skill dir at run time and
  injects them into the reviewer, triage and fixer personas. Without
  the workflow, execute the stages inline as above.
- **Claude Code**: run the installed dynamic workflow `spec-code-review`
  (same args) — `tools/install-workflow.sh claude` bakes
  `workflows/spec-code-review.js` into `~/.claude/workflows/` (a
  project-scoped `.claude/workflows/` copy wins locally, same rule).
  Its agents are one-shot: cross-lens dedup runs as one explicit merge
  pass instead of a shared triage conversation, and the report returns
  as the run result's `markdown` field.
- **Other agents**: follow the stages inline; `scripts/gate.sh` is
  plain bash + python3 and is the only script you need.
- **Long foreground calls** (this skill runs none itself, but a fix
  loop may) may be auto-backgrounded by the harness; the result
  arrives as a follow-up when the job finishes. NEVER poll a
  backgrounded job (`sleep`, `ps`, `pgrep`, `top`) — do other work or
  end your reply; you will be woken with its output.

## Reading the result

Findings carry `path:line`, evidence, severity, lens, and a
verified/unconfirmed status (or fixed/unfixed/worse after a fix round).
Triage drops are listed with reasons — "dropped at triage" means judged
out of scope, not missed. `notCovered` distinguishes "found nothing"
from "looked nowhere": read it before trusting a clean report. In pr
mode the `merge` recommendation reads as the PR is ready; in branch
mode, as the branch is ready to merge.

## Resource map

`contracts/panel.md` is the canonical contract (this file summarizes;
it arbitrates). `gates/recommendation.md` arbitrates stop conditions
and recommendation criteria. `decisions/` holds the panel's ADRs
(D-001…D-011 — gate-first, independent confirmation, advisory-only,
targets-collapse-to-diffs, the fix loop, dialect parity,
precision-over-recall, the preflight scout, sub-repo targets, sharded
project coverage, audits continuing past red gates).
`references/quickstart.md` is navigation, not
a second contract. `evals/cases.md` + `examples/review-target/` are
the standing live-eval scenarios with a seeded-bug answer key;
`templates/fix-from-findings.json` is the continuation payload
template; `diagrams/` holds the flow graph (.mmd canonical + an HTML
render); `observations/open-items.md` is the living open-items list;
`scripts/skill-dir.sh` prints the active skill dir per the launch
priority order.
