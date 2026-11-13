#!/usr/bin/env python3
"""Approval freeze and lifecycle-evidence verification.

The approve gate is human, but its *inputs* must not be mutable after the
user signs them. freeze.py records a content manifest for the approved
intent/evidence documents and audit.py/check.py verify that manifest before
execution and delivery:

  spec.md     canonical hash (the volatile Status line is removed; at
              tiny tier also § Evidence, the delivery record, and the
              status markers inside § Tasks — the task list itself is
              frozen)
  plan.md     exact hash
  survey.md   exact hash
  test.md     exact hash
  tech-spec.md prefix hash/length (only appended decisions may drift)

task.md is deliberately not frozen: it is the lifecycle's status holder.
Its contract-shape protections are traceability checks and the task-body
scope gate.

Tiny tier freezes its one file the same way: spec.md is the only entry.
There § Tasks is hashed with its status tokens normalized away
(checkbox state, the (in-progress)/(implemented)/(fix n/5)/(fixed n/5)
markers, `done <date> — <proof>` sub-lines, a `Delivered:` record), so
status progress stays legal while an added, edited, or struck task or
requirement breaks the freeze.

--record writes ONE file: the `## Contract review` section (the review
payload's trio — fingerprint, digest, rulings) followed by the
`## Freeze` manifest. At full tier the review payload the orchestrator
saved is passed as `--review <payload>` (the auditor itself writes
nothing); until migrate.py upgrade retires the old grammar, a
persisted approvals/review.md backs a bare --record the same way.
Three things must be on the review: the docset fingerprint the review
named, the auditor's digest line (`digest: BLOCK <n> ·
WARN <n> · NIT <n> · worst …`), and after that digest one `ruling:`
line per BLOCK it counts. A docset repaired after its review has a new
fingerprint, so the freeze refuses until it is re-reviewed.

--verify treats the Approved-at commit as history once the docset
records its delivery: a squash-merge or rebase rewrites the anchor, and
the delivery record owns the proof from there. It re-checks the folded
review section's shape but never re-hashes the record — the manifest
covers the five frozen files only — and never re-compares the
fingerprint to the live docset, whose legal post-approval drift
(tech-spec appends, task.md status) changes it.

Usage:
  freeze.py <spec-dir> --record [--review <payload>] [--by "<name>"]... [--repo <path>]
  freeze.py <spec-dir> --record --force [--repo <path>]   # fresh approval only
  freeze.py <spec-dir> --verify [--repo <path>]
  freeze.py -h | --help

--record is run only after explicit user approval. It writes
specs/<name>/approvals/approval.md atomically. --verify writes nothing.
--by names who signed off, one `**Approved-by**: <name>` line each
(repeatable, optional — a record without it is the session user's yes).
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
TINY_EVIDENCE_HEADING = "## Evidence"
TASK_STATUS_LINE = re.compile(
    r"^\s*(?:-\s*)?(?:done \d{4}-\d{2}-\d{2} \u2014|fix(?:ed)? \d+ \u2014"
    r"|\*{0,2}Delivered\*{0,2}\s*:)")
TASK_STATUS_MARKER = re.compile(
    r"\s*\((?:in-progress|implemented|fix(?:ed)?\s+\d+/\d+)\)")
TICKED_BOX = re.compile(r"^(\s*)- \[x\]")
ENTRY = re.compile(
    r"^-\s+`([^`]+)`:\s+(exact|prefix)\s+"
    r"sha256:([0-9a-f]{64})\s+length:(\d+)\s*$",
    re.M,
)
APPROVED_AT = re.compile(
    r"\*\*Approved-at\*\*:\s+`?([0-9a-f]{7,40}|-)`?", re.I
)


def _task_line_less_status(line: str) -> str | None:
    """A § Tasks line with its status tokens removed; None when nothing
    but status remains."""
    if TASK_STATUS_LINE.match(line):
        return None
    bare = TASK_STATUS_MARKER.sub("", TICKED_BOX.sub(r"\1- [ ]", line))
    if bare != line and not bare.strip():
        return None
    return bare


def _tasks_less_status(lines: list[str]) -> list[str]:
    kept = [bare for bare in map(_task_line_less_status, lines)
            if bare is not None]
    # a tick or a delivery record may leave blank lines at the tail
    while kept and not kept[-1].strip():
        kept.pop()
    if kept:
        kept[-1] = kept[-1].rstrip("\r\n") + "\n"
    return kept


def _canonical_spec(text: str) -> bytes:
    """Spec bytes less what the lifecycle rewrites: the Status line, and
    at tiny tier § Evidence and the status tokens inside § Tasks — the
    task list is contract, its progress markers are not."""
    tiny = specstate.spec_tier(text) == "tiny"
    kept: list[str] = []
    tasks: list[str] = []
    section = ""
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            kept += _tasks_less_status(tasks)
            tasks = []
            section = line.strip() if tiny else ""
        if section == TINY_EVIDENCE_HEADING or specstate.STATUS_LINE.match(line):
            continue
        (tasks if section == specstate.TASKS_HEADING else kept).append(line)
    return "".join(kept + _tasks_less_status(tasks)).encode("utf-8")


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


def docset_fingerprint(spec_dir: Path) -> str:
    """Short hash over the reviewable docset: the frozen manifest plus
    task.md, which the contract review reads though the freeze leaves it
    free to carry status."""
    h = hashlib.sha256()
    for name, (_kind, digest, _length) in sorted(
            manifest_values(spec_dir).items()):
        h.update(f"{name}:{digest}\n".encode())
    task = spec_dir / "task.md"
    if task.exists():
        h.update(b"task.md:" + hashlib.sha256(task.read_bytes()).digest())
    return h.hexdigest()[:12]


REVIEW_DIGEST = re.compile(
    r"^[ \t>*`-]*digest:[ \t]*BLOCK[ \t]+(\d+)\b", re.M)
REVIEW_FINGERPRINT = re.compile(
    r"Docset fingerprint:[ \t]*`?([0-9a-f]{6,64})`?", re.I)
REVIEW_RULING = re.compile(
    r"^[ \t]*(?:[-*][ \t]+)?\**ruling\b[^\n:]*:[ \t]*\S", re.I | re.M)
REVIEW_LEAD_MARKUP = re.compile(r"^[ \t>*`-]+")
REVIEW_SHAPE = ("`Docset fingerprint: <hash>`, then the auditor's `digest: "
                "BLOCK <n> · WARN <n> · NIT <n> · worst …` line verbatim, "
                "then one `ruling: <finding> — repaired | <the user's "
                "ruling>` line per BLOCK")

REVIEW_EMIT = ("spec-design's `graph.py <spec-dir> --emit-spawns --repair "
               "approve` (writes spawns/wave-<N>/reviewer-contract.md)")


def _is_tiny(spec_dir: Path) -> bool:
    spec = spec_dir / "spec.md"
    return spec.exists() and specstate.spec_tier(
        spec.read_text(encoding="utf-8", errors="replace")) == "tiny"


def approval_steps(spec_dir: Path) -> str:
    """What records an approval — a first one, or the one re-approval
    of a docset approved before the freeze existed. Tiny tier has no
    contract-review record."""
    if _is_tiny(spec_dir):
        return "on the user's explicit yes run `freeze.py <spec-dir> --record`"
    return (f"emit the contract review with {REVIEW_EMIT}, spawn the "
            f"auditor on it, save the review payload ({REVIEW_SHAPE}), then "
            "on the user's explicit yes run `freeze.py <spec-dir> --record "
            "--review <payload>`")


def _review_text(spec_dir: Path, review: str | None) -> str:
    """The review payload's text: the --review file when given, else the
    legacy approvals/review.md the old flow persisted."""
    path = Path(review) if review else spec_dir / "approvals" / "review.md"
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def review_shape_problem(text: str) -> str | None:
    """Why review text is not a complete REVIEW_SHAPE trio. A re-review
    appends its digest, so the last one is the current review."""
    digests = list(REVIEW_DIGEST.finditer(text))
    if not digests:
        return ("the review carries the fingerprint but no auditor digest "
                "— a fingerprint alone is not a review: paste the "
                "auditor's first line (`digest: BLOCK <n> · WARN <n> · NIT "
                "<n> · worst …`) verbatim; no auditor ran yet → emit with "
                f"{REVIEW_EMIT} and spawn it")
    current = digests[-1]
    blocks = int(current.group(1))
    rulings = len(REVIEW_RULING.findall(text, current.end()))
    if rulings < blocks:
        return (f"digest counts BLOCK {blocks} but {rulings} "
                "ruling line(s) follow it — every BLOCK needs an owner: "
                "add one `ruling: <finding> — repaired | <the user's "
                "ruling in their words>` line per BLOCK after the digest "
                "(a repaired docset is re-reviewed: record the new "
                "fingerprint and digest)")
    if not REVIEW_FINGERPRINT.search(text):
        return ("the review carries no `Docset fingerprint: <hash>` line "
                "— without it the record cannot name the docset the "
                "auditor read")
    return None


def review_problem(spec_dir: Path, review: str | None = None) -> str | None:
    """Why the contract review cannot back a freeze of the current
    docset, or None when it can (tiny tier has no contract review)."""
    if _is_tiny(spec_dir):
        return None
    text = _review_text(spec_dir, review)
    if not text.strip():
        return (f"contract review not recorded — emit it with {REVIEW_EMIT}, "
                "spawn the auditor on that payload, then pass the saved "
                "payload: `freeze.py <spec-dir> --record --review <payload>` "
                f"({REVIEW_SHAPE})")
    fingerprint = docset_fingerprint(spec_dir)
    if fingerprint not in text:
        return (f"the review reviews a different docset (current "
                f"fingerprint {fingerprint} not found) — the docset "
                f"changed after its review: re-emit with {REVIEW_EMIT}, "
                "re-review, and record the new digest and fingerprint")
    return review_shape_problem(text)


def _line_of(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return text[start:len(text) if end < 0 else end].strip()


def _heading_section(text: str, title: str) -> str | None:
    """A `## <title>` section's body, to the next `## ` heading — None
    when the heading is absent (the old-grammar record has neither
    section)."""
    m = re.search(rf"^## {re.escape(title)}[ \t]*$", text, re.M)
    if m is None:
        return None
    tail = re.search(r"^## ", text[m.end():], re.M)
    body_end = m.end() + tail.start() if tail else len(text)
    return text[m.end():body_end]


def fold_review(text: str) -> tuple[str, ...]:
    """The REVIEW_SHAPE trio folded into the record: the payload's
    fingerprint line, the last auditor digest line, then the ruling
    lines after it."""
    lines: list[str] = []
    fingerprints = list(REVIEW_FINGERPRINT.finditer(text))
    if fingerprints:
        lines.append(f"Docset fingerprint: {fingerprints[-1].group(1)}")
    digests = list(REVIEW_DIGEST.finditer(text))
    if digests:
        last = digests[-1]
        lines.append(REVIEW_LEAD_MARKUP.sub("", _line_of(text, last.start())))
        lines += [REVIEW_LEAD_MARKUP.sub("", _line_of(text, m.start()))
                  for m in REVIEW_RULING.finditer(text, last.end())]
    return tuple(lines)


def render(spec_dir: Path, approved_at: str,
           approvers: tuple[str, ...] = (),
           review: tuple[str, ...] = ()) -> str:
    vals = manifest_values(spec_dir)
    lines = [
        "# Approval freeze",
        "",
        f"**Approved-at**: `{approved_at}`",
        *(f"**Approved-by**: {name}" for name in approvers),
        "**Algorithm**: sha256 over UTF-8 bytes",
        "",
        "Recorded only after explicit user approval. `spec.md` is hashed without",
        "its volatile Status line (at tiny tier also without § Evidence and the",
        "status markers inside § Tasks; the task list itself is frozen).",
        "`tech-spec.md` is verified as an immutable prefix so implementation",
        "may append D-### decisions. `task.md` is not frozen because it is the",
        "status holder.",
    ]
    if review:
        lines += ["", "## Contract review", "", *review]
    lines += ["", "## Freeze", ""]
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


def record(spec_dir: Path, repo: Path, force: bool = False,
           approvers: tuple[str, ...] = (),
           review: str | None = None) -> int:
    if any("NEEDS CLARIFICATION" in (spec_dir / f).read_text(
            encoding="utf-8", errors="replace")
           for f in FROZEN_FILES if (spec_dir / f).exists()):
        print("FAIL: unresolved NEEDS CLARIFICATION marker — do not freeze", file=sys.stderr)
        return 1
    problem = review_problem(spec_dir, review)
    if problem:
        print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    review_lines = ()
    if not _is_tiny(spec_dir):
        review_lines = fold_review(_review_text(spec_dir, review))
    git_ok = specstate.git_available(repo)
    sha = specstate.head_sha(repo) if git_ok else "-"
    text = render(spec_dir, sha or "-", approvers, review_lines)
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


def _delivered(spec_dir: Path) -> bool:
    return any(
        specstate.delivery_state(
            (spec_dir / name).read_text(encoding="utf-8", errors="replace")
        )[0] == "delivered"
        for name in ("task.md", "spec.md") if (spec_dir / name).exists())


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
        if (approved_at != "-" and not _commit_exists(repo, approved_at)
                and not _delivered(spec_dir)):
            problems.append(
                f"approval freeze: Approved-at commit {approved_at!r} not found "
                "or not an ancestor of HEAD — history rewritten before "
                "delivery: re-approve (`freeze.py <spec-dir> --record "
                "--force` on the user's yes)"
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
    # a `## Freeze` heading marks the folded one-file grammar; old-grammar
    # records (## Frozen contract) keep their legacy review.md sidecar and
    # are migrate.py upgrade's to convert
    if not _is_tiny(spec_dir) and _heading_section(text, "Freeze") is not None:
        review = _heading_section(text, "Contract review")
        if review is None:
            problems.append(
                "approval freeze: contract review section missing from the "
                "record — a full-tier freeze folds the review trio; "
                "re-approve (`freeze.py <spec-dir> --record --force --review "
                "<payload>` on the user's yes)")
        else:
            shape = review_shape_problem(review)
            if shape:
                problems.append(f"approval freeze: {shape}")
    return problems


def parse_args(
    argv: list[str],
) -> tuple[Path, Path, str, bool, tuple[str, ...], str | None] | None:
    spec_dir = repo = None
    mode = ""
    force = False
    review: str | None = None
    approvers: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--record", "--verify"):
            mode = arg
        elif arg == "--force":
            force = True
        elif arg == "--review":
            i += 1
            if i >= len(argv):
                return None
            review = argv[i]
        elif arg == "--by":
            i += 1
            name = " ".join(argv[i].split()) if i < len(argv) else ""
            if not name:
                return None
            approvers.append(name)
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
    if (approvers or review) and mode != "--record":
        return None
    return (Path(spec_dir), Path(repo) if repo else Path(spec_dir).parent.parent,
            mode, force, tuple(approvers), review)


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
    spec_dir, repo, mode, force, approvers, review = parsed
    if not spec_dir.is_dir():
        print(f"FAIL: {spec_dir} is not a directory", file=sys.stderr)
        return 1
    if mode == "--record":
        return record(spec_dir, repo, force, approvers, review)
    problems = verify(spec_dir, repo)
    for problem in problems:
        print(f"FAIL: {problem}")
    print(f"freeze: {'PASS' if not problems else 'FAIL'} ({len(problems)} problem(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
