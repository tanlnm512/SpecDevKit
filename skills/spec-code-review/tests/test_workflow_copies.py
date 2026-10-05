"""Structural parity between the spec-code-review workflow dialects.

Two masters automate one review protocol on two runtimes — the zcode
facade (workflows/spec-code-review.dwf.ts) and the Claude Code workflow
runtime (workflows/spec-code-review.js). The runtimes impose different
primitives (persistent typed agents + world.run vs one-shot agents +
probe seams), so byte equality is impossible; what MUST stay identical
is the protocol: the phases, the panel, the tunables, the ask anchors,
and the report contract. These tests are the drift guard for that
layout — a protocol edit to one master that misses the other fails here.

Runtime-specific invariants are pinned too (no import/export/declare in
the zcode function body; meta-first, no module loading, no
nondeterministic primitives, shell only through probe agents in the
claude script), mirroring tools/tests/test_workflow_defs.py's dialect
tests for spec-run.
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
DWF_TS = SKILL / "workflows" / "spec-code-review.dwf.ts"
WF_JS = SKILL / "workflows" / "spec-code-review.js"
# D-014: the shared review oracle is the single home of the asks,
# systems, tunables, sharding, findings parsing and report assembly the
# dialects used to duplicate — anchors that lived "in both masters" now
# live here, once, and the dialects are pinned for the relay.
ORACLE = SKILL / "scripts" / "review_orchestrator.py"

# shardProjectFiles is executed (not just anchored) by ShardPartitionTests
# below; node is the executor, so the invariant test skips loudly where
# node is absent or cannot execute TypeScript rather than silently not
# protecting the partition.
NODE = shutil.which("node")

# The protocol spine both dialects must carry, phase for phase. The
# fix_from loader phase runs first in source order (its phase() call is
# emitted before the scope phase's, though only executed in fix_from
# mode). The preflight phase (0.10.0) runs between the green gate and
# the panel on fresh reviews only.
PHASES = [
    "Load the findings from the previous review",
    "Scope the change and run the repo's checks",
    "Preflight the codebase and modules the target touches",
    "Review the change through separate lenses and confirm every finding",
    "Fix the confirmed findings and verify every fix",
    "Synthesize the final review report",
]

# Load-bearing sentences of the shared ask texts — anchors that drift
# the moment someone rewords one master's prompts without the other.
ASK_ANCHORS = [
    "never invent one to seem busy",
    "the repo's checks own those",
    "cosmetic proximity is not a fix",
    "An empty findings list is the expected answer for clean fixes",
    "merge | fix-first | human",
    "escalate and say so plainly rather than working around it",
]

# The whole-project mode (target: project) carries its own ask family in
# both masters — anchors that pin the project-side contract. Since 0.11.0
# the reviewers read sharded parts of the full target, so the scope
# sentence names the part, not a bare file list.
PROJECT_ASK_ANCHORS = [
    "There is no diff — the target is ",
    "of the project's tracked source files (",
    "your sibling reviewers of the same lens read the other parts",
    "present in the code as it stands",
    "path:line in the current tree",
    "merge means the code is ready as it stands",
]

# The 0.11.0 full-coverage audit contract: sub-repo targeting rooted at
# an absolutely-resolved toplevel (D-009), sharded project coverage
# (D-010), and audits continuing past red gates (D-011). Anchors pin the
# resolution and refusal sentences, the sharding helpers and tunables,
# the gate-continue line, and the accurate red-gate gateNote.
SUBREPO_SHARD_ANCHORS = [
    "did not resolve to a git repository",
    "repo with target",           # the refusal names the unsupported combo
    "the workflow from inside that repository",
    "function shardProjectFiles",
    "function partLabel",
    "reviewer part(s) per lens",
    "project audit continues past the red gate",
    "did NOT all pass — failing:",
    "Repo check failed before the review",
]

# The pr and branch targets (0.5.0) resolve to a merge-base diff before
# the panel machinery runs, so the ask family is shared with diff mode.
# These anchors pin the resolution contract in both dialects: the gh pr
# fields, the merge-base/rev-list mechanics, the default-branch
# detection, and the checkout safety rule (never check out over a dirty
# tree; always announce the checkout with the previous HEAD).
PR_TARGET_ANCHORS = [
    "baseRefOid",
    "headRefOid",
    "refs/remotes/origin/HEAD",
    "merge-base",
    "rev-list",
    "needs a pr arg",
    "the working tree is dirty",
    "common ancestor",
    "switch back when done reviewing",
]

# The stated-intent channel and the split recommendation (0.6.0): intent
# (the arg, else the PR description) rides into the reviewer, triage,
# final and fixer asks in both dialects, with the intent-blind
# confirmation rule preserved; oversized changes earn a split line in
# the report. Anchors pin the load-bearing sentences and tunables.
INTENT_SPLIT_ANCHORS = [
    "the author's stated intent",
    "stated intent never waives a demonstrable defect",
    "consider splitting into smaller",
]

# The fix_from continuation and the impact field (0.7.0): a fix-only run
# skips the review stages and carries the previous report's findings into
# the fix loop; every reviewer ask asks for a one-line impact. Anchors
# pin the shared sentences and the loader/probe wiring.
FIX_CONTINUATION_ANCHORS = [
    "fix_from",
    "findings carried from the previous review",
    "the review stages were skipped (fix_from)",
    "what the defect breaks and when it bites",
]
FIX_FROM_PROBE = "fix-from-probe"

# The 0.13.0 identity and carrier contract (D-013): findings carry
# stable ids minted at tracking (board key, report heading, fixer
# replies join on ids), the saved report markdown parses back as a
# fix_from carrier, and the fixer reads the target repo's AGENTS.md
# before its first edit. Anchors pin the minting helpers, the
# id-bearing heading, the parser and the carried-N fallback in both
# dialects.
FINDING_ID_ANCHORS = [
    "the finding ids you fully fixed",
    "before your first edit — the repo's own rules bind your fixes",
    "function parseFindingsMd",
    '"carried-" + (++carriedSeq)',
    '"### [" + f.id + " · "',
    'nextId("gate")',
    'nextId("fix-review")',
]

# The 0.7.1 repair pins: every panel-confirmed defect from the 0.7.0
# review gets an anchor here so it cannot silently regress.
FIXES_071 = {
    "ts": [
        "let FIX_ROUNDS",                       # F1: const assignment crashed both dialects
        "!FIX_FROM && PR",                      # F2: fix_from + target pr null-crashed the verified render
        "!FIX_FROM && BRANCH_MODE",             # F2: target branch rendered a bogus entry
        "The refusal is unconditional",         # F4: pr dirty refusal moved out of the checkout branch
        "refused to review a PR target over a dirty working tree",  # F4: the refusal's notCovered line
        "function mdSafe",                      # F5: PR metadata escaped in report markdown
        "let scopeDirty",                       # F6: uncommitted-work note surfaced in the report
        "included in the reviewed diff",        # F6: the note line itself
    ],
    "js": [
        "let FIX_ROUNDS",
        "!FIX_FROM && PR",
        "!FIX_FROM && BRANCH_MODE",
        "The refusal is unconditional",
        "refused to review a PR target over a dirty working tree",
        "function mdSafe",
        "let scopeDirty",
        "included in the reviewed diff",
        # F3: the confirmation wave and fix-review push rebuild
        # field-by-field in this dialect — impact must be carried
        'impact: typeof keptAll[i].finding.impact',
        'impact: typeof fixKept[i].impact',
    ],
}

# The 0.9.0 dogfood-review repairs (the first live workflow run found
# seven defects in this very stack; all fixed before commit).
FIXES_DOGFOOD = [
    "Repo check failed before the fixes",   # a red pre-fix gate enters tracked instead of rendering green
    "let finalGate",                        # renders read the authoritative last gate run
    "indistinguishable from omission",      # explicit fix_rounds: 0 is bumped too — comments state it
]

# The 0.11.0 panel-review repairs (the review of the 0.11.0 change
# itself, plus its fix-review round, confirmed these defects; all fixed
# before commit): a part reviewer that returns nothing becomes a
# coverage failure, the fix loop keys off tracked so gate findings
# reach the fixer, the fix-loop asks carry the repo block with a rooted
# diff command, and every confirmation claim — the report's re-check
# bullet and counts, the Mode line, the final-assessment preamble —
# names non-gate findings, since gate findings are confirmed by their
# checks' exit codes, not an independent reader.
FIXES_PANEL_REVIEW = [
    "reviewer part(s) returned no result — their files were not reviewed",
    "FIX_ROUNDS > 0 && tracked.length > 0",
    "const diffCmd = REPO_ABS",
    "Each non-gate finding was re-checked by an independent reader",
    "every kept non-gate finding confirmed by an independent reader",
    "Every kept non-gate finding has now been through independent confirmation",
]

# The preflight scout (0.10.0): one read-only map turn between the green
# gate and the panel. Anchors pin the scout ask, the injection block and
# the degradation line in both dialects. The map rides reviewer and
# final-assessment asks only — triage, fixer and confirm asks carry no
# scoutBlock call, pinned by the call-site count below.
PREFLIGHT_ANCHORS = [
    "You are the preflight scout",
    "you produce the map they start from",
    "at most 8 modules, 6 conventions, 6 risk areas",
    "never cite it as evidence",
    "preflight scout returned no map",
    "the review ran without the codebase and module context step",
]

# A plain/compound assignment to a const-declared name is a TS2588
# compile error (and a runtime TypeError in the js dialect). The 0.7.0
# release shipped exactly that — `FIX_ROUNDS = 2` under a const — while
# every suite stayed green because the tests are text anchors, not
# execution. This scanner is the deterministic guard for that class.
CONST_DECL = re.compile(r"^[ \t]*(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=", re.M)
LET_VAR_DECL = re.compile(r"^[ \t]*(?:export\s+)?(?:let|var)\s+([A-Za-z_$][\w$]*)", re.M)
DECL_LINE = re.compile(r"^[ \t]*(?:export\s+)?(?:const|let|var)\s")


def const_reassignments(text):
    """[(name, line)] for every assignment to a const-declared
    identifier. A name that is ALSO declared let/var anywhere is skipped
    entirely — without scope analysis the two declarations cannot be
    told apart, and the guard stays conservative (no false positives).
    Declarations are never assignments; for(...) heads are skipped
    (loop-scoped); property writes (obj.name =) never match; a match
    sitting inside a double-quoted string on its line (shell snippets
    embedded in probe commands) is skipped by odd-quote parity."""
    let_or_var = set(LET_VAR_DECL.findall(text))
    bad = []
    for m in CONST_DECL.finditer(text):
        name = m.group(1)
        if name in let_or_var:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        if "for (" in text[line_start:m.start()] or "for(" in text[line_start:m.start()]:
            continue
        assign = re.compile(
            r"(?<![\w$.])" + re.escape(name) +
            r"\s*(?:=(?!=)|\+\+|--|\+=|-=|\*=|/=|%=|\|\|=|&&=|\?\?=)")
        for a in assign.finditer(text):
            a_line_start = text.rfind("\n", 0, a.start()) + 1
            a_line_end = text.find("\n", a.start())
            a_line = text[a_line_start:a_line_end if a_line_end != -1 else len(text)]
            if DECL_LINE.match(a_line):
                continue  # a declaration of that name — its own scope
            if text[a_line_start:a.start()].count('"') % 2 == 1:
                continue  # inside a string literal (embedded shell)
            bad.append((name, text.count("\n", 0, a.start()) + 1))
    return bad

# The fix-loop invariant: a reader verifier is never spawned for a
# gate-lens entry (its `where` is a check name, not a file location) —
# the fresh authoritative gate re-run owns those.
GATE_EXCLUSION = '.finding.lens !== "gate"'

# The panel's third representation: each side of the rubric is also an
# installable agent brief (agents/code-review-<lens>.md). The lens focus
# strings below are asserted in BOTH workflow masters AND the matching
# brief, so no representation can drift from the others.
BRIEFS = SKILL / "agents"
LENS_BRIEFS = {
    "correctness": BRIEFS / "code-review-correctness.md",
    "security": BRIEFS / "code-review-security.md",
    "quality": BRIEFS / "code-review-quality.md",
}
FIXER_BRIEF = BRIEFS / "code-review-fixer.md"
SCOUT_BRIEF = BRIEFS / "code-review-scout.md"
PANEL_PROTOCOL = BRIEFS / "_panel-protocol.md"
LENS_FOCUS = {
    "correctness":
        "logic errors, broken edge cases, wrong or missing error handling, "
        "concurrency hazards, broken contracts between caller and callee.",
    "security":
        "untrusted input paths, injection, secrets and token handling, "
        "unsafe deserialization, permission changes, destructive operations.",
    "quality":
        "complexity the next reader pays for, over-engineering, misleading "
        "names, comments and docs that drift from the code, and tests — "
        "behavior this change alters with no test covering it, tests that "
        "cannot fail, and design fit — whether the change follows the "
        "patterns the surrounding code already establishes instead of "
        "inventing a parallel way.",
}


def read(path):
    text = path.read_text(encoding="utf-8")
    # the bake placeholder must sit inside a double-quoted literal on one
    # line, or tools/workflow-defs.py --bake would corrupt the master
    assert 'const SKILL_DIR_BAKED = "__SKILL_DIR__";' in text, path.name
    return text


def flat(text):
    """Collapse all whitespace to single spaces — prose anchors must
    match across each file's own line wrapping."""
    return " ".join(text.split())


def pflat(text):
    """flat, for python sources: implicit string concatenation across
    lines must not break prose anchors (quotes, plus signs and escape
    backslashes vanish; whitespace collapses)."""
    return " ".join(text.replace('"', " ").replace("+", " ").replace("\\", " ").split())


class ParityTests(unittest.TestCase):
    def setUp(self):
        self.ts = read(DWF_TS)
        self.js = read(WF_JS)

    def test_both_dialects_exist_and_are_bakeable(self):
        for path in (DWF_TS, WF_JS):
            self.assertTrue(path.is_file(), path)
            self.assertIn("__SKILL_DIR__", path.read_text())
        self.assertIn("scripts/gate.sh", self.js)

    def test_phases_are_identical_and_literal(self):
        ts_phases = re.findall(r'phase\("([^"]+)"\)', self.ts)
        js_phases = re.findall(r'phase\("([^"]+)"\)', self.js)
        self.assertEqual(ts_phases, PHASES)
        self.assertEqual(js_phases, PHASES)

    def test_tunables_match(self):
        # one home since D-014: the oracle owns every tunable; the
        # dialects consume its resolved flags instead of re-declaring
        oracle = ORACLE.read_text(encoding="utf-8")
        for anchor in ("FAST_MAX_LINES = 400", "FAST_MAX_FILES = 5",
                       "SHARD_TARGET_BYTES = 240000", "SHARD_MAX_FILES = 32",
                       "SUGGEST_SPLIT_LINES = 1000", "SUGGEST_SPLIT_FILES = 20",
                       "SEV_RANK"):
            self.assertIn(anchor, oracle, anchor)
        self.assertNotIn("PROJECT_MAX_FILES", oracle)
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertNotIn("FAST_MAX_LINES =", text, f"{name} re-declares an oracle tunable")
            # the mode/split decisions ride the oracle's resolved flags
            self.assertIn("fast_mode_default", text, name)

    def test_target_mode_branches_are_shared(self):
        oracle = ORACLE.read_text(encoding="utf-8")
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn('TARGET === "project"', text, name)
            self.assertIn('"--tree"', text, name)
        # the project ask family exists once, in the oracle, and both
        # dialects dispatch on its ask kinds
        for fn in ("def _review_ask_project", "def _triage_ask_project",
                   "def _confirm_ask_project", "def _final_ask_project"):
            self.assertIn(fn, oracle, fn)
        for kind in ("review-project", "triage-project", "confirm-project", "final-project"):
            self.assertIn(kind, oracle, kind)
            self.assertIn(kind, self.js, f"{kind} relayed in js")
            self.assertIn(kind, self.ts, f"{kind} relayed in ts")

    def test_pr_and_branch_targets_are_shared(self):
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn('TARGET === "branch"', text, name)
            self.assertIn('TARGET === "pr"', text, name)
            self.assertIn("const TARGETS", text, name)
        # resolution mechanics live in the oracle's scope; the refusal
        # and checkout-safety UX lives in the dialects that render it
        for anchor in ("baseRefOid", "headRefOid", "refs/remotes/origin/HEAD",
                       "merge-base", "rev-list"):
            self.assertIn(anchor, oracle, f"{anchor} in oracle")
        for anchor in ("needs a pr arg", "the working tree is dirty",
                       "common ancestor", "switch back when done reviewing"):
            for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
                self.assertIn(anchor, flat(text), f"{anchor} in {name}")

    def test_panel_definition_matches(self):
        # the panel's lenses are defined once in the oracle; both
        # dialects dispatch on the fetched definitions
        oracle = ORACLE.read_text(encoding="utf-8")
        for label in ("correctness", "security", "quality", "general"):
            self.assertIn(f'"label": "{label}"', oracle, f"{label} in oracle")
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn("general", text, f"general dispatched in {name}")
            self.assertTrue("SYSTEMS.general" in text or "systemsCache.general" in text,
                            f"general dispatched in {name}")
            self.assertTrue("SYSTEMS.lenses" in text or "systemsCache.lenses" in text,
                            f"lenses dispatched in {name}")

    def test_ask_anchors_are_shared(self):
        # asks exist exactly once (the oracle); both dialects render
        # every wave through the batch relay
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for anchor in ASK_ANCHORS + PROJECT_ASK_ANCHORS:
            self.assertIn(anchor, oracle, anchor)
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn("askWave", text, f"batch relay in {name}")
            self.assertIn('"--kind", "batch"', flat(text), f"batch kind in {name}")

    def test_intent_channel_and_split_advice_are_shared(self):
        # intent rides the oracle's reviewer/triage/final/fixer asks
        # (intentBlock is its helper); confirmation stays intent-blind —
        # the confirm renderers never read it
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for anchor in ("the author's stated intent",
                       "stated intent never waives a demonstrable defect"):
            self.assertIn(anchor, oracle, anchor)
        self.assertGreaterEqual(oracle.count("_intent_block(ctx)"), 4,
                                "intent rides reviewer/triage/final/fixer asks")
        self.assertNotIn("_intent_block", oracle.split("def _confirm_ask")[1].split("def ")[0])
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn("INTENT_ARG", text, name)
            self.assertIn("intent: intentText", text, f"intent crosses the relay in {name}")
            self.assertIn("suggestSplit", text, f"oracle's split flag consumed in {name}")
            self.assertIn("consider splitting into smaller", flat(text),
                          f"split advice renders in {name}")

    def test_fix_from_continuation_and_impact_are_shared(self):
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            # the continuation UX sentences render from the dialects
            for anchor in ("fix_from", "findings carried from the previous review",
                           "the review stages were skipped (fix_from)"):
                self.assertIn(anchor, flat(text), f"{anchor} in {name}")
            # fix-only defaults the loop to 2 rounds instead of a no-op
            self.assertIn("if (FIX_FROM && FIX_ROUNDS === 0) FIX_ROUNDS = 2;", text, name)
        # the impact ask sentence lives in the oracle's reviewer asks
        self.assertIn("what the defect breaks and when it bites", oracle)
        # the impact field rides each dialect's finding schema: optional
        # in the zcode interface, schema-declared in the claude master
        # with the required list left unchanged (impact is optional)
        self.assertIn("impact?: string", self.ts)
        self.assertIn('impact: { type: "string" }', self.js)
        self.assertIn('required: ["where", "what", "evidence", "severity"],', self.js)

    def test_finding_ids_and_markdown_carrier_are_shared(self):
        # D-013: every tracked finding carries a stable id; the fixer
        # replies in ids; the report markdown parses back as a carrier.
        # Minting helpers, the id-bearing heading and the carried-N
        # fallback live in the oracle; the dialects mint gate and
        # fix-review ids at their tracking sites.
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for anchor in ("the finding ids you fully fixed",
                       "before your first edit — the repo's own rules bind your fixes",
                       "def parse_findings_md", "carried-{carried}",
                       "### [{f['id']}"):
            self.assertIn(anchor, oracle, anchor)
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn('nextId("gate")', text, f"gate ids minted in {name}")
            self.assertIn('nextId("fix-review")', text, f"fix-review ids minted in {name}")
        # the findings board keys on the id, never on where (zcode-only)
        self.assertIn('key: "id"', self.ts)
        # the claude fixer schema joins skipped items on ids too
        self.assertIn(
            'properties: { id: { type: "string" }, why: { type: "string" } }', self.js)

    def test_zero_seven_one_fixes_are_shared(self):
        # anchors that moved to the oracle are pinned there; the ones
        # that stayed in the dialects (mutability, render guards, the
        # refusal UX) stay pinned in both
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for anchor in ("The refusal is unconditional", "function mdSafe"):
            self.assertIn(anchor, oracle.replace("def md_safe", "function mdSafe").replace(
                "# The refusal is unconditional", "The refusal is unconditional"), anchor)
        for text, name in ((self.ts, "ts"), (self.js, "js")):
            for anchor in ("let FIX_ROUNDS", "!FIX_FROM && PR", "!FIX_FROM && BRANCH_MODE",
                           "refused to review a PR target over a dirty working tree",
                           "let scopeDirty", "included in the reviewed diff"):
                self.assertIn(anchor, text, f"{anchor} in {name}")
        self.assertIn("function mdSafe", self.js, "mdSafe in js")
        self.assertIn("*_[\\]()!<>", self.ts, "ts escapes the same markdown-active class")
        for anchor in ("impact: typeof keptAll[i].finding.impact",
                       "impact: typeof fixKept[i].impact"):
            self.assertIn(anchor, self.js, anchor)

    def test_dynamic_workflow_contract_pieces(self):
        # 0.9.0: the zcode master is checked against the real
        # dynamic-workflow compiler facade — pinned here are the pieces
        # that audit added. The findings board (live dashboard, §10) and
        # its report tag are zcode-only: the claude runtime has neither
        # an artifact primitive nor report() calls, so js carries none
        # of the board machinery (no stage field either).
        self.assertIn('artifact.board("findings"', self.ts)
        self.assertIn('columns: ["verified", "unconfirmed", "fixed", "unfixed", "worse", "gate"]', self.ts)
        self.assertEqual(self.ts.count(', "findings");'), 6, "6 report sites tagged findings")
        # unknown-narrowing fix: args.* is unknown on the facade, so a
        # narrowed value cannot cross a boolean flag variable
        for text, name in ((self.ts, "ts"), (self.js, "js")):
            self.assertIn("String(args.base).trim()", text, name)
        # gate findings carry the required impact field in both dialects
        for text, name in ((self.ts, "ts"), (self.js, "js")):
            self.assertIn('lens: "gate",', flat(text), name)

    def test_dogfood_review_repairs_are_shared(self):
        # the first live workflow run (dogfooding this stack) found the
        # fix_from pre-fix gate rendering red as green — both dialects
        # now failure-handle it and render from the authoritative gate
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            for anchor in ("Repo check failed before the fixes", "let finalGate"):
                self.assertIn(anchor, flat(text), f"{anchor} in {name}")
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertIn("indistinguishable from omission", flat(text), f"rounds comment in {name}")

    def test_panel_review_repairs_are_shared(self):
        # the review of the 0.11.0 change confirmed four defects in it;
        # each repair is pinned so none regresses — ask-side anchors in
        # the oracle, orchestration anchors in both dialects
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for anchor in ("diff_cmd = ", "Every kept non-gate finding has now been through independent confirmation"):
            self.assertIn(anchor, oracle, anchor)
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            for anchor in ("reviewer part(s) returned no result — their files were not reviewed",
                           "FIX_ROUNDS > 0 && tracked.length > 0",
                           "Each non-gate finding was re-checked by an independent reader",
                           "every kept non-gate finding confirmed by an independent reader"):
                self.assertIn(anchor, flat(text), f"{anchor} in {name}")
            # the repo arg resolves BEFORE the fix_from branch runs its
            # pre-fix gate, so a continuation run roots there too
            self.assertLess(text.index("if (REPO_ARG)"), text.index("if (FIX_FROM) {"), name)
            # the sub-repo roots every ask: the relay carries repo_abs
            self.assertIn("repo_abs: REPO_ABS", text, f"repo_abs crosses the relay in {name}")

    def test_subrepo_sharding_and_red_gate_audit_are_shared(self):
        # 0.11.0: full-coverage project audits. Sub-repo targeting roots
        # every command at an absolutely-resolved toplevel and refuses
        # unverified targets; the project target shards into parts every
        # lens reads; a red gate becomes gate findings instead of a stop.
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for anchor in ("function shardProjectFiles".replace("function shardProjectFiles", "def shard_files"),
                       "def part_label", "did NOT all pass — failing:"):
            self.assertIn(anchor, oracle, anchor)
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            for anchor in ("did not resolve to a git repository", "repo with target",
                           "the workflow from inside that repository",
                           "reviewer part(s) per lens", "project audit continues past the red gate",
                           "Repo check failed before the review"):
                self.assertIn(anchor, flat(text), f"{anchor} in {name}")
            self.assertIn("REPO_ARG", text, name)
            self.assertIn("REPO_ABS", text, name)
            self.assertIn('"--repo"', text, name)
            self.assertIn("rev-parse", text, name)
            self.assertIn("gateTracked", text, name)
        # the repo arg is declared in the zcode master's metadata
        self.assertIn("repo:", self.ts)
        # both dialects resolve the toplevel before anything else runs
        self.assertIn('"repo-probe"', self.js)
        self.assertIn('world.run("git", ["-C", REPO_ARG, "rev-parse", "--show-toplevel"])', self.ts)

    def test_preflight_scout_is_shared(self):
        # 0.10.0: the scout map rides reviewer and final-assessment asks
        # — the triage, fixer and confirm asks carry none, so
        # independent confirmation can inherit no scout claim. The ask
        # text lives in the oracle; the dialects pass the map through
        # the relay and keep the degradation line.
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for anchor in PREFLIGHT_ANCHORS:
            if anchor in ("preflight scout returned no map",
                          "the review ran without the codebase and module context step"):
                continue
            self.assertIn(anchor, oracle, anchor)
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            for anchor in ("preflight scout returned no map",
                           "the review ran without the codebase and module context step"):
                self.assertIn(anchor, flat(text), f"{anchor} in {name}")
            self.assertTrue("SYSTEMS.scout" in text or "systemsCache.scout" in text,
                            f"scout system dispatched in {name}")
            self.assertIn("scout_map: scoutMap", text, f"scout map crosses the relay in {name}")
            self.assertIn("files: PROJECT ? targetFiles : changed", text, f"scout target in {name}")
        # the scout's RepoMap is schema-validated in the claude master
        # and a typed interface in the zcode master
        self.assertIn("SCOUT_SCHEMA", self.js)
        self.assertIn('label: "preflight-scout"', self.js)
        self.assertIn("interface RepoMap", self.ts)
        # a malformed scout reply degrades to a map-less run instead of
        # killing it: the claude master re-checks its schema-validated
        # reply, the zcode master has no runtime schema so it guards the
        # three fields itself (the 0.11.0 panel review caught the ts seam
        # reading scoutMap.riskAreas.length outside the try/catch)
        self.assertIn("Array.isArray(scoutResult.modules)", self.js)
        self.assertIn("!Array.isArray(scoutMap.modules)", self.ts)

    def test_no_assignment_to_const_declared_names(self):
        # deterministic guard for the TS2588 class the 0.7.0 release
        # shipped: the scanner must be clean on both dialects...
        for text, name in ((self.ts, "dwf.ts"), (self.js, "js")):
            self.assertEqual(const_reassignments(text), [], name)
        # ...and must actually fire on the 0.7.0 bug shape
        self.assertEqual(
            const_reassignments("const FIX_ROUNDS = 0;\nif (f && FIX_ROUNDS === 0) FIX_ROUNDS = 2;\n"),
            [("FIX_ROUNDS", 2)],
        )

    def test_fix_loop_never_verifies_gate_lens_with_a_reader(self):
        self.assertIn(GATE_EXCLUSION, self.ts)
        self.assertIn(GATE_EXCLUSION, self.js)

    def test_report_contract_is_shared(self):
        for token in ("fixStatus", "notCovered", "residualRisks", "testGaps"):
            self.assertIn(token, self.ts, token)
            self.assertIn(token, self.js, token)


class VersionParityTests(unittest.TestCase):
    """The skill ships its version in four surfaces: the VERSION file,
    the SKILL.md frontmatter, the plugin manifest and the CHANGELOG's
    latest heading. 0.11.0 shipped 0.10.0 in the frontmatter because
    nothing pinned the parity — this test does."""

    def test_version_is_the_same_in_every_surface(self):
        version = (SKILL / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertIn('version: "' + version + '"',
                      (SKILL / "SKILL.md").read_text(encoding="utf-8"))
        manifest = json.loads(
            (SKILL / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], version)
        self.assertIn("## " + version + " — ",
                      (SKILL / "CHANGELOG.md").read_text(encoding="utf-8"))


def node_runs_typescript():
    """True when node exists and can execute TypeScript (unflagged type
    stripping) — the executor for the extracted dialect functions. Probes
    with a typed one-liner so pre-23.6 builds skip loudly instead of
    hard-failing the suite."""
    if not NODE:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "ts_probe.ts"
        probe.write_text(
            "function double(n: number): number { return n * 2; }\n"
            'if (double(2) !== 4) throw new Error("ts probe failed");\n',
            encoding="utf-8")
        r = subprocess.run([NODE, str(probe)], capture_output=True, text=True)
    return r.returncode == 0


class ShardPartitionTests(unittest.TestCase):
    """shardProjectFiles is the core behavioral change of 0.11.0, and
    the string anchors above only prove both dialects carry its text.
    This suite extracts the REAL function from each master and executes
    it through node, pinning the partition contract: every file in
    exactly one part, contiguous path-sorted order, the byte/file caps,
    the trailing-merge rule — and identical output from both dialects.
    (Expected outputs were derived by running the shipped functions.)"""

    @classmethod
    def setUpClass(cls):
        # Skip on capability, not mere existence: a node without
        # unflagged type stripping (pre-23.6, or older builds that only
        # strip behind --experimental flags) cannot run the extracted
        # dwf.ts function and would hard-fail the suite instead of
        # skipping — so probe it once with a typed one-liner first.
        if not NODE:
            raise unittest.SkipTest(
                "node is required to execute the real shardProjectFiles")
        if not node_runs_typescript():
            raise unittest.SkipTest(
                "node cannot execute TypeScript (unflagged type stripping "
                "required)")

    # (files, sizes, expected parts); inputs unsorted on purpose — the
    # function sorts before partitioning
    CASES = [
        # one part: a small target is a single byte-balanced run
        (["z/mod.py", "a/main.py", "m/util.py"],
         {"z/mod.py": 100, "a/main.py": 200, "m/util.py": 50},
         [["a/main.py", "m/util.py", "z/mod.py"]]),
        # byte cap: 110 KB files pair up (110+110 <= 240 KB, +110 > 240 KB)
        (["a", "b", "c", "d"], {f: 110000 for f in "abcd"},
         [["a", "b"], ["c", "d"]]),
        # trailing merge: a 50 KB tail (<= 240 KB / 4) folds into the
        # previous part instead of becoming its own
        (["a", "b", "c", "d", "e"],
         {"a": 110000, "b": 110000, "c": 110000, "d": 110000, "e": 50000},
         [["a", "b"], ["c", "d", "e"]]),
        # file cap: 7 KB files reach exactly 32 per part (32*7 = 224 KB)
        ([("f%02d" % i) for i in range(64)],
         {("f%02d" % i): 7000 for i in range(64)},
         [[("f%02d" % i) for i in range(32)],
          [("f%02d" % i) for i in range(32, 64)]]),
        # unknown sizes count as 0 bytes: the count cap drives, and the
        # 6-file tail merges back (0 bytes <= 240 KB / 4)
        ([("g%02d" % i) for i in range(70)], {},
         [[("g%02d" % i) for i in range(32)],
          [("g%02d" % i) for i in range(32, 70)]]),
        # a single file over the byte cap lands alone (300 KB > 240 KB)
        (["big", "s1", "s2", "s3"],
         {"big": 300000, "s1": 50000, "s2": 50000, "s3": 50000},
         [["big"], ["s1", "s2", "s3"]]),
    ]

    def test_partition_contract_holds_in_the_oracle(self):
        """D-014: sharding lives once, in the oracle — execute its REAL
        shard_files against the same cases the dialect extraction used
        to cover: expected partitions, contiguity, both caps."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("review_orchestrator", ORACLE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cap_bytes, max_files = mod.SHARD_TARGET_BYTES, mod.SHARD_MAX_FILES
        for files, sizes, expected in self.CASES:
            got = mod.shard_files(files, sizes)
            self.assertEqual(got, expected, f"partition of {files!r}")
            self.assertEqual([f for p in got for f in p], sorted(files))
            for part in got[:-1]:
                self.assertLessEqual(len(part), max_files)
                if len(part) > 1:
                    self.assertLessEqual(
                        sum(sizes.get(f, 0) for f in part), cap_bytes)


class FindingsMarkdownTests(unittest.TestCase):
    """parseFindingsMd is the 0.13.0 fix_from markdown carrier (D-013).
    Like ShardPartitionTests, this suite extracts the REAL function from
    each master and executes it through node: the id-bearing 0.13
    heading, the pre-id 0.12 heading, the fix-suffix, the bullet fields,
    junk lines and the where/what floor must behave identically in both
    dialects — the report findingsMd emits is the exact text this
    parser reads back on a fix_from handover."""

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise unittest.SkipTest(
                "node is required to execute the real parseFindingsMd")
        if not node_runs_typescript():
            raise unittest.SkipTest(
                "node cannot execute TypeScript (unflagged type stripping "
                "required)")

    SAMPLE = "\n".join([
        "# Code review — HEAD (3 files, ~40 added lines)",
        "",
        "## Findings (4 confirmed · 2 high · 0 fixed)",
        "",
        "### [correctness-1 · HIGH · verified · correctness] Refund computed before conversion.",
        "- where: `src/pay.py:42`",
        "- evidence: amount = base * qty  # line 42",
        "- impact: non-USD refunds wrong",
        "",
        "### [quality-2 · LOW · unconfirmed · quality · fix: unfixed] Dead legacy block slows startup.",
        "- where: `src/legacy.py:10`",
        "- evidence: import six — unused",
        "",
        "### [MEDIUM · verified · security] Legacy-shape finding without an id.",
        "- where: `src/old.py:7`",
        "- evidence: md5 used for passwords",
        "",
        "### [gate-3 · HIGH · verified · gate] Repo check failed: pytest",
        "- where: `pytest`",
        "- evidence: 2 failed",
        "",
        "### [quality-9 · MEDIUM · verified · quality] No where bullet — dropped.",
        "",
        "Some prose line that is not a finding.",
        "- evidence: orphan bullet",
    ])

    EXPECTED = [
        {"id": "correctness-1", "where": "src/pay.py:42",
         "what": "Refund computed before conversion.",
         "evidence": "amount = base * qty  # line 42", "severity": "high",
         "status": "verified", "lens": "correctness",
         "impact": "non-USD refunds wrong", "fixStatus": "pending"},
        {"id": "quality-2", "where": "src/legacy.py:10",
         "what": "Dead legacy block slows startup.",
         "evidence": "import six — unused", "severity": "low",
         "status": "unconfirmed", "lens": "quality",
         "impact": "", "fixStatus": "unfixed"},
        {"id": "", "where": "src/old.py:7",
         "what": "Legacy-shape finding without an id.",
         "evidence": "md5 used for passwords", "severity": "medium",
         "status": "verified", "lens": "security",
         "impact": "", "fixStatus": "pending"},
        {"id": "gate-3", "where": "pytest",
         "what": "Repo check failed: pytest", "evidence": "2 failed",
         "severity": "high", "status": "verified", "lens": "gate",
         "impact": "", "fixStatus": "pending"},
    ]

    def test_report_markdown_round_trips_through_the_oracle(self):
        """D-014: findings markdown and its parser live once, in the
        oracle — the report it renders must parse back to exactly what
        a fix_from handover carries (D-013's carrier contract)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("review_orchestrator", ORACLE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        parsed = mod.parse_findings_md(self.SAMPLE)
        self.assertEqual(parsed, self.EXPECTED)
        # render → parse is the identity the carrier depends on
        rendered = "\n".join(mod.findings_md([
            {"id": f["id"] or "carried-1", "where": f["where"], "what": f["what"],
             "evidence": f["evidence"], "severity": f["severity"], "status": f["status"],
             "lens": f["lens"], "impact": "", "fixStatus": "pending"}
            for f in self.EXPECTED]))
        round_trip = mod.parse_findings_md(rendered)
        self.assertEqual([(f["where"], f["what"], f["severity"]) for f in round_trip],
                         [(f["where"], f["what"], f["severity"]) for f in self.EXPECTED])


class ZcodeDialectTests(unittest.TestCase):
    """The zcode facade compiles a plain function body: no import/export/
    declare token anywhere (comments included), literal phase names, and
    the gate reached through world.run."""

    def setUp(self):
        self.ts = DWF_TS.read_text(encoding="utf-8")

    def test_no_facade_forbidden_tokens(self):
        for token in ("import", "export", "declare"):
            self.assertIsNone(
                re.search(rf"\b{token}\b", self.ts),
                f"forbidden token {token!r} in spec-code-review.dwf.ts")

    def test_gate_runs_through_world_run(self):
        # D-014: the shell seam is the oracle itself — one world.run per
        # fetch, gate.sh reached only inside it
        self.assertIn('world.run("python3"', self.ts)
        self.assertIn("scripts/review_orchestrator.py", self.ts)
        self.assertIn("gate-probe", self.ts)

    def test_panel_briefs_are_injected_at_run_time(self):
        # no user-installable agent types on zcode: the briefs are read
        # from the skill dir at run time and appended to the inline
        # personas; a missing brief degrades to the inline rubric
        self.assertIn("world.run(\"cat\"", self.ts)
        for brief in ("_panel-protocol.md",
                      "code-review-correctness.md",
                      "code-review-security.md",
                      "code-review-quality.md",
                      "code-review-fixer.md",
                      "code-review-scout.md"):
            self.assertIn(brief, self.ts, brief)


class ClaudeDialectTests(unittest.TestCase):
    """Claude Code dynamic workflows: `export const meta` as the first
    statement, no module loading, no direct fs/shell in the script (the
    probe agents are the seam), deterministic primitives only."""

    def setUp(self):
        self.js = WF_JS.read_text(encoding="utf-8")

    def test_meta_is_the_first_statement(self):
        first = next(l for l in self.js.splitlines() if l.strip())
        self.assertTrue(first.startswith("export const meta"),
                        f"first statement is: {first!r}")
        self.assertIn('name: "spec-code-review"', self.js)

    def test_no_module_loading_and_no_nondeterministic_primitives(self):
        self.assertIsNone(re.search(r"\bimport\b", self.js))
        self.assertIsNone(re.search(r"\brequire\s*\(", self.js))
        self.assertNotIn("Date.now", self.js)
        self.assertNotIn("Math.random", self.js)

    def test_documented_primitives_and_schema_validation(self):
        for token in ("pipeline(", "agent(", "phase(", "log(",
                      "schema:", "additionalProperties: false"):
            self.assertIn(token, self.js)

    def test_shell_needs_route_through_probe_agents(self):
        self.assertNotIn("world.run", self.js)
        self.assertNotIn("subprocess", self.js)
        self.assertIn("gate-probe", self.js)
        self.assertIn("scope-probe", self.js)
        # pr/branch resolution rides the ONE scope fetch (NFR-003)
        # fix_from continuation probe (0.7.0): reads the carried findings
        self.assertIn(FIX_FROM_PROBE, self.js)
        # the oracle command reaches the probe shell-quoted, never bare
        self.assertIn('shq(skillDir + "/scripts/review_orchestrator.py")', self.js)


class AgentBriefTests(unittest.TestCase):
    """Each side of the rubric is materialized as an agent brief — the
    panel's third representation after the two workflow dialects. The
    briefs must exist, carry def-generator-compatible frontmatter, and
    hold the same lens focus strings the workflows dispatch on."""

    def test_every_rubric_side_has_a_brief(self):
        for label, path in LENS_BRIEFS.items():
            self.assertTrue(path.is_file(), f"{label}: {path}")
        self.assertTrue(FIXER_BRIEF.is_file())
        self.assertTrue(SCOUT_BRIEF.is_file())
        self.assertTrue(PANEL_PROTOCOL.is_file())
        # shared prose is _-prefixed: never installed as an agent def
        for path in BRIEFS.glob("*.md"):
            if path.stem.startswith("_"):
                continue
            self.assertIn(path, list(LENS_BRIEFS.values()) + [FIXER_BRIEF, SCOUT_BRIEF],
                          f"unpinned brief: {path.name} — add it to the tests")

    def test_brief_frontmatter_is_def_generator_compatible(self):
        # tools/omp/agent-defs parse name, description, tools (comma
        # list), model, effort — the shape every dialect derives from
        for path in list(LENS_BRIEFS.values()) + [FIXER_BRIEF, SCOUT_BRIEF]:
            text = path.read_text(encoding="utf-8")
            m = re.search(r"^name: (\S+)", text, re.M)
            self.assertIsNotNone(m, f"name: in {path.name}")
            self.assertEqual(m.group(1), path.stem)
            self.assertIn("description: ", text)
            self.assertIn("model: inherit", text)
            self.assertIn("tools: ", text)
            self.assertIn("disallowedTools:", text)

    def test_lens_focus_strings_match_every_representation(self):
        # D-014: the workflows dispatch on the oracle's definitions; the
        # focus strings live in the oracle and the agent briefs
        oracle = pflat(ORACLE.read_text(encoding="utf-8"))
        for label, focus in LENS_FOCUS.items():
            brief = LENS_BRIEFS[label].read_text(encoding="utf-8")
            self.assertIn(pflat(focus), oracle, f"{label} focus in oracle")
            self.assertIn(flat(focus), flat(brief), f"{label} focus in brief")

    def test_panel_protocol_carries_the_shared_bar(self):
        text = PANEL_PROTOCOL.read_text(encoding="utf-8")
        for anchor in (
            "discrete and actionable",
            "part of the target under review",
            "escalate and say so plainly",
            "Zero findings is the expected answer",
        ):
            self.assertIn(anchor, flat(text))

    def test_fixer_brief_pins_the_hard_rules(self):
        text = FIXER_BRIEF.read_text(encoding="utf-8")
        for anchor in ("Never commit", "pin the corrected behavior in the test"):
            self.assertIn(anchor, flat(text))
        # D-012: the fixer is the review side's only code writer — the
        # kit-wide engineering rules ride its brief (byte parity with
        # the shared-protocol carrier is pinned in
        # tools/tests/test_kit_rules.py)
        for anchor in (
            "## Engineering rules (kit-wide)",
            "fail on the pre-fix code",
            "NEVER poll a",
            "git history owns that",
            "one owner test at the strongest boundary",
        ):
            self.assertIn(anchor, flat(text), anchor)

    def test_scout_brief_pins_the_map_not_findings_rule(self):
        # the scout is orientation, never a findings source: the brief
        # must state the mission boundary and the honest-output rule
        text = SCOUT_BRIEF.read_text(encoding="utf-8")
        for anchor in (
            "the map they start from",
            "You do not report defects",
            "riskAreas",
            "a guessed entry is not",
        ):
            self.assertIn(anchor, flat(text))


if __name__ == "__main__":
    unittest.main(verbosity=2)
