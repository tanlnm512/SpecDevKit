#!/usr/bin/env python3
"""Shared review-state oracle for the spec-code-review workflow dialects.

One stdlib home for the logic both workflow dialects need: target
resolution (diff/branch/pr/project), the mechanical gate, project-file
sharding, finding-ID allocation, carried-findings parsing, and report
markdown assembly (spec: code-review-workflow-extraction FR-001).

Contract (NFR-004/005): every subcommand prints ONE JSON object; success
is {"status": "ok", ...} exit 0, failure is {"status": "error",
"error": ...} exit 1 — a workflow never proceeds on missing state.

Usage:
  review_orchestrator.py scope   --target diff|branch|pr|project
                                [--base REF] [--pr SPEC] [--repo DIR]
                                [--paths TERMS] [--include-gate]
  review_orchestrator.py gate    [--repo DIR] [--base REF] [--tree]
  review_orchestrator.py shard   --files-json LIST [--budget N] [--max-files N]
  review_orchestrator.py id-next --prefix P --used N
  review_orchestrator.py findings-parse (--file PATH | --text STR)
  review_orchestrator.py report  --kind review|fix --data @FILE|STR
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
GATE_SH = SKILL_DIR / "scripts" / "gate.sh"

FAST_MAX_LINES = 400
FAST_MAX_FILES = 5
SUGGEST_SPLIT_LINES = 1000
SUGGEST_SPLIT_FILES = 20
SHARD_TARGET_BYTES = 240000
SHARD_MAX_FILES = 32
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
EXCLUDED_SEGMENTS = [
    "vendor/", "third_party/", "external/", "node_modules/", "dist/",
    "__snapshots__/", ".venv/", "venv/",
]


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


# --- source-file targeting (ported verbatim from the dialects) --------------

def is_excluded_source(path):
    base = path.rsplit("/", 1)[-1]
    if base in EXCLUDED_BASENAMES:
        return True
    if base.endswith((".d.ts", ".min.js", ".min.css", ".pb.go")) or base.endswith("_pb2.py"):
        return True
    return any(seg in path for seg in EXCLUDED_SEGMENTS)


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
    return {"clean": porcelain.strip() == "", "files": files, "added": added}


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
         "number,title,author,baseRefName,baseRefOid,headRefName,headRefOid,state,url,body"],
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
    candidates = [p for p in all_files
                  if is_source_file(p) and not is_excluded_source(p) and matches_path_filter(p, terms)]
    ordered = sorted(candidates, key=lambda p: (-(sizes.get(p, 0)), p))
    return {"files": ordered, "sizes": sizes, "candidates": len(candidates)}


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
        return [{"name": "gate.sh (spec-code-review)", "exit_code": 1,
                 "tail": "gate.sh produced no JSON report"}]
    return [{"name": g.get("name", ""), "exit_code": g.get("exit_code", 0),
             "tail": g.get("tail", "")} for g in parsed]


def gate_note(rows):
    if not rows:
        return ("No repo checks were detected by the gate — this review has no "
                "mechanical floor; the report must say so under notCovered")
    failed = [g["name"] for g in rows if g["exit_code"] != 0]
    if not failed:
        return ("The repo's own checks the gate detected ("
                + "; ".join(g["name"] for g in rows) + ") all passed")
    return ("The repo's own checks the gate detected did NOT all pass — failing: "
            + "; ".join(failed) + " (each failure is recorded as a gate finding)")


def stage_err(stage, **extra):
    doc = {"status": "error", "stage": stage}
    doc.update(extra)
    print(json.dumps(doc))
    return 1


def cmd_scope(a):
    repo_abs = resolve_repo(a.repo)
    result = {"target": a.target, "repo_abs": repo_abs, "base": a.base or ""}
    if a.target == "diff":
        if git(["rev-parse", "-q", "--verify", a.base or "HEAD"], repo_abs).returncode != 0:
            return stage_err("base-unresolved", base=a.base or "HEAD")
        result.update(diff_scope(a.base or "HEAD", repo_abs))
        result["mode"] = "diff"
    elif a.target == "branch":
        base_ref = detect_base_branch(a.base, repo_abs)
        if not base_ref:
            return stage_err("branch-no-base")
        mb = merge_base_with_count(base_ref, repo_abs)
        if mb is None:
            return stage_err("branch-merge-base", base=base_ref)
        sc = diff_scope(mb["sha"], repo_abs)
        result.update({"mode": "branch", "base": base_ref, "merge_base": mb["sha"],
                       "commit_count": mb["count"], **sc})
    elif a.target == "pr":
        if not a.pr:
            return stage_err("pr-no-arg")
        meta = pr_meta(a.pr, repo_abs)
        if meta is None:
            return stage_err("pr-view", pr=a.pr)
        head = git_out(["rev-parse", "HEAD"], repo_abs) or ""
        if not head.strip():
            return stage_err("pr-state")
        dirty = (git_out(["status", "--porcelain"], repo_abs) or "").strip() != ""
        if head.strip() != meta["headRefOid"]:
            # The refusal is unconditional: a dirty tree misattributes
            # uncommitted work to the PR either way.
            if dirty:
                return stage_err("pr-dirty", head_matches=False, head=head.strip())
            prev = head.strip()
            co = subprocess.run(["gh", "pr", "checkout", a.pr], capture_output=True, text=True)
            head = git_out(["rev-parse", "HEAD"], repo_abs) or ""
            if co.returncode != 0 or head.strip() != meta["headRefOid"]:
                return stage_err("pr-checkout")
            result["previous_head"] = prev
        elif dirty:
            return stage_err("pr-dirty", head_matches=True, head=head.strip())
        mb = merge_base_with_count(meta["baseRefOid"], repo_abs)
        if mb is None:
            return stage_err("pr-merge-base", base=meta["baseRefOid"])
        sc = diff_scope(mb["sha"], repo_abs)
        result.update({"mode": "pr", "pr": meta, "merge_base": mb["sha"],
                       "checked_out_head": head.strip(), **sc})
    elif a.target == "project":
        pf = project_files(a.paths, repo_abs)
        if pf is None:
            return stage_err("ls-files")
        parts = shard_files(pf["files"], pf["sizes"])
        result.update({"mode": "project", "files": pf["files"], "sizes": pf["sizes"],
                       "candidates": pf["candidates"], "parts": parts,
                       "part_labels": [part_label(p) for p in parts]})
    else:
        return stage_err("target-unknown", target=a.target)
    result["suggest_split"] = bool(
        result.get("added", 0) > SUGGEST_SPLIT_LINES
        or len(result.get("files", [])) > SUGGEST_SPLIT_FILES
    )
    result["fast_mode_default"] = bool(
        result.get("added", 0) <= FAST_MAX_LINES and len(result.get("files", [])) <= FAST_MAX_FILES
    )
    if a.include_gate:
        rows = gate_rows(repo_abs, result.get("base") or "HEAD", a.target == "project")
        result["gate"] = {"rows": rows, "green": all(g["exit_code"] == 0 for g in rows),
                          "note": gate_note(rows)}
    return out(True, **result)


def cmd_gate(a):
    repo_abs = resolve_repo(a.repo)
    rows = gate_rows(repo_abs, a.base or "HEAD", a.tree)
    return out(True, rows=rows, green=all(g["exit_code"] == 0 for g in rows),
               note=gate_note(rows))


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


FINDING_HEAD = re.compile(r"^### \[([^\s·]+) · (LOW|MEDIUM|HIGH) · (verified|unconfirmed) · ([^\]]+?)\] (.*)$")
FINDING_HEAD_LEGACY = re.compile(r"^### \[(LOW|MEDIUM|HIGH) · (verified|unconfirmed) · ([^\]]+?)\] (.*)$")
FIX_SUFFIX = re.compile(r"^(.*?) · fix: (fixed|unfixed|worse|pending)$")


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
        if it.get("fixStatus") == "fixed":
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
                    "status": "unconfirmed" if it.get("status") == "unconfirmed" else "verified",
                    "note": "carried from the previous review's report",
                },
            },
            "fix": "pending", "fixNote": "carried from the previous review",
        })
    tracked.sort(key=lambda t: SEV_RANK.get(t["finding"]["severity"], 3))
    return tracked


def cmd_findings_parse(a):
    text = a.text if a.text is not None else Path(a.file).read_text(encoding="utf-8")
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
        lines.append(f"### [{f['id']} · {f['severity'].upper()} · {f['status']} · {f['lens']}{fix}] {f['what']}")
        lines.append(f"- where: `{f['where']}`")
        lines.append(f"- evidence: {f['evidence']}")
        if f.get("impact"):
            lines.append(f"- impact: {f['impact']}")
        lines.append("")
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
    assessment = d.get("assessment", {})
    reported = [{
        "id": t["finding"]["id"], "where": t["finding"]["where"], "what": t["finding"]["what"],
        "evidence": t["finding"]["evidence"], "status": t["finding"]["confirmation"]["status"],
        "severity": t["finding"]["severity"], "lens": t["finding"]["lens"],
        "impact": t["finding"].get("impact", ""), "fixStatus": t["fix"],
    } for t in tracked]
    n_high = sum(1 for t in tracked if t["finding"]["severity"] == "high")
    n_fixed = sum(1 for t in tracked if t["fix"] == "fixed")
    rounds = d.get("rounds_used", 0)
    lines = [d.get("title", "Code review report"), "", d.get("mode_line", ""), ""]
    lines += [assessment.get("verdict", ""), "",
              f"## Mechanical gate ({len(gate)} detected check{'' if len(gate) == 1 else 's'}) — "
              + ("nothing detected in this repo — no mechanical floor" if not gate
                 else "green after the final fix round" if gate_green and rounds
                 else "all passed" if gate_green
                 else "RED after the final fix round" if rounds else "RED"), ""]
    for g in gate:
        code = g.get("exit_code", g.get("exitCode", 0))
        if code == 0:
            lines.append(f"- pass — {g['name']}")
        else:
            lines += [f"- **FAIL** — {g['name']}", "", "  ```", f"  {g['tail']}", "  ```"]
    lines += ["", f"## Findings ({len(tracked)} confirmed · {n_high} high · {n_fixed} fixed)", ""]
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
    lines += ["", "## How this was checked", ""] + d.get("checked", []) + [""] + d.get("fix_checked", [])
    return out(True, markdown="\n".join(lines), reported_findings=reported,
               conclusion=d.get("conclusion", ""))


def main(argv=None):
    p = argparse.ArgumentParser(description="spec-code-review shared state oracle")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scope")
    s.add_argument("--target", required=True, choices=["diff", "branch", "pr", "project"])
    s.add_argument("--base"), s.add_argument("--pr"), s.add_argument("--repo")
    s.add_argument("--paths"), s.add_argument("--include-gate", action="store_true")
    s.set_defaults(fn=cmd_scope)
    g = sub.add_parser("gate")
    g.add_argument("--repo"), g.add_argument("--base"), g.add_argument("--tree", action="store_true")
    g.set_defaults(fn=cmd_gate)
    sh = sub.add_parser("shard")
    sh.add_argument("--files-json", required=True), sh.add_argument("--sizes-json")
    sh.add_argument("--budget", type=int, default=SHARD_TARGET_BYTES)
    sh.add_argument("--max-files", type=int, default=SHARD_MAX_FILES)
    sh.set_defaults(fn=cmd_shard)
    i = sub.add_parser("id-next")
    i.add_argument("--prefix", required=True), i.add_argument("--used", type=int, required=True)
    i.set_defaults(fn=cmd_id_next)
    f = sub.add_parser("findings-parse")
    f.add_argument("--file"), f.add_argument("--text")
    f.set_defaults(fn=cmd_findings_parse)
    r = sub.add_parser("report")
    r.add_argument("--kind", required=True, choices=["review", "fix"])
    r.add_argument("--data", required=True)
    r.set_defaults(fn=cmd_report)
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




# --- panel systems + ask rendering (single source, D-014) --------------------
# Ported verbatim from the workflow dialects: one home for the panel's
# system prompts and ask builders. The dialects fetch systems once per
# run and render asks through `ask` — the strings can no longer drift
# between twins (they exist exactly once, here).

HONESTY = (" If your instructions are impossible to satisfy, escalate and "
           "say so plainly rather than working around it.")

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

VERIFY_SYSTEM = ("You are an independent verifier. You receive one reported finding at a time and check it from the code "
                 "alone — the reviewer's claim, quoted lines, and the change that introduced it. You never see the scout's "
                 "map, the author's intent, or the other lenses' findings, and you never edit anything." + HONESTY)


def jdump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


def jd(obj):
    # JS JSON.stringify's compact form — used by verifyAsk exactly as the
    # master writes it (behavior preservation, not style choice)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _repo_path(ctx, p):
    return f"{ctx['repo_abs']}/{p}" if ctx.get("repo_abs") else p


def _repo_block(ctx):
    if not ctx.get("repo_abs"):
        return ""
    return (f"The repository under review lives at \"{ctx['repo_abs']}\" — treat that directory as the repo root "
            "(AGENTS.md / CLAUDE.md / the Makefile live there; every path below is absolute). Run any git command as "
            f"`git -C {ctx['repo_abs']} ...`.\n")


def _intent_block(ctx):
    t = ctx.get("intent") or ""
    if not t:
        return ""
    return ("What this change is supposed to do (the author's stated intent):\n" + t + "\n" +
            "Judge the change against that intent: a deliberate choice the intent states up front is an "
            "intentional behavior change, not a finding — but stated intent never waives a demonstrable defect.\n")


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


def _scout_ask(ctx):
    files = ctx["files"]
    listed = files[:40]
    target = (f"A whole-project review is about to start. Its target is the repo's tracked source files — the "
              f"{len(files)} files the panel will read, and the modules they live in.\n" if ctx["project"]
              else f"A change review is about to start. The change (`git diff {ctx['base']}`) touches these files:\n")
    more = (f"\n- ... and {len(files) - len(listed)} more — map the modules across all of them"
            if len(files) > len(listed) else "")
    return (target + _repo_block(ctx)
            + "\n".join(f"- {_repo_path(ctx, f)}" for f in listed) + more + "\n"
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


def _review_ask(ctx):
    ld = ctx["lens"]
    over = " (diff over the harness size cap — page through it with git diff directly)" if ctx.get("over_cap") else ""
    scope = f"`git diff {ctx['base']}` — {ctx['files_n']} files, ~{ctx['lines']} added lines{over}"
    return ("Review the change " + scope + " in this repository.\n" + _scout_block(ctx)
            + f"1. Run `git diff {ctx['base']}` and read the FULL diff — do not stop at the first issue. Open the changed "
            "files for context wherever the diff alone is ambiguous; check call sites when a defect depends on them.\n"
            "2. If AGENTS.md or CLAUDE.md exists at the repo root, read it first and cite any rule a finding violates.\n"
            f"3. Report only findings from your lens: {ld['focus']}\n" + _intent_block(ctx)
            + "Each finding also carries impact: one sentence on what the defect breaks and when it bites (which callers, "
            "what data is at risk). Omit it only for minor, low-severity items.\n"
            "A finding must be: discrete and actionable; introduced by this change; demonstrable from the code (quote the "
            "deciding lines in evidence); something the author would reasonably fix. Exclude: speculative might-fail "
            "concerns, pre-existing problems the change does not worsen, style/formatting (the repo's checks own those), "
            "and intentional behavior changes.\n"
            "Cite every finding as path:line on the new side of the diff. An empty findings list is the expected answer "
            "for a clean diff — never invent one to seem busy.\n"
            "Do not edit any file. " + ctx["gate_line"] + " before you started, so do not re-run the "
            "test suites; spend your turn on what only a reader can see.")


def _review_ask_project(ctx):
    ld = ctx["lens"]
    scope = (f"part {ctx['part']} of {ctx['parts']} of the project's tracked source files ({ctx['candidates']}"
             " files in total — your sibling reviewers of the same lens read the other parts; report only "
             "what you find in the files below)")
    return ("Review the current state of this project's code. There is no diff — the target is " + scope + ":\n"
            + "\n".join(f"- {_repo_path(ctx, f)}" for f in ctx["files"]) + "\n"
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
            "team has clearly signed off on.\n"
            "Cite every finding as path:line in the current tree. An empty findings list is the expected answer "
            "for clean code — never invent one to seem busy.\n"
            "Do not edit any file. " + ctx["gate_line"] + " before you started, so do not re-run the "
            "test suites; spend your turn on what only a reader can see.")


def _triage_ask(ctx):
    return (f"Raw findings from the {ctx['lens_label']} reviewer for the change under review (`git diff {ctx['base']}`):\n"
            + jdump(ctx["findings"]) + "\n" + _intent_block(ctx)
            + "You are the triage editor. For each finding, keep it or drop it. Keep = it meets the bar — real, "
            "introduced by this change, actionable, worth the author's attention. Drop = a duplicate of another finding "
            "in this same list, a style nit, speculation, or a pre-existing issue. Never drop something "
            "merely because it is inconvenient, and never keep what the repo's own checks already decide (they all "
            "passed). Give every dropped item a one-line reason.")


def _triage_ask_project(ctx):
    return (f"Raw findings from the {ctx['lens_label']} reviewer(s) for the project code under review:\n"
            + jdump(ctx["findings"])
            + "\nYou are the triage editor. For each finding, keep it or drop it. Keep = it meets the bar — real, "
            "present in the code as it stands, actionable, worth the author's attention. Drop = a duplicate of a finding "
            "you have already kept from another lens, a style nit, or speculation. Never drop something merely because "
            "it is inconvenient, and never keep what the repo's own checks already decide (they all passed). Give every "
            "dropped item a one-line reason.")


def _cross_lens_ask(ctx):
    return (f"Kept findings from every lens after per-lens triage (change: `git diff {ctx['base']}`):\n"
            + jdump(ctx["kept"])
            + "\nYou are the triage editor making the final cross-lens pass. Drop a finding ONLY if it duplicates another "
            "kept finding — the same underlying defect reported twice. When two entries describe one defect, keep the "
            "more precise one and drop the other with a reason naming its twin. Never drop anything else here; "
            "per-lens triage already enforced the flagging bar. Return the kept findings with their lens field intact.")


def _confirm_ask(ctx):
    return (f"You are an independent confirmer. A reviewer reported this finding on the change `git diff {ctx['base']}`:\n"
            + jdump(ctx["finding"])
            + f"\nVerify it from the code alone. Read the file at that location; confirm the cited lines exist and the claim "
            "holds; confirm this change introduced it (`git diff " + ctx["base"] + " -- <path>` covers those lines). Check a "
            "call site if the claim depends on one. Do not edit anything, and do not re-run the repo's test suites.\n"
            "If the claim holds and the change introduced it, answer verified. If you cannot reproduce it, or it predates "
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
    return ("Every kept non-gate finding has now been through independent confirmation:\n"
            + jdump(ctx["summary"])
            + f"\n{ctx['gate_line']} before review started. Produce the final assessment of this change. Run `git diff {ctx['base']}"
            "` yourself wherever you need to judge it, and read the test files before claiming a test gap.\n"
            + _intent_block(ctx) + _scout_block(ctx)
            + "risk: low | medium | high — what merging this change as-is would risk. testGaps: behaviors this change "
            "alters that no test covers (empty if none). residualRisks: what remains unverified after the checks and "
            "the review. verdict: two or three sentences — should this merge, and what must the author fix first.")


def _final_ask_project(ctx):
    files = ctx["files"]
    head = ", ".join(_repo_path(ctx, f) for f in files[:10]) + (", ..." if len(files) > 10 else "")
    return ("Every kept non-gate finding has now been through independent confirmation:\n"
            + jdump(ctx["summary"])
            + f"\n{ctx['gate_line']} before review started. Produce the final assessment of the project's code. Read the "
            "target files yourself wherever you need to judge them (" + head
            + "), and read the test files before claiming a test gap.\n"
            + _repo_block(ctx) + _scout_block(ctx)
            + "risk: low | medium | high — the risk in the code as it stands. testGaps: behaviors with no test covering "
            "them (empty if none). residualRisks: what remains unverified after the checks and the review. verdict: two "
            "or three sentences — is the code ready as it stands, and what must be fixed first.")


def _fixer_ask(ctx):
    if ctx["round"] == 1:
        opening = ("Fix the confirmed findings in the project's code:\n" if ctx["project"]
                   else f"Fix the confirmed findings on the change (`git diff {ctx['base']}`):\n")
        items = [{"id": t["finding"]["id"], "where": t["finding"]["where"], "what": t["finding"]["what"],
                  "evidence": t["finding"]["evidence"], "severity": t["finding"]["severity"],
                  "lens": t["finding"]["lens"],
                  "impact": t["finding"].get("impact") if isinstance(t["finding"].get("impact"), str) else ""}
                 for t in ctx["unresolved"]]
        return (opening + _repo_block(ctx) + jdump(items)
                + "\nWork in the working tree; never commit. If AGENTS.md or CLAUDE.md exists at the repo root, read it "
                "before your first edit — the repo's own rules bind your fixes. You may run a single targeted test file "
                "for code you touch, but the repo's checks re-run the moment you finish — do not run them yourself.\n"
                + _intent_block(ctx)
                + "Return addressed (the finding ids you fully fixed), skipped (the finding ids you deliberately left, with "
                "why), changedPaths, and notes (one sentence per change: what was done and why it is minimal).")
    items = [{"id": t["finding"]["id"], "where": t["finding"]["where"], "what": t["finding"]["what"],
              "evidence": t["finding"]["evidence"], "severity": t["finding"]["severity"],
              "lens": t["finding"]["lens"], "verifier": t.get("fixNote")} for t in ctx["unresolved"]]
    gate_fb = (f"\nThe repo's own checks are currently FAILING after the last round:\n{ctx['gate_feedback']}"
               if ctx.get("gate_feedback")
               else "\nThe repo's own checks passed after the last round.")
    return (f"Round {ctx['round']}. These findings are still unresolved after the previous round — the independent "
            "verifiers said, per item:\n" + jdump(items) + gate_fb + _repo_block(ctx)
            + "\nEach finding above carries its full detail. Fix exactly these, same rules as before: minimal, in the "
            "repo's style, never commit, never weaken a test to make a finding go away.")


def _verify_ask(ctx):
    t = ctx["tracked"]
    where = ("in the project's code" if ctx["project"] else f"on the change (`git diff {ctx['base']}`)")
    finding = {"id": t["finding"]["id"], "where": t["finding"]["where"], "what": t["finding"]["what"],
               "severity": t["finding"]["severity"], "lens": t["finding"]["lens"]}
    return (f"A reviewer confirmed this finding {where}, and the author has since attempted a fix.\n"
            + _repo_block(ctx) + "Finding: " + jd(finding)
            + "\nAuthor's notes: " + (ctx.get("notes") or "(none)")
            + "\nVerify in the CURRENT working tree: read the location and its immediate callers or contract; confirm "
            "the described defect is gone and the fix is minimal and sound.\n"
            "Answer fixed only if the defect itself is resolved — cosmetic proximity is not a fix. Answer unfixed if "
            "it still stands. Answer worse if the fix introduced a new problem (say what, in note). Do not edit anything.")


def _fix_review_ask(ctx):
    ra = ctx.get("repo_abs")
    diff_cmd = (f"git -C '{ra}'.replace(/'/g, \"'\\\\''\") diff {ctx['base']} -- <path>" if False else
                (f"git -C " + "'" + ra.replace("'", "'\\''") + "' diff " + ctx["base"] + " -- <path>" if ra
                 else f"git diff {ctx['base']} -- <path>"))
    gate_state = "all passed" if ctx.get("gate_green") else "are currently failing"
    return ("The author fixed review findings by changing:\n"
            + "\n".join(f"- {p}" for p in ctx["paths"])
            + "\n" + _repo_block(ctx)
            + "Read the cumulative diff for exactly these paths (`" + diff_cmd + "`, one per path) and "
            "the current file contents where context matters. Judge the fix code as a fresh reviewer on a new change: "
            "report only NEW defects these fixes introduce — the same bar as the panel (real, introduced by these "
            "fixes, demonstrable from the code, the author would fix). Do not re-report the original findings; "
            "separate verifiers own those.\n"
            "An empty findings list is the expected answer for clean fixes. Do not edit anything; the repo's own "
            "checks " + gate_state + " after the fixes.")


def _loop_final_ask(ctx):
    tracked = ctx["tracked"]
    gate_state = "all passed" if ctx.get("gate_green") else "FAILING (see lens 'gate' items)"
    items = [{"id": t["finding"]["id"], "where": t["finding"]["where"], "what": t["finding"]["what"],
              "severity": t["finding"]["severity"], "lens": t["finding"]["lens"],
              "reviewStatus": t["finding"]["confirmation"]["status"], "fix": t["fix"],
              "fixNote": t.get("fixNote")} for t in tracked]
    project_part = ("\nProduce the final assessment of the project's code INCLUDING the fixes — read the target files "
                    "yourself where you need to judge them, and read the test files before claiming a test gap.\n"
                    "risk: the risk in the code as it stands. testGaps: behaviors still without any test covering them. "
                    "residualRisks: what remains unverified. verdict: two or three sentences — is the code ready as it "
                    "stands now? recommendation: merge | fix-first | human — merge means the code is ready as it stands "
                    "(every finding fixed, the checks green, nothing new surfaced); human when judgment calls or "
                    "unconfirmed residue remain." if ctx["project"] else
                    f"\nProduce the final assessment of the change INCLUDING the fixes — run `git diff {ctx['base']}` yourself "
                    "where you need to judge it, and read the test files before claiming a test gap.\n"
                    "risk: what merging now would risk. testGaps: behaviors still altered with no test covering them. "
                    "residualRisks: what remains unverified. verdict: two or three sentences — should this merge now? "
                    "recommendation: merge | fix-first | human — merge only if every finding is fixed, the checks are green, "
                    "and nothing new surfaced; human when judgment calls or unconfirmed residue remain.")
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
    return out(True, lenses=LENSES, general=GENERAL, triage=TRIAGE_SYSTEM, fixer=FIXER_SYSTEM,
               fix_review=FIX_REVIEW_SYSTEM, scout=SCOUT_SYSTEM, verify=VERIFY_SYSTEM, honesty=HONESTY)


def cmd_ask(a):
    try:
        ctx = json.loads(Path(a.ctx[1:]).read_text(encoding="utf-8")
                         if a.ctx.startswith("@") else a.ctx)
    except (json.JSONDecodeError, OSError) as e:
        return out(False, error=f"ask ctx invalid: {e}")
    if isinstance(ctx, dict) and isinstance(ctx.get("batch"), list):
        # One probe renders a whole wave of asks (NFR-003: no extra
        # round trips per agent spawned).
        asks = []
        for item in ctx["batch"]:
            renderer = ASK_RENDERERS.get(item.get("kind"))
            if renderer is None:
                return out(False, error=f"unknown ask kind: {item.get('kind')}")
            asks.append(renderer(item.get("ctx") or {}))
        return out(True, asks=asks)
    renderer = ASK_RENDERERS.get(a.kind)
    if renderer is None:
        return out(False, error=f"unknown ask kind: {a.kind}")
    return out(True, ask=renderer(ctx))


if __name__ == "__main__":
    sys.exit(main())
