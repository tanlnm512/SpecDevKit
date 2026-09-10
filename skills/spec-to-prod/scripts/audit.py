#!/usr/bin/env python3
"""Closing-audit helpers for a spec-to-prod spec: the diff-facing halves of
SKILL.md's closing audit — scope diff, cleanliness sweep, TC proofs.

Usage: audit.py scope    <spec-dir> [--repo <path>] [--base <rev>]
       audit.py clean    [--repo <path>] [--base <rev>]
       audit.py proofs   <spec-dir> [--repo <path>] [--run]
       audit.py dod      <spec-dir> [--repo <path>] [--base <rev>]
       audit.py converge <spec-dir> [--repo <path>] [--base <rev>]
       audit.py -h | --help        (prints this text, exit 0)

(--repo defaults to the spec dir's grandparent: specs/<name>/ -> repo
root; clean, which takes no spec dir, defaults to .)

scope  — every file changed vs base (default: working tree vs HEAD, plus
         untracked files) is grep'd against the spec dir's task.md,
         tech-spec.md and plan.md. A changed path no doc mentions (full
         path, then bare filename) is listed as UNMENTIONED — a scope-creep
         candidate for the orchestrator to adjudicate, not a verdict:
         renames and generated files can be legitimate.
clean  — the diff's ADDED lines (plus untracked files' contents) scanned
         for debug prints, TODO/FIXME/XXX/HACK markers, and commented-out
         calls. Heuristic suspects for the orchestrator to adjudicate;
         spec-mandated logging is a ruling, not a finding.
proofs — each TC's Pass condition in test.md is classified auto (a
         runnable command) or manual (human observation) and listed; with
         --run, auto commands execute (cwd = repo root, 120s timeout
         each) and report PASS/FAIL with the command line for pasting
         into the audit. --run executes commands embedded in test.md —
         opt-in for the same reason you'd read a command before pasting
         it into a shell.
dod    — the Definition-of-Done scorecard (gates/dod.md): runs
         check.py, live TC proofs, and the scope/hygiene counts in one
         pass; mechanical gates print PASS/FAIL, judgment gates print
         MANUAL for the orchestrator to satisfy. Like proofs --run, dod
         executes the TC commands embedded in test.md.
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

Exit:  0 = report produced (scope/clean/converge always; proofs without
       --run) · proofs --run / dod: 0 = every mechanical gate green,
       1 = any FAILED or errored · 2 = usage error.

Non-git repos: git-derived output degrades explicitly, never silently —
scope/clean print `SKIPPED (not a git repo)` instead of a false all-clear
(an empty diff is not a clean tree), converge reports the missing
repository rather than a phantom baseline, and dod's git-derived gates
read SKIPPED.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

# Shared doc-state parsers live in specstate.py beside this script — one
# canonical regex per doc shape, shared with check.py and graph.py. The
# scripts dir goes on sys.path locally (no install step): tests load this
# file by path via importlib, which does not put scripts/ on sys.path.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from specstate import survey_items, task_entries  # noqa: E402 - the sys.path setup above runs first

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
    plan's work sits uncommitted until the closing audit's single commit."""
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


def scope_data(spec_dir: Path, repo: Path, base: str | None) -> tuple[list[str], list[str]]:
    """(changed paths, unmentioned subset) — shared by scope and dod."""
    docs = ""
    for f in ("task.md", "tech-spec.md", "plan.md"):
        p = spec_dir / f
        if p.exists():
            docs += p.read_text(encoding="utf-8", errors="replace") + "\n"
    paths = [p for p in changed_paths(repo, base) if not p.startswith("specs/")]
    unmentioned = [
        p for p in paths
        if p not in docs and Path(p).name not in docs
    ]
    return paths, unmentioned


def mode_scope(spec_dir: Path, repo: Path, base: str | None) -> int:
    if not git_available(repo):
        print("scope: SKIPPED (not a git repo) — no scope verdict")
        return 0
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
    for path, ln, text in added_lines(repo, base):
        if path.startswith("specs/"):
            continue  # the docs are the intent, not the debris surface
        if DEBUG.search(text):
            finds.append((path, ln, "debug print", text.strip()))
        elif MARKER.search(text):
            finds.append((path, ln, "marker", text.strip()))
        elif COMMENTED_CALL.match(text):
            finds.append((path, ln, "commented-out call", text.strip()))
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
        print("  no debug prints, markers, or commented-out calls in added lines")
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


def proofs_data(spec_dir: Path, repo: Path, run: bool) -> dict:
    """Classify every TC's pass condition; execute the auto ones when run.
    {"auto": [(tc, cmd)], "manual": [(tc, note)], "ok": {tc: (passed,
    summary)}, "errors": [(tc, cmd, err)], "failed": n} — ok/errors/failed
    stay empty/zero on a dry run. Shared by proofs and dod."""
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
    data = {"auto": auto, "manual": manual, "ok": {}, "errors": [], "failed": 0}
    if not run:
        return data
    for tc, cmd in auto:
        try:
            r = subprocess.run(
                cmd, shell=True, cwd=str(repo), timeout=120,
                capture_output=True, text=True,
            )
            ok = r.returncode == 0
            summary = (r.stdout.strip().splitlines() or [""])[-1]
        except subprocess.TimeoutExpired:
            ok, summary = False, "(timeout after 120s)"
        except OSError as e:
            data["errors"].append((tc, cmd, str(e)))
            data["failed"] += 1
            continue
        data["ok"][tc] = (ok, summary[:100])
        if not ok:
            data["failed"] += 1
    return data


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
    errs = {tc: e for tc, _, e in d["errors"]}
    for tc, cmd in auto:
        if tc in d["ok"]:
            ok, summary = d["ok"][tc]
            print(f"  {'PASS' if ok else 'FAIL'}  {tc}  {cmd}  ->  {summary}")
        else:
            print(f"  ERROR   {tc}  {cmd}  ({errs[tc]})")
    return 1 if d["failed"] else 0


def mode_dod(spec_dir: Path, repo: Path, base: str | None) -> int:
    """The DoD scorecard: mechanical gates measured, judgment gates MANUAL.
    Runs check.py, live proofs, and the scope/hygiene counts — the same
    trust level as the closing audit itself (it executes TC commands)."""
    # gate 4 — task.md completeness (specstate.task_entries, the same
    # shared parser check.py reads the docset with)
    task_p = spec_dir / "task.md"
    task = task_p.read_text(encoding="utf-8", errors="replace") if task_p.exists() else ""
    entries = task_entries(task)
    total = len(entries)
    done = sum(1 for e in entries if e.done)
    inprog = sum(1 for e in entries if e.claimed)
    # gate 5 — check.py (sibling script; WARNs don't fail, ownership is a
    # judgment the detail line reminds the orchestrator of)
    check = Path(__file__).resolve().parent / "check.py"
    cp = subprocess.run([sys.executable, str(check), str(spec_dir)],
                        capture_output=True, text=True)
    nfail = len(re.findall(r"^  FAIL  ", cp.stdout, flags=re.M))
    mw = re.search(r"\((\d+) fail, (\d+) warn\)", cp.stdout)
    nwarn = int(mw.group(2)) if mw else 0
    # gates 1-2 — proofs, live
    pr = proofs_data(spec_dir, repo, True)
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

    gates = [
        (1, "PROOF auto", "PASS" if pr["failed"] == 0 else "FAIL",
         f"{nauto - pr['failed']}/{nauto} TCs green" if nauto else "no auto TCs (n/a)"),
        (2, "PROOF manual", "MANUAL",
         f"{len(pr['manual'])} observation TC(s) — record each result"),
        (3, "REGRESSION", "MANUAL", "run the repo suite; paste exit-0 output"),
        (4, "COMPLETENESS",
         "PASS" if total and done == total and not inprog else "FAIL",
         f"{done}/{total} ticked, {inprog} in-progress"),
        (5, "CONTRACT", "PASS" if nfail == 0 else "FAIL",
         f"check.py: {nfail} fail, {nwarn} warn (each WARN fixed or ruled)"),
        (6, "SCOPE", scope_st, scope_dt),
        (7, "HYGIENE", hyg_st, hyg_dt),
        (8, "REVIEW", "MANUAL",
         "reviewer BLOCKs = 0; WARN/NIT fixed or parked-with-ruling"),
        (9, "RULINGS", "MANUAL",
         "every D-### surfaced in the closing report"),
        (10, "SIGN-OFF", "MANUAL", "user acks the rulings report"),
    ]
    print(f"dod: {spec_dir} — gate table in gates/dod.md")
    for num, name, st, detail in gates:
        print(f"  {num:>2} {name:<13} {st:<7} {detail}")
    bad = [str(n) for n, _, st, _ in gates if st == "FAIL"]
    if bad:
        print(f"  VERDICT: MECHANICAL FAIL — gate(s) {', '.join(bad)}; manual gates remain")
        return 1
    skipped = [str(n) for n, _, st, _ in gates if st == "SKIPPED"]
    if skipped:
        print(f"  VERDICT: MECHANICAL PASS — git gates {', '.join(skipped)} "
              "SKIPPED (not a git repo); manual gates (2, 3, 8, 9, 10) remain")
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


def parse_args(argv: list[str]):
    if not argv:
        print(__doc__)
        return None
    mode = argv[0]
    if mode not in ("scope", "clean", "proofs", "dod", "converge"):
        print(__doc__)
        return None
    repo = None
    base = None
    run = "--run" in argv
    rest = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--run":
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
        else:
            rest.append(a)
            i += 1
    if mode in ("scope", "proofs", "dod", "converge") and len(rest) != 1:
        print(__doc__)
        return None
    if mode == "clean" and rest:
        print(__doc__)
        return None
    return mode, (rest[0] if rest else None), repo, base, run


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
    mode, spec_dir_s, repo_arg, base, run = parsed
    spec_dir = Path(spec_dir_s) if spec_dir_s else None
    if spec_dir is not None and not spec_dir.is_dir():
        print(f"FAIL: {spec_dir} is not a directory")
        return 1
    if mode == "clean":
        repo = Path(repo_arg) if repo_arg else Path(".")
    else:
        repo = Path(repo_arg) if repo_arg else spec_dir.parent.parent
    if mode == "scope":
        return mode_scope(spec_dir, repo, base)
    if mode == "clean":
        return mode_clean(repo, base)
    if mode == "dod":
        return mode_dod(spec_dir, repo, base)
    if mode == "converge":
        return mode_converge(spec_dir, repo, base)
    return mode_proofs(spec_dir, repo, run)


if __name__ == "__main__":
    sys.exit(main())
