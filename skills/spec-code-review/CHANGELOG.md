# Changelog — spec-code-review

Release history. The skill began life 2026-09-23 as the validated
`spec-code-review` dynamic workflow in the SpecDevKit repo (three-stage
review: mechanical gate → specialist panel with triage and independent
confirmation → synthesis), then became a portable sibling skill.

## Unreleased

Kilo harness support (spec-to-prod D-033): the `/spec-code-review`
router installs to `~/.config/kilo/command/` and the panel briefs
render as Kilo subagent defs (`mode: subagent` + permission map) in
`~/.config/kilo/agent/` — gated on `~/.config/kilo` existing. Skills
already reach Kilo via the `~/.agents/skills` root; no workflow
dialect (inline stages, like opencode/droid).

Labelled design-smell baseline in the quality lens (D-015, serves
eval cases E2/E5). The quality brief's rubric now carries a fixed
twelve-smell baseline (Fowler, _Refactoring_, ch.3 — Mysterious Name
through Refused Bequest, each what → how-to-fix) with two binding
rules: every smell is always a judgement call ("possible <smell>",
never a hard violation), and a documented repo standard or
established surrounding pattern overrides the baseline. Also
sharpens the "tests that cannot fail" tautology shape: an expected
value recomputed by the same logic the code under test uses (instead
of a known-good literal, worked example, or the spec) is named
explicitly. Brief-only fix, one source — both workflow dialects
append the brief into every reviewer ask at run time (the 0.13.1
pattern), so inline, workflow and general-reviewer paths get it
together.

Shared review oracle (D-014): target resolution, the mechanical gate,
project sharding, finding IDs, carried-findings parsing, report
assembly, panel systems and ask text move from the two workflow
dialects into one stdlib script (`scripts/review_orchestrator.py`),
unit-tested in the skill's suite and fetched by both dialects through
one probe per phase. The dialect twins shrink to thin orchestration
(2,114 → 996 and 2,239 → 1,102 lines) and the runtime harness now
EXECUTES the Claude dialect end-to-end (`tools/tests/
test_workflow_runtime.py`). Parity tests re-pinned to the split:
shared anchors live in the oracle once, dialect anchors pin the relay.

## 0.1.0 — 2026-10-05 (re-baseline)

Suite-wide version re-baseline: every skill resets to 0.1.0 (user
decision, 2026-10-05), and releases from here bump minor or patch by
the user's explicit choice at release time — never automatically
(RELEASE.md § 2). No behavior change rides this entry; the latest
behavioral releases below remain accurate history.

Migration: none required — the reset is metadata-only; update any
pinned-version references to 0.1.0.

## 0.13.1 — 2026-10-05

Quality-lens severity calibration for test findings (serves eval case
`spec-code-review/e2`). The 2026-10-04 baseline run found EXPECTED
defect 4 — a test-facing helper that cannot fail — but rated it `low`
against the answer key's `medium` floor: nothing in the quality brief
told a lens that a fabricated safety net is a real defect rather than
a nit. The brief's "Tests that cannot fail" rubric now pins the floor:
a test that cannot fail while the behavior it names did change is
`medium` at minimum. Brief-only fix, one source — both workflow
dialects append the brief into every reviewer ask at run time, so
inline and workflow paths get the calibration together. Verified live:
a fresh panel re-run over the seeded-bug fixture reports all four
EXPECTED rows at or above their floors (`evals/results/
2026-10-05-e2.md`, 4/4 criteria pass; the pre-fix failure is recorded
alongside it from the baseline run).

Migration: none required — the calibration rides the brief every
reviewer already reads; no workflow, argument, or report shape changed.


## 0.13.0 — 2026-10-02

Stable finding ids and the report markdown as the fix_from carrier
(D-013). A finding's identity is its `id`, minted when it becomes
tracked — `<lens>-<n>` at confirmation, `gate-N` / `fix-review-N`
in the loop, `carried-N` for id-less carried items — replacing
`where` (which collides at a shared `path:line` and moves under the
fixes the loop lands). The id rides the findings board key, the
report heading (`### [correctness-1 · HIGH · verified · lens] …`),
the returned findings JSON, and the fixer's `addressed`/`skipped`
replies (now ids, not matched `what`-strings). `fix_from` accepts
the saved report markdown itself — `parseFindingsMd` reads the
findings section back (id-bearing 0.13 headings and pre-id 0.12
headings alike), so the review-then-ask flow hands over the artifact
the user actually saved; JSON stays equally valid. The fixer now
reads the target repo's AGENTS.md/CLAUDE.md before its first edit —
the reviewers already did; the repo's own rules bind the fixes.

Migration: none required — ids are additive (a fix_from payload
without them mints `carried-N`), and the pre-0.13 report markdown
still parses. Fixes that consume the report's findings JSON
programmatically see one new leading field per item (`id`).

## 0.12.0 — 2026-10-01

Kit-wide engineering rules in the fix loop (D-012): the fixer brief
(`agents/code-review-fixer.md`) carries the suite's engineering
rules verbatim as § Engineering rules — test discipline (a new or
strengthened test protects behavior, a contract, or a credible
regression; smallest test that proves it; a regression test fails
on the pre-fix code for the intended reason), the backgrounded-job
discipline (never poll a backgrounded job), and strict code
commenting (why not what; no decision logs or volatile values —
git history owns the why). The brief is the one channel that
reaches every fixer path: runtime-loaded by both workflow
dialects, installed as an agent def, and cited by SKILL.md
§ Stage 4 for the inline path. Compliance-side, not
enforcement-side: the lenses keep their own bar (Principle 8 —
the panel imposes nothing of its own). The brief's section is a
generated view of the canonical `rules/engineering-rules.md`
(injected by `tools/kit-rules.py`, drift-checked — spec-to-prod's
D-028); `tools/tests/test_kit_rules.py` pins the anchors and the
injection.

Migration: none required — additive brief section; workflow
masters are untouched, so no re-bake is needed.


## 0.11.0 — 2026-09-28

Full-coverage project audits, verified on a live 441-file run. Three
changes, each proven by that audit (a multi-repo workspace's sub-repo,
441 tracked source files / ~3.7 MB, read as 18 reviewer parts per lens,
54 reviewer sessions, red pytest gate):

- **Sub-repo targets — the `repo` arg** (D-009). In a multi-repo
  workspace whose root is not a git repository, project mode
  previously reviewed nothing and exited clean ("no tracked source
  files matched") — a confident empty report. `repo <dir>` (absolute
  or cwd-relative) is resolved to the repo's absolute toplevel via
  `git -C <dir> rev-parse --show-toplevel` before anything runs; every
  git call (`git -C`), the gate (`gate.sh --repo`) and the reviewers'
  absolute file paths root there, because the runtime's cwd is not
  guaranteed to be the workspace root (observed live). Change, branch
  and PR targets refuse the arg until verified — run those from inside
  the repository.
- **Sharded project coverage** (D-010). Project mode now reviews every
  tracked source file instead of the 30 largest: the path-sorted list
  is cut into contiguous, directory-coherent parts closed at
  SHARD_TARGET_BYTES (240 000) or SHARD_MAX_FILES (32), byte-balanced;
  every lens reads every part and the lens's findings concatenate
  before triage. "Covered 30 of 441" notCovered apologies are gone —
  coverage is complete; `paths` narrows, the tunables live in control
  flow only.
- **Audits continue past red gates** (D-011). D-001's hard stop stands
  for change reviews; a project audit instead records each failing
  check as a high-severity gate finding and the panel still reads the
  code — a red test suite is an audit finding, not a blocker of the
  audit. gateNote now reports failing checks accurately wherever the
  gate is red.

SKILL.md's whole-project section, the router command, the workflow arg
metadata, and the parity tests all carry the new contract; the
PROJECT_MAX_FILES tunable and its cap wording are removed from both
dialects.

Migration: none required — the changes are additive for stock
single-repo workspaces (no `repo` arg ⇒ stock behavior, byte-identical
ask anchors on the diff path); re-run tools/sync.sh to redistribute.

## 0.10.0 — 2026-09-28

Preflight step — the scout. Between the green gate and the first
reviewer, one read-only agent explores the codebase and the modules the
target touches and returns a bounded RepoMap the panel starts from:
`modules` (name/path/role, within two hops of the target, ≤8),
`conventions` (the patterns design fit is judged against, ≤6) and
`riskAreas` (one-line paths deserving extra attention, ≤6). The map
rides the reviewer asks and the final assessments in both workflow
dialects as context to verify, never evidence to cite; triage,
confirmers and the fixer never receive it, so an independent
confirmation inherits no scout claim; the scout reports no findings —
a suspicion travels only as a riskAreas line with its path. A failed
scout degrades to the raw target with a notCovered line; fix_from runs
skip the step (their review stages are skipped); fast mode still gets
it — one bounded turn buys every reviewer the same starting ground.
The scout is materialized as `agents/code-review-scout.md` (injected
into the zcode master's scout persona at run time, like the lens
briefs; inline SCOUT_SYSTEM in the claude master). New phase
"Preflight the codebase and modules the target touches" in both
masters; contracts/panel.md gains the Preflight section and the
roles-matrix row; D-008 records the decision; the router command and
README name the step; parity tests pin the ask anchors, the
scoutBlock call-site count (5 asks + definition — the confirm, triage
and fixer asks carry none), the phase, and the brief.

Migration: none required — the step is additive; re-run tools/sync.sh
so the scout brief reaches every harness root.

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
