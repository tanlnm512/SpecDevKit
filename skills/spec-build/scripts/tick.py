#!/usr/bin/env python3
"""tick.py — the orchestrator's mechanical task-ticking tool.

Ticks `- [ ] T###` entries to `- [x]`, inserts one `done <date> — <proof>`
sub-line per ticked task, strips the entry's `(in-progress)` and
`(implemented)` status markers, and recomputes task.md's burndown table in memory via check.py's pure
burndown transform (the single arithmetic authority). The full prospective
text — ticks, done-lines, and burndown — is computed and validated before
any write. Replacement is durable and atomic: the prospective text goes to
a same-directory temp file, is fsynced, then renamed over the original, and
the promoted file is re-verified (byte-equality + re-parse); any failure at
any stage restores the byte-identical original and exits nonzero. Refuses
partial application: every note is
validated against the current file before any line changes, and a re-parse
of the prospective text must show exactly the intended ticks and a
burndown table that agrees with them.

The transform touches ONLY: the ticked task's first line, the one inserted
done-line under it, and the burndown Done column. Entry bodies, checkpoint
comments, and conventions stay byte-identical — the failure mode this tool
exists to prevent is the orchestrator hand-editing a dozen hunks and
gutting the as-built record.

--redeliver re-points a delivery record that rewritten history orphaned: a
squash-merge or rebase replaces the commit `Delivered: commit @ <sha>`
names, and check.py then fails the record. The one record line — in
task.md, or spec.md at tiny tier — becomes `Delivered: commit @ <new-sha>
(was <old-sha>)`; nothing else changes, and committing the rewrite stays
the user's. Refused when no record exists, when the recorded commit is
still an ancestor of HEAD, or when <new-sha> is not a commit HEAD contains.

--park appends a parked item — a WARN/NIT ruled "later", a review's residual
risk, a deviation left open — to specs/BACKLOG.md as one date-free line,
`- <spec-name> — <item> (source: <source>)`, after any ticks land; a line
already there is not repeated. Every run that ticks or parks lists the
spec's parked lines.

Usage: tick.py <spec-dir> --note 'T### :: <proof>' [--note …]
               [--park '<item> :: <source>' …] [--date YYYY-MM-DD] [--dry-run]
       tick.py <spec-dir> --park '<item> :: <source>' [--park …] [--dry-run]
       tick.py <spec-dir> --redeliver <new-sha> [--repo <path>] [--dry-run]
       tick.py -h | --help
Exit:  0 = applied (or --dry-run validated) · 1 = validation or transaction
       failure (nothing left changed) · 2 = usage error.
"""
from __future__ import annotations

import contextlib
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check
import specstate

USAGE = "Usage:" + __doc__.split("Usage:", 1)[1].split("Exit:", 1)[0].rstrip()

RECORD_RE = re.compile(
    r"(Delivered\*{0,2}\s*:\s*commit\s+@\s*`?)([0-9a-f]{7,40})(`?)"
    r"(?:[ \t]*\(was [0-9a-f]{7,40}\))?")
SHA_RE = re.compile(r"[0-9a-f]{7,40}\Z")

NOTE_RE = re.compile(r"^(T\d{3})\s*::\s*(.+)$", re.DOTALL)
PARK_RE = re.compile(r"^(.+?)\s*::\s*(.+)$", re.DOTALL)
BACKLOG_HEADER = ("# Backlog\n\nParked work, one line each: spec, item, source. Pick a line "
                  "up as a new spec, or delete it once it is moot.\n\n")
TASK_LINE_RE = re.compile(r"^- \[ \] (T\d{3})\b")
DATE_DEFAULT = None  # filled from datetime in main


def _tasks_by_id(task_md: str) -> dict:
    return {e.id: e for e in specstate.task_entries(task_md) if e.id}


def _apply_ticks(task_md: str, notes: list[tuple[str, str]], date: str) -> str:
    """Flip the named entries and insert done-lines. Caller has validated
    that every target exists, is unticked, and is unclaimed-or-claimable."""
    out: list[str] = []
    pending = dict(notes)
    for line in task_md.splitlines():
        m = TASK_LINE_RE.match(line)
        if m and m.group(1) in pending:
            proof = pending.pop(m.group(1))
            flipped = line.replace("- [ ]", "- [x]", 1)
            flipped = flipped.replace(" (in-progress)", "", 1)
            flipped = flipped.replace(" (implemented)", "", 1)
            out.append(flipped)
            out.append(f"  - done {date} — {proof}")
        else:
            out.append(line)
    assert not pending, f"validated task vanished mid-write: {sorted(pending)}"
    return "\n".join(out) + ("\n" if task_md.endswith("\n") else "")


def _prospective(task_md: str, notes: list[tuple[str, str]], date: str) -> str:
    """The complete prospective text — flipped entries, inserted done-lines,
    and the burndown table recomputed from the prospective entries — with
    no I/O, so main validates every byte of it before replacing the file."""
    updated = _apply_ticks(task_md, notes, date)
    ph_total, ph_done = check.phase_counts(specstate.task_entries(updated))
    out, _ = check.burndown_rewrite(updated, ph_total, ph_done)
    return out


def _verify_text(text: str, by_id: dict, seen: set[str],
                 notes: list[tuple[str, str]], date: str) -> list[str]:
    """Re-parse a candidate text and return its problems: exactly the named
    tasks newly done with done-lines landed, no other task's state changed,
    and the burndown table agreeing with the entries. Runs identically on
    the prospective text (pre-write) and the promoted text (postcheck)."""
    problems: list[str] = []
    after = _tasks_by_id(text)
    for tid, proof in notes:
        e = after.get(tid)
        if e is None or not e.done or f"done {date} — {proof}" not in e.block:
            problems.append(f"{tid}: post-write verification failed")
    before_ids = {t: (by_id[t].done, by_id[t].struck, by_id[t].claimed) for t in by_id}
    for t, state in before_ids.items():
        if t in seen:
            continue
        a = after.get(t)
        if a is None or (a.done, a.struck) != state[:2]:
            problems.append(f"{t}: state changed but was not named")
    sums = check.burndown_sums(text)
    if sums is None:
        print("warning: no burndown table in task.md; nothing to recompute", file=sys.stderr)
    else:
        bd_total, bd_done, sum_row = sums
        ph_total, ph_done = check.phase_counts(specstate.task_entries(text))
        want_total, want_done = sum(ph_total.values()), sum(ph_done.values())
        if bd_total != want_total:
            problems.append(f"burndown: table totals {bd_total} != prospective tasks {want_total}")
        if bd_done != want_done:
            problems.append(f"burndown: table done {bd_done} != prospective ticked {want_done}")
        if sum_row is not None and sum_row != (bd_total, bd_done):
            problems.append(
                f"burndown: Σ row {sum_row[0]}/{sum_row[1]} disagrees with "
                f"row sums {bd_total}/{bd_done}"
            )
    return problems


def _durable_replace(path: Path, text: str) -> None:
    """Write text to a same-directory temp file, fsync it, then rename it
    atomically over path. Any failure unlinks the temp and raises; path is
    only ever changed by the single atomic rename."""
    fd, tmpname = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmpname)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            with contextlib.suppress(OSError):
                os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        # After a real rename the temp no longer exists; after a simulated
        # or failed one it must not survive as debris.
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)


def _fsync_dir(path: Path) -> None:
    """Sync the directory entry so the rename itself survives a crash."""
    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _rollback(path: Path, original: str) -> None:
    """Best-effort restore of the byte-identical original after a failed
    postcheck; if restoration fails too, preserve the original bytes in a
    journal beside the file and print the exact recovery path."""
    try:
        _durable_replace(path, original)
        _fsync_dir(path)
        print("original task.md restored byte-identically", file=sys.stderr)
    except OSError as exc:
        journal = path.parent / (path.name + ".rollback")
        try:
            journal.write_bytes(original.encode("utf-8"))
        except OSError:
            print(
                f"ROLLBACK FAILED: {exc} — task.md is left replaced and no "
                "journal could be written; restore manually from version control",
                file=sys.stderr)
            return
        print(
            f"ROLLBACK FAILED: {exc} — original bytes preserved at {journal}; "
            f"recover with: mv {journal} {path}",
            file=sys.stderr)


def _park(spec_dir: Path, parks: list[tuple[str, str]], dry: bool) -> int:
    backlog = spec_dir.resolve().parent / "BACKLOG.md"
    name = spec_dir.resolve().name
    text = backlog.read_text(encoding="utf-8") if backlog.is_file() else ""
    lines = [f"- {name} — {item} (source: {source})" for item, source in parks]
    new = [line for line in dict.fromkeys(lines) if line not in text.splitlines()]
    if dry:
        for line in new:
            print(f"dry-run: would park {line}")
        return 0
    if new:
        try:
            head = text.rstrip("\n") + "\n" if text else BACKLOG_HEADER
            backlog.write_text(head + "\n".join(new) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"park failed, nothing appended to {backlog}: {exc}", file=sys.stderr)
            return 1
    _list_parked(spec_dir)
    return 0


def _list_parked(spec_dir: Path) -> None:
    backlog = spec_dir.resolve().parent / "BACKLOG.md"
    prefix = f"- {spec_dir.resolve().name} — "
    parked = [line for line in (backlog.read_text(encoding="utf-8").splitlines()
                                if backlog.is_file() else []) if line.startswith(prefix)]
    print(f"parked for {spec_dir.resolve().name} in specs/BACKLOG.md: {len(parked)}")
    for line in parked:
        print(f"  {line}")


def _status_holder(spec_dir: Path) -> Path:
    """task.md, or spec.md at tiny tier (its § Tasks and § Evidence)."""
    spec_path = spec_dir / "spec.md"
    if spec_path.is_file() and specstate.spec_tier(
            spec_path.read_text(encoding="utf-8", errors="replace")) == "tiny":
        return spec_path
    return spec_dir / "task.md"


def _new_sha_problem(repo: Path, sha: str) -> str | None:
    if not check._git_probe(repo, "rev-parse", "--git-dir"):
        return (f"{repo} is not a git repo — a non-git delivery records "
                "`Delivered: commit @ -`")
    if not check._git_probe(repo, "cat-file", "-e", f"{sha}^{{commit}}"):
        return f"{sha} is not a commit in {repo}"
    if not check._git_probe(repo, "merge-base", "--is-ancestor", sha, "HEAD"):
        return (f"{sha} is not an ancestor of HEAD — name the commit on "
                "this branch that carries the delivered work (the squash "
                "or rebased commit)")
    return None


def redeliver(spec_dir: Path, new_sha: str, repo: Path, dry: bool) -> int:
    path = _status_holder(spec_dir)
    if not path.is_file():
        print(f"no {path.name} under {spec_dir}", file=sys.stderr)
        return 1
    original = path.read_text(encoding="utf-8")
    record = RECORD_RE.search(original)
    if record is None:
        print(f"no `Delivered: commit @ <sha>` record in {path} — nothing "
              "to re-point; the delivery pass writes the record in C2",
              file=sys.stderr)
        return 1
    old_sha = record.group(2)
    if not check.lifecycle_integrity_problems(original, repo):
        print(f"Delivered: commit @ {old_sha} is intact (an ancestor of "
              "HEAD) — nothing to re-point", file=sys.stderr)
        return 1
    problem = _new_sha_problem(repo, new_sha)
    if problem:
        print(f"{problem} — nothing written", file=sys.stderr)
        return 1
    line = f"Delivered: commit @ {new_sha} (was {old_sha})"
    if dry:
        print(f"dry-run: would record `{line}` in {path}")
        return 0
    prospective = (original[:record.start()]
                   + f"{record.group(1)}{new_sha}{record.group(3)} "
                     f"(was {old_sha})"
                   + original[record.end():])
    try:
        _durable_replace(path, prospective)
        _fsync_dir(path)
    except OSError as exc:
        print(f"redeliver aborted: write/sync/replace failed: {exc}",
              file=sys.stderr)
        return 1
    print(f"re-pointed {path}: `{line}` — commit the change")
    return 0


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry = False
    date = None
    notes: list[tuple[str, str]] = []
    parks: list[tuple[str, str]] = []
    spec_dir = None
    new_sha = None
    repo = None
    it = iter(args)
    for a in it:
        if a == "--note":
            raw = next(it, None)
            if raw is None:
                print(USAGE, file=sys.stderr)
                return 2
            m = NOTE_RE.match(raw.strip())
            if not m:
                print(f"--note must be 'T### :: <proof>': got {raw!r}", file=sys.stderr)
                return 2
            notes.append((m.group(1), " ".join(m.group(2).split())))
        elif a == "--park":
            m = PARK_RE.match((next(it, None) or "").strip())
            if not m:
                print("--park must be '<item> :: <source>'", file=sys.stderr)
                return 2
            parks.append((" ".join(m.group(1).split()), " ".join(m.group(2).split())))
        elif a == "--date":
            date = next(it, None)
            if not date or not re.match(r"^\d{4}-\d{2}-\d{2}$", date or ""):
                print("--date must be YYYY-MM-DD", file=sys.stderr)
                return 2
        elif a == "--redeliver":
            new_sha = (next(it, None) or "").strip().lower()
            if not SHA_RE.match(new_sha):
                print("--redeliver needs a commit sha (7-40 hex chars)",
                      file=sys.stderr)
                return 2
        elif a == "--repo":
            repo = next(it, None)
            if repo is None:
                print(USAGE, file=sys.stderr)
                return 2
        elif a == "--dry-run":
            dry = True
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        elif spec_dir is None and not a.startswith("-"):
            spec_dir = a
        else:
            print(f"unexpected argument: {a}\n{USAGE}", file=sys.stderr)
            return 2
    if spec_dir is None or (new_sha and (notes or parks)) or not (notes or parks or new_sha):
        print(USAGE, file=sys.stderr)
        return 2
    if parks and not notes:
        return _park(Path(spec_dir), parks, dry)

    if new_sha:
        return redeliver(Path(spec_dir), new_sha,
                         Path(repo) if repo else Path(spec_dir).parent.parent,
                         dry)

    import datetime
    date = date or datetime.date.today().isoformat()

    # Tiny tier keeps tasks in spec.md § Tasks; there is no burndown table to recompute.
    task_path = _status_holder(Path(spec_dir))
    if not task_path.is_file():
        print(f"no task.md under {spec_dir}", file=sys.stderr)
        return 1
    original = task_path.read_text(encoding="utf-8")

    # Validate everything BEFORE writing anything: every target exists,
    # is unticked with no fix round open, and no note names a task twice.
    seen: set[str] = set()
    problems: list[str] = []
    by_id = _tasks_by_id(original)
    for tid, _ in notes:
        if tid in seen:
            problems.append(f"{tid}: named twice")
        seen.add(tid)
        e = by_id.get(tid)
        if e is None:
            problems.append(f"{tid}: no such task entry")
        elif e.done or e.struck:
            problems.append(f"{tid}: already ticked or struck")
        elif e.fix_round is not None:
            problems.append(
                f"{tid}: fix round {e.fix_round} is open — land it and "
                f"rewrite the marker (fixed {e.fix_round}/5) first")
    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print("validation failed — nothing written", file=sys.stderr)
        return 1

    prospective = _prospective(original, notes, date)

    problems = _verify_text(prospective, by_id, seen, notes, date)
    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print("post-write verification failed — nothing written", file=sys.stderr)
        return 1

    if dry:
        print(f"dry-run: would tick {len(notes)} task(s) with date {date}:")
        for tid, proof in notes:
            print(f"  [x] {tid} — {proof}")
        return _park(Path(spec_dir), parks, dry)

    try:
        _durable_replace(task_path, prospective)
    except OSError as exc:
        print(f"tick aborted: write/sync/replace failed, original preserved: {exc}",
              file=sys.stderr)
        return 1

    # Postcheck the promoted file: byte-equality with the validated
    # prospective text, then the same re-parse used pre-write. Any problem
    # here rolls back to the byte-identical original.
    problems = []
    landed = ""
    try:
        landed_bytes = task_path.read_bytes()
    except OSError as exc:
        landed_bytes = None
        problems.append(f"postcheck: replaced task.md unreadable: {exc}")
    if landed_bytes is not None:
        if landed_bytes != prospective.encode("utf-8"):
            problems.append(
                "postcheck: task.md on disk differs from the validated prospective text")
        landed = landed_bytes.decode("utf-8", errors="replace")
        problems += _verify_text(landed, by_id, seen, notes, date)
    if not problems:
        try:
            _fsync_dir(task_path)
        except OSError as exc:
            problems = [f"postcheck: directory sync failed after replace: {exc}"]
    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print("postcheck failed — rolling back", file=sys.stderr)
        _rollback(task_path, original)
        return 1

    done_now = sum(1 for e in specstate.task_entries(landed) if e.done)
    total = len(specstate.task_entries(landed))
    print(f"ticked {len(notes)}: {', '.join(tid for tid, _ in notes)}")
    print(f"burndown now {done_now}/{total} done")
    return _park(Path(spec_dir), parks, dry)


if __name__ == "__main__":
    sys.exit(main())
