#!/usr/bin/env python3
"""spec-release's one script — every fact a release needs, derived from git
and the doc state on each call; nothing is cached between calls.

Subcommands:
  collect                          what is releasable since the last tag
  version                          version sources + the proposed bump
  bump <version> [--write]         set the version in the detected files
  notes <version> [--write|--check|--body]
                                   the changelog section: render, insert,
                                   fact-check, or the GitHub release body
  preflight <version>              the release gate (contracts/run.md)
  cut <version> [--confirm <tag>]  release commit + annotated tag + records
  record <tag> [--write]           the Released lines for a cut tag
  publish <tag> [--confirm <tag>]  push commit + tag, create the GitHub release
  verify <tag> [--outcome pass|fail --note TEXT --write]
                                   the post-release checklist and its record
  status                           where the release stands, and what is next

Without --confirm, cut and publish only print the plan. --confirm <tag> is
passed only after the user's explicit yes to that plan; it re-runs the gate
before acting. Common options: --repo PATH, --json, --tag-prefix P,
--remote NAME, --branch NAME, --only FILE[,FILE].

Exit: 0 ok/green · 1 gate red · 2 usage or environment · 3 nothing to
release · 4 refused (dirty tree, detached HEAD, failed git step).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"

OK, RED, USAGE, NOTHING, REFUSED = 0, 1, 2, 3, 4

SEMVER = re.compile(
    r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?")
TAG = re.compile(
    r"^(?P<prefix>(?:.*[-/@])?v?)(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)$")

DELIVERED = re.compile(r"Delivered\*{0,2}\s*:\s*commit\s+@\s*`?([0-9a-f]{7,40}|-)")
RELEASED = re.compile(r"Released\*{0,2}\s*:\s*(\S+)\s+@\s*`?([0-9a-f]{7,40})")
POST_RELEASE = re.compile(r"Post-release check\*{0,2}\s*:\s*(\S+)\s+(pass|fail)\b")
HEADER = r"^\*\*{key}\*\*\s*:\s*(.+)$"
FR_LINE = re.compile(r"^\s*-\s+\*\*(FR-\d{3})\*\*\s*:\s*(.+)$", re.M)
BREAKING_FIELD = re.compile(r"^\s*(?:-\s*)?\*\*Breaking\*\*\s*:\s*(.+)$", re.M | re.I)
COMPATIBILITY = re.compile(r"^\s*-\s*\*\*Compatibility\*\*\s*:\s*(.+)$", re.M)
NEGATED = re.compile(r"^(?:none|no\b|n/a|not\b)", re.I)
UNBROKEN = re.compile(r"\b(?:non-|no |not |without )break", re.I)
COMMENT = re.compile(r"<!--.*?-->", re.S)
PLACEHOLDER = re.compile(r"^<.*>$|^\.\.\.$|^—?$")
CONVENTIONAL = re.compile(r"^(?P<type>\w+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE:", re.M)
MUST_FIX = re.compile(r"\b(?:must-fix|BLOCK|blocker|security|critical|high)\b", re.I)
RELEASE_SUBJECT = "chore(release):"

LEVEL_BY_TYPE = {"feature": "minor", "bugfix": "patch", "hotfix": "patch",
                 "refactor": "patch", "upgrade": "patch"}
GROUP_BY_TYPE = {"feature": "added", "bugfix": "fixed", "hotfix": "fixed",
                 "refactor": "changed", "upgrade": "changed"}
LEVELS = ("patch", "minor", "major")

CHANGELOG_NAMES = ("CHANGELOG.md", "CHANGELOG", "CHANGES.md", "HISTORY.md",
                   "changelog.md")
DEP_MANIFESTS = ("package.json", "requirements.txt", "requirements-dev.txt",
                 "pyproject.toml", "Pipfile", "setup.cfg", "Cargo.toml",
                 "go.mod", "Gemfile", "composer.json", "pom.xml",
                 "build.gradle", "build.gradle.kts")
VERSION_KEY = re.compile(r'^[+-]\s*"?version"?\s*[:=]')
PY_VERSION_FILES = ("__init__.py", "_version.py", "version.py", "__about__.py")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "build", "dist",
             "__pycache__", "site-packages", ".tox", "target", "specs"}


class Stop(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


# --- git -------------------------------------------------------------------

def run(cmd: list[str], cwd: Path, stdin: str | None = None,
        timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True,
                          text=True, timeout=timeout)


def git(repo: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return run(["git", *args], repo, stdin)


def git_out(repo: Path, *args: str) -> str | None:
    r = git(repo, *args)
    return r.stdout.strip() if r.returncode == 0 else None


def is_ancestor(repo: Path, older: str, newer: str) -> bool:
    return git(repo, "merge-base", "--is-ancestor", older, newer).returncode == 0


def resolve_commit(repo: Path, ref: str) -> str | None:
    return git_out(repo, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}")


def toplevel(path: Path) -> Path:
    top = git_out(path, "rev-parse", "--show-toplevel")
    if not top:
        raise Stop(USAGE, f"{path} is not inside a git repository")
    return Path(top)


def current_branch(repo: Path) -> str | None:
    return git_out(repo, "symbolic-ref", "--quiet", "--short", "HEAD")


def upstream(repo: Path) -> str | None:
    return git_out(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")


def remote_name(repo: Path, wanted: str | None) -> str | None:
    remotes = (git_out(repo, "remote") or "").split()
    if wanted:
        return wanted if wanted in remotes else None
    up = upstream(repo)
    if up and up.split("/", 1)[0] in remotes:
        return up.split("/", 1)[0]
    return "origin" if "origin" in remotes else (remotes[0] if remotes else None)


def default_branch(repo: Path, remote: str | None) -> str | None:
    if remote:
        ref = git_out(repo, "symbolic-ref", "--quiet", f"refs/remotes/{remote}/HEAD")
        if ref:
            return ref.rsplit("/", 1)[-1]
    for name in ("main", "master", "trunk"):
        if git(repo, "rev-parse", "-q", "--verify", f"refs/heads/{name}").returncode == 0:
            return name
    return None


def dirty_paths(repo: Path) -> list[str]:
    out = git(repo, "status", "--porcelain", "--untracked-files=normal").stdout
    paths = []
    for line in out.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip('"'))
    return paths


# --- versions and tags -----------------------------------------------------

def parse_version(text: str) -> tuple | None:
    m = SEMVER.fullmatch(text.strip())
    if not m:
        return None
    pre = m.group("pre")
    pre_key = (1,) if pre is None else (0, *[
        (0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split(".")])
    return (int(m.group("major")), int(m.group("minor")), int(m.group("patch")), pre_key)


def bump_version(version: str, level: str) -> str:
    major, minor, patch, pre = parse_version(version)
    if pre != (1,):
        return f"{major}.{minor}.{patch}"
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def tag_state(repo: Path, wanted_prefix: str | None) -> dict:
    """The tag family in use and its newest version reachable from HEAD."""
    families: dict[str, list[tuple[tuple, str]]] = {}
    for name in (git_out(repo, "tag", "--merged", "HEAD") or "").split():
        m = TAG.match(name)
        if m and parse_version(m.group("version")):
            families.setdefault(m.group("prefix"), []).append(
                (parse_version(m.group("version")), name))
    note = None
    if wanted_prefix is not None:
        prefix = wanted_prefix
    elif len(families) == 1:
        prefix = next(iter(families))
    elif families:
        newest = (git_out(repo, "for-each-ref", "--merged", "HEAD",
                          "--sort=-creatordate", "--format=%(refname:short)",
                          "refs/tags") or "").split()
        prefix = next((TAG.match(t).group("prefix") for t in newest
                       if TAG.match(t) and TAG.match(t).group("prefix") in families), "v")
        note = (f"several tag families reachable ({', '.join(repr(p) for p in sorted(families))}) "
                f"— using {prefix!r}, the most recent; pass --tag-prefix to choose")
    else:
        prefix = "v"
        note = "no version tag reachable from HEAD — this is the first release; tags will read 'v<version>'"
    tags = sorted(families.get(prefix, []))
    last = tags[-1][1] if tags else None
    return {"prefix": prefix, "last_tag": last,
            "last_version": TAG.match(last).group("version") if last else None,
            "families": sorted(families), "note": note}


def _section_span(text: str, header: str) -> tuple[int, int] | None:
    m = re.search(rf"^\[{re.escape(header)}\]\s*$", text, re.M)
    if not m:
        return None
    nxt = re.search(r"^\[", text[m.end():], re.M)
    return m.end(), m.end() + nxt.start() if nxt else len(text)


def _toml_version(text: str, headers: tuple[str, ...]) -> tuple[str, int, int, str] | None:
    for header in headers:
        span = _section_span(text, header)
        if not span:
            continue
        body = text[span[0]:span[1]]
        m = re.search(r"""^version\s*=\s*["']([^"']+)["']""", body, re.M)
        if m:
            return m.group(1), span[0] + m.start(1), span[0] + m.end(1), header
        if re.search(r"""^dynamic\s*=.*["']version["']""", body, re.M):
            return "dynamic", -1, -1, header
    return None


def version_sources(repo: Path) -> list[dict]:
    """Every place the project states its version, with the exact span."""
    found: list[dict] = []

    def add(path: Path, kind: str, version: str, start: int, end: int) -> None:
        found.append({"file": path.relative_to(repo).as_posix(), "kind": kind,
                      "version": version, "start": start, "end": end,
                      "writable": start >= 0})

    vf = repo / "VERSION"
    if vf.is_file():
        text = vf.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"\S+", text)
        if m:
            add(vf, "VERSION file", m.group(0), m.start(), m.end())
    pj = repo / "package.json"
    if pj.is_file():
        text = pj.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^\s{0,4}"version"\s*:\s*"([^"]+)"', text, re.M)
        if m:
            add(pj, "package.json", m.group(1), m.start(1), m.end(1))
    for name, headers in (("pyproject.toml", ("project", "tool.poetry")),
                          ("Cargo.toml", ("package", "workspace.package"))):
        path = repo / name
        if path.is_file():
            hit = _toml_version(path.read_text(encoding="utf-8", errors="replace"), headers)
            if hit:
                add(path, f"{name} [{hit[3]}]", hit[0], hit[1], hit[2])
    for path in _py_version_files(repo):
        text = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"""^__version__\s*=\s*["']([^"']+)["']""", text, re.M)
        if m:
            add(path, "__version__", m.group(1), m.start(1), m.end(1))
    return found


def _py_version_files(repo: Path, depth: int = 3):
    def walk(d: Path, level: int):
        try:
            entries = sorted(d.iterdir())
        except OSError:
            return
        for e in entries:
            if e.is_dir() and level < depth and e.name not in SKIP_DIRS and not e.name.startswith("."):
                yield from walk(e, level + 1)
            elif e.is_file() and e.name in PY_VERSION_FILES:
                yield e
    yield from walk(repo, 0)


# --- doc state -------------------------------------------------------------

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def header(text: str, key: str) -> str | None:
    m = re.search(HEADER.format(key=re.escape(key)), text, re.M)
    if not m:
        return None
    return COMMENT.sub("", m.group(1)).split("<!--")[0].strip() or None


def first_word(value: str | None, default: str) -> str:
    return value.split()[0].strip("`").lower() if value else default


def section(text: str, heading: str, level: int = 2) -> str | None:
    marks = "#" * level
    m = re.search(rf"^{marks}\s+{re.escape(heading)}(?!\w).*$", text, re.M | re.I)
    if not m:
        return None
    nxt = re.search(rf"^#{{1,{level}}}\s", text[m.end():], re.M)
    return text[m.end(): m.end() + nxt.start() if nxt else len(text)]


def clean(text: str | None) -> str:
    return COMMENT.sub("", text or "").strip()


def first_sentence(text: str) -> str:
    flat = " ".join(clean(text).split())
    return re.split(r"(?<=[.!?])\s", flat, maxsplit=1)[0] if flat else ""


def labelled_bullets(body: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"^\s*-\s+\*\*(.+?)\*\*\s*:\s*(.+)$", clean(body), re.M):
        value = m.group(2).strip()
        if not PLACEHOLDER.match(value):
            out[m.group(1).strip()] = value
    return out


def rollout_facts(plan: str) -> dict:
    body = section(plan, "Rollout", 3)
    if body is None:
        return {"present": False}
    text = clean(body)
    if re.match(r"^none\b", text, re.I):
        return {"present": True, "none": text}
    return {"present": True, "none": None, "items": labelled_bullets(text)}


def rollback_rows(tech: str) -> list[dict]:
    m = re.search(r"^##\s+.*rollback.*$", tech, re.M | re.I)
    if not m:
        return []
    body = section(tech, m.group(0).lstrip("#").strip())
    rows = []
    for line in clean(body).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(line.replace("|", "").strip()) <= set("-: "):
            continue
        if cells[0].lower() in ("requirement", "row", "item"):
            continue
        if not PLACEHOLDER.match(cells[-1]) and not cells[0].endswith("###"):
            rows.append({"row": cells[0], "rollback": cells[-1]})
    return rows


DELIVERY_NOTE = ("notes", "delivery.md")
DELIVERED_FIELD = re.compile(r"^[ \t]*\*{0,2}Delivered\*{0,2}[ \t]*:.*$", re.M)
RECORD_LINE = re.compile(r"^[ \t]*\*{0,2}(?:Released|Post-release check)\*{0,2}[ \t]*:")
FACT_BULLET = re.compile(r"^[ \t]*-[ \t]")
BD_ROW = re.compile(r"^\|([^|]+)\|\s*(\d+)\s*\|\s*(\d+)\s*\|([^|]*)\|\s*$", re.M)
BD_SUM_LABELS = ("σ", "sum", "total", "totals", "all")


def delivery_block(spec_dir: Path) -> str:
    """The fact lines under the status holder's Delivered field — the
    delivery-record commit's block; empty on specs that predate it."""
    text = read(holder_path(spec_dir))
    m = DELIVERED_FIELD.search(text)
    if not m:
        return ""
    rest = text[m.end():].splitlines()
    i = 0
    while i < len(rest) and (not rest[i].strip() or RECORD_LINE.match(rest[i])):
        i += 1
    lines = []
    while i < len(rest) and FACT_BULLET.match(rest[i]):
        lines.append(rest[i].strip()[1:].strip())
        i += 1
    return "\n".join(lines)


def delivery_note(spec_dir: Path) -> dict:
    block = delivery_block(spec_dir)
    source = block if block.strip() else read(spec_dir.joinpath(*DELIVERY_NOTE))
    pick = lambda key: [m.group(1).strip() for m in re.finditer(
        rf"^\s*(?:-\s*)?{key}:\s*(.+)$", source, re.M)]
    docs = pick("Docs impact")
    return {"docs_impact": docs[0] if docs else None, "rollback": pick("Rollback"),
            "behavior_preserved": pick("Behavior preserved")}


def burndown_verdicts(holder_text: str) -> dict[str, str]:
    """The Verified column per data row — orchestrator-stamped delivery-pass
    evidence (D-004), never recomputed; an empty dict on a two-column table."""
    verdicts: dict[str, str] = {}
    for m in BD_ROW.finditer(holder_text):
        label = m.group(1).strip().strip("*").strip()
        if label.lower() not in BD_SUM_LABELS:
            verdicts[label] = m.group(4).strip()
    return verdicts


def smoke_checks(spec_dir: Path, spec_md: str, tiny: bool) -> list[dict]:
    if tiny:
        out = []
        for block in re.split(r"(?m)^(?=- \[[ x]\] T\d{3})", section(spec_md, "Tasks") or ""):
            if re.search(r"\bsmoke\b", block, re.I):
                accept = re.search(r"Accept:\s*(.+)", block)
                tid = re.search(r"T\d{3}", block)
                out.append({"id": tid.group(0) if tid else "?",
                            "check": accept.group(1).strip() if accept else block.splitlines()[0]})
        return out
    out = []
    test = read(spec_dir / "test.md")
    for m in re.finditer(r"^##\s+(TC-\d{3})\s*[—-]\s*(.+)$", test, re.M):
        block = section(test[m.start():], m.group(0).lstrip("#").strip()) or ""
        smoke = header_value(block, "Smoke")
        if re.search(r"\bsmoke\b", m.group(2), re.I) or (smoke and not NEGATED.match(smoke)):
            cond = header_value(block, "Pass condition")
            out.append({"id": m.group(1), "title": m.group(2).strip(),
                        "check": cond or m.group(2).strip()})
    return out


def header_value(block: str, label: str) -> str | None:
    m = re.search(rf"\*\*{re.escape(label)}\*\*\s*:\s*(.+)$", block, re.M)
    return m.group(1).strip() if m else None


def breaking_markers(spec_dir: Path) -> list[str]:
    hits = []
    for name in ("spec.md", "tech-spec.md", "/".join(DELIVERY_NOTE)):
        text = clean(read(spec_dir / name))
        for m in BREAKING_FIELD.finditer(text):
            if not NEGATED.match(m.group(1).strip()):
                hits.append(f"{name}: Breaking: {m.group(1).strip()}")
        for m in COMPATIBILITY.finditer(text):
            value = m.group(1).strip()
            if re.search(r"\bbreak", value, re.I) and not UNBROKEN.search(value) \
                    and not NEGATED.match(value):
                hits.append(f"{name}: Compatibility: {value}")
    return hits


def spec_name(spec_dir: Path) -> str:
    if spec_dir.parent.name == "archive":
        return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", spec_dir.name)
    return spec_dir.name


def spec_dirs(repo: Path) -> list[Path]:
    root = repo / "specs"
    if not root.is_dir():
        return []
    live = [d for d in sorted(root.iterdir())
            if d.is_dir() and d.name not in ("context", "archive") and (d / "spec.md").is_file()]
    archive = root / "archive"
    archived = [d for d in sorted(archive.iterdir())
                if d.is_dir() and (d / "spec.md").is_file()] if archive.is_dir() else []
    return live + archived


def holder_path(spec_dir: Path) -> Path:
    spec_md = read(spec_dir / "spec.md")
    return spec_dir / ("spec.md" if first_word(header(spec_md, "Tier"), "full") == "tiny" else "task.md")


def hotfix_target(spec_md: str) -> dict:
    """The declared `**Hotfix for**` tag and `**Fixes spec**` name; empty
    fields when a header is absent or still a template placeholder —
    whether the target resolves is the checker's verdict, never release's."""
    def declared(key: str) -> str:
        value = (header(spec_md, key) or "").strip("`")
        return "" if PLACEHOLDER.match(value) else value
    return {"tag": declared("Hotfix for"), "spec": declared("Fixes spec")}


def spec_facts(repo: Path, spec_dir: Path, backlog: list[str]) -> dict:
    spec_md = read(spec_dir / "spec.md")
    tiny = first_word(header(spec_md, "Tier"), "full") == "tiny"
    holder = holder_path(spec_dir)
    holder_text = read(holder)
    delivered = DELIVERED.search(holder_text)
    name = spec_name(spec_dir)
    title = re.search(r"^#\s+Spec:\s*(.+)$", spec_md, re.M)
    return {
        "name": name,
        "path": spec_dir.relative_to(repo).as_posix(),
        "archived": spec_dir.parent.name == "archive",
        "tier": "tiny" if tiny else "full",
        "type": first_word(header(spec_md, "Type"), "feature"),
        "hotfix_target": hotfix_target(spec_md),
        "status": first_word(header(spec_md, "Status"), "draft"),
        "title": title.group(1).strip() if title else name,
        "what": first_sentence(section(spec_md, "What") or ""),
        "frs": [{"id": m.group(1), "text": m.group(2).strip()} for m in FR_LINE.finditer(spec_md)],
        "holder": holder.relative_to(repo).as_posix(),
        "delivered": delivered.group(1) if delivered else None,
        "verified": burndown_verdicts(holder_text),
        "released": [{"tag": m.group(1), "sha": m.group(2)} for m in RELEASED.finditer(holder_text)],
        "post_release": [{"tag": m.group(1), "outcome": m.group(2)}
                         for m in POST_RELEASE.finditer(holder_text)],
        "breaking": breaking_markers(spec_dir),
        "delivery_note": delivery_note(spec_dir),
        "rollout": {"present": False} if tiny else rollout_facts(read(spec_dir / "plan.md")),
        "rollback_table": [] if tiny else rollback_rows(read(spec_dir / "tech-spec.md")),
        "smoke": smoke_checks(spec_dir, spec_md, tiny),
        "backlog": [line for line in backlog if line.startswith(f"- {name} — ")],
    }


# --- collect ---------------------------------------------------------------

def commits_in(repo: Path, rng: str) -> list[dict]:
    out = git(repo, "log", "--no-merges", "--name-only",
              "--format=%x1e%H%x1f%h%x1f%s%x1f%b%x1d", rng).stdout
    commits = []
    for record in out.split("\x1e")[1:]:
        head, _, files = record.partition("\x1d")
        sha, short, subject, body = (head.split("\x1f") + ["", "", "", ""])[:4]
        cc = CONVENTIONAL.match(subject)
        commits.append({
            "sha": sha, "short": short, "subject": subject.strip(),
            "type": cc.group("type").lower() if cc else None,
            "scope": cc.group("scope") if cc else None,
            "breaking": bool(cc and cc.group("bang")) or bool(BREAKING_FOOTER.search(body)),
            "files": [f for f in files.splitlines() if f.strip()],
        })
    return commits


def owns(commit: dict, spec: dict) -> bool:
    name = spec["name"]
    sha = spec.get("delivered") or ""
    if len(sha) >= 7 and (commit["sha"].startswith(sha) or sha.startswith(commit["short"])):
        return True
    if f"({name})" in commit["subject"] or commit["scope"] == name:
        return True
    return any(f.startswith(f"specs/{name}/") or re.match(
        rf"specs/archive/\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(name)}/", f) for f in commit["files"])


def dependency_changes(repo: Path, base: str | None) -> list[dict]:
    if base is None:
        return []
    specs = [f":(glob)**/{name}" for name in DEP_MANIFESTS]
    out = git(repo, "diff", "--unified=0", base, "HEAD", "--", *specs).stdout
    changes, current = [], None
    for line in out.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif current and line[:1] in "+-" and not line.startswith(("+++", "---")):
            if VERSION_KEY.match(line) or not line[1:].strip():
                continue
            changes.append({"file": current, "change": f"{line[0]} {line[1:].strip()}"})
    return changes


def collect(repo: Path, prefix: str | None) -> dict:
    head = resolve_commit(repo, "HEAD")
    if not head:
        raise Stop(USAGE, "the repository has no commits")
    tags = tag_state(repo, prefix)
    last = tags["last_tag"]
    rng = f"{last}..HEAD" if last else "HEAD"
    commits = commits_in(repo, rng)
    backlog = [l for l in read(repo / "specs" / "BACKLOG.md").splitlines() if l.startswith("- ")]
    notes = []
    if tags["note"]:
        notes.append(tags["note"])
    buckets = {"included": [], "unreachable": [], "untraceable": [], "in_flight": []}
    has_specs = (repo / "specs").is_dir()
    if not has_specs:
        notes.append("no specs/ dir — nothing is traced; the notes come from commit subjects alone")
    for spec_dir in spec_dirs(repo):
        facts = spec_facts(repo, spec_dir, backlog)
        sha = facts["delivered"]
        attributed = [c for c in commits if owns(c, facts)]
        if facts["released"]:
            continue
        if sha is None:
            if attributed:
                facts["commits"] = [c["short"] for c in attributed]
                buckets["in_flight"].append(facts)
            continue
        if sha == "-":
            buckets["untraceable"].append(facts)
            continue
        full = resolve_commit(repo, sha)
        if not full or not is_ancestor(repo, full, "HEAD"):
            buckets["unreachable"].append(facts)
            continue
        if last and is_ancestor(repo, full, last):
            continue
        facts["delivered_full"] = full
        facts["commits"] = [c["short"] for c in attributed]
        buckets["included"].append(facts)
    traced = {c["sha"] for c in commits
              if all(f.startswith("specs/") for f in c["files"]) and c["files"]
              or any(owns(c, s) for s in buckets["included"] + buckets["in_flight"])}
    outside = [{k: c[k] for k in ("sha", "short", "subject", "type", "breaking")}
               for c in commits
               if c["sha"] not in traced and not c["subject"].startswith(RELEASE_SUBJECT)]
    if not last:
        notes.append("first release — dependency changes are not listed (every dependency is new)")
    return {
        "repo": str(repo), "head": head, "branch": current_branch(repo),
        "tag": tags, "range": rng, "specs_dir": has_specs,
        **buckets,
        "outside": outside,
        "deps": dependency_changes(repo, last),
        "backlog": [l for s in buckets["included"] for l in s["backlog"]],
        "notes": notes,
    }


def collect_lines(facts: dict) -> list[str]:
    t = facts["tag"]
    lines = [f"range: {facts['range']} (last tag: {t['last_tag'] or 'none'})"]
    for s in facts["included"]:
        flag = " BREAKING" if s["breaking"] else ""
        lines.append(f"  spec  {s['name']} — {s['type']}{flag} · delivered @ {s['delivered']}"
                     f"{' · archived' if s['archived'] else ''}")
    for s in facts["unreachable"]:
        lines.append(f"  FAIL  {s['name']}: Delivered @ {s['delivered']} is not reachable from HEAD "
                     "— re-point the record (spec-build's `tick.py --redeliver`; /spec-ship does it after a squash-merge)")
    for s in facts["untraceable"]:
        lines.append(f"  WARN  {s['name']}: delivered without git (`commit @ -`) — not traceable to this range")
    for s in facts["in_flight"]:
        lines.append(f"  WARN  {s['name']}: not delivered, yet {len(s['commits'])} commit(s) of it are in range")
    if facts["outside"]:
        lines.append(f"  outside the spec flow: {len(facts['outside'])} commit(s)")
        lines += [f"    {c['short']} {c['subject']}" for c in facts["outside"]]
    for d in facts["deps"]:
        lines.append(f"  deps: {d['file']}: {d['change']}")
    for b in facts["backlog"]:
        lines.append(f"  parked: {b}")
    lines += [f"  note: {n}" for n in facts["notes"]]
    return lines


def nothing_to_release(facts: dict) -> bool:
    return not facts["included"] and not facts["outside"] and not facts["in_flight"] \
        and not facts["unreachable"]


# --- version ---------------------------------------------------------------

def proposal(facts: dict, sources: list[dict]) -> dict:
    reasons, level = [], "patch"

    def raise_to(new: str, why: str) -> None:
        nonlocal level
        reasons.append(f"{why} → {new}")
        if LEVELS.index(new) > LEVELS.index(level):
            level = new

    for s in facts["included"]:
        if s["breaking"]:
            raise_to("major", f"breaking: {s['name']} ({s['breaking'][0]})")
        raise_to(LEVEL_BY_TYPE.get(s["type"], "minor"), f"{s['type']} spec {s['name']}")
    for c in facts["outside"]:
        if c["breaking"]:
            raise_to("major", f"breaking commit {c['short']}")
        elif c["type"] == "feat":
            raise_to("minor", f"feat commit {c['short']}")
    if not reasons:
        reasons.append("only non-feature commits → patch")
    written = sorted({s["version"] for s in sources if s["writable"]})
    last = facts["tag"]["last_version"]
    notes = []
    if len(written) > 1:
        notes.append(f"version sources disagree ({', '.join(written)}) — the user rules which to bump")
    effective = level
    if last:
        if parse_version(last)[3] != (1,):
            notes.append(f"{last} is a pre-release — proposing its final version")
        if parse_version(last)[0] == 0 and level == "major":
            effective = "minor"
            notes.append("pre-1.0 (SemVer §4): a breaking change bumps minor; 1.0.0 is the user's call")
        proposed = bump_version(last, effective)
    elif len(written) == 1 and parse_version(written[0]):
        proposed = written[0]
        notes.append(f"no tag yet — proposing the version already written ({proposed}) as the first release")
    else:
        proposed = "0.1.0"
        notes.append("no tag and no single written version — proposing 0.1.0 as the first release")
    if last and any(parse_version(v) and parse_version(v) != parse_version(last) for v in written):
        notes.append(f"a version source differs from the last tag {last} — check it was not bumped already")
    return {"level": level, "effective_level": effective, "reasons": reasons,
            "current": last, "proposed": proposed,
            "tag": f"{facts['tag']['prefix']}{proposed}", "notes": notes}


# --- changelog -------------------------------------------------------------

def find_changelog(repo: Path) -> Path | None:
    for name in CHANGELOG_NAMES:
        if (repo / name).is_file():
            return repo / name
    return None


VERSION_HEADING = re.compile(r"^##\s+\[?v?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\]?.*$", re.M)
UNRELEASED = re.compile(r"^##\s+\[?Unreleased\]?[ \t]*$", re.M | re.I)
LINK_FOOTER = re.compile(r"(?:^\[[^\]\n]+\]:[^\n]*(?:\n|\Z))+\s*\Z", re.M)


def split_footer(text: str) -> tuple[str, str]:
    """Keep a Changelog's trailing link references stay at the end of the file."""
    m = LINK_FOOTER.search(text)
    return (text[: m.start()], text[m.start():]) if m else (text, "")


def changelog_style(text: str) -> dict:
    unreleased = UNRELEASED.search(text)
    prior = VERSION_HEADING.search(text)
    kac = bool(re.search(r"^##\s+\[(?:Unreleased|\d)", text, re.M | re.I))
    return {"keep_a_changelog": kac, "unreleased": bool(unreleased),
            "heading_model": prior.group(0) if prior else None}


def section_heading(style: dict, version: str, date: str) -> str:
    model = style["heading_model"]
    if model:
        old = VERSION_HEADING.match(model).group(1)
        heading = model.replace(old, version, 1)
        return re.sub(r"\d{4}-\d{2}-\d{2}", date, heading, count=1)
    return f"## [{version}] - {date}"


def parse_groups(body: str) -> tuple[list[str], dict[str, list[str]]]:
    preamble, groups, current = [], {}, None
    for line in body.splitlines():
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            current = m.group(1)
            groups.setdefault(current, [])
        elif current is None:
            preamble.append(line)
        else:
            groups[current].append(line)
    return preamble, groups


def render_groups(heading: str, preamble: list[str], groups: dict[str, list[str]]) -> str:
    out = [heading, ""]
    pre = "\n".join(preamble).strip()
    if pre:
        out += [pre, ""]
    for name, lines in groups.items():
        body = "\n".join(lines).strip()
        if body:
            out += [f"### {name}", "", body, ""]
    return "\n".join(out).rstrip() + "\n"


def bullet(lines: list[str]) -> str:
    return "\n".join(lines)


HOTFIX_LINEAGE = (("tag", "patches"), ("spec", "fixes"))


def hotfix_lineage(spec: dict) -> str:
    target = spec["hotfix_target"]
    marks = [f"{verb} {target[key]}" for key, verb in HOTFIX_LINEAGE if target[key]]
    return "".join(f" — {mark}" for mark in marks)


def generated_section(facts: dict, version: str, date: str, style: dict) -> str:
    groups = {"added": [], "fixed": [], "changed": []}
    for s in facts["included"]:
        text = s["what"] or s["title"]
        mark = "**Breaking**: " if s["breaking"] else ""
        suffix = hotfix_lineage(s) if s["type"] == "hotfix" else ""
        groups[GROUP_BY_TYPE.get(s["type"], "added")].append(
            f"- {mark}{text} ({s['name']}){suffix}")
    deps = [f"- `{d['file']}`: {d['change']}" for d in facts["deps"][:20]]
    if len(facts["deps"]) > 20:
        deps.append(f"- … and {len(facts['deps']) - 20} more dependency lines")
    upgrade = []
    for s in facts["included"]:
        for marker in s["breaking"]:
            upgrade.append(f"- {s['name']}: {marker.split(': ', 1)[1]}")
        items = s["rollout"].get("items") or {}
        for label in ("Exposure", "Migration order"):
            if label in items:
                upgrade.append(f"- {s['name']}: {label}: {items[label]}")
    known = [f"- {b[2:].split(' — ', 1)[1]} ({b[2:].split(' — ', 1)[0]})" for b in facts["backlog"]]
    outside = [f"- {c['subject']} ({c['short']})" for c in facts["outside"]]
    template = string.Template((TEMPLATES / "changelog-section.md").read_text(encoding="utf-8"))
    rendered = template.safe_substitute(
        heading=section_heading(style, version, date),
        added=bullet(groups["added"]), fixed=bullet(groups["fixed"]),
        changed=bullet(groups["changed"]), dependencies=bullet(deps),
        upgrade=bullet(upgrade), known=bullet(known), outside=bullet(outside))
    first, _, rest = rendered.partition("\n")
    preamble, parsed = parse_groups(rest)
    return render_groups(first, preamble, parsed)


def merge_unreleased(generated: str, unreleased_body: str) -> str:
    heading, _, rest = generated.partition("\n")
    gen_pre, gen_groups = parse_groups(rest)
    pre, groups = parse_groups(unreleased_body)
    for name, lines in gen_groups.items():
        kept = "\n".join(groups.get(name, [])).strip()
        groups[name] = ([kept] if kept else []) + ["\n".join(lines).strip()]
    return render_groups(heading, pre + gen_pre, groups)


def insert_section(text: str, section_text: str, version: str, prev_tag: str | None,
                   tag: str) -> tuple[str, int]:
    """The changelog with the new section placed; returns (text, moved Unreleased lines)."""
    moved = 0
    text, footer = split_footer(text)
    unreleased = UNRELEASED.search(text)
    if unreleased:
        after = text[unreleased.end():]
        nxt = re.search(r"^##\s", after, re.M)
        body = after[: nxt.start()] if nxt else after
        rest = after[nxt.start():] if nxt else ""
        moved = len([l for l in COMMENT.sub("", body).splitlines() if l.strip()])
        if moved:
            head = text[: unreleased.end()] + "\n\n" + merge_unreleased(section_text, body)
        else:
            head = text[: unreleased.end()] + body.rstrip("\n") + "\n\n" + section_text
        text = head + ("\n" + rest if rest else "")
    else:
        first = re.search(r"^##\s", text, re.M)
        if first:
            text = text[: first.start()] + section_text + "\n" + text[first.start():]
        else:
            text = text.rstrip() + "\n\n" + section_text
    link = re.search(r"^\[Unreleased\]:\s*(\S+?/compare/)\S+?\.\.\.HEAD[ \t]*$", footer, re.M | re.I)
    if link and prev_tag:
        base = link.group(1)
        footer = (footer[: link.start()] + f"[Unreleased]: {base}{tag}...HEAD\n"
                  + f"[{version}]: {base}{prev_tag}...{tag}" + footer[link.end():])
    if footer:
        text = text.rstrip("\n") + "\n\n" + footer
    return text, moved


def section_for(text: str, version: str) -> str | None:
    text = split_footer(text)[0]
    for m in VERSION_HEADING.finditer(text):
        if m.group(1) == version:
            nxt = re.search(r"^##\s", text[m.end():], re.M)
            return text[m.start(): m.end() + nxt.start() if nxt else len(text)].rstrip() + "\n"
    return None


def fact_check(repo: Path, facts: dict, section_text: str | None) -> list[dict]:
    if section_text is None:
        return [row("changelog", "fail", "no changelog section for this version — run `notes <version> --write`")]
    rows = []
    for s in facts["included"]:
        if s["name"] not in section_text:
            rows.append(row("changelog", "fail", f"spec {s['name']} is in this release but not in the section"))
    included = {s["name"] for s in facts["included"]}
    every = {spec_name(d) for d in spec_dirs(repo)}
    trailing = re.findall(r"\(([a-z0-9]+(?:-[a-z0-9]+)*)\)[ \t]*$", section_text, re.M)
    for name in sorted(set(trailing) & every - included):
        rows.append(row("changelog", "fail", f"the section names spec {name}, which is not in this release"))
    known = [c["sha"] for c in facts["outside"]] + [s.get("delivered_full", "") for s in facts["included"]]
    for sha in re.findall(r"\(([0-9a-f]{7,40})\)[ \t]*$", section_text, re.M):
        if not any(k.startswith(sha) for k in known):
            rows.append(row("changelog", "fail", f"the section cites commit {sha}, which is not in this range"))
    if "${" in section_text or re.search(r"<[a-z][a-z -]+>", section_text):
        rows.append(row("changelog", "fail", "a template placeholder survives in the section"))
    return rows or [row("changelog", "pass", "every included spec is named; every cited spec and commit is in range")]


# --- gate ------------------------------------------------------------------

def row(name: str, status: str, reason: str) -> dict:
    return {"name": name, "status": status, "reason": reason}


def release_surfaces(repo: Path, only: list[str] | None) -> set[str]:
    changelog = find_changelog(repo)
    files = {changelog.relative_to(repo).as_posix() if changelog else "CHANGELOG.md"}
    files |= {s["file"] for s in version_sources(repo) if not only or s["file"] in only}
    return files


def refuse_dirty(repo: Path, allowed: set[str]) -> None:
    stray = [p for p in dirty_paths(repo) if p not in allowed]
    if stray:
        raise Stop(REFUSED, f"the working tree is dirty outside the release files: {', '.join(stray[:8])}"
                   + (" …" if len(stray) > 8 else "") + " — commit or stash them first")


def ci_row(repo: Path, sha: str) -> dict:
    if not shutil.which("gh"):
        return row("ci", "skip", f"gh not installed — confirm CI is green for {sha[:12]} by hand")
    try:
        r = run(["gh", "run", "list", "--commit", sha, "--json", "name,status,conclusion",
                 "--limit", "100"], repo, timeout=60)
    except subprocess.TimeoutExpired:
        return row("ci", "warn", "gh timed out — confirm CI by hand")
    if r.returncode != 0:
        why = (r.stderr.strip().splitlines() or ["unknown error"])[0]
        return row("ci", "warn", f"gh could not read CI ({why}) — confirm CI by hand")
    try:
        runs = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return row("ci", "warn", "gh returned unreadable output — confirm CI by hand")
    if not runs:
        return row("ci", "warn", f"no CI runs recorded for {sha[:12]} — push it and let CI run, or confirm by hand")
    pending = [x["name"] for x in runs if x.get("status") != "completed"]
    failing = [x["name"] for x in runs if x.get("status") == "completed"
               and x.get("conclusion") not in ("success", "skipped", "neutral")]
    if failing:
        return row("ci", "fail", f"CI red for {sha[:12]}: {', '.join(sorted(set(failing)))}")
    if pending:
        return row("ci", "fail", f"CI still running for {sha[:12]}: {', '.join(sorted(set(pending)))}")
    return row("ci", "pass", f"{len(runs)} CI run(s) green for {sha[:12]}")


def rollback_row(spec: dict) -> dict | None:
    rollout = spec["rollout"]
    if not rollout.get("present") or rollout.get("none"):
        return None
    stated = ("Rollback trigger" in (rollout.get("items") or {})
              or spec["delivery_note"]["rollback"] or spec["rollback_table"])
    if stated:
        return row("rollback", "pass", f"{spec['name']}: rollback path stated")
    return row("rollback", "fail", f"{spec['name']}: plan § Rollout is filled but no rollback path is stated "
               "(Rollback trigger, a tech-spec rollback row, or a delivery-note `Rollback:` line)")


def preflight(repo: Path, args, version: str) -> tuple[list[dict], dict]:
    facts = collect(repo, args.tag_prefix)
    tag = f"{facts['tag']['prefix']}{version}"
    only = args.only.split(",") if args.only else None
    rows = []
    stray = [p for p in dirty_paths(repo) if p not in release_surfaces(repo, only)]
    rows.append(row("tree", "fail", f"dirty outside the release files: {', '.join(stray[:8])}") if stray
                else row("tree", "pass", "clean apart from the release files"))
    remote = remote_name(repo, args.remote)
    branch = current_branch(repo)
    wanted = args.branch or default_branch(repo, remote)
    if branch is None:
        rows.append(row("branch", "fail", "detached HEAD — check out the release branch"))
    elif branch == wanted or re.match(r"^releases?/", branch):
        rows.append(row("branch", "pass", f"on {branch}"))
    else:
        rows.append(row("branch", "fail", f"on {branch}, not the release branch {wanted or '(unknown — pass --branch)'}"))
    up = upstream(repo)
    if up:
        counts = (git_out(repo, "rev-list", "--left-right", "--count", f"{up}...HEAD") or "0 0").split()
        behind, ahead = int(counts[0]), int(counts[1])
        if behind:
            rows.append(row("upstream", "fail", f"{behind} commit(s) behind {up} (as of the last fetch) — pull first"))
        elif ahead:
            rows.append(row("upstream", "warn", f"{ahead} commit(s) not on {up} — CI has not seen them"))
        else:
            rows.append(row("upstream", "pass", f"level with {up} (as of the last fetch)"))
    else:
        rows.append(row("upstream", "warn", "no upstream branch — CI and the remote cannot be checked"))
    rows.append(ci_row(repo, facts["head"]))
    exists = git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode == 0
    rows.append(row("tag", "fail", f"tag {tag} already exists") if exists else row("tag", "pass", f"{tag} is free"))
    sources = [s for s in version_sources(repo) if s["writable"] and (not only or s["file"] in only)]
    stale = [f"{s['file']} ({s['version']})" for s in sources if s["version"] != version]
    if not sources:
        rows.append(row("version", "warn", "no version file detected — the tag alone carries the version"))
    elif stale:
        rows.append(row("version", "fail", f"not yet {version}: {', '.join(stale)} — run `bump {version} --write`"))
    else:
        rows.append(row("version", "pass", f"{len(sources)} version source(s) read {version}"))
    changelog = find_changelog(repo)
    section_text = section_for(read(changelog), version) if changelog else None
    rows += fact_check(repo, facts, section_text)
    for s in facts["unreachable"]:
        rows.append(row("specs", "fail", f"{s['name']}: Delivered @ {s['delivered']} is not reachable from HEAD "
                        "— re-point the record before releasing"))
    for s in facts["in_flight"]:
        rows.append(row("specs", "warn", f"{s['name']}: undelivered work is on the branch ({', '.join(s['commits'])})"))
    if not facts["unreachable"]:
        rows.append(row("specs", "pass", f"{len(facts['included'])} delivered spec(s) included"))
    rows += [r for r in map(rollback_row, facts["included"]) if r]
    for line in facts["backlog"]:
        item = line[2:].split(" — ", 1)[-1].split(" (source:")[0].strip()
        if not MUST_FIX.search(line):
            continue
        known = section_text and "Known issues" in section_text and item[:40] in section_text
        rows.append(row("backlog", "pass" if known else "fail",
                        f"must-fix parked item {'ruled ship-with (in Known issues)' if known else 'needs a ruling'}: {line}"))
    return rows, {"facts": facts, "tag": tag, "section": section_text, "remote": remote, "branch": branch}


def rows_lines(rows: list[dict]) -> list[str]:
    worst = "FAIL" if any(r["status"] == "fail" for r in rows) else "PASS"
    return [f"  {r['status'].upper():5} {r['name']}: {r['reason']}" for r in rows] + [f"  {worst}"]


def red(rows: list[dict]) -> bool:
    return any(r["status"] == "fail" for r in rows)


# --- writes ----------------------------------------------------------------

def write_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def record_line(tier: str, label: str, value: str) -> str:
    return f"**{label}**: {value}" if tier == "full" else f"{label}: {value}"


def place_record(text: str, tier: str, line: str, anchor: re.Pattern) -> str:
    """Full tier: below the anchor line in task.md's header (task.md is not
    frozen). Tiny tier: inside spec.md § Evidence, which the approval freeze
    excludes — a line anywhere else in a tiny spec breaks the freeze."""
    if tier == "tiny":
        m = re.search(r"^## Evidence[ \t]*$", text, re.M)
        if not m:
            return text.rstrip("\n") + f"\n\n## Evidence\n\n{line}\n"
        nxt = re.search(r"^##\s", text[m.end():], re.M)
        end = m.end() + nxt.start() if nxt else len(text)
        body = text[m.end():end].rstrip("\n")
        return text[: m.end()] + body + f"\n{line}\n" + ("\n" + text[end:] if nxt else "")
    m = anchor.search(text) or DELIVERED.search(text)
    lines = text.splitlines(keepends=True)
    if not m:
        return text.rstrip("\n") + f"\n{line}\n"
    idx = text[: m.start()].count("\n") + 1
    while idx < len(lines) and re.match(r"^\*\*(?:Released|Post-release check)\*\*", lines[idx]):
        idx += 1
    return "".join(lines[:idx]) + line + "\n" + "".join(lines[idx:])


def specs_in_tag(repo: Path, tag: str, prefix: str | None) -> tuple[list[dict], str | None]:
    """Delivered specs whose record is reachable from the tag and not from the previous tag."""
    target = resolve_commit(repo, tag)
    if not target:
        raise Stop(USAGE, f"no tag {tag}")
    families = tag_state(repo, prefix)
    versions = []
    for name in (git_out(repo, "tag", "--merged", target) or "").split():
        m = TAG.match(name)
        if m and m.group("prefix") == families["prefix"] and name != tag and parse_version(m.group("version")):
            versions.append((parse_version(m.group("version")), name))
    prev = max(versions)[1] if versions else None
    backlog = [l for l in read(repo / "specs" / "BACKLOG.md").splitlines() if l.startswith("- ")]
    out = []
    for spec_dir in spec_dirs(repo):
        facts = spec_facts(repo, spec_dir, backlog)
        if any(r["tag"] == tag for r in facts["released"]):
            out.append(facts)
            continue
        sha = facts["delivered"]
        full = resolve_commit(repo, sha) if sha and sha != "-" else None
        if full and is_ancestor(repo, full, target) and not facts["released"] \
                and not (prev and is_ancestor(repo, full, prev)):
            out.append(facts)
    return out, prev


def write_records(repo: Path, tag: str, specs: list[dict], dry: bool) -> list[str]:
    sha = git_out(repo, "rev-parse", "--short=12", f"{tag}^{{commit}}")
    touched = []
    for s in specs:
        if any(r["tag"] == tag for r in s["released"]):
            continue
        path = repo / s["holder"]
        line = record_line(s["tier"], "Released", f"{tag} @ {sha}")
        if not dry:
            write_atomic(path, place_record(read(path), s["tier"], line, DELIVERED))
        touched.append(s["holder"])
    return touched


# --- subcommands -----------------------------------------------------------

def emit(args, payload: dict, lines: list[str], code: int = OK) -> int:
    print(json.dumps(payload, indent=2) if args.json else "\n".join(lines))
    return code


def need_version(value: str) -> str:
    value = value[1:] if value.startswith("v") else value
    if not parse_version(value):
        raise Stop(USAGE, f"{value!r} is not a SemVer version (MAJOR.MINOR.PATCH[-pre])")
    return value


def cmd_collect(repo: Path, args) -> int:
    facts = collect(repo, args.tag_prefix)
    dirty = dirty_paths(repo)
    if dirty:
        facts["notes"].append(f"working tree dirty ({len(dirty)} path(s)) — writes will refuse until it is clean")
    if nothing_to_release(facts):
        return emit(args, facts, [f"nothing to release since {facts['tag']['last_tag'] or 'the first commit'}"]
                    + [f"  note: {n}" for n in facts["notes"]], NOTHING)
    code = RED if facts["unreachable"] else OK
    return emit(args, facts, collect_lines(facts), code)


def cmd_version(repo: Path, args) -> int:
    facts = collect(repo, args.tag_prefix)
    sources = version_sources(repo)
    prop = proposal(facts, sources)
    payload = {"sources": [{k: s[k] for k in ("file", "kind", "version", "writable")} for s in sources],
               **prop}
    lines = [f"  source: {s['file']} ({s['kind']}) = {s['version']}" for s in sources] \
        or ["  source: none detected — the tag alone will carry the version"]
    lines += [f"  last tag: {facts['tag']['last_tag'] or 'none'}",
              *[f"  reason: {r}" for r in prop["reasons"]],
              f"  proposed: {prop['proposed']} ({prop['effective_level']}) → tag {prop['tag']}",
              *[f"  note: {n}" for n in prop["notes"]]]
    return emit(args, payload, lines)


def cmd_bump(repo: Path, args) -> int:
    version = need_version(args.version)
    only = args.only.split(",") if args.only else None
    sources = [s for s in version_sources(repo) if s["writable"] and (not only or s["file"] in only)]
    if not sources:
        raise Stop(USAGE, "no writable version source detected (or none matched --only)")
    if args.write:
        refuse_dirty(repo, release_surfaces(repo, only))
    lines = []
    for s in sources:
        path = repo / s["file"]
        if s["version"] == version:
            lines.append(f"  {s['file']}: already {version}")
            continue
        if args.write:
            text = read(path)
            write_atomic(path, text[: s["start"]] + version + text[s["end"]:])
        lines.append(f"  {s['file']}: {s['version']} → {version}{'' if args.write else ' (dry run)'}")
    return emit(args, {"version": version, "files": [s["file"] for s in sources], "written": args.write}, lines)


def cmd_notes(repo: Path, args) -> int:
    version = need_version(args.version)
    facts = collect(repo, args.tag_prefix)
    tag = f"{facts['tag']['prefix']}{version}"
    changelog = find_changelog(repo)
    if args.body:
        return emit_body(repo, args, facts, version, tag, changelog)
    text = read(changelog) if changelog else ""
    existing = section_for(text, version)
    if args.check:
        rows = fact_check(repo, facts, existing)
        return emit(args, {"rows": rows}, rows_lines(rows), RED if red(rows) else OK)
    date = args.date or dt.date.today().isoformat()
    style = changelog_style(text)
    generated = generated_section(facts, version, date, style)
    if not args.write:
        return emit(args, {"section": generated, "changelog": changelog.name if changelog else None,
                           "style": style}, [generated.rstrip()])
    if existing:
        raise Stop(USAGE, f"{changelog.name} already has a {version} section — edit it in place")
    refuse_dirty(repo, release_surfaces(repo, args.only.split(",") if args.only else None))
    if not changelog:
        changelog = repo / "CHANGELOG.md"
        text = (TEMPLATES / "changelog.md").read_text(encoding="utf-8")
    new_text, moved = insert_section(text, generated, version, facts["tag"]["last_tag"], tag)
    write_atomic(changelog, new_text)
    lines = [f"  wrote the {version} section into {changelog.name}"]
    if moved:
        lines.append(f"  moved {moved} Unreleased line(s) into it verbatim — dedupe against the generated bullets")
    return emit(args, {"changelog": changelog.name, "moved_unreleased": moved}, lines)


def github_compare(repo: Path, remote: str | None, prev: str | None, tag: str) -> str:
    url = git_out(repo, "remote", "get-url", remote) if remote else None
    m = re.match(r"^(?:git@github\.com:|https://github\.com/)([^/]+/[^/]+?)(?:\.git)?/?$", url or "")
    if not (m and prev):
        return ""
    return f"Full changelog: https://github.com/{m.group(1)}/compare/{prev}...{tag}"


def release_body(repo: Path, args, facts: dict, version: str, tag: str,
                 changelog: Path | None, specs: list[dict] | None = None) -> str | None:
    text = None
    if changelog and resolve_commit(repo, tag):
        text = git_out(repo, "show", f"{tag}:{changelog.relative_to(repo).as_posix()}")
    if text is None and changelog:
        text = read(changelog)
    sec = section_for(text or "", version)
    if sec is None:
        return None
    body = sec.partition("\n")[2].strip()
    specs = facts["included"] if specs is None else specs
    trace = "\n".join(f"- {s['name']} — delivered @ {s['delivered']}" for s in specs) \
        or "- none — this release is outside the spec flow"
    prev = facts["tag"]["last_tag"] if not resolve_commit(repo, tag) else specs_in_tag(repo, tag, args.tag_prefix)[1]
    template = string.Template((TEMPLATES / "release-notes.md").read_text(encoding="utf-8"))
    return template.safe_substitute(tag=tag, version=version, section=body, specs=trace,
                                    compare=github_compare(repo, remote_name(repo, args.remote), prev, tag)
                                    ).strip() + "\n"


def emit_body(repo, args, facts, version, tag, changelog) -> int:
    specs = specs_in_tag(repo, tag, args.tag_prefix)[0] if resolve_commit(repo, tag) else None
    body = release_body(repo, args, facts, version, tag, changelog, specs)
    if body is None:
        raise Stop(RED, f"no {version} section in the changelog — nothing to render")
    return emit(args, {"tag": tag, "body": body}, [body.rstrip()])


def cmd_preflight(repo: Path, args) -> int:
    version = need_version(args.version)
    rows, ctx = preflight(repo, args, version)
    return emit(args, {"tag": ctx["tag"], "rows": rows}, [f"preflight {ctx['tag']}:", *rows_lines(rows)],
                RED if red(rows) else OK)


def cmd_cut(repo: Path, args) -> int:
    version = need_version(args.version)
    rows, ctx = preflight(repo, args, version)
    tag, facts = ctx["tag"], ctx["facts"]
    only = args.only.split(",") if args.only else None
    dirty = set(dirty_paths(repo))
    staged = sorted(p for p in release_surfaces(repo, only) if p in dirty)
    message = f"{RELEASE_SUBJECT} {tag}"
    holders = [s["holder"] for s in facts["included"]]
    plan = {"tag": tag, "stage": staged, "commit": message,
            "tag_message": f"{tag} + the {version} changelog section",
            "records": [f"{h}: {record_line(s['tier'], 'Released', f'{tag} @ <release commit>')}"
                        for s, h in zip(facts["included"], holders)],
            "record_commit": f"{RELEASE_SUBJECT} record {tag} on delivered specs" if holders else None,
            "rows": rows}
    lines = [f"cut plan for {tag} (local only — nothing leaves this machine):",
             f"  1. stage by path: {', '.join(staged) or '(nothing — bump and notes not written yet)'}",
             f"  2. commit: {message}",
             f"  3. annotated tag {tag} on that commit (message: the {version} section)"]
    if holders:
        lines += [f"  4. Released record in {h}" for h in holders]
        lines.append(f"  5. commit: {plan['record_commit']}")
    lines += ["preflight:", *rows_lines(rows)]
    if not args.confirm:
        return emit(args, plan, lines, RED if red(rows) else OK)
    if args.confirm != tag:
        raise Stop(USAGE, f"--confirm {args.confirm} does not match the planned tag {tag}")
    if red(rows):
        return emit(args, plan, lines + ["refused: the gate is red — nothing was written"], RED)
    if not staged:
        raise Stop(REFUSED, "nothing to commit — write the bump and the changelog section first")
    step(repo, ["add", "--", *staged], "stage the release files")
    step(repo, ["commit", "-m", message], "the release commit")
    tag_text = f"{tag}\n\n{(ctx['section'] or '').partition(chr(10))[2].strip()}\n"
    step(repo, ["tag", "-a", tag, "-F", "-"], "the annotated tag", stdin=tag_text)
    done = [f"  committed {git_out(repo, 'rev-parse', '--short=12', 'HEAD')} and tagged {tag}"]
    if holders:
        specs, _ = specs_in_tag(repo, tag, args.tag_prefix)
        touched = write_records(repo, tag, specs, dry=False)
        if touched:
            step(repo, ["add", "--", *touched], "stage the Released records")
            step(repo, ["commit", "-m", plan["record_commit"]], "the record commit")
            done.append(f"  recorded Released on {len(touched)} spec(s) and committed")
    done.append(f"next: `publish {tag}` shows the push + GitHub release plan — a second yes")
    return emit(args, {**plan, "done": True}, done)


def step(repo: Path, git_args: list[str], what: str, stdin: str | None = None) -> None:
    r = git(repo, *git_args, stdin=stdin)
    if r.returncode != 0:
        why = (r.stderr.strip() or r.stdout.strip()).splitlines()
        raise Stop(REFUSED, f"{what} failed: {why[0] if why else 'git exited ' + str(r.returncode)} "
                   "— stopped there; `status` shows what landed")


def cmd_record(repo: Path, args) -> int:
    specs, _ = specs_in_tag(repo, args.tag, args.tag_prefix)
    touched = write_records(repo, args.tag, specs, dry=not args.write)
    verb = "wrote" if args.write else "would write"
    lines = [f"  {verb} Released: {args.tag} in {h}" for h in touched] or ["  every spec in the tag is already recorded"]
    if args.write and touched:
        lines.append("  commit them by path (asked first): " + " ".join(touched))
    return emit(args, {"tag": args.tag, "holders": touched, "written": args.write}, lines)


def cmd_publish(repo: Path, args) -> int:
    tag = args.tag
    target = resolve_commit(repo, tag)
    if not target:
        raise Stop(USAGE, f"no tag {tag} — cut it first")
    branch = current_branch(repo)
    if branch is None:
        raise Stop(REFUSED, "detached HEAD — check out the release branch")
    if not is_ancestor(repo, target, "HEAD"):
        raise Stop(REFUSED, f"{tag} is not on {branch}")
    if dirty_paths(repo):
        raise Stop(REFUSED, "the working tree is dirty — publish pushes commits, so it must be clean")
    remote = remote_name(repo, args.remote)
    if not remote:
        raise Stop(USAGE, "no git remote — nothing to publish to")
    m = TAG.match(tag)
    version = m.group("version") if m else tag
    gh = shutil.which("gh") is not None
    prerelease = bool(m and parse_version(version) and parse_version(version)[3] != (1,))
    gh_cmd = ["gh", "release", "create", tag, "--title", tag, "--notes-file", "-", "--verify-tag"] \
        + (["--prerelease"] if prerelease else [])
    plan = {"tag": tag, "remote": remote, "branch": branch,
            "push": [f"git push {remote} {branch}", f"git push {remote} refs/tags/{tag}"],
            "release": " ".join(gh_cmd) if gh else None}
    lines = [f"publish plan for {tag} (outward — leaves this machine):",
             f"  1. git push {remote} {branch}   (never --force)",
             f"  2. git push {remote} refs/tags/{tag}",
             f"  3. {' '.join(gh_cmd) + '   (body: notes ' + version + ' --body)' if gh else 'gh not installed — create the release by hand from `notes ' + version + ' --body`'}",
             "  deploy: not this skill — deployment stays with your CI/CD and its owners"]
    if not args.confirm:
        return emit(args, plan, lines)
    if args.confirm != tag:
        raise Stop(USAGE, f"--confirm {args.confirm} does not match {tag}")
    for push in ([branch], [f"refs/tags/{tag}"]):
        r = git(repo, "push", remote, *push)
        if r.returncode != 0:
            why = (r.stderr.strip().splitlines() or ["push rejected"])[-1]
            raise Stop(REFUSED, f"git push {remote} {push[0]} failed: {why} — never forced; "
                       "pull or resolve, then publish again")
    done = [f"  pushed {branch} and {tag} to {remote}"]
    if gh:
        facts = collect(repo, args.tag_prefix)
        specs, _ = specs_in_tag(repo, tag, args.tag_prefix)
        body = release_body(repo, args, facts, version, tag, find_changelog(repo), specs) or f"{tag}\n"
        r = run(gh_cmd, repo, stdin=body, timeout=120)
        if r.returncode != 0:
            why = (r.stderr.strip().splitlines() or ["gh failed"])[0]
            raise Stop(REFUSED, f"the tag is pushed but the GitHub release failed: {why} — "
                       f"retry by hand with `notes {version} --body`")
        done.append(f"  GitHub release: {r.stdout.strip()}")
    done.append(f"next: `verify {tag}` — the post-release checklist for a human to run")
    return emit(args, {**plan, "done": True}, done)


def cmd_verify(repo: Path, args) -> int:
    tag = args.tag
    specs, _ = specs_in_tag(repo, tag, args.tag_prefix)
    checklist = []
    for s in specs:
        items = s["rollout"].get("items") or {}
        if "Post-release check" in items:
            checklist.append({"spec": s["name"], "source": "plan § Rollout", "check": items["Post-release check"]})
        for tc in s["smoke"]:
            checklist.append({"spec": s["name"], "source": tc["id"], "check": tc["check"]})
    lines = [f"post-release checklist for {tag} — run each by hand; this skill deploys and monitors nothing:"]
    lines += [f"  [ ] {c['spec']} ({c['source']}): {c['check']}" for c in checklist] \
        or ["  [ ] no traced checks — no spec in this tag names a post-release check or a smoke TC; "
            "smoke the release by hand"]
    payload = {"tag": tag, "checklist": checklist, "specs": [s["name"] for s in specs]}
    if not args.outcome:
        return emit(args, payload, lines)
    date = dt.date.today().isoformat()
    note = re.sub(r"[<>\n]", " ", args.note or "no note").strip()
    value = f"{tag} {args.outcome} {date} — {note}"
    anchor = re.compile(rf"Released\*{{0,2}}\s*:\s*{re.escape(tag)}\b")
    touched = []
    for s in specs:
        path = repo / s["holder"]
        if any(p["tag"] == tag for p in s["post_release"]):
            continue
        if args.write:
            write_atomic(path, place_record(read(path), s["tier"],
                                            record_line(s["tier"], "Post-release check", value), anchor))
        touched.append(s["holder"])
    verb = "recorded" if args.write else "would record"
    lines.append(f"  {verb} `Post-release check: {value}` in {', '.join(touched) or '(no spec — keep the line yourself)'}")
    if args.outcome == "fail":
        lines.append("  failed: open the fix as a hotfix spec — /spec-define <name> with Type: hotfix "
                     "(a tiny-tier bugfix, failing test first); revert or roll back per the spec's Rollout first if users are hurt")
    return emit(args, {**payload, "outcome": args.outcome, "holders": touched, "written": args.write}, lines)


def cmd_status(repo: Path, args) -> int:
    facts = collect(repo, args.tag_prefix)
    last = facts["tag"]["last_tag"]
    remote = remote_name(repo, args.remote)
    dirty = dirty_paths(repo)
    surfaces = release_surfaces(repo, None)
    state = {"last_tag": last, "dirty": dirty, "unreleased_specs": [s["name"] for s in facts["included"]],
             "outside": len(facts["outside"])}
    lines = [f"last tag: {last or 'none'}"]
    if last:
        on_remote = None
        if remote:
            r = git(repo, "ls-remote", "--tags", remote, f"refs/tags/{last}")
            on_remote = bool(r.stdout.strip()) if r.returncode == 0 else None
        state["last_tag_pushed"] = on_remote
        specs, _ = specs_in_tag(repo, last, args.tag_prefix)
        unrecorded = [s["name"] for s in specs if not any(r["tag"] == last for r in s["released"])]
        unverified = [s["name"] for s in specs if not any(p["tag"] == last for p in s["post_release"])]
        state.update(unrecorded=unrecorded, unverified=unverified)
        lines.append(f"  pushed: {'yes' if on_remote else 'no' if on_remote is False else 'unknown (remote unreachable)'}")
        if unrecorded:
            lines.append(f"  Released record missing on: {', '.join(unrecorded)}")
        if unverified and specs:
            lines.append(f"  post-release check not recorded on: {', '.join(unverified)}")
    stray = [p for p in dirty if p not in surfaces]
    drafted = [p for p in dirty if p in surfaces]
    # a cut that stopped between the tag and the record commit leaves HEAD on the release commit
    cut_interrupted = bool(last) and git_out(repo, "log", "-1", "--format=%s") == f"{RELEASE_SUBJECT} {last}"
    if stray:
        nxt = "refuse: commit or stash the stray changes first"
    elif cut_interrupted and unrecorded:
        nxt = f"record {last} --write, then commit the records"
    elif last and state.get("last_tag_pushed") is False:
        nxt = f"publish {last}"
    elif drafted:
        nxt = "preflight <version>, then cut <version>"
    elif not nothing_to_release(facts):
        nxt = "collect → version → bump/notes → preflight → cut"
    elif last and specs and unverified:
        nxt = f"verify {last}"
    else:
        nxt = "nothing to release"
    state["next"] = nxt
    lines.append(f"  unreleased: {len(facts['included'])} spec(s), {len(facts['outside'])} other commit(s)")
    if drafted:
        lines.append(f"  drafted (uncommitted): {', '.join(drafted)}")
    lines.append(f"next: {nxt}")
    return emit(args, state, lines)


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", default=".")
    common.add_argument("--json", action="store_true")
    common.add_argument("--tag-prefix")
    common.add_argument("--remote")
    common.add_argument("--branch")
    common.add_argument("--only", help="comma-separated version files to bump; the rest stay as they are")
    p = argparse.ArgumentParser(prog="release.py", description=__doc__.split("\n", 1)[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def verb(name: str, *positional: str) -> argparse.ArgumentParser:
        parser = sub.add_parser(name, parents=[common])
        for arg in positional:
            parser.add_argument(arg)
        return parser

    verb("collect")
    verb("version")
    verb("bump", "version").add_argument("--write", action="store_true")
    n = verb("notes", "version")
    mode = n.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--body", action="store_true")
    n.add_argument("--date")
    verb("preflight", "version")
    verb("cut", "version").add_argument("--confirm", metavar="TAG")
    verb("record", "tag").add_argument("--write", action="store_true")
    verb("publish", "tag").add_argument("--confirm", metavar="TAG")
    v = verb("verify", "tag")
    v.add_argument("--outcome", choices=("pass", "fail"))
    v.add_argument("--note")
    v.add_argument("--write", action="store_true")
    verb("status")
    args = p.parse_args(argv)
    handlers = {"collect": cmd_collect, "version": cmd_version, "bump": cmd_bump,
                "notes": cmd_notes, "preflight": cmd_preflight, "cut": cmd_cut,
                "record": cmd_record, "publish": cmd_publish, "verify": cmd_verify,
                "status": cmd_status}
    try:
        repo = toplevel(Path(args.repo).resolve())
        return handlers[args.cmd](repo, args)
    except Stop as stop:
        print(f"ERROR: {stop}", file=sys.stderr)
        return stop.code
    except subprocess.TimeoutExpired as exc:
        print(f"ERROR: {exc.cmd[0]} timed out", file=sys.stderr)
        return USAGE


if __name__ == "__main__":
    sys.exit(main())
