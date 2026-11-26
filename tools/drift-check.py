#!/usr/bin/env python3
"""Release validation for generated surfaces: every committed artifact a
tool regenerates must match a fresh regeneration, every derived surface
must agree with its canonical source, and every SKILL.md description
must stay inside its length budget. One command, one verdict —
exit 0 releases; exit 1 names what drifted and what owns it:

  manifests   .claude-plugin/marketplace.json and    vs the regeneration
              skills/*/.claude-plugin/plugin.json    from SKILL.md
                                                     frontmatter + VERSION
                                                     (tools/plugin-manifest.py
                                                     --check)
  kit-rules   agents/developer.md and                  vs the injection from
              agents/spec-review-fixer.md       rules/engineering-rules.md
              § Engineering rules + § Budgets        and rules/agent-limits.md
              sections                           (tools/kit-rules.py --check)
  parity      skills/*/scripts/ replica views of     vs the master closure
              the shared core                        at skills/spec-design/
                                                     scripts/ (tools/parity.py
                                                     --check)
  diagrams    diagrams/spec-workflow.mmd     vs the workflow graph
                                                     contract in
                                                     scripts/graph.py
                                                     (NODES and the edge
                                                     tables), and the HTML
                                                     renders' coverage of
                                                     every model node
  examples    skills/spec-design/examples/mini-spec —   must still pass
               the green fixture                      skills/spec-design/
                                                       scripts/check.py
  personas    agents/*.md (agy personas)              vs a fresh
                                                      regeneration from
                                                      skills/*/agents/
                                                      (tools/agent-defs.py
                                                      --target agy)
  evals       skills/*/evals/cases.md and            vs the parse +
              skills/*/evals/results/*.md          referential integrity
                                                   rules of tools/evals.py
                                                   (case grammar, Check
                                                   bullets in range, results
                                                   citing real cases)
  descriptions skills/*/SKILL.md description:       within the loader cap
              lengths, counted as tools/sync.sh     (1024 chars — FAIL
              counts them                           above it) and the
                                                     600-char budget (WARN
                                                     above it — AGENTS.md,
                                                     § Commands)

No `guards` set: the approval guard tools/hooks.py generates is
machine-installed and never committed, so there is nothing here to
compare — `tools/hooks.py --check` verifies an installed root, and
`tools/sync.sh --check` runs it.

Exit: 0 every surface matches its canonical source · 1 drift · 2 usage
error.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
SKILL = PKG_ROOT / "skills" / "spec-design"
SHAPE = SKILL
MODEL = SKILL / "diagrams" / "spec-workflow.mmd"
DIAGRAMS_DIR = SKILL / "diagrams"
FIXTURE = SHAPE / "examples" / "mini-spec" / "specs" / "mini-spec"

NODE_DEF = re.compile(
    r'^\s*([A-Za-z0-9_]+)\s*(?:\[\[|\[|\{\{)"(.*)"(?:\]\]|\]|\}\})\s*$')
SOLID_EDGE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*-->\s*([A-Za-z0-9_]+)\s*$')
DOTTED_EDGE = re.compile(
    r'^\s*([A-Za-z0-9_]+)\s*-\.\->\s*\|([^|]*)\|\s*([A-Za-z0-9_]+)\s*$')
# tools/sync.sh counts a description with this same block at install —
# the two measures must stay alike.
FOLDED_DESCRIPTION = re.compile(
    r"description: >-\n((?:  .*\n|\n)*?)metadata:")
DESCRIPTION_BUDGET = 600
DESCRIPTION_CAP = 1024


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
        bad.append("diagrams/spec-workflow.mmd — node set differs "
                   f"from scripts/graph.py NODES: {_diff(canonical_nodes, model_nodes)}")

    canonical_solid = {tuple(e) for e in g.DATA_EDGES}
    if solid != canonical_solid:
        bad.append("diagrams/spec-workflow.mmd — solid edges differ "
                   f"from scripts/graph.py DATA_EDGES: {_diff(canonical_solid, solid)}")

    conditional = {tuple(e) for e in g.CONDITIONAL_EDGES}
    loops = {(e[0], e[1]) for e in g.LOOP_EDGES}
    for a, b in sorted(conditional):
        if (a, b) not in dotted:
            bad.append(f"diagrams/spec-workflow.mmd — conditional "
                       f"edge {a} -.-> {b} of scripts/graph.py "
                       f"CONDITIONAL_EDGES is not drawn")
    for a, b in sorted(loops):
        if (a, b) not in dotted and (b, a) not in dotted:
            bad.append(f"diagrams/spec-workflow.mmd — loop edge "
                       f"{a} <-> {b} of scripts/graph.py LOOP_EDGES is not "
                       f"drawn")
    for a, b in sorted(dotted):
        if (a, b) in conditional or any({a, b} == {x, y} for x, y in loops):
            continue
        bad.append(f"diagrams/spec-workflow.mmd — dotted edge "
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
                           f"diagrams/spec-workflow.mmd")
    return bad


def check_contract() -> int:
    """The workflow node table: spec-design SKILL.md's generated block
    must match a fresh render of its scripts/contract.py."""
    print("== contract — canonical source: skills/spec-design/"
          "scripts/contract.py")
    skill = PKG_ROOT / "skills" / "spec-design"
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "s2p_contract", skill / "scripts" / "contract.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    start, end = text.find(mod.BEGIN), text.find(mod.END)
    if start < 0 or end < 0:
        print("  DRIFT: SKILL.md lost the generated node-table sentinels")
        return 1
    committed = text[start:end + len(mod.END)]
    if committed != mod.render_skill_table():
        print("  DRIFT: SKILL.md node table differs from contract.py")
        print("  regenerate: python3 skills/spec-design/scripts/"
              "contract.py --render skill-table (replace the block)")
        return 1
    s_start, s_end = text.find(mod.SPAWN_BEGIN), text.find(mod.SPAWN_END)
    if s_start < 0 or s_end < 0:
        print("  DRIFT: SKILL.md lost the generated spawn-table sentinels")
        return 1
    if (text[s_start:s_end + len(mod.SPAWN_END)]
            != mod.render_spawn_table()):
        print("  DRIFT: SKILL.md spawn table differs from graph.py")
        print("  regenerate: python3 skills/spec-design/scripts/"
              "contract.py --render spawn-table (replace the block)")
        return 1
    print("  OK  skills/spec-design/SKILL.md node table and spawn table")
    return 0


def check_manifests() -> int:
    print("== manifests — canonical source: SKILL.md frontmatter + VERSION "
          "via tools/plugin-manifest.py")
    return run_tool(PKG_ROOT / "tools" / "plugin-manifest.py", "--check")


def check_kit_rules() -> int:
    print("== kit-rules — canonical source: rules/engineering-rules.md via "
          "tools/kit-rules.py")
    return run_tool(PKG_ROOT / "tools" / "kit-rules.py", "--check")


def check_parity() -> int:
    print("== parity — canonical source: skills/spec-design/scripts/ via "
          "tools/parity.py")
    return run_tool(PKG_ROOT / "tools" / "parity.py", "--check")


def check_diagrams() -> int:
    print("== diagrams — canonical source: scripts/graph.py's workflow "
          "graph (NODES, DATA_EDGES, CONDITIONAL_EDGES, LOOP_EDGES)")
    try:
        problems = diagram_problems(load_graph_contract())
    except KeyError as e:
        print(f"DRIFT diagrams/spec-workflow.mmd — edge references "
              f"an undefined node {e}")
        return 1
    for problem in problems:
        print(f"DRIFT {problem}")
    return 1 if problems else 0


def check_examples() -> int:
    print("== examples — canonical contract: the mini-spec green fixture "
          "passes skills/spec-design/scripts/check.py")
    return run_tool(SHAPE / "scripts" / "check.py", FIXTURE)


def check_personas() -> int:
    print("== personas — canonical source: skills/*/agents/*.md via "
          "tools/agent-defs.py --target agy")
    committed = PKG_ROOT / "agents"
    problems: list[str] = []
    expected: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="personas-") as tmp:
        out = Path(tmp)
        for agents_dir in sorted(PKG_ROOT.glob("skills/*/agents")):
            r = subprocess.run(
                [sys.executable, str(PKG_ROOT / "tools" / "agent-defs.py"),
                 "--target", "agy", "--skill-dir", str(agents_dir.parent),
                 "--out", str(out)],
                cwd=PKG_ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                problems.append(f"agents/ — agent-defs.py failed for "
                                f"{agents_dir.parent.name}: {r.stderr.strip()}")
                continue
            for f in sorted(out.glob("*.md")):
                expected.add(f.name)
                dest = committed / f.name
                if not dest.is_file():
                    problems.append(f"agents/{f.name} — missing a fresh agy "
                                    f"regeneration (regenerate: bash tools/sync.sh)")
                elif dest.read_bytes() != f.read_bytes():
                    problems.append(f"agents/{f.name} — differs from a fresh "
                                    f"agy regeneration (regenerate: bash tools/sync.sh)")
    for stale in sorted(p.name for p in committed.glob("*.md")
                        if p.name not in expected):
        problems.append(f"agents/{stale} — no brief ships this persona "
                        f"anymore (delete it)")
    for problem in problems:
        print(f"DRIFT {problem}")
    return 1 if problems else 0


def check_evals() -> int:
    """The eval corpus: cases parse cleanly and every recorded result
    cites a real case — the corpus the runner, grade.py's S4, and
    RELEASE.md's live-eval gate all read."""
    print("== evals — canonical source: skills/*/evals/cases.md via "
          "tools/evals.py")
    spec = importlib.util.spec_from_file_location(
        "kit_evals", PKG_ROOT / "tools" / "evals.py")
    evals = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evals)
    cases = evals.load_cases()
    problems: list[str] = []
    by_case = {}
    for case in cases:
        by_case[case.selector] = case
        if not case.run_value:
            problems.append(f"{case.source} — {case.selector} has no "
                            f"Run: bullet (malformed, never a pass)")
        oor, dupes = evals.check_defects(case)
        if oor:
            problems.append(f"{case.source} — {case.selector} Check "
                            f"bullets name no criterion: C{oor}")
        if dupes:
            problems.append(f"{case.source} — {case.selector} duplicates "
                            f"Check bullets: C{dupes}")
    if not cases:
        problems.append("skills/*/evals/cases.md — no cases discovered")
    for rf in sorted(PKG_ROOT.glob("skills/*/evals/results/*.md")):
        rel = rf.relative_to(PKG_ROOT)
        skill = rel.parts[-4]
        text = rf.read_text(encoding="utf-8")
        caseid = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", rf.stem)
        m = re.search(r"^- selector: (\S+)$", text, re.M)
        if not m:
            problems.append(f"{rel} — no selector line (record via "
                            f"tools/evals.py validate)")
            continue
        selector = m.group(1)
        if selector != f"{skill}/{caseid}":
            problems.append(f"{rel} — selector {selector} disagrees with "
                            f"the filename ({skill}/{caseid})")
        elif selector not in by_case:
            problems.append(f"{rel} — selector {selector} names no case in "
                            f"{skill}/evals/cases.md")
        elif not re.search(r"^#+\s+Verdicts\s*$", text, re.M | re.I):
            problems.append(f"{rel} — no Verdicts section")
        else:
            n = len(by_case[selector].criteria)
            verdicts = re.split(r"^#+\s+Findings", text, maxsplit=1,
                                flags=re.M)[0]
            for cid, _, _ in evals.VERDICT_LINE.findall(verdicts):
                if int(cid) > n:
                    problems.append(f"{rel} — C{cid} names no criterion of "
                                    f"{selector} ({n} criteria)")
    for problem in problems:
        print(f"DRIFT {problem}")
    if not problems:
        print(f"  OK  {len(cases)} cases across "
              f"{len({c.skill for c in cases})} skills, "
              f"{len(list(PKG_ROOT.glob('skills/*/evals/results/*.md')))} "
              f"recorded results, all citing real cases")
    return 1 if problems else 0


def folded_description(skill_md: Path) -> str | None:
    m = FOLDED_DESCRIPTION.search(skill_md.read_text(encoding="utf-8"))
    if not m:
        return None
    lines = m.group(1).splitlines(keepends=True)
    return "".join(l[2:] if l.startswith("  ") else l for l in lines).strip()


def check_descriptions() -> int:
    print(f"== descriptions — budget {DESCRIPTION_BUDGET} chars "
          f"(AGENTS.md), loader cap {DESCRIPTION_CAP} (HARNESS-FACTS.md); "
          f"counted as tools/sync.sh counts")
    skill_mds = sorted(PKG_ROOT.glob("skills/*/SKILL.md"))
    if not skill_mds:
        print("  FAIL skills/*/SKILL.md — no skill to count")
        return 1
    failed = False
    for skill_md in skill_mds:
        name = skill_md.parent.name
        text = folded_description(skill_md)
        if text is None:
            print(f"  FAIL {name} — no folded description: >- block to "
                  f"count")
            failed = True
            continue
        count = len(text)
        if count > DESCRIPTION_CAP:
            print(f"  FAIL {name} — {count} chars, over the "
                  f"{DESCRIPTION_CAP} loader cap")
            failed = True
        elif count > DESCRIPTION_BUDGET:
            print(f"  WARN {name} — {count} chars, over the "
                  f"{DESCRIPTION_BUDGET}-char budget")
        else:
            print(f"  OK   {name} — {count} chars")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="drift-check.py",
        description="Release-validate every generated surface against its "
                    "canonical source (contract, manifests, kit-rules, "
                    "parity, diagrams, examples, personas, evals) and every "
                    "SKILL.md description against its length budget "
                    "(descriptions).")
    p.parse_args(argv)

    failed = []
    for name, check in (("contract", check_contract),
                        ("manifests", check_manifests),
                        ("kit-rules", check_kit_rules),
                        ("parity", check_parity),
                        ("diagrams", check_diagrams),
                        ("examples", check_examples),
                        ("personas", check_personas),
                        ("evals", check_evals),
                        ("descriptions", check_descriptions)):
        if check():
            failed.append(name)
    if failed:
        print(f"drift check: FAILED — {', '.join(failed)} differ from their "
              f"canonical sources or break a budget")
        return 1
    print("drift check: OK — contract, manifests, kit-rules, parity, "
          "diagrams, examples, personas, evals match their canonical "
          "sources; descriptions within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
