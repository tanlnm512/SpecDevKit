#!/usr/bin/env python3
"""contract.py — the spec workflow graph's single declarative source.

One table owns every node's identity, readiness, done-signal, and
spawn wiring. `graph.py` imports its READY_WHEN/DONE_WHEN from here
(the behavior), and `--render skill-table` regenerates the node table
in SKILL.md (the documentation) — never hand-edit the generated block;
edit this file and regenerate (`tools/drift-check.py` pins the pair,
the same way it pins diagrams).

Tier rows note where `**Tier**: tiny` SKIPPEDs a node.
"""
from __future__ import annotations

import sys
from pathlib import Path

# (node, kind, ready-when, done-when) — kind: entry | loop | gate |
# agent | mechanical | human | terminal. The ready/done strings are
# graph.py's vocabulary verbatim (it imports them below).
NODE_TABLE = [
    ("spec", "entry",
     "always (entry node)",
     "spec.md exists, non-empty, no open NEEDS CLARIFICATION markers"),
    ("clarify", "loop",
     "open NEEDS CLARIFICATION markers exist in spec.md",
     "markers resolved (removed/answered in spec.md)"),
    ("research-gate", "gate",
     "spec.md done",
     "research.md exists (real content → ran, or the skip marker → skipped)"),
    ("research", "agent",
     "the research gate is resolved `run`",
     "research.md exists, non-marker, non-empty"),
    ("intent", "agent",
     "intent.md present and unfilled, or `check.py --intent-only` fails "
     "(absent → SKIPPED: legacy path)",
     "intent.md filled AND `check.py <spec-dir> --intent-only` exits 0"),
    ("survey", "agent",
     "spec.md done",
     "survey.md filled AND `check.py <spec-dir> --survey-only` exits 0"),
    ("plan", "agent",
     "spec + survey done",
     "plan.md exists, non-empty, filled"),
    ("tech", "agent",
     "spec + survey done AND research resolved (either form)",
     "tech-spec.md exists, non-empty, filled"),
    ("qa", "agent",
     "spec + survey done (never reads plan/tech — parallel-safe)",
     "test.md exists, non-empty, filled"),
    ("tasks", "agent",
     "plan + tech + survey done",
     "task.md exists, non-empty, filled"),
    ("verify", "mechanical",
     "plan, tech, qa, tasks, survey all done",
     "`check.py <spec-dir>` exits 0"),
    ("approve", "human",
     "verify done (HUMAN gate)",
     "spec.md Status: approved (or later)"),
    ("execute", "mechanical",
     "approved",
     "every task entry implemented, ticked [x], or struck ~~"),
    ("tick-commit", "human",
     "execute done (HUMAN gate: the tick, then the delivery)",
     "durable task-tick evidence (every task ticked/struck, every tick "
     "with its proof note) plus the delivery record — `Delivered: commit "
     "@ <sha>` in task.md, or the explicit non-git skip"),
    ("archive", "terminal",
     "tick-commit done AND spec Status: done",
     "dir moved to specs/archive/<date>-<name>/, INDEX repointed"),
]

# Nodes `**Tier**: tiny` SKIPPEDs — the one-file contract has no
# authoring docs to wait on.
TINY_SKIPPED = ("survey", "plan", "tech", "qa", "tasks")

READY_WHEN = {n: r for n, _, r, _ in NODE_TABLE}
DONE_WHEN = {n: d for n, _, _, d in NODE_TABLE}

BEGIN = "<!-- BEGIN generated: node-table (scripts/contract.py --render" \
        " skill-table) -->"
END = "<!-- END generated: node-table -->"


def render_skill_table() -> str:
    """The SKILL.md node-table block, beginning and ending sentinels
    included — drift-check byte-compares this against the committed
    file."""
    rows = ["| Node | Kind | Ready when | Done when |",
            "|------|------|------------|-----------|"]
    for node, kind, ready, done in NODE_TABLE:
        if node in TINY_SKIPPED:
            rows.append(f"| `{node}` | {kind} | {ready} — *SKIPPED at "
                        f"Tier: tiny (D-037)* | {done} — *not required at "
                        "Tier: tiny* |")
        else:
            rows.append(f"| `{node}` | {kind} | {ready} | {done} |")
    return "\n".join([BEGIN] + rows + [END])


SPAWN_BEGIN = "<!-- BEGIN generated: spawn-table (scripts/contract.py " \
              "--render spawn-table) -->"
SPAWN_END = "<!-- END generated: spawn-table -->"

REVIEWER_MODES = {"approve": "contract", "tick-commit": "implementation-diff"}


def render_spawn_table() -> str:
    """The SKILL.md spawn-table block: which brief and lens each node's
    payload carries, and which span prepares it — read from graph.py's
    AGENT_BRIEFS and SPAN_AGENT_NODES so the docs cannot drift."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import graph
    rows = ["| Node | Brief | Lens / mode | Span |",
            "|------|-------|-------------|------|"]
    for node, _, _, _ in NODE_TABLE:
        spans = [sp for sp, nodes in graph.SPAN_AGENT_NODES.items()
                 if node in nodes]
        if not spans:
            continue
        if node in graph.AGENT_BRIEFS:
            _, brief, lens = graph.AGENT_BRIEFS[node]
        else:
            brief, lens = "reviewer.md", REVIEWER_MODES[node]
        rows.append(f"| `{node}` | `{brief}` | {lens} | "
                    f"{', '.join(spans)} |")
    return "\n".join([SPAWN_BEGIN] + rows + [SPAWN_END])


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--render", "skill-table"]:
        print(render_skill_table())
        return 0
    if argv == ["--render", "spawn-table"]:
        print(render_spawn_table())
        return 0
    print("usage: contract.py --render skill-table|spawn-table",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
