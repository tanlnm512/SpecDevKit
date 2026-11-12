#!/usr/bin/env python3
"""retro.py — the retrospective and decisions roll-up.

Writes <spec-dir>/retro.md, assembled only from the spec's own records:
task states and fix rounds — (fixed n/5) markers, notes/T###.md
fix-round headings, and the task entries' fix/fixed sub-lines — the
D-### decisions (those past the approval freeze's tech-spec prefix
are deviations), the delivery facts — the status holder's delivery
block, with notes/delivery.md as the fallback for specs that predate
the block — the spec's specs/BACKLOG.md lines, and the local telemetry
counts for the spec. Then appends each D-###
title to specs/context/decisions.md, so the decisions outlive the
archived spec. The delivery pass writes the retro at ship; an existing
retro.md is reused, never rewritten — nothing is committed.

Usage: retro.py <spec-dir> <spec-name> [<repo-root>]
Exit:  0 = written or an existing retro reused · 1 = unreadable spec dir or a failed write · 2 = usage.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit  # noqa: E402
import specstate  # noqa: E402
import telemetry  # noqa: E402

DECISION = re.compile(r"^###[ \t]+(D-\d{3})[ \t]*[:—-][ \t]*(.+?)[ \t]*$", re.M)
FIXED = re.compile(r"\(fixed (\d)/5\)")
FIX_ROUND_HEADING = re.compile(r"^## Fix round \d+", re.M)
TECH_PREFIX = re.compile(r"^-\s+`tech-spec\.md`:\s+prefix\s+sha256:[0-9a-f]{64}\s+length:(\d+)", re.M)
DECISIONS_HEADER = ("# Decisions\n\nArchitecture decisions of archived specs, one line each; "
                    "the full record lives in the archived spec.\n\n")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def decisions(spec_dir: Path) -> list[tuple[str, str, bool]]:
    """(id, title, deviation) — a deviation sits past the approved tech-spec prefix."""
    source = spec_dir / ("tech-spec.md" if (spec_dir / "tech-spec.md").is_file() else "spec.md")
    raw = source.read_bytes() if source.is_file() else b""
    m = TECH_PREFIX.search(_read(spec_dir / "approvals" / "approval.md"))
    approved_len = int(m.group(1)) if m and source.name == "tech-spec.md" else len(raw)
    text = raw.decode("utf-8", errors="replace")
    return [(d.group(1), d.group(2), len(text[:d.start()].encode("utf-8")) >= approved_len)
            for d in DECISION.finditer(text)]


def task_rows(spec_dir: Path) -> list[tuple[str, str, int, tuple[specstate.FixRound, ...]]]:
    spec_md = _read(spec_dir / "spec.md")
    source = (specstate.tiny_task_text(spec_md) or "" if specstate.spec_tier(spec_md) == "tiny"
              else _read(spec_dir / "task.md"))
    rows = []
    for e in specstate.task_entries(source):
        state = "struck" if e.struck else "ticked" if e.done else "open"
        fixed = FIXED.search(e.first_line)
        logged = len(FIX_ROUND_HEADING.findall(_read(spec_dir / "notes" / f"{e.id}.md")))
        rounds = max(int(fixed.group(1)) if fixed else 0, logged, len(e.rounds))
        rows.append((e.id or e.first_line.strip(), state, rounds, e.rounds))
    return rows


def telemetry_lines(name: str) -> list[str]:
    if not telemetry.enabled():
        return ["Telemetry is off (KIT_TELEMETRY)."]
    counts: dict[str, list[int]] = {}
    path = telemetry.store_path("spec-build")
    for line in _read(path).splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        payload = row.get("payload") if isinstance(row, dict) else None
        if not isinstance(payload, dict) or payload.get("spec") != name:
            continue
        key = str(row.get("event", "?")) + (f" {payload['mode']}" if payload.get("mode") else "")
        tally = counts.setdefault(key, [0, 0])
        tally[0] += 1
        tally[1] += payload.get("rc") not in (0, None)
    return [f"- {key}: {n} run(s), {red} red" for key, (n, red) in sorted(counts.items())]


def retro(spec_dir: Path, name: str, root: Path) -> str:
    backlog = [line for line in _read(root / "specs" / "BACKLOG.md").splitlines()
               if line.startswith(f"- {name} — ")]
    decided = decisions(spec_dir)
    rows = task_rows(spec_dir)
    facts, _ = audit.delivery_block(spec_dir)
    note = facts.strip() or _read(spec_dir / "notes" / "delivery.md").strip()
    record = specstate.delivery_state(_read(spec_dir / (
        "spec.md" if specstate.spec_tier(_read(spec_dir / "spec.md")) == "tiny" else "task.md")))
    out = [f"# Retro: {name}", "",
           "Assembled from this spec's own records; no line is a judgement.", "",
           "## Tasks", "", "| Task | State | Fix rounds |", "|------|-------|------------|",
           *(f"| {tid} | {state} | {rounds} |" for tid, state, rounds, _ in rows),
           "", f"Fix rounds: {sum(r[2] for r in rows)} across {len(rows)} task(s)."]
    out += [f"- {tid} fix {r.n} — {r.digest}"
            + (f" — fixed: {r.resolution} — proof: {r.proof}" if r.closed else " — open")
            for tid, _, _, rs in rows for r in rs]
    out += ["", "## Decisions", ""]
    out += [f"- {d}: {t}" + (" (deviation, after approval)" if dev else "")
            for d, t, dev in decided] or ["None recorded."]
    out += ["", "## Delivery note", "", note or "None recorded.", "", "## Parked", ""]
    out += backlog or ["Nothing parked."]
    out += ["", "## Telemetry (this machine)", ""]
    out += telemetry_lines(name) or ["No events recorded for this spec."]
    out += ["", "## Delivered", "", f"Delivered: commit @ {record[1] or '-'}", ""]
    return "\n".join(out)


def roll_up(spec_dir: Path, name: str, root: Path) -> int:
    target = root / "specs" / "context" / "decisions.md"
    existing = _read(target)
    lines = [f"- {name} {d}: {t}" for d, t, _ in decisions(spec_dir)]
    new = [line for line in lines if line not in existing.splitlines()]
    if new:
        target.parent.mkdir(parents=True, exist_ok=True)
        head = existing.rstrip("\n") + "\n" if existing else DECISIONS_HEADER
        target.write_text(head + "\n".join(new) + "\n", encoding="utf-8")
    return len(new)


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3) or argv[0] in ("-h", "--help"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    spec_dir, name = Path(argv[0]), argv[1]
    root = Path(argv[2]) if len(argv) == 3 else Path(".")
    if not (spec_dir / "spec.md").is_file():
        print(f"retro: {spec_dir}/spec.md not found", file=sys.stderr)
        return 1
    target = spec_dir / "retro.md"
    if target.is_file():
        print(f"retro: {target} exists — reused, not rewritten")
        return 0
    try:
        target.write_text(retro(spec_dir, name, root), encoding="utf-8")
        added = roll_up(spec_dir, name, root)
    except OSError as exc:
        print(f"retro: write failed: {exc}", file=sys.stderr)
        return 1
    print(f"retro: wrote {target}; {added} decision(s) rolled up to "
          "specs/context/decisions.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
