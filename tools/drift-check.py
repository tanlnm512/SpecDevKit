#!/usr/bin/env python3
"""Release validation for generated surfaces: every committed artifact a
tool regenerates must match a fresh regeneration, and every derived
surface must agree with its canonical source. One command, one verdict —
exit 0 releases; exit 1 names what drifted and what owns it:

  workflows   skills/spec-to-prod/workflows/*        vs the dialect
                                                     templates in
                                                     tools/workflow-defs.py
                                                     (--check)
  manifests   .claude-plugin/marketplace.json and    vs the regeneration
              skills/*/.claude-plugin/plugin.json    from SKILL.md
                                                     frontmatter + VERSION
                                                     (tools/plugin-manifest.py
                                                     --check)
  diagrams    diagrams/spec-to-prod-workflow.mmd     vs the workflow graph
                                                     contract in
                                                     scripts/graph.py
                                                     (NODES and the edge
                                                     tables), and the HTML
                                                     renders' coverage of
                                                     every model node
  examples    examples/mini-spec — the tests'        must still pass
              green fixture                          scripts/check.py

Exit: 0 every surface matches its canonical source · 1 drift · 2 usage
error.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
SKILL = PKG_ROOT / "skills" / "spec-to-prod"
MODEL = SKILL / "diagrams" / "spec-to-prod-workflow.mmd"
DIAGRAMS_DIR = SKILL / "diagrams"
FIXTURE = SKILL / "examples" / "mini-spec" / "specs" / "mini-spec"

NODE_DEF = re.compile(
    r'^\s*([A-Za-z0-9_]+)\s*(?:\[\[|\[|\{\{)"(.*)"(?:\]\]|\]|\}\})\s*$')
SOLID_EDGE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*-->\s*([A-Za-z0-9_]+)\s*$')
DOTTED_EDGE = re.compile(
    r'^\s*([A-Za-z0-9_]+)\s*-\.\->\s*\|([^|]*)\|\s*([A-Za-z0-9_]+)\s*$')


def run_tool(*argv: Path | str) -> int:
    """Run one checker CLI from the repo root; its own output is the
    report — fail-slower streaming, never a swallowed capture."""
    cmd = [sys.executable] + [str(a) for a in argv]
    return subprocess.run(cmd, cwd=PKG_ROOT).returncode


def load_graph_contract():
    """scripts/graph.py by path — its NODES/edge tables are the canonical
    workflow model the committed diagram documents."""
    spec = importlib.util.spec_from_file_location(
        "s2p_graph_contract", SKILL / "scripts" / "graph.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_model(text: str) -> tuple[dict[str, str],
                                    set[tuple[str, str]],
                                    set[tuple[str, str]]]:
    """The diagram's node display names (mermaid id -> first label line)
    and its solid/dotted edges, endpoints resolved to display names."""
    names: dict[str, str] = {}
    solid: set[tuple[str, str]] = set()
    dotted: set[tuple[str, str]] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("%%", "flowchart", "subgraph")):
            continue
        m = NODE_DEF.match(line)
        if m:
            names.setdefault(m.group(1), m.group(2).split("<br/>")[0].strip())
            continue
        m = SOLID_EDGE.match(line)
        if m:
            solid.add((m.group(1), m.group(2)))
            continue
        m = DOTTED_EDGE.match(line)
        if m:
            dotted.add((m.group(1), m.group(3)))
    return (names,
            {(names[a], names[b]) for a, b in solid},
            {(names[a], names[b]) for a, b in dotted})


def _diff(canonical: set, drawn: set) -> str:
    missing, extra = sorted(canonical - drawn), sorted(drawn - canonical)
    return f"missing {missing}, unknown {extra}"


def diagram_problems(g) -> list[str]:
    """Every way the committed diagram disagrees with graph.py's graph
    contract, as complete one-line findings naming the canonical table."""
    bad: list[str] = []
    names, solid, dotted = parse_model(MODEL.read_text(encoding="utf-8"))

    canonical_nodes = set(g.NODES)
    model_nodes = set(names.values())
    if model_nodes != canonical_nodes:
        bad.append("diagrams/spec-to-prod-workflow.mmd — node set differs "
                   f"from scripts/graph.py NODES: {_diff(canonical_nodes, model_nodes)}")

    canonical_solid = {tuple(e) for e in g.DATA_EDGES}
    if solid != canonical_solid:
        bad.append("diagrams/spec-to-prod-workflow.mmd — solid edges differ "
                   f"from scripts/graph.py DATA_EDGES: {_diff(canonical_solid, solid)}")

    conditional = {tuple(e) for e in g.CONDITIONAL_EDGES}
    loops = {(e[0], e[1]) for e in g.LOOP_EDGES}
    for a, b in sorted(conditional):
        if (a, b) not in dotted:
            bad.append(f"diagrams/spec-to-prod-workflow.mmd — conditional "
                       f"edge {a} -.-> {b} of scripts/graph.py "
                       f"CONDITIONAL_EDGES is not drawn")
    for a, b in sorted(loops):
        if (a, b) not in dotted and (b, a) not in dotted:
            bad.append(f"diagrams/spec-to-prod-workflow.mmd — loop edge "
                       f"{a} <-> {b} of scripts/graph.py LOOP_EDGES is not "
                       f"drawn")
    for a, b in sorted(dotted):
        if (a, b) in conditional or any({a, b} == {x, y} for x, y in loops):
            continue
        bad.append(f"diagrams/spec-to-prod-workflow.mmd — dotted edge "
                   f"{a} -.-> {b} is in no scripts/graph.py "
                   f"CONDITIONAL_EDGES/LOOP_EDGES table")

    renders = sorted(DIAGRAMS_DIR.glob("*.html"))
    if not renders:
        bad.append(f"diagrams/ — no HTML render of the model exists in "
                   f"{DIAGRAMS_DIR.relative_to(PKG_ROOT)}/")
    else:
        rendered = "\n".join(p.read_text(encoding="utf-8") for p in renders)
        for node in sorted(canonical_nodes):
            if node not in rendered:
                bad.append(f"diagrams/ — model node \"{node}\" appears in no "
                           f"HTML render; regenerate the renders from "
                           f"diagrams/spec-to-prod-workflow.mmd")
    return bad


def check_workflows() -> int:
    print("== workflows — canonical source: tools/workflow-defs.py")
    return run_tool(PKG_ROOT / "tools" / "workflow-defs.py", "--check")


def check_manifests() -> int:
    print("== manifests — canonical source: SKILL.md frontmatter + VERSION "
          "via tools/plugin-manifest.py")
    return run_tool(PKG_ROOT / "tools" / "plugin-manifest.py", "--check")


def check_diagrams() -> int:
    print("== diagrams — canonical source: scripts/graph.py's workflow "
          "graph (NODES, DATA_EDGES, CONDITIONAL_EDGES, LOOP_EDGES)")
    try:
        problems = diagram_problems(load_graph_contract())
    except KeyError as e:
        print(f"DRIFT diagrams/spec-to-prod-workflow.mmd — edge references "
              f"an undefined node {e}")
        return 1
    for problem in problems:
        print(f"DRIFT {problem}")
    return 1 if problems else 0


def check_examples() -> int:
    print("== examples — canonical contract: the mini-spec green fixture "
          "passes scripts/check.py")
    return run_tool(SKILL / "scripts" / "check.py", FIXTURE)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="drift-check.py",
        description="Release-validate every generated surface against its "
                    "canonical source: workflows, manifests, diagrams, "
                    "examples.")
    p.parse_args(argv)

    failed = []
    for name, check in (("workflows", check_workflows),
                        ("manifests", check_manifests),
                        ("diagrams", check_diagrams),
                        ("examples", check_examples)):
        if check():
            failed.append(name)
    if failed:
        print(f"drift check: FAILED — {', '.join(failed)} differ from their "
              f"canonical sources")
        return 1
    print("drift check: OK — workflows, manifests, diagrams, examples match "
          "their canonical sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
