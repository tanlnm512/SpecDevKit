#!/usr/bin/env python3
"""mark.py — the one writer of task markers (spec-build D-039, amending
D-034's prose table into an executable one).

D-034 made the orchestrator "the sole status writer" — but the writer was
an LLM editing markdown by hand, so claims were forgotten, illegal
transitions slipped through, and two writers (a session and tick.py)
could read-rewrite task.md at once. mark.py makes the transition table
executable: every verb checks the entry's current marker and refuses
anything else, every write happens under specstate.task_lock, and every
rewrite lands atomically (temp file + os.replace). The docs stay the
only status — nothing here becomes a second store; hand edits remain
possible but are no longer the sanctioned path (SKILL.md § Task markers
says markers are written only through mark.py / tick.py).

Verbs and the transitions they own (the D-034 table, executable):

  mark.py claim   <spec-dir> --wave <wave-dir> [--run-id ID]
  mark.py land    <spec-dir> T### [--resolution "<text>"] [--digest "<line>"] [--allow-pending]
  mark.py release <spec-dir> T### --reason "<text>"
  mark.py fail    <spec-dir> T### --evidence <file> --digest "<line>"
  mark.py drop    <spec-dir> T### --decision D-###

| Verb    | Allowed from                        | Writes |
|---------|-------------------------------------|--------|
| claim   | `- [ ]` pending, or `(fix n/5)` with an open round | `(in-progress)` + stamp sub-line `  - claimed <UTC ISO> — run <id>` |
| land    | `(in-progress)`                     | `(implemented)`, or `(implemented) (fixed n/5)` + `fixed n — …` when a round is open |
| release | `(in-progress)`                     | claim and stamp removed (blocked / settling orphans) |
| fail    | `(in-progress)` or `(implemented)`  | `(fix n/5)` + `fix n — <digest>`; evidence verbatim into notes/T###.md |
| drop    | any open entry                      | `~~T###~~ dropped <date> (D-###)` |

claim --wave claims exactly the implementer-T###.md files in the wave
dir: it re-runs graph.task_frontier + schedule_wave on the CURRENT doc
state and refuses everything if any wave task is no longer runnable or
now defers, so a stale wave cannot be claimed. land is gated on a
developer digest reporting implemented/already-satisfied — the digest
FILE the agent wrote (digests/wave-<N>/<stem>.md, D-040) is the
primary evidence, `--digest` the override when the file is missing —
and on `audit.py proofs <spec> --run --task T###` running at least one
acceptance command green — on red it prints the failure and the exact
fail command to run. A proof whose named tests do not exist is PENDING,
never a pass: when none of the task's proofs ran, land refuses unless
`--allow-pending` says the tests are written by a later task — the
landing is then an unproven `(implemented)`, and the delivery pass (dod
gate 1) stays red until the pending proofs run. fail copies the digest verbatim from the recorded
evidence and refuses a digest that is not a substring of it; a
superseded in-flight round closes as `fixed n — failed again — …` so
the checker's pairing gate stays green; round 3 points at
/spec-design, round 4 at a tier up, round 5 at the cap and the user's
adjudication. drop strikes the entry with its D-### ruling — refused
for a D-### tech-spec.md does not define, and refused outright at
Tier: tiny (a drop breaks the freeze — route it to /spec-design).

The claim stamp is a SUB-LINE, never an inline marker: specstate
detects a claim by the `(in-progress)` substring and freeze.py's marker
regex matches only the exact marker words, so a stamp touches neither.
It is removed on land, release and tick — unlike fix sub-lines it is
not history. A claim with no stamp stays valid (older docsets); only a
stamp with no claim is an error (check.py's pairing gate).

Every verb records one local-only telemetry event (task_claim, task_land
{rounds, seconds_since_claim}, task_fail {round}, task_release
{reason: blocked|orphan|other}, task_drop) — counts and ids only, per
the telemetry contract.

Usage: mark.py <verb> …        (see the verb lines above)
Exit:  0 = done · 1 = transition refused (current marker, wanted
       transition, and the allowed ones printed) · 2 = usage ·
       5 = lock busy (another marker writer holds .task.lock)
"""
from __future__ import annotations

import contextlib
import datetime
import os
import re
import secrets
import stat
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit  # noqa: E402 - sys.path setup above runs first
import graph  # noqa: E402
import specstate  # noqa: E402
from specstate import TaskLockBusy  # noqa: E402

USAGE = "Usage:" + __doc__.split("Usage:", 1)[1].split("Exit:", 1)[0].rstrip()

ENTRY_LINE = re.compile(r"^- \[[x ]\] (T\d{3})\b")
# Where an inline marker is inserted: after the entry id and any
# dependency / parallel flags that directly follow it
# (`- [ ] T002 (after T001) [P] title` → flags then the marker).
LEAD_FLAGS = re.compile(
    r"^- \[[x ]\] T\d{3}(?:\s*\(after\s+T\d{3}\))?(?:\s*\[P\])?")
TASK_ARG = re.compile(r"^T\d{3}$")
DECISION_ARG = re.compile(r"^D-\d{3}$")
DIGEST_STATUS = re.compile(r"status\s+(implemented|already-satisfied)\b")
WAVE_PAYLOAD = re.compile(r"^implementer-(T\d{3})\.md$")

EM = "\u2014"
LOCK_TIMEOUT = 5.0


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _status_holder(spec_dir: Path) -> Path:
    """task.md, or spec.md at tiny tier (its § Tasks) — the file whose
    entries carry the markers, identical rule to tick.py's."""
    spec_path = spec_dir / "spec.md"
    if spec_path.is_file() and specstate.spec_tier(
            spec_path.read_text(encoding="utf-8", errors="replace")) == "tiny":
        return spec_path
    return spec_dir / "task.md"


def _entry_span(lines: list[str], task_id: str) -> tuple[int, int] | None:
    """(first-line index, one-past-end) of task_id's entry block: the
    `- [ ] T###` line plus its contiguous sub-lines up to the first blank
    line or the next entry — the same block task_entries parses."""
    start = None
    for i, ln in enumerate(lines):
        m = ENTRY_LINE.match(ln)
        if m and m.group(1) == task_id:
            start = i
            break
    if start is None:
        return None
    end = start + 1
    while end < len(lines) and lines[end].strip() \
            and not ENTRY_LINE.match(lines[end]):
        end += 1
    return start, end


def _edit_block(lines: list[str], task_id: str,
                edit) -> str | None:
    """Apply `edit(block_lines) -> block_lines | None` to task_id's
    contiguous block in `lines`, splicing the result back in place.
    None when the entry does not exist. Sub-line inserts/removals never
    shift outside indices because the block is edited as its own list."""
    span = _entry_span(lines, task_id)
    if span is None:
        return None
    s, e = span
    block = edit(lines[s:e])
    if block is not None:
        lines[s:e] = block
    return "ok"


def _add_marker(line: str, marker: str) -> str:
    """Insert an inline marker after the entry's leading flags."""
    m = LEAD_FLAGS.match(line)
    at = m.end() if m else len(line)
    return f"{line[:at]} {marker}{line[at:]}"


def _strip_stamp(block: list[str]) -> list[str]:
    """The block without its claim-stamp sub-lines (the stamp is not
    history — land, release, fail and tick all remove it)."""
    return [ln for ln in block if not specstate.CLAIM_NOTE.match(ln)]


def _durable_replace(path: Path, text: str) -> None:
    """Same-directory temp file, fsync, atomic os.replace — mark.py never
    leaves a reader half a file (the tick.py transaction shape)."""
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
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)


def _refuse(task_id: str, current: str, wanted: str,
            allowed: list[str], why: str = "") -> int:
    print(f"refused: {task_id} transition — current entry: {current!r}")
    if why:
        print(f"  {why}")
    print(f"  wanted: {wanted}")
    print(f"  allowed from: {'; '.join(allowed)}")
    return 1


def _record(event: str, **payload) -> None:
    try:
        from telemetry import record
        record("spec-build", event, **payload)
    except Exception:
        pass  # fire-and-forget: telemetry never breaks a marker write


def _write_locked(holder: Path, lines: list[str], had_eol: bool) -> None:
    _durable_replace(holder, "\n".join(lines) + ("\n" if had_eol else ""))


# --- claim ---------------------------------------------------------------

def claim(spec_dir: Path, wave_dir: Path, run_id: str | None) -> int:
    """Claim exactly the implementer-T### files in the wave dir — after
    re-running the frontier on the CURRENT doc state, so a wave computed
    before some other change cannot claim a task that is no longer
    runnable or whose files now overlap a claimed task's."""
    holder = _status_holder(spec_dir)
    if not holder.is_file():
        print(f"no {holder.name} under {spec_dir}", file=sys.stderr)
        return 1
    if not wave_dir.is_dir():
        print(f"no wave dir: {wave_dir}", file=sys.stderr)
        return 2
    payloads = sorted(p.name for p in wave_dir.glob("implementer-T*.md"))
    ids = [m.group(1) for p in payloads if (m := WAVE_PAYLOAD.match(p))]
    if not ids:
        print(f"no implementer-T### payloads in {wave_dir}", file=sys.stderr)
        return 2
    run_id = run_id or f"r-{secrets.token_hex(2)}"

    try:
        with specstate.task_lock(spec_dir, LOCK_TIMEOUT):
            text = holder.read_text(encoding="utf-8")
            entries = specstate.task_entries(text)
            per_task = graph.task_frontier(entries)
            by_id = {t["id"]: t for t in per_task if t["id"]}
            stale = []
            for tid in ids:
                t = by_id.get(tid)
                if t is None or t["state"] != "runnable":
                    state = t["state"] if t else "no such entry"
                    stale.append(f"{tid}: {state} — not runnable")
                elif t.get("deferred"):
                    stale.append(f"{tid}: deferred ({t['deferred']})")
            if stale:
                for s in stale:
                    print(f"  stale wave: {s}")
                print("refused: the wave no longer matches the frontier — "
                      "re-emit and claim the fresh wave (nothing claimed)")
                return 1

            lines = text.splitlines(keepends=False)
            had_eol = text.endswith("\n")
            for tid in ids:
                def edit(block: list[str]) -> list[str]:
                    return ([_add_marker(block[0], "(in-progress)")]
                            + [_stamp_line(run_id)] + block[1:])
                _edit_block(lines, tid, edit)
            _write_locked(holder, lines, had_eol)
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5

    print(f"claimed {len(ids)}: {', '.join(ids)}")
    print(f"run id: {run_id} — reuse it (--run-id) for this session's "
          "waves and graph.py --run-id for orphan scoping")
    _record("task_claim", tasks=len(ids), run=run_id,
            wave=wave_dir.name)
    return 0


def _stamp_line(run_id: str) -> str:
    return f"  - claimed {_now_iso()} {EM} run {run_id}"


# --- land ----------------------------------------------------------------

def land(spec_dir: Path, task_id: str, resolution: str | None,
         digest: str | None, allow_pending: bool = False) -> int:
    """(implemented) in place of the claim — gated on the developer
    digest and a green scoped proofs run. On red proofs nothing is
    written and the fail command is printed."""
    holder = _status_holder(spec_dir)
    if not holder.is_file():
        print(f"no {holder.name} under {spec_dir}", file=sys.stderr)
        return 1
    repo = spec_dir.parent.parent
    try:
        with specstate.task_lock(spec_dir, LOCK_TIMEOUT):
            text = holder.read_text(encoding="utf-8")
            entry = _parse_task(specstate.task_entries(text), task_id)
            if entry is None:
                return _refuse(task_id, "no such entry", "(implemented)",
                               ["an existing `- [ ] T###` entry"])
            if entry.done or entry.struck:
                return _refuse(task_id, entry.first_line, "(implemented)",
                               ["(in-progress)"])
            if not entry.claimed:
                return _refuse(task_id, entry.first_line, "(implemented)",
                               ["(in-progress) — claim the task first "
                                "(mark.py claim)"])

            # the digest gate (D-040): the agent-written digest file is
            # the primary evidence; --digest is the override when the
            # file is missing (a dead session's write), never a way to
            # talk over a file that says blocked
            dig = specstate.latest_digest(spec_dir, task_id)
            if dig is not None:
                status = dig["status"]
                if not re.match(r"(implemented|already-satisfied)\b", status):
                    route = {
                        "scope": ("its scope: deviation names paths outside "
                                  "Touches — widen the entry's Touches under "
                                  "the D-### ruling and re-emit; no fix round"),
                        "spec-defect": ("its spec-defect: deviation says the "
                                        "task itself is wrong — route to "
                                        "/spec-design; no fix round, no "
                                        "higher tier"),
                    }.get(dig.get("deviation_kind"),
                          "rule on the block (D-###) and re-spawn, or route "
                          "to /spec-design")
                    print(f"refused: {task_id}'s digest on file reports "
                          f"{status!r} ({dig['path']}) — a blocked digest "
                          f"is not a landing: `mark.py release` the task "
                          f"and {route}", file=sys.stderr)
                    return 1
            elif digest and DIGEST_STATUS.search(digest):
                print("warning: no digest file under digests/ — using the "
                      "--digest override", file=sys.stderr)
            else:
                print("refused: land needs the developer digest reporting "
                      "implemented/already-satisfied — none on file under "
                      "digests/, and no --digest override given",
                      file=sys.stderr)
                return 1

            print(f"proofs for {task_id}: running its TC commands")
            d = audit.proofs_data(spec_dir, repo, True, task=task_id)
            for line in audit.proof_verdict_lines(d).values():
                print(line)
            if not d["auto"]:
                print(f"refused: no auto proof ran for {task_id} — land "
                      "needs at least one runnable acceptance command "
                      "green (a task with none is a spec gap: "
                      "/spec-design, not a silent pass)", file=sys.stderr)
                return 1
            if d["failed"]:
                print(f"proofs red for {task_id} — nothing landed. Record "
                      "the failure and open the round:")
                print(f"  python3 {Path(__file__).name} fail {spec_dir} "
                      f"{task_id} --evidence <file> --digest \"<line from "
                      "the output above>\"")
                return 1
            pending = d["pending"]
            if pending and len(pending) == len(d["auto"]):
                if not allow_pending:
                    print(f"refused: none of {task_id}'s proofs ran — the "
                          "tests they name do not exist yet "
                          f"({', '.join(sorted(pending))}). Write them with "
                          "the task; if a later task owns them, land with "
                          "--allow-pending (an unproven landing the "
                          "delivery pass will not accept)", file=sys.stderr)
                    return 1
                print(f"warning: {task_id} lands unproven — pending: "
                      f"{', '.join(sorted(pending))}; the delivery pass "
                      "stays red until these tests exist and pass",
                      file=sys.stderr)
            elif pending:
                print(f"note: {len(pending)} of {task_id}'s proofs are "
                      f"pending ({', '.join(sorted(pending))}) — the "
                      "delivery pass needs them", file=sys.stderr)

            open_round = entry.fix_round
            if open_round is not None and not resolution:
                print(f"refused: round {open_round} is open — land needs "
                      f"--resolution \"<what closed it>\"", file=sys.stderr)
                return 2
            lines = text.splitlines(keepends=False)
            had_eol = text.endswith("\n")

            def edit(block: list[str]) -> list[str]:
                first = block[0]
                if " (implemented)" not in first:
                    first = first.replace(" (in-progress)",
                                          " (implemented)", 1)
                else:
                    first = first.replace(" (in-progress)", "", 1)
                out = [first]
                if open_round is not None:
                    out[0] = out[0].replace(
                        f" (fix {open_round}/5)", f" (fixed {open_round}/5)",
                        1)
                    proof = f"audit.py proofs --task {task_id} green"
                    out.append(f"  - fixed {open_round} {EM} {resolution} "
                               f"{EM} {proof}")
                return _strip_stamp(out + block[1:])

            _edit_block(lines, task_id, edit)
            _write_locked(holder, lines, had_eol)
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5

    rounds_note = (f" (round {open_round} closed)" if open_round else "")
    print(f"landed {task_id} (implemented){rounds_note}")
    _record("task_land", task=task_id, rounds=open_round or 0,
            seconds_since_claim=_seconds_since_claim(entry))
    return 0


def _digest_status(digest: str | None) -> str | None:
    if not digest:
        return None
    m = DIGEST_STATUS.search(digest)
    return m.group(1) if m else None


def _seconds_since_claim(entry) -> int | None:
    if not entry.claim:
        return None
    try:
        then = datetime.datetime.fromisoformat(
            entry.claim.at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, int(time.time() - then.timestamp()))


def _parse_task(entries, task_id: str):
    return next((e for e in entries if e.id == task_id), None)


# --- release -------------------------------------------------------------

def release(spec_dir: Path, task_id: str, reason: str) -> int:
    """Remove the claim and its stamp — the blocked/why ruling move and
    the resume move for a dead run's orphan. The reason is recorded as a
    telemetry category only."""
    holder = _status_holder(spec_dir)
    if not holder.is_file():
        print(f"no {holder.name} under {spec_dir}", file=sys.stderr)
        return 1
    try:
        with specstate.task_lock(spec_dir, LOCK_TIMEOUT):
            text = holder.read_text(encoding="utf-8")
            entry = _parse_task(specstate.task_entries(text), task_id)
            if entry is None:
                return _refuse(task_id, "no such entry", "claim released",
                               ["(in-progress)"])
            if not entry.claimed:
                return _refuse(task_id, entry.first_line, "claim released",
                               ["(in-progress) — nothing to release"])
            lines = text.splitlines(keepends=False)
            had_eol = text.endswith("\n")

            def edit(block: list[str]) -> list[str]:
                first = block[0].replace(" (in-progress)", "", 1)
                return [first] + _strip_stamp(block[1:])

            _edit_block(lines, task_id, edit)
            _write_locked(holder, lines, had_eol)
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5

    low = reason.lower()
    category = ("blocked" if low.startswith("blocked")
                else "orphan" if low.startswith("orphan") else "other")
    print(f"released {task_id} — claim cleared ({category}); the next "
          "emit re-spawns it, its partial edits stay in the tree")
    _record("task_release", task=task_id, reason=category)
    return 0


# --- fail ----------------------------------------------------------------

def fail(spec_dir: Path, task_id: str, evidence: Path, digest: str) -> int:
    """Open the next fix round: the marker, the round's open sub-line
    with the verbatim digest, and the evidence file copied verbatim into
    notes/T###.md under `## Fix round n`."""
    holder = _status_holder(spec_dir)
    if not holder.is_file():
        print(f"no {holder.name} under {spec_dir}", file=sys.stderr)
        return 1
    if not evidence.is_file():
        print(f"no evidence file: {evidence}", file=sys.stderr)
        return 2
    evidence_text = evidence.read_text(encoding="utf-8", errors="replace")
    if digest not in evidence_text:
        print("refused: the digest must be copied verbatim from the "
              f"evidence — it is not a substring of {evidence}",
              file=sys.stderr)
        return 1
    note_path = spec_dir / "notes" / f"{task_id}.md"

    try:
        with specstate.task_lock(spec_dir, LOCK_TIMEOUT):
            text = holder.read_text(encoding="utf-8")
            entry = _parse_task(specstate.task_entries(text), task_id)
            if entry is None:
                return _refuse(task_id, "no such entry", "(fix n/5)",
                               ["(in-progress) or (implemented)"])
            if entry.done or entry.struck:
                return _refuse(task_id, entry.first_line, "(fix n/5)",
                               ["(in-progress) or (implemented) — a ticked "
                                "or struck task is closed; route the "
                                "failure through /spec-design"])
            if not (entry.claimed or entry.implemented
                    or entry.fix_round is not None):
                return _refuse(task_id, entry.first_line, "(fix n/5)",
                               ["(in-progress) or (implemented)"])

            prior = max((r.n for r in entry.rounds), default=0)
            if entry.fix_round is not None:
                prior = max(prior, entry.fix_round)
            n = prior + 1
            if n > graph.FIX_CAP:
                print(f"refused: round {n} is above the cap "
                      f"({graph.FIX_CAP}/{graph.FIX_CAP}) — the user must "
                      "decide: wrong (park with a D-###), isolated "
                      "(defer), or load-bearing (/spec-design re-plans)",
                      file=sys.stderr)
                return 1

            lines = text.splitlines(keepends=False)
            had_eol = text.endswith("\n")

            def edit(block: list[str]) -> list[str]:
                first = block[0]
                # the superseded in-flight round closes as failed-again,
                # so the checker's pairing gate stays green: an open
                # sub-line whose marker moved would read as orphaned
                superseded = None
                if entry.fix_round is not None:
                    # a re-fail over an open round: the claim goes, the
                    # marker advances, the old round closes as failed-again
                    old = entry.fix_round
                    superseded = (f"  - fixed {old} {EM} failed again {EM} "
                                  f"superseded by round {n} "
                                  f"(notes/{task_id}.md)")
                    first = first.replace(" (in-progress)", "", 1)
                    first = first.replace(f" (fix {old}/5)",
                                          f" (fix {n}/5)", 1)
                elif " (in-progress)" in first:
                    first = first.replace(
                        " (in-progress)", f" (fix {n}/5)", 1)
                elif " (implemented)" in first:
                    first = first.replace(
                        " (implemented)", f" (implemented) (fix {n}/5)", 1)
                out = [first]
                if superseded:
                    out.append(superseded)
                out.append(f"  - fix {n} {EM} {digest}")
                return _strip_stamp(out + block[1:])

            _edit_block(lines, task_id, edit)
            _write_locked(holder, lines, had_eol)

            # the note file: the round's evidence verbatim (the developer
            # may append later — its one specs/ exception)
            note_path.parent.mkdir(parents=True, exist_ok=True)
            with note_path.open("a", encoding="utf-8") as f:
                if note_path.stat().st_size == 0:
                    f.write(f"# Notes: {task_id}\n\n")
                f.write(f"\n## Fix round {n}\n{evidence_text}")
                if not evidence_text.endswith("\n"):
                    f.write("\n")
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5

    print(f"fix round {n} opened on {task_id} — evidence in "
          f"{note_path}, re-emit and spawn the round's payload")
    if n == 3:
        print("round 3 suspects the plan: repair via /spec-design before "
              "round 4")
    sig, run = specstate.failure_signature_run(
        note_path.read_text(encoding="utf-8", errors="replace"))
    if sig and run >= graph.SAME_FAILURE_ADVISORY:
        print(f"same-signature: {sig} has failed {run} consecutive "
              f"round(s) — another round, or a stronger tier, re-runs the "
              "same failing command; repair the plan (/spec-design) or "
              "adjudicate now (D-044)")
    if n == 4:
        print("round 4: spawn one tier up")
    if n == graph.FIX_CAP:
        print(f"round {graph.FIX_CAP} is the cap — the engine never "
              "re-spawns it; the user must decide: wrong (park with a "
              "D-###), isolated (defer), or load-bearing (/spec-design "
              "re-plans)")
    _record("task_fail", task=task_id, round=n)
    return 0


# --- drop ----------------------------------------------------------------

def drop(spec_dir: Path, task_id: str, decision: str) -> int:
    """Strike the entry with its ruling — refused when the D-### is not
    defined in tech-spec.md, refused outright at Tier: tiny."""
    spec_md = (spec_dir / "spec.md").read_text(
        encoding="utf-8", errors="replace") \
        if (spec_dir / "spec.md").is_file() else ""
    if specstate.spec_tier(spec_md) == "tiny":
        print("refused: Tier: tiny — dropping a task breaks the frozen "
              "spec.md; route the change to /spec-design for re-approval",
              file=sys.stderr)
        return 1
    tech_md = (spec_dir / "tech-spec.md").read_text(
        encoding="utf-8", errors="replace") \
        if (spec_dir / "tech-spec.md").is_file() else ""
    defined = specstate.defined_ids(tech_md).get("D", set())
    if decision not in defined:
        print(f"refused: {decision} is not defined in tech-spec.md — a "
              "drop rides a real ruling, not an invented id "
              f"(defined: {', '.join(sorted(defined)) or 'none'})",
              file=sys.stderr)
        return 1
    holder = _status_holder(spec_dir)
    if not holder.is_file():
        print(f"no {holder.name} under {spec_dir}", file=sys.stderr)
        return 1

    try:
        with specstate.task_lock(spec_dir, LOCK_TIMEOUT):
            text = holder.read_text(encoding="utf-8")
            entry = _parse_task(specstate.task_entries(text), task_id)
            if entry is None:
                return _refuse(task_id, "no such entry", "dropped",
                               ["any open entry"])
            if entry.done:
                return _refuse(task_id, entry.first_line, "dropped",
                               ["any open entry — a ticked task is "
                                "delivered work, not open scope"])
            if entry.struck:
                return _refuse(task_id, entry.first_line, "dropped",
                               ["— already struck"])
            today = datetime.date.today().isoformat()
            lines = text.splitlines(keepends=False)
            had_eol = text.endswith("\n")

            def edit(block: list[str]) -> list[str]:
                return [f"- [ ] ~~{task_id}~~ dropped {today} "
                        f"({decision})"] + _strip_stamp(block[1:])

            _edit_block(lines, task_id, edit)
            _write_locked(holder, lines, had_eol)
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5

    print(f"dropped {task_id} ({decision}) — struck in {holder.name}, "
          "the decision stays visible")
    _record("task_drop", task=task_id, decision=decision)
    return 0


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if args else 2
    verb = args.pop(0)
    positional: list[str] = []
    opts: dict[str, str] = {}
    flags = {"--wave", "--run-id", "--resolution", "--digest",
             "--reason", "--evidence", "--decision"}
    switches = {"--allow-pending"}
    it = iter(args)
    for a in it:
        if a in switches:
            opts[a] = "1"
        elif a in flags:
            v = next(it, None)
            if v is None:
                print(f"{a} needs a value\n{USAGE}", file=sys.stderr)
                return 2
            opts[a] = v
        else:
            positional.append(a)
    if verb not in ("claim", "land", "release", "fail", "drop"):
        print(f"unknown verb: {verb!r} — verbs: claim, land, release, "
              f"fail, drop\n{USAGE}", file=sys.stderr)
        return 2
    if verb != "claim" and (len(positional) != 2
                            or not TASK_ARG.match(positional[1])):
        print("every verb except claim takes <spec-dir> T###",
              file=sys.stderr)
        return 2
    if verb == "claim":
        if len(positional) != 1 or "--wave" not in opts:
            print(USAGE, file=sys.stderr)
            return 2
        return claim(Path(positional[0]), Path(opts["--wave"]),
                     opts.get("--run-id"))
    if verb == "land":
        return land(Path(positional[0]), positional[1],
                    opts.get("--resolution"), opts.get("--digest"),
                    "--allow-pending" in opts)
    if verb == "release":
        if "--reason" not in opts:
            print(USAGE, file=sys.stderr)
            return 2
        return release(Path(positional[0]), positional[1],
                       opts["--reason"])
    if verb == "fail":
        if "--evidence" not in opts or "--digest" not in opts:
            print(USAGE, file=sys.stderr)
            return 2
        return fail(Path(positional[0]), positional[1],
                    Path(opts["--evidence"]), opts["--digest"])
    if "--decision" not in opts or not DECISION_ARG.match(opts["--decision"]):
        print(USAGE + "\ndrop needs --decision D-### (defined in "
              "tech-spec.md)", file=sys.stderr)
        return 2
    return drop(Path(positional[0]), positional[1], opts["--decision"])


if __name__ == "__main__":
    sys.exit(main())
