#!/usr/bin/env python3
"""Shared review-state oracle for spec-review.

One stdlib home for: target
resolution (diff/branch/pr/project), the mechanical gate, project-file
sharding, finding-ID allocation, carried-findings parsing, and report
markdown assembly.

Contract: every subcommand prints ONE JSON object; success
is {"status": "ok", ...} exit 0, failure is {"status": "error",
"error": ...} exit 1 — a workflow never proceeds on missing state.

Usage:
  review_orchestrator.py scope   --target diff|branch|pr|project
                                [--base REF] [--pr SPEC] [--repo DIR]
                                [--paths TERMS] [--include-gate]
  review_orchestrator.py gate    [--repo DIR] [--base REF] [--tree] [--pr SPEC]
  review_orchestrator.py run-init  --target … (scope's args) [--keep N]
  review_orchestrator.py run-save  --run-dir D --stage S --data @FILE|STR
  review_orchestrator.py run-resume --run-dir D
  review_orchestrator.py run-gc    [--repo DIR] [--keep N]
  review_orchestrator.py shard   --files-json LIST [--budget N] [--max-files N]
  review_orchestrator.py id-next --prefix P --used N
  review_orchestrator.py handshake --role ROLE (--file PATH | --text STR)
  review_orchestrator.py findings-parse (--role ROLE | --saved-report)
                                (--file PATH | --text STR)
  review_orchestrator.py report  --kind review|fix --data @FILE|STR
  review_orchestrator.py systems                        (confirm/verify = brief bodies from agents/)
  review_orchestrator.py ask     --kind KIND --ctx @FILE|JSON   (ctx {"batch": [...]} renders a wave)

No reply is read before its capability handshake: every reply opens with
`tools: <the tools it actually holds>`, and ROLE (a brief in agents/,
without its spec-review- prefix) requires every tool on that brief's
`tools:` line. `handshake` returns {tools, reply} — the reply past its
tools line — and `findings-parse --role ROLE` runs the same gate ahead
of the parse. `findings-parse --saved-report` reads the fix_from input,
a saved report, which never opens with a tools report; handed neither,
it refuses naming both. A short or missing report, a reply declared a
saved report, or an undeclared payload is {"status": "error", "stage":
"handshake"}: a failed call to run again, never a finding or a round.

run-init / run-save / run-resume checkpoint a review run into
<repo>/.spec-review/runs/<run-id>/ (D-020): run-init records the
target's fingerprint (the exact diff + untracked files scope lists)
after scope ran; run-save stores one stage's JSON (the stage names are
the STAGES tuple); run-resume re-computes the fingerprint and either
returns {completed, next, data} — continue at `next` — or refuses: a
changed target never resumes. The folder carries its own .gitignore
containing `*`, so runs are never committed.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from gate_helpers import GIT_DIFF, diff_changes, git_diff

SKILL_DIR = Path(__file__).resolve().parent.parent
GATE_SH = SKILL_DIR / "scripts" / "gate.sh"

FAST_MAX_LINES = 400
FAST_MAX_FILES = 5
SUGGEST_SPLIT_LINES = 1000
SUGGEST_SPLIT_FILES = 20
SHARD_TARGET_BYTES = 240000
SHARD_MAX_FILES = 32
PROJECT_CONFIRM_PARTS = 3
EXCLUDED_LISTED_MAX = 50
SEV_RANK = {"high": 0, "medium": 1, "low": 2}

CODE_EXTENSIONS = [
    "bash", "c", "cc", "clj", "cljs", "cmake", "cpp", "cs", "css", "cxx", "dart",
    "d", "edn", "el", "elm", "erl", "ex", "exs", "fish", "go", "gradle", "groovy",
    "graphql", "h", "hh", "hpp", "hs", "html", "hrl", "java", "js", "json", "jsx",
    "kt", "kts", "less", "lua", "m", "ml", "mli", "mm", "nim", "php", "pl", "pm",
    "proto", "ps1", "py", "pyi", "r", "rb", "rs", "sass", "scala", "scss", "sh",
    "sql", "svelte", "swift", "tf", "toml", "ts", "tsx", "vue", "yaml", "yml",
    "zig", "zsh",
]
CODE_BASENAMES = [
    "Makefile", "Dockerfile", "CMakeLists.txt", "Rakefile", "Gemfile",
    "Justfile", "Podfile", "Vagrantfile", "Brewfile",
]
EXCLUDED_BASENAMES = [
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock",
    "poetry.lock", "Pipfile.lock", "uv.lock", "go.sum", "composer.lock",
    "Gemfile.lock",
]
EXCLUDED_DIRS = {
    "vendor", "third_party", "external", "node_modules", "dist",
    "__snapshots__", ".venv", "venv",
}
NOISE_DIRS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".cache",
    "node_modules", ".venv", "venv",
}
CI_STATUS = {"pass": "pass", "fail": "fail", "pending": "pending", "skipping": "skipped"}
# A red CI row classed infrastructure or unknown stands without failing
# the gate (D-023) — it is carried to the report and floors merge at human.
CI_STANDING = ("infrastructure", "unknown")
# The runner's own setup or wrap-up steps — exact names, then name
# prefixes. Narrow on purpose: `Set up Node` is a project step, and a
# failed project step is a code failure however fast it ran. This
# constant and the three functions below are duplicated byte-for-byte
# in ship.py and pinned identical by tools/tests.
RUNNER_STEPS = (("Set up job", "Complete job"),
                ("actions/checkout@", "Post "))
BACKLOG = Path("specs") / "BACKLOG.md"
SEVERITY_LADDER = ("Severity: high = data loss, crash, wrong result, or security compromise; "
                   "medium = a real defect the author should fix; low = minor.")


def out(ok, **payload):
    doc = {"status": "ok" if ok else "error"}
    doc.update(payload)
    print(json.dumps(doc))
    return 0 if ok else 1


def git(args, repo):
    cmd = ["git"] + (["-C", str(repo)] if repo else []) + args
    return subprocess.run(cmd, capture_output=True, text=True)


def git_out(args, repo):
    r = git(args, repo)
    return r.stdout if r.returncode == 0 else None


# --- source-file targeting --------------

def is_excluded_source(path):
    base = path.rsplit("/", 1)[-1]
    if base in EXCLUDED_BASENAMES:
        return True
    if base.endswith((".d.ts", ".min.js", ".min.css", ".pb.go")) or base.endswith("_pb2.py"):
        return True
    return any(seg in EXCLUDED_DIRS for seg in path.split("/")[:-1])


def is_source_file(path):
    base = path.rsplit("/", 1)[-1]
    if base in CODE_BASENAMES:
        return True
    dot = base.rfind(".")
    if dot <= 0:
        return False
    return base[dot + 1:].lower() in CODE_EXTENSIONS


def matches_path_filter(path, terms):
    return not terms or any(path == t or path.startswith(t + "/") for t in terms)


# --- scope -------------------------------------------------------------------

def resolve_repo(repo_arg):
    if not repo_arg:
        return None
    r = git(["rev-parse", "--show-toplevel"], repo_arg)
    return r.stdout.strip() if r.returncode == 0 else None


def read_text_bytes(path):
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return None if b"\0" in data[:8192] else data


def text_line_count(path):
    data = read_text_bytes(path)
    return len(data.splitlines()) if data is not None else 0


def is_noise_untracked(rel, root):
    return (rel.endswith((".pyc", ".pyo"))
            or any(seg in NOISE_DIRS for seg in rel.split("/")[:-1])
            or read_text_bytes(root / rel) is None)


def diff_scope(base, repo):
    porcelain = git_out(["status", "--porcelain"], repo) or ""
    numstat = git_out(["diff", "--numstat", base], repo) or ""
    files, added = [], 0
    for line in numstat.splitlines():
        cols = line.split("\t")
        if len(cols) < 3 or not cols[2].strip():
            continue
        files.append("\t".join(cols[2:]).strip())
        try:
            added += int(cols[0])
        except ValueError:
            pass
    # `git diff` never shows untracked files, yet they are part of the change.
    listed = git_out(["ls-files", "--others", "--exclude-standard", "--full-name", "-z", "--", ":/"], repo) or ""
    root = Path(repo) if repo else Path(git_out(["rev-parse", "--show-toplevel"], repo).strip())
    candidates = [f for f in listed.split("\0") if f and f not in files]
    skipped = [f for f in candidates if is_noise_untracked(f, root)]
    untracked = [f for f in candidates if f not in skipped]
    added += sum(text_line_count(root / f) for f in untracked)
    return {"clean": porcelain.strip() == "", "files": files + untracked,
            "untracked": untracked, "untracked_skipped": [f for f in skipped if is_source_file(f)],
            "added": added}


def detect_base_branch(explicit, repo):
    if explicit:
        for cand in (f"origin/{explicit}", explicit):
            if git(["rev-parse", "-q", "--verify", cand], repo).returncode == 0:
                return cand
        return ""
    head = git_out(["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"], repo) or ""
    cands = ([head] if head else []) + ["origin/main", "main", "origin/master", "master"]
    for cand in cands:
        if cand and git(["rev-parse", "-q", "--verify", cand], repo).returncode == 0:
            return cand
    return ""


def pr_meta(pr_spec, repo):
    r = subprocess.run(
        ["gh", "pr", "view", pr_spec, "--json",
         "number,title,author,baseRefName,baseRefOid,headRefName,headRefOid,state,url,body,"
         "isCrossRepository"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None
    try:
        j = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(j, dict) or not j.get("headRefOid"):
        return None
    body = re.sub(r"\s+", " ", j.get("body") or "").strip()
    author = j.get("author") or {}
    return {
        "number": j.get("number") if isinstance(j.get("number"), int) else 0,
        "title": re.sub(r"\s+", " ", j.get("title") or "").strip(),
        "author": author.get("login") if isinstance(author, dict) else "unknown",
        "state": j.get("state") if isinstance(j.get("state"), str) else "UNKNOWN",
        "url": j.get("url") if isinstance(j.get("url"), str) else "",
        "baseRefName": j.get("baseRefName") if isinstance(j.get("baseRefName"), str) else "",
        "baseRefOid": j.get("baseRefOid") if isinstance(j.get("baseRefOid"), str) else "",
        "headRefName": j.get("headRefName") if isinstance(j.get("headRefName"), str) else "",
        "headRefOid": j["headRefOid"],
        "fork": j.get("isCrossRepository") is True,
        "body": body[:1200] + "..." if len(body) > 1200 else body,
    }


def merge_base_with_count(ref, repo):
    mb = git_out(["merge-base", "HEAD", ref], repo)
    if mb is None or not mb.strip():
        return None
    sha = mb.strip()
    cnt = git_out(["rev-list", "--count", f"{sha}..HEAD"], repo) or "0"
    try:
        count = int(cnt.strip())
    except ValueError:
        count = 0
    return {"sha": sha, "count": count}


def project_files(paths_arg, repo):
    listed = git_out(["ls-files"], repo)
    if listed is None:
        return None
    all_files = [s.strip() for s in listed.splitlines() if s.strip()]
    if not all_files:
        return {"files": [], "sizes": {}, "candidates": 0}
    sizes = {}
    for f in all_files:
        p = (Path(repo) / f) if repo else Path(f)
        try:
            sizes[f] = p.stat().st_size
        except OSError:
            sizes[f] = 0
    terms = [t for t in re.split(r"[\s,]+", paths_arg or "") if t]
    in_scope = [p for p in all_files if is_source_file(p) and matches_path_filter(p, terms)]
    candidates = [p for p in in_scope if not is_excluded_source(p)]
    excluded = [p for p in in_scope if is_excluded_source(p)]
    ordered = sorted(candidates, key=lambda p: (-(sizes.get(p, 0)), p))
    return {"files": ordered, "sizes": sizes, "candidates": len(candidates),
            "excluded": excluded[:EXCLUDED_LISTED_MAX], "excluded_count": len(excluded)}


def shard_files(files, sizes, budget=SHARD_TARGET_BYTES, max_files=SHARD_MAX_FILES):
    parts, cur, cur_bytes = [], [], 0
    for f in sorted(files):
        b = sizes.get(f, 0)
        if cur and (cur_bytes + b > budget or len(cur) >= max_files):
            parts.append(cur)
            cur, cur_bytes = [], 0
        cur.append(f)
        cur_bytes += b
    if cur:
        if parts and cur_bytes <= budget / 4:
            parts[-1].extend(cur)
        else:
            parts.append(cur)
    return parts


def part_label(files):
    counts = {}
    for f in files:
        segs = f.split("/")
        key = "/".join(segs[:2]) if len(segs) >= 2 else segs[0]
        counts[key] = counts.get(key, 0) + 1
    return max(counts, key=counts.get) if counts else ""


def gate_rows(repo, base, tree):
    cmd = ["bash", str(GATE_SH)]
    if repo:
        cmd += ["--repo", str(repo)]
    cmd += ["--tree"] if tree else ["--base", base or "HEAD"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        parsed = json.loads(r.stdout)
    except json.JSONDecodeError:
        parsed = None
    if not isinstance(parsed, list):
        return [{"name": "gate.sh (spec-review)", "exit_code": 1,
                 "tail": "gate.sh produced no JSON report"}]
    return [{"name": g.get("name", ""), "exit_code": g.get("exit_code", 0),
             "status": g.get("status", ""), "source": g.get("source", "repo"),
             "tail": g.get("tail", "")} for g in parsed]


def is_runner_step(name):
    exact, prefixes = RUNNER_STEPS
    return isinstance(name, str) and (name in exact or name.startswith(prefixes))


def first_failed_step(steps):
    """The lowest-numbered step that neither succeeded nor was skipped."""
    if not isinstance(steps, list):
        return None
    failed = [s for s in steps if isinstance(s, dict)
              and s.get("conclusion") not in ("success", "skipped")]
    return min(failed, key=lambda s: s.get("number")
               if isinstance(s.get("number"), int) else 0, default=None)


def classify_check(bucket, check_name, jobs):
    """(class, failedStep, reason) for a red `gh pr checks` row.

    bucket is the row's bucket; check_name its name; jobs the run's jobs
    as `gh run view <id> --json jobs` reports them — None when no run
    sits behind the status or gh could not be read (a status context
    from a CI outside Actions), [] when it lists none. Evidence order,
    first hit wins: cancelled or never started → infrastructure; a
    first failed step that is the runner's own → infrastructure; any
    other failed step → code; no step evidence at all → unknown. Never
    how fast the job failed and never log text: a real test can print
    `connection reset` or `context deadline exceeded`.
    """
    if bucket == "cancel":
        return ("infrastructure", None,
                "the run was cancelled — the runner stopped it, "
                "no step verdict exists")
    if jobs is None:
        return ("unknown", None,
                "no step data behind the status — the run could not be "
                "read, or the check comes from a CI outside Actions")
    if not jobs:
        return ("infrastructure", None, "the run lists no jobs — it never started")
    candidates = [j for j in jobs if isinstance(j, dict)
                  and j.get("name") == check_name]
    if not candidates:
        candidates = [j for j in jobs if isinstance(j, dict)
                      and j.get("conclusion") not in (None, "success",
                                                      "skipped", "neutral")]
    judged = []
    for job in candidates:
        steps = job.get("steps")
        if not isinstance(steps, list):
            steps = None
        judged.append((job, steps, first_failed_step(steps)))
    if judged and all(steps == [] for _, steps, _ in judged):
        return ("infrastructure", None,
                "the job lists no steps — it never started")
    failed = [(job, step) for job, _, step in judged if step]
    if not failed:
        return ("unknown", None,
                "no failed step stands behind the red status — nothing to class")
    project = [(job, step) for job, step in failed
               if not is_runner_step(step.get("name"))]
    if project:
        job, step = project[0]
        return ("code", step.get("name"),
                f"the job '{job.get('name')}' failed in its project step "
                f"'{step.get('name')}'")
    job, step = failed[0]
    return ("infrastructure", step.get("name"),
            f"the job '{job.get('name')}' failed in the runner step "
            f"'{step.get('name')}'")


RUN_ID = re.compile(r"/actions/runs/(\d+)")


def run_jobs(link, repo):
    """A check row's run jobs (`gh run view <id> --json jobs`), or None
    when the link names no run or gh cannot serve the shape."""
    m = RUN_ID.search(link or "")
    if not m:
        return None
    r = subprocess.run(["gh", "run", "view", m.group(1), "--json", "jobs"],
                       capture_output=True, text=True, cwd=repo or None)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    jobs = data.get("jobs") if isinstance(data, dict) else None
    return jobs if isinstance(jobs, list) else None


def ci_rows(pr_spec, repo):
    """The PR's CI checks as gate rows (`source: ci`). A code-class red row
    fails the gate like any check; an infrastructure or unknown red row
    (a cancelled run, a runner setup/wrap-up failure, no step data behind
    the status — D-023) does not fail the gate and does not stop the
    reviewers, but stands with its class, reason and (infrastructure)
    rerun command — never green-washed."""
    if not shutil.which("gh"):
        return []
    r = subprocess.run(["gh", "pr", "checks", pr_spec, "--json", "name,bucket,link"],
                       capture_output=True, text=True, cwd=repo or None)
    try:
        checks = json.loads(r.stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(checks, list):
        return []
    rows = []
    for c in checks:
        if not isinstance(c, dict):
            continue
        bucket = c.get("bucket")
        name = c.get("name", "?")
        row = {"name": f"CI: {name}", "exit_code": 0,
               "status": CI_STATUS.get(bucket, "pending"), "source": "ci",
               "tail": c.get("link") or "",
               "class": None, "failedStep": None, "reason": None}
        if bucket in ("fail", "cancel"):
            row["class"], row["failedStep"], row["reason"] = classify_check(
                bucket, name, run_jobs(c.get("link"), repo))
            if row["class"] == "code":
                row["exit_code"], row["status"] = 1, "fail"
            else:
                row["status"] = row["class"]
                if row["class"] == "infrastructure":
                    m = RUN_ID.search(c.get("link") or "")
                    row["rerun"] = f"gh run rerun {m.group(1)} --failed" if m else None
        rows.append(row)
    return rows


def is_repo_row(row):
    return row.get("source", "repo") == "repo"


def is_info_row(row):
    return row.get("status") == "info"


def failed_label(row):
    return row["name"] + (" (timed out)" if row.get("status") == "timed_out" else "")


def gate_summary(rows):
    repo_rows = [g for g in rows if is_repo_row(g)]
    ci = [g for g in rows if g.get("source") == "ci"]
    builtin = [g for g in rows if g.get("source") == "builtin" and not is_info_row(g)]
    note = gate_note(repo_rows, builtin) + ci_note(ci) + "".join(
        f"; {g['name']} — name every new or changed dependency in the report" for g in rows if is_info_row(g))
    return {"rows": rows, "green": all(g["exit_code"] == 0 for g in rows),
            "repo_checks": len(repo_rows), "note": note}


def ci_note(ci):
    if not ci:
        return ""
    failed = [g["name"] for g in ci if g["exit_code"] != 0]
    standing = [g["name"] for g in ci if g.get("class") in CI_STANDING]
    pending = [g["name"] for g in ci if g.get("status") == "pending"]
    if failed:
        part = "; the PR's CI did NOT pass — failing: " + "; ".join(failed) + " (each a gate finding)"
    else:
        part = f"; the PR's CI checks ({len(ci)}) did not fail"
    if standing:
        part += ("; standing red, not failing the gate: " + "; ".join(standing)
                 + " (infrastructure or unknown — carried to the report, "
                   "merge floors at human until they clear)")
    return part + ("; still pending: " + "; ".join(pending) if pending else "")


def gate_note(repo_rows, builtin):
    # Built-in rows (bash -n, secret scan) are hygiene, never the floor.
    failed_builtin = [failed_label(g) for g in builtin if g["exit_code"] != 0]
    builtin_part = ""
    if failed_builtin:
        builtin_part = ("; the built-in checks did NOT all pass — failing: "
                        + "; ".join(failed_builtin) + " (each failure is recorded as a gate finding)")
    elif builtin:
        builtin_part = "; the built-in checks (" + "; ".join(g["name"] for g in builtin) + ") passed"
    if not repo_rows:
        return ("No repo checks were detected by the gate — this review has no mechanical floor "
                "(no tests, build or lint of the repo's own ran); the report must say so under "
                "notCovered" + builtin_part)
    failed = [failed_label(g) for g in repo_rows if g["exit_code"] != 0]
    if not failed:
        return ("The repo's own checks the gate detected ("
                + "; ".join(g["name"] for g in repo_rows) + ") all passed" + builtin_part)
    return ("The repo's own checks the gate detected did NOT all pass — failing: "
            + "; ".join(failed) + " (each failure is recorded as a gate finding)" + builtin_part)


def stage_err(stage, **extra):
    doc = {"status": "error", "stage": stage}
    doc.update(extra)
    print(json.dumps(doc))
    return 1


def _scope_result(a) -> tuple[bool, dict]:
    """The scope resolution shared by the scope command and run-init —
    (ok, result-or-error-doc); the caller prints. On error the doc
    carries `stage` like stage_err's output."""
    repo_abs = resolve_repo(a.repo)
    result = {"target": a.target, "repo_abs": repo_abs, "base": a.base or "HEAD"}
    if a.target == "diff":
        if git(["rev-parse", "-q", "--verify", a.base or "HEAD"], repo_abs).returncode != 0:
            return False, {"stage": "base-unresolved", "base": a.base or "HEAD"}
        result.update(diff_scope(a.base or "HEAD", repo_abs))
        result["mode"] = "diff"
    elif a.target == "branch":
        base_ref = detect_base_branch(a.base, repo_abs)
        if not base_ref:
            return False, {"stage": "branch-no-base"}
        mb = merge_base_with_count(base_ref, repo_abs)
        if mb is None:
            return False, {"stage": "branch-merge-base", "base": base_ref}
        sc = diff_scope(mb["sha"], repo_abs)
        result.update({"mode": "branch", "base": base_ref, "merge_base": mb["sha"],
                       "commit_count": mb["count"], **sc})
    elif a.target == "pr":
        if not a.pr:
            return False, {"stage": "pr-no-arg"}
        meta = pr_meta(a.pr, repo_abs)
        if meta is None:
            return False, {"stage": "pr-view", "pr": a.pr}
        head = git_out(["rev-parse", "HEAD"], repo_abs) or ""
        if not head.strip():
            return False, {"stage": "pr-state"}
        dirty = (git_out(["status", "--porcelain"], repo_abs) or "").strip() != ""
        if head.strip() != meta["headRefOid"]:
            # The refusal is unconditional: a dirty tree misattributes
            # uncommitted work to the PR either way.
            if dirty:
                return False, {"stage": "pr-dirty", "head_matches": False,
                               "head": head.strip()}
            prev = head.strip()
            prev_ref = (git_out(["symbolic-ref", "-q", "--short", "HEAD"], repo_abs) or "").strip()
            co = subprocess.run(["gh", "pr", "checkout", a.pr], capture_output=True, text=True)
            head = git_out(["rev-parse", "HEAD"], repo_abs) or ""
            if co.returncode != 0 or head.strip() != meta["headRefOid"]:
                return False, {"stage": "pr-checkout"}
            result["previous_head"] = prev
            result["previous_ref"] = prev_ref or prev
        elif dirty:
            return False, {"stage": "pr-dirty", "head_matches": True,
                           "head": head.strip()}
        mb = merge_base_with_count(meta["baseRefOid"], repo_abs)
        if mb is None:
            return False, {"stage": "pr-merge-base", "base": meta["baseRefOid"]}
        sc = diff_scope(mb["sha"], repo_abs)
        result.update({"mode": "pr", "pr": meta, "merge_base": mb["sha"],
                       "checked_out_head": head.strip(), **sc})
    elif a.target == "project":
        pf = project_files(a.paths, repo_abs)
        if pf is None:
            return False, {"stage": "ls-files"}
        parts = shard_files(pf["files"], pf["sizes"])
        result.update({"mode": "project", "files": pf["files"], "sizes": pf["sizes"],
                       "candidates": pf["candidates"], "parts": parts,
                       "part_labels": [part_label(p) for p in parts],
                       "excluded": pf["excluded"], "excluded_count": pf["excluded_count"],
                       "reviewer_spawns": len(parts) * len(LENSES),
                       "confirm_before_spawn": len(parts) > PROJECT_CONFIRM_PARTS})
    else:
        return False, {"stage": "target-unknown", "target": a.target}
    result["suggest_split"] = bool(
        result.get("added", 0) > SUGGEST_SPLIT_LINES
        or len(result.get("files", [])) > SUGGEST_SPLIT_FILES
    )
    result["fast_mode_default"] = bool(
        result.get("added", 0) <= FAST_MAX_LINES and len(result.get("files", [])) <= FAST_MAX_FILES
    )
    gate_base = result.get("merge_base") or result.get("base") or "HEAD"
    if a.include_gate and result.get("pr", {}).get("fork"):
        # The gate executes the checked-out code; a fork's code needs the user's go-ahead.
        result["gate_deferred"] = ("fork PR: the gate would run the PR author's code — confirm with "
                                   f"the user, then run `gate --base {gate_base}`")
    elif a.include_gate:
        rows = gate_rows(repo_abs, gate_base, a.target == "project")
        result["gate"] = gate_summary(rows + (ci_rows(a.pr, repo_abs) if a.target == "pr" else []))
    return True, result


def cmd_scope(a):
    ok, result = _scope_result(a)
    return out(ok, **result)


def cmd_gate(a):
    repo_abs = resolve_repo(a.repo)
    rows = gate_rows(repo_abs, a.base or "HEAD", a.tree)
    return out(True, **gate_summary(rows + (ci_rows(a.pr, repo_abs) if a.pr else [])))


TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs)/|(^|/)test_[^/]*$|_test\.[^/]+$|"
                       r"\.(test|spec)\.[^/]+$|Tests?\.[^/.]+$")
REMOVED_ASSERT = re.compile(r"\bassert|\bexpect\(|\.should\b|\bt\.(Error|Fatal)|\brequire\.")
ADDED_SKIP = re.compile(r"\bskip(If|Unless)?\b|\.skip\(|\bxfail\b|\bx(it|describe|test)\(|@Disabled|"
                        r"@Ignore|\bt\.Skip|#\[ignore\]|\.only\(")


def stash_count(repo):
    return len((git_out(["stash", "list"], repo) or "").splitlines())


def working_tree_sha(repo):
    """Tree of the whole working tree, untracked files included, built in a scratch index so the
    real index and the stash list stay untouched (`stash create` omits untracked files)."""
    index_path = (git_out(["rev-parse", "--git-path", "index"], repo) or "").strip()
    if index_path and repo:
        index_path = os.path.join(str(repo), index_path)
    with tempfile.TemporaryDirectory(prefix="fix-snapshot-") as scratch:
        scratch_index = os.path.join(scratch, "index")
        if index_path and os.path.exists(index_path):
            shutil.copyfile(index_path, scratch_index)
        env = {**os.environ, "GIT_INDEX_FILE": scratch_index}
        base = ["git"] + (["-C", str(repo)] if repo else [])
        if subprocess.run(base + ["add", "-A"], env=env, capture_output=True).returncode:
            return None
        r = subprocess.run(base + ["write-tree"], env=env, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def cmd_fix_snapshot(a):
    repo_abs = resolve_repo(a.repo)
    head = (git_out(["rev-parse", "HEAD"], repo_abs) or "").strip()
    if not head:
        return out(False, error="cannot resolve HEAD")
    tree = working_tree_sha(repo_abs)
    if not tree:
        return out(False, error="cannot snapshot the working tree")
    return out(True, head=head, stash_count=stash_count(repo_abs), tree=tree)


def test_weakening(diff_text):
    hunks = {}
    for path, sign, _, text in diff_changes(diff_text):
        if not TEST_PATH.search(path):
            continue
        hunk = hunks.setdefault(path, {"path": path, "removed_asserts": [], "added_skips": []})
        if sign == "-" and REMOVED_ASSERT.search(text):
            hunk["removed_asserts"].append(text.strip())
        elif sign == "+" and ADDED_SKIP.search(text):
            hunk["added_skips"].append(text.strip())
    return [h for h in hunks.values() if h["removed_asserts"] or h["added_skips"]]


def cmd_fix_check(a):
    repo_abs = resolve_repo(a.repo)
    head = (git_out(["rev-parse", "HEAD"], repo_abs) or "").strip()
    stashes = stash_count(repo_abs)
    if head != a.head:
        return stage_err("fixer-moved-head", expected=a.head, head=head,
                         error="HEAD moved during the fix round — the fixer committed, reset or "
                               "switched branches; abort the loop and report it")
    if stashes != a.stash_count:
        return stage_err("fixer-touched-stash", expected=a.stash_count, stash_count=stashes,
                         error="the stash list changed during the fix round; abort the loop and report it")
    now = working_tree_sha(repo_abs)
    if not now:
        return out(False, error="cannot snapshot the working tree")
    diff = git_diff(repo_abs, a.tree, now)
    return out(True, head=head, stash_count=stashes, test_hunks=test_weakening(diff))


def cmd_shard(a):
    try:
        files = json.loads(a.files_json)
        sizes = json.loads(a.sizes_json) if a.sizes_json else {}
    except json.JSONDecodeError as e:
        return out(False, error=f"files/sizes JSON invalid: {e}")
    parts = shard_files(files, sizes, a.budget, a.max_files)
    return out(True, parts=parts, part_labels=[part_label(p) for p in parts])


def cmd_id_next(a):
    if a.used < 0:
        return out(False, error="used count must be >= 0")
    return out(True, id=f"{a.prefix}-{a.used + 1}", next_used=a.used + 1)


SELF_CHECKED = " (self-checked)"
FINDING_HEAD = re.compile(r"^### \[([^\s·]+) · (LOW|MEDIUM|HIGH) · (verified|unconfirmed)(?: \(self-checked\))?"
                          r" · ([^\]]+?)\] (.*)$")
FINDING_HEAD_LEGACY = re.compile(r"^### \[(LOW|MEDIUM|HIGH) · (verified|unconfirmed)(?: \(self-checked\))?"
                                 r" · ([^\]]+?)\] (.*)$")
FIX_SUFFIX = re.compile(r"^(.*?) · fix: (fixed|unfixed|worse|rejected-valid|rejected-invalid|out-of-scope|pending)$")


def parse_findings_md(text):
    items, cur = [], None
    for line in text.splitlines():
        m = FINDING_HEAD.match(line)
        legacy = None if m else FINDING_HEAD_LEGACY.match(line)
        hit = m or legacy
        if hit:
            if cur:
                items.append(cur)
            off = 0 if m else 1
            lens = hit[4 - off]
            fix_status = "pending"
            fx = FIX_SUFFIX.match(lens)
            if fx:
                lens, fix_status = fx.group(1), fx.group(2)
            cur = {"id": hit.group(1) if m else "", "where": "", "what": hit.group(5 - off),
                   "evidence": "", "severity": hit.group(2 - off).lower(),
                   "status": hit.group(3 - off), "lens": lens, "impact": "",
                   "fixStatus": fix_status}
            continue
        if cur:
            w = re.match(r"^- where: `(.*)`$", line)
            if w:
                cur["where"] = w.group(1)
                continue
            e = re.match(r"^- evidence: (.*)$", line)
            if e:
                cur["evidence"] = e.group(1)
                continue
            im = re.match(r"^- impact: (.*)$", line)
            if im:
                cur["impact"] = im.group(1)
    if cur:
        items.append(cur)
    return [f for f in items if f["where"] and f["what"]]


def normalize_findings(items):
    tracked, carried = [], 0
    for it in items:
        if not isinstance(it, dict) or not it.get("where") or not it.get("what"):
            continue
        # D-022: a withdrawn finding (rejected-valid) is as dead as a fixed
        # one — neither comes back on a fix_from carry.
        if it.get("fixStatus") in RESOLVED_FIX:
            continue
        carried += 1
        tracked.append({
            "finding": {
                "id": it["id"] if isinstance(it.get("id"), str) and it.get("id") else f"carried-{carried}",
                "where": it["where"], "what": it["what"],
                "evidence": it.get("evidence") if isinstance(it.get("evidence"), str) else "",
                "severity": it.get("severity") if it.get("severity") in SEV_RANK else "medium",
                "lens": it.get("lens") if isinstance(it.get("lens"), str) and it.get("lens") else "general",
                "impact": it.get("impact") if isinstance(it.get("impact"), str) else "",
                "confirmation": {
                    "status": "verified" if it.get("status") == "verified" else "unconfirmed",
                    "note": "carried from the previous review's report",
                },
            },
            "fix": "pending", "fixNote": "carried from the previous review",
        })
    tracked.sort(key=lambda t: SEV_RANK.get(t["finding"]["severity"], 3))
    return tracked


# --- capability handshake -----------------------------------------------
# A spawn that cannot see a tool still answers, and its answer reads like a
# clean one: a reader with no file tool reports an empty diff. So nothing in
# a reply is read before the tools report it opens with holds every tool on
# its role's brief `tools:` line. The briefs are the table, read at call
# time; this skill ships alone, so the names a kit def dialect maps a tool
# to are carried here.

BRIEF_PREFIX = "spec-review-"
TOOLS_REPORT = re.compile(r"\A[ \t>*`-]*tools:(?P<report>[^\n]*)\n?", re.I)
TOOL_ALIASES = {
    "Write": ("Create", "ApplyPatch"),
    "Bash": ("Execute",),
}


class ToolsRefused(Exception):
    def __init__(self, error: str, **detail):
        super().__init__(error)
        self.detail = {"error": error, **detail}


def _tool_names(value: str) -> list[str]:
    names = []
    for item in value.split(","):
        name = item.strip().rstrip(".,").strip().strip("`").strip()
        if name and name.casefold() not in {n.casefold() for n in names}:
            names.append(name)
    return names


def _brief_tools(role: str) -> list[str]:
    brief = SKILL_DIR / "agents" / f"{BRIEF_PREFIX}{role}.md"
    try:
        front = FRONTMATTER.match(brief.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        raise ToolsRefused(f"agents/{brief.name}: not UTF-8", role=role) from None
    except OSError as e:
        raise ToolsRefused(f"agents/{brief.name}: {e.strerror or e}", role=role) from None
    line = next((l for l in front.group(0).splitlines() if l.startswith("tools:")), None) \
        if front else None
    if line is None:
        raise ToolsRefused(f"agents/{brief.name}: no tools: line in its frontmatter", role=role)
    return _tool_names(line[len("tools:"):])


def _check_tools_report(role: str, text: str) -> tuple[list[str], str]:
    roles = sorted(p.name[len(BRIEF_PREFIX):-3]
                   for p in (SKILL_DIR / "agents").glob(f"{BRIEF_PREFIX}*.md"))
    if role not in roles:
        raise ToolsRefused(f"unknown role {role!r} — name the brief the spawn ran on, "
                           f"without its {BRIEF_PREFIX} prefix: {', '.join(roles)}", role=role)
    report = TOOLS_REPORT.match(text)
    reported = _tool_names(report["report"]) if report else []
    held = {n.casefold() for n in reported}
    missing = [tool for tool in _brief_tools(role)
               if not held & {n.casefold() for n in (tool, *TOOL_ALIASES.get(tool, ()))}]
    if missing:
        raise ToolsRefused(
            f"capability handshake failed: the {role} role reported tools "
            f"`{', '.join(reported) or 'none'}` — its brief requires `{', '.join(missing)}` — "
            "a failed call, never a finding or a round: run the same stage again on a "
            "type or harness that holds them",
            role=role, reported=reported, missing=missing)
    return reported, text[report.end():] if report else text


def cmd_handshake(a):
    try:
        reported, reply = _check_tools_report(a.role, a.text if a.text is not None
                                              else Path(a.file).read_text(encoding="utf-8"))
    except ToolsRefused as e:
        return stage_err("handshake", **e.detail)
    return out(True, tools=reported, reply=reply)


def cmd_findings_parse(a):
    text = a.text if a.text is not None else Path(a.file).read_text(encoding="utf-8")
    try:
        if a.role is not None:
            _, text = _check_tools_report(a.role, text)
        elif a.saved_report:
            if TOOLS_REPORT.match(text):
                raise ToolsRefused(
                    "a saved report never opens with a tools report, so this is a role's "
                    "reply — name the role with --role so the report is checked against its "
                    "brief before a finding is read")
        else:
            raise ToolsRefused(
                "findings-parse was handed a payload and told neither which it is: a role's "
                "reply goes in with --role <role>, its tools report checked against its "
                "brief before a finding is read, and a saved report — the fix_from input — "
                "with --saved-report")
    except ToolsRefused as e:
        return stage_err("handshake", **e.detail)
    if re.match(r"^\s*[\[{]", text):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return out(False, error="payload starts as JSON but does not parse")
        items = parsed if isinstance(parsed, list) else (
            parsed.get("findings") if isinstance(parsed, dict) and isinstance(parsed.get("findings"), list) else [])
        tracked = normalize_findings(items)
        if not tracked:
            return out(False, error="payload carried no actionable findings — every item was "
                       "invalid or already marked fixed")
        return out(True, tracked=tracked)
    md_items = parse_findings_md(text)
    if not md_items:
        return out(False, error="payload is neither valid JSON nor a parseable review report")
    tracked = normalize_findings(md_items)
    if not tracked:
        return out(False, error="report carried no actionable findings")
    return out(True, tracked=tracked)


def md_safe(s):
    return re.sub(r"[\\`*_[\]()!<>]", lambda m: "\\" + m.group(0), str(s))


def findings_md(items):
    lines = []
    for f in items:
        fix = "" if f.get("fixStatus") == "pending" else " · fix: " + f.get("fixStatus", "")
        status = f["status"] + (SELF_CHECKED if f.get("selfChecked") else "")
        lines.append(f"### [{f['id']} · {f['severity'].upper()} · {status} · {f['lens']}{fix}] {f['what']}")
        lines.append(f"- where: `{f['where']}`")
        lines.append(f"- evidence: {f['evidence']}")
        if f.get("impact"):
            lines.append(f"- impact: {f['impact']}")
        lines.append("")
    return lines


def reported_finding(t):
    f, conf = t["finding"], t["finding"]["confirmation"]
    self_checked = bool(conf.get("self_checked"))
    # A self-check is never independent confirmation, whatever status it claims.
    status = "unconfirmed" if self_checked or conf.get("status") != "verified" else "verified"
    return {"id": f["id"], "where": f["where"], "what": f["what"], "evidence": f["evidence"],
            "status": status, "selfChecked": self_checked, "severity": f["severity"],
            "lens": f["lens"], "impact": f.get("impact", ""), "fixStatus": t.get("fix") or "pending"}


# D-021: the recommendation floor is derived from the report's own state
# (gates/recommendation.md), and an assessor's claim may only ESCALATE above
# it — human outranks fix-first outranks merge. A claim below the floor is an
# inconsistent result: rejected with both values, never guessed.
RECOMMENDATION_RANK = {"merge": 0, "fix-first": 1, "human": 2}

# D-022: fix-verdict vocabulary. RESOLVED_FIX ends a finding's life in the
# loop: `fixed` (the fix held) or `rejected-valid` (the fixer's skip reason
# held — the finding was withdrawn as not a real defect to fix). Everything
# else keeps it open; `out-of-scope` (the sound fix needs paths or behavior
# this change must not touch) is the user's widening call, not a round.
RESOLVED_FIX = ("fixed", "rejected-valid")
KNOWN_FIX = RESOLVED_FIX + ("unfixed", "worse", "rejected-invalid",
                            "out-of-scope", "pending")
# out-of-scope waits on the user's widening call, never on a round
OFF_LOOP_FIX = RESOLVED_FIX + ("out-of-scope",)


def derive_conclusion(gate_green, reported, ci_standing=()):
    """The derived recommendation for a fix-loop report: `human` while an
    out-of-scope widening call, unconfirmed findings, or a standing
    infrastructure-or-unknown CI row (D-023 — the rerun is the user's
    call, not an edit) remains, `fix-first` while ordinary findings or
    gate failures persist, else `merge`."""
    if any(f["fixStatus"] == "out-of-scope" for f in reported):
        return "human"
    if any(f["status"] == "unconfirmed" and f["fixStatus"] not in RESOLVED_FIX
           for f in reported):
        return "human"
    if ci_standing:
        return "human"
    if not gate_green or any(f["fixStatus"] not in RESOLVED_FIX
                             for f in reported):
        return "fix-first"
    return "merge"


# D-024: a consequential stop — one whose next move is the owner's judgment,
# not an edit — renders a stop ask derived from the report's own state, never
# from a claim (gates/recommendation.md § Consequential stops). Only a
# `human` verdict and the `fix-first` a spent loop ends on carry one; `merge`
# and an ordinary fix-first (rounds left) are unaffected, and so is every
# review-only run (D-021 — there is nothing to recommend about yet).
STOP_GATE = "the recommendation gate (gates/recommendation.md)"
STOP_IDS_MAX = 6


def _stop_ids(findings, with_where=True):
    parts = [f"{f['id']} ({f['where']})" if with_where else f["id"]
             for f in findings]
    if len(parts) > STOP_IDS_MAX:
        parts = parts[:STOP_IDS_MAX] + [f"and {len(parts) - STOP_IDS_MAX} more"]
    return ", ".join(parts)


def _stop_evidence(findings, with_where=True):
    # Contract item 1: what stopped names the ids with the evidence
    # itself — each finding's evidence, or its text when none — bounded
    # so the one-line ask stays readable.
    parts = []
    for f in findings:
        text = _stop_line(f["evidence"] or f["what"])
        if len(text) > 120:
            text = text[:120] + "…"
        parts.append(f"{f['id']} ({f['where']}) — {text}" if with_where
                     else f"{f['id']} — {text}")
    if len(parts) > STOP_IDS_MAX:
        parts = parts[:STOP_IDS_MAX] + [f"and {len(findings) - STOP_IDS_MAX} more"]
    return "; ".join(parts)


def _stop_line(s):
    # whatStops is one line by contract; data-derived fragments must not break it
    return " ".join(str(s).split())


def stop_recommendation(options, label, reason):
    """Contract item 4: a recommendation is one of the offered option
    labels — a pick that names no option is dropped to null."""
    if label is not None and not any(o["label"] == label for o in options):
        return None, None
    return label, reason


def _fold_note(dropped):
    # a folded option stays stated: its move rides in the kept option's
    # consequence
    extra = (f" Or {dropped['label'][0].lower() + dropped['label'][1:]}: "
             + dropped["consequence"])
    return extra if extra.endswith(".") else extra + "."


def stop_ask(reported, gate_green, ci_standing, rounds_used, conclusion,
             changed_since=None):
    """The stop ask for a fix-kind report, or None when nothing in the
    state waits on the owner's judgment. whatStops reads the unconfirmed
    findings, the overruled skips and the unresolved items; the options
    come from the same state; the recommendation fires only where a
    criterion in gates/recommendation.md picks one, and names it."""
    unconf = [f for f in reported
              if f["status"] == "unconfirmed" and f["fixStatus"] not in RESOLVED_FIX]
    oos = [f for f in reported if f["fixStatus"] == "out-of-scope"]
    skips = [f for f in reported if f["fixStatus"] == "rejected-invalid"]
    ordinary = [f for f in reported if f["fixStatus"] not in RESOLVED_FIX
                and f["status"] == "verified" and f["fixStatus"] != "out-of-scope"
                and f["fixStatus"] != "rejected-invalid"]
    open_ordinary = ordinary + skips
    # the loop is spent only when a round ran into work it left standing
    exhausted = bool(rounds_used) and bool(open_ordinary)
    # a contested skip is a judgment hand-over only when the verdict says so;
    # under a fix-first floor it is ordinary residue an author turn clears
    hand_over = bool(unconf or oos or ci_standing
                     or (conclusion == "human" and skips))
    if not (hand_over or exhausted):
        return None

    parts = []
    if unconf:
        parts.append(f"{len(unconf)} unconfirmed finding(s) await your "
                     f"adjudication: {_stop_evidence(unconf)}")
    if skips:
        parts.append(f"{len(skips)} fixer skip(s) the verifier overruled "
                     f"(rejected-invalid): {_stop_evidence(skips, False)}")
    if oos:
        parts.append(f"{len(oos)} out-of-scope finding(s) wait on your "
                     f"widening call: {_stop_evidence(oos)}")
    if ci_standing:
        names = "; ".join(g["name"] for g in ci_standing)
        reason = _stop_line(ci_standing[0].get("reason") or "")
        parts.append(f"{len(ci_standing)} standing CI row(s): {names}"
                     + (f" — {reason}" if reason else ""))
    if exhausted and ordinary:  # skips left standing name themselves above
        parts.append(f"{len(open_ordinary)} finding(s) still unresolved after "
                     f"{rounds_used} fix round(s): "
                     f"{_stop_evidence(ordinary, False)}")
    if not gate_green:
        parts.append("the mechanical gate is red")
    what_stops = f"{STOP_GATE}: " + "; ".join(parts) + "."

    drivers = unconf + ordinary + skips + oos
    if any(f["severity"] == "high" for f in drivers):
        level = "high"
    elif drivers or ci_standing or not gate_green:
        level = "medium"
    else:
        level = "low"
    whys = []
    if unconf:
        whys.append(f"{len(unconf)} unverified claim(s) could be real defects "
                    "shipping unjudged")
    if skips:
        whys.append(f"the fixer and its verifier disagree on {len(skips)} "
                    "finding(s) — one side is wrong")
    if oos:
        whys.append("the sound fix sits outside this change — the need stays "
                    "unmet until you widen or carry it")
    if ci_standing:
        whys.append("the standing CI row(s) hold no code verdict — merging "
                    "floors at human until they clear")
    if exhausted and ordinary:
        whys.append(f"{len(ordinary)} finding(s) remain after the round cap — "
                    "the loop cannot clear them by running again")
    why = f"risk: {level} — " + "; ".join(whys) + "."
    # the retry rule: a spent loop is not offered another round on nothing
    if exhausted and not changed_since:
        why += " No further fix round is offered — nothing has changed since the last one."

    # the rules and open owner's-calls are computed before the options so
    # the cap below never folds away an option they name
    picks, opens = [], []
    if unconf:
        picks.append(("Adjudicate the unconfirmed findings",
                      "the human criterion: unconfirmed findings are the user's "
                      "adjudication (gates/recommendation.md)"))
    if ci_standing:
        if any(g.get("rerun") for g in ci_standing) and not oos:
            picks.append(("Rerun the failed CI run",
                          "the CI triage rule (D-023): the row is infrastructure — the code "
                          "was never judged, so the verdict needs the rerun the row itself "
                          "carries; rerunning an unjudged run is not a retry"))
        else:
            opens.append("whether the standing CI row is a flap to rerun or a workflow "
                         "to repair is the owner's call — its class carries no step "
                         "evidence to pick one (D-023)")
    if oos:
        opens.append("the widening call is the owner's by rule — an out-of-scope finding "
                     "derives human until you settle it (D-022)")
    if conclusion == "human" and skips:
        opens.append("the fixer and its verifier split on the overruled skip(s) — the "
                     "state holds both positions and picks neither")

    options = []
    if unconf:
        options.append({"label": "Adjudicate the unconfirmed findings",
                        "consequence": f"rule each of {_stop_ids(unconf, False)} real or not — "
                                       "a confirmed one becomes fixable in a follow-up fix_from "
                                       "run, a withdrawn one leaves the report; until then they "
                                       "stay unverified claims in it"})
        if ordinary or not gate_green:
            options.append({"label": "Re-enter the fix loop after adjudicating (fix_from)",
                            "consequence": "the adjudicated findings go through another loop's "
                                           "fixer, verifiers and gate re-run; the round cap starts over"})
    settle_skips = bool(skips) and (conclusion == "human" or unconf or oos or ci_standing)
    if settle_skips:
        options.append({"label": "Settle the overruled skips",
                        "consequence": f"sustaining the fixer's skip withdraws {_stop_ids(skips, False)}, "
                                       "rejecting it leaves them standing for an author turn — you "
                                       "override one of the two agents either way"})
    if oos:
        options.append({"label": "Widen the change and fix the out-of-scope findings",
                        "consequence": f"the sound fix for {_stop_ids(oos, False)} touches paths or "
                                       "behavior this change must not touch; the widened set needs "
                                       "its own review before the findings close"})
        options.append({"label": "Keep them out of scope and carry the findings",
                        "consequence": "the need ships unmet and the recommendation stays floored "
                                       "at human; park it where the backlog offer was made, or "
                                       "track it yourself"})
    if ci_standing:
        rerun = next((g.get("rerun") for g in ci_standing if g.get("rerun")), None)
        if rerun:
            options.append({"label": "Rerun the failed CI run",
                            "consequence": f"`{rerun}` — the run never reached a code verdict; "
                                           "while the row stands the recommendation floors at "
                                           "human, and a repeat flap stands again"})
        else:
            options.append({"label": "Clear the standing CI row",
                            "consequence": "rerun or repair the workflow yourself — the row keeps "
                                           "flooring the recommendation at human until it clears; "
                                           "the report carries its class and reason"})
    if exhausted:
        n = len(skips) if settle_skips else len(open_ordinary)
        options.append({"label": "Clear what remains in a normal author turn",
                        "consequence": f"the {n} unresolved finding(s)"
                                       f"{' and the red gate' if not gate_green else ''} close only "
                                       "once the edits land and a fix_from run verifies them"})
        if changed_since:
            options.append({"label": "Another fix round",
                            "consequence": f"something changed since the last attempt "
                                           f"({_stop_line(changed_since)[:200]}) — the next round "
                                           "attempts the still-unresolved findings and re-runs "
                                           "the gate"})
    options.append({"label": "Accept the change as it is, risks on record",
                    "consequence": "the open findings and residual risks ship with the change and "
                                   "stay on record in this report; the recommendation stays at its "
                                   "floor until they are settled"})
    # Two to four options (contract item 3), the accept fallback always
    # the last. A state that derives more folds its follow-through moves
    # into the kept option that carries their route — never a chop: an
    # option a rule above names must not go missing while the ask's own
    # reason still names it.
    accept = options[-1]
    protected = {label for label, _ in picks} | {accept["label"]}
    for label, carrier, clause in (
        # re-entering the loop is adjudication's stated follow-through —
        # the kept consequence already names the follow-up fix_from run,
        # so the fold is silent (None)
        ("Re-enter the fix loop after adjudicating (fix_from)",
         "Adjudicate the unconfirmed findings", None),
        # a named change re-opens the round inside the author-turn option
        ("Another fix round",
         "Clear what remains in a normal author turn",
         f". Another fix round stays open — something changed since the "
         f"last attempt ({_stop_line(changed_since)[:120]})."
         if changed_since else ""),
        # the author turn is an edit, not a judgment; the dropped option's
        # own consequence (with the round clause above, if it landed there)
        # folds beside adjudication's follow-up run
        ("Clear what remains in a normal author turn",
         "Adjudicate the unconfirmed findings", ""),
    ):
        if len(options) <= 4:
            break
        dropped = next((o for o in options if o["label"] == label), None)
        if dropped is None or label in protected:
            continue
        options.remove(dropped)
        kept = (next((o for o in options if o["label"] == carrier), None)
                or next((o for o in options[:-1] if o["label"] not in protected),
                        None))
        if kept is not None and clause is not None:
            extra = clause or _fold_note(dropped)
            kept["consequence"] = _stop_line(kept["consequence"] + extra)
    # the widening either/or folds into one option when the ask is still
    # full — both halves stay stated
    if len(options) > 4:
        wide = next((o for o in options if o["label"].startswith("Widen ")), None)
        carry = next((o for o in options if o["label"].startswith("Keep them ")), None)
        if (wide is not None and carry is not None
                and wide["label"] not in protected):
            wide["label"] = ("Settle the widening call: widen the change "
                             "or carry the findings")
            wide["consequence"] = _stop_line(
                wide["consequence"] + " Or keep them out of scope: "
                + carry["consequence"])
            options.remove(carry)
    # every state caps at four: the last unpicked route folds into the
    # option above it, its move still stated
    while len(options) > 4:
        dropped = next((o for o in reversed(options[:-1])
                        if o["label"] not in protected), None)
        if dropped is None:
            break
        options.remove(dropped)
        kept = next((o for o in options[:-1] if o["label"] not in protected),
                    accept)
        kept["consequence"] = _stop_line(kept["consequence"]
                                         + _fold_note(dropped))

    rec = rec_reason = None
    if len(picks) == 1 and not opens:
        rec, rec_reason = picks[0]
    elif len(picks) == 1:
        pass  # a rule picks a move, but an open owner's-call sits beside it
    elif len(picks) > 1:
        opens.insert(0, "the rules pick different moves ("
                        + "; ".join(p[0] for p in picks)
                        + ") — no rule ranks one over the other")
    elif not opens and exhausted:
        rec, rec_reason = ("Clear what remains in a normal author turn",
                           "the fix-first criterion: the remaining findings are ordinary — "
                           "a normal author turn can clear them (gates/recommendation.md)")
    rec, rec_reason = stop_recommendation(options, rec, rec_reason)
    return {
        "whatStops": _stop_line(what_stops),
        "whyItMatters": _stop_line(why),
        "options": options,
        "recommendation": rec,
        "recommendationReason": rec_reason if rec else None,
        "noRecommendationReason": None if rec else ("; ".join(opens) or
            "no rule in gates/recommendation.md picks an option for this state"),
    }


def stop_ask_md(stop):
    """The ask in the contract's order: what stopped, why it matters,
    the options, the recommendation, what the answer covers."""
    lines = [f"**What stopped:** {stop['whatStops']}", "",
             f"**Why it matters:** {stop['whyItMatters']}", "", "**Options:**", ""]
    for n, o in enumerate(stop["options"], 1):
        lines.append(f"{n}. **{o['label']}** — {o['consequence']}")
    lines.append("")
    if stop["recommendation"]:
        lines.append(f"**Recommendation:** {stop['recommendation']} — "
                     f"{stop['recommendationReason']}")
    else:
        lines.append(f"**No recommendation:** {stop['noRecommendationReason']}")
    lines += ["", "**What the answer covers:** your yes covers exactly the "
                  "chosen option and nothing else.", ""]
    return lines


def cmd_report(a):
    try:
        d = json.loads(Path(a.data[1:]).read_text(encoding="utf-8")
                       if a.data.startswith("@") else a.data)
    except (json.JSONDecodeError, OSError) as e:
        return out(False, error=f"report data invalid: {e}")
    tracked = d.get("tracked", [])
    gate = d.get("gate_rows", [])
    gate_green = d.get("gate_green", False)
    ci_standing = [g for g in gate
                   if g.get("source") == "ci" and g.get("class") in CI_STANDING]
    assessment = d.get("assessment", {})
    reported = [reported_finding(t) for t in tracked]
    unknown = sorted({f["fixStatus"] for f in reported} - set(KNOWN_FIX))
    if unknown:
        return out(False, error=(f"unknown fix status {', '.join(map(repr, unknown))} — "
                                 f"one of: {', '.join(KNOWN_FIX)}"))
    conclusion = d.get("conclusion", "")
    derived = None
    if a.kind == "fix":
        derived = derive_conclusion(gate_green, reported, ci_standing)
        n_open = sum(1 for f in reported if f["fixStatus"] not in RESOLVED_FIX)
        if conclusion in RECOMMENDATION_RANK \
                and RECOMMENDATION_RANK[conclusion] < RECOMMENDATION_RANK[derived]:
            return out(False, derived_conclusion=derived, conclusion=conclusion,
                       error=(f"conclusion {conclusion!r} is below the derived floor "
                              f"{derived!r} ({n_open} unresolved finding(s), gate green: "
                              f"{bool(gate_green)}"
                              + (f", {len(ci_standing)} CI row(s) standing "
                                 "infrastructure-or-unknown" if ci_standing else "")
                              + ") — a claim may escalate to fix-first or "
                              "human, never below the state the report itself shows"))
        if conclusion not in RECOMMENDATION_RANK:
            conclusion = derived
    n_high = sum(1 for f in reported if f["severity"] == "high")
    n_fixed = sum(1 for f in reported if f["fixStatus"] == "fixed")
    n_withdrawn = sum(1 for f in reported if f["fixStatus"] == "rejected-valid")
    n_oos = sum(1 for f in reported if f["fixStatus"] == "out-of-scope")
    n_confirmed = sum(1 for f in reported if f["status"] == "verified")
    n_self = sum(1 for f in reported if f["selfChecked"])
    unconfirmed = f"{len(reported) - n_confirmed} unconfirmed" + (f" ({n_self} self-checked)" if n_self else "")
    verdict_extra = (f" · {n_withdrawn} withdrawn" if n_withdrawn else "") \
                    + (f" · {n_oos} out-of-scope" if n_oos else "")
    rounds = d.get("rounds_used", 0)
    stop = None
    if a.kind == "fix":
        stop = stop_ask(reported, gate_green, ci_standing, rounds, conclusion,
                        d.get("changed_since"))
    repo_rows = [g for g in gate if is_repo_row(g)]
    ci = [g for g in gate if g.get("source") == "ci"]
    lines = [d.get("title", "Code review report"), "", d.get("mode_line", ""), ""]
    # a standing red CI row is never green-washed into the header either
    green = ("all passed" if not rounds else "green after the final fix round") \
        if gate_green and not ci_standing \
        else ("green" + (" after the final fix round" if rounds else "")
              + f", with {len(ci_standing)} CI row(s) standing "
                "(infrastructure-or-unknown — see below)") \
        if gate_green else None
    lines += [assessment.get("verdict", ""), "",
              f"## Mechanical gate ({len(repo_rows)} repo check{'' if len(repo_rows) == 1 else 's'}"
              f" · {len(gate) - len(repo_rows) - len(ci)} built-in"
              + (f" · {len(ci)} CI" if ci else "") + ") — "
              + ("no repo checks detected — no mechanical floor"
                 + ("" if gate_green else "; built-in checks RED") if not repo_rows
                 else green
                 if green else "RED after the final fix round" if rounds else "RED"), ""]
    for g in gate:
        code = g.get("exit_code", g.get("exitCode", 0))
        if is_info_row(g):
            lines.append(f"- info — {g['name']}")
            lines += [f"  - {t}" for t in g.get("tail", "").splitlines()[1:]]
        elif g.get("status") in ("pending", "skipped"):
            lines.append(f"- {g['status']} — {g['name']}")
        elif g.get("class") in CI_STANDING:
            # a standing red CI row: carried with its evidence, never a pass
            lines.append(f"- {g['class']} — {g['name']}"
                         + (f" — {g['reason']}" if g.get("reason") else ""))
            if g.get("failedStep"):
                lines.append(f"  - first failed step: {g['failedStep']}")
            if g.get("rerun"):
                lines.append(f"  - rerun (an outward action, never run here): "
                             f"`{g['rerun']}`")
        elif code in (0, None):
            lines.append(f"- pass — {g['name']}")
        else:
            verdict = "TIMED OUT" if g.get("status") == "timed_out" else "FAIL"
            lines += [f"- **{verdict}** — {g['name']}", "", "  ```", f"  {g['tail']}", "  ```"]
    lines += ["", f"## Findings ({len(reported)} · {n_confirmed} confirmed · {unconfirmed} · "
                  f"{n_high} high · {n_fixed} fixed{verdict_extra})", ""]
    lines += findings_md(reported) if tracked else ["None — the reviewers reported nothing that met the bar.", ""]
    if rounds:
        lines += ["## What the fixer did", ""] + (
            [f"- {n}" for n in d.get("fixer_notes", [])] or ["(no changes)"]) + [""]
    lines += [f"## Dropped at triage ({len(d.get('dropped', []))})", ""]
    lines += [f"- `{x['where']}` — {x['what']} — _{x['reason']}_" for x in d.get("dropped", [])] or ["None."]
    lines += ["", "## Test gaps", ""]
    lines += [f"- {t}" for t in assessment.get("testGaps", [])] or ["None identified."]
    lines += ["", "## Residual risks", ""]
    lines += [f"- {r}" for r in assessment.get("residualRisks", [])] or ["None identified."]
    if a.kind == "fix":
        # the stop ask renders in the contract's order under the recommendation (D-024)
        floor_note = (f" (the state's floor is {derived} — a claim may escalate above it, "
                      "never descend, D-021)") if derived is not None and derived != conclusion else ""
        lines += ["", f"## Recommendation — {conclusion}{floor_note}", ""]
        if stop:
            lines += stop_ask_md(stop)
    lines += ["", "## How this was checked", ""] + d.get("checked", []) + [""] + d.get("fix_checked", [])
    try:  # fire-and-forget local telemetry (see scripts/telemetry.py)
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).resolve().parent))
        from telemetry import record
        record("spec-review", "review_report", kind=a.kind,
               conclusion=conclusion,
               findings=len(reported),
               unconfirmed=sum(1 for f in reported
                               if f.get("status") == "unconfirmed"))
    except Exception:
        pass
    payload_extra = {"derived_conclusion": derived} if derived is not None else {}
    return out(True, markdown="\n".join(lines), reported_findings=reported,
               conclusion=conclusion, stopAsk=stop,
               **payload_extra, **backlog_offer(d, assessment))


def backlog_offer(d, assessment):
    """Residual-risk lines for the user to park in specs/BACKLOG.md — offered only where that file exists."""
    risks = assessment.get("residualRisks", [])
    repo = d.get("repo_abs") or resolve_repo(None)
    if not risks or not repo or not (Path(repo) / BACKLOG).is_file():
        return {}
    label = d.get("backlog_label") or (git_out(["rev-parse", "--abbrev-ref", "HEAD"], repo) or "").strip() or "review"
    lines = [f"- {label} — {' '.join(r.split())} (source: spec-review residual risk)" for r in risks]
    return {"backlog_offer": {"path": str(BACKLOG), "lines": lines}}


# --- resumable runs (spec-review D-020) -------------------------------
# A full review is 10+ agent turns, all of it in conversation — a crash
# restarted from zero. A run folder under <repo>/.spec-review/runs/
# checkpoints each stage's JSON; run-resume verifies the target did not
# move (the diff + untracked fingerprint) and reports where to continue.
# The folder carries its own .gitignore containing `*`, so a run is
# never committed and the user's .gitignore is never edited.

STAGES = (
    "scope",
    "scout",
    "review-<lens>",
    "triage-<lens>",
    "crosslens",
    "confirm-<F-id>",
    "assessment",
    "report",
    "fix-<n>-snapshot", "fix-<n>-fixer", "fix-<n>-check",
    "fix-<n>-gate", "fix-<n>-verify", "fix-<n>-review",
)

RUNS_DIRNAME = ".spec-review/runs"
RUN_GC_KEEP = 5


def _stage_pattern(stage: str) -> str | None:
    """The STAGES pattern a concrete stage name instantiates, or None —
    the save path's vocabulary check."""
    for pat in STAGES:
        rx = re.escape(pat)
        rx = rx.replace(re.escape("<lens>"), r"[a-z0-9-]+")
        rx = rx.replace(re.escape("<F-id>"), r"[A-Za-z0-9-]+")
        rx = rx.replace(re.escape("<n>"), r"\d+")
        if re.fullmatch(rx, stage):
            return pat
    return None


def _stage_file(run_dir: Path, stage: str) -> Path:
    return run_dir / (re.sub(r"[^A-Za-z0-9._-]", "-", stage) + ".json")


def _atomic_write_json(path: Path, doc: dict) -> None:
    """Same-directory temp file, then os.replace — a reader never sees
    half a stage file."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                               prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _run_fingerprint(repo_abs: str, base: str, files: list[str]) -> str:
    """sha256 over the exact diff and the untracked files scope lists —
    run-resume recomputes it; a different value means the target moved
    and the run must not resume."""
    h = hashlib.sha256()
    h.update((git_out(["diff", base], repo_abs)
              or "").encode("utf-8", "replace"))
    root = Path(repo_abs)
    for f in sorted(files or []):
        h.update(f.encode("utf-8", "replace"))
        h.update(b"\0")
        try:
            h.update((root / f).read_bytes())
        except OSError:
            h.update(b"<unreadable>")
        h.update(b"\0")
    return h.hexdigest()


def _run_gc(runs_root: Path, keep: int) -> list[str]:
    """Delete the oldest run dirs beyond `keep` (names are
    date-prefixed, so name order is age order); returns what went."""
    runs = sorted(d for d in runs_root.iterdir()
                  if d.is_dir() and not d.name.startswith("."))
    removed = []
    for d in runs[:-keep] if len(runs) > keep else []:
        shutil.rmtree(d, ignore_errors=True)
        removed.append(d.name)
    return removed


def cmd_run_init(a):
    ok, result = _scope_result(a)
    if not ok:
        return out(False, **result)
    repo_abs = result["repo_abs"]
    base = result.get("merge_base") or result.get("base") or "HEAD"
    run_id = (datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
              + "-" + secrets.token_hex(2))
    run_dir = Path(repo_abs) / RUNS_DIRNAME / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / ".gitignore").write_text("*\n", encoding="utf-8")
    head_sha = (git_out(["rev-parse", "HEAD"], repo_abs) or "").strip()
    record = {
        "run_id": run_id,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"),
        "target": a.target,
        "args": {"base": a.base, "pr": a.pr, "paths": a.paths,
                 "repo": a.repo},
        "base_sha": base,
        "head_sha": head_sha,
        "diff_sha256": _run_fingerprint(repo_abs, base,
                                        result.get("files") or []),
        "mode": result.get("mode"),
    }
    _atomic_write_json(run_dir / "run.json", record)
    removed = _run_gc(run_dir.parent, a.keep)
    return out(True, run_dir=str(run_dir), run_id=run_id,
               fingerprint=record["diff_sha256"], gc_removed=removed)


def cmd_run_save(a):
    run_dir = Path(a.run_dir)
    record = run_dir / "run.json"
    if not record.is_file():
        return out(False, error=f"no run record in {run_dir}")
    if _stage_pattern(a.stage) is None:
        return out(False, error=(
            f"unknown stage {a.stage!r} — the vocabulary is the STAGES "
            f"tuple: {', '.join(STAGES)}"))
    try:
        data = json.loads(_read_arg(a.data))
    except ValueError as e:
        return out(False, error=f"--data is not JSON: {e}")
    _atomic_write_json(_stage_file(run_dir, a.stage),
                       {"stage": a.stage, "data": data})
    return out(True, stage=a.stage, run_dir=str(run_dir))


def _read_arg(v: str) -> str:
    """@FILE reads the file; anything else is the literal JSON string —
    the same convention report/ask take."""
    if v.startswith("@"):
        return Path(v[1:]).read_text(encoding="utf-8")
    return v


def _saved_stages(run_dir: Path) -> list[str]:
    """The saved concrete stages, canonically ordered: pattern rank,
    then name within the pattern."""
    def rank(name: str):
        pat = _stage_pattern(name)
        return (STAGES.index(pat) if pat else len(STAGES), name)
    out_ = []
    for p in run_dir.glob("*.json"):
        if p.name == "run.json":
            continue
        stage = p.name[:-len(".json")]
        if _stage_pattern(stage) is not None:
            out_.append(stage)
    return sorted(out_, key=rank)


def _kept_ids(crosslens_data) -> list[str]:
    """The kept finding ids a saved crosslens stage names — best effort:
    the orchestrator's cross-lens output shape is its own."""
    if not isinstance(crosslens_data, dict):
        return []
    kept = crosslens_data.get("kept")
    if not isinstance(kept, list):
        return []
    ids = []
    for k in kept:
        if isinstance(k, dict) and k.get("id"):
            ids.append(str(k["id"]))
        elif isinstance(k, str):
            ids.append(k)
    return ids


def _next_stage(saved: list[str], data: dict[str, dict]) -> str | None:
    """The first skeleton slot with no save. Lenses: fast mode (the
    saved scope's `fast_mode_default`) runs one general lens, full mode
    runs every LENSES lens — the lens set is the mode's, never the
    saved subset. Confirm slots come from the saved crosslens data's
    kept ids. None means the skeleton is exhausted — continue from the
    saved data (the fix loop's rounds are the orchestrator's count)."""
    scope_data = (data.get("scope", {}) or {}).get("data") or {}
    if scope_data.get("fast_mode_default"):
        lenses = ["general"]
    else:
        lenses = [l["label"] for l in LENSES]
    order = (["scope", "scout"]
             + [f"review-{l}" for l in lenses]
             + [f"triage-{l}" for l in lenses]
             + ["crosslens"])
    if "crosslens" in saved:
        order += [f"confirm-{i}" for i in _kept_ids(
            data.get("crosslens", {}).get("data"))]
    order += ["assessment", "report"]
    for s in order:
        if s not in saved:
            return s
    return None


def cmd_run_resume(a):
    run_dir = Path(a.run_dir)
    record = run_dir / "run.json"
    if not record.is_file():
        return out(False, error=f"no run record in {run_dir}")
    try:
        rec = json.loads(record.read_text(encoding="utf-8"))
    except ValueError as e:
        return out(False, error=f"run.json is not JSON: {e}")
    base = rec.get("base_sha") or "HEAD"
    # the target re-resolves from the run record's own args unless the
    # caller overrides them — the fingerprint is over the same target
    # the run scoped, not over whatever the CLI points at now
    args2 = argparse.Namespace(
        target=a.target or rec.get("target"),
        base=a.base if a.base is not None else (rec.get("args") or {}).get("base"),
        pr=a.pr if a.pr is not None else (rec.get("args") or {}).get("pr"),
        paths=a.paths if a.paths is not None else (rec.get("args") or {}).get("paths"),
        repo=a.repo if a.repo is not None else (rec.get("args") or {}).get("repo"),
        include_gate=False,
    )
    ok, result = _scope_result(args2)
    if not ok:
        return out(False, error=(
            f"the target no longer resolves: {result.get('stage')} — "
            "start a new run (or continue from the saved report with "
            "fix_from)"))
    now = _run_fingerprint(result["repo_abs"], base,
                           result.get("files") or [])
    if now != rec.get("diff_sha256"):
        return out(False, error=(
            "target changed since the run started — start a new run "
            "(or continue from the saved report with fix_from)"),
            diff_sha256=now, run_diff_sha256=rec.get("diff_sha256"))
    saved = _saved_stages(run_dir)
    data: dict[str, dict] = {}
    for s in saved:
        try:
            data[s] = json.loads(
                _stage_file(run_dir, s).read_text(encoding="utf-8"))
        except ValueError:
            data[s] = {}
    return out(True, run_id=rec.get("run_id"), completed=saved,
               next=_next_stage(saved, data), data=data)


def cmd_run_gc(a):
    repo_abs = resolve_repo(a.repo)
    runs_root = Path(repo_abs) / RUNS_DIRNAME
    if not runs_root.is_dir():
        return out(True, removed=[], kept=0)
    removed = _run_gc(runs_root, a.keep)
    kept = len([d for d in runs_root.iterdir()
                if d.is_dir() and not d.name.startswith(".")])
    return out(True, removed=removed, kept=kept)


def main(argv=None):
    p = argparse.ArgumentParser(description="spec-review shared state oracle")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scope")
    s.add_argument("--target", required=True, choices=["diff", "branch", "pr", "project"])
    s.add_argument("--base"), s.add_argument("--pr"), s.add_argument("--repo")
    s.add_argument("--paths"), s.add_argument("--include-gate", action="store_true")
    s.set_defaults(fn=cmd_scope)
    ri = sub.add_parser("run-init")
    ri.add_argument("--target", required=True, choices=["diff", "branch", "pr", "project"])
    ri.add_argument("--base"), ri.add_argument("--pr"), ri.add_argument("--repo")
    ri.add_argument("--paths"), ri.add_argument("--include-gate", action="store_true")
    ri.add_argument("--keep", type=int, default=RUN_GC_KEEP)
    ri.set_defaults(fn=cmd_run_init)
    rs = sub.add_parser("run-save")
    rs.add_argument("--run-dir", required=True)
    rs.add_argument("--stage", required=True)
    rs.add_argument("--data", required=True)
    rs.set_defaults(fn=cmd_run_save)
    rr = sub.add_parser("run-resume")
    rr.add_argument("--run-dir", required=True)
    rr.add_argument("--target", choices=["diff", "branch", "pr", "project"])
    rr.add_argument("--base"), rr.add_argument("--pr"), rr.add_argument("--repo")
    rr.add_argument("--paths"), rr.add_argument("--include-gate", action="store_true")
    rr.set_defaults(fn=cmd_run_resume)
    rg = sub.add_parser("run-gc")
    rg.add_argument("--repo"), rg.add_argument("--keep", type=int, default=RUN_GC_KEEP)
    rg.set_defaults(fn=cmd_run_gc)
    g = sub.add_parser("gate")
    g.add_argument("--repo"), g.add_argument("--base"), g.add_argument("--tree", action="store_true")
    g.add_argument("--pr")
    g.set_defaults(fn=cmd_gate)
    sh = sub.add_parser("shard")
    sh.add_argument("--files-json", required=True), sh.add_argument("--sizes-json")
    sh.add_argument("--budget", type=int, default=SHARD_TARGET_BYTES)
    sh.add_argument("--max-files", type=int, default=SHARD_MAX_FILES)
    sh.set_defaults(fn=cmd_shard)
    i = sub.add_parser("id-next")
    i.add_argument("--prefix", required=True), i.add_argument("--used", type=int, required=True)
    i.set_defaults(fn=cmd_id_next)
    h = sub.add_parser("handshake")
    h.add_argument("--role", required=True)
    source = h.add_mutually_exclusive_group(required=True)
    source.add_argument("--file"), source.add_argument("--text")
    h.set_defaults(fn=cmd_handshake)
    f = sub.add_parser("findings-parse")
    f.add_argument("--file"), f.add_argument("--text")
    kind = f.add_mutually_exclusive_group()
    kind.add_argument("--role"), kind.add_argument("--saved-report", action="store_true")
    f.set_defaults(fn=cmd_findings_parse)
    r = sub.add_parser("report")
    r.add_argument("--kind", required=True, choices=["review", "fix"])
    r.add_argument("--data", required=True)
    r.set_defaults(fn=cmd_report)
    fs = sub.add_parser("fix-snapshot")
    fs.add_argument("--repo")
    fs.set_defaults(fn=cmd_fix_snapshot)
    fc = sub.add_parser("fix-check")
    fc.add_argument("--repo"), fc.add_argument("--head", required=True)
    fc.add_argument("--stash-count", type=int, required=True), fc.add_argument("--tree", required=True)
    fc.set_defaults(fn=cmd_fix_check)
    sy = sub.add_parser("systems")
    sy.set_defaults(fn=cmd_systems)
    ak = sub.add_parser("ask")
    ak.add_argument("--kind", required=True)  # validated in cmd_ask: errors exit 1 as JSON
    ak.add_argument("--ctx", required=True)
    ak.set_defaults(fn=cmd_ask)
    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except OSError as e:
        return out(False, error=f"{type(e).__name__}: {e}")




# --- panel systems + ask rendering --------------------
# One home for the panel's system prompts and ask builders; callers fetch
# systems once per run and render asks through `ask`.

HONESTY = (" If your instructions are impossible to satisfy, escalate and "
           "say so plainly rather than working around it.")

# Every ask opens with this line: the rule itself lives in
# protocol/panel-protocol.md and the judge briefs — the ask only asks for
# the report, and the capability handshake reads it before the reply is.
TOOLS_ASK = ("The first line of your reply is `tools: <the tools you actually hold, "
             "comma-separated>`.\n")

LENSES = [
    {
        "label": "correctness",
        "name": "Correctness reviewer",
        "system": ("You are the correctness reviewer on a code review panel. You read whole diffs, follow call sites, "
                   "and report only defects a reasonable author would fix: logic errors, broken edge cases, wrong or missing "
                   "error handling, concurrency hazards, contract violations between caller and callee. Never style, never "
                   "speculation, never pre-existing issues the change does not touch." + HONESTY),
        "focus": "logic errors, broken edge cases, wrong or missing error handling, concurrency hazards, broken contracts between caller and callee.",
    },
    {
        "label": "security",
        "name": "Security reviewer",
        "system": ("You are the security reviewer on a code review panel. You read whole diffs and trace untrusted data from "
                   "where it enters to where it is used. You report only real, demonstrable vulnerabilities and exposure "
                   "changes a reasonable author would fix — not checklist theater, not speculation." + HONESTY),
        "focus": "untrusted input paths, injection, secrets and token handling, unsafe deserialization, permission changes, destructive operations.",
    },
    {
        "label": "quality",
        "name": "Quality and tests reviewer",
        "system": ("You are the quality-and-tests reviewer on a code review panel. You read whole diffs and judge what the next "
                   "reader pays for. You report complexity that obscures, over-engineering, misleading names, comments and docs "
                   "that drift from the code, test problems — changed behavior with no test covering it, tests that cannot "
                   "fail — and design fit: whether the change follows the patterns the surrounding code already establishes. "
                   "Never pure style or formatting; the repo's checks own those." + HONESTY),
        "focus": ("complexity the next reader pays for, over-engineering, misleading names, comments and docs that drift from the code, "
                  "and tests — behavior this change alters with no test covering it, tests that cannot fail, and design fit — whether "
                  "the change follows the patterns the surrounding code already establishes instead of inventing a parallel way."),
    },
]

GENERAL = {
    "label": "general",
    "name": "General reviewer",
    "system": ("You are the sole reviewer on a small change. You combine three lenses — correctness (logic, edge cases, "
               "error handling), security (untrusted input, secrets, permissions), and quality (complexity, tests that fail "
               "to cover changed behavior, design fit with the patterns the surrounding code establishes) — and report only "
               "defects a reasonable author would fix. Never style, never speculation, never pre-existing issues the change "
               "does not touch." + HONESTY),
    "focus": ("correctness (logic, edge cases, error handling), security (untrusted input, secrets, permissions), and quality "
              "(complexity, tests that fail to cover changed behavior, design fit with the patterns the surrounding code establishes)."),
}

TRIAGE_SYSTEM = ("You are the triage editor of a code review panel. Reviewers hand you their raw findings lens by lens; you "
                 "dedupe across lenses, enforce the flagging bar (real, introduced by the change, actionable), and drop style "
                 "nits, speculation and pre-existing issues with a one-line reason. You are stingy but never suppress a real "
                 "defect to keep the count down.")

FIXER_SYSTEM = ("You are the author and fixer of this change. You receive confirmed review findings and fix them in the "
                "working tree. Minimal, surgical fixes in the repo's own style — no refactors beyond what a finding requires. "
                "Never commit. Never weaken, skip, or delete a test to make a finding go away; if a fix legitimately changes "
                "behavior, pin the corrected behavior in the test. If a finding is wrong or cannot be fixed, say so in skipped "
                "with why rather than pretending." + HONESTY)

FIX_REVIEW_SYSTEM = ("You are the fresh-eyes reviewer for an author's fixes. The author cannot see their own gaps; you can. You "
                     "read only the cumulative diff of the paths the author changed, and you report NEW defects those fixes "
                     "introduce — never the original findings, which separate verifiers own." + HONESTY)

SCOUT_SYSTEM = ("You are the preflight scout of a code review panel. Before the reviewers read the target, you explore the "
                "codebase and map the modules, conventions and risk areas they will judge against. You report a map, never "
                "findings — defects belong to the reviewers, and a map entry is context to verify, not evidence to cite." + HONESTY)

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
# A judge stage's system prompt is its brief's body, read from agents/ at
# call time — the brief is the one copy (D-027).
BRIEF_SYSTEMS = {"confirm": "spec-review-confirmer.md", "verify": "spec-review-verifier.md"}


def brief_body(name):
    try:
        text = (SKILL_DIR / "agents" / name).read_bytes().decode("utf-8")
    except OSError as e:
        raise ValueError(f"agents/{name}: {e.strerror or e}") from None
    except UnicodeDecodeError:
        raise ValueError(f"agents/{name}: not UTF-8") from None
    m = FRONTMATTER.match(text)
    if not m:
        raise ValueError(f"agents/{name}: no frontmatter block")
    return text[m.end():]


def jdump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


def jd(obj):
    # Matches JS JSON.stringify's compact output byte-for-byte.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _base(ctx):
    return ctx.get("base") or "HEAD"


# --- reader files ------------------------------------------------------------
# A panel reader holds no shell: what it used a git command for, the oracle
# writes into the run folder and the ask names the file.

READER_DIRNAME = "reader-files"
NO_RUN_FOLDER = ("a reader ask names files the oracle writes into the run folder — ctx.run_dir is "
                 "missing or is not a run folder (no run.json); pass the path `O run-init` returned")


class NoRunFolder(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def _is_run_dir(v) -> bool:
    return isinstance(v, str) and bool(v) and (Path(v) / "run.json").is_file()


def _run_dir(ctx) -> Path:
    if not _is_run_dir(ctx.get("run_dir")):
        raise NoRunFolder("")
    return Path(ctx["run_dir"])


# run-init's layout: <repo>/.spec-review/runs/<run-id>
def _run_repo(run_dir: Path) -> Path:
    return run_dir.parents[2]


def _repo_root(ctx):
    if ctx.get("repo_abs"):
        return ctx["repo_abs"]
    return str(_run_repo(Path(ctx["run_dir"]))) if _is_run_dir(ctx.get("run_dir")) else None


def _repo_path(ctx, p):
    root = _repo_root(ctx)
    return f"{root}/{p}" if root else p


def _repo_block(ctx, shell=False):
    root = _repo_root(ctx)
    if not root:
        return ""
    return (f"The repository under review lives at \"{root}\" — treat that directory as the repo root "
            "(AGENTS.md / CLAUDE.md / the Makefile live there; every path below is absolute)."
            + (f" Run any git command as `git -C {root} ...`.\n" if shell else "\n"))


def _write_reader_file(ctx, name: str, data: bytes) -> Path:
    folder = _run_dir(ctx) / READER_DIRNAME
    folder.mkdir(exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    return path


def _reader_git(ctx, args: list) -> tuple[bytes | None, str]:
    try:
        r = subprocess.run(["git", "-C", str(_run_repo(_run_dir(ctx))), *args], capture_output=True)
    except OSError as e:
        return None, f"{type(e).__name__}: {e}"
    if r.returncode != 0:
        # git can answer a usage error with its whole help text
        lines = r.stderr.decode("utf-8", "replace").strip().splitlines()
        return None, lines[0][:200] if lines else f"exit {r.returncode}"
    return r.stdout, ""


def _write_diff(ctx, name: str, path: str | None = None) -> tuple[Path | None, str]:
    base = str(_base(ctx))
    if base.startswith("-"):
        return None, f"base {base!r} is not a revision"
    data, reason = _reader_git(ctx, [*GIT_DIFF, base] + (["--", path] if path is not None else []))
    if data is None:
        return None, reason
    return _write_reader_file(ctx, name, data), ""


def _hunk_name(path: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]", "-", path)[-80:]
    return f"hunk-{slug}-{hashlib.sha256(path.encode('utf-8', 'replace')).hexdigest()[:8]}.patch"


def _intent_block(ctx):
    t = ctx.get("intent") or ""
    if not t:
        return ""
    return ("What this change is supposed to do (the author's stated intent):\n" + t + "\n" +
            "Judge the change against that intent: a deliberate choice the intent states up front is an "
            "intentional behavior change, not a finding — but stated intent never waives a demonstrable defect.\n")


def _untracked_block(ctx):
    files = ctx.get("untracked") or []
    if not files:
        return ""
    return ("The change also adds these untracked files, which the diff file does not show — read each one in "
            "full as new code introduced by this change:\n" + "\n".join(f"- {_repo_path(ctx, f)}" for f in files) + "\n")


def _gate_sentence(ctx):
    return f"The mechanical gate ran before you started: {ctx['gate_line']}."


def _test_hunks_block(ctx, verdict):
    hunks = ctx.get("test_hunks") or []
    if not hunks:
        return ""
    return ("The author's edits in this round touched test files — removed assertion lines and added skip "
            "markers, per file:\n" + jdump(hunks)
            + "\nCheck each one: a fix that deletes, loosens or skips a test to make a finding go away is not a "
            f"fix — {verdict}.\n")


def _scout_block(ctx):
    m = ctx.get("scout_map")
    if not m:
        return ""
    mods = "; ".join(f"{x['name']} ({x['path']}) — {x['role']}" for x in m.get("modules", []))
    return ("Codebase map from the preflight scout — context to start from; verify against the code, "
            "never cite it as evidence:\n"
            f"- modules: {mods or '(none mapped)'}\n"
            f"- conventions: {'; '.join(m.get('conventions', [])) or '(none mapped)'}\n"
            f"- risk areas: {'; '.join(m.get('riskAreas', [])) or '(none mapped)'}\n")


def _inventory_block(ctx, files):
    tree, reason = _reader_git(ctx, ["ls-files", "-z"])
    listing = [f for f in tree.decode("utf-8", "replace").split("\0") if f] if tree is not None else None
    body = f"# target files ({len(files)})\n" + "".join(f"{f}\n" for f in files)
    if listing is not None:
        body += f"\n# tracked files in the repository ({len(listing)})\n" + "".join(f"{f}\n" for f in listing)
    path = _write_reader_file(ctx, "inventory.txt", body.encode("utf-8"))
    if listing is None:
        return (f"The full target file list is the file `{path}`; its tracked-tree listing: ABSENT — {reason}. "
                "You hold no shell: explore with your file tools and name the gap.\n")
    return (f"The full target file list and the repository's tracked tree are the file `{path}` — you hold "
            "no shell: read them there and explore with your file tools.\n")


def _scout_ask(ctx):
    files = ctx["files"]
    listed = files[:40]
    inventory = _inventory_block(ctx, files)
    target = (f"A whole-project review is about to start. Its target is the repo's tracked source files — the "
              f"{len(files)} files the panel will read, and the modules they live in.\n" if ctx["project"]
              else "A change review is about to start. The change (its diff plus any untracked new files) touches "
              "these files:\n")
    more = (f"\n- ... and {len(files) - len(listed)} more, all in the target file list"
            if len(files) > len(listed) else "")
    return (target + _repo_block(ctx)
            + "\n".join(f"- {_repo_path(ctx, f)}" for f in listed) + more + "\n"
            + inventory
            + "You are the preflight scout: before the panel reads the target, explore the codebase and map the ground "
            "the reviewers will stand on.\n"
            "1. modules — the modules the target files live in, plus the modules they depend on and are depended on "
            "by (name, path, one-line role each; stay within two hops of the target).\n"
            "2. conventions — the patterns the surrounding code already establishes, the ones design fit is judged "
            "against (error-handling idiom, test layout, naming, module boundaries); read AGENTS.md or CLAUDE.md at "
            "the root first if one exists.\n"
            "3. riskAreas — the places in or near the target that deserve the reviewers' extra attention (hotspots, "
            "tricky call paths, concurrency or parsing edges), one line each with its path.\n"
            "Read-only: do not edit anything, do not report defects — findings are the reviewers' job; "
            "you produce the map they start from. Verify every entry against the code as it stands: an empty list "
            "for a small repo is honest, a guessed entry is not. Keep it tight — "
            "at most 8 modules, 6 conventions, 6 risk areas; the map orients, it does not enumerate.")


NO_DIFF = ("You hold no shell and nothing else carries the diff: do not work around it. Report "
           "`not run: <why>` instead of a findings list — an empty list would read as a clean diff.")


def _review_ask(ctx):
    ld = ctx["lens"]
    over = (" (diff over the harness size cap — page through the diff file with your Read tool's offset and "
            "limit until you have seen all of it)" if ctx.get("over_cap") else "")
    diff = _write_diff(ctx, "diff.patch")
    scope = (f"the diff file `{diff[0]}` — {ctx['files_n']} files, ~{ctx['lines']} added lines{over}"
             if diff[0] else f"diff file ABSENT — {diff[1]}")
    step = ("1. Read the FULL diff from that file — do not stop at the first issue. Open the changed files "
            "for context wherever the diff alone is ambiguous; check call sites when a defect depends on them.\n"
            if diff[0] else "1. " + NO_DIFF + "\n")
    return ("Review the change in this repository: " + scope + ".\n" + _repo_block(ctx) + _scout_block(ctx)
            + step + _untracked_block(ctx)
            + "2. If AGENTS.md or CLAUDE.md exists at the repo root, read it first and cite any rule a finding violates.\n"
            f"3. Report only findings from your lens: {ld['focus']}\n" + _intent_block(ctx)
            + "Each finding also carries impact: one sentence on what the defect breaks and when it bites (which callers, "
            "what data is at risk). Omit it only for minor, low-severity items.\n"
            "A finding must be: discrete and actionable; introduced by this change; demonstrable from the code (quote the "
            "deciding lines in evidence); something the author would reasonably fix. Exclude: speculative might-fail "
            "concerns, pre-existing problems the change does not worsen, style/formatting (the repo's checks own those), "
            "and intentional behavior changes.\n" + SEVERITY_LADDER + "\n"
            "Cite every finding as path:line on the new side of the diff. An empty findings list is the expected answer "
            "for a clean diff — never invent one to seem busy.\n"
            "Do not edit any file. " + _gate_sentence(ctx) + " Do not re-run the test suites; spend your turn on "
            "what only a reader can see.")


def _review_ask_project(ctx):
    ld = ctx["lens"]
    scope = (f"part {ctx['part']} of {ctx['parts']} of the project's tracked source files ({ctx['candidates']}"
             " files in total — your sibling reviewers of the same lens read the other parts; report only "
             "what you find in the files below)")
    part = _write_reader_file(ctx, f"part-{ctx['part']}-of-{ctx['parts']}.txt",
                              "".join(f"{f}\n" for f in ctx["files"]).encode("utf-8"))
    return ("Review the current state of this project's code. There is no diff — the target is " + scope + ":\n"
            + "\n".join(f"- {_repo_path(ctx, f)}" for f in ctx["files"]) + "\n"
            + f"This part's file list is also the file `{part}`.\n"
            + _repo_block(ctx) + _scout_block(ctx)
            + "1. Read EVERY target file in full — do not stop at the first issue. Check call sites outside the list "
            "whenever a defect depends on them.\n"
            "2. If AGENTS.md or CLAUDE.md exists at the repo root, read it first and cite any rule a finding violates.\n"
            f"3. Report only findings from your lens: {ld['focus']}\n"
            "Each finding also carries impact: one sentence on what the defect breaks and when it bites (which callers, "
            "what data is at risk). Omit it only for minor, low-severity items.\n"
            "A finding must be: discrete and actionable; present in the code as it stands; demonstrable from the code "
            "(quote the deciding lines in evidence); something the author would reasonably fix. Exclude: speculative "
            "might-fail concerns, style/formatting (the repo's checks own those), and deliberate design choices the "
            "team has clearly signed off on.\n" + SEVERITY_LADDER + "\n"
            "Cite every finding as path:line in the current tree. An empty findings list is the expected answer "
            "for clean code — never invent one to seem busy.\n"
            "Do not edit any file. " + _gate_sentence(ctx) + " Do not re-run the test suites; spend your turn on "
            "what only a reader can see.")


def _triage_ask(ctx):
    return (f"Raw findings from the {ctx['lens_label']} reviewer for the change under review:\n"
            + jdump(ctx["findings"]) + "\n" + _intent_block(ctx)
            + "You are the triage editor. For each finding, keep it or drop it. Keep = it meets the bar — real, "
            "introduced by this change, actionable, worth the author's attention. Drop = a duplicate of another finding "
            "in this same list, a style nit, speculation, or a pre-existing issue. Never drop something "
            "merely because it is inconvenient, and never keep what the repo's own checks already decide. Give every "
            "dropped item a one-line reason.")


def _triage_ask_project(ctx):
    return (f"Raw findings from the {ctx['lens_label']} reviewer(s) for the project code under review:\n"
            + jdump(ctx["findings"])
            + "\nYou are the triage editor. For each finding, keep it or drop it. Keep = it meets the bar — real, "
            "present in the code as it stands, actionable, worth the author's attention. Drop = a duplicate of a finding "
            "you have already kept from another lens, a style nit, or speculation. Never drop something merely because "
            "it is inconvenient, and never keep what the repo's own checks already decide. Give every "
            "dropped item a one-line reason.")


def _cross_lens_ask(ctx):
    return ("Kept findings from every lens after per-lens triage of the change under review:\n"
            + jdump(ctx["kept"])
            + "\nYou are the triage editor making the final cross-lens pass. Drop a finding ONLY if it duplicates another "
            "kept finding — the same underlying defect reported twice. When two entries describe one defect, keep the "
            "more precise one and drop the other with a reason naming its twin. Never drop anything else here; "
            "per-lens triage already enforced the flagging bar. Return the kept findings with their lens field intact.")


NO_HUNK = ("You hold no shell and nothing else carries the change to that path: do not work around it — "
           "the finding is `unconfirmed`, its note `not run: <why>`.")


def _confirm_ask(ctx):
    finding = ctx["finding"]
    path = str(finding.get("where") or "").split(":")[0]
    if not path:
        hunk = "Hunk file: ABSENT — the finding names no path. " + NO_HUNK + "\n"
    elif path in (ctx.get("untracked") or []):
        hunk = (f"`{path}` is an untracked file — new code in its entirety, so there is no hunk file: the "
                "whole file is the change.\n")
    else:
        wrote = _write_diff(ctx, _hunk_name(path), path)
        if wrote[0] is None:
            hunk = f"Hunk file: ABSENT — {wrote[1]}. " + NO_HUNK + "\n"
        elif wrote[0].stat().st_size == 0:
            hunk = (f"The hunk file `{wrote[0]}` is EMPTY: the change does not touch `{path}`, so the finding "
                    "predates the change — answer unconfirmed.\n")
        else:
            hunk = (f"The change to that path is the hunk file `{wrote[0]}`: the cited lines must be inside "
                    "what it shows the change touching.\n")
    return ("You are an independent confirmer. A reviewer reported this finding on the change under review:\n"
            + jdump(finding)
            + "\nVerify it from the code alone. Read the file at that location; confirm the cited lines exist and the claim "
            "holds; confirm this change introduced it.\n"
            + _repo_block(ctx) + hunk
            + "Check a call site if the claim depends on one. Do not edit anything, and do not re-run the repo's test suites.\n"
            + _untracked_block(ctx)
            + "If the claim holds and the change introduced it, answer verified. If you cannot reproduce it, or it predates "
            "the change, answer unconfirmed and say what you saw instead.")


def _confirm_ask_project(ctx):
    return ("You are an independent confirmer. A reviewer reported this finding in the project's code:\n"
            + jdump(ctx["finding"])
            + "\nVerify it from the code alone. Read the file at that location; confirm the cited lines exist and the "
            "claim holds. Check a call site if the claim depends on one. Do not edit anything, and do not re-run the "
            "repo's test suites.\n"
            "If the claim holds, answer verified. If you cannot reproduce it, answer unconfirmed and say what you saw "
            "instead.")


def _final_ask(ctx):
    diff = _write_diff(ctx, "diff.patch")
    judge = (f"Read the diff file `{diff[0]}` wherever you need to judge it, and read the test files before "
             "claiming a test gap.\n" if diff[0] else
             f"Diff file: ABSENT — {diff[1]}. You hold no shell: do not work around it — judge from what you "
             "can read, and name the diff you did not see under residualRisks as `not run: <why>`.\n")
    return ("Every kept non-gate finding has now been through independent confirmation:\n"
            + jdump(ctx["summary"])
            + "\n" + _gate_sentence(ctx) + " Produce the final assessment of this change. " + judge + _repo_block(ctx)
            + _untracked_block(ctx) + _intent_block(ctx) + _scout_block(ctx)
            + "risk: low | medium | high — what merging this change as-is would risk. testGaps: behaviors this change "
            "alters that no test covers (empty if none). residualRisks: what remains unverified after the checks and "
            "the review. verdict: two or three sentences — should this merge, and what must the author fix first.")


def _final_ask_project(ctx):
    files = ctx["files"]
    head = ", ".join(_repo_path(ctx, f) for f in files[:10]) + (", ..." if len(files) > 10 else "")
    return ("Every kept non-gate finding has now been through independent confirmation:\n"
            + jdump(ctx["summary"])
            + "\n" + _gate_sentence(ctx) + " Produce the final assessment of the project's code. Read the "
            "target files yourself wherever you need to judge them (" + head
            + "), and read the test files before claiming a test gap.\n"
            + _repo_block(ctx) + _scout_block(ctx)
            + "risk: low | medium | high — the risk in the code as it stands. testGaps: behaviors with no test covering "
            "them (empty if none). residualRisks: what remains unverified after the checks and the review. verdict: two "
            "or three sentences — is the code ready as it stands, and what must be fixed first.")


def _fixer_ask(ctx):
    ctx = {**ctx, "unresolved": [t for t in ctx["unresolved"] if t.get("fix") not in OFF_LOOP_FIX]}
    if ctx["round"] == 1:
        opening = ("Fix the confirmed findings in the project's code:\n" if ctx["project"]
                   else f"Fix the confirmed findings on the change (`git diff {_base(ctx)}`):\n")
        items = [{"id": t["finding"]["id"], "where": t["finding"]["where"], "what": t["finding"]["what"],
                  "evidence": t["finding"]["evidence"], "severity": t["finding"]["severity"],
                  "lens": t["finding"]["lens"],
                  "impact": t["finding"].get("impact") if isinstance(t["finding"].get("impact"), str) else ""}
                 for t in ctx["unresolved"]]
        return (opening + _repo_block(ctx, shell=True) + jdump(items)
                + "\nWork in the working tree; never commit. If AGENTS.md or CLAUDE.md exists at the repo root, read it "
                "before your first edit — the repo's own rules bind your fixes. You may run a single targeted test file "
                "for code you touch, but the repo's checks re-run the moment you finish — do not run them yourself.\n"
                + _intent_block(ctx)
                + "Return addressed (the finding ids you fully fixed), skipped (the finding ids you deliberately left, "
                "with why — either the finding is wrong, and your why will be independently ruled on, or it cannot be "
                "fixed), outOfScope (finding ids whose SOUND fix needs paths or behavior this change must not touch — "
                "name the paths and why; never make that change yourself), changedPaths, and notes (one sentence per "
                "change: what was done and why it is minimal).")
    items = [{"id": t["finding"]["id"], "where": t["finding"]["where"], "what": t["finding"]["what"],
              "evidence": t["finding"]["evidence"], "severity": t["finding"]["severity"],
              "lens": t["finding"]["lens"], "verifier": t.get("fixNote")} for t in ctx["unresolved"]]
    gate_fb = (f"\nThe repo's own checks are currently FAILING after the last round:\n{ctx['gate_feedback']}"
               if ctx.get("gate_feedback")
               else "\nThe repo's own checks passed after the last round.")
    return (f"Round {ctx['round']}. These findings are still unresolved after the previous round — the independent "
            "verifiers said, per item:\n" + jdump(items) + gate_fb + _repo_block(ctx, shell=True)
            + "\nEach finding above carries its full detail. Fix exactly these, same rules as before: minimal, in the "
            "repo's style, never commit, never weaken a test to make a finding go away.")


def _verify_ask(ctx):
    t = ctx["tracked"]
    where = ("in the project's code" if ctx["project"] else "on the change under review")
    finding = {"id": t["finding"]["id"], "where": t["finding"]["where"], "what": t["finding"]["what"],
               "severity": t["finding"]["severity"], "lens": t["finding"]["lens"]}
    return (f"A reviewer confirmed this finding {where}, and the author has since attempted a fix.\n"
            + _repo_block(ctx) + "Finding: " + jd(finding)
            + "\nAuthor's notes: " + (ctx.get("notes") or "(none)")
            + "\nVerify in the CURRENT working tree: read the location and its immediate callers or contract; confirm "
            "the described defect is gone and the fix is minimal and sound.\n"
            + _test_hunks_block(ctx, "answer worse and name the weakened test")
            + "Answer fixed only if the defect itself is resolved — cosmetic proximity is not a fix. Answer unfixed if "
            "it still stands. Answer worse if the fix introduced a new problem (say what, in note).\n"
            "If the author SKIPPED this finding (their reason is in the notes), do not verify a fix — rule on the skip "
            "instead: rejected-valid when the reason holds (the finding was not a real defect the author must fix — "
            "say what the code actually does), rejected-invalid when it does not (the finding stands whatever the "
            "author believes). An unruled skip leaves the finding standing. Do not edit anything.")


def _fix_review_ask(ctx):
    hunks = []
    for p in ctx["paths"]:
        path, reason = _write_diff(ctx, _hunk_name(p), p)
        hunks.append(f"- {p} — hunk file `{path}`" if path else f"- {p} — hunk file: ABSENT — {reason}")
    gate_state = "all passed" if ctx.get("gate_green") else "are currently failing"
    return ("The author fixed review findings by changing:\n"
            + "\n".join(hunks)
            + "\n" + _repo_block(ctx)
            + "Read the cumulative change for exactly these paths from the hunk files above, one per path, and "
            "the current file contents where context matters; an empty hunk file means the diff shows nothing for "
            "that path — an untracked new file, read it in full. You hold no shell: a path whose hunk file is "
            "ABSENT above you did not see — do not work around it; report `not run: <why>` instead of findings. "
            "Judge the fix code as a fresh reviewer on a new change: "
            "report only NEW defects these fixes introduce — the same bar as the panel (real, introduced by these "
            "fixes, demonstrable from the code, the author would fix). Do not re-report the original findings; "
            "separate verifiers own those.\n"
            + _test_hunks_block(ctx, "report it as a high-severity finding naming the weakened test")
            + "An empty findings list is the expected answer for clean fixes. Do not edit anything; the repo's own "
            "checks " + gate_state + " after the fixes.")


def _loop_final_ask(ctx):
    tracked = ctx["tracked"]
    gate_state = "all passed" if ctx.get("gate_green") else "FAILING (see lens 'gate' items)"
    items = [{"id": t["finding"]["id"], "where": t["finding"]["where"], "what": t["finding"]["what"],
              "severity": t["finding"]["severity"], "lens": t["finding"]["lens"],
              "reviewStatus": t["finding"]["confirmation"]["status"], "fix": t["fix"],
              "fixNote": t.get("fixNote")} for t in tracked]
    diff = (None, "") if ctx["project"] else _write_diff(ctx, "diff-with-fixes.patch")
    project_part = ("\nProduce the final assessment of the project's code INCLUDING the fixes — read the target files "
                    "yourself where you need to judge them, and read the test files before claiming a test gap.\n"
                    "risk: the risk in the code as it stands. testGaps: behaviors still without any test covering them. "
                    "residualRisks: what remains unverified. verdict: two or three sentences — is the code ready as it "
                    "stands now? recommendation: merge | fix-first | human — merge means the code is ready as it stands "
                    "(every finding fixed, the checks green, nothing new surfaced); human when judgment calls or "
                    "unconfirmed residue remain. The oracle derives the floor from the tracked findings and rejects a "
                    "claim below it (escalating is always allowed), so claim what the state shows." if ctx["project"] else
                    "\nProduce the final assessment of the change INCLUDING the fixes — "
                    + (f"read the diff file `{diff[0]}` (the change as it now stands, fixes included) where you "
                       "need to judge it, and read the test files before claiming a test gap.\n" if diff[0] else
                       f"diff file: ABSENT — {diff[1]}. You hold no shell: do not work around it — judge from what "
                       "you can read, name the diff you did not see under residualRisks as `not run: <why>`, and "
                       "read the test files before claiming a test gap.\n")
                    + "risk: what merging now would risk. testGaps: behaviors still altered with no test covering them. "
                    "residualRisks: what remains unverified. verdict: two or three sentences — should this merge now? "
                    "recommendation: merge | fix-first | human — merge only if every finding is fixed, the checks are green, "
                    "and nothing new surfaced; human when judgment calls or unconfirmed residue remain. The oracle derives "
                    "the floor from the tracked findings and rejects a claim below it (escalating is always allowed), so "
                    "claim what the state shows.")
    return (f"The fix loop ran {ctx['rounds_used']} round(s). Every tracked finding and its state:\n" + jdump(items)
            + f"\nThe repo's own checks after the final round: {gate_state}."
            f"\nAll paths the author changed: {', '.join(ctx.get('changed_paths', [])) or '(none)'}"
            + _scout_block(ctx) + project_part)


ASK_RENDERERS = {
    "scout": _scout_ask, "review": _review_ask, "review-project": _review_ask_project,
    "triage": _triage_ask, "triage-project": _triage_ask_project, "cross-lens": _cross_lens_ask,
    "confirm": _confirm_ask, "confirm-project": _confirm_ask_project,
    "final": _final_ask, "final-project": _final_ask_project, "fixer": _fixer_ask,
    "verify": _verify_ask, "fix-review": _fix_review_ask, "loop-final": _loop_final_ask,
}


def cmd_systems(_a):
    try:
        briefs = {stage: brief_body(name) for stage, name in BRIEF_SYSTEMS.items()}
    except ValueError as e:
        return stage_err("systems", error=f"brief unreadable: {e}")
    return out(True, lenses=LENSES, general=GENERAL, triage=TRIAGE_SYSTEM, fixer=FIXER_SYSTEM,
               fix_review=FIX_REVIEW_SYSTEM, scout=SCOUT_SYSTEM, honesty=HONESTY, **briefs)


def _render_ask(kind, ctx):
    renderer = ASK_RENDERERS.get(kind)
    if renderer is None:
        raise ValueError(f"unknown ask kind: {kind}")
    try:
        return TOOLS_ASK + renderer(ctx)
    except NoRunFolder:
        raise NoRunFolder(kind) from None


def cmd_ask(a):
    try:
        ctx = json.loads(Path(a.ctx[1:]).read_text(encoding="utf-8")
                         if a.ctx.startswith("@") else a.ctx)
    except (json.JSONDecodeError, OSError) as e:
        return out(False, error=f"ask ctx invalid: {e}")
    try:
        if isinstance(ctx, dict) and isinstance(ctx.get("batch"), list):
            # One probe renders a whole wave of asks, with no extra round trips per agent.
            return out(True, asks=[_render_ask(i.get("kind"), i.get("ctx") or {})
                                   for i in ctx["batch"]])
        return out(True, ask=_render_ask(a.kind, ctx))
    except NoRunFolder as e:
        return stage_err("ask", kind=e.kind, error=NO_RUN_FOLDER)
    except ValueError as e:
        return out(False, error=str(e))


if __name__ == "__main__":
    sys.exit(main())
