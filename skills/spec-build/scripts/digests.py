#!/usr/bin/env python3
"""digests.py — one schema per digest grammar; a digest is never
half-parsed.

Every role's digest grammar lives here as data, quoted from the place
that defines it: the line grammars (`digest: <key value> · <key value>
· …`, keyed by lens or mode where a role carries several) and the block
grammars of the conversation-only roles. validate returns a digest's
problems; parse returns its fields, only when there are none. Strict:
every key present, in order, no unknown key, every value of its kind; a
block with a missing, unknown, or misordered top-level field is
malformed. A line value ends where the next key begins, so free text
may hold a ` · `; a typed value may not. Tolerant only of leading
markup on a line (`>`, `*`, backticks, list dashes) — review files quote
the auditor line.

Every returned digest is validated with its schema before anything is
read from it; a malformed one is a fix-and-run-again refusal, never
something to act on.

The capability handshake rides the same line (spec-design D-076). A
role opens its reply — and its digest file, above the `digest:` line —
with `tools: <the tools it actually holds>`; every grammar ignores that
line. REQUIRED_TOOLS is the least a role needs to do its job at all,
quoted from its brief: nothing else is required — a missing WebSearch
degrades research, it does not void the artifact. A report that lacks
a required tool is a failed spawn: refused, never acted on, and never a
fix round.

Usage:
  digests.py validate <role> [<variant>] [file] [--require-tools]

  file defaults to stdin. Roles, with variants where a role has
  several: developer; architect tech | plan | tasks; analyst intent |
  research | constitution; tester; auditor; panelist visionary | cynic
  | minimalist; integrator pr-text | threads; release-manager.
Exit:  0 = valid · 1 = malformed (the problems printed) · 2 = usage
       · 3 = --require-tools: the `tools:` line lacks a required tool
"""
from __future__ import annotations

import re
import sys
from collections import namedtuple
from pathlib import Path

USAGE = "Usage:" + __doc__.split("Usage:", 1)[1].split("Exit:", 1)[0].rstrip()
REQUIRE_TOOLS_FLAG = "--require-tools"

Kind = namedtuple("Kind", "expect pattern")
Field = namedtuple("Field", "name shape")
Sub = namedtuple("Sub", "name kind label")


def _kind(expect: str, pattern: str) -> Kind:
    return Kind(expect, re.compile(pattern))


def _enum(*words: str) -> Kind:
    return _kind(" | ".join(words),
                 "|".join(re.escape(word) for word in words))


TEXT = _kind("a non-empty text", r"\S.*")
INT = _kind("a count", r"\d+")
TASK = _kind("a task id (T###)", r"T\d{3}")
TASK_OR_NONE = _kind("a task id (T###) or `none`", r"T\d{3}|none")
STATUS = _kind("`implemented`, `already-satisfied` or `blocked:<why>`",
               r"implemented|already-satisfied|blocked:\s*\S.*")
DEVIATION = _kind(
    "`none`, `scope:<paths>`, `spec-defect:<why>` or `other:<summary>`",
    r"none|(?P<kind>scope|spec-defect|other):\s*\S.*")
NOTE = _kind(
    "`none` or `acceptance command red outside my files: <command> "
    "— <file>`",
    r"none|acceptance command red outside my files:\s*\S.*")
ANSWERED = _kind("`<n> answered / <n> open`",
                 r"\d+\s+answered\s*/\s*\d+\s+open")
PHASES = _kind("`<n> in <n> phases`", r"\d+\s+in\s+\d+\s+phases")
MILESTONES = _kind("`<n>: <names>`", r"\d+:\s*\S.*")
SPLIT = _kind("`<done>/<partial>/<todo>`", r"\d+\s*/\s*\d+\s*/\s*\d+")
GUARDS = _kind("`<n> / guards <n>`", r"\d+\s*/\s*guards\s+\d+")
TRIPLE = _kind("`<n> DONE / <n> PARTIAL / <n> TODO`",
               r"\d+\s+DONE\s*/\s*\d+\s+PARTIAL\s*/\s*\d+\s+TODO")
CHANGED = _kind("`<n> wording edits · facts untouched`",
                r"\d+\s+wording edits\s*·\s*facts untouched")
SUMMARY = _kind(
    "`must-fix <n> · question <n> · nit <n> · disagree <n>`",
    r"must-fix\s+\d+\s*·\s*question\s+\d+\s*·\s*nit\s+\d+\s*·\s*"
    r"disagree\s+\d+")
THREAD_HEAD = _kind(
    "`thread <id> — <must-fix|question|nit|disagree> — <path:line>`",
    r"(?P<id>\S+)\s+—\s+(?P<label>must-fix|question|nit|disagree)"
    r"\s+—\s+(?P<where>\S.*)")
TRACE = _kind(
    "`<first words> ← spec:<name> | commit:<sha> | dep:<file> | "
    "backlog:<spec> | rollout:<spec>:<label>`",
    r".+?\s+←\s+(?:spec|commit|dep|backlog|rollout):\S.*")

GRAMMARS = {
    "developer": {None: (
        ("task", TASK), ("status", STATUS), ("files", INT),
        ("commit-line", TEXT), ("deviation", DEVIATION), ("note", NOTE))},
    "auditor": {None: (
        ("BLOCK", INT), ("WARN", INT), ("NIT", INT), ("worst", TEXT))},
    "tester": {None: (
        ("TCs", INT),
        ("requirement coverage", _kind("`<n>/<total>`", r"\d+\s*/\s*\d+")),
        ("untestable", TEXT),
        ("UI tests", _enum("skill-guided", "spec flows", "none")))},
    "architect": {
        "tech": (("statuses", TRIPLE), ("approach", TEXT),
                 ("rejected", TEXT), ("blast radius", TEXT)),
        "plan": (("milestones", MILESTONES), ("parallel groups", TEXT),
                 ("serial spine", TEXT)),
        "tasks": (("tasks", PHASES), ("status split", SPLIT),
                  ("TCs owned", GUARDS), ("ungrounded", TEXT)),
    },
    "analyst": {
        "intent": (
            ("intent grounded", _kind("`<n> facts`", r"\d+\s+facts")),
            ("markers", _kind("`<n> open`", r"\d+\s+open")),
            ("session FAILs", INT), ("unknowns", INT)),
        "research": (("questions", ANSWERED), ("options", TEXT)),
        "constitution": (
            ("constitution", _kind("`<n> proposed`", r"\d+\s+proposed")),
            ("areas", TEXT), ("contradicted", TEXT), ("unknowns", INT)),
    },
}

ANGLES = {"visionary": "The Visionary", "cynic": "The Cynic",
          "minimalist": "The Minimalist"}
THREAD_SUBS = (
    Sub("why", TEXT, None), Sub("task", TASK_OR_NONE, None),
    Sub("evidence", TEXT, "must-fix"), Sub("reply", TEXT, None))


def _panel(lens: str, tail: Field | None = None) -> tuple[Field, ...]:
    return (Field("angle", ("line", _enum(ANGLES[lens]))),
            Field("pitch", ("line", TEXT)),
            Field("points", ("lines", 2, 3, False, TEXT)),
            Field("watch", ("line", TEXT)),
            *((tail,) if tail else ()))


BLOCK_GRAMMARS = {
    "panelist": {
        "visionary": _panel("visionary"),
        "cynic": _panel("cynic", Field("kill", ("line", TEXT))),
        "minimalist": _panel("minimalist", Field("proof", ("line", TEXT))),
    },
    "integrator": {
        "pr-text": (
            Field("title", ("line", TEXT)), Field("body", ("body", False)),
            Field("changed", ("line", CHANGED)),
            Field("flags", ("lines", 1, None, True, TEXT))),
        "threads": (
            Field("thread", ("group", THREAD_HEAD, THREAD_SUBS)),
            Field("summary", ("line", SUMMARY)),
            Field("injection", ("lines", 1, None, True, TEXT))),
    },
    "release-manager": {None: (
        Field("section", ("body", True)),
        Field("trace", ("lines", 1, None, False, TRACE)),
        Field("dropped", ("lines", 1, None, True, TEXT)),
        Field("watch", ("lines", 1, None, True, TEXT)))},
}

# Each requirement is the tool names that satisfy it, any one of them.
REQUIRED_TOOLS = {
    "developer": (("Write", "Edit"), ("Bash",)),
    "analyst": (("Write", "Edit"),),
    "architect": (("Write", "Edit"),),
    "tester": (("Write", "Edit"),),
    "auditor": (("Read",),),
    "panelist": (("Read",),),
    "integrator": (("Read",),),
    "release-manager": (("Read",),),
}

# A required tool is met by any name a kit def dialect maps it to
# (tools/agent-defs.py's DROID_TOOLS; ZCode's ApplyPatch) — a developer
# spawned on Droid reports Execute and Create, and is not short a tool.
TOOL_ALIASES = {
    "Write": ("Create", "ApplyPatch"),
    "Bash": ("Execute",),
}

LEAD = re.compile(r"^[ \t>*`-]+")
SEP = re.compile(r"[ \t]*\u00b7[ \t]*")
QUOTE = re.compile(r"^(?:[ \t]*>)+[ \t]?")
FENCE = re.compile(r"^`{3,}[\w+-]*$")
MARKER = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+")
SUBFIELD = re.compile(r"^[ \t]+([A-Za-z]+):(?:[ \t]+(.*))?$")


def _stripped(raw: str) -> str:
    lead = LEAD.match(raw)
    line = raw[lead.end():].rstrip() if lead else raw.rstrip()
    closing = "".join(c for c in "`*" if lead and c in lead.group(0))
    return line.rstrip(closing).rstrip() if closing else line


def digest_lines(text: str) -> list[tuple[int, str]]:
    """(offset, line) of every `digest:` line in `text`, markup
    stripped; the offset is where the line starts in `text`."""
    out = []
    offset = 0
    for raw in text.splitlines(keepends=True):
        line = _stripped(raw)
        if line.startswith("digest:"):
            out.append((offset, line))
        offset += len(raw)
    return out


TOOLS_KEY = "tools"


def _tools_names(value: str) -> list[str]:
    names = []
    for item in value.split(","):
        name = item.strip().rstrip(".,").strip().strip("`").strip()
        if name and name.casefold() not in {n.casefold() for n in names}:
            names.append(name)
    return names


def tools_lines(text: str) -> list[tuple[int, str]]:
    """(offset, line) of every `tools:` line in `text`, markup stripped
    — the capability handshake's report."""
    out = []
    offset = 0
    for raw in text.splitlines(keepends=True):
        line = _stripped(raw)
        if line[:len(TOOLS_KEY) + 1].casefold() == TOOLS_KEY + ":":
            out.append((offset, line))
        offset += len(raw)
    return out


def tools_report(text: str) -> set[str]:
    """The tools the role reports holding — the first `tools:` line's
    names, spelled as the role spelled them; empty when there is none.
    A report is the agent's claim, never a fact the kit asserts."""
    lines = tools_lines(text)
    return set(_tools_names(lines[0][1][len(TOOLS_KEY) + 1:])) if lines \
        else set()


def tools_missing(role: str, reported: set[str]) -> tuple[str, ...]:
    """The requirements of `role` the report leaves unmet, each spelled
    as its alternatives; a name matches whatever its case."""
    held = {name.casefold() for name in reported}
    missing = []
    for names in REQUIRED_TOOLS[role]:
        spelled = {n.casefold() for name in names
                   for n in (name, *TOOL_ALIASES.get(name, ()))}
        if not held & spelled:
            missing.append(" or ".join(names))
    return tuple(missing)


def tools_refusal(role: str, reported: set[str],
                  missing: tuple[str, ...]) -> str:
    """The refusal for a report that lacks a required tool: the role,
    what it reported, what was required, and the remedy."""
    wanted = ", ".join(missing)
    return (f"capability handshake failed: {role} reported tools "
            f"`{', '.join(sorted(reported)) or 'none'}` — the {role} role "
            f"requires `{wanted}` — spawn again on a type or harness "
            f"that holds `{wanted}`; a failed spawn, not a fix round")


def _value_problem(name: str, kind: Kind, value: str,
                   matched: bool = True) -> str | None:
    if not value:
        return f"`{name}` needs a value"
    return None if matched else \
        f"`{name}` expects {kind.expect}, got `{value}`"


def _at(text: str, pos: int, key: str) -> bool:
    return text.startswith(key, pos) and (
        len(text) == pos + len(key) or text[pos + len(key)] in " \t")


def _next_key(body: str, start: int, keys: list[str],
              base: int) -> tuple[int, int, int] | None:
    """(value end, key offset, grammar index) of the first separator at
    or after `start` that a key of `keys` (grammar indices from
    `base`) follows."""
    for sep in SEP.finditer(body, start):
        for offset, key in enumerate(keys):
            if _at(body, sep.end(), key):
                return sep.start(), sep.end(), base + offset
    return None


def _parse_line(grammar: tuple, line: str) -> tuple[dict, list[str]]:
    body = line[len("digest:"):].lstrip()
    keys = [key for key, _pattern in grammar]
    fields: dict = {}
    problems: list[str] = []
    index = pos = 0
    while index < len(grammar):
        key, kind = grammar[index]
        if not _at(body, pos, key):
            found = _next_key(body, pos, keys[index:], index)
            if found is None:
                problems.append(f"`{key}` missing")
                break
            _end, nxt, at = found
            if at == index:
                skipped = SEP.split(body[pos:nxt].strip(), 1)[0]
                problems.append(f"unknown segment `{skipped}` before "
                                f"`{key}`")
            else:
                problems.append(
                    f"`{key}` missing — `{keys[at]}` follows "
                    f"`{keys[index - 1] if index else 'digest:'}`")
            pos, index = nxt, at
            continue
        start = pos + len(key)
        found = _next_key(body, start, keys[index + 1:], index + 1)
        end, nxt = found[:2] if found else (len(body), len(body))
        value = body[start:end].strip()
        match = kind.pattern.fullmatch(value)
        problem = _value_problem(key, kind, value, match is not None)
        if problem:
            problems.append(problem)
        else:
            fields[key] = value
            if match and "kind" in match.groupdict():
                fields[key + "_kind"] = match["kind"]
        pos, index = nxt, index + 1
    return fields, problems


def _sequence(specs, seen: list[str], repeats=()) -> list[str]:
    """Order-and-presence problems for the field names `seen`, in the
    order met, against `specs`; a name in `repeats` may come again."""
    index = {field.name: at for at, field in enumerate(specs)}
    problems = []
    nxt = 0
    for name in seen:
        at = index[name]
        if at < nxt:
            if at == nxt - 1 and name in repeats:
                continue
            problems.append(f"`{name}` twice" if at == nxt - 1
                            else f"`{name}` out of order")
        else:
            problems += [f"missing field `{field.name}`"
                         for field in specs[nxt:at]]
            nxt = at + 1
    problems += [f"missing field `{field.name}`" for field in specs[nxt:]]
    return problems


def _lines_value(name: str, shape: tuple, items: list[str]
                 ) -> tuple[list[str] | None, list[str]]:
    """(value, problems) of a multi-line field: `none` stands alone
    where the grammar allows it; otherwise every item is checked
    against the field's kind once its list marker is off."""
    _tag, lo, hi, none_ok, kind = shape
    if none_ok and items[:1] == ["none"]:
        return ((items, []) if len(items) == 1 else
                (None, [f"`{name}` says `none` but "
                        f"{len(items) - 1} line(s) follow"]))
    if not items:
        return None, [f"`{name}` needs a value"]
    if len(items) < lo or (hi is not None and len(items) > hi):
        wanted = f"{lo}\u2013{hi}" if hi is not None else f"at least {lo}"
        return None, [f"`{name}` carries {len(items)} line(s) — "
                      f"{wanted} expected"]
    cleaned = [MARKER.sub("", item).strip() for item in items]
    problems = [p for p in (
        _value_problem(name, kind, item,
                       kind.pattern.fullmatch(item) is not None)
        for item in cleaned) if p]
    return (None, problems) if problems else (cleaned, [])


def _parse_group(name: str, shape: tuple, inline: str, lines: list[str],
                 n: int) -> tuple[dict, list[str], int]:
    """(record, problems, next line) of one repeated block: its head
    at line `n`, then its indented fields."""
    head_kind, subs = shape[1], shape[2]
    head = head_kind.pattern.fullmatch(inline)
    who = f"{name} {head['id']}" if head else f"{name} at line {n + 1}"
    label = head["label"] if head else None
    problems = [] if head else [
        f"`{name}` expects {head_kind.expect}, got `{inline}`"]
    record: dict = {}
    seen: list[str] = []
    n += 1
    while n < len(lines) and lines[n][:1].isspace() and lines[n].strip():
        raw = lines[n]
        found = SUBFIELD.match(raw)
        sub = next((s for s in subs if found and found.group(1) == s.name),
                   None)
        if sub is None:
            problems.append(f"line {n + 1}: not a field of `{who}` — "
                            f"`{raw.strip()}`")
        elif sub.label and sub.label != label:
            problems.append(f"`{who}`: `{sub.name}:` is {sub.label} only")
        else:
            seen.append(sub.name)
            value = (found.group(2) or "").strip()
            problem = _value_problem(
                sub.name, sub.kind, value,
                sub.kind.pattern.fullmatch(value) is not None)
            if problem:
                problems.append(f"`{who}`: {problem}")
            else:
                record[sub.name] = value
        n += 1
    wanted = [s for s in subs if not s.label or s.label == label]
    problems += [f"`{who}`: {p}" for p in _sequence(wanted, seen)]
    if head:
        record.update(id=head["id"], label=label, where=head["where"])
    return record, problems, n


def _parse_block(fields: tuple, heads: tuple, text: str) -> tuple[dict, list[str]]:
    lines = [QUOTE.sub("", raw) for raw in text.splitlines()]
    by_name = {field.name: field for field in fields}

    def head_name(n: int) -> str | None:
        line = lines[n]
        if line[:1].isspace():
            return None
        return next((name for name, sep in heads
                     if line.startswith(name + sep)), None)

    values: dict = {}
    seen: list[str] = []
    problems: list[str] = []
    n = 0
    while n < len(lines):
        line = lines[n]
        skipped = (not line.strip() or FENCE.match(line.strip())
                   or bool(tools_lines(line)))
        field = by_name.get(head_name(n)) if not skipped else None
        if field is None:
            if not skipped:
                problems.append(f"line {n + 1}: not a field of the "
                                f"digest — `{line.strip()}`")
            n += 1
            continue
        seen.append(field.name)
        name, shape = field.name, field.shape
        inline = line[len(name) + 1:].strip()
        if shape[0] == "line":
            problem = _value_problem(
                name, shape[1], inline,
                shape[1].pattern.fullmatch(inline) is not None)
            if problem:
                problems.append(problem)
            else:
                values[name] = inline
            n += 1
        elif shape[0] == "lines":
            items = [inline] if inline else []
            n += 1
            while n < len(lines) and lines[n].strip() \
                    and not FENCE.match(lines[n].strip()) \
                    and head_name(n) is None:
                items.append(lines[n])
                n += 1
            values[name], trouble = _lines_value(name, shape, items)
            problems += trouble
        elif shape[0] == "body":
            body = [inline] if inline else []
            n += 1
            while n < len(lines) and head_name(n) is None:
                body.append(lines[n])
                n += 1
            while body and (not body[-1].strip()
                            or FENCE.match(body[-1].strip())):
                body.pop()
            opening = next((raw for raw in body if raw.strip()), "")
            if not opening:
                problems.append(f"`{name}` is empty")
            elif shape[1] and not opening.lstrip().startswith("#"):
                problems.append(f"`{name}` must open with the section's "
                                f"heading — got `{opening.strip()}`")
            else:
                values[name] = "\n".join(body)
        else:
            record, trouble, n = _parse_group(name, shape, inline, lines, n)
            problems += trouble
            values.setdefault(name, []).append(record)
    problems += _sequence(fields, seen, repeats={
        f.name for f in fields if f.shape[0] == "group"})
    return values, problems


def _variants(schemas: dict, variant: str | None) -> list:
    return list(schemas) if variant is None else [variant]


def _label(role: str, variant: str | None) -> str:
    return f"{role} {variant}" if variant else role


def _prefixed(schemas: dict, variant, problem: str) -> str:
    return f"{variant}: {problem}" if len(schemas) > 1 else problem


def _check_line(role: str, schemas: dict, variant: str | None,
                text: str) -> tuple[dict | None, list[str]]:
    lines = digest_lines(text)
    if not lines:
        return None, ["no `digest:` line"]
    wanted = _variants(schemas, variant)
    hits: dict = {}
    order: list = []
    problems: list[str] = []
    for _offset, line in lines:
        attempts = [(name, *_parse_line(schemas[name], line))
                    for name in schemas]
        made = next((a for a in attempts if not a[2]), None)
        if made is None:
            shown = attempts if variant is None else [
                a for a in attempts if a[0] == variant]
            name, _fields, trouble = min(shown, key=lambda a: len(a[2]))
            problems += [_prefixed(schemas, name, p) for p in trouble]
        elif made[0] in wanted:
            hits.setdefault(made[0], []).append(made[1])
            order.append(made[0])
    for name, found in hits.items():
        if len(found) > 1:
            problems.append(f"{len(found)} `digest:` lines match "
                            f"{_label(role, name)} — one expected")
    if variant is not None and not hits and not problems:
        problems.append(f"no `digest:` line for {role} {variant}")
    if problems:
        return None, problems
    return {**hits[order[0]][0], "variant": order[0]}, []


def _check_block(role: str, schemas: dict, variant: str | None,
                 text: str) -> tuple[dict | None, list[str]]:
    heads = tuple(sorted({(field.name, " " if field.shape[0] == "group"
                          else ":")
                          for fields in schemas.values()
                          for field in fields}))
    attempts = [(name, *_parse_block(schemas[name], heads, text))
                for name in _variants(schemas, variant)]
    made = next((a for a in attempts if not a[2]), None)
    if made:
        return {**made[1], "variant": made[0]}, []
    name, _values, problems = min(attempts, key=lambda a: (len(a[2]),
                                                           -len(a[1])))
    return None, [_prefixed(schemas, name, p) for p in problems]


def validate(role: str, variant: str | None = None,
             text: str = "") -> list[str]:
    """A digest's problems against its role's schema — empty means
    valid. `variant` names the lens or mode; omitted, each of the
    role's is accepted."""
    return _check(role, variant, text)[1]


def parse(role: str, variant: str | None = None,
          text: str = "") -> dict | None:
    """A valid digest's fields — each value verbatim, `variant` naming
    the lens or mode it matched — or None; never a partial one."""
    return _check(role, variant, text)[0]


def _check(role: str, variant: str | None, text: str) -> tuple:
    for grammars, check in ((GRAMMARS, _check_line),
                            (BLOCK_GRAMMARS, _check_block)):
        if role in grammars:
            if variant is not None and variant not in grammars[role]:
                raise KeyError(variant)
            return check(role, grammars[role], variant, text)
    raise KeyError(f"no digest schema for role {role!r}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    schemas_all = {**GRAMMARS, **BLOCK_GRAMMARS}
    require_tools = REQUIRE_TOOLS_FLAG in argv[2:]
    argv = argv[:2] + [arg for arg in argv[2:] if arg != REQUIRE_TOOLS_FLAG]
    if len(argv) < 2 or len(argv) > 4 or argv[0] != "validate" \
            or argv[1] not in schemas_all:
        print(USAGE, file=sys.stderr)
        return 2
    role, args = argv[1], argv[2:]
    schemas = schemas_all[role]
    variant = None
    if len(schemas) > 1 and args and args[0] in schemas:
        variant, args = args[0], args[1:]
    if len(schemas) > 1 and variant is None and len(args) > 1:
        print(f"unknown {role} variant `{args[0]}` — variants: "
              f"{', '.join(schemas)}", file=sys.stderr)
        return 2
    if len(args) > 1:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        text = (Path(args[0]).read_text(encoding="utf-8", errors="replace")
                if args else sys.stdin.read())
    except OSError as exc:
        print(f"cannot read {args[0]}: {exc.strerror}", file=sys.stderr)
        return 2
    problems = validate(role, variant, text)
    if problems:
        print("\n".join(f"malformed: {p}" for p in problems))
        return 1
    reported = tools_report(text)
    missing = tools_missing(role, reported) if require_tools else ()
    if missing:
        print(tools_refusal(role, reported, missing))
        return 3
    matched = parse(role, variant, text) or {}
    print(f"valid: {_label(role, variant or matched.get('variant'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
