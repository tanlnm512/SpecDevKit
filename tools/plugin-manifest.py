#!/usr/bin/env python3
"""Generate Claude Code / omp plugin-marketplace manifests from repo structure.

Derived, regenerate-only artifacts (same shape as tools/omp-defs.py's
output) — never hand-edited. Every field is either fixed repo metadata
(OWNER/REPO/LICENSE below) or read straight from a skill's own SKILL.md
frontmatter and VERSION file — adding a second skill needs no edit here.

Writes:
- .claude-plugin/marketplace.json (repo root) — the catalog every
  skills/<name>/ registers itself in, one plugin entry per skill. omp
  reads this same path as its Claude-Code-compatible fallback
  (docs/marketplace.md) — no separate .omp-plugin/ copy is published,
  since the content would be byte-identical.
- skills/<name>/.claude-plugin/plugin.json — one per skill, making that
  skill directory a self-contained, independently installable plugin:
  its commands/ and agents/ already live inside it (the plugin root IS
  the skill root), both at Claude Code's own default scan locations, so
  neither needs a manifest path override.

Known limitation, NOT fixed here: a skill's agents/ dir may hold shared
prose a role brief points at (spec-to-prod's own _shared-protocol.md)
that is not itself a role. Claude Code's default agents/ directory scan
loads every file in it as an agent even when frontmatter is absent or
doesn't parse (naming it after the file) — and per its own manifest
reference, listing specific files in an `agents` manifest field ADDS to
that default scan rather than replacing it ("merge behavior... no
overwriting"), so there is no manifest-level way to exclude one file from
an otherwise-wanted directory. Installing this plugin via Claude Code
will therefore show one extra, inert "spec-to-prod:_shared-protocol"
entry in the subagent list. The real fix (moving that file out of
agents/) touches every cross-reference to it across SKILL.md, the 8
briefs, and contracts/docset.md — out of scope for a packaging pass;
flagged here rather than silently worked around with a manifest field
that would not actually do anything.

Run manually after adding a skill, bumping a skill's VERSION, or changing
a SKILL.md description — not part of tools/sync.sh, since regenerating
these has nothing to do with copying files to installed dotfile roots:

    tools/plugin-manifest.py
"""
import json
import re
import sys
from pathlib import Path

OWNER = {"name": "Stanley", "email": "minhtan512@gmail.com"}
REPO = "tanlnm512/SpecDevKit"
LICENSE = "MIT"
MARKETPLACE_NAME = "spec-dev-kit"

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
ROOT = Path(__file__).resolve().parent.parent


def read_name_desc(source: Path):
    """Minimal Claude-style frontmatter reader: name + folded description
    only. SKILL.md carries no tools/model/effort fields, so this is
    deliberately not tools/omp-defs.py's parser — that one also reads
    those, unused here, and forcing one shared reader onto two unrelated
    schemas is the wrong kind of reuse."""
    text = source.read_text()
    m = FM.match(text)
    if not m:
        sys.exit(f"{source}: no frontmatter")
    name = None
    desc = None
    folded = False
    for line in m.group(1).splitlines():
        if name is None and line.startswith("name:"):
            name = line[len("name:"):].strip()
        elif desc is None and line.startswith("description:"):
            desc = line[len("description:"):].strip()
            folded = bool(desc) and desc[0] in ">|"
            if folded:
                desc = ""
        elif folded and line[:1] in (" ", "\t") and line.strip():
            desc = f"{desc} {line.strip()}".strip()
        elif line and line[0] not in (" ", "\t"):
            folded = False
    if not name or not desc:
        sys.exit(f"{source}: missing name/description")
    return name, " ".join(desc.split())


def first_sentence(desc: str) -> str:
    """First sentence of a folded frontmatter description — SKILL.md's
    own description is written for the orchestrator's own routing match
    (one long paragraph), not for a marketplace listing. A deterministic
    derivation of it, not a second hand-maintained text."""
    cut = desc.find(". ")
    return desc[:cut + 1] if cut != -1 else desc


def discover_skills():
    return sorted(
        d for d in (ROOT / "skills").glob("*")
        if (d / "SKILL.md").is_file()
    )


def plugin_json_for(skill_dir: Path, name: str, short_desc: str) -> dict:
    version_file = skill_dir / "VERSION"
    version = version_file.read_text().strip() if version_file.is_file() else "0.1.0"
    return {
        "name": name,
        "version": version,
        "description": short_desc,
        "author": dict(OWNER),
        "repository": f"https://github.com/{REPO}",
        "license": LICENSE,
    }


def main() -> int:
    skills = discover_skills()
    if not skills:
        sys.exit("no skills/*/SKILL.md found")

    marketplace_plugins = []
    for skill_dir in skills:
        name, desc = read_name_desc(skill_dir / "SKILL.md")
        short_desc = first_sentence(desc)

        plugin_dir = skill_dir / ".claude-plugin"
        plugin_dir.mkdir(exist_ok=True)
        (plugin_dir / "plugin.json").write_text(
            json.dumps(plugin_json_for(skill_dir, name, short_desc), indent=2) + "\n")
        print(f"plugin.json  skills/{name}")

        marketplace_plugins.append({
            "name": name,
            "description": short_desc,
            "author": dict(OWNER),
            "source": f"./skills/{name}",
            "license": LICENSE,
            "homepage": f"https://github.com/{REPO}/tree/main/skills/{name}",
        })

    marketplace_doc = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": MARKETPLACE_NAME,
        "owner": dict(OWNER),
        "metadata": {
            "description": "Spec-driven multi-agent development skills.",
        },
        "plugins": marketplace_plugins,
    }
    marketplace_dir = ROOT / ".claude-plugin"
    marketplace_dir.mkdir(exist_ok=True)
    (marketplace_dir / "marketplace.json").write_text(
        json.dumps(marketplace_doc, indent=2) + "\n")
    print(f"marketplace.json  {len(marketplace_plugins)} plugin(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
