#!/usr/bin/env python3
"""Mechanical Phase-C checks for a spec folder under specs/<name>/.

Verifies what a script can: file presence (5 contract files + survey.md/
research.md as optional inputs), ID traceability graph (FR/AC/US/TC/D),
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
zero matches), parallel-file overlap between [P] tasks, TC structural
shape, spec-status ↔ task/INDEX consistency, EARS-shaped FRs (every FR
line says 'shall'), constitution presence, context-baseline presence, and
stage gating (progress requires Status ≥ approved; NEEDS CLARIFICATION
resolved before tasks exist; before-audit recorded once implementation
starts). Test quality itself stays a human/LLM check.
--fix-burndown repairs the burndown table from the actual task entries
before checking; --next-ids prints the next free ID per family
(append-scope helper) and exits; --survey-only runs just the evidence-
reality and verify-command checks against survey.md alone (the other four
contract files need not exist yet) — the surveyor agent's own self-check,
meant to be run right after writing survey.md and before returning its
digest, so a bad survey fails here instead of flowing into tech/plan/qa.
--constitution runs only the repo-level specs/CONSTITUTION.md presence/fill
check and exits — a scriptable form of before-audit gate 6's presence half,
usable standalone (no spec dir contract files needed) as a pre-flight or CI
hook; the full check (no flag) also runs this check inline and escalates it
from WARN to FAIL once a second spec exists in the repo, closing the gap
where a later spec silently skips the gate scaffold.sh only auto-creates on
the *first* one. --checklist additionally writes specs/<name>/checklist.md
— a plain, human-tickable FR/AC summary generated from spec.md + task.md
(regenerate-only, never hand-edited; task.md stays the only status holder).

Usage: check.py <spec-dir> [--repo <path>] [--fix-burndown] [--next-ids] [--checklist]
       check.py <spec-dir> [--repo <path>] --survey-only
       check.py <spec-dir> [--repo <path>] --constitution
       check.py -h | --help        (prints this text, exit 0)
       e.g. check.py specs/postgres-backend --repo ../.. --fix-burndown
       e.g. check.py specs/postgres-backend --repo ../.. --survey-only
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
    TaskEntry,
    before_audit_state,
    defined_ids,
    next_ids,
    spec_status,
    survey_baseline,
    task_entries,
)

CONTRACT_FILES = ["spec.md", "plan.md", "tech-spec.md", "task.md", "test.md"]
# Stage-1 inputs: created by scaffold.sh, optional (WARN not FAIL) here.
INPUT_FILES = ["survey.md", "research.md"]
ALL_FILES = CONTRACT_FILES + INPUT_FILES

# Zero-width/invisible/bidi-control characters. A live adversarial test
# showed a zero-width space inserted between an ID's digits and its closing
# `**` (e.g. "FR-001" + ZWSP + "**") silently breaks the DEFINITIONS regex,
# making a real ID invisible to the ID graph — it fails safe (spurious FAIL,
# not a bypass) but is real corruption from a stray copy-paste. Stripped
# once, at file-read time, so every regex downstream (definitions,
# references, traceability) sees clean text uniformly. Escapes only —
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
# placeholder); the reviewer agent judges the real thing.
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
# grep/read output"). A live incident showed the surveyor writing plausible
# but nonexistent symbol names and off-by-hundreds line numbers for 9 of 13
# citations in one survey — nothing mechanically caught it before this.
EVIDENCE_CITATION = re.compile(r"([\w./-]+\.\w+):([A-Za-z_]\w*):(\d+)\b")

# A def/class introducing SYMBOL, any indentation, optional async/decorators
# handled by just matching the def/class line itself (multi-line signatures
# still start on this line).
def _symbol_def_lines(text: str, symbol: str) -> list[int]:
    # [ \t]* not \s* for the indent: \s matches newlines too, so a blank
    # line (or two) directly above the def/class let it eat backwards past
    # ^ and skew every match's line count by however many blank lines
    # preceded it — caught by a live off-by-2 on every citation in a real
    # survey.md, all landing on defs with exactly one blank line above them.
    pat = re.compile(rf"^[ \t]*(?:async[ \t]+def|def|class)[ \t]+{re.escape(symbol)}\b", re.M)
    return [text.count("\n", 0, m.start()) + 1 for m in pat.finditer(text)]


# verify:/Pass-condition commands that shell out to pytest with a path or
# glob argument — the other half of the same incident: a wrong path
# (tests/unit/test_contribution_suggest_graph.py for the real
# tests/test_contribution_suggest_graph.py) matches zero files and pytest
# silently reports nothing to run, instead of failing loudly.
PYTEST_CMD = re.compile(r"`([^`\n]*\bpytest\b[^`\n]*)`")
# survey.md's own `verify:` lines sit inside the item list's ``` fence, not
# wrapped in single backticks like tech-spec.md/plan.md/test.md — a plain
# PYTEST_CMD scan silently skips them entirely, which is exactly the file a
# wrong test path originates in. Matched separately, backticks optional.
SURVEY_VERIFY_LINE = re.compile(r"^\s*verify:\s*(.+)$", re.M)


def _pytest_target_exists(repo_root: Path, tok: str) -> bool:
    """True if tok (a literal path or glob) resolves under repo_root OR
    under one of its immediate subdirectories. The fallback matters for a
    multi-repo workspace (specs/<name>/ documenting one component repo
    among several siblings, per this workspace's own CLAUDE.md) where
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
        elif (root / tok).exists():
            return True
    return False


def bd_label(cell: str) -> tuple[str, int | None]:
    """Classify a burndown row label: ('sum'|'data'|'skip', phase or None).

    Shared by burndown_sums and burndown_rewrite so validation and repair
    can never drift apart on what counts as a data row (that drift was the
    actual root cause of "Phase 1" rows escaping both).
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
) -> tuple[str, str | None, bool, bool, bool, bool, bool] | None:
    """Return (spec_dir, repo_override, fix_burndown, next_ids, survey_only,
    constitution_only, checklist) or None."""
    fix = "--fix-burndown" in argv
    ids = "--next-ids" in argv
    survey_only = "--survey-only" in argv
    constitution_only = "--constitution" in argv
    checklist = "--checklist" in argv
    repo = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in (
            "--fix-burndown", "--next-ids", "--survey-only",
            "--constitution", "--checklist",
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
    return rest[0], repo, fix, ids, survey_only, constitution_only, checklist


def survey_only_check(spec_dir: Path, repo_root: Path) -> int:
    """Check just survey.md's own evidence citations and verify-command
    paths — the two checks a surveyor agent can and should run on itself
    right after writing survey.md, before returning its digest. Deliberately
    skips everything that needs the other four contract files (they don't
    exist yet at Stage 1) so this catches a bad survey BEFORE tech/plan/qa
    build on it, rather than only at Stage 4's full check.py — the gap that
    let a fabricated survey.md flow into four downstream docs undetected in
    a real incident.
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
    repo's first spec, so scaffold.sh's auto-create on first scaffold no
    longer explains a missing constitution."""
    specs_root = repo_root / "specs"
    if not specs_root.is_dir():
        return False
    this = spec_dir.resolve()
    for p in specs_root.iterdir():
        if p.is_dir() and p.name not in ("context", "archive") and p.resolve() != this:
            return True
    return False


def constitution_only_check(repo_root: Path) -> int:
    """Standalone --constitution mode: a scriptable pre-flight for before-
    audit gate 6's presence half (the semantic "every article complied with"
    half stays the orchestrator's judgment call) — usable without any of the
    five contract files existing, e.g. as a CI hook or a Stage-0 sanity check."""
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
    maintained status representation is exactly the drift class D-007
    (agents/_shared-protocol.md) already killed once for agent defs/briefs.
    FR checkboxes derive from task.md ticks (task.md stays the only status
    holder — this mirrors it, never adds a new one); ACs are listed plain
    since no independent AC-level status exists to mirror."""
    fr_ticked: dict[str, list[bool]] = {}
    for e in entries:
        for fr in re.findall(r"FR-\d{3}", e.block):
            fr_ticked.setdefault(fr, []).append(e.done)

    fr_text: dict[str, str] = {}
    ac_text: dict[str, str] = {}
    for line in spec.splitlines():
        s = line.strip()
        m = DEFINITIONS["FR"].match(s)
        if m:
            fr_text[m.group(1)] = s.lstrip("- ").strip()
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
        done = fr in fr_ticked and all(fr_ticked[fr])
        lines.append(f"- [{'x' if done else ' '}] {fr_text[fr]}")
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
    for family in ("FR", "AC", "US", "T", "TC", "D"):
        print(f"  {ids[family]}")


def main(argv: list[str] | None = None) -> int:
    # argv is optional so a persistent process (e.g. an orchestrator's
    # eval kernel, importing this module once and calling main() across
    # many recomputes) can pass args directly instead of paying a fresh
    # interpreter + import per invocation; the CLI path (argv=None) is
    # unchanged. graph.py's own internal probe still shells out via
    # subprocess (process isolation from this module's prints/argv), so
    # this is additive, not a replacement for that call site.
    if argv is None:
        argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    parsed = parse_args(argv)
    if parsed is None:
        print(__doc__)
        return 2
    spec_dir_s, repo_arg, do_fix, do_ids, survey_only, constitution_only, do_checklist = parsed
    spec_dir = Path(spec_dir_s)
    if not spec_dir.is_dir():
        print(f"FAIL: {spec_dir} is not a directory")
        return 1
    # specs/<name>/ is two levels below the repo root. (Historically
    # docs/specs/<name>/ was three levels; the parenthetical
    # "spec_dir.parent.parent" is now literally correct.)
    repo_root = Path(repo_arg) if repo_arg else spec_dir.parent.parent

    if survey_only:
        return survey_only_check(spec_dir, repo_root)
    if constitution_only:
        return constitution_only_check(repo_root)

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

    # 1b. repo-level baselines, checked once against the repo root (both
    # are cross-spec, not members of any one spec folder): the shared
    # constitution — scaffold.sh creates it on the repo's first scaffold —
    # and the surveyor's context baseline. WARN-only: process inputs, not
    # per-spec contract files.
    constitution_filled, constitution_msg = constitution_status(repo_root)
    if not constitution_filled:
        if other_specs_exist(repo_root, spec_dir):
            fails.append(f"constitution: {constitution_msg} — other specs already exist; the gate was skipped")
        else:
            warns.append(f"constitution: {constitution_msg}")
    if not (repo_root / "specs" / "context").is_dir():
        warns.append(
            "no specs/context/ baseline (surveyor writes it "
            "on the repo's first spec)"
        )

    # 2. ID graph
    frs = defined(spec, "FR")
    acs = defined(spec, "AC")
    uss = defined(spec, "US")
    tcs = defined(test, "TC")
    ds = defined(tech, "D")

    # EARS shape: every FR definition line must say "shall" (the spec
    # template's SHALL-statement convention). WARN — a missing "shall" is
    # a wording defect the reviewer fixes in place, not ID corruption.
    for line in spec.splitlines():
        m = DEFINITIONS["FR"].match(line.strip())
        if m and "shall" not in line.lower():
            warns.append(f"{m.group(1)}: not EARS-shaped (no 'shall')")

    # Task entries: "- [ ]"-anchored blocks (with wrapped continuation
    # lines) inside "## Phase ..." sections only — Conventions examples
    # don't count. specstate.task_entries is the shared parser; the
    # bookkeeping below is this file's per-check view of the same entries.
    entries = task_entries(task)
    ph_total, ph_done = phase_counts(entries)
    task_phase: dict[str, int] = {}
    # phase -> backticked path-ish span -> [task ids]; [P] tasks in one
    # phase sharing a span is the parallel-wave collision risk.
    par_files: dict[int, dict[str, list[str]]] = {}
    for e in entries:
        if e.phase is None:
            continue
        if e.id:
            task_phase[e.id] = e.phase
            if e.parallel:
                for span in re.findall(r"`([^`\n]+)`", e.block):
                    pathish = " " not in span and (
                        "/" in span
                        or span.rsplit(".", 1)[-1].lower() in CODE_EXT
                    )
                    if pathish:
                        par_files.setdefault(e.phase, {}).setdefault(
                            span, []
                        ).append(e.id)
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
    # citing an ID must not be able to stand in for a real reference. A live
    # adversarial test proved the whole-file version gameable — 3 real
    # "FR has no task" FAILs vanished by adding one HTML comment with no
    # actual task behind it, and a stale matrix row masked a TC whose Story
    # line had been changed to cite a different FR entirely.
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
    for t in sorted(tsks):
        entry = next((e.block for e in entries if re.search(rf"\b{t}\b", e.block)), "")
        if not re.search(r"FR-\d{3}", entry):
            fails.append(f"traceability: {t} cites no FR (scope creep?)")
    # Task-dependency dangling check: a "(after T###)" chain marker (the
    # Conventions-documented shape) pointing at a T-ID that doesn't exist —
    # same pattern as the FR/AC/D dangling checks below, just for the one ID
    # family those don't cover. WARN: this never had a check before, and a
    # dangling dependency, while a real doc defect, doesn't itself corrupt
    # status the way an ungrounded FR/task does.
    for ref in sorted(set(re.findall(r"\(after\s+(T\d{3})\)", task)) - tsks):
        warns.append(f"dangling: (after {ref}) references a task that doesn't exist")
    # Cross-phase chains: a task depending on a task in a LATER phase can
    # never be scheduled — before-audit precondition 1 in mechanical form.
    for e in entries:
        if not e.id or e.id not in task_phase:
            continue
        for ref in e.after:
            if ref in task_phase and task_phase[ref] > task_phase[e.id]:
                fails.append(
                    f"dependency: {e.id} (phase {task_phase[e.id]}) "
                    f"chains after {ref} in a later phase ({task_phase[ref]})"
                )
    # Parallel-wave collision: two [P] tasks in one phase naming the same
    # path. WARN — prose can legitimately mention a shared context file;
    # the orchestrator adjudicates (chain them or confirm disjoint).
    for n, files in sorted(par_files.items()):
        for span, ids in sorted(files.items()):
            uniq = sorted(set(ids))
            if len(uniq) > 1:
                warns.append(
                    f"parallel: {', '.join(uniq)} (phase {n}) both name `{span}` "
                    "- chain them or confirm the files are disjoint"
                )
    for ref in sorted(set(re.findall(r"FR-\d{3}", task + test)) - frs):
        fails.append(f"dangling: {ref} referenced but not defined in spec.md")
    for ref in sorted(set(re.findall(r"AC\d+", test)) - acs):
        fails.append(f"dangling: {ref} referenced but not defined in spec.md")
    for ref in sorted(set(re.findall(r"D-\d{3}", task + spec)) - ds):
        fails.append(f"dangling: {ref} referenced but not defined in tech-spec.md")
    # D-### structural completeness: a heading alone isn't a decision — the
    # template's shape is Context/Decision/Consequences, bulleted or (as
    # real specs also do it) written as bold-labelled prose paragraphs.
    # Match the label itself, not a specific bullet syntax — a live check
    # against real docs found "**Context**:" as a paragraph opener, not a
    # "- **Context**" list item, and a syntax-strict pattern false-flagged
    # it as missing. WARN, not FAIL: a stub is a real defect but not an
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
        if not re.search(r"FR-\d{3}", tc_blocks.get(tc, "")):
            fails.append(f"traceability: {tc} traces to no FR")
    # Coverage-matrix ↔ TC consistency: a matrix row's own claim (this FR is
    # covered by this TC) must be backed by that TC's own content — a stale
    # row citing a TC that no longer exists, or one whose Traces-to line was
    # since changed to a different FR, silently passed before this check.
    for fr_m, tc_col in re.findall(r"^\|\s*(FR-\d{3})\s*\|([^|]*)\|[^|]*\|\s*$", test, re.M):
        for tc_ref in re.findall(r"TC-\d{3}", tc_col):
            if tc_ref not in tc_blocks:
                warns.append(f"coverage matrix: {fr_m} cites {tc_ref}, which doesn't exist")
            elif fr_m not in tc_blocks[tc_ref]:
                warns.append(
                    f"coverage matrix: {fr_m} → {tc_ref}, but {tc_ref}'s own "
                    f"content doesn't mention {fr_m}"
                )
    # US traceability is WARN-only: never enforced before this check existed,
    # so promoting it to FAIL would break specs in the wild that have
    # untraced stories today.
    for ref in sorted(set(re.findall(r"\bUS\d{1,2}\b", test + task)) - uss):
        warns.append(f"dangling: {ref} referenced but not defined in spec.md")
    for us in sorted(uss):
        if not any(us in blk for blk in tc_blocks.values()):
            warns.append(f"traceability: {us} has no test case")
    # FR → milestone coverage: planner's "every FR in exactly one
    # milestone" rule, enforced against the ## Milestones table rows.
    # No milestone is FAIL (same severity as FR-has-no-task); membership
    # in multiple rows is WARN (the planner says exactly one, but a FR
    # split across two milestones is a planning conversation, not an
    # ID-graph corruption).
    ms_rows: list[str] = []
    for sec in re.split(r"^## ", texts["plan.md"], flags=re.M):
        if sec.split("\n", 1)[0].strip().lower().startswith("milestone"):
            ms_rows = [l for l in sec.splitlines() if l.startswith("|") and "FR-" in l]
            break
    if ms_rows:
        fr_ms: dict[str, int] = {}
        for line in ms_rows:
            for fr in re.findall(r"FR-\d{3}", line):
                fr_ms[fr] = fr_ms.get(fr, 0) + 1
        for fr in sorted(frs):
            if fr not in fr_ms:
                fails.append(f"traceability: {fr} has no milestone in plan.md")
            elif fr_ms[fr] > 1:
                warns.append(f"plan: {fr} appears in {fr_ms[fr]} milestone rows (exactly one expected)")
    else:
        warns.append("plan: no ## Milestones table rows with FR-### found")
    # TC structural shape: presence of the four labels only — vacuousness
    # is the reviewer agent's job, missing scaffolding is mechanical.
    for tc in sorted(tcs):
        blk = tc_blocks.get(tc, "")
        missing = [w for w in ("Given", "When", "Then", "Pass condition") if w not in blk]
        if missing:
            warns.append(f"{tc}: missing {'/'.join(missing)} label(s) — incomplete case?")
    # Stage gates — skipped steps become mechanical failures: progress
    # requires an approved spec, clarifications are resolved before tasks
    # exist, and the before-audit is recorded once implementation starts.
    status = spec_status(spec)
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
    if (done or in_progress) and before_audit_state(task) == "missing":
        warns.append(
            "before-audit: implementation started but task.md has no 'Before-audit:' "
            "line — record 'Before-audit: passed @ <sha>'"
        )
    # spec.md Status ↔ task.md reality ↔ specs/INDEX.md. WARN: the state
    # machine is real (Resuming depends on it) but a closing audit may
    # legitimately sit between "all ticked" and "Status: done", and
    # "approved" is indistinguishable from draft by task state alone —
    # approved-with-no-progress stays silent by design.
    if status in ("draft", "approved", "active", "done") and total_tasks:
        expected = "done" if done == total_tasks else ("active" if done or in_progress else "draft")
        if status != expected and not (status == "approved" and expected == "draft"):
            warns.append(
                f"status: spec.md says {status}, task.md looks {expected} "
                f"({done}/{total_tasks} ticked, {in_progress} in-progress)"
            )
        index = repo_root / "specs" / "INDEX.md"
        if index.exists():
            idx = index.read_text(encoding="utf-8")
            name = spec_dir.name
            idx_line = next((l for l in idx.splitlines() if f"({name}/spec.md)" in l), None)
            if idx_line is None:
                warns.append(f"index: {name} not registered in specs/INDEX.md")
            elif status not in idx_line.lower():
                warns.append(
                    f"index: INDEX.md line for {name} doesn't say '{status}' - update to match spec.md"
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
        phit: list[str] = []
        vhit: list[str] = []
        for lineno, line in enumerate(texts[f].splitlines(), start=1):
            s = HTML_COMMENT.sub(" ", CODE_SPAN.sub(" ", line))
            m = PLACEHOLDER.search(s)
            if m or "YYYY-MM-DD" in s:
                tok = m.group(0) if m else "YYYY-MM-DD"
                phit.append(f"{tok}@{lineno}")
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
        # The baseline commit may live in repo_root itself (single-repo
        # layout) or in one of its immediate subdirectories (a multi-repo
        # workspace like this one, where specs/ sits beside agent_runtime/
        # etc. and repo_root — two levels up from specs/<name>/ — has no
        # .git of its own). Same fallback shape as _pytest_target_exists.
        # `cat-file -e <sha>^{commit}` — not just ".git exists" — confirms
        # the candidate actually contains this commit before trusting its
        # HEAD, so a same-named-but-wrong repo can't produce a false staleness
        # warning (or a false all-clear).
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
            if not (cand / ".git").exists():
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
        if repo_hit is None and not saw_git_dir:
            # GITDEG honesty: a baseline that cannot be compared is not a
            # fresh baseline — the skip must be visible, not silent.
            notes.append("staleness: SKIPPED (not a git repo)")
        elif repo_hit is None:
            # Same honesty for the subtler skip: .git dirs exist, but none
            # of the candidates actually contains the baseline commit, so
            # the comparison still cannot run — say so instead of passing
            # silently. Informational note, never a warn or fail.
            notes.append(
                "staleness: SKIPPED — no candidate repo contains the baseline commit"
            )
        if repo_hit is not None:
            try:
                head = subprocess.run(
                    ["git", "-C", str(repo_hit), "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, timeout=10,
                ).stdout.strip().lower()
            except (OSError, subprocess.SubprocessError):
                head = ""
            if head and head != sha.lower() and not (
                head.startswith(sha.lower()) or sha.lower().startswith(head)
            ):
                where = f" (repo: {repo_hit.name})" if repo_hit != repo_root else ""
                warns.append(
                    f"survey baseline {sha}, HEAD {head}{where} — "
                    "re-survey before trusting statuses"
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
    # matching nothing is exactly how the wrong suggest-graph path went
    # unnoticed through four downstream docs in the live incident.
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
        f"  IDs: {len(frs)} FR · {len(acs)} AC · {len(uss)} US · "
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
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
