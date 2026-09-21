#!/usr/bin/env python3
"""tick.py — the orchestrator's mechanical task-ticking tool.

Ticks `- [ ] T###` entries to `- [x]`, inserts one `done <date> — <proof>`
sub-line per ticked task, strips the entry's `(in-progress)` claim marker,
and recomputes task.md's burndown table in memory via check.py's pure
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

Exit: 0 = applied (or --dry-run validated) · 1 = validation or transaction
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

USAGE = __doc__.rsplit("Exit:", 1)[0].strip()

NOTE_RE = re.compile(r"^(T\d{3})\s*::\s*(.+)$", re.DOTALL)
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


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry = False
    date = None
    notes: list[tuple[str, str]] = []
    spec_dir = None
    it = iter(args)
    for a in it:
        if a == "--note":
            raw = next(it, None)
            if raw is None:
                print("usage: tick.py <spec-dir> --note 'T### :: <proof>' [--date YYYY-MM-DD] [--dry-run]", file=sys.stderr)
                return 2
            m = NOTE_RE.match(raw.strip())
            if not m:
                print(f"--note must be 'T### :: <proof>': got {raw!r}", file=sys.stderr)
                return 2
            notes.append((m.group(1), " ".join(m.group(2).split())))
        elif a == "--date":
            date = next(it, None)
            if not date or not re.match(r"^\d{4}-\d{2}-\d{2}$", date or ""):
                print("--date must be YYYY-MM-DD", file=sys.stderr)
                return 2
        elif a == "--dry-run":
            dry = True
        elif a in ("-h", "--help"):
            print(USAGE)
            return 0
        elif spec_dir is None:
            spec_dir = a
        else:
            print(f"unexpected argument: {a}", file=sys.stderr)
            return 2
    if spec_dir is None or not notes:
        print("usage: tick.py <spec-dir> --note 'T### :: <proof>' [--date YYYY-MM-DD] [--dry-run]", file=sys.stderr)
        return 2

    import datetime
    date = date or datetime.date.today().isoformat()

    task_path = Path(spec_dir) / "task.md"
    if not task_path.is_file():
        print(f"no task.md under {spec_dir}", file=sys.stderr)
        return 1
    original = task_path.read_text(encoding="utf-8")

    # Validate everything BEFORE writing anything: every target exists,
    # is unticked, and no duplicate note names one task twice.
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
        return 0

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
