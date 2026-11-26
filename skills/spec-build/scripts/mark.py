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

  mark.py claim   <spec-dir> --wave <wave-dir> [--run-id ID] [--harness NAME]
                  [--budget-spawns N] [--budget-minutes N]
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
fail command to run. The file is read through its digest schema
(scripts/digests.py, D-054): a file that exists but carries no valid
digest line refuses the landing as malformed — a fix and run again
that `--digest` never talks over. The file opens with its `tools:`
report (D-056): one that lacks a tool the developer requires — a file
writer, and Bash — refuses the landing as a failed spawn, never a fix
round, which `--digest` does not talk over either. When none exists
the override is
read for a status only: it is the orchestrator's attestation, not an
agent artifact. A proof whose named tests do not exist is PENDING,
never a pass, and an ENV-BLOCKED proof (D-047 — the environment it
needs is missing) counts the same: neither ran. When none of the
task's proofs ran, land refuses unless `--allow-pending` says the
tests are written by a later task (or the environment cannot be
supplied) — the landing is then an unproven `(implemented)`, and the
delivery pass (dod gate 1) stays red until the pending proofs run or
the env-blocked ones are ruled. fail copies the digest verbatim from the recorded
evidence and refuses a digest that is not a substring of it; a
superseded in-flight round closes as `fixed n — failed again — …` so
the checker's pairing gate stays green; round 3 points at
/spec-design, round 4 — the last attempt — one model step up, and
round 4 failing writes the stop marker `(fix 5/5)`, the cap: the
user's adjudication. drop strikes the entry with its D-### ruling —
refused for a D-### tech-spec.md does not define, and refused outright
at Tier: tiny (a drop breaks the freeze — route it to /spec-design).

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

Every verb also appends one row to the spec's run ledger
(`specs/<name>/runs/ledger.jsonl`, D-055) — inside the same lock hold
as the marker write, so a landing and the record of what landed are
written together. The ledger is evidence, never status: what ran
(run id, role, payload sha, the brief's model, the harness `claim
--harness` was given), what was seen (each digest file's sha and status
word), and what the verb did. `claim --harness NAME` records the
harness running the session, verbatim; ungiven, the row says `unknown`.
Before `land` and `fail` read a digest, the orchestrator's provenance
sweep runs over digests/wave-*/: every digest file with no provenance
line yet is validated with its role's schema and, when valid, gains the
one line the ledger vouches for — the request that produced it, from
what the orchestrator spawned, never from the agent. A malformed file,
or one whose provenance line no ledger row vouches for, is left as it
is, recorded as `digest_malformed`, and named. Agents are never asked
to write or copy a provenance line.

Claims are checked against every other spec's live claims in the repo
(spec-build D-057): `claim` registers each task it claims in
`specs/.claims/registry.json` under one repo-level lock,
`specs/.claims.lock`, taken outside the spec's `.task.lock` and never
inside it. A wave task whose `Touches:` overlap a live entry of another
spec — live while that spec's task still reads `(in-progress)` — is
dropped from the wave and printed `deferred: T### (shares <path> with
<other-spec>/T###)`; the rest is claimed. `land`, `release`, `drop` and
tick.py remove the spec's entry, and rows whose task is no longer
claimed are swept on the next claim. A registry that cannot be read or
parsed is refused, never read as empty: remove or repair it.

A run budget is spent — 30 implementer spawns or 120 wall-clock
minutes since the first claim, by default; D-059 — and `claim` refuses
with exit 1: `AWAITING HUMAN: run budget — <what> used <n> of <n>`,
the same line `graph.py --run` parks on. Both are counted from the
spec's run ledger: the spawns over the run (its `claim` rows) and
again over the spec's whole ledger, the minutes over this run alone
since its first claim — a spec resumed hours or days later under a new
run id is never refused on minutes. So the budget holds however the
run is driven; `--budget-spawns N` and `--budget-minutes N` raise or
lower one on the claim, and 0 lifts it. Tokens are not budgeted: no
harness reports them to the kit. A refusal claims nothing and writes
nothing.

Under `graph.py --isolate worktree` (D-058) each implementer works in
its own detached worktree at `<repo>/.spec-kit/worktrees/<spec>/T###/`,
a snapshot of the main tree, and land merges from there. With a
worktree present, land runs the proofs in the worktree, folds its whole
delta — tracked and untracked, binary included — into the main tree
with `git apply` to the working tree alone (nothing staged, nothing
committed, the index untouched), removes the worktree, and lands as
usual. A delta the main tree will not take clean is refused with exit
1, naming both trees and the conflicting paths: nothing is written, the
worktree stays and the task stays claimed — settle by hand, then land
again or release. release removes the worktree with the claim, so its
work is discarded; fail keeps it, and the next round continues there.

Usage: mark.py <verb> …        (see the verb lines above)
Exit:  0 = done · 1 = transition refused (current marker, wanted
       transition, and the allowed ones printed), or a run budget spent
       (nothing claimed) · 2 = usage ·
       5 = lock busy (another writer holds .task.lock or .claims.lock)
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
import digests  # noqa: E402
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
DIGEST_OUTCOME = re.compile(
    r"status\s+(implemented|already-satisfied|blocked)\b")
WAVE_PAYLOAD = re.compile(r"^implementer-(T\d{3})\.md$")
WAVE_DIR_NAME = re.compile(r"wave-(\d+)$")
DEVELOPER_BRIEF = (Path(__file__).resolve().parent.parent
                   / "agents" / "developer.md")

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


def _ledger(spec_dir: Path, *rows: dict) -> None:
    """Append the verb's rows to the run ledger. Called inside the lock
    the verb already holds, so the marker write and its record land in
    one critical section; a ledger that cannot be written is reported
    and never undoes the marker."""
    try:
        for row in rows:
            specstate.ledger_append(spec_dir, row)
    except OSError as exc:
        print(f"warning: run ledger not written — {exc}", file=sys.stderr)


def _sweep(spec_dir: Path, task_id: str | None = None) -> None:
    """The provenance sweep before a verb reads a digest: every
    malformed file it left in place is named — except the task's own,
    which a land refusal names itself."""
    own = ((specstate.latest_digest(spec_dir, task_id) or {}).get("path")
           if task_id else None)
    for seen in specstate.sweep_digests(spec_dir, "spec-build"):
        if seen["path"] != own:
            print(f"note: malformed digest at {seen['path']} — "
                  f"{'; '.join(seen['problems'])} — fix and run again: "
                  "re-spawn the same payload to rewrite its digest file",
                  file=sys.stderr)


def _digest_sha(path: str) -> str | None:
    try:
        return specstate.digest_sha(Path(path).read_text(
            encoding="utf-8", errors="replace"))
    except OSError:
        return None


def _claim_run(entry) -> str | None:
    return entry.claim.run if entry.claim else None


def _task_row(event: str, task_id: str, entry, **fields) -> dict:
    return specstate.ledger_row(
        "spec-build", event, run=_claim_run(entry), task=task_id,
        role="implementer", stem=f"implementer-{task_id}", **fields)


def _write_locked(holder: Path, lines: list[str], had_eol: bool) -> None:
    _durable_replace(holder, "\n".join(lines) + ("\n" if had_eol else ""))


def _forget_locked(spec_dir: Path, task_id: str, registry: dict) -> None:
    """Drop the task's claim-registry row while both locks are held;
    written only when it had one."""
    kept = specstate.claims_without(registry, spec_dir, [task_id])
    if len(kept) != len(registry):
        specstate.claims_write(spec_dir, kept)


# --- claim ---------------------------------------------------------------

def claim(spec_dir: Path, wave_dir: Path, run_id: str | None,
          harness: str = specstate.UNKNOWN_HARNESS,
          budget_spawns: int = specstate.BUDGET_SPAWNS,
          budget_minutes: int = specstate.BUDGET_MINUTES) -> int:
    """Claim exactly the implementer-T### files in the wave dir — after
    re-running the frontier on the CURRENT doc state, so a wave computed
    before some other change cannot claim a task that is no longer
    runnable or whose files now overlap a claimed task's. A task whose
    files overlap a live claim of another spec in the repo is dropped
    from the wave and printed `deferred` (D-057); the rest is claimed.
    The registry lock is taken outside the spec's task lock, never the
    reverse. A spent run budget (D-059) refuses first, under the same
    locks the claim would write under: nothing claimed, nothing
    written."""
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
        with specstate.claims_lock(spec_dir, LOCK_TIMEOUT), \
                specstate.task_lock(spec_dir, LOCK_TIMEOUT):
            stop = specstate.budget_stop(spec_dir, run_id, budget_spawns,
                                         budget_minutes)
            if stop:
                print("\n".join(stop))
                print("refused: the run budget is spent (nothing claimed)")
                return 1
            text = holder.read_text(encoding="utf-8")
            registry = specstate.claims_live(
                spec_dir, specstate.claims_read(spec_dir))
            own = specstate.claim_key(spec_dir, "")
            held = {key: row["paths"] for key, row in registry.items()
                    if not key.startswith(own)}
            entries = specstate.task_entries(text)
            per_task = graph.task_frontier(entries, held=held)
            by_id = {t["id"]: t for t in per_task if t["id"]}
            stale, dropped = [], {}
            for tid in ids:
                t = by_id.get(tid)
                if t is None or t["state"] != "runnable":
                    state = t["state"] if t else "no such entry"
                    stale.append(f"{tid}: {state} — not runnable")
                elif t.get("held_by"):
                    dropped[tid] = t["deferred"]
                elif t.get("deferred"):
                    stale.append(f"{tid}: deferred ({t['deferred']})")
            if stale:
                for s in stale:
                    print(f"  stale wave: {s}")
                print("refused: the wave no longer matches the frontier — "
                      "re-emit and claim the fresh wave (nothing claimed)")
                return 1
            ids = [tid for tid in ids if tid not in dropped]
            for tid, why in sorted(dropped.items()):
                print(f"deferred: {tid} ({why})")
            try:
                specstate.claims_write(spec_dir, {
                    **registry,
                    **{specstate.claim_key(spec_dir, tid): {
                        "run": run_id, "at": _now_iso(),
                        "paths": by_id[tid]["files"]}
                       for tid in ids}})
            except OSError as exc:
                print(f"refused: the claim registry cannot be written — "
                      f"{exc} (nothing claimed)", file=sys.stderr)
                return 1

            lines = text.splitlines(keepends=False)
            had_eol = text.endswith("\n")
            for tid in ids:
                def edit(block: list[str]) -> list[str]:
                    return ([_add_marker(block[0], "(in-progress)")]
                            + [_stamp_line(run_id)] + block[1:])
                _edit_block(lines, tid, edit)
            _write_locked(holder, lines, had_eol)
            wave_no = WAVE_DIR_NAME.fullmatch(wave_dir.name)
            _ledger(spec_dir, *(
                specstate.ledger_row(
                    "spec-build", "claim", run=run_id,
                    wave=int(wave_no.group(1)) if wave_no else None,
                    task=tid, role="implementer",
                    lens=graph.AGENT_BRIEFS["execute"][2],
                    stem=f"implementer-{tid}",
                    payload=specstate.file_sha(
                        wave_dir / f"implementer-{tid}.md"),
                    model=specstate.brief_model(DEVELOPER_BRIEF),
                    harness=harness)
                for tid in ids))
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5
    except specstate.ClaimsRegistryError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    if not ids:
        print("nothing claimed — every task in the wave is held off by "
              "another spec's claim; re-emit once it lands or is released")
        return 0
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
    _sweep(spec_dir, task_id)
    repo = spec_dir.parent.parent
    worktree = specstate.worktree_path(repo, spec_dir.name, task_id)
    isolated = worktree.is_dir()
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
            # talk over a file that says blocked — or says nothing
            # the schema accepts
            dig = specstate.latest_digest(spec_dir, task_id)
            if dig is not None \
                    and dig["state"] == specstate.DIGEST_MALFORMED:
                print(f"refused: malformed digest at {dig['path']} — "
                      f"{'; '.join(dig['problems'])} — fix and run "
                      "again: re-spawn the developer with the same "
                      "payload to rewrite its digest file",
                      file=sys.stderr)
                return 1
            if dig is not None:
                # the capability handshake (D-056): the file's `tools:`
                # line must cover the developer's required tools. A
                # report that lacks one is a failed spawn — the task
                # stays claimed, no round opens, and no --digest talks
                # over it; recorded once per content, like a malformed file
                reported = digests.tools_report(Path(dig["path"]).read_text(
                    encoding="utf-8", errors="replace"))
                missing = digests.tools_missing("developer", reported)
                if missing:
                    sha = _digest_sha(dig["path"])
                    if not any(row.get("event") == specstate.CAPABILITY_MISSING
                               and row.get("task") == task_id
                               and row.get("digest") == sha
                               for row in specstate.ledger_rows(spec_dir)):
                        _ledger(spec_dir, _task_row(
                            specstate.CAPABILITY_MISSING, task_id, entry,
                            wave=dig["wave"], digest=sha,
                            outcome=", ".join(missing),
                            **{specstate.TOOLS_FIELD:
                               specstate.tools_reported(reported)}))
                    print(f"refused: {digests.tools_refusal('developer', reported, missing)} "
                          f"— the digest file at {dig['path']} lands nothing: "
                          f"`mark.py release` {task_id} --reason \"blocked: "
                          "capability handshake failed\", then re-emit and "
                          "spawn it again", file=sys.stderr)
                    return 1
                status = dig["status"]
                if status not in ("implemented", "already-satisfied"):
                    route = {
                        "scope": ("its scope: deviation names paths outside "
                                  "Touches — widen the entry's Touches under "
                                  "the D-### ruling and re-emit; no fix round"),
                        "spec-defect": ("its spec-defect: deviation says the "
                                        "task itself is wrong — route to "
                                        "/spec-design; no fix round, no "
                                        "stronger model"),
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

            print(f"proofs for {task_id}: running its TC commands"
                  + (f" in the worktree {worktree}" if isolated else ""))
            d = audit.proofs_data(spec_dir, worktree if isolated else repo,
                                  True, task=task_id)
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
            blocked = d["env_blocked"]
            unrun = sorted(set(pending) | set(blocked))
            if unrun and len(unrun) == len(d["auto"]):
                if not allow_pending:
                    why = []
                    if blocked:
                        why.append("ENV-BLOCKED: " + ", ".join(
                            f"{tc} (missing: {blocked[tc]})"
                            for tc in sorted(blocked)))
                    if pending:
                        why.append("pending — the tests they name do not "
                                   f"exist yet: {', '.join(sorted(pending))}")
                    print(f"refused: none of {task_id}'s proofs ran — "
                          f"{'; '.join(why)}. Write the tests with the "
                          "task, or supply what the environment is "
                          "missing; if a later task owns the tests or the "
                          "environment cannot be supplied, land with "
                          "--allow-pending (an unproven landing the "
                          "delivery pass will not accept)", file=sys.stderr)
                    return 1
                loud = []
                if blocked:
                    loud.append("env-blocked: " + ", ".join(
                        f"{tc} (missing {blocked[tc]})"
                        for tc in sorted(blocked)))
                if pending:
                    loud.append(f"pending: {', '.join(sorted(pending))}")
                print(f"warning: {task_id} lands unproven — "
                      f"{'; '.join(loud)}; the delivery pass stays red "
                      "until these proofs run (the env-blocked ones until "
                      "they run or are ruled)", file=sys.stderr)
            else:
                if blocked:
                    print(f"note: {len(blocked)} of {task_id}'s proofs are "
                          "ENV-BLOCKED (" + ", ".join(
                              f"{tc}: missing {blocked[tc]}"
                              for tc in sorted(blocked))
                          + ") — the delivery pass needs them run or ruled",
                          file=sys.stderr)
                if pending:
                    print(f"note: {len(pending)} of {task_id}'s proofs are "
                          f"pending ({', '.join(sorted(pending))}) — the "
                          "delivery pass needs them", file=sys.stderr)

            open_round = entry.fix_round
            if open_round is not None and not resolution:
                print(f"refused: round {open_round} is open — land needs "
                      f"--resolution \"<what closed it>\"", file=sys.stderr)
                return 2
            if isolated:
                refused = _merge_worktree(task_id, repo, worktree)
                if refused is not None:
                    return refused
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
            _ledger(spec_dir, _task_row(
                "land", task_id, entry,
                wave=dig["wave"] if dig is not None else None,
                digest=_digest_sha(dig["path"]) if dig is not None else None,
                outcome=(dig["status"] if dig is not None
                         else _digest_status(digest))))
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5

    specstate.claims_forget(spec_dir, [task_id])

    rounds_note = (f" (round {open_round} closed)" if open_round else "")
    print(f"landed {task_id} (implemented){rounds_note}")
    _record("task_land", task=task_id, rounds=open_round or 0,
            seconds_since_claim=_seconds_since_claim(entry))
    return 0


def _merge_worktree(task_id: str, repo: Path, worktree: Path) -> int | None:
    """Fold the worktree's delta into the main tree and remove the
    worktree (D-058): None once done, 1 when the main tree would not
    take the delta — nothing is written then, the worktree stays and
    the task stays claimed."""
    try:
        merged, refused = specstate.worktree_merge(repo, worktree)
    except specstate.WorktreeError as exc:
        print(f"refused: {task_id}'s delta cannot be read off its worktree "
              f"— {exc}\n  worktree: {worktree}\n  main tree: {repo}\n"
              f"nothing was written; the worktree stays and {task_id} "
              "stays claimed", file=sys.stderr)
        return 1
    if refused:
        print(f"refused: {task_id}'s worktree delta does not apply to the "
              f"main tree — {len(refused)} conflicting path(s):",
              file=sys.stderr)
        for path in refused:
            print(f"  {path}", file=sys.stderr)
        print(f"  worktree: {worktree}\n  main tree: {repo}\n"
              "nothing was written; the worktree stays and the task stays "
              "claimed — settle by hand, then land again or release",
              file=sys.stderr)
        return 1
    done = (f"{len(merged)} path(s) merged into {repo} — working tree "
            "only: nothing staged, nothing committed" if merged else
            "nothing to merge — the worktree holds no change (a developer "
            "that worked in the main tree left its edits there)")
    left = specstate.worktree_remove(repo, worktree)
    if left is None:
        print(f"worktree {worktree}: {done}; worktree removed")
    else:
        print(f"worktree {worktree}: {done}\n"
              f"warning: the worktree was NOT removed — {left}; remove it "
              f"by hand: git worktree remove --force {worktree}",
              file=sys.stderr)
    return None


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
    low = reason.lower()
    category = ("blocked" if low.startswith("blocked")
                else "orphan" if low.startswith("orphan") else "other")
    try:
        with specstate.claims_lock(spec_dir, LOCK_TIMEOUT), \
                specstate.task_lock(spec_dir, LOCK_TIMEOUT):
            text = holder.read_text(encoding="utf-8")
            entry = _parse_task(specstate.task_entries(text), task_id)
            if entry is None:
                return _refuse(task_id, "no such entry", "claim released",
                               ["(in-progress)"])
            if not entry.claimed:
                return _refuse(task_id, entry.first_line, "claim released",
                               ["(in-progress) — nothing to release"])
            registry = specstate.claims_read(spec_dir)
            lines = text.splitlines(keepends=False)
            had_eol = text.endswith("\n")

            def edit(block: list[str]) -> list[str]:
                first = block[0].replace(" (in-progress)", "", 1)
                return [first] + _strip_stamp(block[1:])

            _edit_block(lines, task_id, edit)
            _write_locked(holder, lines, had_eol)
            _forget_locked(spec_dir, task_id, registry)
            seen = specstate.latest_digest(spec_dir, task_id)
            _ledger(spec_dir, _task_row(
                "release", task_id, entry, outcome=category,
                wave=seen["wave"] if seen else None,
                digest=_digest_sha(seen["path"]) if seen else None))
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5
    except specstate.ClaimsRegistryError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    worktree = specstate.worktree_path(spec_dir.parent.parent,
                                        spec_dir.name, task_id)
    if not worktree.is_dir():
        tail = ("the next emit re-spawns it, its partial edits stay in "
                "the tree")
    else:
        left = specstate.worktree_remove(spec_dir.parent.parent, worktree)
        if left is None:
            tail = (f"its worktree {worktree} is removed with the work in "
                    "it — the next emit re-spawns it in a fresh one")
        else:
            print(f"warning: the worktree was NOT removed — {left}",
                  file=sys.stderr)
            tail = (f"the next emit re-spawns it once the leftover worktree "
                    f"is removed by hand (git worktree remove --force "
                    f"{worktree})")
    print(f"released {task_id} — claim cleared ({category}); {tail}")
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
    _sweep(spec_dir)

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
            seen = specstate.latest_digest(spec_dir, task_id)
            reported = DIGEST_OUTCOME.search(digest)
            _ledger(spec_dir, _task_row(
                "fail", task_id, entry,
                wave=seen["wave"] if seen else None,
                digest=_digest_sha(seen["path"]) if seen else None,
                outcome=reported.group(1) if reported else None))
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5

    print(f"fix round {n} opened on {task_id} — evidence in "
          f"{note_path}, re-emit and spawn the round's payload")
    worktree = specstate.worktree_path(spec_dir.parent.parent,
                                        spec_dir.name, task_id)
    if worktree.is_dir():
        print(f"worktree kept: {worktree} — the round continues there")
    if n == 3:
        print("round 3 suspects the plan: repair via /spec-design before "
              "round 4")
    sig, run = specstate.failure_signature_run(
        note_path.read_text(encoding="utf-8", errors="replace"))
    if sig and run >= graph.SAME_FAILURE_ADVISORY:
        print(f"same-signature: {sig} has failed {run} consecutive "
              f"round(s) — another round, or a stronger model, re-runs the "
              "same failing command; repair the plan (/spec-design) or "
              "adjudicate now (D-044)")
    if n == 4:
        print("round 4: spawn one model step up")
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
        with specstate.claims_lock(spec_dir, LOCK_TIMEOUT), \
                specstate.task_lock(spec_dir, LOCK_TIMEOUT):
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
            registry = specstate.claims_read(spec_dir)
            today = datetime.date.today().isoformat()
            lines = text.splitlines(keepends=False)
            had_eol = text.endswith("\n")

            def edit(block: list[str]) -> list[str]:
                return [f"- [ ] ~~{task_id}~~ dropped {today} "
                        f"({decision})"] + _strip_stamp(block[1:])

            _edit_block(lines, task_id, edit)
            _write_locked(holder, lines, had_eol)
            _forget_locked(spec_dir, task_id, registry)
            _ledger(spec_dir, _task_row("drop", task_id, entry))
    except TaskLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 5
    except specstate.ClaimsRegistryError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

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
             "--reason", "--evidence", "--decision", "--harness",
             "--budget-spawns", "--budget-minutes"}
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
    if verb != "claim" and "--harness" in opts:
        print("--harness is claim's flag — the run ledger takes the "
              "harness with the claims of one run\n" + USAGE,
              file=sys.stderr)
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
        budgets = {"--budget-spawns": specstate.BUDGET_SPAWNS,
                   "--budget-minutes": specstate.BUDGET_MINUTES}
        for flag, value in opts.items():
            if flag in budgets:
                if not re.fullmatch(r"\d+", value):
                    print(f"{flag} needs a whole number >= 0 (0 lifts "
                          f"the budget)\n{USAGE}", file=sys.stderr)
                    return 2
                budgets[flag] = int(value)
        return claim(Path(positional[0]), Path(opts["--wave"]),
                     opts.get("--run-id"),
                     opts.get("--harness") or specstate.UNKNOWN_HARNESS,
                     budgets["--budget-spawns"], budgets["--budget-minutes"])
    if "--budget-spawns" in opts or "--budget-minutes" in opts:
        print("--budget-spawns/--budget-minutes are claim's flags — only "
              "a claim is counted against a run budget\n" + USAGE,
              file=sys.stderr)
        return 2
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
