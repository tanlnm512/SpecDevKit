#!/usr/bin/env python3
"""Diff-facing review instruments for a spec-to-prod spec: scope diff,
cleanliness sweep, TC proofs, DoD scorecard — the evidence-gathering
tools the orchestrator runs after execute lands (no pipeline gates of
their own; findings are adjudicated by the orchestrator).

Usage: audit.py scope    <spec-dir> [--repo <path>] [--base <rev>]
       audit.py clean    [<spec-dir>] [--repo <path>] [--base <rev>]
       audit.py proofs   <spec-dir> [--repo <path>] [--run]
       audit.py mutate   <spec-dir> [--repo <path>] [--base <rev>] [--max-mutants N]
       audit.py coverage <spec-dir> [--repo <path>] [--threshold N]
       audit.py dod      <spec-dir> [--repo <path>] [--base <rev>] [--dry-run]
       audit.py converge <spec-dir> [--repo <path>] [--base <rev>]
       audit.py archived [--repo <path>]
       audit.py -h | --help        (prints this text, exit 0)

(--repo defaults to the spec dir's grandparent: specs/<name>/ -> repo
root; clean, whose optional spec-dir positional is accepted and ignored,
defaults to ., as does archived, which takes no positional)

scope  — every file changed vs base (default: the approval freeze's
         Approved-at SHA, falling back to HEAD; explicit --base
         overrides) is grep'd against the spec dir's task.md,
         tech-spec.md and plan.md. A changed path no doc mentions (full
         path, then bare filename) is listed as UNMENTIONED — a scope-creep
         candidate for the orchestrator to adjudicate, not a verdict:
clean  — the diff's ADDED lines (plus untracked files' contents) scanned
         for debug prints, TODO/FIXME/XXX/HACK markers, commented-out
         calls, essay comments (one comment line ≥120 chars), and
         comment walls (≥8 consecutive comment lines) — comments should
         state constraints, not narrate. Heuristic suspects for the
         orchestrator to adjudicate; spec-mandated logging is a ruling,
         not a finding.
proofs — each TC's Pass condition in test.md is classified auto (a
         runnable command) or manual (human observation) and listed; with
         --run, auto commands execute (cwd = repo root, 120s timeout
         each) and report PASS/FAIL with the command line for pasting
         into the tick evidence. --run executes commands embedded in
         test.md — opt-in for the same reason you'd read a command
         before pasting it into a shell.
dod    — the Definition-of-Done scorecard (gates/dod.md): runs
         check.py, live TC proofs, and the scope/hygiene counts in one
         pass; mechanical gates print PASS/FAIL, judgment gates print
         MANUAL for the orchestrator to satisfy. Like proofs --run, dod
         executes the TC commands embedded in test.md. Every checker
         subprocess fails closed: one that cannot start, times out, or
         delivers no verdict line fails its gate with a diagnostic
         instead of reading as green, and failed proofs are named under
         the gate table. --dry-run keeps the scorecard inert: auto TCs
         are classified, gate 1 reads DRY, and no test.md command
         executes — the state-inspection path.
converge — diffs specs/<name>/survey.md against its last committed
         version (default: HEAD; --base overrides) to surface what a
         fresh re-survey found that the previous one didn't: run this
         AFTER re-running the surveyor in place (single-agent repair run,
         SKILL.md § Run modes), never before. Reports each item id that is
         new (NEW GAP) or whose status regressed (DONE -> PARTIAL/TODO,
         REGRESSED) since the committed baseline — the mechanical half of
         "the codebase drifted past the spec"; the orchestrator turns each
         into a task (next free T-ID via `check.py --next-ids`) instead of
         the drift going unnoticed. Items unchanged or newly improved are
         not listed.

mutate  — mutation testing over the changed implementation files
         (D-027): flips operators and constants one at a time in every
         changed non-test .py file vs base (default: the approval
         freeze's Approved-at SHA) and re-runs the auto TC commands from
         test.md after each mutant. A mutant that turns the suite red is
         KILLED; one the whole suite survives is SURVIVED — no test in
         the suite distinguishes it, a test gap to adjudicate, not a
         pass. Stdlib-only AST engine (compare/boolean/arithmetic
         operator swaps, small-int constant bumps); --max-mutants caps
         the run (default 40) and a 10-minute wall budget stops it
         early, listing what stayed untried. Mutants are written in
         place and byte-restored after each run (a restore that cannot
         be verified aborts the file loudly); timeouts count as killed
         (the mutant hung the suite). Report always; exit 0.

coverage — line-coverage floor over the tasks' intended files (D-027):
         runs the repo suite once under pytest-cov and checks every
         `Touches:` path from task.md against the floor — spec.md's
         `**Coverage**: <int>` header (default 80), or --threshold to
         override for this run. Uses the repo's OWN pytest/pytest-cov
         when present (optional instruments, never new dependencies);
         without them it degrades to an explicit SKIPPED, never a
         false all-green. A red suite fails the mode outright; a touched
         file missing from the report reads UNMEASURED and fails.
         Exit 0 = every touched file at/above the floor · 1 = below,
         unmeasured, or the suite is red.

archived — the archive gate (OpenSpec validate --archived semantics):
         every dir under specs/archive/ must hold a task.md with no
         unticked, unstruck entry — an open box in the archive means a
         plan was archived incomplete, and the as-built record lies.
         Pure doc-state (no git, no SKIPPED path); runs anywhere, cheap
         enough for a pre-push or pre-archive hook.

Exit:  0 = report produced (scope/clean/converge always; proofs without
      --run) · proofs --run / dod / archived: 0 = every mechanical gate
      green, 1 = any FAILED or errored (dod --dry-run: gate 1 reads DRY —
      classified, not executed — and is not a failure) · 2 = usage error.

Non-git repos: git-derived output degrades explicitly, never silently —
scope/clean print `SKIPPED (not a git repo)` instead of a false all-clear
(an empty diff is not a clean tree), converge reports the missing
repository rather than a phantom baseline, and dod's git-derived gates
read SKIPPED.
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Shared doc-state parsers live in specstate.py beside this script — one
# canonical regex per doc shape, shared with check.py and graph.py. The
# scripts dir goes on sys.path locally (no install step): tests load this
# file by path via importlib, which does not put scripts/ on sys.path.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from specstate import (  # noqa: E402 - the sys.path setup above runs first
    approval_sha,
    coverage_floor,
    survey_items,
    task_entries,
    task_touches,
)

# Debug prints across common languages. printf( is deliberately absent —
# ordinary C output; WARN heuristics err toward recall, the orchestrator
# rules on precision.
DEBUG = re.compile(
    r"console\.(log|debug|error)\(|\be?println!\(|\bdbg!\(|"
    r"\bSystem\.(out|err)\.print|\bNSLog\(|\bprint_r\(|\bvar_dump\(|"
    r"(?<![\w.])print\("
)
MARKER = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
# A commented function call — `# foo(...)` / `// foo(...)` — the classic
# commented-out-code shape. Coarse on purpose; WARN-tier only.
COMMENTED_CALL = re.compile(r"^\s*(#|//)\s*[A-Za-z_][\w.]*\(")
# A comment line in any line-comment dialect (#, //, --). Markdown is
# excluded downstream: '#' there is a heading, not a comment.
COMMENT_LINE = re.compile(r"^\s*(#(?!!)|//|--)")
ESSAY_MIN = 120  # chars: a comment paragraph, not a constraint
WALL_MIN = 8     # consecutive comment lines: prose where a doc belongs

RUNNERS = {
    "npm", "pnpm", "yarn", "pytest", "python", "python3", "cargo", "go",
    "make", "curl", "bash", "sh", "zsh", "node", "deno", "mvn", "gradle",
    "dotnet", "ruby", "rspec", "docker", "git",
}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True
        )
    except (OSError, subprocess.SubprocessError) as e:
        # git missing/unreadable degrades exactly like non-git: a failing
        # status flows into the same SKIPPED paths below — never a traceback
        # (same catch shape as check.py's staleness guard).
        return subprocess.CompletedProcess(
            ["git", "-C", str(repo), *args], 127, "", f"git: {e}"
        )


def git_available(repo: Path) -> bool:
    """True iff `repo` sits inside a working git repository — the single
    availability probe at the git() choke point. Every git-derived verdict
    consults this first: when it is False the mode prints an explicit
    `SKIPPED (not a git repo)` notice instead of silently reading the
    empty diff output as a clean result.

    Local wrapper on purpose, mirroring git() above: routing through
    audit.git keeps the suite's audit.git patches in charge (delegating to
    specstate.git_available bypasses them and un-mocks the converge
    distinction tests). specstate.git_available remains the canonical
    probe for check.py-external consumers (graph.py)."""
    return git(repo, "rev-parse", "--git-dir").returncode == 0


def changed_paths(repo: Path, base: str | None) -> list[str]:
    """All changed paths: tracked diff vs base (default HEAD) plus every
    untracked file — git diff alone is blind to new files, and a whole
    plan's work sits uncommitted until delivery's implementation commit."""
    paths: set[str] = set()
    diff_arg = base if base else "HEAD"
    r = git(repo, "diff", "--name-only", diff_arg)
    paths.update(l.strip() for l in r.stdout.splitlines() if l.strip())
    r = git(repo, "status", "--porcelain", "--untracked-files=all")
    for line in r.stdout.splitlines():
        p = line[3:].strip().strip('"')
        if "->" in p:  # rename: keep the new side; the old side is covered below
            p = p.split("->")[-1].strip().strip('"')
        if p:
            paths.add(p)
    return sorted(paths)


def added_lines(repo: Path, base: str | None):
    """Yield (path, lineno, text) for every added line: tracked diff plus
    untracked files (whose whole content counts as added)."""
    diff_arg = base if base else "HEAD"
    r = git(repo, "diff", "-U0", diff_arg)
    path, lineno = None, None
    for line in r.stdout.splitlines():
        m = re.match(r"^\+\+\+ b/(.*)$", line)
        if m:
            path, lineno = m.group(1), None
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", line)
        if m:
            lineno = int(m.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++") and path:
            yield path, lineno, line[1:]
            if lineno:
                lineno += 1
    r = git(repo, "status", "--porcelain", "--untracked-files=all")
    for line in r.stdout.splitlines():
        if not line.startswith("??"):
            continue
        p = line[3:].strip().strip('"')
        f = repo / p
        if f.is_file():
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                for i, t in enumerate(text.splitlines(), 1):
                    yield p, i, t
            except OSError:
                pass


def effective_base(spec_dir: Path, base: str | None) -> str | None:
    """Diff base for the review instruments: explicit override, else the
    approval freeze's Approved-at anchor (the commit the docset was
    approved against — what "the implementation changed" means)."""
    if base:
        return base
    return approval_sha(spec_dir)


def scope_data(spec_dir: Path, repo: Path, base: str | None) -> tuple[list[str], list[str]]:
    """(changed paths, unmentioned subset) — shared by scope and dod."""
    docs = ""
    for f in ("task.md", "tech-spec.md", "plan.md"):
        p = spec_dir / f
        if p.exists():
            docs += p.read_text(encoding="utf-8", errors="replace") + "\n"
    base = effective_base(spec_dir, base)
    paths = changed_paths(repo, base)
    try:
        own_prefix = spec_dir.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        own_prefix = f"specs/{spec_dir.name}"
    unmentioned: list[str] = []
    for p in paths:
        if not p.startswith("specs/"):
            if p not in docs and Path(p).name not in docs:
                unmentioned.append(p)
            continue
        # This spec's own contract/evidence tree is expected delivery
        # surface. Shared specs files are allowed only when a contract doc
        # names them; every other specs/ path is scope creep.
        if p.startswith(own_prefix + "/"):
            continue
        shared = (
            p == "specs/INDEX.md"
            or p == "specs/CONSTITUTION.md"
            or p.startswith("specs/context/")
        )
        if not shared or (p not in docs and Path(p).name not in docs):
            unmentioned.append(p)
    return paths, unmentioned


def mode_scope(spec_dir: Path, repo: Path, base: str | None) -> int:
    if not git_available(repo):
        print("scope: SKIPPED (not a git repo) — no scope verdict")
        return 0
    base = effective_base(spec_dir, base)
    paths, unmentioned = scope_data(spec_dir, repo, base)
    print(f"scope: {len(paths)} changed file(s) vs {base or 'working tree'}")
    for p in unmentioned:
        print(f"  UNMENTIONED  {p}")
    if not unmentioned:
        print("  every changed file is named in task/tech-spec/plan")
    return 0


def clean_findings(repo: Path, base: str | None) -> list[tuple[str, int | None, str, str]]:
    """(path, lineno, kind, text) suspects — shared by clean and dod."""
    finds: list[tuple[str, int | None, str, str]] = []
    wall_run = 0
    wall_path: str | None = None
    for path, ln, text in added_lines(repo, base):
        if path.startswith("specs/"):
            continue  # the docs are the intent, not the debris surface
        is_comment = (not path.endswith(".md")) and bool(COMMENT_LINE.match(text))
        if is_comment:
            if wall_path != path:
                wall_path, wall_run = path, 0
            wall_run += 1
            if wall_run == WALL_MIN:
                finds.append((path, ln, "comment wall",
                              f"{WALL_MIN}+ consecutive comment lines"))
        else:
            wall_run = 0
        if DEBUG.search(text):
            finds.append((path, ln, "debug print", text.strip()))
        elif MARKER.search(text):
            finds.append((path, ln, "marker", text.strip()))
        elif COMMENTED_CALL.match(text):
            finds.append((path, ln, "commented-out call", text.strip()))
        elif is_comment and len(text.strip()) >= ESSAY_MIN and "http" not in text:
            finds.append((path, ln, "essay comment", text.strip()[:100]))
    return finds


def mode_clean(repo: Path, base: str | None) -> int:
    if not git_available(repo):
        print("clean: SKIPPED (not a git repo) — no cleanliness verdict")
        return 0
    finds = clean_findings(repo, base)
    print(f"clean: scanned added lines vs {base or 'working tree'}")
    for path, ln, kind, text in finds:
        loc = f"{path}:{ln}" if ln else path
        print(f"  SUSPECT  {loc}  [{kind}]  {text[:100]}")
    if not finds:
        print("  no debug prints, markers, commented-out calls, essay "
              "comments, or comment walls in added lines")
    return 0


def looks_runnable(cmd: str) -> bool:
    c = cmd.strip()
    if c.startswith(("./", "/")):
        return True
    parts = c.split()
    first = parts[0] if parts else ""
    if first in RUNNERS or "/" in first:
        return True
    # Anything else that resolves on PATH (bare `true`, `ls`, a project
    # binary) is runnable; prose first words ("The suite …") are not.
    return bool(shutil.which(first))


def classify_proofs(spec_dir: Path) -> dict:
    """Classify every TC's pass condition — {"auto": [(tc, cmd)],
    "manual": [(tc, note)]}. Pure doc-state read: nothing executes on this
    path, so state inspection can consume it freely; execution happens only
    in proofs_data, on the explicit live paths."""
    test_p = spec_dir / "test.md"
    text = test_p.read_text(encoding="utf-8", errors="replace") if test_p.exists() else ""
    tc_blocks: dict[str, str] = {}
    for sec in re.split(r"^#{2,3} ", text, flags=re.M):
        m = re.match(r"(TC-\d{3})\b", sec)
        if m:
            tc_blocks[m.group(1)] = sec
    auto: list[tuple[str, str]] = []
    manual: list[tuple[str, str]] = []
    for tc in sorted(tc_blocks):
        blk = tc_blocks[tc]
        pm = re.search(r"\*\*Pass condition\*\*:?(.*)", blk)
        if not pm:
            manual.append((tc, "(no pass-condition line)"))
            continue
        chunk = pm.group(1)
        for cont in blk[pm.end():].splitlines():  # wrapped command lines
            if cont.startswith("- ") or not cont.strip():
                break
            chunk += " " + cont.strip()
        cmds = re.findall(r"`([^`]+)`", chunk)
        cmd = cmds[0].strip() if cmds else ""
        (auto if cmd and looks_runnable(cmd) else manual).append((tc, cmd or "(observation only)"))
    return {"auto": auto, "manual": manual}


def proofs_data(spec_dir: Path, repo: Path, run: bool) -> dict:
    """classify_proofs plus, only when run, execution of the auto commands:
    {"auto": [(tc, cmd)], "manual": [(tc, note)], "ok": {tc: (passed,
    summary)}, "errors": [(tc, cmd, err)], "failed": n} — ok/errors/failed
    stay empty/zero on a dry run. Shared by proofs and dod's live path;
    callers that must stay inert use classify_proofs itself."""
    data: dict = {"ok": {}, "errors": [], "failed": 0, "timeouts": set()}
    data.update(classify_proofs(spec_dir))
    if not run:
        return data
    for tc, cmd in data["auto"]:
        try:
            r = subprocess.run(
                cmd, shell=True, cwd=str(repo), timeout=120,
                capture_output=True, text=True, errors="replace",
            )
            ok = r.returncode == 0
            summary = (r.stdout.strip().splitlines() or [""])[-1]
        except subprocess.TimeoutExpired:
            ok, summary = False, ("(timeout after 120s — runtime cap, not a "
                                  "correctness verdict: bound the corpus or "
                                  "record a D-### standing verify)")
            data["timeouts"].add(tc)
        except OSError as e:
            data["errors"].append((tc, cmd, str(e)))
            data["failed"] += 1
            continue
        data["ok"][tc] = (ok, summary[:100])
        if not ok:
            data["failed"] += 1
    return data


def proof_verdict_lines(data: dict) -> dict[str, str]:
    """{tc: verdict line} for a run proofs_data returned — the one
    formatter behind proofs' full listing and dod's failed-proof naming."""
    errs = {tc: e for tc, _, e in data["errors"]}
    lines: dict[str, str] = {}
    for tc, cmd in data["auto"]:
        if tc in data["ok"]:
            ok, summary = data["ok"][tc]
            verdict = "TIMEOUT" if (not ok and tc in data["timeouts"]) else ("PASS" if ok else "FAIL")
            lines[tc] = f"  {verdict:<7}  {tc}  {cmd}  ->  {summary}"
        else:
            lines[tc] = f"  ERROR   {tc}  {cmd}  ({errs[tc]})"
    return lines


def mode_proofs(spec_dir: Path, repo: Path, run: bool) -> int:
    d = proofs_data(spec_dir, repo, run)
    auto, manual = d["auto"], d["manual"]
    if not run:
        print(f"proofs: {len(auto)} auto · {len(manual)} manual (dry run — add --run to execute)")
        for tc, cmd in auto:
            print(f"  AUTO   {tc}  {cmd}")
        for tc, note in manual:
            print(f"  MANUAL {tc}  {note}")
        return 0
    print(f"proofs: running {len(auto)} auto command(s), {len(manual)} manual (yours to observe)")
    for line in proof_verdict_lines(d).values():
        print(line)
    return 1 if d["failed"] else 0


# --- mutation testing (D-027) ----------------------------------------------
# A stdlib-only AST engine: one operator/constant flip at a time, the auto
# TC commands as the kill suite. Optional instrument in the target repo's
# own terms — no new dependency anywhere (constitution C-06).

CMP_SWAP = {
    ast.Lt: ast.GtE, ast.LtE: ast.Gt, ast.Gt: ast.LtE, ast.GtE: ast.Lt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Is: ast.IsNot,
    ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In,
}
BIN_SWAP = {
    ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult,
}
MUT_TIMEOUT = 120        # per auto-TC command while killing one mutant
MUT_BUDGET = 600         # wall-clock seconds before no new mutant starts
TEST_PATH = re.compile(r"(^|/)(tests?/|test_[^/]+\.py$|[^/]+_test\.py$)")


class _OneMutator(ast.NodeTransformer):
    """Applies exactly one mutation, targeted by node identity."""

    def __init__(self, target: ast.AST, kind: str) -> None:
        self.target, self.kind, self.hit = target, kind, False

    def _try(self, node: ast.AST) -> ast.AST | None:
        if node is not self.target:
            return None
        self.hit = True
        if self.kind == "compare":
            node.ops = [CMP_SWAP[type(node.ops[0])]()]
        elif self.kind == "boolop":
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        elif self.kind == "binop":
            node.op = BIN_SWAP[type(node.op)]()
        elif self.kind == "const":
            node.value = node.value + 1
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.Compare:
        return self._try(node) or self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.BoolOp:
        return self._try(node) or self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> ast.BinOp:
        return self._try(node) or self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:
        return self._try(node) or self.generic_visit(node)


def mutation_sites(tree: ast.Module) -> list[tuple[str, ast.AST, int, str]]:
    """Every mutable site as (kind, node, lineno, human description)."""
    sites: list[tuple[str, ast.AST, int, str]] = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and type(node.ops[0]) in CMP_SWAP):
            sites.append(("compare", node, node.lineno,
                          f"{type(node.ops[0]).__name__}→"
                          f"{CMP_SWAP[type(node.ops[0])].__name__}"))
        elif isinstance(node, ast.BoolOp):
            kind = "boolop"
            desc = (f"{type(node.op).__name__}→"
                    f"{'Or' if isinstance(node.op, ast.And) else 'And'}")
            sites.append((kind, node, node.lineno, desc))
        elif isinstance(node, ast.BinOp) and type(node.op) in BIN_SWAP:
            sites.append(("binop", node, node.lineno,
                          f"{type(node.op).__name__}→"
                          f"{BIN_SWAP[type(node.op)].__name__}"))
        elif (isinstance(node, ast.Constant) and type(node.value) is int
                and not isinstance(node.value, bool)
                and abs(node.value) < 10 ** 6):
            sites.append(("const", node, node.lineno,
                          f"const {node.value}→{node.value + 1}"))
    return sites


def python_mutants(text: str, path: str) -> tuple[list[tuple[int, str, str]], str | None]:
    """(lineno, description, mutated source) per mutant — fresh parse per
    mutant, so flips never stack. Second element: fatal parse error, if
    the file is not valid Python at all."""
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [], f"{path}: not valid Python ({e.msg} line {e.lineno})"
    out: list[tuple[int, str, str]] = []
    for kind, _node, lineno, desc in mutation_sites(tree):
        fresh = ast.parse(text)          # identity targeting needs the
        sites = mutation_sites(fresh)    # same deterministic walk order
        target = next((n for k, n, ln, _ in sites
                       if k == kind and ln == lineno), None)
        if target is None:
            continue
        mut = _OneMutator(target, kind)
        mutated = mut.visit(fresh)
        if not mut.hit:
            continue
        ast.fix_missing_locations(mutated)
        out.append((lineno, desc, ast.unparse(mutated)))
    return out, None


def _mutantable_paths(repo: Path, base: str | None) -> list[str]:
    """Changed .py implementation files: the mutation surface. Tests are
    excluded — the engine mutates the implementation and lets the suite
    kill it, never the other way around."""
    return [p for p in changed_paths(repo, base)
            if p.endswith(".py") and not p.startswith("specs/")
            and not TEST_PATH.search(p) and (repo / p).is_file()]


def _kill_env() -> dict[str, str]:
    """The kill suite runs without bytecode caching: a same-size mutant
    written within the same mtime tick would otherwise reuse the previous
    mutant's __pycache__ entry and read a cached predecessor (CPython
    validates pyc by mtime+size), turning every survivor into a fake
    kill."""
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def _drop_pycache(repo: Path, path: str) -> None:
    """Delete the mutated module's stale .pyc files — a pyc compiled from
    an earlier mutant (or the pre-mutate source) can still be judged valid
    when size and mtime-second collide; none may outlive the run."""
    pyc_dir = (repo / path).parent / "__pycache__"
    if not pyc_dir.is_dir():
        return
    stem = Path(path).stem
    for pyc in pyc_dir.glob(f"{stem}.*.pyc"):
        try:
            pyc.unlink()
        except OSError:
            pass


def _run_kill_suite(commands: list[str], repo: Path) -> tuple[str, str]:
    """(verdict, detail) for one mutant: 'killed' on the first red or
    timeout command, 'survived' when the whole suite stays green."""
    for cmd in commands:
        try:
            r = subprocess.run(cmd, shell=True, cwd=str(repo),
                               capture_output=True, text=True,
                               timeout=MUT_TIMEOUT,
                               env=_kill_env())
        except subprocess.TimeoutExpired:
            return "killed", f"timeout in `{cmd}`"
        except (OSError, subprocess.SubprocessError) as e:
            return "killed", f"`{cmd}` raised {e!r}"
        if r.returncode != 0:
            return "killed", f"exit {r.returncode} in `{cmd}`"
    return "survived", "suite stayed green"


def mode_mutate(spec_dir: Path, repo: Path, base: str | None,
                max_mutants: int) -> int:
    """Mutation testing over the changed implementation files: every
    KILLED mutant was distinguished by some test; every SURVIVED one is a
    test gap for the orchestrator to adjudicate. Report always; the
    original file bytes are restored and verified after each mutant."""
    if not git_available(repo):
        print("mutate: SKIPPED (not a git repo) — no changed-file surface")
        return 0
    commands = [cmd for _tc, cmd in classify_proofs(spec_dir)["auto"]]
    if not commands:
        print("mutate: no auto TC commands in test.md — nothing to kill "
              "mutants with (write executable pass conditions first)")
        return 0
    files = _mutantable_paths(repo, effective_base(spec_dir, base))
    if not files:
        print("mutate: no changed non-test .py files vs "
              f"{effective_base(spec_dir, base) or 'working tree'} — "
              "nothing to mutate")
        return 0
    print(f"mutate: {len(files)} changed implementation file(s) vs "
          f"{effective_base(spec_dir, base)}, kill suite = "
          f"{len(commands)} auto TC command(s), cap {max_mutants} mutants")
    counts = {"killed": 0, "survived": 0}
    survivors: list[str] = []
    started = time.monotonic()
    tried = 0
    done = False
    for path in files:
        if done:
            break
        _drop_pycache(repo, path)
        original = (repo / path).read_text(encoding="utf-8",
                                           errors="replace")
        mutants, err = python_mutants(original, path)
        if err:
            print(f"  SKIP     {err}")
            continue
        if not mutants:
            print(f"  NOTE     {path}: no mutable sites")
            continue
        for lineno, desc, mutated in mutants:
            if tried >= max_mutants:
                print(f"  STOP     mutant cap {max_mutants} reached — "
                      "re-run with --max-mutants to go deeper")
                done = True
                break
            if time.monotonic() - started > MUT_BUDGET:
                print("  STOP     time budget reached — remaining sites "
                      "untried")
                done = True
                break
            tried += 1
            try:
                (repo / path).write_text(mutated, encoding="utf-8")
                verdict, detail = _run_kill_suite(commands, repo)
            finally:
                (repo / path).write_text(original, encoding="utf-8")
            if (repo / path).read_text(encoding="utf-8",
                                       errors="replace") != original:
                print(f"  FAIL     {path}: restore not verifiable — "
                      "stopping this file, check `git diff` before "
                      "proceeding")
                done = True
                break
            counts[verdict] += 1
            line = f"{path}:{lineno}  {desc}"
            if verdict == "survived":
                survivors.append(line)
                print(f"  SURVIVED {line} — {detail}")
            else:
                print(f"  KILLED   {line} ({detail})")
    total = counts["killed"] + counts["survived"]
    if not total:
        print("  no mutants tried")
        return 0
    pct = round(100 * counts["killed"] / total)
    print(f"  {counts['killed']}/{total} mutants killed ({pct}%) · "
          f"{counts['survived']} survived")
    if survivors:
        print("  adjudicate the survivors: no test in the suite "
              "distinguishes them — a missing case, not a pass")
    return 0


# --- coverage floor (D-027) -------------------------------------------------

COV_LINE = re.compile(r"^(.*?)\s+(\d+)\s+(\d+)\s+(\d+)%\s*(.*)$")


def _cov_tooling(repo: Path) -> bool:
    """True when the repo's own pytest + pytest-cov are importable —
    optional instruments detected at runtime, never installed by us."""
    for mod in ("pytest", "pytest_cov"):
        r = subprocess.run(
            [sys.executable, "-c", f"import {mod}"], cwd=str(repo),
            capture_output=True)
        if r.returncode != 0:
            return False
    return True


def parse_cov_table(text: str) -> dict[str, int]:
    """{normalized path: cover%} from a `coverage term` table. Paths may
    contain spaces; the shape (name stmts miss % missing) pins the parse."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        m = COV_LINE.match(line.strip())
        if not m:
            continue
        name = m.group(1)
        if name in ("Name", "TOTAL", ""):
            continue
        try:
            int(m.group(2)), int(m.group(3)), int(m.group(4))
        except ValueError:
            continue
        out[Path(name).as_posix()] = int(m.group(4))
    return out


def mode_coverage(spec_dir: Path, repo: Path, threshold: int | None) -> int:
    """Line-coverage floor over the tasks' intended files: the repo suite
    once under its own pytest-cov, every task.md `Touches:` path checked
    against the floor. SKIPPED (loudly) without the tooling; a red suite
    or an unmeasured touched file fails."""
    if not _cov_tooling(repo):
        print("coverage: SKIPPED (pytest or pytest-cov not installed in "
              "this repo) — no coverage verdict, never a false green")
        return 0
    task_p = spec_dir / "task.md"
    task = task_p.read_text(encoding="utf-8", errors="replace") if task_p.exists() else ""
    touched: set[str] = set()
    for entry in task_entries(task):
        touched.update(task_touches(entry))
    targets = sorted(t for t in touched
                     if (repo / t).exists() and not t.startswith("specs/"))
    if not targets:
        print("coverage: no resolvable intended files in task.md "
              "`Touches:` — nothing to measure")
        return 0
    spec_p = spec_dir / "spec.md"
    spec_text = (spec_p.read_text(encoding="utf-8", errors="replace")
                 if spec_p.exists() else "")
    floor = threshold if threshold is not None else coverage_floor(spec_text)
    # pytest-cov treats a non-directory --cov argument as a MODULE name,
    # so a bare `calc.py` collects nothing ("module calc.py was never
    # imported") — widen file targets to their parent directory and match
    # the exact file's row in the report instead.
    cov_args = [t if (repo / t).is_dir() else str(Path(t).parent or ".")
                for t in targets]
    argv = [sys.executable, "-m", "pytest",
            *[f"--cov={a}" for a in sorted(set(cov_args))],
            "--cov-report=term", "-q"]
    print(f"coverage: floor {floor}% over {len(targets)} intended "
          f"file(s)/dir(s) — running the repo suite once")
    try:
        r = subprocess.run(argv, cwd=str(repo), capture_output=True,
                           text=True, errors="replace", timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"coverage: FAIL — the suite could not run ({e!r})")
        return 1
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        print("coverage: FAIL — the repo suite is red; coverage of a "
              "failing suite is not evidence")
        for line in tail:
            print(f"    {line}")
        return 1
    measured = parse_cov_table(r.stdout)
    fails = 0
    for t in targets:
        key = Path(t).as_posix()
        hit = measured.get(key)
        hits = [pct for p, pct in measured.items()
                if p == key or p.startswith(key.rstrip("/") + "/")]
        if hit is None and hits:
            hit = min(hits)   # a directory target: its weakest file speaks
        if hit is None:
            print(f"  FAIL  {t}: UNMEASURED — in Touches but absent from "
                  "the coverage report")
            fails += 1
        elif hit < floor:
            print(f"  FAIL  {t}: {hit}% < floor {floor}%")
            fails += 1
        else:
            print(f"  PASS  {t}: {hit}%")
    print(f"  {'PASS' if not fails else 'FAIL'} — "
          f"{len(targets) - fails}/{len(targets)} intended file(s)/dir(s) "
          f"at or above {floor}%")
    return 1 if fails else 0


def mode_dod(spec_dir: Path, repo: Path, base: str | None,
             dry: bool = False) -> int:
    """The DoD scorecard: mechanical gates measured, judgment gates MANUAL.
    Runs check.py, live proofs, and the scope/hygiene counts — the same
    trust level as the delivery pass itself (it executes TC commands).
    Every checker subprocess fails closed: one that cannot start, times
    out, or delivers no verdict fails its gate with a diagnostic, and
    failed proofs are named under the gate table. dry classifies the
    auto TCs without executing any command (gate 1 reads DRY) — the
    state-inspection path."""
    # gate 4 — task.md completeness (specstate.task_entries, the same
    # shared parser check.py reads the docset with)
    task_p = spec_dir / "task.md"
    task = task_p.read_text(encoding="utf-8", errors="replace") if task_p.exists() else ""
    entries = task_entries(task)
    total = len(entries)
    done = sum(1 for e in entries if e.done)
    landed = sum(1 for e in entries
                 if e.done or e.implemented or e.struck)
    inprog = sum(1 for e in entries if e.claimed)
    # gate 5 — check.py (sibling script; WARNs don't fail, ownership is a
    # judgment the detail line reminds the orchestrator of). Fail-closed:
    # a checker that never delivered a verdict must fail the gate — its
    # stdout holds no FAIL lines, so counting alone would read as green.
    nfail = nwarn = 0
    check_err: str | None = None
    check = Path(__file__).resolve().parent / "check.py"
    try:
        check_argv = [str(spec_dir)]
        if repo != spec_dir.parent.parent:
            check_argv += ["--repo", str(repo)]
        cp = subprocess.run([sys.executable, str(check), *check_argv],
                            capture_output=True, text=True, errors="replace",
                            timeout=120)
    except subprocess.TimeoutExpired:
        check_err = "check.py timed out after 120s — no contract verdict"
    except OSError as e:
        check_err = f"check.py could not start: {e}"
    else:
        mw = re.search(r"\((\d+) fail, (\d+) warn\)", cp.stdout)
        if mw is None:
            # Nonzero rc WITH the summary is check.py's normal failing
            # verdict; any rc without it is a crash — stderr's last line
            # is the concise cause.
            cause = (cp.stderr.strip().splitlines() or ["(no stderr)"])[-1]
            check_err = (f"check.py produced no verdict (rc {cp.returncode}): "
                         f"{cause[:80]}")
        else:
            nfail = len(re.findall(r"^  FAIL  ", cp.stdout, flags=re.M))
            nwarn = int(mw.group(2))
    # gates 1-2 — proofs. --dry-run classifies only: no test.md command
    # executes on that path; the live run stays the explicit default.
    verdict_lines: dict[str, str] = {}
    bad_tcs: list[str] = []
    if dry:
        pr = classify_proofs(spec_dir)
    else:
        pr = proofs_data(spec_dir, repo, True)
        verdict_lines = proof_verdict_lines(pr)
        bad_tcs = sorted(
            {tc for tc, (ok, _) in pr["ok"].items() if not ok}
            | {tc for tc, _, _ in pr["errors"]}
        )
    nauto = len(pr["auto"])
    # gates 6-7 — scope + hygiene. Git-derived: without a repository they
    # print SKIPPED instead of passing off the empty diff as a clean one.
    git_ok = git_available(repo)
    paths, unment = scope_data(spec_dir, repo, base)
    dirt = clean_findings(repo, base)
    if git_ok:
        scope_st = "PASS" if not unment else "FAIL"
        scope_dt = f"{len(unment)} unmentioned of {len(paths)} changed"
        hyg_st = "PASS" if not dirt else "FAIL"
        hyg_dt = f"{len(dirt)} suspect(s) in added lines"
    else:
        scope_st = hyg_st = "SKIPPED"
        scope_dt = "(not a git repo) — no scope verdict"
        hyg_dt = "(not a git repo) — no cleanliness verdict"

    if dry:
        proof_st = "DRY"
        proof_dt = (f"{nauto} auto TC(s) classified, not executed — drop "
                    "--dry-run to prove them")
    else:
        proof_st = "PASS" if pr["failed"] == 0 else "FAIL"
        proof_dt = (f"{nauto - pr['failed']}/{nauto} TCs green"
                    if nauto else "no auto TCs (n/a)")
        if bad_tcs:
            proof_dt += f" — failed: {', '.join(bad_tcs)}"

    gates = [
        (1, "PROOF auto", proof_st, proof_dt),
        (2, "PROOF manual", "MANUAL",
         f"{len(pr['manual'])} observation TC(s) — record each result"),
        (3, "REGRESSION", "MANUAL", "run the repo suite; paste exit-0 output"),
        (4, "COMPLETENESS",
         "PASS" if total and landed == total and not inprog else "FAIL",
         f"{done}/{total} ticked, {landed}/{total} landed, {inprog} in-progress"),
        (5, "CONTRACT", "FAIL" if nfail or check_err else "PASS",
         check_err or f"check.py: {nfail} fail, {nwarn} warn (each WARN fixed or ruled)"),
        (6, "SCOPE", scope_st, scope_dt),
        (7, "HYGIENE", hyg_st, hyg_dt),
        (8, "REVIEW", "MANUAL",
         "reviewer BLOCKs = 0; WARN/NIT fixed or parked-with-ruling"),
        (9, "RULINGS", "MANUAL",
         "every D-### surfaced in the delivery summary"),
        (10, "SIGN-OFF", "MANUAL", "explicit yes on the summary"),
    ]
    print(f"dod: {spec_dir} — gate table in gates/dod.md"
          + (" (dry run)" if dry else ""))
    for num, name, st, detail in gates:
        print(f"  {num:>2} {name:<13} {st:<7} {detail}")
    for tc in bad_tcs:
        print(verdict_lines[tc])
    bad = [str(n) for n, _, st, _ in gates if st == "FAIL"]
    if bad:
        print(f"  VERDICT: MECHANICAL FAIL — gate(s) {', '.join(bad)}; manual gates remain")
        return 1
    notes: list[str] = []
    dry_gates = [str(n) for n, _, st, _ in gates if st == "DRY"]
    if dry_gates:
        notes.append(f"gate(s) {', '.join(dry_gates)} classified, not "
                     "executed (dry run)")
    skipped = [str(n) for n, _, st, _ in gates if st == "SKIPPED"]
    if skipped:
        notes.append(f"git gates {', '.join(skipped)} SKIPPED (not a git repo)")
    if notes:
        print(f"  VERDICT: MECHANICAL PASS — {'; '.join(notes)}; "
              "manual gates (2, 3, 8, 9, 10) remain")
        return 0
    print("  VERDICT: MECHANICAL PASS — manual gates (2, 3, 8, 9, 10) remain")
    return 0


STATUS_RANK = {"DONE": 2, "PARTIAL": 1, "TODO": 0}


def parse_survey_items(text: str) -> dict[str, tuple[str, str]]:
    """{item id: (description, status)} — specstate.survey_items adapted to
    the dict shape converge diffs with (same `item <id>: "..."` / `status:`
    shape as check.py's survey-item template). Malformed/missing status
    reads as "unknown" rather than raising, since converge's job is to
    diff two possibly-messy snapshots, not to validate either one (that's
    check.py's job)."""
    return {i.id: (i.description, i.status) for i in survey_items(text)}


def mode_converge(spec_dir: Path, repo: Path, base: str | None) -> int:
    survey_p = spec_dir / "survey.md"
    new_text = survey_p.read_text(encoding="utf-8", errors="replace") if survey_p.exists() else ""
    if not git_available(repo):
        # Distinct from the no-committed-baseline case below: without a
        # repository there is nothing to converge against at all — listing
        # every item as a NEW GAP would be diff noise, not a finding.
        print(f"converge: {survey_p} vs {base or 'HEAD'} — SKIPPED (not a git repo): "
              "no git repository, so the survey has no committed history to converge against")
        return 0
    try:
        rel = str(survey_p.resolve().relative_to(repo.resolve()))
    except ValueError:
        rel = None
    old_text = ""
    if rel:
        r = git(repo, "show", f"{base or 'HEAD'}:{rel}")
        if r.returncode == 0:
            old_text = r.stdout
    old_items = parse_survey_items(old_text)
    new_items = parse_survey_items(new_text)
    added = sorted(i for i in new_items if i not in old_items)
    regressed = sorted(
        i for i in new_items if i in old_items
        and STATUS_RANK.get(new_items[i][1], -1) < STATUS_RANK.get(old_items[i][1], -1)
    )
    suffix = "" if rel and old_text else " (no committed baseline found — every item reads as new)"
    print(f"converge: {survey_p} vs {base or 'HEAD'}{suffix}")
    for i in added:
        desc, status = new_items[i]
        print(f"  NEW GAP    item {i}: \"{desc}\" — status {status} (not in previous survey)")
    for i in regressed:
        old_status, new_status = old_items[i][1], new_items[i][1]
        print(f"  REGRESSED  item {i}: \"{new_items[i][0]}\" — {old_status} -> {new_status} "
              "(re-check before trusting downstream docs)")
    if not added and not regressed:
        print("  no new gaps or regressions vs the previous survey")
    else:
        print(f"  {len(added) + len(regressed)} item(s) need a task appended "
              "(next free T-ID: check.py --next-ids), citing the FR each evidences")
    return 0


def mode_archived(repo: Path) -> int:
    """Every archived plan must be fully closed — task.md holds no
    unticked, unstruck entry (ticked `[x]` or struck `~~T###~~` both
    count as closed; the tick-commit node's contract, checked after the
    fact). The archive is the as-built record: an open box there means
    a plan was archived incomplete."""
    archive_root = repo / "specs" / "archive"
    if not archive_root.is_dir():
        print(f"archived: {archive_root} — no archive yet, nothing to verify")
        return 0
    bad = 0
    for d in sorted(p for p in archive_root.iterdir() if p.is_dir()):
        task_md = d / "task.md"
        if not task_md.exists():
            bad += 1
            print(f"  FAIL  {d.name}: no task.md — an archive without its plan")
            continue
        entries = task_entries(task_md.read_text(encoding="utf-8", errors="replace"))
        open_ids = [e.id or e.first_line.strip() for e in entries
                    if not e.done and not e.struck]
        if open_ids:
            bad += len(open_ids)
            noun = "entry" if len(open_ids) == 1 else "entries"
            print(f"  FAIL  {d.name}: open {noun} — {', '.join(open_ids)}")
        else:
            noun = "entry" if len(entries) == 1 else "entries"
            print(f"  PASS  {d.name}: {len(entries)} {noun} closed (ticked or struck)")
    if bad:
        print(f"archived: {bad} problem(s) — a plan was archived incomplete")
        return 1
    print("archived: every archived plan fully closed")
    return 0


def parse_args(argv: list[str]):
    if not argv:
        print(__doc__)
        return None
    mode = argv[0]
    if mode not in ("scope", "clean", "proofs", "mutate", "coverage", "dod",
                    "converge", "archived"):
        print(__doc__)
        return None
    repo = None
    base = None
    run = "--run" in argv
    dry = "--dry-run" in argv
    max_mutants = 40
    threshold = None
    rest = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--run":
            i += 1
        elif a == "--dry-run":
            i += 1
        elif a == "--repo":
            if i + 1 >= len(argv):
                return None
            repo = argv[i + 1]
            i += 2
        elif a == "--base":
            if i + 1 >= len(argv):
                return None
            base = argv[i + 1]
            i += 2
        elif a == "--max-mutants":
            if i + 1 >= len(argv) or not argv[i + 1].isdigit():
                return None
            max_mutants = int(argv[i + 1])
            i += 2
        elif a == "--threshold":
            if i + 1 >= len(argv) or not argv[i + 1].isdigit():
                return None
            threshold = int(argv[i + 1])
            i += 2
        else:
            rest.append(a)
            i += 1
    if mode in ("scope", "proofs", "mutate", "coverage", "dod",
                "converge") and len(rest) != 1:
        print(__doc__)
        return None
    if mode == "archived" and rest:
        print(__doc__)
        return None
    if mode == "clean" and len(rest) > 1:
        # One optional spec-dir positional is accepted and ignored — the
        # other audit subcommands all take it, and uniform invocation
        # should not be a usage error.
        print(__doc__)
        return None
    return (mode, (rest[0] if rest else None), repo, base, run, dry,
            max_mutants, threshold)


def main(argv: list[str] | None = None) -> int:
    # See check.py's main() for why argv is optional: in-process callers
    # (e.g. an orchestrator eval kernel) pass args directly; the CLI path
    # (argv=None) reads sys.argv unchanged.
    if argv is None:
        argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    parsed = parse_args(argv)
    if parsed is None:
        return 2
    (mode, spec_dir_s, repo_arg, base, run, dry,
     max_mutants, threshold) = parsed
    spec_dir = Path(spec_dir_s) if spec_dir_s else None
    if spec_dir is not None and not spec_dir.is_dir():
        print(f"FAIL: {spec_dir} is not a directory")
        return 1
    if mode in ("clean", "archived"):
        repo = Path(repo_arg) if repo_arg else Path(".")
    else:
        repo = Path(repo_arg) if repo_arg else spec_dir.parent.parent
    if mode == "scope":
        return mode_scope(spec_dir, repo, base)
    if mode == "clean":
        return mode_clean(repo, base)
    if mode == "archived":
        return mode_archived(repo)
    if mode == "mutate":
        return mode_mutate(spec_dir, repo, base, max_mutants)
    if mode == "coverage":
        return mode_coverage(spec_dir, repo, threshold)
    if mode == "dod":
        return mode_dod(spec_dir, repo, base, dry)
    if mode == "converge":
        return mode_converge(spec_dir, repo, base)
    return mode_proofs(spec_dir, repo, run)


if __name__ == "__main__":
    sys.exit(main())
