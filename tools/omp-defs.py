#!/usr/bin/env python3
"""Generate omp task-agent defs from harness-neutral agent briefs.

Shared, skill-agnostic tool: every skill under skills/<name>/agents/*.md
that carries Claude-style frontmatter (name/description/tools/model/
effort) gets an omp-frontmatter twin, derived by parsing that
frontmatter directly. No per-skill or per-role table lives in this
script — adding a second skill's roles needs no edit here, only a new
`agents/` dir under that skill following the same frontmatter shape.

omp (Oh My Pi) discovers task agents only from .omp/agents dirs — it
intentionally skips ~/.claude/agents — and its tool registry uses
lowercase names, so the Claude frontmatter cannot be copied as-is. The
brief bodies are shared verbatim with the source agents/*.md files; only
the frontmatter is regenerated here, making these derived
regenerate-only artifacts (same anti-drift shape as checklist.md),
never hand-edited. Role files named with a leading underscore (e.g.
_shared-protocol.md) are shared prose, not roles, and are skipped.

Frontmatter derivation (from each source file's own Claude-style block):
- name/description: copied as-is (description folded to one line —
  safest across frontmatter parsers).
- tools: parsed from the source `tools:` comma list, mapped
  Read/Grep/Glob/Bash/Write/Edit -> lowercase, WebSearch -> web_search;
  Skill/WebFetch/NotebookEdit have no omp tool and are dropped (skills
  load via read skill://…, URLs via read, notebooks have no omp editor).
- model: `model: inherit` (or absent) => omitted (omp inherits the
  parent session's model, matching Claude's `model: inherit`
  semantics). Any other explicit model name (e.g. `model: sonnet`) is
  the source brief's own signal that this role is a deliberate
  cost-downgrade from the flagship default — ported to omp's built-in
  `@smol` role alias (models.md "Role aliases and settings"), the one
  documented cheap/fast tier every install gets with zero config.
  D-012 made this data-driven and D-016 extended the tiered set: the
  four source briefs whose `model:` isn't `inherit` are spec-surveyor,
  spec-researcher, spec-task-breaker, and spec-implementer — a new
  skill's own tiering choices carry over the same way, with no edit to
  this file. `@`-prefixed values must be quoted in YAML.
- effort: `effort: low` -> `thinking-level: low`; absent -> omitted.

Stale-output scoping: regenerating one skill's defs must never delete
another skill's files in a shared --out dir (~/.omp/agent/agents is
exactly that — omp agent unpacks and hand-added defs share it with every
synced skill). Ownership is proven, not guessed: each skill writes a
per-skill manifest (.spec-dev-kit-omp-defs-<skill>, name -> sha256 of
what it generated) next to its output, and stale removal deletes only
manifest-listed files whose content still matches that hash. A foreign
file — even one named like this skill's roles — is never touched, and a
generated file edited since generation is kept with a loud note. A
missing manifest (first run into a fresh root) skips stale removal
entirely: nothing is deleted that this tool cannot prove it made.

The same manifest gates writes, through the shared ownership planner
(tools/ownership.py): a role destination is replaced only when its
current hash is recorded there, and output is staged before the first
write, each file landing via a destination-local temp replaced
atomically. A foreign file at a role name — byte-different or even
byte-identical, with or without a manifest — is refused with a nonzero
exit and nothing written: never clobbered, never silently adopted.

Run by tools/sync.sh; standalone:

    tools/omp-defs.py --skill-dir skills/spec-to-prod --out ~/.omp/agent/agents
"""
import hashlib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ownership

TOOL_MAP = {
    "read": "read",
    "grep": "grep",
    "glob": "glob",
    "bash": "bash",
    "write": "write",
    "edit": "edit",
    "websearch": "web_search",
}

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def parse(source: Path):
    """Return (name, one-line description, {model,tools,effort} -> raw
    value, body) from a Claude-style frontmatter block."""
    text = source.read_text()
    m = FM.match(text)
    if not m:
        sys.exit(f"{source}: no frontmatter")
    name = None
    desc = None
    folded = False
    fields = {}
    for line in m.group(1).splitlines():
        top_level = bool(line) and line[0] not in (" ", "\t")
        if name is None and line.startswith("name:"):
            name = line[len("name:"):].strip()
        elif desc is None and line.startswith("description:"):
            desc = line[len("description:"):].strip()
            folded = bool(desc) and desc[0] in ">|"
            if folded:
                desc = ""
        elif folded and line[:1] in (" ", "\t") and line.strip():
            desc = f"{desc} {line.strip()}".strip()
        elif top_level:
            folded = False
            key, _, val = line.partition(":")
            if key in ("model", "tools", "effort"):
                fields[key] = val.strip()
    if not name or not desc:
        sys.exit(f"{source}: missing name/description")
    return name, " ".join(desc.split()), fields, text[m.end():]


def omp_tools(claude_tools: str) -> str:
    names = [t.strip().lower() for t in claude_tools.split(",") if t.strip()]
    return ", ".join(TOOL_MAP[n] for n in names if n in TOOL_MAP)


def render(name: str, desc: str, fields: dict, body: str) -> str:
    fm = [f"name: {name}", "description: '" + desc.replace("'", "''") + "'"]
    model = fields.get("model")
    if model and model != "inherit":
        fm.append('model: "@smol"')
    tools = fields.get("tools")
    if tools:
        mapped = omp_tools(tools)
        if mapped:
            fm.append(f"tools: {mapped}")
    if fields.get("effort") == "low":
        fm.append("thinking-level: low")
    return "---\n" + "\n".join(fm) + "\n---\n" + body


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_path_for(out: Path, skill_dir: Path) -> Path:
    """The skill's own provenance manifest inside the shared --out dir —
    a hidden, non-.md file, inert to every harness that scans the dir."""
    return out / f".spec-dev-kit-omp-defs-{skill_dir.name}"


def write_manifest(path: Path, out: Path, names: set) -> None:
    lines = sorted(f"{file_sha(out / n)} {n}" for n in names)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("\n".join(lines) + ("\n" if lines else ""))
    os.replace(tmp, path)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    skill_dir = out = None
    for i, a in enumerate(argv):
        if a == "--skill-dir" and i + 1 < len(argv):
            skill_dir = Path(argv[i + 1])
        elif a == "--out" and i + 1 < len(argv):
            out = Path(argv[i + 1])
    if skill_dir is None or out is None:
        sys.exit("usage: omp-defs.py --skill-dir <skill dir> --out <dir>")
    agents = skill_dir / "agents"
    if not agents.is_dir():
        sys.exit(f"{agents}: no agents/ dir")
    sources = sorted(p for p in agents.glob("*.md") if not p.name.startswith("_"))
    mpath = manifest_path_for(out, skill_dir)

    stage = Path(tempfile.mkdtemp(prefix="omp-defs-stage-"))
    try:
        # Full render into staging before the first destination write: a
        # bad role aborts with --out untouched.
        rendered = {}
        for source in sources:
            name, desc, fields, body = parse(source)
            rendered[source.name] = (name, render(name, desc, fields, body))
            (stage / source.name).write_text(rendered[source.name][1])

        # The per-skill manifest is the provenance ledger: a destination
        # may be replaced only when its current hash is recorded there.
        # Anything else at a role name is foreign — refused before any
        # write, never clobbered, never silently adopted.
        try:
            prev = ownership.read_ledger(mpath)
            planned, refused = [], []
            for fname in sorted(rendered):
                d = ownership.plan_file(stage / fname, out / fname,
                                        name=fname, ledger_file=mpath)
                (refused if d.kind == ownership.REFUSE else planned).append(
                    (d, fname))
        except (ValueError, OSError) as e:
            print(f"ERROR {e}", file=sys.stderr)
            return 2
        if refused:
            for _, fname in refused:
                print(f"REFUSE {out / fname} — foreign file (differs from "
                      f"generated, not a prior deploy); resolve manually")
            return 1

        out.mkdir(parents=True, exist_ok=True)
        for d, fname in planned:
            if d.kind == ownership.UNCHANGED:
                continue
            tmp = out / f".{fname}.tmp"
            tmp.write_text(rendered[fname][1])
            tmp.replace(out / fname)
            print(f"omp def {rendered[fname][0]}")

        keep = set(rendered)
        for name in sorted(prev.keys() - keep):
            stale = out / name
            if not stale.is_file():
                continue
            if file_sha(stale) != prev[name]:
                print(f"omp def kept {name} — changed since generation; "
                      f"remove manually if stale")
                continue
            stale.unlink()
            print(f"omp def removed {name}")
        if not prev and keep:
            print(f"omp def stale-check skipped — no provenance manifest in "
                  f"{out} (first run establishes it; delete renamed roles' "
                  f"old files manually this once)")
        write_manifest(mpath, out, keep)
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
