---
name: spec-code-review
description: >-
  Portable three-stage code review for any git repository. Stage 1 runs the
  repo's own detected checks as the mechanical gate (scripts/gate.sh probes
  Makefile targets, npm scripts, cargo, go, pytest/unittest (resolving the repo's own
  pytest via PATH, repo venv, or uv run), and shell syntax
  on the diff). Stage 2 reviews the diff through separate lenses —
  correctness, security, quality & tests (one general reviewer on small
  diffs) — triaged by one editor with independent confirmation of every kept
  finding. Stage 3 synthesizes a report with risk class, test gaps and
  residual risks. An optional fix loop has an author agent fix the confirmed
  findings in the working tree, verify every fix independently, re-run the
  gate, and end with a merge / fix-first / human recommendation. Use when the
  user asks to review a change — "review the diff", "review the last commit",
  "review and fix" — in this or any repo.
metadata:
  owner: platform-core
  version: "0.3.2"
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
commit" — or to review AND fix: "review and fix the findings". The change
scope is a diff base: the working tree (default), `HEAD~1` for the last
commit, or any ref/branch.

## The three stages (and the optional fourth)

### Stage 1 — the mechanical gate, always first

Run `scripts/gate.sh` from this skill before any reviewer works:

```bash
bash <skill-dir>/scripts/gate.sh --base HEAD        # working-tree changes
bash <skill-dir>/scripts/gate.sh --base HEAD~1      # the last commit
bash <skill-dir>/scripts/gate.sh --plan             # what it would run
```

It detects and runs the repo's OWN checks (Makefile targets, npm
scripts, cargo/go, pytest or unittest discover (pytest resolved via PATH,
the repo's venv, or `uv run` when the repo is uv-locked), plus `bash -n` on every
changed `*.sh`) and prints a JSON array — one `{name, exit_code, tail}`
per check. Rules:

- A red gate ends the review: report the failing checks with their
  tails as the findings, and stop. Mechanical failures are fixed before
  reviewer attention is spent.
- An empty detection (no markers, no git) is NOT a green light to skip
  the floor: ask the repo for its documented check command (README, CI
  config) and run that instead; say so in the report if none exists.
- Never let a reviewer re-run the suites — the gate already decided
  them; reviewers spend their turn on what only a reader can see.

### Stage 2 — specialist review with triage and confirmation

Review the diff (`git diff <base>`) through separate lenses, in
parallel where you can:

- **correctness** — logic errors, edge cases, error handling,
  concurrency, caller/callee contracts;
- **security** — untrusted input paths, injection, secrets and tokens,
  permissions, destructive operations;
- **quality & tests** — complexity the next reader pays for,
  misleading names, doc drift, and tests: changed behavior with no
  covering test, tests that cannot fail.

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

1. Read the FULL diff; open the changed files for context; follow call
   sites when a defect depends on them.
2. Read the repo's rules first — `AGENTS.md` / `CLAUDE.md` at the root,
   if present — and cite any rule a finding violates.
3. The flagging bar — a finding must be ALL of: discrete and
   actionable; introduced by this change; demonstrable from the code
   (quote the deciding lines); something the author would reasonably
   fix.
4. Exclusions: speculative might-fail concerns, pre-existing problems
   the change does not worsen, style/formatting (the gate owns those),
   intentional behavior changes.
5. Severity: `high` = data loss, crash, wrong result, security
   compromise; `medium` = a real defect the author should fix; `low` =
   minor. Cite every finding as `path:line` on the new side.
6. Zero findings is the expected answer for a clean diff. Never invent
   one to seem busy.

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
not.

### Stage 4 (optional) — the fix loop

When the user asked to fix as well, run bounded rounds (default 2):

1. An **author/fixer** fixes the confirmed findings in the working
   tree: minimal, repo style, NEVER commits, never weakens a test to
   make a finding go away (pin corrected behavior instead). Dispatch
   `agents/code-review-fixer.md` where the harness supports subagents.
2. Every attempted fix is verified by an independent reader: `fixed` /
   `unfixed` / `worse`.
3. The gate re-runs; failures become findings the fixer must clear.
4. A fresh-eyes reviewer scans the diff of exactly the paths the fixer
   touched, for NEW defects the fixes introduce.
5. Loop until everything is fixed or rounds run out.

End with a **recommendation**: `merge` (everything fixed, gate green,
nothing new), `fix-first` (ordinary findings remain), or `human`
(judgment calls or unconfirmed residue). Fixes stay uncommitted — the
commit decision and message are the user's.

## Launch discipline

- **zcode harness**: run the installed workflow by name —
  `spec-code-review` (args: `base`, `mode` fast/full/auto,
  `fix_rounds`, optional `skill_dir` override). A repo may keep its own
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

## Reading the result

Findings carry `path:line`, evidence, severity, lens, and a
verified/unconfirmed status (or fixed/unfixed/worse after a fix round).
Triage drops are listed with reasons — "dropped at triage" means judged
out of scope, not missed. `notCovered` distinguishes "found nothing"
from "looked nowhere": read it before trusting a clean report.
