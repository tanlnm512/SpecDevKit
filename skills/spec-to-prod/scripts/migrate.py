#!/usr/bin/env python3
"""migrate.py — bring a version 1 active docset's task.md to the current
contract header shape: dry-run, idempotent, evidence-neutral.

The task template IS the target shape: every `**Field**:` line in the
template's preamble that the docset's task.md lacks is inserted verbatim —
pending placeholders only, so migration never fabricates mechanical-audit,
human-acknowledgement, or delivery evidence. Existing lines (filled
evidence included) are never moved, rewritten, or removed. A second apply
finds nothing missing and changes nothing.

Refused (exit 1, nothing written): a missing spec.md/task.md or template,
an unrecognizable spec.md Status, a Status other than draft/active (a done
plan is a record), and any path under specs/archive/ — archived history is
never migrated.

Usage: migrate.py <spec-dir> [--template <path>] [--dry-run]
       migrate.py -h | --help        (prints this text, exit 0)
Exit:  0 = migrated, previewed (--dry-run), or already at the template's
       contract · 1 = validation failure (nothing written) · 2 = usage error
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import specstate  # noqa: E402 - the sys.path setup above runs first
from tick import _durable_replace, _fsync_dir, _rollback  # noqa: E402

DEFAULT_TEMPLATE = Path(_SCRIPTS_DIR).parent / "templates" / "task.md"
FIELD_LINE = re.compile(r"^\*\*([^*]+)\*\*:")
MIGRATABLE_STATUS = ("draft", "active")


def body_start(lines: list[str]) -> int | None:
    """Index of the first '## ' section line — the preamble's end."""
    for i, line in enumerate(lines):
        if line.startswith("## "):
            return i
    return None


def header_fields(text: str) -> tuple[int | None, list[tuple[str, str]]]:
    """(body start or None, ordered unique `**Name**:` preamble fields)."""
    lines = text.split("\n")
    start = body_start(lines)
    if start is None:
        return None, []
    seen: set[str] = set()
    fields: list[tuple[str, str]] = []
    for line in lines[:start]:
        m = FIELD_LINE.match(line)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            fields.append((m.group(1), line))
    return start, fields


def plan_migration(task_text: str, template_text: str) -> tuple[str | None, list[str]]:
    """(problem or None, additions) — additions are the template's preamble
    field lines the task text lacks, in template order. problem names which
    text has no '## ' section ('task' or 'template')."""
    t_start, t_fields = header_fields(template_text)
    if t_start is None:
        return "template", []
    start, fields = header_fields(task_text)
    if start is None:
        return "task", []
    present = {name for name, _ in fields}
    return None, [line for name, line in t_fields if name not in present]


def insert_lines(text: str, additions: list[str]) -> str:
    """Splice additions into the preamble after its last non-blank line —
    purely additive: every original line keeps its order and bytes."""
    lines = text.split("\n")
    start = body_start(lines)
    at = (start or 0) - 1
    while at >= 0 and not lines[at].strip():
        at -= 1
    return "\n".join(lines[: at + 1] + list(additions) + lines[at + 1 :])


def verify_text(original: str, candidate: str, additions: list[str]) -> list[str]:
    """The invariants that make the splice trustworthy: the original lines
    survive in order, the line count grows by exactly the insertion count,
    every inserted line is present, and the candidate stays a recognizable
    plan. Runs identically on the prospective text (pre-write) and the
    promoted text (postcheck)."""
    problems: list[str] = []
    orig = original.split("\n")
    new = candidate.split("\n")
    if len(new) != len(orig) + len(additions):
        problems.append(
            f"line count {len(new)} != original {len(orig)} + {len(additions)} inserted")
    it = iter(new)
    for line in orig:
        for cand in it:
            if cand == line:
                break
        else:
            problems.append("an original line is missing or reordered")
            break
    for added in additions:
        if added not in new:
            problems.append(f"inserted line not found: {added[:60]}")
    if body_start(new) is None:
        problems.append("no '## ' section after insertion")
    return problems


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    spec_dir_arg = None
    template_arg = None
    dry = False
    it = iter(argv)
    for a in it:
        if a == "--template":
            template_arg = next(it, None)
            if not template_arg:
                print("--template needs a path", file=sys.stderr)
                return 2
        elif a == "--dry-run":
            dry = True
        elif spec_dir_arg is None:
            spec_dir_arg = a
        else:
            print(f"unexpected argument: {a}", file=sys.stderr)
            return 2
    if spec_dir_arg is None:
        print("usage: migrate.py <spec-dir> [--template <path>] [--dry-run]",
              file=sys.stderr)
        return 2

    def refuse(msg: str) -> int:
        print(f"refusing: {msg}", file=sys.stderr)
        return 1

    spec_dir = Path(spec_dir_arg)
    template_path = Path(template_arg) if template_arg else DEFAULT_TEMPLATE
    if not spec_dir.is_dir():
        return refuse(f"{spec_dir} is not a directory")
    if not template_path.is_file():
        return refuse(f"template not found: {template_path}")
    parts = spec_dir.resolve().parts
    if ("specs", "archive") in zip(parts, parts[1:]):
        return refuse(f"{spec_dir} is under specs/archive/ — archived history "
                      "is never migrated")
    task_path = spec_dir / "task.md"
    if not task_path.is_file():
        return refuse(f"no task.md under {spec_dir}")
    spec_path = spec_dir / "spec.md"
    if not spec_path.is_file():
        return refuse(f"no spec.md under {spec_dir} — the lifecycle state "
                      "cannot be verified")
    status = specstate.spec_status(
        spec_path.read_text(encoding="utf-8", errors="replace"))
    if status is None:
        return refuse("spec.md has no recognizable **Status**: line")
    if status not in MIGRATABLE_STATUS:
        return refuse(f"spec.md Status is {status} — only draft or active "
                      "docsets migrate; a done plan is a record")

    original = task_path.read_text(encoding="utf-8")
    template_text = template_path.read_text(encoding="utf-8")
    problem, additions = plan_migration(original, template_text)
    if problem == "task":
        return refuse("task.md has no '## ' section — not a recognizable plan")
    if problem == "template":
        return refuse("template has no '## ' section — not a recognizable "
                      "task template")

    if not additions:
        print("already migrated: task.md has every header field the template declares")
        return 0

    for line in additions:
        print(f"  + {line}")
    if dry:
        print(f"dry-run: {len(additions)} header line(s) would be inserted "
              "— nothing written")
        return 0

    prospective = insert_lines(original, additions)
    problems = verify_text(original, prospective, additions)
    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return refuse("prospective text failed verification — nothing written")

    try:
        _durable_replace(task_path, prospective)
    except OSError as exc:
        print(f"migrate aborted: write/replace failed, original preserved: {exc}",
              file=sys.stderr)
        return 1

    problems = []
    try:
        landed_bytes = task_path.read_bytes()
    except OSError as exc:
        landed_bytes = None
        problems.append(f"postcheck: replaced task.md unreadable: {exc}")
    if landed_bytes is not None:
        if landed_bytes != prospective.encode("utf-8"):
            problems.append(
                "postcheck: task.md on disk differs from the verified "
                "prospective text")
        problems += verify_text(original,
                                landed_bytes.decode("utf-8", errors="replace"),
                                additions)
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

    print(f"migrated: {len(additions)} header line(s) inserted into task.md")
    print("evidence fields stay pending until the normal lifecycle records "
          "them — nothing is inferred")
    return 0


if __name__ == "__main__":
    sys.exit(main())
