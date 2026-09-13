#!/usr/bin/env python3
"""tick.py — the orchestrator's mechanical task-ticking tool.

Ticks `- [ ] T###` entries to `- [x]`, inserts one `done <date> — <proof>`
sub-line per ticked task, strips the entry's `(in-progress)` claim marker,
and recomputes task.md's burndown table via `check.py --fix-burndown` (the
single arithmetic authority). Refuses partial application: every note is
validated against the current file before any line changes, and a re-parse
after writing must show exactly the intended ticks.

The transform touches ONLY: the ticked task's first line, the one inserted
done-line under it, and the burndown Done column. Entry bodies, checkpoint
comments, and conventions stay byte-identical — the failure mode this tool
exists to prevent is the orchestrator hand-editing a dozen hunks and
gutting the as-built record.

Exit: 0 = applied (or --dry-run validated) · 1 = validation failed (no
changes written) · 2 = usage error.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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

    updated = _apply_ticks(original, notes, date)

    # Re-parse the prospective text: exactly the named tasks newly done,
    # nothing else changed state, and the done-lines landed.
    after = _tasks_by_id(updated)
    for tid, proof in notes:
        e = after[tid]
        if not e.done or f"done {date} — {proof}" not in e.block:
            problems.append(f"{tid}: post-write verification failed")
    before_ids = {t: (by_id[t].done, by_id[t].struck, by_id[t].claimed) for t in by_id}
    for t, state in before_ids.items():
        if t in seen:
            continue
        a = after.get(t)
        if a is None or (a.done, a.struck) != state[:2]:
            problems.append(f"{t}: state changed but was not named")
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

    task_path.write_text(updated, encoding="utf-8")

    # Burndown arithmetic belongs to exactly one implementation.
    check = Path(__file__).resolve().parent / "check.py"
    r = subprocess.run([sys.executable, str(check), str(spec_dir), "--fix-burndown"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"warning: check.py --fix-burndown exited {r.returncode}; burndown may need attention", file=sys.stderr)
        print(r.stdout.strip(), file=sys.stderr)

    done_now = sum(1 for e in specstate.task_entries(task_path.read_text(encoding="utf-8")) if e.done)
    total = len(specstate.task_entries(task_path.read_text(encoding="utf-8")))
    print(f"ticked {len(notes)}: {', '.join(tid for tid, _ in notes)}")
    print(f"burndown now {done_now}/{total} done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
