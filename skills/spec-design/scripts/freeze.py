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

--approve is the owner's own-terminal step, run only after the explicit
user approval. The record it writes is the `## Contract review` section
(the review payload's trio — fingerprint, digest, rulings) followed by
the `## Freeze` manifest. At full tier the review payload the
orchestrator saved is passed as `--review <payload>` (the auditor itself
writes nothing); a persisted approvals/review.md from the old grammar
backs a bare --approve the same way.
Three things must be on the review: the docset fingerprint the review
named, the auditor's digest line (`digest: BLOCK <n> ·
WARN <n> · NIT <n> · worst …`), and after that digest one `ruling:`
line per BLOCK it counts. A docset repaired after its review has a new
fingerprint, so the freeze refuses until it is re-reviewed. The digest
line is read through its schema (digests.py): one the schema rejects
refuses the approval as malformed until the auditor is re-run; a
signed record verifies on the BLOCK count it carries.

An approval is a signature: --approve signs the record with an SSH key
listed in the approver list (ssh allowed_signers: one `<principal>
<key-type> <key-blob>` line per approver, `#` starts a comment) and
writes specs/<name>/approvals/approval.md and approval.md.sig together
— both or neither. The signed text is the record with LF line endings
and exactly one trailing newline, so a CRLF checkout still verifies and
any other change to the record breaks it. The record's `**Approved-by**`
line carries the signing key's principal. --key defaults to the first
of ~/.ssh/id_ed25519, ~/.ssh/id_ecdsa, ~/.ssh/id_rsa that exists;
--force replaces an existing record.

The approver list is read from a trust root the workspace cannot write,
never from the working tree:
  1. the machine list ~/.config/spec-dev-kit/approvers, wherever it
     exists — the authority for --approve and --verify alike;
  2. else in CI (the `CI` variable set to a non-empty value): the list
     as it stands on the remote default branch — the target of
     refs/remotes/origin/HEAD, else origin/main, else origin/master —
     read with `git show` and never fetched;
  3. else nothing signs or verifies: a local run without the machine
     list refuses.
A specs/.approvers in the working tree is only what CI commits. Verify
refuses, naming the file, while any other file named `.approvers` sits
under <repo-root>/specs/.

--approve confirms on the terminal: the prompt names the spec and the
docset fingerprint, and the exact phrase it prints must be typed on
/dev/tty. With no controlling terminal, a different line, or an end of
file, it exits 1 having written nothing.

--verify refuses a record without a signature and one whose signature
does not verify, unless the remote default branch carries the record
byte for byte — an unsigned record approved before signatures existed
stays valid once delivered and pushed; a local commit and a
`Delivered:` line prove nothing. It treats the Approved-at commit as
history after delivery too: a
squash-merge or rebase rewrites the anchor, and the delivery record
owns the proof from there. It re-checks the folded review section's
shape but never re-hashes the record — the signature covers it and the
manifest covers the four frozen files only — and never re-compares the
fingerprint to the live docset, whose legal post-approval drift
(tech-spec appends, task.md status) changes it.

Usage:
  freeze.py <spec-dir> --approve [--review <payload>] [--key <private-key>] [--repo <path>] [--force]
  freeze.py <spec-dir> --verify [--repo <path>]
  freeze.py -h | --help

--verify writes nothing on a machine that holds the machine list; in CI
it copies the remote list to a private temporary file for ssh-keygen.
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import digests
import specstate

FROZEN_FILES = ("spec.md", "plan.md", "test.md", "tech-spec.md")
NAMESPACE = "spec-dev-kit-approval"
APPROVERS = Path("specs") / ".approvers"
MACHINE_APPROVERS = Path(".config") / "spec-dev-kit" / "approvers"
REMOTE_HEAD = "refs/remotes/origin/HEAD"
DEFAULT_BRANCHES = ("main", "master")
TTY = "/dev/tty"
DEFAULT_KEYS = ("id_ed25519", "id_ecdsa", "id_rsa")
TINY_EVIDENCE_HEADING = "## Evidence"
TASK_STATUS_LINE = re.compile(
    r"^\s*(?:-\s*)?(?:done \d{4}-\d{2}-\d{2} \u2014|fix(?:ed)? \d+ \u2014"
    r"|claimed \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \u2014 run "
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


BLOCK_COUNT = re.compile(r"^digest:\s*BLOCK\s+(\d+)")
REVIEW_FINGERPRINT = re.compile(
    r"Docset fingerprint:[ \t]*`?([0-9a-f]{6,64})`?", re.I)
REVIEW_RULING = re.compile(
    r"^[ \t]*(?:[-*][ \t]+)?\**ruling\b[^\n:]*:[ \t]*\S", re.I | re.M)
REVIEW_LEAD_MARKUP = re.compile(r"^[ \t>*`-]+")
REVIEW_SHAPE = ("`Docset fingerprint: <hash>`, then the auditor's "
                "`tools: <the tools it holds>` line and its `digest: "
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
    of a docset whose record no longer verifies. Tiny tier has no
    contract-review record."""
    if _is_tiny(spec_dir):
        return ("on the user's explicit yes the owner runs `freeze.py "
                "<spec-dir> --approve` in their own terminal")
    return (f"emit the contract review with {REVIEW_EMIT}, spawn the "
            "auditor on it, save the review payload ("
            f"{REVIEW_SHAPE}), then on the user's explicit yes the owner "
            "runs `freeze.py <spec-dir> --approve --review <payload>` in "
            "their own terminal")


def _review_text(spec_dir: Path, review: str | None) -> str:
    """The review payload's text: the --review file when given, else the
    legacy approvals/review.md the old flow persisted."""
    path = Path(review) if review else spec_dir / "approvals" / "review.md"
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _last_digest(text: str) -> tuple[int, str] | None:
    lines = digests.digest_lines(text)
    return lines[-1] if lines else None


def review_shape_problem(text: str, strict: bool = True) -> str | None:
    """Why review text is not a complete REVIEW_SHAPE trio. A re-review
    appends its digest, so the last one is the current review. A signed
    record verifies on its BLOCK count alone (strict=False): re-running
    the review it froze means re-approving, which breaks a docset still
    in execution (spec-design D-074). The live payload (strict=True) also
    answers the capability handshake: the last `tools:` line above the
    digest must hold Read (spec-design D-076)."""
    last = _last_digest(text)
    if last is None:
        return ("the review carries the fingerprint but no auditor digest "
                "— a fingerprint alone is not a review: paste the "
                "auditor's first line (`digest: BLOCK <n> · WARN <n> · NIT "
                "<n> · worst …`) verbatim; no auditor ran yet → emit with "
                f"{REVIEW_EMIT} and spawn it")
    offset, line = last
    parsed = digests.parse("auditor", None, line)
    loose = BLOCK_COUNT.match(line)
    blocks = (parsed["BLOCK"] if parsed else
              loose.group(1) if loose and not strict else None)
    if blocks is None:
        return (f"malformed auditor digest {line!r} — "
                f"{'; '.join(digests.validate('auditor', None, line))} — "
                "fix and run again: hand the problems back to the auditor, "
                "re-run the review, and record the digest it returns")
    if strict:
        # the signed record folds the digest line alone: only the live
        # payload carries the auditor's own `tools:` line
        tools = digests.tools_lines(text[:offset])
        reported = digests.tools_report(tools[-1][1] if tools else "")
        missing = digests.tools_missing("auditor", reported)
        if missing:
            return (f"{digests.tools_refusal('auditor', reported, missing)} — "
                    "spawn the auditor again on a type or harness that "
                    "holds `Read`, re-run the review, and record the reply "
                    "it returns, its `tools:` line first")
    blocks = int(blocks)
    rulings = len(REVIEW_RULING.findall(text, offset))
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
                "spawn the auditor on that payload, then hand the saved "
                "payload to the owner: `freeze.py <spec-dir> --approve "
                f"--review <payload>` ({REVIEW_SHAPE})")
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
    last = _last_digest(text)
    if last:
        lines.append(last[1])
        lines += [REVIEW_LEAD_MARKUP.sub("", _line_of(text, m.start()))
                  for m in REVIEW_RULING.finditer(text, last[0])]
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


def _canonical(text: str) -> bytes:
    """The signed bytes: LF line endings, exactly one trailing newline."""
    return (text.replace("\r\n", "\n").rstrip("\n") + "\n").encode("utf-8")


def _first_line(text: bytes) -> str:
    lines = text.decode("utf-8", errors="replace").strip().splitlines()
    return lines[0] if lines else ""


def _ssh_keygen(*args: str,
                data: bytes | None = None) -> tuple[int, bytes, str]:
    """(exit code, stdout, stderr's first line); stdin is `data`, or the
    caller's own when None."""
    try:
        run = subprocess.run(["ssh-keygen", *args], input=data,
                             capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return 255, b"", str(exc)
    return run.returncode, run.stdout, _first_line(run.stderr)


def _keygen_problem() -> str | None:
    if shutil.which("ssh-keygen") is None:
        return ("ssh-keygen not found — an approval signature needs the "
                "OpenSSH client tools")
    return None


def _git(repo: Path, *args: str) -> bytes | None:
    """A read-only git command's stdout, or None when it cannot run or
    refuses."""
    try:
        run = subprocess.run(["git", "-C", str(repo), *args],
                             capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return run.stdout if run.returncode == 0 else None


def _repo_root(spec_dir: Path, repo: Path) -> Path:
    """The workspace root: git's toplevel for the spec dir, else the
    --repo root."""
    top = _git(spec_dir, "rev-parse", "--show-toplevel")
    if top is None:
        return repo
    return Path(top.decode("utf-8", errors="replace").strip())


def _remote_default(repo: Path) -> str | None:
    """The remote default branch's full ref (refs/remotes/origin/<branch>)
    — origin/HEAD's target, else origin/main, else origin/master — or
    None when none resolves. Full, because git resolves a tag or a
    branch ahead of the remote-tracking ref of the same short name, and
    a session can make either."""
    head = _git(repo, "symbolic-ref", "--quiet", REMOTE_HEAD)
    targets = ([head.decode("utf-8", errors="replace").strip()] if head
               else []) + [f"refs/remotes/origin/{name}"
                           for name in DEFAULT_BRANCHES]
    for ref in targets:
        if ref.startswith("refs/remotes/origin/") and _git(
                repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            return ref
    return None


def _short(ref: str) -> str:
    return ref.removeprefix("refs/remotes/")


LIST_LOCATION = ("~/.config/spec-dev-kit/approvers, or in CI the list on the "
                "remote default branch")
NO_LIST = ("no approver list on this machine "
           "(~/.config/spec-dev-kit/approvers) — create it with your SSH "
           "public key, one `<principal> <key-type> <key-blob>` line per "
           "approver: `ssh-keygen -y -f ~/.ssh/id_ed25519` prints yours; a "
           "workspace `specs/.approvers` is never an authority (CI reads "
           "the list from the remote default branch)")
NO_REMOTE = ("no remote default branch (the target of refs/remotes/origin/"
             "HEAD, origin/main, origin/master) — CI reads the approver "
             "list from it: fetch the remote (`git remote set-head origin "
             "-a`), or create the machine list "
             "~/.config/spec-dev-kit/approvers")


@contextlib.contextmanager
def _approvers(repo: Path) -> Iterator[Path | str]:
    """The approver list as the file ssh-keygen reads — or why none can
    be trusted. The one resolver for --approve and --verify: the machine
    list ~/.config/spec-dev-kit/approvers wherever it exists; else in CI
    the list on the remote default branch, copied to a private temporary
    file for this block and never fetched; else nothing. The working
    tree's specs/.approvers is never an authority, so no workspace edit
    makes a key an approver."""
    machine = Path.home() / MACHINE_APPROVERS
    if machine.is_file():
        yield machine
        return
    if not os.environ.get("CI"):
        yield NO_LIST
        return
    ref = _remote_default(repo)
    remote = _git(repo, "show", f"{ref}:{APPROVERS.as_posix()}") if ref else None
    if remote is None:
        yield NO_REMOTE if ref is None else (
            f"no approver list on {_short(ref)} (`specs/.approvers` is "
            "absent from the remote default branch) — commit it there, or "
            "create the machine list ~/.config/spec-dev-kit/approvers")
        return
    with tempfile.NamedTemporaryFile("wb", prefix="approvers-") as copy:
        copy.write(remote)
        copy.flush()
        yield Path(copy.name)


def _nested_approvers(repo_root: Path) -> list[Path]:
    """Every file named .approvers under specs/ but the root list: a
    shadow, whatever it holds."""
    specs, root_list = repo_root / "specs", repo_root / APPROVERS
    return sorted(Path(base) / APPROVERS.name
                  for base, _dirs, files in os.walk(specs)
                  if APPROVERS.name in files
                  and Path(base) / APPROVERS.name != root_list)


def _shadow_problem(shadow: Path) -> str:
    return (f"nested approver list {shadow} — a workspace list is never an "
            "authority, and only <repo-root>/specs/.approvers may exist: "
            "delete it")


def _allowed_lines(approvers: Path) -> list[str]:
    """The approver list's key lines — blank and `#` lines dropped."""
    if not approvers.is_file():
        return []
    return [line for line in
            approvers.read_text(encoding="utf-8",
                                errors="replace").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def _principals(approvers: Path) -> list[str]:
    return list(dict.fromkeys(
        name for name in (line.split()[0].split(",")[0]
                          for line in _allowed_lines(approvers))
        if name))


def _public_half(path: Path) -> tuple[str, str] | str:
    """The key's type and blob — read from its .pub file first, so a
    passphrase-protected key resolves without a prompt — or why neither
    yields them."""
    pub = path.with_name(path.name + ".pub")
    if pub.is_file():
        words = pub.read_text(encoding="utf-8", errors="replace").split()
        if len(words) >= 2:
            return words[0], words[1]
    code, public, error = _ssh_keygen("-y", "-f", str(path))
    if code != 0:
        return f"cannot read the public half of {path} — {error}"
    keytype, blob = public.decode("utf-8", errors="replace").split()[:2]
    return keytype, blob


def _signer(spec_dir: Path, repo: Path,
            key: str | None) -> tuple[Path, str] | str:
    """The signing key and its principal in the approver list — the key
    --key names, else the first standard identity that exists — or why
    nothing can sign."""
    problem = _keygen_problem()
    if problem:
        return problem
    if key:
        path = Path(key).expanduser()
        missing = f"no signing key at {path}"
    else:
        path = next((candidate for candidate in
                     (Path.home() / ".ssh" / name for name in DEFAULT_KEYS)
                     if candidate.is_file()), None)
        missing = ("no signing key found — pass --key <private-key> "
                   "(looked for "
                   + ", ".join(f"~/.ssh/{name}" for name in DEFAULT_KEYS)
                   + ")")
    if path is None or not path.is_file():
        return missing
    public = _public_half(path)
    if isinstance(public, str):
        return public
    with _approvers(_repo_root(spec_dir, repo)) as approvers:
        if isinstance(approvers, str):
            return approvers
        for line in _allowed_lines(approvers):
            words = line.split()
            if any(words[i:i + 2] == list(public)
                   for i in range(len(words) - 1)):
                return path, words[0].split(",")[0]
        return (f"the key {path} is not in the approver list "
                f"({LIST_LOCATION}) — add its public half there as "
                "`<principal> <key-type> <key-blob>` (`ssh-keygen -y -f "
                "<key>` prints it), or sign with a listed key: "
                "--key <private-key>")


def _staged(target: Path, data: bytes) -> Path:
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}-",
                               dir=str(target.parent))
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    return Path(tmp)


def _discard(tmp: Path) -> None:
    try:
        tmp.unlink()
    except OSError:
        pass


def _write_pair(out: Path, tmp_record: Path, tmp_sig: Path) -> None:
    """Replace the record and its signature together; a failed second
    replace puts the record back as it was."""
    before = out.read_bytes() if out.exists() else None
    os.replace(tmp_record, out)
    try:
        os.replace(tmp_sig, out.with_name(out.name + ".sig"))
    except OSError:
        if before is None:
            out.unlink()
        else:
            out.write_bytes(before)
        raise


def _confirm(spec_dir: Path, fingerprint: str, principal: str) -> str | None:
    """None once the owner types the phrase the terminal shows; else why
    the approval stops. /dev/tty is the only channel that answers it: a
    bare "y", a pipe on stdin or an end of file approves nothing."""
    phrase = f"approve {spec_dir.name} {fingerprint}"
    try:
        terminal = os.open(TTY, os.O_RDWR)
    except OSError:
        return ("--approve runs only in the owner's own terminal — it asks "
                "for a confirmation on /dev/tty, and this call has no "
                "controlling terminal")
    try:
        os.write(terminal, (
            f"\nApprove {spec_dir.name} (docset fingerprint {fingerprint}) "
            f"as {principal}?\nType exactly: {phrase}\n"
            "Anything else, or Ctrl-D, cancels.\n").encode("utf-8"))
        # one line and no more: a raw read leaves whatever follows for
        # the passphrase prompt ssh-keygen may put on the same terminal
        typed = bytearray()
        while not typed.endswith(b"\n"):
            chunk = os.read(terminal, 1024)
            if not chunk:
                break
            typed += chunk
    except OSError as exc:
        return f"the terminal did not answer ({exc}) — nothing was approved"
    finally:
        os.close(terminal)
    line = typed.decode("utf-8", errors="replace")
    if line.rstrip("\r\n") != phrase:
        return (f"`{line.strip()}` was typed, not `{phrase}` — nothing was "
                "approved: run again and type the phrase the prompt shows")
    return None


def approve(spec_dir: Path, repo: Path, force: bool = False,
            review: str | None = None, key: str | None = None) -> int:
    out = spec_dir / "approvals" / "approval.md"
    if any("NEEDS CLARIFICATION" in (spec_dir / f).read_text(
            encoding="utf-8", errors="replace")
           for f in FROZEN_FILES if (spec_dir / f).exists()):
        print("FAIL: unresolved NEEDS CLARIFICATION marker — do not freeze", file=sys.stderr)
        return 1
    problem = review_problem(spec_dir, review)
    if problem:
        print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    if out.exists() and not force:
        print(
            f"FAIL: {out} already exists — a replacement requires a fresh "
            "user approval and --force",
            file=sys.stderr,
        )
        return 1
    shadow = _nested_approvers(_repo_root(spec_dir, repo))
    if shadow:
        print(f"FAIL: {_shadow_problem(shadow[0])}", file=sys.stderr)
        return 1
    signer = _signer(spec_dir, repo, key)
    if isinstance(signer, str):
        print(f"FAIL: {signer}", file=sys.stderr)
        return 1
    key_path, principal = signer
    review_lines = ()
    if not _is_tiny(spec_dir):
        review_lines = fold_review(_review_text(spec_dir, review))
    sha = specstate.head_sha(repo) if specstate.git_available(repo) else "-"
    text = render(spec_dir, sha or "-", (principal,), review_lines)
    fingerprint = docset_fingerprint(spec_dir)
    print(f"approving {spec_dir.name} — docset fingerprint {fingerprint}, "
          f"signing as {principal}\n{text}",
          end="")
    problem = _confirm(spec_dir, fingerprint, principal)
    if problem:
        print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    # the record is staged as a file and signed where it lies: ssh-keygen
    # then leaves stdin to the terminal, so a passphrase prompt works
    tmp_record = _staged(out, _canonical(text))
    tmp_sig = Path(f"{tmp_record}.sig")
    try:
        code, _, error = _ssh_keygen("-Y", "sign", "-f", str(key_path), "-n",
                                     NAMESPACE, str(tmp_record))
        if code != 0 or not tmp_sig.is_file():
            print(f"FAIL: ssh-keygen could not sign — {error}",
                  file=sys.stderr)
            return 1
        _write_pair(out, tmp_record, tmp_sig)
    finally:
        _discard(tmp_record)
        _discard(tmp_sig)
    print(f"approved {out} (approved-at {sha or '-'}; "
          f"signed by {principal})")
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


def _record_is_history(spec_dir: Path, repo: Path) -> bool:
    """True when an unsigned record is provably history: the docset is
    delivered and the remote default branch carries the record byte for
    byte at the same path. HEAD and the claimed delivery sha prove
    nothing — a commit is something a session can make — so with no
    remote default branch an unsigned record is never an approval."""
    record = spec_dir / "approvals" / "approval.md"
    if not _delivered(spec_dir) or not record.exists():
        return False
    ref = _remote_default(repo)
    if ref is None:
        return False
    try:
        rel = record.resolve().relative_to(
            _repo_root(spec_dir, repo).resolve()).as_posix()
    except (OSError, ValueError):
        return False
    carried = _git(repo, "show", f"{ref}:{rel}")
    if carried is None:
        return False
    return _canonical(carried.decode("utf-8", errors="replace")) == (
        _canonical(record.read_bytes().decode("utf-8", errors="replace")))


def signature_problem(spec_dir: Path, repo: Path) -> str | None:
    """Why the record's signature does not prove an approval, or None.
    An unsigned record proves one only when the remote default branch
    carries it."""
    sig = spec_dir / "approvals" / "approval.md.sig"
    if not sig.exists():
        if _record_is_history(spec_dir, repo):
            return None
        return ("no signature (approvals/approval.md.sig) — an unsigned "
                "record is not an approval, whatever its `Delivered:` line "
                "says: only the remote default branch carrying it makes it "
                "history; the owner re-approves in their own terminal: "
                "`freeze.py <spec-dir> --approve --force`")
    record = sig.with_name("approval.md")
    message = _canonical(
        record.read_bytes().decode("utf-8", errors="replace"))
    with _approvers(_repo_root(spec_dir, repo)) as approvers:
        problem = _keygen_problem() or approvers
        if isinstance(problem, str):
            return problem
        detail = ""
        for principal in _principals(approvers):
            code, _, error = _ssh_keygen(
                "-Y", "verify", "-f", str(approvers), "-I", principal,
                "-n", NAMESPACE, "-s", str(sig), data=message)
            if code == 0:
                return None
            detail = detail or error
        return (f"signature does not verify ({detail or 'no approver listed'}) "
                "— the record changed after signing, or its signer is not in "
                f"the approver list ({LIST_LOCATION}): the owner re-approves "
                "in their own terminal: `freeze.py <spec-dir> --approve "
                "--force`")


def verify(spec_dir: Path, repo: Path) -> list[str]:
    """Return human-readable integrity problems; empty means green."""
    path = spec_dir / "approvals" / "approval.md"
    shadows = [f"approval freeze: {_shadow_problem(shadow)}"
               for shadow in _nested_approvers(_repo_root(spec_dir, repo))]
    if not path.exists():
        return [f"approval freeze missing: {path.relative_to(spec_dir)}",
                *shadows]
    text = path.read_text(encoding="utf-8", errors="replace")
    problems: list[str] = []
    signature = signature_problem(spec_dir, repo)
    if signature:
        problems.append(f"approval freeze: {signature}")
    problems += shadows
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
                "delivery: re-approve (`freeze.py <spec-dir> --approve "
                "--force` in the owner's terminal on the user's yes)"
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
    # a `## Freeze` heading marks the one-file grammar; an old-grammar
    # record (## Frozen contract) is unsigned and never got this far
    # unless its docset is delivered
    if not _is_tiny(spec_dir) and _heading_section(text, "Freeze") is not None:
        review = _heading_section(text, "Contract review")
        if review is None:
            problems.append(
                "approval freeze: contract review section missing from the "
                "record — a full-tier freeze folds the review trio; "
                "re-approve (`freeze.py <spec-dir> --approve --force "
                "--review <payload>` in the owner's terminal on the user's "
                "yes)")
        else:
            shape = review_shape_problem(review, strict=False)
            if shape:
                problems.append(f"approval freeze: {shape}")
    return problems


def parse_args(
    argv: list[str],
) -> tuple[Path, Path, str, bool, str | None, str | None] | None:
    spec_dir = repo = None
    mode = ""
    force = False
    review: str | None = None
    key: str | None = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--approve", "--verify"):
            mode = arg
        elif arg == "--force":
            force = True
        elif arg == "--review":
            i += 1
            if i >= len(argv):
                return None
            review = argv[i]
        elif arg == "--key":
            i += 1
            if i >= len(argv):
                return None
            key = argv[i]
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
    if not spec_dir or mode not in ("--approve", "--verify"):
        return None
    if (key or review) and mode != "--approve":
        return None
    return (Path(spec_dir), Path(repo) if repo else Path(spec_dir).parent.parent,
            mode, force, key, review)


RECORD_REFUSAL = (
    "FAIL: --record is retired — an unsigned record is not an approval; "
    "the owner signs one in their own terminal: "
    "`freeze.py <spec-dir> --approve`")


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    if "--record" in argv:
        print(RECORD_REFUSAL, file=sys.stderr)
        return 1
    parsed = parse_args(argv)
    if parsed is None:
        print(__doc__, file=sys.stderr)
        return 2
    spec_dir, repo, mode, force, key, review = parsed
    if not spec_dir.is_dir():
        print(f"FAIL: {spec_dir} is not a directory", file=sys.stderr)
        return 1
    if mode == "--approve":
        return approve(spec_dir, repo, force, review, key)
    problems = verify(spec_dir, repo)
    for problem in problems:
        print(f"FAIL: {problem}")
    print(f"freeze: {'PASS' if not problems else 'FAIL'} ({len(problems)} problem(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
