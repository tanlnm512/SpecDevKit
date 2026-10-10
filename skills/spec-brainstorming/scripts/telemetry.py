#!/usr/bin/env python3
"""telemetry.py — local, append-only run telemetry for a kit skill.

Records what the skill's mechanical chokepoints already compute —
wave shapes, gate pauses, check outcomes, review findings — as one
JSONL line per event under ~/.spec-dev-kit/telemetry/<skill>.jsonl,
so self-improvement decisions (ADR recalibrations, eval verdicts)
rest on a standing evidence stream instead of hand-recalled runs.

Contract (kit constitution):
- LOCAL ONLY. No network, no contents: payloads carry counts, node
  names, exit codes and paths — never user prose, code, or secrets.
- NOT STATUS (C-01): nothing under specs/<name>/ reads this file;
  check.py/graph.py never consume it. Humans and summary only.
- stdlib-only (C-06), harness-neutral (C-03), fire-and-forget: a
  telemetry failure must never break the host script.
- KIT_TELEMETRY=off disables recording entirely;
  KIT_TELEMETRY_DIR relocates the store (tests).

CLI:
  telemetry.py record <skill> <event> [json-payload]
  telemetry.py summary <skill> [--since ISO8601]
  telemetry.py path <skill>

API (from sibling scripts, same sys.path trick as specstate):
  from telemetry import record, summary
  record("spec-to-prod", "wave", wave=2, roles=["survey"])
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from pathlib import Path

SCHEMA = 1


def _store_dir() -> Path:
    return Path(os.environ.get(
        "KIT_TELEMETRY_DIR",
        str(Path.home() / ".spec-dev-kit" / "telemetry")))


def store_path(skill: str) -> Path:
    return _store_dir() / f"{skill}.jsonl"


def enabled() -> bool:
    return os.environ.get("KIT_TELEMETRY", "").lower() not in (
        "off", "0", "no", "false")


def record(skill: str, event: str, **payload) -> None:
    """Append one event; swallow every error (fire-and-forget)."""
    try:
        if not enabled():
            return
        line = {
            "schema": SCHEMA,
            "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(
                timespec="seconds"),
            "skill": skill,
            "event": event,
            "payload": payload,
        }
        p = store_path(skill)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:  # never break the host script
        pass


def _pct(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    i = min(len(sorted_vals) - 1, max(0, round(q * (len(sorted_vals) - 1))))
    return sorted_vals[i]


def summary(skill: str, since: str | None = None) -> str:
    """Markdown digest: per-event counts plus mean/p90 for numeric
    payload keys. Reads only; never writes."""
    p = store_path(skill)
    if not p.exists():
        return f"no telemetry recorded for {skill} ({p})"
    since_ts = None
    if since:
        try:
            since_ts = _dt.datetime.fromisoformat(since)
        except ValueError:
            return f"bad --since: {since!r} (ISO8601 expected)"
    events: dict[str, int] = {}
    nums: dict[tuple[str, str], list[float]] = {}
    last_ts = ""
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        ts = str(row.get("ts", ""))
        if since_ts is not None and ts and ts < since.isoformat():
            continue
        event = str(row.get("event", "?"))
        events[event] = events.get(event, 0) + 1
        last_ts = max(last_ts, ts)
        payload = row.get("payload")
        if isinstance(payload, dict):
            for key, val in payload.items():
                if isinstance(val, (int, float)) and not isinstance(
                        val, bool):
                    nums.setdefault((event, key), []).append(float(val))
    out = [f"# telemetry — {skill}",
           f"events: {sum(events.values())} · last: {last_ts or 'n/a'}"]
    for event in sorted(events):
        out.append(f"- **{event}**: {events[event]}")
        for (ev, key), vals in sorted(nums.items()):
            if ev != event:
                continue
            vals.sort()
            out.append(
                f"  - {key}: mean {sum(vals) / len(vals):.1f} · "
                f"p90 {_pct(vals, 0.9):.1f} · max {vals[-1]:.1f}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        print("usage: telemetry.py record <skill> <event> [json] · "
              "summary <skill> [--since ISO] · path <skill>",
              file=sys.stderr)
        return 2
    cmd, skill = argv[0], argv[1]
    if cmd == "record":
        if len(argv) < 3:
            print("record needs an event", file=sys.stderr)
            return 2
        try:
            payload = json.loads(argv[3]) if len(argv) > 3 else {}
        except ValueError as e:
            print(f"bad json payload: {e}", file=sys.stderr)
            return 2
        if not isinstance(payload, dict):
            print("payload must be a json object", file=sys.stderr)
            return 2
        record(skill, argv[2], **payload)
        return 0
    if cmd == "summary":
        since = None
        rest = argv[2:]
        if "--since" in rest:
            i = rest.index("--since")
            if i + 1 >= len(rest):
                print("--since needs a value", file=sys.stderr)
                return 2
            since = rest[i + 1]
        print(summary(skill, since))
        return 0
    if cmd == "path":
        print(store_path(skill))
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
