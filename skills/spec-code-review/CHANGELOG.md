# Changelog — spec-code-review

Release history. The skill began life 2026-09-23 as the validated
`spec-code-review` dynamic workflow in the SpecDevKit repo (three-stage
review: mechanical gate → specialist panel with triage and independent
confirmation → synthesis), then became a portable sibling skill.


## 0.7.0 — 2026-09-26

Fix continuation and impact. (1) A `fix_from` arg turns the workflow
into a fix-only second run: it takes the findings JSON of a previous
review — inline, or a file path read with cat / a probe agent; a bare
array or an object with a findings array — skips the review stages,
and runs the fix loop directly on the carried findings (items already
marked fixed are dropped, severities are re-sorted, the gate runs once
pre-fix and again after every round). This makes the decision gate a
real step: run a review, present the findings with severity and
impact, let the user decide, then fix from the report without paying
for a second review. `fix_rounds` defaults to 2 in fix_from mode; a
new "Load the findings from the previous review" phase opens the run,
and the report/verified/notCovered fields state that coverage
inherits the previous report. (2) Findings gain an optional `impact`
field — one sentence on what the defect breaks and when it bites
(callee/caller exposure, data at risk) — requested in every reviewer
ask (diff and project), carried through triage, the fixer brief and
both report renderings. Parity tests pin the new phase, the
fix_from/impact anchors, the fix_rounds default, the probe label and
the schema shapes.

Migration: none required — both changes are additive; existing
invocations behave exactly as before, and re-run tools/sync.sh to pick
up the regenerated dialects.

## 0.6.0 — 2026-09-26

Stated intent, split advice, design fit — closing the gaps against
classic human-review principles. (1) An `intent` arg (change modes)
carries what the change is supposed to do, in the author's words, into
the reviewer, triage, final-assessment and fixer asks; in pr mode the
PR description (whitespace-collapsed, capped at 1200 chars) is used
when no intent arg is passed. Intent is the author's rebuttal channel
for unattended runs — a deliberate choice the intent states up front is
an intentional behavior change, not a finding, but stated intent never
waives a demonstrable defect; confirmation stays intent-blind on
purpose so the confirmer verifies from the code alone. (2) Changes over
SUGGEST_SPLIT_LINES (1000 added lines) or SUGGEST_SPLIT_FILES (20 files)
earn a one-line split recommendation in the report — reviewers read
whole targets, and coverage thins as size grows. (3) The quality lens
gains design fit: whether the change follows the patterns the
surrounding code already establishes instead of inventing a parallel
way — focus string updated in both workflow dialects and the quality
brief (pinned together). Parity tests pin the intent wiring (exactly
four intentBlock call sites per dialect, confirm asks excluded), the
split tunables and anchors, and the new focus string.

Migration: none required — the arg is optional and every existing
invocation behaves exactly as before; re-run tools/sync.sh to pick up
the regenerated workflow dialects, briefs and the root agents/ copies.

## 0.5.0 — 2026-09-26

Pull-request and branch targets: the panel can now review a GitHub pull
request or a branch's recent changes, completing the target set —
diff (default), branch, pr, project. Both new targets resolve to a
merge-base diff before any panel machinery runs, so the ask family, the
gate, the confirmation step and the fix loop are unchanged underneath.
Branch mode diffs the current branch against an explicit `base` or the
remote's default branch (origin/HEAD, then main/master), uncommitted
work included and noted. Pr mode resolves the PR with the gh CLI
(`pr` arg: number, URL or owner/repo#N); because the panel and the fix
loop read the working tree, the PR head must be checked out — on a clean
tree the workflow checks it out itself (announced, previous HEAD in the
log), on a dirty tree it refuses rather than hide uncommitted work. The
PR diff is the merge-base against the PR's base commit — GitHub's own
PR-diff semantics — and the report names the PR (number, title, author,
base, URL), with "merge" reading as the PR is ready; branch mode's
"merge" reads as the branch is ready to merge. Unknown target values now
fail with the valid set instead of silently reviewing as diff mode. The
zcode master resolves pr/branch through world.run git/gh calls; the
Claude dialect routes the same resolution through five new probe agents
(pr-meta, pr-head, pr-checkout, merge-base, base-ref). Parity tests pin
the new target modes, the resolution anchors (merge-base, origin/HEAD
detection, the dirty-tree refusal, the checkout announcement) and the
probe labels in both dialects.

Adopted from a phased AI-code-review rollout proposal: the pr target's
report header carries the pull-request summary (title, author, base) and
stays advisory-only; test-gap and security feedback were already first
class. Deliberately NOT adopted: a hard cap on findings (conflicts with
"never suppress a real defect" — findings stay severity-ordered instead)
and an AI-owned hard gate (the only blocking gate remains the repo's own
mechanical checks).

Migration: none required — `target` still defaults to `diff` and every
existing invocation behaves exactly as before; pass `target: "branch"`
(optionally with `base`) or `target: "pr"` with a `pr` arg for the new
targets, and re-run `tools/sync.sh` to pick up the regenerated workflow
dialects.

## 0.4.0 — 2026-09-25

Whole-project review: the panel can now review the codebase as it
stands, not only a change. A `target` arg picks the mode (`diff` is the
default and unchanged; `project` reviews the repository's tracked
source files), and a `paths` arg narrows a project review to named
paths/directories. Project targeting: tracked files, extension-filtered
with lockfiles, generated code (`.d.ts`, protobuf outputs, minified
bundles) and vendored/build directories excluded, largest first, capped
at `PROJECT_MAX_FILES` (30) — anything the cap leaves out is named
under `notCovered`. gate.sh gains `--tree`: the bash -n family scans
every tracked `*.sh` instead of the diff (its suites were always
project-wide). The ask family branches per mode: no diff to read, the
flagging bar's "introduced by this change" becomes "present in the code
as it stands", confirmation drops the introduced-by clause, and the
`merge` recommendation reads as ready-as-is. The fix loop is unchanged —
fixes are still an uncommitted diff, so verification and fresh-eyes fix
review work in both modes. The panel briefs (protocol + three lens
briefs) are reworded target-agnostic so agents installed as real
subagent types serve both modes. Parity tests pin the project ask
anchors, the new tunable, and the `--tree` wiring in both dialects;
gate tests cover `--tree` green and red.

Migration: none required — `target` defaults to `diff` and every
existing invocation behaves exactly as before; pass `target: "project"`
(optionally with `paths`) for a whole-project review, and re-run
`tools/sync.sh` to pick up the regenerated workflow dialects, gate.sh
`--tree`, and the reworded panel briefs.

## 0.3.2 — 2026-09-24

The zcode facade now carries the full panel. With no user-installable
agent types, the zcode workflow reads the panel briefs from the skill
dir at run time (cat through the same world.run seam gate.sh uses) and
injects them into the reviewer, triage and fixer personas: each lens
reviewer carries its lens brief, the triage editor and fixer carry
`_panel-protocol.md` and the fixer brief, and the general reviewer
carries all three lens briefs. A missing brief degrades to the inline
rubric, never an error. SKILL.md's launch discipline documents the
injection; ZcodeDialectTests pins every brief as wired.

Migration: none required — the injection is additive and degrades to
the inline rubric when a brief is absent; re-run `tools/sync.sh` to
pick up the regenerated workflow dialect.

## 0.3.1 — 2026-09-24

The Python family resolves the repo's own pytest before falling back to
unittest discover: PATH pytest, then `.venv/bin/pytest` /
`venv/bin/pytest`, then `uv run pytest` when the repo carries a
`uv.lock` (so no environment is invented), then `python3 -m pytest`
when importable. unittest discover remains the last resort — a red tail
beats a skipped family. A repo whose tests import pytest but whose
pytest lives in a venv no longer gates red on 263 collection errors.

## 0.3.0 — 2026-09-24

The panel's agents, materialized. Each side of the review rubric now
ships as an installable agent brief under `agents/`:
`code-review-correctness`, `code-review-security`, `code-review-quality`
(each carrying the full checklist for its side of the rubric) and
`code-review-fixer` (the fix loop's author role), over the shared
`_panel-protocol.md` (the flagging bar, severity ladder, citation
format, zero-findings rule — the contract every panel member shares).
Harnesses with subagent dispatch (Claude Code, omp, opencode, Factory
Droid, Antigravity) get them as real subagent types from
`tools/sync.sh`, so the inline path dispatches genuine specialists
instead of one agent simulating every lens; SKILL.md's Stage 2 and fix
loop now say exactly that. The three lens briefs are pinned to the
workflow masters by their focus strings — a third representation of
the panel that cannot drift silently (tests/test_workflow_copies.py).

Migration: none required — rerun `tools/sync.sh` to install the new
agent defs alongside the existing skills and workflows.


## 0.2.0 — 2026-09-24

Second dialect, plus the drift guard. `workflows/spec-code-review.js`
ports the full protocol to the Claude Code dynamic-workflow runtime, so
`tools/install-workflow.sh claude` (and `tools/sync.sh`) deliver the
review to Claude Code exactly as the zcode dialect reaches zcode. The
one-shot agent model forced three documented divergences (header of the
file): system prompts ride at the head of each ask; cross-lens dedup
runs as one explicit merge pass instead of a shared triage
conversation; every fixer round embeds the full finding detail instead
of relying on conversation context. Shell work (gate.sh, git) reaches
the runtime only through probe agents returning stdout verbatim, and
the report returns as the run result's `markdown` field.

`tests/test_workflow_copies.py` pins the two masters together — shared
phases, tunables, panel definition, ask anchors, report contract, and
each runtime's structural invariants — the guard the hand-maintained
two-dialect layout demands.

Fix-loop correctness fix, applied to both dialects and to the repo's
own project-scoped copy: the post-fix verification wave no longer
spawns reader verifiers for gate-lens findings — a reader cannot
verify a check name, and the fresh authoritative gate re-run owns
those.

Migration: none required. The zcode dialect's behavior is unchanged;
rerun `tools/install-workflow.sh` (or sync) to pick up the fix and the
new claude dialect.


## 0.1.0 — 2026-09-23

First release. The review protocol of the validated workflow, packaged
for any repo and any coding agent: `scripts/gate.sh` detects and runs
the target repo's own checks (Makefile targets, npm scripts, cargo, go,
pytest/unittest, `bash -n` on the changed shell scripts) and reports a
JSON array callers can branch on; SKILL.md carries the full protocol —
defect-first flagging bar, severity ladder, exclusions, triage,
independent confirmation, the bounded fix loop, and the
merge/fix-first/human recommendation. The zcode workflow
(`workflows/spec-code-review.dwf.ts`) automates the stages on harnesses
that run dynamic workflows; agents without workflow support execute the
stages inline. Validated end-to-end twice in SpecDevKit: the review
pass confirmed 7 findings on a 20-file commit (risk medium), and the
fix loop resolved 7 of 8 tracked findings across 2 rounds with the gate
green and every fix independently verified.

Migration: none required — first release. `tools/sync.sh` installs the
skill tree and the workflow (as the saved zcode workflow
`spec-code-review`); repos that want a gate tuned to their exact CI set
keep a project-scoped workflow copy, which takes precedence there.
