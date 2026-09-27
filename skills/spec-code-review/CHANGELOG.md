# Changelog — spec-code-review

Release history. The skill began life 2026-09-23 as the validated
`spec-code-review` dynamic workflow in the SpecDevKit repo (three-stage
review: mechanical gate → specialist panel with triage and independent
confirmation → synthesis), then became a portable sibling skill.


## 0.9.0 — 2026-09-27

Directory structure aligned with spec-to-prod's resource distribution:
every directory now has a canonical job. contracts/panel.md is the
canonical panel contract (targets, gate rows, finding/report schemas,
role-independence matrix) — SKILL.md summarizes, it arbitrates.
decisions/ carries the skill's first seven ADRs (D-001 gate-first,
D-002 independent confirmation, D-003 advisory-only, D-004
targets-collapse-to-diffs, D-005 fix loop and fix_from continuation,
D-006 dialect parity, D-007 precision-over-recall) in the repo's
Why/Cost-if-wrong shape, converting living CHANGELOG folklore into
addressable records. commands/spec-code-review.md is the router
(/spec-code-review review|fix|gate|plan) installed by sync to every
commands root; scripts/skill-dir.sh prints the active skill dir per
the launch priority order (spec-to-prod's pattern).
gates/recommendation.md arbitrates stop conditions and the
merge/fix-first/human criteria. references/quickstart.md is
navigation, not a second contract. evals/cases.md defines four
standing live-eval scenarios (clean-diff precision, seeded-bug recall,
PR flow, fix_from continuation) backed by examples/review-target/ — a
fixture base plus a git-generated change.diff with four seeded defects
and three must-not-flag traps, answered by EXPECTED.md.
templates/fix-from-findings.json is the continuation payload template.
diagrams/ adds the flow graph (.mmd canonical + hand-crafted HTML
render in the spec-to-prod style). observations/open-items.md is the
living open-items list (suggestion sketches, config file, incremental
re-review, PR posting, never-run evals, accepted limitations). SKILL.md
gains a Resource map section pointing at all of it; behavior,
workflows, and tests are unchanged.

The same release aligns the zcode master with the dynamic-workflow
authoring contract, verified by compiling it against the compiler's
actual facade (strict, no-DOM) instead of a type-stripping esbuild
pass. That check caught and fixed two real compile errors esbuild had
been silently accepting: args.base losing its unknown-narrowing across
the HAS_BASE flag (TS18046) and gate findings missing the required
impact field (TS2322) — both dialects fixed, both pinned in parity
tests. The run also gains a live findings board (artifact.board, fed
by the five report sites now tagged "findings" with a stage field):
every confirmed finding is a card that moves verified → unconfirmed →
fixed/unfixed/worse as fix rounds land — the dashboard §10 of the
authoring contract asks for, absent from the claude dialect which has
no artifact primitive. The pure helpers (mdSafe, prMetaFromJson) were
verified through EvalWorkflowSnippet against the same compiler path.

The first live workflow run (dogfooding this very stack, twice) also
changed the release: run one was gate-stopped by the new secrets
family flagging its own test fixtures — exactly as designed — which
added the spec-review:allow inline escape hatch to 0.8.0's family;
run two put the full panel over the stack and found seven defects,
all fixed in-place before commit: the fix_from pre-fix gate now
failure-handles (a red gate enters the tracked findings instead of
rendering as all-pass; every report surface reads the authoritative
last gate run via finalGate), the 0.7.1 pr dirty-refusal repair
gained its missing anchor, and five doc/comment drifts were synced
(js stage-field comment, quickstart recommendation promise, SKILL.md
npm shape, the fix_rounds explicit-0 comments, the gates gate-red
fix_from carve-out).

Migration: none required — the new tree is additive; re-run
tools/sync.sh so the router command and the expanded skill tree reach
every harness root.

## 0.8.0 — 2026-09-27

Principles and secret scanning — aligning the panel with where AI code
review stood in 2026 (precision as the trust metric; deterministic
security checks before reviewer attention; explicit human ownership).
(1) SKILL.md gains a Principles section: the panel's contract in
priority order — machine-decidable before human attention; evidence or
it does not exist; independence beats volume; zero findings is success;
stated intent is context, not a waiver; AI advises, the human decides;
honesty about coverage; the repo owns its standards. Collisions resolve
toward the lower-numbered rule, giving future edits a compass instead
of folklore. (2) The gate gains an always-on secrets family (diff
mode): a high-precision token-shape scan — AWS access keys, GitHub
PATs (classic and fine-grained), GitLab PATs, Stripe live keys, Slack
tokens, Google API keys, npm tokens, Anthropic keys, private-key
headers — over the change's added diff lines AND untracked files (a
brand-new untracked file is the classic leak vector the diff alone
misses). Precision over recall by design: curated shapes only, prose
about keys never trips it, project mode skips the family (fixtures
with fake keys would false-positive there — the security lens owns
whole-project reading). Five new gate tests cover red/green, the
untracked path, fixture-shaped prose, tree-mode exclusion, and the
escape hatch. Found the hard way by the first live workflow run
(dogfooding this very stack): the family flagged its own test
fixtures, exactly as designed — a line carrying the inline marker
"spec-review:allow" (gitleaks-style) is now skipped, so tests for the
family can hold fixture tokens without weakening the patterns.

Migration: none required — the secrets family is additive; a change
that adds a secret-shaped token now fails the gate where before it
passed, which is the point. Re-run tools/sync.sh to pick up the new
gate and the Principles section.

## 0.7.1 — 2026-09-27

Repairs every panel-confirmed defect from the 0.7.0 review (three
independent lenses, triage, independent confirmation — six findings, all
verified). (1) The fix_from default `FIX_ROUNDS = 2` assigned a const:
the zcode dialect could not compile (TS2588) and the claude dialect
threw at startup on the documented default flow — now a let in both.
(2) A fix_from continuation with `target: pr` dereferenced a null
prMeta in the shared verified render (and `target: branch` rendered a
bogus empty entry) — the pr/branch verified lines are now guarded by
`!FIX_FROM` in both dialects. (3) The claude dialect's confirmation
wave and fix-review push rebuilt findings field-by-field and dropped
the new impact field — both now carry it, restoring parity with the
zcode spread. (4) The pr-mode dirty-tree refusal now applies
unconditionally: a dirty tree misattributes uncommitted work to the PR
whether or not the head is already checked out (distinct refusal
messages per case). (5) PR-author-controlled metadata (title, author,
base, url) is markdown-escaped via mdSafe before rendering into the
report artifact, closing the report-markdown injection surface. (6)
Branch mode now surfaces "uncommitted work included in the reviewed
diff" in the report itself (scopeDirty), matching SKILL.md's promise.
Root cause guarded: a new parity test scans both dialects for any
assignment to a const-declared name (the TS2588 class) — deterministic,
self-tested against the exact 0.7.0 bug shape, so the suite can no
longer stay green over a crashing workflow. All six repairs are pinned
by new anchors in test_workflow_copies.py.

Migration: none required — every change is a repair of 0.7.0 behavior;
rerun tools/sync.sh to replace the broken 0.7.0 workflow installs.

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
