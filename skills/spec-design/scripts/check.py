#!/usr/bin/env python3
"""Mechanical Phase-C checks for a spec folder under specs/<name>/.

Verifies what a script can: file presence (5 contract files + survey.md/
research.md as optional inputs; intent.md a third optional input,
checked only when present), ID traceability graph (FR/NFR/AC/US/TC/D;
FR, applicable NFR, and AC test coverage enforced, US stays WARN),
task-dependency and coverage-matrix consistency (including cross-phase
`(after T###)` chains and FR→milestone coverage in plan.md), D-###
structural completeness, burndown arithmetic (incl. the Σ total row),
checkbox hygiene, NEEDS CLARIFICATION markers, unfilled template
placeholders, vague plan phrases (TBD, "handle edge cases"…),
citation-path reality (heuristic, any known source extension — not just
.py), survey-baseline staleness, survey.md evidence reality (every
file:symbol:line citation names a real def/class — FAIL on a fabricated
symbol, WARN on line drift), verify-command path reality (a pytest path/glob
argument, in any contract/input file, must match a real file — WARN on
zero matches), directory/glob-aware parallel-file overlap between [P] tasks, TC structural
shape, spec-status ↔ task/INDEX consistency, EARS-shaped FRs (every FR
line says 'shall'), constitution presence, context-baseline presence, and
stage gating (progress requires Status ≥ approved; NEEDS CLARIFICATION
resolved before tasks exist), approval-freeze presence and integrity
for every approved-or-later spec (tiny tier included), and
git existence/ancestry for recorded lifecycle SHAs. Test quality itself
stays a human/LLM check.
SDLC coverage, scaled by tier: the `**Type**` header's vocabulary
(feature | bugfix | hotfix | refactor | upgrade; absent reads feature) at
both tiers and in intent.md; at full tier every quality family triaged
(Security, Privacy, Performance, Reliability, Observability,
Accessibility — an NFR, or `not applicable: <reason>`), a non-empty
`## Interfaces & data` in tech-spec.md and `### Rollout` in plan.md
(`none — <reason>` counts), and for a refactor or upgrade a
behavior-preservation TC (a `**Preserves**:` line; at tiny tier a task
`Accept:` command instead). These coverage checks FAIL a draft and WARN
once the contract is frozen. Cross-spec: every `**Depends on**` name
must be a spec under specs/ or its archive (FAIL), a dependency not yet
approved WARNs, an in-flight spec whose pending Touches overlap this
spec's WARNs, and the specs/INDEX.md line must match index.py's render.
--fix-burndown repairs the burndown table from the actual task entries
before checking; --next-ids prints the next free ID per family
(append-scope helper) and exits; --survey-only runs just the evidence-
reality and verify-command checks against survey.md alone (the other four
contract files need not exist yet) — the surveyor agent's own self-check,
meant to be run right after writing survey.md and before returning its
digest, so a bad survey fails here instead of flowing into tech/plan/qa.
--intent-only runs just the intent artifact's own refusal families against
specs/<name>/intent.md (the analyst+grill front end's output, an optional
input like research.md): unfilled/empty artifact, surviving template
placeholders, open NEEDS CLARIFICATION markers (the grilling vocabulary),
an empty required section (Problem, Audience, Constraints, FR seeds) or
no FR seed, a baseline sha the repo cannot resolve, and baseline
staleness — code changed between the baseline and HEAD; commits that
touch only the kit's doc trees (the specs tree, the brainstorms/ handoff
beside it) never stale it. In the full check (no flag) intent.md is an optional input:
absent → not checked; present → these same intent checks run and can
fail red — except the baseline pair, which only --intent-only fails:
intent.md is intake-time evidence, so under a docset the full check
notes a baseline the repo cannot resolve as SKIPPED and code changed
since the baseline as stale (a squash, rebase, shallow clone, or a
teammate's commit must not strand an in-flight docset; survey.md's
baseline owns freshness there).
--constitution runs only the repo-level specs/CONSTITUTION.md presence/fill
check and exits — a scriptable form of the constitution-presence gate,
usable standalone (no spec dir contract files needed) as a pre-flight or CI
hook; the full check (no flag) also runs this check inline and escalates it
from WARN to FAIL once a second spec exists in the repo, closing the gap
where a later spec silently skips the gate scaffold.sh only auto-creates on
the *first* one. --checklist additionally writes specs/<name>/checklist.md
— a plain, human-tickable FR/AC summary generated from spec.md + task.md
(regenerate-only, never hand-edited; task.md stays the only status holder).

Usage: check.py <spec-dir> [--repo <path>] [--fix-burndown] [--next-ids] [--checklist]
       check.py <spec-dir> [--repo <path>] --survey-only
       check.py <spec-dir> [--repo <path>] --intent-only
       check.py <spec-dir> [--repo <path>] --constitution
       check.py -h | --help        (prints this text, exit 0)
       e.g. check.py specs/postgres-backend --repo ../.. --fix-burndown
       e.g. check.py specs/postgres-backend --repo ../.. --survey-only
       e.g. check.py specs/postgres-backend --repo ../.. --intent-only
       e.g. check.py specs/postgres-backend --repo ../.. --constitution
Exit:  0 = pass (warnings allowed) · 1 = at least one FAIL · 2 = usage error
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Shared doc-state parsers live in specstate.py beside this script — one
# canonical regex per doc shape, shared with audit.py and graph.py. The
# scripts dir goes on sys.path locally (no install step): tests load this
# file by path via importlib, which does not put scripts/ on sys.path.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from specstate import (  # noqa: E402 - the sys.path setup above runs first
    CODE_SPAN,
    DEFINITIONS,
    HTML_COMMENT,
    PLACEHOLDER,
    PRESERVING_TYPES,
    QUOTE_SPAN,
    TYPE_LINE,
    TaskEntry,
    WORK_TYPES,
    code_paths,
    defined_ids,
    delivery_state,
    diff_paths,
    doc_tree_prefixes,
    lifecycle_shas,
    next_ids,
    paths_overlap,
    spec_depends,
    spec_status,
    spec_tier,
    spec_type,
    survey_baseline,
    task_touches,
    task_entries,
    tiny_task_text,
)
import freeze  # noqa: E402 - sibling module, loaded through scripts/
import index  # noqa: E402 - sibling module, loaded through scripts/

CONTRACT_FILES = ["spec.md", "plan.md", "tech-spec.md", "task.md", "test.md"]

# The quality families a full-tier spec triages one by one: an applicable
# NFR, or an NFR line saying `not applicable: <reason>`.
NFR_FAMILIES = ("Security", "Privacy", "Performance", "Reliability",
                "Observability", "Accessibility")
# Full-tier sections that must exist with a body — `none — <reason>` is one.
REQUIRED_SECTIONS = (
    ("tech-spec.md", "## Interfaces & data"),
    ("plan.md", "### Rollout"),
)
# The line that marks a test case as a behavior-preservation case.
PRESERVES_LINE = re.compile(r"^\s*-\s+\*\*Preserves\*\*:\s*\S", re.M)
APPROVED_STATUSES = ("approved", "active", "done")
IN_FLIGHT_STATUSES = ("approved", "active")
# Stage-1 inputs: created by scaffold.sh, optional (WARN not FAIL) here.
INPUT_FILES = ["survey.md", "research.md"]
ALL_FILES = CONTRACT_FILES + INPUT_FILES

# Zero-width/invisible/bidi-control characters. A zero-width space inserted between an ID's digits and its closing
# `**` (e.g. "FR-001" + ZWSP + "**") silently breaks the DEFINITIONS regex,
# making a real ID invisible to the ID graph — it fails safe (spurious FAIL,
# not a bypass) but is still corruption. Stripped once, at file-read time,
# so every regex downstream (definitions, references, traceability) sees
# clean text uniformly. Escapes only —
# these codepoints render as nothing, so spelling them out as \u escapes
# keeps this auditable instead of pasting invisible bytes into the source.
INVISIBLE = re.compile(
    "["
    "​‌‍"  # zero-width space / non-joiner / joiner
    "‎‏"        # left-to-right / right-to-left mark
    "﻿⁠­"  # BOM-as-ZWNBSP / word joiner / soft hyphen
    "‪‫‬‭‮"  # bidi embed/override + pop
    "⁦⁧⁨⁩"        # bidi isolates + pop
    "]"
)

# Template placeholder / code-span shapes and the ID-definition line shapes
# (DEFINITIONS) are shared vocabulary — canonical home: specstate.py.

# Vague plan phrases — writing-plans calls these "plan failures": a step
# that describes what to do without pinning it down. WARN-only, and bare
# "TODO" is deliberately absent (it is survey-status vocabulary, not a
# placeholder); the auditor agent judges the real thing.
VAGUE = re.compile(
    r"\bTBD\b|\bFIXME\b|implement later|fill in details|"
    r"handle edge cases|appropriate error handling|as appropriate",
    re.I,
)

# A burndown table row (label + two integers), anchored to the whole line —
# used by burndown_rewrite (it must not touch a 4-column row).
BD_ROW = re.compile(r"^\|([^|]+)\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*$")
# Same, unanchored — used by burndown_sums' scan (tolerates a trailing 4th column).
BD_ROW_SCAN = re.compile(r"^\|([^|]+)\|\s*(\d+)\s*\|\s*(\d+)\s*\|", re.M)

# Burndown label classification. A label is the Σ/total row, an attributable
# data row ("1", "P1", "Phase 1", "Sprint 1" all attribute to phase 1), or
# unattributable prose ("Setup") — still counted in the arithmetic, just not
# rewritable by --fix-burndown. Header/separator rows never reach this: their
# cells aren't both \d+, so BD_ROW/BD_ROW_SCAN don't match them at all.
BD_SUM_LABELS = {"σ", "sum", "total", "totals", "all"}
BD_PHASE = re.compile(r"^(?:phase|sprint|stage|milestone|p)?\s*[-–:]?\s*(\d+)\b", re.I)

# First path segment that marks a backtick span as a repo-rooted citation.
# Deliberately conventional, not repo-specific: specs sometimes quote wrong or
# shorthand paths in prose (e.g. `bench/foo.py` for `src/x/bench/foo.py`),
# and a heuristic WARN must not fire on those.
SRC_ROOTS = {
    # generic
    "src", "lib", "libs", "app", "apps", "pkg", "packages", "modules",
    "tests", "test", "scripts", "tools", "internal", "cmd", "docs",
    "specs", "config", "api", "server", "web", "client", ".github",
    # JVM / Android / Gradle
    "buildSrc", "gradle", "core", "data", "domain", "ui", "common",
    "shared", "feature", "features", "android", "ios",
}

# Extensions that make a backtick span "a file in this repo" for check 7.
# Add-only: an unlisted extension means the span is skipped silently, never
# failed — this check is a heuristic WARN, not a source of truth.
CODE_EXT = {
    "kt", "kts", "java", "groovy", "scala", "gradle", "pro", "aidl",
    "py", "rb", "go", "rs", "swift", "m", "mm", "c", "h", "cc", "cpp",
    "hpp", "cs", "php", "sh", "bash", "zsh", "lua", "dart", "ex", "exs",
    "ts", "tsx", "js", "jsx", "mjs", "cjs", "vue", "svelte", "css",
    "scss", "html", "json", "yaml", "yml", "toml", "xml", "properties",
    "plist", "ini", "cfg", "conf", "env", "sql", "proto", "graphql",
    "tf", "lock", "md", "txt", "rst",
}
# Characters that mark a backtick span as prose / glob / code, not a path.
NON_PATH = set("*?$<>()[]{}|\"'!;,")

# survey.md evidence citation shape: `<path with extension>:<symbol>:<line>`,
# e.g. `agent_runtime/app/adk/runner.py:_run_workflow_async:214`. Matches the
# surveyor's own template ("file:symbol with line — copied verbatim from
# grep/read output"). Surveyors have written plausible but nonexistent symbol
# names and far-off line numbers; this check catches both mechanically.
EVIDENCE_CITATION = re.compile(r"([\w./-]+\.\w+):([A-Za-z_]\w*):(\d+)\b")

# A def/class introducing SYMBOL, any indentation, optional async/decorators
# handled by just matching the def/class line itself (multi-line signatures
# still start on this line).
def _symbol_def_lines(text: str, symbol: str) -> list[int]:
    # [ \t]* not \s* for the indent: \s matches newlines too, so blank
    # lines directly above a def/class would eat backwards past ^ and skew
    # the line count.
    pat = re.compile(rf"^[ \t]*(?:async[ \t]+def|def|class)[ \t]+{re.escape(symbol)}\b", re.M)
    return [text.count("\n", 0, m.start()) + 1 for m in pat.finditer(text)]


def _placeholder_hits(text: str) -> list[str]:
    """Lines carrying unfilled template placeholders, as `<tok>@<line>`
    strings. Code spans, quoted spans, and HTML comments are stripped
    first (in Python, not in the pattern): real content like
    `<schema>_staging` lives inside backticks and must not be flagged."""
    hits: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        s = HTML_COMMENT.sub(
            " ", QUOTE_SPAN.sub(" ", CODE_SPAN.sub(" ", line)))
        m = PLACEHOLDER.search(s)
        if m or "YYYY-MM-DD" in s:
            hits.append(f"{m.group(0) if m else 'YYYY-MM-DD'}@{lineno}")
    return hits


def _baseline_head_probe(
    repo_root: Path, sha: str
) -> tuple[Path | None, str, bool]:
    """(repo containing the baseline commit, its short HEAD, whether any
    candidate .git was seen) — the probe behind every baseline-staleness
    diagnosis (survey.md's and intent.md's).

    The baseline commit may live in repo_root itself (single-repo
    layout) or in one of its immediate subdirectories (a multi-repo
    workspace where specs/ sits beside component repos; repo_root, two
    levels up from specs/<name>/, has no .git of its own). `cat-file -e <sha>^{commit}` — not just ".git
    exists" — confirms the candidate actually contains this commit
    before trusting its HEAD, so a same-named-but-wrong repo can't
    produce a false staleness warning (or a false all-clear)."""
    candidates = [repo_root]
    try:
        candidates += [
            p for p in repo_root.iterdir() if p.is_dir() and not p.name.startswith(".")
        ]
    except OSError:
        pass
    repo_hit = None
    saw_git_dir = False
    for cand in candidates:
        # A candidate dir can be unreadable (shared /tmp on CI holds
        # root-owned mode-700 systemd-private-* dirs): stat'ing inside
        # raises EACCES, which Path.exists does not swallow. An
        # unreadable dir is not a repo of ours — skip it.
        try:
            has_git = (cand / ".git").exists()
        except OSError:
            continue
        if not has_git:
            continue
        saw_git_dir = True
        try:
            r = subprocess.run(
                ["git", "-C", str(cand), "cat-file", "-e", f"{sha}^{{commit}}"],
                capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0:
            repo_hit = cand
            break
    head = ""
    if repo_hit is not None:
        try:
            head = subprocess.run(
                ["git", "-C", str(repo_hit), "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip().lower()
        except (OSError, subprocess.SubprocessError):
            head = ""
    return repo_hit, head, saw_git_dir


# verify:/Pass-condition commands that shell out to pytest with a path or
# glob argument. A wrong path matches zero files and pytest silently reports
# nothing to run, instead of failing loudly.
PYTEST_CMD = re.compile(r"`([^`\n]*\bpytest\b[^`\n]*)`")
# survey.md's own `verify:` lines sit inside the item list's ``` fence, not
# wrapped in single backticks like tech-spec.md/plan.md/test.md, so a plain
# PYTEST_CMD scan would skip them. Matched separately, backticks optional.
SURVEY_VERIFY_LINE = re.compile(r"^\s*verify:\s*(.+)$", re.M)


def _pytest_target_exists(repo_root: Path, tok: str) -> bool:
    """True if tok (a literal path or glob) resolves under repo_root OR
    under one of its immediate subdirectories. The fallback matters for a
    multi-repo workspace (specs/<name>/ documenting one component repo
    among several siblings) where
    verify commands are written relative to the component repo's own root
    (cd agent_runtime && uv run pytest tests/...), not the workspace root
    two levels up from specs/<name>/ that repo_root defaults to."""
    roots = [repo_root]
    try:
        roots += [p for p in repo_root.iterdir() if p.is_dir() and not p.name.startswith(".")]
    except OSError:
        pass
    for root in roots:
        if "*" in tok:
            if list(root.glob(tok)):
                return True
        else:
            # root can be unreadable (shared /tmp on CI: mode-700
            # systemd-private-* dirs) — treat the probe as a miss
            # instead of crashing the checker.
            try:
                if (root / tok).exists():
                    return True
            except OSError:
                continue
    return False


def bd_label(cell: str) -> tuple[str, int | None]:
    """Classify a burndown row label: ('sum'|'data'|'skip', phase or None).

    Shared by burndown_sums and burndown_rewrite so validation and repair
    can never drift apart on what counts as a data row.
    """
    lab = cell.strip().strip("*").strip("`").strip()
    if not lab or not lab.strip("-:= "):
        return "skip", None
    if lab.casefold().rstrip(":") in BD_SUM_LABELS:
        return "sum", None
    m = BD_PHASE.match(lab)
    return "data", (int(m.group(1)) if m else None)


def defined(text: str, kind: str) -> set[str]:
    return defined_ids(text).get(kind, set())


def parse_args(
    argv: list[str],
) -> tuple[str, str | None, bool, bool, bool, bool, bool, bool] | None:
    """Return (spec_dir, repo_override, fix_burndown, next_ids, survey_only,
    intent_only, constitution_only, checklist) or None."""
    fix = "--fix-burndown" in argv
    ids = "--next-ids" in argv
    survey_only = "--survey-only" in argv
    intent_only = "--intent-only" in argv
    constitution_only = "--constitution" in argv
    checklist = "--checklist" in argv
    repo = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in (
            "--fix-burndown", "--next-ids", "--survey-only",
            "--intent-only", "--constitution", "--checklist",
        ):
            i += 1
        elif a == "--repo":
            if i + 1 >= len(argv):
                return None
            repo = argv[i + 1]
            i += 2
        else:
            rest.append(a)
            i += 1
    if len(rest) != 1:
        return None
    return rest[0], repo, fix, ids, survey_only, intent_only, constitution_only, checklist


def survey_only_check(spec_dir: Path, repo_root: Path) -> int:
    """Check just survey.md's own evidence citations and verify-command
    paths — the two checks a surveyor agent can and should run on itself
    right after writing survey.md, before returning its digest. Deliberately
    skips everything that needs the other four contract files (they don't
    exist yet at Stage 1) so this catches a bad survey BEFORE tech/plan/qa
    build on it, rather than only at the full check.py.
    """
    p = spec_dir / "survey.md"
    if not p.exists():
        print("FAIL: survey.md missing")
        return 1
    survey = INVISIBLE.sub("", p.read_text(encoding="utf-8", errors="replace"))
    if not survey:
        print("FAIL: survey.md is empty")
        return 1

    fails: list[str] = []
    warns: list[str] = []

    for path_s, symbol, line_s in sorted(set(EVIDENCE_CITATION.findall(survey))):
        target = repo_root / path_s
        if not target.exists():
            warns.append(f"file not found: {path_s} (cited for {symbol})")
            continue
        try:
            target_text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        def_lines = _symbol_def_lines(target_text, symbol)
        if not def_lines:
            fails.append(
                f"{symbol!r} not found (def/class) in {path_s} (cited at line {line_s})"
            )
        elif int(line_s) not in def_lines:
            warns.append(
                f"{path_s}:{symbol} cited at line {line_s}, actually at {def_lines} "
                "— fix the citation"
            )

    seen: set[str] = set()
    for m in SURVEY_VERIFY_LINE.finditer(survey):
        cmd = m.group(1).strip()
        if "pytest" not in cmd:
            continue
        for tok in cmd.split():
            tok_clean = tok.strip("'\"")
            if not tok_clean.endswith(".py") or tok_clean in seen:
                continue
            seen.add(tok_clean)
            if not _pytest_target_exists(repo_root, tok_clean):
                warns.append(f"verify command path matches no file: `{tok_clean}` (in `{cmd}`)")

    print(f"survey-only check: {p}")
    for w in warns:
        print(f"  WARN  {w}")
    for f_ in fails:
        print(f"  FAIL  {f_}")
    print(f"  {'PASS' if not fails else 'FAIL'} ({len(fails)} fail, {len(warns)} warn)")
    return 1 if fails else 0


def _delivery_recorded(*doc_texts: str) -> bool:
    """True when any doc text carries the Delivered commit record —
    the docset is historical and HEAD-vs-baseline comparisons are moot
    (C1/C2 move HEAD by design)."""
    return any(delivery_state(t)[0] == "delivered" for t in doc_texts)


INTENT_SECTIONS = ("Problem", "Audience", "Constraints", "FR seeds")
FR_SEED = re.compile(r"^-\s+\*\*FR-\d{3}\*\*", re.M)


def _section_bodies(text: str) -> dict[str, str]:
    """Lower-cased `## heading` → its body, HTML comments removed."""
    clean = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    parts = re.split(r"^##\s+(.+?)\s*$", clean, flags=re.M)
    return {name.lower(): body.strip()
            for name, body in zip(parts[1::2], parts[2::2])}


def _code_changed_since(repo: Path, sha: str, specs_root: Path | None) -> bool:
    """Whether a path outside the kit's doc trees changed between sha and
    HEAD. Committing the specs tree (intent.md, the docset) or the
    brainstorm handoff beside it moves HEAD without moving the code the
    baseline was probed against. A diff git cannot compute reads as
    changed — never a silent all-clear."""
    paths = diff_paths(repo, sha, "HEAD")
    if paths is None:
        return True
    prefixes = doc_tree_prefixes(repo, specs_root) if specs_root else []
    return bool(code_paths(paths, prefixes))


def intent_failures(intent: str, repo_root: Path, delivered: bool = False,
                    specs_root: Path | None = None,
                    gate: bool = False) -> tuple[list[str], list[str]]:
    """(failures, notes) for the intent artifact's refusal families:
    unfilled/empty artifact, surviving template placeholders, open NEEDS
    CLARIFICATION markers (the grilling vocabulary — the same marker scan
    spec.md uses), an empty required section or no FR seed, a baseline
    sha the repo cannot resolve, and baseline staleness — code outside
    the kit's doc trees (`specs_root`, the brainstorm handoff beside it)
    changed between the baseline and HEAD. `delivered`
    exempts the baseline comparison: once the docset records its
    delivery commit, HEAD has moved by design and a stale baseline is
    history, not drift. Shared by --intent-only (`gate`) and the full
    check's optional-input path — one discipline, never a second
    checker. Only the gate fails the baseline pair: intent.md is
    intake-time evidence, and a squash, rebase, shallow clone, or a
    teammate's commit moves the repo under an in-flight docset whose
    intake already passed, so off the gate both are notes and
    survey.md's baseline owns freshness."""
    if not intent.strip():
        return ["intent.md is unfilled or empty"], []
    fails: list[str] = []
    notes: list[str] = []
    phit = _placeholder_hits(intent)
    if phit:
        detail = ", ".join(phit[:5]) + ("…" if len(phit) > 5 else "")
        fails.append(
            f"intent.md: {len(phit)} line(s) with unfilled placeholder(s) "
            f"(<name>…, YYYY-MM-DD): {detail}"
        )
    n = len(re.findall(r"\[NEEDS CLARIFICATION", intent))
    if n:
        fails.append(f"intent.md: {n} NEEDS CLARIFICATION marker(s) still open")
    if TYPE_LINE.search(intent):
        fails += type_problems(intent, "intent.md")
    bodies = _section_bodies(intent)
    for name in INTENT_SECTIONS:
        if not bodies.get(name.lower()):
            fails.append(f"intent.md: section `## {name}` is missing or empty")
    seeds = bodies.get("fr seeds")
    if seeds and not FR_SEED.search(seeds):
        fails.append(
            "intent.md: `## FR seeds` holds no `- **FR-###**:` seed"
        )
    bl = survey_baseline(intent)
    if bl is None:
        if re.search(r"Baseline\*\*[^\n]*<[^>\n]*>", intent):
            fails.append(
                "intent.md baseline is an unfilled placeholder "
                "(<version @ commit>) — fill it from the analyst run"
            )
        elif "Baseline" in intent:
            fails.append(
                "intent.md baseline header has no commit hash "
                "(expected `**Baseline**: <version> @ <sha>`)"
            )
        else:
            fails.append("intent.md has no baseline header")
        return fails, notes
    sha = bl[1]
    repo_hit, head, saw_git_dir = _baseline_head_probe(repo_root, sha)
    if repo_hit is None and not saw_git_dir:
        # A baseline that cannot be compared is visible as skipped, never fatal.
        notes.append("intent staleness: SKIPPED (not a git repo)")
    elif delivered:
        notes.append(
            "intent staleness: SKIPPED — delivery recorded; "
            "the docset is historical"
        )
    elif repo_hit is None and gate:
        fails.append(
            f"intent.md baseline {sha} is not a commit in this repo — "
            "record the HEAD the analyst probed"
        )
    elif repo_hit is None:
        notes.append(
            "intent staleness: SKIPPED — no candidate repo contains the "
            "baseline commit"
        )
    elif head and head != sha.lower() and not (
        head.startswith(sha.lower()) or sha.lower().startswith(head)
    ):
        where = f" (repo: {repo_hit.name})" if repo_hit != repo_root else ""
        if not _code_changed_since(repo_hit, sha, specs_root):
            notes.append(
                f"intent staleness: fresh — only the kit's doc trees "
                f"(specs/, brainstorms/) changed since baseline {sha} "
                f"(HEAD {head})"
            )
        elif gate:
            fails.append(
                f"intent.md baseline {sha}, HEAD {head}{where}: code "
                "changed since the baseline — re-run the analyst before trusting "
                "the artifact"
            )
        else:
            notes.append(
                f"intent staleness: stale — code changed since baseline "
                f"{sha} (HEAD {head}{where}); intake-time evidence, "
                "survey.md owns freshness"
            )
    return fails, notes


def intent_only_check(spec_dir: Path, repo_root: Path) -> int:
    """--intent-only mode: validate specs/<name>/intent.md alone — the
    analyst+grill front end's self-check, run before the artifact gates
    anything downstream. The other docset files need not exist yet; the
    failure families are exactly intent_failures'."""
    p = spec_dir / "intent.md"
    if not p.exists():
        print("FAIL: intent.md missing")
        return 1
    intent = INVISIBLE.sub(
        "", p.read_text(encoding="utf-8", errors="replace"))
    delivered = _delivery_recorded(*(
        (spec_dir / f).read_text(encoding="utf-8", errors="replace")
        for f in ("task.md", "spec.md") if (spec_dir / f).exists()
    ))
    fails, notes = intent_failures(intent, repo_root, delivered,
                                   spec_dir.parent, gate=True)
    print(f"intent-only check: {p}")
    for n_ in notes:
        print(f"  {n_}")
    for f_ in fails:
        print(f"  FAIL  {f_}")
    print(f"  {'PASS' if not fails else 'FAIL'} ({len(fails)} fail)")
    return 1 if fails else 0


CONSTITUTION_STEP = ("draft its articles with the user before the approve "
                     "gate (spec-design SKILL.md § The constitution), then "
                     "re-run")


def constitution_status(repo_root: Path) -> tuple[bool, str]:
    """(filled, message) for the repo-level specs/CONSTITUTION.md — shared by
    the standalone --constitution mode and the full check's baseline check.
    Same emptiness/placeholder bar as a contract file (check 1's <200-char
    threshold, plus the same PLACEHOLDER regex the template-hygiene check
    uses) — a constitution that's still just the unfilled template is
    structurally indistinguishable from one that was never written."""
    p = repo_root / "specs" / "CONSTITUTION.md"
    text = INVISIBLE.sub("", p.read_text(encoding="utf-8", errors="replace")) if p.exists() else ""
    if not text:
        return False, (
            "no specs/CONSTITUTION.md (scaffold.sh creates it on first "
            "scaffold; articles bind every spec)"
        )
    if len(text) < 200 or PLACEHOLDER.search(text):
        return False, "specs/CONSTITUTION.md exists but looks unfilled (empty/placeholder/too short)"
    return True, ""


def other_specs_exist(repo_root: Path, spec_dir: Path) -> bool:
    """True if specs/ holds another spec dir besides this one (excluding the
    non-spec `context/` and `archive/` folders) — i.e. this is not the
    repo's first spec, so a missing constitution cannot be blamed on
    scaffold.sh's first-scaffold auto-create."""
    specs_root = repo_root / "specs"
    if not specs_root.is_dir():
        return False
    this = spec_dir.resolve()
    for p in specs_root.iterdir():
        if p.is_dir() and p.name not in ("context", "archive") and p.resolve() != this:
            return True
    return False


def constitution_only_check(repo_root: Path) -> int:
    """Standalone --constitution mode: a scriptable form of the approval
    pre-flight's constitution presence half (the semantic "every article
    complied with" half stays the orchestrator's judgment call) — usable
    without any of the five contract files existing, e.g. as a CI hook or a
    Stage-0 sanity check."""
    filled, msg = constitution_status(repo_root)
    print(f"constitution check: {repo_root / 'specs' / 'CONSTITUTION.md'}")
    if filled:
        print("  PASS")
        return 0
    print(f"  FAIL  {msg}")
    return 1


def build_checklist(name: str, spec: str, entries: list[TaskEntry]) -> str:
    """Plain, human-tickable FR/AC summary derived from spec.md + task.md —
    for stakeholders who won't parse task.md's burndown table. Regenerated
    on every --checklist run, never hand-edited: a second, independently
    maintained status representation is exactly the drift class to avoid.
    Requirement checkboxes derive from task.md ticks (task.md stays the only status
    holder — this mirrors it, never adds a new one); ACs are listed plain
    since no independent AC-level status exists to mirror."""
    req_ticked: dict[str, list[bool]] = {}
    for e in entries:
        for req in re.findall(r"\b(?:FR|NFR)-\d{3}\b", e.block):
            req_ticked.setdefault(req, []).append(e.done)

    fr_text: dict[str, str] = {}
    nfr_text: dict[str, str] = {}
    ac_text: dict[str, str] = {}
    for line in spec.splitlines():
        s = line.strip()
        m = DEFINITIONS["FR"].match(s)
        if m:
            fr_text[m.group(1)] = s.lstrip("- ").strip()
            continue
        m = DEFINITIONS["NFR"].match(s)
        if m:
            nfr_text[m.group(1)] = s.lstrip("- ").strip()
            continue
        m = DEFINITIONS["AC"].match(s)
        if m:
            ac_text[m.group(1)] = s.lstrip("- ").strip()

    lines = [
        f"# Checklist: {name} (generated — do not hand-edit)",
        "",
        f"Regenerate: `check.py specs/{name} --checklist`. Derived from "
        "spec.md + task.md; task.md remains the only status holder — this "
        "is a read-only summary for readers who won't parse its burndown "
        "table. TC pass/fail is live, not stored here: see `audit.py "
        "proofs [--run]`.",
        "",
        "## Functional requirements",
    ]
    for fr in sorted(fr_text):
        done = fr in req_ticked and all(req_ticked[fr])
        lines.append(f"- [{'x' if done else ' '}] {fr_text[fr]}")
    if nfr_text:
        lines += ["", "## Quality requirements"]
    for nfr in sorted(nfr_text):
        done = nfr in req_ticked and all(req_ticked[nfr])
        lines.append(f"- [{'x' if done else ' '}] {nfr_text[nfr]}")
    lines += ["", "## Acceptance criteria"]
    for ac in sorted(ac_text, key=lambda a: int(re.sub(r"\D", "", a) or 0)):
        lines.append(f"- {ac_text[ac]}")
    lines.append("")
    return "\n".join(lines)


def phase_counts(entries: list[TaskEntry]) -> tuple[dict[int, int], dict[int, int]]:
    """Per-phase (total, done) entry counts — the burndown table's data rows.
    The one counting implementation behind both the table's validation and
    its repair, so the two can never drift apart on the numbers."""
    ph_total: dict[int, int] = {}
    ph_done: dict[int, int] = {}
    for e in entries:
        if e.phase is None:
            continue
        ph_total[e.phase] = ph_total.get(e.phase, 0) + 1
        if e.done:
            ph_done[e.phase] = ph_done.get(e.phase, 0) + 1
    return ph_total, ph_done


def burndown_sums(task: str) -> tuple[int, int, tuple[int, int] | None] | None:
    """(table total, table done, first Σ row) scanned from task text; None
    when no attributable data row exists (no table). Shared by check 3 and
    tick.py's pre-write validation via the same bd_label classifier."""
    data_rows: list[tuple[int, int]] = []
    sum_row: tuple[int, int] | None = None
    for cell, a, b in BD_ROW_SCAN.findall(task):
        kind, _ = bd_label(cell)
        if kind == "data":
            data_rows.append((int(a), int(b)))
        elif kind == "sum" and sum_row is None:
            sum_row = (int(a), int(b))
    if not data_rows:
        return None
    return (sum(a for a, _ in data_rows), sum(b for _, b in data_rows), sum_row)


def burndown_rewrite(task: str, ph_total: dict[int, int],
                     ph_done: dict[int, int]) -> tuple[str, list[str]]:
    """Pure rewrite of the burndown table from the given phase counts:
    returns (new text, fix messages) with no I/O, so tick.py can compute
    the prospective table before replacing the original file.

    Row labels, header, and separator lines are left byte-identical; only the
    two number cells of attributable data rows and the Σ row change. Rows we
    cannot attribute to a "## Phase N" section are left alone and excluded
    from the recomputed Σ.
    """
    lines = task.split("\n")
    new_lines = list(lines)
    msgs: list[str] = []

    # pass 1: data rows attributable to a parsed phase section
    fixes: list[tuple[int, str, int, int, int, int]] = []  # ln, label, old..
    for ln, line in enumerate(lines):
        m = BD_ROW.match(line)
        if not m:
            continue
        kind, n = bd_label(m.group(1))
        if kind != "data" or n is None or n not in ph_total:
            continue
        label = m.group(1).strip()
        fixes.append((ln, label, int(m.group(2)), int(m.group(3)),
                      ph_total[n], ph_done.get(n, 0)))

    for ln, label, a, b, na, nb in fixes:
        if a != na:
            msgs.append(f"fixed: {label} Total {a}→{na}")
        if b != nb:
            msgs.append(f"fixed: {label} Done {b}→{nb}")
        if (a, b) != (na, nb):
            new_lines[ln] = f"| {label} | {na} | {nb} |"

    # pass 2: the Σ row (matched by content, however bolded)
    sum_total = sum(f[4] for f in fixes)
    sum_done = sum(f[5] for f in fixes)
    for ln, line in enumerate(lines):
        m = BD_ROW.match(line)
        if not m:
            continue
        if bd_label(m.group(1))[0] != "sum":
            continue
        a, b = int(m.group(2)), int(m.group(3))
        if a != sum_total:
            msgs.append(f"fixed: Σ Total {a}→{sum_total}")
        if b != sum_done:
            msgs.append(f"fixed: Σ Done {b}→{sum_done}")
        if (a, b) != (sum_total, sum_done):
            new_lines[ln] = f"|{m.group(1)}| {sum_total} | {sum_done} |"
        break

    return "\n".join(new_lines), msgs


def fix_burndown(task: str, path: Path, ph_total: dict[int, int],
                 ph_done: dict[int, int]) -> str:
    """Rewrite data-row Total/Done (and the Σ row) from actual phase entries
    and write the result: burndown_rewrite plus the printed fix messages and
    file write the --fix-burndown CLI mode owns."""
    out, msgs = burndown_rewrite(task, ph_total, ph_done)
    for m in msgs:
        print(m)
    path.write_text(out, encoding="utf-8")
    return out


def print_next_ids(texts: dict[str, str]) -> None:
    """Print the next free ID per family — append-scope helper, so the
    orchestrator allocates instead of guessing (IDs are never renumbered,
    so a collision is the only failure mode to prevent). The allocation
    itself is specstate.next_ids."""
    ids = next_ids(texts)
    print("next free IDs:")
    for family in ("FR", "NFR", "AC", "US", "T", "TC", "D"):
        print(f"  {ids[family]}")


def _git_probe(repo: Path, *args: str) -> bool:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=10,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


REPOINT_HINT = ("history rewritten (squash-merge, rebase)? re-point the "
                "record with spec-build's `tick.py <spec-dir> --redeliver "
                "<new-sha>`")


def lifecycle_integrity_problems(task: str, repo: Path) -> list[str]:
    """Validate recorded lifecycle SHAs against the actual git repository."""
    values = lifecycle_shas(task)
    git_ok = _git_probe(repo, "rev-parse", "--git-dir")
    problems: list[str] = []
    for label, value in values.items():
        if value is None:
            continue
        if value == "-":
            if git_ok:
                problems.append(
                    f"{label}: explicit non-git dash recorded inside a git repo"
                )
            continue
        if not git_ok:
            problems.append(f"{label}: SHA {value!r} recorded in a non-git repo")
            continue
        if not _git_probe(repo, "cat-file", "-e", f"{value}^{{commit}}"):
            problems.append(
                f"{label}: commit {value!r} not found — {REPOINT_HINT}")
            continue
        if not _git_probe(repo, "merge-base", "--is-ancestor", value, "HEAD"):
            problems.append(
                f"{label}: commit {value!r} is not an ancestor of HEAD — "
                f"{REPOINT_HINT}")
    return problems


def type_problems(text: str, doc: str) -> list[str]:
    word = spec_type(text)
    if word in WORK_TYPES:
        return []
    return [f"type: {doc} says `**Type**: {word}` — the work types are "
            + " | ".join(WORK_TYPES)]


def heading_body(text: str, heading: str) -> str | None:
    """The body under an exact heading, up to the next heading of its
    level or higher, HTML comments removed; None when the heading is
    absent."""
    level = len(heading) - len(heading.lstrip("#"))
    m = re.search(rf"^{re.escape(heading)}[ \t]*$", text, re.M)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(rf"^#{{1,{level}}} ", rest, re.M)
    body = rest[:nxt.start()] if nxt else rest
    return re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()


def coverage_shape_problems(texts: dict[str, str], nfr_defs: dict[str, str],
                            tc_blocks: dict[str, str]) -> list[str]:
    """What a full-tier docset must cover beyond the ID graph: every
    quality family triaged, the interface and rollout sections present,
    and — for a behavior-preserving work type — a preservation TC."""
    problems: list[str] = []
    for family in NFR_FAMILIES:
        word = re.compile(rf"\b{family}\b", re.I)
        if not any(word.search(line) for line in nfr_defs.values()):
            problems.append(
                f"quality: {family} is not triaged — add an NFR for it, or "
                f"`- **NFR-###**: {family} — not applicable: <reason>`")
    for doc, heading in REQUIRED_SECTIONS:
        if not heading_body(texts[doc], heading):
            problems.append(
                f"structure: {doc} has no `{heading}` section, or it is "
                "empty — write it, or `none — <reason>`")
    work_type = spec_type(texts["spec.md"])
    if work_type in PRESERVING_TYPES and not any(
            PRESERVES_LINE.search(re.sub(r"<!--.*?-->", "", block, flags=re.S))
            for block in tc_blocks.values()):
        problems.append(
            f"type: a {work_type} spec needs a behavior-preservation test "
            "case — a TC carrying a `- **Preserves**: <existing behavior>` "
            "line whose pass condition is green before the change")
    return problems


def by_approval(problems: list[str], status: str | None,
                fails: list[str], warns: list[str]) -> None:
    """Coverage-shape problems fail a draft and only warn once the
    contract is frozen: repairing one edits a frozen file, which is a
    re-approval, never a mid-execution chore."""
    if status in APPROVED_STATUSES:
        warns += [f"{p} (frozen contract — repair at the next re-approval)"
                  for p in problems]
    else:
        fails += problems


def _read(path: Path) -> str:
    try:
        return INVISIBLE.sub(
            "", path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""


def open_touches(spec_dir: Path, spec_text: str) -> list[str]:
    """The touches of a spec's unfinished tasks — its pending footprint."""
    task_text = (tiny_task_text(spec_text) or ""
                 if spec_tier(spec_text) == "tiny"
                 else _read(spec_dir / "task.md"))
    return sorted({touch for e in task_entries(task_text)
                   if not e.done and not e.struck
                   for touch in task_touches(e)})


def cross_spec_findings(spec_dir: Path,
                        spec_text: str) -> tuple[list[str], list[str]]:
    """(fails, warns) from the specs beside this one: a `**Depends on**`
    name that is no spec fails; a dependency not yet approved warns; so
    does an in-flight spec whose pending touches overlap this spec's,
    unless one of the pair already depends on the other."""
    fails: list[str] = []
    warns: list[str] = []
    try:
        siblings = {index.spec_name(p): p
                    for p in index.all_spec_dirs(index.specs_root(spec_dir))
                    if p.resolve() != spec_dir.resolve()}
    except OSError:
        siblings = {}
    depends = spec_depends(spec_text)
    for dep in depends:
        target = siblings.get(dep)
        if target is None:
            fails.append(
                f"depends: `{dep}` on the `**Depends on**` header is not a "
                "spec under specs/ or specs/archive/")
            continue
        dep_status = spec_status(_read(target / "spec.md")) or "draft"
        if dep_status not in APPROVED_STATUSES:
            warns.append(
                f"depends: {dep} is still {dep_status} — this spec builds "
                "on a contract that is not approved yet")
    if spec_status(spec_text) == "done":
        return fails, warns
    mine = open_touches(spec_dir, spec_text)
    for name, other in sorted(siblings.items()) if mine else ():
        if other.parent.name == index.ARCHIVE_DIR or name in depends:
            continue
        other_text = _read(other / "spec.md")
        other_status = spec_status(other_text)
        if (other_status not in IN_FLIGHT_STATUSES
                or spec_dir.name in spec_depends(other_text)):
            continue
        theirs = open_touches(other, other_text)
        hit = next((a for a in mine for b in theirs if paths_overlap(a, b)),
                   None)
        if hit is not None:
            warns.append(
                f"overlap: in-flight spec {name} ({other_status}) also "
                f"touches `{hit}` — order the two with a `**Depends on**` "
                "header, or re-survey once it lands")
    return fails, warns


def index_warnings(spec_dir: Path) -> list[str]:
    """specs/INDEX.md's line for this spec vs a fresh render of it."""
    path = index.specs_root(spec_dir) / "INDEX.md"
    want = index.render_line(spec_dir)
    if not path.exists() or want is None:
        return []
    name = index.spec_name(spec_dir)
    have = index.committed_line(_read(path), name)
    fix = "run `index.py <spec-dir>`"
    if have is None:
        return [f"index: {name} not registered in specs/INDEX.md — {fix}"]
    if have.strip() != want:
        return [f"index: INDEX.md line for {name} is stale (spec.md says "
                f"`{want.split(' — ', 1)[1]}`) — {fix}"]
    return []


def approval_failures(spec_dir: Path, repo_root: Path,
                      status: str | None) -> list[str]:
    """An approved-or-later Status must be backed by the approval
    freeze, intact — at every tier."""
    if status not in ("approved", "active", "done"):
        return []
    if not (spec_dir / "approvals" / "approval.md").exists():
        return [f"evidence: Status {status} but no approvals/approval.md "
                "freeze — never approved: set Status back to draft; "
                "approved before the freeze existed: re-approve once — "
                f"{freeze.approval_steps(spec_dir)}"]
    return [f"evidence: {problem}"
            for problem in freeze.verify(spec_dir, repo_root)]


def tiny_check(spec_dir: Path, repo_root: Path) -> int:
    """The ONE-FILE contract gate: spec.md carries the task list
    in § Tasks; no other docset file exists or is required. Checks the
    in-file contract only — placeholders, open clarify markers, task
    grammar (IDs, FR citations, unique, Accept lines on code tasks),
    tick proof notes, the approval freeze — then reports like the full
    checker. The gates that need the seven-file surface (traceability
    to TCs, burndown table) do not exist at this tier by design; the
    human proof pass still binds."""
    import specstate
    fails: list[str] = []
    warns: list[str] = []
    text = (spec_dir / "spec.md").read_text(encoding="utf-8",
                                            errors="replace")
    clean = INVISIBLE.sub("", text)
    if not clean.strip() or PLACEHOLDER.search(clean):
        fails.append("spec.md is unfilled or carries template placeholders")

    if "NEEDS CLARIFICATION" in clean:
        fails.append("open NEEDS CLARIFICATION markers in spec.md")

    section = specstate.tasks_section(clean)
    if section is None:
        fails.append("spec.md has no `## Tasks` section — the tier's "
                     "status holder (Tier: tiny)")
    else:
        wrapped = specstate.tiny_task_text(clean) or ""
        entries = specstate.task_entries(wrapped)
        if not entries:
            fails.append("§ Tasks has no task entries")
        seen: set[str] = set()
        frs = set(re.findall(r"\bFR-\d{3}\b", clean))
        for e in entries:
            if e.id is None:
                fails.append(f"task without a bare T### id: {e.first_line}")
            elif e.id in seen:
                fails.append(f"duplicate task id {e.id}")
            else:
                seen.add(e.id)
            if e.id and e.done and "done 20" not in e.block:
                fails.append(f"{e.id} ticked without a `done <date> — proof` "
                             "sub-line")
            if e.id and not re.search(r"\((?:FR|NFR)-\d{3}\)", e.block):
                fails.append(f"{e.id} cites no FR/NFR id")
            if e.id and "Touches:" not in e.block:
                warns.append(f"{e.id} has no Touches: block (code tasks "
                             "need one)")
        for fr in frs:
            if fr not in wrapped:
                fails.append(f"{fr} defined but no task cites it")
        work_type = spec_type(clean)
        if work_type in PRESERVING_TYPES and not any(
                "Accept:" in e.block for e in entries):
            by_approval(
                [f"type: a {work_type} spec needs a task with an `Accept:` "
                 "command that is green before the change — the proof that "
                 "behavior is preserved"],
                specstate.spec_status(clean), fails, warns)

    if not re.search(r"^\*\*Status\*\*", clean, re.M):
        fails.append("spec.md has no Status header")
    fails += type_problems(clean, "spec.md")
    cross_fails, cross_warns = cross_spec_findings(spec_dir, clean)
    fails += cross_fails
    warns += cross_warns + index_warnings(spec_dir)
    fails += approval_failures(spec_dir, repo_root,
                               specstate.spec_status(clean))

    print(f"check: {spec_dir} (tier: tiny — one-file contract)")
    print(f"  {'PASS' if not fails else 'FAIL'} ({len(fails)} fail, "
          f"{len(warns)} warn)")
    for w in warns:
        print(f"  WARN  {w}")
    for f_ in fails:
        print(f"  FAIL  {f_}")
    from telemetry import record
    record(Path(__file__).resolve().parent.parent.name, "check_run", spec=spec_dir.name,
           fails=len(fails), warns=len(warns), frs=len(frs),
           tasks=len(entries) if section else 0)
    return 1 if fails else 0


def main(argv: list[str] | None = None) -> int:
    # argv is optional so a persistent process can call main() with args
    # instead of paying a fresh interpreter + import per invocation; the CLI
    # path (argv=None) is unchanged. graph.py's own probe still shells out
    # via subprocess for process isolation.
    if argv is None:
        argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    parsed = parse_args(argv)
    if parsed is None:
        print(__doc__)
        return 2
    spec_dir_s, repo_arg, do_fix, do_ids, survey_only, intent_only, constitution_only, do_checklist = parsed
    spec_dir = Path(spec_dir_s)
    if not spec_dir.is_dir():
        print(f"FAIL: {spec_dir} is not a directory")
        return 1
    # specs/<name>/ is two levels below the repo root.
    repo_root = Path(repo_arg) if repo_arg else spec_dir.parent.parent

    if survey_only:
        return survey_only_check(spec_dir, repo_root)
    if intent_only:
        return intent_only_check(spec_dir, repo_root)
    if constitution_only:
        return constitution_only_check(repo_root)

    spec_raw = (spec_dir / "spec.md")
    if spec_raw.exists():
        if spec_tier(spec_raw.read_text(encoding="utf-8",
                                        errors="replace")) == "tiny":
            return tiny_check(spec_dir, repo_root)

    fails: list[str] = []
    warns: list[str] = []
    notes: list[str] = []  # informational lines — visible, never warn/fail
    texts = {}

    # 1. contract files exist and are non-trivial; survey.md/research.md are
    # optional inputs (WARN not FAIL)
    for f in ALL_FILES:
        p = spec_dir / f
        t = p.read_text(encoding="utf-8") if p.exists() else ""
        t = INVISIBLE.sub("", t)
        texts[f] = t
        if not t:
            if f in CONTRACT_FILES:
                fails.append(f"missing/empty: {f}")
            elif f == "research.md":
                warns.append(
                    "missing: research.md (input — if the researcher was "
                    'deliberately gated off, create it reading "not applicable '
                    '— no open questions at Stage 0" to record the skip)'
                )
            else:
                warns.append("missing/empty: survey.md (input, optional)")
        elif f in CONTRACT_FILES and len(t) < 200:
            warns.append(f"suspiciously short (<200 chars): {f}")

    spec, task, test, tech = (
        texts["spec.md"], texts["task.md"], texts["test.md"], texts["tech-spec.md"]
    )

    if do_ids:
        print_next_ids(texts)
        return 0

    # 1a. intent.md — optional input beside survey.md/research.md, but
    # with FAIL teeth: absent → not checked, no warn (specs shaped without
    # an analyst pass must stay green); present → the --intent-only refusal
    # families run here too, less the baseline pair (notes off the gate).
    intent_path = spec_dir / "intent.md"
    if intent_path.exists():
        intent_text = INVISIBLE.sub(
            "", intent_path.read_text(encoding="utf-8", errors="replace"))
        delivered = _delivery_recorded(texts["task.md"], texts["spec.md"])
        intent_fails_, intent_notes = intent_failures(
            intent_text, repo_root, delivered, spec_dir.parent)
        notes.extend(intent_notes)
        fails.extend(intent_fails_)

    # 1b. repo-level baselines, checked once against the repo root (both
    # are cross-spec, not members of any one spec folder): the shared
    # constitution — scaffold.sh creates it on the repo's first scaffold —
    # and the surveyor's context baseline. WARN-only: process inputs, not
    # per-spec contract files.
    constitution_filled, constitution_msg = constitution_status(repo_root)
    if not constitution_filled:
        if other_specs_exist(repo_root, spec_dir):
            fails.append(
                f"constitution: {constitution_msg} — other specs already "
                f"exist, so the first-spec grace is over: {CONSTITUTION_STEP}")
        else:
            warns.append(
                f"constitution: {constitution_msg} — {CONSTITUTION_STEP}")
    if not (repo_root / "specs" / "context").is_dir():
        warns.append(
            "no specs/context/ baseline (surveyor writes it "
            "on the repo's first spec)"
        )

    # 2. ID graph
    frs = defined(spec, "FR")
    nfrs = defined(spec, "NFR")
    acs = defined(spec, "AC")
    uss = defined(spec, "US")
    tcs = defined(test, "TC")
    ds = defined(tech, "D")
    # an NFR definition with its wrapped continuation lines: the family
    # names and the "not applicable" verdict may sit past the first line
    nfr_defs: dict[str, str] = {}
    open_nfr = None
    for line in spec.splitlines():
        m = DEFINITIONS["NFR"].match(line.strip())
        if m:
            open_nfr = m.group(1)
            nfr_defs[open_nfr] = line
        elif open_nfr and line[:1] in (" ", "\t") and line.strip():
            nfr_defs[open_nfr] += " " + line.strip()
        else:
            open_nfr = None

    # EARS shape: every FR/NFR definition line must say "shall" (the spec
    # template's SHALL-statement convention). WARN — a missing "shall" is
    # a wording defect the auditor flags for repair, not ID corruption.
    for line in spec.splitlines():
        m = (DEFINITIONS["FR"].match(line.strip())
             or DEFINITIONS["NFR"].match(line.strip()))
        definition = nfr_defs.get(m.group(1), line).lower() if m else ""
        if m and ("shall" not in definition
                  and "not applicable" not in definition):
            warns.append(f"{m.group(1)}: not EARS-shaped (no 'shall')")

    # Task entries: "- [ ]"-anchored blocks (with wrapped continuation
    # lines) inside "## Phase ..." sections only — Conventions examples
    # don't count. specstate.task_entries is the shared parser; the
    # bookkeeping below is this file's per-check view of the same entries.
    entries = task_entries(task)
    ph_total, ph_done = phase_counts(entries)
    task_phase: dict[str, int] = {}
    # phase -> task id -> intended touches. Touches are read from the full
    # entry (including a structured `Touches:` block) and compared using
    # directory/glob-aware overlap, not exact string equality alone.
    par_files: dict[int, dict[str, list[str]]] = {}
    for e in entries:
        if e.phase is None:
            continue
        if e.id:
            task_phase[e.id] = e.phase
            if e.parallel:
                touches = task_touches(e)
                if not touches:
                    warns.append(
                        f"parallel: {e.id} marks [P] but names no intended "
                        "file/directory/glob — add a Touches block"
                    )
                par_files.setdefault(e.phase, {})[e.id] = touches
    in_progress = sum(1 for e in entries if e.claimed)
    tsks = {m for e in entries for m in re.findall(r"\bT\d{3}\b", e.block)}
    done = sum(1 for e in entries if e.done)
    todo = sum(1 for e in entries if e.first_line.startswith("- [ ]"))
    total_tasks = done + todo

    if do_checklist:
        checklist_p = spec_dir / "checklist.md"
        checklist_p.write_text(
            build_checklist(spec_dir.name, spec, entries), encoding="utf-8"
        )
        print(f"wrote {checklist_p}")

    # TC blocks in test.md, split the same way task.md's entries are — each
    # "## TC-### ..." section's own body. Existence checks below search
    # WITHIN these blocks (and within task entries, above), never raw
    # whole-file substrings: a decoy comment or a stale coverage-matrix row
    # citing an ID must not be able to stand in for a real reference.
    # Split on H2 OR H3 headings: some real specs nest "### TC-###" cases
    # under a "## US#" grouping header rather than the flat template's
    # top-level "## TC-###" — either shape isolates each TC's own content
    # up to the next heading of either level.
    tc_blocks: dict[str, str] = {}
    for sec in re.split(r"^#{2,3} ", test, flags=re.M):
        m = re.match(r"(TC-\d{3})\b", sec)
        if m:
            tc_blocks[m.group(1)] = sec

    # D-### blocks in tech-spec.md, split the same way — each decision
    # heading's own body, so its structural-completeness check (below)
    # looks only at that decision's content.
    d_blocks: dict[str, str] = {}
    for sec in re.split(r"^### ", tech, flags=re.M):
        m = re.match(r"(D-\d{3})\b", sec)
        if m:
            d_blocks[m.group(1)] = sec

    # 2b. optional repair before the arithmetic check below sees the table
    if do_fix:
        task = fix_burndown(task, spec_dir / "task.md", ph_total, ph_done)
        texts["task.md"] = task

    for fr in sorted(frs):
        if not any(fr in e.block for e in entries):
            fails.append(f"traceability: {fr} has no task")
        if not any(fr in blk for blk in tc_blocks.values()):
            fails.append(f"traceability: {fr} has no test case")
    for nfr, definition in sorted(nfr_defs.items()):
        if "not applicable" in definition.lower():
            if not re.search(r"not applicable\s*[—:-]", definition, re.I):
                warns.append(f"traceability: {nfr} skips coverage without a reason")
            continue
        if not any(nfr in e.block for e in entries):
            fails.append(f"traceability: {nfr} has no task")
        if not any(nfr in blk for blk in tc_blocks.values()):
            fails.append(f"traceability: {nfr} has no test case")
    for t in sorted(tsks):
        entry = next((e.block for e in entries if re.search(rf"\b{t}\b", e.block)), "")
        if not re.search(r"\b(?:FR|NFR)-\d{3}\b", entry):
            fails.append(f"traceability: {t} cites no FR/NFR (scope creep?)")
    # Task-dependency dangling check: a "(after T###)" chain marker pointing
    # at a T-ID that doesn't exist — same pattern as the FR/AC/D dangling
    # checks below, for the one ID family those don't cover. WARN: a dangling
    # dependency is a real doc defect but does not corrupt status the way an
    # ungrounded FR/task does.
    for ref in sorted(set(re.findall(r"\(after\s+(T\d{3})\)", task)) - tsks):
        warns.append(f"dangling: (after {ref}) references a task that doesn't exist")
    # Cross-phase chains: a task depending on a task in a LATER phase can
    # never be scheduled — phase-order preconditions in mechanical form.
    for e in entries:
        if not e.id or e.id not in task_phase:
            continue
        for ref in e.after:
            if ref in task_phase and task_phase[ref] > task_phase[e.id]:
                fails.append(
                    f"dependency: {e.id} (phase {task_phase[e.id]}) "
                    f"chains after {ref} in a later phase ({task_phase[ref]})"
                )
    # Parallel-wave collision: two [P] tasks whose exact paths, directories,
    # or glob prefixes overlap. WARN keeps legacy prose adjudicable, but the
    # overlap computation itself is conservative rather than exact-string.
    for n, files in sorted(par_files.items()):
        ids = sorted(files)
        for i, left in enumerate(ids):
            for right in ids[i + 1:]:
                overlap = next(
                    (x for x in files[left] for y in files[right]
                     if paths_overlap(x, y)),
                    None,
                )
                if overlap is not None:
                    warns.append(
                        f"parallel: {left}, {right} (phase {n}) overlap at "
                        f"`{overlap}` — chain them or prove disjoint touches"
                    )
    for ref in sorted(set(re.findall(r"\b(?:FR|NFR)-\d{3}", task + test)) - frs - nfrs):
        fails.append(f"dangling: {ref} referenced but not defined in spec.md")
    for ref in sorted(set(re.findall(r"AC\d+", test)) - acs):
        fails.append(f"dangling: {ref} referenced but not defined in spec.md")
    for ref in sorted(set(re.findall(r"D-\d{3}", task + spec)) - ds):
        fails.append(f"dangling: {ref} referenced but not defined in tech-spec.md")
    # D-### structural completeness: a heading alone isn't a decision — the
    # template's shape is Context/Decision/Consequences, bulleted or (as
    # real specs also do it) written as bold-labelled prose paragraphs.
    # Match the label itself, not a specific bullet syntax: "**Context**:"
    # is often a paragraph opener, not a "- **Context**" list item. WARN, not FAIL: a stub is a real defect but not an
    # ID-graph corruption.
    for d in sorted(ds):
        blk = d_blocks.get(d, "")
        missing = [
            label for label in ("Context", "Decision", "Consequences")
            if f"**{label}**" not in blk
        ]
        if missing:
            warns.append(f"{d}: missing {'/'.join(missing)} label(s) — stub decision? (every D-### opens with - **Context** / **Decision** / **Consequences** labels, and names literal file paths when it touches files)")
    for tc in sorted(tcs):
        if not re.search(r"\b(?:FR|NFR)-\d{3}\b", tc_blocks.get(tc, "")):
            fails.append(f"traceability: {tc} traces to no FR/NFR")
    # Coverage-matrix ↔ TC consistency: a matrix row's own claim (this FR is
    # covered by this TC) must be backed by that TC's own content — a stale
    # row citing a TC that no longer exists, or one whose Traces-to line names
    # a different FR, is caught here.
    for fr_m, tc_col in re.findall(
            r"^\|\s*((?:FR|NFR)-\d{3})\s*\|([^|]*)\|[^|]*\|\s*$", test, re.M):
        for tc_ref in re.findall(r"TC-\d{3}", tc_col):
            if tc_ref not in tc_blocks:
                warns.append(f"coverage matrix: {fr_m} cites {tc_ref}, which doesn't exist")
            elif fr_m not in tc_blocks[tc_ref]:
                warns.append(
                    f"coverage matrix: {fr_m} → {tc_ref}, but {tc_ref}'s own "
                    f"content doesn't mention {fr_m}"
                )
    # US traceability is WARN-only: promoting it to FAIL would break specs
    # that have untraced stories.
    for ref in sorted(set(re.findall(r"\bUS\d{1,2}\b", test + task)) - uss):
        warns.append(f"dangling: {ref} referenced but not defined in spec.md")
    for us in sorted(uss):
        if not any(us in blk for blk in tc_blocks.values()):
            warns.append(f"traceability: {us} has no test case")
    # AC coverage is FAIL: every acceptance criterion needs a TC mapping.
    # \b over a bare `in`: AC1 must not read as mapped by a block naming AC10.
    for ac in sorted(acs):
        if not any(re.search(rf"\b{ac}\b", blk) for blk in tc_blocks.values()):
            fails.append(f"traceability: {ac} has no test case")
    # FR/NFR → milestone coverage: planner's "every requirement in exactly one
    # milestone" rule, enforced against the ## Milestones table rows.
    # No milestone is FAIL (same severity as FR-has-no-task); membership
    # in multiple rows is WARN (the planner says exactly one, but a FR
    # split across two milestones is a planning conversation, not an
    # ID-graph corruption).
    ms_rows: list[str] = []
    for sec in re.split(r"^## ", texts["plan.md"], flags=re.M):
        if sec.split("\n", 1)[0].strip().lower().startswith("milestone"):
            ms_rows = [
                l for l in sec.splitlines()
                if l.startswith("|") and re.search(r"\b(?:FR|NFR)-\d{3}\b", l)
            ]
            break
    if ms_rows:
        req_ms: dict[str, int] = {}
        for line in ms_rows:
            for req in re.findall(r"\b(?:FR|NFR)-\d{3}\b", line):
                req_ms[req] = req_ms.get(req, 0) + 1
        requirements = set(frs) | {
            nfr for nfr, line in nfr_defs.items()
            if "not applicable" not in line.lower()
        }
        for req in sorted(requirements):
            if req not in req_ms:
                fails.append(f"traceability: {req} has no milestone in plan.md")
            elif req_ms[req] > 1:
                warns.append(f"plan: {req} appears in {req_ms[req]} milestone rows (exactly one expected)")
    else:
        warns.append("plan: no ## Milestones table rows with FR/NFR-### found")
    # TC structural shape: presence of the four labels only — vacuousness
    # is the auditor agent's job, missing scaffolding is mechanical.
    for tc in sorted(tcs):
        blk = tc_blocks.get(tc, "")
        missing = [w for w in ("Given", "When", "Then", "Pass condition") if w not in blk]
        if missing:
            warns.append(f"{tc}: missing {'/'.join(missing)} label(s) — incomplete case?")
    # Stage gates — skipped steps become mechanical failures: progress
    # requires an approved spec, and clarifications are resolved before
    # tasks exist.
    status = spec_status(spec)
    fails += type_problems(spec, "spec.md")
    if spec_type(spec) == "hotfix":
        warns.append("type: hotfix is the tiny-tier bugfix — a full-tier "
                     "docset is a `**Type**: bugfix`")
    by_approval(coverage_shape_problems(texts, nfr_defs, tc_blocks),
                status, fails, warns)
    cross_fails, cross_warns = cross_spec_findings(spec_dir, spec)
    fails += cross_fails
    warns += cross_warns + index_warnings(spec_dir)
    for problem in lifecycle_integrity_problems(task, repo_root):
        fails.append(f"evidence: {problem}")
    fails += approval_failures(spec_dir, repo_root, status)
    if status == "draft" and (done or in_progress):
        fails.append(
            f"gate: implementation progress ({done} ticked, {in_progress} in-progress) "
            "while spec.md Status is draft — the approval gate was skipped"
        )
    if total_tasks and re.search(r"\[NEEDS CLARIFICATION", spec):
        fails.append(
            "clarify: spec.md still holds NEEDS CLARIFICATION markers but task.md "
            "has tasks — answers are due before Stage 3"
        )
    # spec.md Status ↔ task.md reality. WARN: the state
    # machine is real (Resuming depends on it) but delivery may
    # legitimately sit between "all ticked" and "Status: done", and
    # "approved" is indistinguishable from draft by task state alone —
    # approved-with-no-progress stays silent by design. `approved` also
    # covers execution: the kit never writes `active` (task.md holds the
    # progress), so an approved spec with work in flight is consistent.
    if status in ("draft", "approved", "active", "done") and total_tasks:
        expected = "done" if done == total_tasks else ("active" if done or in_progress else "draft")
        if status != expected and not (status == "approved" and expected in ("draft", "active")):
            warns.append(
                f"status: spec.md says {status}, task.md looks {expected} "
                f"({done}/{total_tasks} ticked, {in_progress} in-progress)"
            )

    # 3. burndown arithmetic vs actual entries, via the shared burndown_sums
    # scan (burndown_rewrite repairs from the same phase_counts — validation
    # and repair must never disagree on what counts as a data row vs the Σ row).
    sums = burndown_sums(task)
    if sums is not None:
        bd_total, bd_done, sum_row = sums
        if bd_total != total_tasks:
            fails.append(f"burndown: table totals {bd_total} != actual tasks {total_tasks}")
        if bd_done != done:
            fails.append(f"burndown: table done {bd_done} != actual ticked {done}")
        if sum_row is not None and sum_row != (bd_total, bd_done):
            warns.append(
                f"burndown: Σ row {sum_row[0]}/{sum_row[1]} disagrees with "
                f"row sums {bd_total}/{bd_done} (run --fix-burndown)"
            )
    else:
        warns.append("burndown: no table found in task.md")

    # 4. checkbox hygiene: status lives ONLY in task.md
    for f in ("spec.md", "plan.md", "tech-spec.md", "test.md"):
        if re.search(r"^\s*- \[[ x]\]", texts[f], re.M):
            fails.append(f"status bleed: checkboxes in {f} (only task.md holds status)")

    # 5. open NEEDS CLARIFICATION markers
    for f in ALL_FILES:
        n = len(re.findall(r"\[NEEDS CLARIFICATION", texts[f]))
        if n:
            warns.append(f"{f}: {n} NEEDS CLARIFICATION marker(s) still open")

    # 6. leftover template placeholders and vague plan phrases. Code spans
    # and HTML comments are stripped FIRST (in Python, not in the
    # pattern): real content like `<schema>_staging` lives inside
    # backticks and must not be flagged.
    for f in CONTRACT_FILES:
        phit: list[str] = _placeholder_hits(texts[f])
        vhit: list[str] = []
        for lineno, line in enumerate(texts[f].splitlines(), start=1):
            s = HTML_COMMENT.sub(
                " ", QUOTE_SPAN.sub(" ", CODE_SPAN.sub(" ", line)))
            if VAGUE.search(s):
                vhit.append(f"@{lineno}")
        if phit:
            detail = ", ".join(phit[:5]) + ("…" if len(phit) > 5 else "")
            warns.append(f"{f}: {len(phit)} line(s) with unfilled placeholder(s) (<name>…, YYYY-MM-DD): {detail}")
        if vhit:
            warns.append(
                f"{f}: {len(vhit)} vague plan phrase(s) (TBD, handle edge cases, as appropriate…): {', '.join(vhit[:5])}{'…' if len(vhit) > 5 else ''}"
            )

    # 7. citation reality (heuristic): backtick spans in tech-spec.md that
    # look like repo-rooted file paths (any known source extension — not
    # just .py) must exist under the repo root. specs/<name>/ → repo root
    # is two levels up (overridable: --repo).
    citations = set()
    for s in (m.strip() for m in re.findall(r"`([^`\n]+)`", tech)):
        if "/" not in s or re.search(r"\s", s):
            continue
        if "://" in s or "../" in s or any(c in s for c in NON_PATH):
            continue
        p = s[2:] if s.startswith("./") else s
        p = re.sub(r":\d+(?::\d+)?$", "", p)  # strip Foo.kt:42 / Foo.kt:42:7
        base = p.rsplit("/", 1)[-1]
        if "." not in base or base.rsplit(".", 1)[1].lower() not in CODE_EXT:
            continue
        citations.add(p)
    for span in sorted(citations):
        if (repo_root / span).exists():
            continue
        first = span.split("/", 1)[0]
        if first in SRC_ROOTS or (repo_root / first).is_dir():
            warns.append(f"citation path not found: {span}")

    # 8. survey staleness: baseline hash vs the repo's HEAD (the header
    # parse itself is specstate.survey_baseline; the diagnosis branches
    # below only decide how to word an unusable header)
    survey = texts["survey.md"]
    bl = survey_baseline(survey)
    if bl is None:
        if not survey:
            pass  # already reported by check 1 (missing/empty: survey.md)
        elif re.search(r"Baseline\*\*[^\n]*<[^>\n]*>", survey):
            warns.append(
                "survey.md baseline is an unfilled placeholder "
                "(<version @ commit>) — fill it from the survey run"
            )
        elif "Baseline" in survey:
            warns.append(
                "survey.md baseline header has no commit hash "
                "(expected `**Baseline**: <version> @ <sha>`)"
            )
        else:
            warns.append("survey.md has no baseline header")
    else:
        sha = bl[1]
        repo_hit, head, saw_git_dir = _baseline_head_probe(repo_root, sha)
        if repo_hit is None and not saw_git_dir:
            # A baseline that cannot be compared is not a fresh baseline — the
            # skip must be visible, not silent.
            notes.append("staleness: SKIPPED (not a git repo)")
        elif repo_hit is None:
            # A subtler skip: .git dirs exist, but none
            # of the candidates actually contains the baseline commit, so
            # the comparison still cannot run — say so instead of passing
            # silently. Informational note, never a warn or fail.
            notes.append(
                "staleness: SKIPPED — no candidate repo contains the baseline commit"
            )
        if repo_hit is not None and head and head != sha.lower() and not (
            head.startswith(sha.lower()) or sha.lower().startswith(head)
        ):
            if _code_changed_since(repo_hit, sha, spec_dir.parent):
                where = (f" (repo: {repo_hit.name})"
                         if repo_hit != repo_root else "")
                warns.append(
                    f"survey baseline {sha}, HEAD {head}{where} — "
                    "re-survey before trusting statuses"
                )
            else:
                notes.append(
                    "staleness: fresh — only the kit's doc trees (specs/, "
                    f"brainstorms/) changed since baseline {sha} (HEAD {head})"
                )

    # 9. survey.md evidence reality: every `file:symbol:line` citation must
    # name a real file and a real def/class in it. FAIL when the symbol
    # doesn't exist anywhere in the file — that's a fabricated citation, the
    # exact defect class this check exists to catch, and confirming it is
    # cheap once the path itself is known to exist. WARN when the symbol is
    # real but at a different line — ordinary drift since the survey was
    # written (already flagged in aggregate by check 8's baseline-staleness
    # check) is a softer, more forgivable defect than an invented name.
    for path_s, symbol, line_s in sorted(set(EVIDENCE_CITATION.findall(survey))):
        target = repo_root / path_s
        if not target.exists():
            warns.append(f"survey evidence: file not found: {path_s} (cited for {symbol})")
            continue
        try:
            target_text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        def_lines = _symbol_def_lines(target_text, symbol)
        if not def_lines:
            fails.append(
                f"survey evidence: {symbol!r} not found (def/class) in {path_s} "
                f"(cited at line {line_s})"
            )
        elif int(line_s) not in def_lines:
            warns.append(
                f"survey evidence: {path_s}:{symbol} cited at line {line_s}, "
                f"actually at {def_lines} — re-survey or fix the citation"
            )

    # 10. verify-command path reality: a pytest invocation's path/glob
    # arguments (across every contract/input file, not just survey.md —
    # tech-spec.md/plan.md/test.md/task.md all copy verify commands forward)
    # must match at least one real file. WARN: a glob matching zero files
    # today could legitimately be a not-yet-written test, but silently
    # matching nothing hides a wrong path.
    seen_tokens: set[tuple[str, str]] = set()

    def _check_pytest_cmd(f: str, cmd: str) -> None:
        for tok in cmd.split():
            tok_clean = tok.strip("'\"")
            if not tok_clean.endswith(".py") or (f, tok_clean) in seen_tokens:
                continue
            seen_tokens.add((f, tok_clean))
            if not _pytest_target_exists(repo_root, tok_clean):
                warns.append(
                    f"{f}: verify command path matches no file: "
                    f"`{tok_clean}` (in `{cmd}`)"
                )

    for f in ALL_FILES:
        for m in PYTEST_CMD.finditer(texts[f]):
            _check_pytest_cmd(f, m.group(1))
    for m in SURVEY_VERIFY_LINE.finditer(survey):
        if "pytest" in m.group(1):
            _check_pytest_cmd("survey.md", m.group(1).strip())

    print(f"check: {spec_dir}")
    print(
        f"  IDs: {len(frs)} FR · {len(nfrs)} NFR · {len(acs)} AC · {len(uss)} US · "
        f"{len(tsks)} T · {len(tcs)} TC · {len(ds)} D"
    )
    print(f"  tasks: {total_tasks} total · {done} done · {todo} open")
    for n in notes:
        print(f"  {n}")
    for w in warns:
        print(f"  WARN  {w}")
    for f_ in fails:
        print(f"  FAIL  {f_}")
    print(f"  {'PASS' if not fails else 'FAIL'} ({len(fails)} fail, {len(warns)} warn)")
    from telemetry import record  # fire-and-forget local telemetry
    record(Path(__file__).resolve().parent.parent.name, "check_run", spec=spec_dir.name,
           fails=len(fails), warns=len(warns),
           frs=len(frs), tasks=total_tasks)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
