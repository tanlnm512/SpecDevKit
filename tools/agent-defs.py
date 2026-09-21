#!/usr/bin/env python3
"""Generate opencode / droid / agy agent defs from harness-neutral briefs.

Shared, skill-agnostic tool (same contract as omp-defs.py): every role
under skills/<name>/agents/*.md carrying Claude-style frontmatter gets a
target-dialect twin, derived by parsing that frontmatter. No per-skill
or per-role table lives here. Derived, regenerate-only artifacts — never
hand-edited. Underscore-prefixed files (e.g. _shared-protocol.md) are
shared prose, not roles: skipped.

Targets:

- opencode  --out ~/.config/opencode/agents — the filename IS the agent
  name (@-mention / Task target). Frontmatter: description (required),
  mode: subagent, permission map derived from the source `tools:` list
  (read/edit/bash/glob/grep/webfetch/websearch allow iff the source
  lists a matching Claude tool; task always deny — "no agent spawns
  another" from _shared-protocol, made mechanical). model omitted
  (inherit): opencode wants provider-prefixed model IDs the source
  briefs don't carry. Skills reach opencode through the
  ~/.agents/skills compatibility root it already scans — only defs need
  generating.

- droid     --out ~/.factory/droids — Factory custom droids; the Task
  tool spawns them as subagent_type by `name`. Frontmatter: name
  (validated ^[a-z0-9-_]+$), description, model: inherit ALWAYS —
  pinning Factory model IDs guessed from Claude family names would risk
  a DroidValidator load error on every wrong guess; cost tiers belong
  on the Task call (complexity), not the def. Tools mapped Read/Grep/
  Glob -> same, Bash -> Execute, Write -> Create, Edit -> Edit,
  WebSearch/WebFetch -> WebSearch/FetchUrl; Skill is auto-included by
  droid, NotebookEdit has no equivalent (both dropped); a mapped set
  inside {Read, LS, Grep, Glob} collapses to the `read-only` category.
  Skills reach droid through the ~/.agents/skills personal-compatibility
  root it already scans.

- agy       --out <repo-root>/agents — Antigravity plugin personas.
  agy reads Claude-style frontmatter natively, so the def is a
  byte-verbatim copy of the brief. Unlike the other targets this output
  is COMMITTED: the repo root is the plugin that `agy plugin install`
  copies wholesale, so sync.sh regenerates it into the repo and it
  ships with the tree.

Output discipline: the complete set is rendered into a staging dir and
planned against the destination before the first write, and each file
lands via a destination-local temp replaced atomically — a bad role or
a refused destination aborts with --out untouched. A destination is
this generator's to replace only when its current hash sits in the
destination's .spec-dev-kit-deployed ledger (a prior deploy); a foreign
file at a generated name — even a byte-identical one — exits nonzero
and is never clobbered or adopted. The generator deletes nothing in
--out and merges, never prunes, ledger entries (shared roots hold other
skills' deployments): stale-role cleanup is the installer's provenance
ledger's call, never a name-pattern guess. Exception: agy output is
committed regenerate-only repo content — git is its provenance and
sync.sh byte-compares it against a fresh render — so it consults no
destination ledger.

Run by tools/sync.sh; standalone:

    tools/agent-defs.py --target opencode --skill-dir skills/spec-to-prod \
        --out ~/.config/opencode/agents
    tools/agent-defs.py --target droid    --skill-dir skills/spec-to-prod \
        --out ~/.factory/droids
    tools/agent-defs.py --target agy      --skill-dir skills/spec-to-prod \
        --out agents
"""
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ownership

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
DROID_NAME = re.compile(r"^[a-z0-9-_]+$")

DROID_TOOLS = {
    "read": "Read", "grep": "Grep", "glob": "Glob", "bash": "Execute",
    "write": "Create", "edit": "Edit", "websearch": "WebSearch",
    "webfetch": "FetchUrl",
}
DROID_READONLY = {"Read", "LS", "Grep", "Glob"}

OPENCODE_PERMS = {  # opencode permission key <- enabling Claude tools
    "read": ("read",), "edit": ("write", "edit"), "bash": ("bash",),
    "glob": ("glob",), "grep": ("grep",),
    "webfetch": ("webfetch",), "websearch": ("websearch",),
}


def parse(source: Path):
    """(name, one-line description, {model,tools,effort}, body) from a
    Claude-style frontmatter block — the same shape omp-defs.py parses."""
    text = source.read_text()
    m = FM.match(text)
    if not m:
        sys.exit(f"{source}: no frontmatter")
    name = desc = None
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


def claude_names(tools: str):
    return [t.strip().lower() for t in tools.split(",") if t.strip()]


def q(desc):
    return "'" + desc.replace("'", "''") + "'"


def render_opencode(name, desc, fields, body):
    have = set(claude_names(fields.get("tools", "")))
    lines = [f"description: {q(desc)}", "mode: subagent", "permission:"]
    for key, srcs in OPENCODE_PERMS.items():
        lines.append(f"  {key}: {'allow' if have & set(srcs) else 'deny'}")
    lines.append("  task: deny")  # no agent spawns another
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def render_droid(name, desc, fields, body):
    if not DROID_NAME.match(name):
        sys.exit(f"{name}: invalid droid name (^[a-z0-9-_]+$)")
    ids = list(dict.fromkeys(
        DROID_TOOLS[n] for n in claude_names(fields.get("tools", ""))
        if n in DROID_TOOLS))
    fm = [f"name: {name}", f"description: {q(desc)}", "model: inherit"]
    if ids:
        fm.append("tools: read-only" if set(ids) <= DROID_READONLY else
                  "tools: [" + ", ".join(f'"{i}"' for i in ids) + "]")
    return "---\n" + "\n".join(fm) + "\n---\n" + body


TARGETS = {"opencode": render_opencode, "droid": render_droid, "agy": None}


def put(stage: Path, outd: Path, name: str):
    # Temp inside the destination dir: same filesystem, so the replace
    # is atomic.
    tmp = outd / f".{name}.tmp"
    tmp.write_bytes((stage / name).read_bytes())
    tmp.replace(outd / name)


def record_ledger(outd: Path, written):
    """Merge this run's deploys into the destination ledger, atomically.
    Entries for names this run did not generate are kept: shared roots
    hold other skills' deployments, and a dropped role's entry is the
    installer's stale-cleanup evidence, not this generator's to prune."""
    ledger = outd / ownership.LEDGER_NAME
    entries = ownership.read_ledger(ledger)
    for d in written:
        entries[d.name] = d.src_sha
    tmp = outd / f"{ownership.LEDGER_NAME}.tmp"
    tmp.write_text("".join(f"{entries[n]} {n}\n" for n in sorted(entries)))
    tmp.replace(ledger)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    target = out = None
    skill = None
    it = iter(argv)
    for a in it:
        val = next(it, None)
        if a == "--target":
            target = val
        elif a == "--skill-dir":
            skill = val
        elif a == "--out":
            out = val
        else:
            sys.exit(f"unknown arg: {a}")
    if target not in TARGETS or not skill or not out:
        sys.exit("usage: agent-defs.py --target {opencode|droid|agy} "
                 "--skill-dir <dir> --out <dir>")

    src = Path(skill) / "agents"
    roles = sorted(p for p in src.glob("*.md") if not p.name.startswith("_"))
    if not roles:
        sys.exit(f"{src}: no role files")

    outd = Path(out)
    stage = Path(tempfile.mkdtemp(prefix="agent-defs-stage-"))
    try:
        # Full render into staging before the first destination write: a
        # bad role aborts with --out untouched.
        names = []
        for p in roles:
            if target == "agy":
                (stage / p.name).write_bytes(p.read_bytes())  # byte-verbatim persona
            else:
                name, desc, fields, body = parse(p)
                (stage / p.name).write_bytes(TARGETS[target](
                    name, desc, fields, body).encode())
            names.append(p.name)

        if target == "agy":
            outd.mkdir(parents=True, exist_ok=True)
            for name in names:
                put(stage, outd, name)
            print(f"{target} defs  {len(names)} roles -> {outd}")
            return 0

        # Plan every destination before the first write: only a current
        # hash that sits in the destination ledger proves a prior deploy
        # of this generator; anything else there is foreign.
        try:
            planned, refused = [], []
            for name in names:
                d = ownership.plan_file(stage / name, outd / name, name=name)
                (refused if d.kind == ownership.REFUSE else planned).append(d)
        except (ValueError, OSError) as e:
            print(f"ERROR {e}", file=sys.stderr)
            return 2
        if refused:
            for d in refused:
                print(f"REFUSE {outd / d.name} — foreign file (differs from "
                      f"generated, not a prior deploy); resolve manually")
            return 1

        outd.mkdir(parents=True, exist_ok=True)
        written = []
        for d in planned:
            if d.kind == ownership.UNCHANGED:
                continue
            put(stage, outd, d.name)
            written.append(d)
        if written:
            record_ledger(outd, written)
        print(f"{target} defs  {len(names)} roles -> {outd}")
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
