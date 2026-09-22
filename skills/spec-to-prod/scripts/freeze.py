#!/usr/bin/env python3
"""Approval freeze and lifecycle-evidence verification.

The approve gate is human, but its *inputs* must not be mutable after the
user signs them. freeze.py records a content manifest for the approved
intent/evidence documents and audit.py/check.py verify that manifest before
execution and delivery:

  spec.md     canonical hash (the volatile Status line is removed)
  plan.md     exact hash
  survey.md   exact hash
  test.md     exact hash
  tech-spec.md prefix hash/length (only appended D-### decisions may drift)

task.md is deliberately not frozen: it is the lifecycle's status holder.
Its contract-shape protections are traceability checks, the task-body
scope gate, and the closing evidence record.

Usage:
  freeze.py <spec-dir> --record [--repo <path>]
  freeze.py <spec-dir> --record --force [--repo <path>]   # fresh approval only
  freeze.py <spec-dir> --verify [--repo <path>]
  freeze.py -h | --help

--record is run only after explicit user approval. It writes
specs/<name>/approvals/approval.md atomically. --verify writes nothing.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specstate

FROZEN_FILES = ("spec.md", "plan.md", "survey.md", "test.md", "tech-spec.md")
ENTRY = re.compile(
    r"^-\s+`([^`]+)`:\s+(exact|prefix)\s+"
    r"sha256:([0-9a-f]{64})\s+length:(\d+)\s*$",
    re.M,
)
APPROVED_AT = re.compile(
    r"\*\*Approved-at\*\*:\s+`?([0-9a-f]{7,40}|-)`?", re.I
)


def _canonical_spec(text: str) -> bytes:
    """Spec bytes with only the lifecycle Status line removed."""
    return b"".join(
        line.encode("utf-8")
        for line in text.splitlines(keepends=True)
        if not specstate.STATUS_LINE.match(line)
    )


def manifest_values(spec_dir: Path) -> dict[str, tuple[str, str, int]]:
    """Content manifest for the freezeable docs: kind, sha256, byte length."""
    out: dict[str, tuple[str, str, int]] = {}
    for name in FROZEN_FILES:
        path = spec_dir / name
        if not path.exists():
            continue
        raw = path.read_bytes()
        if name == "spec.md":
            raw = _canonical_spec(path.read_text(encoding="utf-8"))
        out[name] = ("prefix" if name == "tech-spec.md" else "exact",
                     hashlib.sha256(raw).hexdigest(), len(raw))
    return out


def render(spec_dir: Path, approved_at: str) -> str:
    vals = manifest_values(spec_dir)
    lines = [
        "# Approval freeze",
        "",
        f"**Approved-at**: `{approved_at}`",
        "**Algorithm**: sha256 over UTF-8 bytes",
        "",
        "Recorded only after explicit user approval. `spec.md` is hashed without",
        "its volatile Status line. `tech-spec.md` is verified as an immutable",
        "prefix so implementation may append D-### decisions. `task.md` is not",
        "frozen because it is the status holder.",
        "",
        "## Frozen contract",
    ]
    for name in FROZEN_FILES:
        if name not in vals:
            continue
        kind, digest, length = vals[name]
        lines.append(
            f"- `{name}`: {kind} sha256:{digest} length:{length}"
        )
    lines += [
        "",
        "Any other change to these files requires a fresh user approval and a",
        "new freeze record.",
        "",
    ]
    return "\n".join(lines)


def record(spec_dir: Path, repo: Path, force: bool = False) -> int:
    if any("NEEDS CLARIFICATION" in (spec_dir / f).read_text(
            encoding="utf-8", errors="replace")
           for f in FROZEN_FILES if (spec_dir / f).exists()):
        print("FAIL: unresolved NEEDS CLARIFICATION marker — do not freeze", file=sys.stderr)
        return 1
    git_ok = specstate.git_available(repo)
    sha = specstate.head_sha(repo) if git_ok else "-"
    text = render(spec_dir, sha or "-")
    out = spec_dir / "approvals" / "approval.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not force:
        print(
            f"FAIL: {out} already exists — a replacement requires a fresh "
            "user approval and --force",
            file=sys.stderr,
        )
        return 1
    fd, tmp = tempfile.mkstemp(prefix=".approval-", dir=str(out.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, out)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    print(f"recorded {out} (approved-at {sha or '-'})")
    return 0


def _commit_exists(repo: Path, sha: str) -> bool:
    if not specstate.git_available(repo):
        return False
    try:
        exists = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", f"{sha}^{{commit}}"],
            capture_output=True, text=True, timeout=10,
        ).returncode == 0
        ancestor = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor",
             sha, "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).returncode == 0
        return exists and ancestor
    except (OSError, subprocess.SubprocessError):
        return False


def verify(spec_dir: Path, repo: Path) -> list[str]:
    """Return human-readable integrity problems; empty means green."""
    path = spec_dir / "approvals" / "approval.md"
    if not path.exists():
        return [f"approval freeze missing: {path.relative_to(spec_dir)}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    problems: list[str] = []
    am = APPROVED_AT.search(text)
    if not am:
        problems.append("approval freeze: missing Approved-at")
    else:
        approved_at = am.group(1)
        if approved_at != "-" and not _commit_exists(repo, approved_at):
            problems.append(
                f"approval freeze: Approved-at commit {approved_at!r} not found "
                "or not an ancestor of HEAD"
            )
    recorded: dict[str, tuple[str, str, int]] = {}
    for name, kind, digest, length in ENTRY.findall(text):
        if name in recorded:
            problems.append(f"approval freeze: duplicate entry for {name}")
        recorded[name] = (kind, digest, int(length))
    current = manifest_values(spec_dir)
    for name in FROZEN_FILES:
        if name not in recorded and name not in current:
            continue
        if name not in recorded:
            problems.append(f"approval freeze: {name} was present but not recorded")
            continue
        if name not in current:
            problems.append(f"approval freeze: frozen {name} is now missing")
            continue
        old, new = recorded[name], current[name]
        if old[0] != new[0]:
            problems.append(f"approval freeze: {name} verification kind changed")
            continue
        if name == "tech-spec.md":
            raw = (spec_dir / name).read_bytes()[: old[2]]
            digest = hashlib.sha256(raw).hexdigest()
            if digest != old[1] or len(raw) != old[2]:
                problems.append(
                    f"approval freeze: {name} approved prefix changed — re-approve"
                )
        else:
            if old != new:
                problems.append(f"approval freeze: {name} changed after approval")
    return problems


def parse_args(argv: list[str]) -> tuple[Path, Path, str, bool] | None:
    spec_dir = repo = None
    mode = ""
    force = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--record", "--verify"):
            mode = arg
        elif arg == "--force":
            force = True
        elif arg == "--repo":
            i += 1
            if i >= len(argv):
                return None
            repo = argv[i]
        elif not spec_dir and not arg.startswith("-"):
            spec_dir = arg
        else:
            return None
        i += 1
    if not spec_dir or mode not in ("--record", "--verify"):
        return None
    return (Path(spec_dir), Path(repo) if repo else Path(spec_dir).parent.parent,
            mode, force)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    parsed = parse_args(argv)
    if parsed is None:
        print(__doc__, file=sys.stderr)
        return 2
    spec_dir, repo, mode, force = parsed
    if not spec_dir.is_dir():
        print(f"FAIL: {spec_dir} is not a directory", file=sys.stderr)
        return 1
    if mode == "--record":
        return record(spec_dir, repo, force)
    problems = verify(spec_dir, repo)
    for problem in problems:
        print(f"FAIL: {problem}")
    print(f"freeze: {'PASS' if not problems else 'FAIL'} ({len(problems)} problem(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
