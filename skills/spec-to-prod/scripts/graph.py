#!/usr/bin/env python3
"""graph.py — the dynamic workflow engine for a spec folder under specs/<name>/.

The doc state under specs/<name>/ is the only state (ADR-002, generalized):
graph.py derives every node's mechanical signal from it via specstate.py and
prints the workflow graph's live picture. Judgment (brief quality, gate
decisions, rulings) stays with the orchestrator and the human; this script is
the mechanical truth about what is done, what is ready, and what is blocked.

The node model (names and ready/done conditions) is contractual — see
architecture.md §2.1/§2.2 and the READY_WHEN/DONE_WHEN tables below. In sum:

  spec → clarify? → research-gate? → (research) → survey → plan ∥ tech ∥ qa
       → tasks → verify → before-audit → approve(HUMAN) → execute (per-task
       frontier, fix-round loops ≤5) → closing-audit → tick-commit → archive,
  with loop edges: clarify, fix-round, re-brief, converge (survey staleness).

Modes:
  default        human-readable report: per-node state + reason, the frontier
                 wave (run it as one wave, then recompute), loop-edge status,
                 the lifecycle Status, task counts, and a git line. Git-derived
                 signals degrade loudly: `SKIPPED (not a git repo)` — never a
                 silent false result.
  --state-json   the same state as machine-readable JSON: nodes (state+reason
                 each), edges, frontier, loops, counts, git, status. The
                 authoritative oracle for tests and validators.
  --mermaid      the live state graph as mermaid: solid arrows are data edges,
                 dotted arrows are conditional/loop edges, node classes encode
                 the state (done/ready/blocked/undetermined/skipped).
  --explain NODE why that node is in its state right now — the same reason the
                 JSON carries, plus the node's ready/done conditions; for
                 execute, the per-task frontier.
  --emit-spawns  write one self-contained spawn payload per frontier agent
                 node to specs/<name>/spawns/wave-<N>/<role>.md (or
                 --wave-dir): frontmatter-stripped brief body byte-verbatim +
                 `_shared-protocol.md` verbatim (the reviewer is the exempt
                 role) + the input payload filled from doc state (spec dir,
                 FR list, task entry verbatim + TC acceptance commands,
                 research questions) + the resolved skill_dir. spawns/ is
                 derived and regenerate-only: safe to delete, never read by
                 check.py, never status.
  --run          the auto-trigger loop: compute the frontier; pause
                 `AWAITING HUMAN: <node>` at every judgment node (clarify,
                 an undetermined research-gate, before-audit, approve, the
                 closing-audit judgment, tick-commit — human gates are never
                 auto-satisfied and this loop mutates no doc state of its
                 own); run the mechanical verify node (check.py) directly;
                 emit payloads for the ready agent wave; invoke --runner per
                 payload (default `print`: echo the invocation); recompute
                 and repeat until a gate, workflow completion, --max-waves,
                 or a wave that changed nothing.

Mechanical probes: the survey node runs `check.py <spec-dir> --survey-only`,
the verify node runs `check.py <spec-dir>`, and the closing-audit node runs
`audit.py dod <spec-dir>` — each only once its inputs are in place. Human gates
(clarify, approve, an undetermined research-gate, closing-audit judgment,
tick-commit) are never auto-satisfied by this script.

Usage: graph.py <spec-dir> [--repo <path>] [--state-json] [--mermaid]
                [--explain <node>] [--wave-dir <dir>]
                [--emit-spawns]
                [--run [--runner '<template>'] [--dry-run] [--max-waves N]]
Exit:  0 = report produced (any workflow state) · 1 = unreadable spec-dir ·
       2 = usage error (unknown flag, unknown --explain node, missing args)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Shared parsers live in specstate.py beside this script; the invisible-char
# strip and the code-span/comment/placeholder regexes are check.py's canonical
# copies (one definition each — graph.py must not grow its own). The scripts
# dir goes on sys.path locally (no install step): tests load this file by path
# via importlib, which does not put scripts/ on sys.path.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from check import CODE_SPAN, HTML_COMMENT, INVISIBLE, PLACEHOLDER  # noqa: E402
import specstate  # noqa: E402

# The workflow graph's nodes, in canonical (dependency) order. Names are
# contractual: CROSS-001 compares them against SKILL.md's table.
NODES = [
    "spec", "clarify", "research-gate", "research", "survey", "plan", "tech",
    "qa", "tasks", "verify", "before-audit", "approve", "execute",
    "closing-audit", "tick-commit", "archive",
]

DOC_FILES = ["spec.md", "survey.md", "research.md", "plan.md",
             "tech-spec.md", "task.md", "test.md"]

# Fix-round cap: `(fix n/5)` — the cap lives in the task.md annotation, so a
# task at cap is surfaced for adjudication, never auto-retried past it.
FIX_CAP = 5

# Lifecycle words that mean the approval gate is behind us (approve's done
# condition is "Status: approved (or later)").
APPROVED_AND_LATER = ("approved", "active", "done")

# Data edges: node B ready ⟺ all in-neighbors done (§2.2).
DATA_EDGES = [
    ("spec", "survey"),
    ("survey", "plan"), ("survey", "tech"), ("survey", "qa"),
    ("plan", "tasks"), ("tech", "tasks"), ("survey", "tasks"),
    ("survey", "verify"), ("plan", "verify"), ("tech", "verify"),
    ("qa", "verify"), ("tasks", "verify"),
    ("verify", "before-audit"), ("before-audit", "approve"),
    ("before-audit", "execute"), ("approve", "execute"),
    ("execute", "closing-audit"), ("closing-audit", "tick-commit"),
    ("tick-commit", "archive"),
]

# Conditional edges: gated on a judgment or an either-form resolution (dotted
# in the mermaid render).
CONDITIONAL_EDGES = [
    ("spec", "research-gate"),
    ("research-gate", "research"),
    ("research-gate", "tech"),
]

# Loop edges: first-class, surfaced in the report and dotted in mermaid.
LOOP_EDGES = [
    ("clarify", "spec", "clarify loop"),
    ("execute", "execute", "fix-round cap 5"),
    ("survey", "tasks", "converge staleness"),
]

# The node/ready/done contract (architecture §2.1), kept as data so --explain
# states it exactly and CROSS-001 has one comparable surface.
READY_WHEN = {
    "spec": "always (entry node)",
    "clarify": "open NEEDS CLARIFICATION markers exist in spec.md",
    "research-gate": "spec.md done",
    "research": "the research gate is resolved `run`",
    "survey": "spec.md done",
    "plan": "spec + survey done",
    "tech": "spec + survey done AND research resolved (either form)",
    "qa": "spec + survey done (never reads plan/tech — parallel-safe)",
    "tasks": "plan + tech + survey done",
    "verify": "plan, tech, qa, tasks, survey all done",
    "before-audit": "verify done",
    "approve": "before-audit done (HUMAN gate)",
    "execute": "approved + before-audit recorded",
    "closing-audit": "execute done — every task ticked/struck (0 todo; digests are orchestrator-confirmed)",
    "tick-commit": "closing-audit done",
    "archive": "tick-commit done AND spec Status: done",
}
DONE_WHEN = {
    "spec": "spec.md exists, non-empty, no open NEEDS CLARIFICATION markers",
    "clarify": "markers resolved (removed/answered in spec.md)",
    "research-gate": "research.md exists (real content → ran, or the skip marker → skipped)",
    "research": "research.md exists, non-marker, non-empty",
    "survey": "survey.md filled AND `check.py <spec-dir> --survey-only` exits 0",
    "plan": "plan.md exists, non-empty, filled",
    "tech": "tech-spec.md exists, non-empty, filled",
    "qa": "test.md exists, non-empty, filled",
    "tasks": "task.md exists, non-empty, filled",
    "verify": "`check.py <spec-dir>` exits 0",
    "before-audit": "`Before-audit: passed @ <sha-or-dash>` recorded in task.md",
    "approve": "spec.md Status: approved (or later)",
    "execute": "every task entry ticked [x] or struck ~~",
    "closing-audit": "`audit.py dod <spec-dir>` DoD scorecard's mechanical gates pass",
    "tick-commit": "tasks ticked + burndown consistent; commit step SKIPPED-noted in non-git repos",
    "archive": "dir moved to specs/archive/<date>-<name>/, INDEX repointed",
}

# Report token per node state — the same vocabulary --state-json carries.
DONE, READY, BLOCKED, UNDETERMINED, SKIPPED = (
    "done", "READY", "blocked", "gate:undetermined", "SKIPPED")

# Frontier agent nodes → (spawn role, brief file under agents/). Payloads are
# named <role>.md (execute: one per runnable task). The reviewer is never a
# frontier node — it rides the before-audit orchestrator judgment — but the
# payload builder still knows its protocol exemption (C1).
AGENT_BRIEFS = {
    "survey": ("surveyor", "spec-surveyor.md"),
    "plan": ("planner", "spec-planner.md"),
    "tech": ("tech", "spec-tech.md"),
    "qa": ("qa", "spec-qa.md"),
    "tasks": ("task-breaker", "spec-task-breaker.md"),
    "execute": ("implementer", "spec-implementer.md"),
}

# This script IS the running skill's — its own root is the resolved skill_dir
# every payload carries (never guessed, never hardcoded in a brief).
SKILL_DIR = _SCRIPTS_DIR.parent

# Default --run runner: echo the invocation instead of executing it —
# equivalent to --dry-run with payloads emitted (architecture §4.5).
PRINT_RUNNER = "print"


def read_doc(path: Path) -> str | None:
    """The file's text with invisible/control characters stripped — the same
    normalization check.py applies at read time, so every parser sees clean
    text. None when the file does not exist (or is unreadable)."""
    try:
        return INVISIBLE.sub("", path.read_text(encoding="utf-8",
                                                errors="replace"))
    except OSError:
        return None


def is_unfilled(text: str) -> bool:
    """True while the text is still scaffold template residue — check.py's own
    bar (unfilled-placeholder shapes, HTML comments and code spans excluded,
    plus the templates' `YYYY-MM-DD` date glue). An unfilled template must
    never read as an authored, done file."""
    if "YYYY-MM-DD" in text:
        return True
    stripped = HTML_COMMENT.sub("", CODE_SPAN.sub("", text))
    return bool(PLACEHOLDER.search(stripped))


def doc_filled(text: str | None) -> bool:
    """The authored-output done predicate: exists, non-empty, not template."""
    return text is not None and bool(text.strip()) and not is_unfilled(text)


def _run_script(script: str, args: list[str], timeout: int = 300) -> int | None:
    """Run a sibling tooling script (check.py/audit.py) as the documented CLI;
    the exit code is the mechanical signal, None means it could not run."""
    cmd = [sys.executable, str(_SCRIPTS_DIR / script), *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.returncode


def run_check(spec_dir: Path, repo: Path | None, extra: list[str]) -> int | None:
    args = [str(spec_dir)]
    if repo is not None:
        args += ["--repo", str(repo)]
    return _run_script("check.py", args + extra)


def run_dod(spec_dir: Path, repo: Path | None) -> int | None:
    args = ["dod", str(spec_dir)]
    if repo is not None:
        args += ["--repo", str(repo)]
    return _run_script("audit.py", args)


def task_files(entry: specstate.TaskEntry) -> list[str]:
    """File paths the entry names (backticked tokens that look like paths) —
    the planner's parallelization map in per-task form."""
    toks = [m.group(1) for m in re.finditer(r"`([^`]+)`", entry.first_line)]
    return [t for t in toks if "/" in t or re.search(r"\.[A-Za-z0-9]{1,4}$", t)]


def task_frontier(entries: list[specstate.TaskEntry]) -> list[dict]:
    """The per-task frontier inside execute (§2.1): a task is runnable when it
    is `- [ ]`, its `(after T###)` deps are all ticked/struck, and it is not at
    the fix-round cap. At-cap tasks are surfaced for adjudication, never
    runnable; file overlaps between runnable tasks are noted for wave
    scheduling (the orchestrator picks the disjoint wave)."""
    by_id = {e.id: e for e in entries if e.id}
    # A struck entry's own id is unparseable (`- [ ] ~~T004~~ …` has no
    # leading T-id), so index the T-id its block names: a struck dep counts
    # as satisfied (§2.1) instead of deadlocking dependents as "not
    # defined". setdefault keeps a real entry's record ahead of a scan hit.
    for e in entries:
        if e.struck and e.id is None:
            m = re.search(r"\bT\d{3}\b", e.block)
            if m:
                by_id.setdefault(m.group(0), e)
    out: list[dict] = []
    for e in entries:
        files = task_files(e)
        if e.done:
            state, why = "ticked", "done — ticked with its proof note"
        elif e.struck:
            state, why = "struck", "struck (dropped) — stays visible, never runnable"
        elif e.claimed:
            state, why = "claimed", "marked (in-progress) — an implementer holds it"
        elif e.id is None:
            state, why = "blocked", "entry line has no T-### id — fix the entry"
        else:
            missing = [d for d in e.after if d not in by_id]
            unmet = [d for d in e.after if d in by_id
                     and not (by_id[d].done or by_id[d].struck)]
            if missing:
                state, why = "blocked", (
                    f"dependency not defined in task.md: {', '.join(missing)}")
            elif unmet:
                state, why = "blocked", f"waiting on {', '.join(unmet)} (unticked)"
            elif e.fix_round is not None and e.fix_round >= FIX_CAP:
                state, why = "at-fix-cap", (
                    f"fix cap reached ({e.fix_round}/{FIX_CAP}) — adjudicate "
                    "before another round (plan-suspect → re-brief tech)")
            else:
                state, why = "runnable", "deps satisfied — ready for an implementer"
        out.append({"id": e.id, "state": state, "reason": why,
                    "files": files, "note": None})

    # Wave-scheduling surface: runnable tasks naming the same files are noted
    # so the orchestrator keeps each wave's files disjoint ([P] discipline).
    runnable = [t for t in out if t["state"] == "runnable"]
    for t in runnable:
        mates = sorted({o["id"] for o in runnable
                        if o is not t and set(o["files"]) & set(t["files"])})
        if mates:
            t["note"] = (f"shares files with {', '.join(mates)} — "
                         "schedule in separate waves")
    return out


# ---------------------------------------------------------------------------
# Executor: --emit-spawns payloads and the --run auto-trigger loop
# (architecture §4.4–§4.5). Everything here is derived from doc state —
# the same state compute_state returns — so both modes always agree on
# wave numbering and payload paths, and neither ever writes doc state.
# ---------------------------------------------------------------------------

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
FR_ENTRY = re.compile(r"^-\s+\*\*FR-\d{3}\*\*", re.M)
PASS_CONDITION = re.compile(r"\*\*Pass condition\*\*:?(.*)")
QUESTION_SECTION = re.compile(
    r"^#+\s*(?:open (?:technical )?questions|research questions)\s*$",
    re.I | re.M)


def read_raw(path: Path) -> str | None:
    """The file's text verbatim (no invisible-char normalization) — payload
    ingredients must be byte-verbatim, not parser-cleaned. None on OSError."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def strip_frontmatter(text: str) -> str:
    """The brief body with its YAML frontmatter block removed — the fallback
    spawn prompt's first ingredient (SKILL.md § Spawn mechanics). Text
    without frontmatter is returned untouched."""
    m = FRONTMATTER.match(text)
    return text[m.end():] if m else text


def wave_number(state: dict) -> int:
    """The wave number for the current doc state — derived, so --emit-spawns
    and --run --dry-run always name the same spawns/wave-<N>/ directory for
    the same state (EXEC-010). Waves advance as milestone groups complete:
    analysis (survey + research), authoring (plan ∥ tech ∥ qa), the task
    list, then one per executed task batch (ticked/struck count)."""
    n = state["nodes"]
    settled = lambda name: n[name]["state"] in (DONE, SKIPPED)
    wave = 1
    if settled("survey") and settled("research"):
        wave += 1
    if all(settled(x) for x in ("plan", "tech", "qa")):
        wave += 1
    if settled("tasks"):
        wave += 1
    return wave + state["counts"]["ticked"] + state["counts"]["struck"]


def fr_entries(spec_text: str) -> list[str]:
    """The spec's FR-### entries verbatim (a line plus its wrapped
    continuation lines) — the payload's FR list."""
    lines = spec_text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if FR_ENTRY.match(lines[i]):
            block = [lines[i]]
            i += 1
            while (i < len(lines) and lines[i].strip()
                   and not FR_ENTRY.match(lines[i])
                   and not lines[i].startswith("## ")):
                block.append(lines[i])
                i += 1
            out.append("\n".join(block).rstrip())
        else:
            i += 1
    return out


def spec_section(spec_text: str, name: str) -> str | None:
    """The body of one `## <name>` section (What/Why), or None."""
    m = re.search(rf"^##\s+{name}\s*$", spec_text, re.I | re.M)
    if not m:
        return None
    body: list[str] = []
    for line in spec_text[m.end():].splitlines():
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body).strip() or None


def research_questions(spec_text: str) -> list[str]:
    """The spec's recorded research/open questions — bullet lines under an
    `Open questions` / `Research questions` heading. Empty when the spec
    records none: the researcher brief derives 3–6 from the open technical
    choices, so the payload says so instead of inventing questions."""
    m = QUESTION_SECTION.search(spec_text)
    if not m:
        return []
    out: list[str] = []
    for line in spec_text[m.end():].splitlines():
        s = line.strip()
        if s.startswith("#"):
            break
        if s.startswith("- "):
            out.append(s)
        elif out and not s:
            break
    return out


def tc_conditions(test_text: str) -> dict[str, dict]:
    """TC id → {frs, commands, note} from test.md — each TC's FR links
    (Traces-to line + coverage matrix row) and the backticked command(s) in
    its Pass condition line, extracted the same way audit.py proofs does.
    A TC with no command is a MANUAL observation, named not dropped."""
    out: dict[str, dict] = {}
    for sec in re.split(r"^#{2,3} ", test_text, flags=re.M):
        m = re.match(r"(TC-\d{3})\b", sec)
        if not m:
            continue
        chunk = ""
        pm = PASS_CONDITION.search(sec)
        if pm:
            chunk = pm.group(1)
            for cont in sec[pm.end():].splitlines():
                if cont.startswith("- ") or not cont.strip():
                    break
                chunk += " " + cont.strip()
        cmds = [c.strip() for c in re.findall(r"`([^`]+)`", chunk)]
        out[m.group(1)] = {"frs": set(re.findall(r"FR-\d{3}", sec)),
                           "commands": cmds,
                           "note": None if cmds
                           else "(observation only — MANUAL)"}
    for line in test_text.splitlines():
        rm = re.match(r"\|\s*(FR-\d{3})\s*\|", line)
        if rm:
            for tc in re.findall(r"TC-\d{3}", line):
                out.setdefault(tc, {"frs": set(), "commands": [],
                                    "note": "(observation only — MANUAL)"})
                out[tc]["frs"].add(rm.group(1))
    return out


def acceptance_for(entry_block: str, test_text: str) -> list[str]:
    """The TC pass-condition command(s) for the FRs a task entry cites — the
    implementer's acceptance list (always for code tasks). MANUAL TCs are
    named; a missing test.md says so instead of inventing a command."""
    if not test_text.strip():
        return ["(test.md not written yet — no TC pass conditions)"]
    frs = set(re.findall(r"FR-\d{3}", entry_block))
    tcs = tc_conditions(test_text)
    matched = [tc for tc in sorted(tcs) if not frs or tcs[tc]["frs"] & frs]
    lines: list[str] = []
    for tc in matched:
        info = tcs[tc]
        if info["commands"]:
            lines += [f"{tc}: `{c}`" for c in info["commands"]]
        else:
            lines.append(f"{tc}: {info['note']}")
    return lines or ["(no TC pass conditions match this task's FRs)"]


def _indent(text: str, pad: str = "   ") -> str:
    return "\n".join(pad + ln for ln in text.splitlines())


def input_payload_for(node: str, spec_dir: Path, repo: Path,
                      entry: specstate.TaskEntry | None) -> str:
    """The filled input payload (SKILL.md § Spawn mechanics step 3): the
    doc-state facts each brief's `Input payload` section asks the
    orchestrator to embed — verbatim where the brief says verbatim. Every
    payload names the spec dir and carries the FR list (EXEC-001); the
    role-specific facts come first."""
    spec_text = read_doc(spec_dir / "spec.md") or ""
    test_text = read_doc(spec_dir / "test.md") or ""
    fr_lines = [f"   {b}" for b in fr_entries(spec_text)]
    if not fr_lines:
        fr_lines = ["   (no FR-### entries in spec.md)"]
    constitution = spec_dir.parent / "CONSTITUTION.md"

    if node == "survey":
        survey_text = read_doc(spec_dir / "survey.md")
        base = (specstate.survey_baseline(survey_text)
                if survey_text else None)
        lines = [
            f"- spec_dir: {spec_dir}",
            f"- repo root: {repo}",
            "- baseline: " + (f"{base[0]} @ {base[1]}" if base
                              else "none recorded yet (first survey)"),
            "- The spec's proposed items (FR list, verbatim):",
            *fr_lines,
        ]
        return "\n".join(lines)

    if node == "research":
        what = spec_section(spec_text, "What")
        why = spec_section(spec_text, "Why")
        questions = research_questions(spec_text)
        lines = [f"- spec_dir: {spec_dir}"]
        if what:
            lines += ["- What (verbatim):", _indent(what)]
        if why:
            lines += ["- Why (verbatim):", _indent(why)]
        if questions:
            lines += ["- Research questions (recorded in spec.md):"]
            lines += [_indent(q) for q in questions]
        else:
            lines += ["- Research questions: none recorded in spec.md — "
                      "derive 3-6 from the open technical choices in the FR "
                      "list below; the orchestrator confirms them."]
        lines += ["- FR list (verbatim):", *fr_lines]
        return "\n".join(lines)

    if node == "plan":
        lines = [
            f"- spec_dir: {spec_dir} (read spec.md and survey.md yourself)",
            "- Team context: none recorded — assume solo, PR-per-milestone "
            "unless the spawn digest says otherwise",
        ]
    elif node == "tech":
        lines = [
            f"- spec_dir: {spec_dir} (read spec.md, survey.md, research.md "
            "yourself)",
            "- Architecture constraints: "
            + (f"specs/CONSTITUTION.md at {constitution}"
               if constitution.exists()
               else "none recorded (no specs/CONSTITUTION.md)"),
        ]
    elif node == "qa":
        lines = [
            f"- spec_dir: {spec_dir}",
            "- Read spec.md and survey.md ONLY — never tech-spec.md or "
            "plan.md (implementation blindness)",
        ]
    elif node == "tasks":
        lines = [f"- spec_dir: {spec_dir} (read spec.md, plan.md, "
                 "tech-spec.md, survey.md yourself)"]
    elif node == "execute" and entry is not None:
        agents_md = repo / "AGENTS.md"
        lines = [
            "- Task entry (verbatim):",
            _indent(entry.block),
            f"- spec_dir: {spec_dir}",
            "- Repo conventions: "
            + (f"see {agents_md}" if agents_md.exists()
               else "no AGENTS.md at the repo root — follow existing code "
                    "style")
            + " · CONSTITUTION: "
            + (str(constitution) if constitution.exists()
               else "not present — report its absence in your digest"),
            "- Acceptance commands (always for code tasks — run them while "
            "implementing; the closing audit re-runs them):",
        ]
        lines += [_indent(c) for c in acceptance_for(entry.block, test_text)]
        if entry.fix_round:
            note = spec_dir / "notes" / f"{entry.id or 'T???'}.md"
            lines += [f"- Fix round {entry.fix_round}: prior scratch note: "
                      f"{note if note.exists() else '(none written yet)'}"]
    else:
        lines = [f"- spec_dir: {spec_dir}"]

    lines += ["- FR list (verbatim from spec.md):", *fr_lines]
    return "\n".join(lines)


def frontier_payloads(state: dict, spec_dir: Path,
                      repo: Path) -> list[dict]:
    """One record per payload this wave writes: one per frontier agent node,
    one per runnable task for execute (named implementer-T###.md when there
    are several, implementer.md when one), plus — while the research-gate is
    undetermined — the researcher payload. That gate is an orchestrator
    judgment with no run-decision artifact in doc state, so --emit-spawns
    prepares its payload as the instrument of a `run` decision; --run still
    pauses at the gate and never spawns it."""
    items: list[dict] = []
    for node in state["frontier"]:
        if node not in AGENT_BRIEFS:
            continue
        role, brief = AGENT_BRIEFS[node]
        if node == "execute":
            entries = specstate.task_entries(
                read_doc(spec_dir / "task.md") or "")
            runnables = [t for t in state["nodes"]["execute"].get("tasks", [])
                         if t["state"] == "runnable" and t["id"]]
            multi = len(runnables) > 1
            for t in runnables:
                entry = next((e for e in entries if e.id == t["id"]), None)
                items.append({
                    "node": node, "role": role, "brief": brief,
                    "filename": (f"implementer-{t['id']}.md" if multi
                                 else "implementer.md"),
                    "entry": entry,
                })
        else:
            items.append({"node": node, "role": role, "brief": brief,
                          "filename": f"{role}.md", "entry": None})
    if state["nodes"]["research-gate"]["state"] == UNDETERMINED:
        items.append({"node": "research", "role": "researcher",
                      "brief": "spec-researcher.md",
                      "filename": "researcher.md", "entry": None})
    return items


def build_payload(item: dict, spec_dir: Path, repo: Path, wave: int) -> str | None:
    """One self-contained spawn payload: header (spec_dir / repo /
    skill_dir) + filled input payload + the frontmatter-stripped brief body
    byte-verbatim + `_shared-protocol.md` verbatim — except the reviewer,
    the one exempt role (its brief states it needs no shared protocol)."""
    brief_raw = read_raw(SKILL_DIR / "agents" / item["brief"])
    if brief_raw is None:
        return None
    protocol = read_raw(SKILL_DIR / "agents" / "_shared-protocol.md")
    parts = [
        f"# Spawn payload — {item['role']} · node {item['node']} · "
        f"wave {wave}",
        "",
        "Generated by `scripts/graph.py --emit-spawns` from doc state "
        "alone. Derived artifact: regenerate-only — safe to delete, never "
        "read by check.py, never status (contracts/docset.md).",
        "",
        f"- spec_dir: {spec_dir}",
        f"- repo: {repo}",
        f"- skill_dir: {SKILL_DIR}",
        "",
        "## Input payload (filled from doc state)",
        "",
        input_payload_for(item["node"], spec_dir, repo, item["entry"]),
        "",
        f"## Brief — agents/{item['brief']} (body; frontmatter stripped)",
        "",
        strip_frontmatter(brief_raw),
    ]
    if protocol is not None and item["role"] != "reviewer":
        parts += ["",
                  "## Shared protocol — agents/_shared-protocol.md "
                  "(verbatim)",
                  "",
                  protocol]
    return "\n".join(parts)


def write_wave_payloads(state: dict, spec_dir: Path, repo: Path,
                        wave_dir: Path | None) -> list[tuple[Path, str, str]]:
    """Write the wave's payloads; returns (path, role, node) per file."""
    wave = wave_number(state)
    target = Path(wave_dir) if wave_dir else (
        spec_dir / "spawns" / f"wave-{wave}")
    written: list[tuple[Path, str, str]] = []
    for item in frontier_payloads(state, spec_dir, repo):
        text = build_payload(item, spec_dir, repo, wave)
        if text is None:
            print(f"   payload: SKIPPED (brief not found: "
                  f"agents/{item['brief']})")
            continue
        target.mkdir(parents=True, exist_ok=True)
        path = target / item["filename"]
        path.write_text(text, encoding="utf-8")
        written.append((path, item["role"], item["node"]))
        print(f"   payload: {path} (role: {item['role']}, "
              f"node: {item['node']})")
    return written


def substitute(template: str, prompt_file: Path, role: str,
               spec_dir: Path, skill_dir: Path) -> str:
    """Placeholders substituted verbatim — no shell quoting, no residual
    braces ({prompt_file}/{role}/{spec_dir}/{skill_dir})."""
    return (template.replace("{prompt_file}", str(prompt_file))
            .replace("{role}", role)
            .replace("{spec_dir}", str(spec_dir))
            .replace("{skill_dir}", str(skill_dir)))


def find_pause(state: dict, wave_dir: str | None = None) -> tuple[str, str] | None:
    """The first judgment node --run must stop at, as (node, what is needed).
    The human gates (clarify, an undetermined research-gate, approve, the
    closing-audit judgment, tick-commit) are never auto-satisfied;
    before-audit — the orchestrator's six-gate judgment — pauses the same
    way. Order is the canonical node order; at most one applies per state."""
    n = state["nodes"]
    if n["clarify"]["state"] == READY:
        return "clarify", n["clarify"]["reason"]
    if n["research-gate"]["state"] == UNDETERMINED:
        target = (Path(wave_dir) if wave_dir
                  else Path(state["spec_dir"]) / "spawns"
                  / f"wave-{wave_number(state)}")
        return "research-gate", (n["research-gate"]["reason"]
                                 + " — if the decision is run, the prepared "
                                 "researcher payload is: "
                                 f"{target / 'researcher.md'}")
    if n["before-audit"]["state"] == READY:
        return "before-audit", ("run the six before-audit gates "
                                "(gates/before-audit.md), then record "
                                "`Before-audit: passed @ <sha-or-dash>` in "
                                "task.md")
    if n["approve"]["state"] == READY:
        return "approve", n["approve"]["reason"]
    if (n["execute"]["state"] == DONE
            and n["closing-audit"]["state"] != DONE):
        return "closing-audit", ("run the closing audit: `audit.py proofs "
                                 "<spec-dir> --run`, scope and clean, "
                                 "`audit.py dod`; rule on the findings, "
                                 "surface every D-###, and get the user's "
                                 "ack")
    if n["closing-audit"]["state"] == DONE and state["status"] != "done":
        commit_note = ("commit the plan" if state["git"]["available"]
                       else "commit SKIPPED (not a git repo)")
        return "tick-commit", ("tick every task `- [x]` with its proof "
                               "note, recompute the burndown "
                               "(`check.py --fix-burndown`), " + commit_note
                               + ", then set spec.md Status: done and "
                               "repoint INDEX.md")
    return None


def resolved_repo(spec_dir: Path, repo_override: str | None) -> Path:
    return Path(repo_override) if repo_override else spec_dir.parent.parent


def run_check_output(spec_dir: Path, repo_override: str | None) -> tuple:
    """check.py's (exit code, stdout) — the run log's verify evidence."""
    args = [str(spec_dir)]
    if repo_override is not None:
        args += ["--repo", str(repo_override)]
    try:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS_DIR / "check.py"), *args],
            capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return r.returncode, r.stdout


def log_verify(state: dict, repo_override: str | None) -> None:
    """The mechanical verify node runs inside --run — its exit (and, on a
    red check, the output tail) goes in the run log, never to a runner."""
    rc = state["nodes"]["verify"].get("check_rc")
    if rc is None:
        return
    print(f"verify: check.py {state['spec_dir']} → exit {rc}")
    if rc not in (0, None):
        _code, output = run_check_output(state["spec_dir"], repo_override)
        if output.strip():
            print("  check.py output (tail):")
            print(_indent("\n".join(output.strip().splitlines()[-12:]),
                          "    "))


def print_complete_or_held(state: dict) -> None:
    n = state["nodes"]
    if n["archive"]["state"] == READY:
        print("workflow complete — archive-ready: run `scripts/archive.sh "
              f"{Path(state['spec_dir']).name}`")
    elif all(n[x]["state"] == DONE for x in NODES):
        print("workflow complete — every node done")
    else:
        print("workflow held — no agent node is runnable; the blocked nodes:")
        for name in NODES:
            if n[name]["state"] == BLOCKED:
                print(f"  {name}: {n[name]['reason']}")


def run_loop(spec_dir: Path, repo_override: str | None, runner: str,
             dry_run: bool, max_waves: int | None,
             wave_dir: str | None = None) -> int:
    """The auto-trigger loop (architecture §4.5): pause at every judgment
    node, run the mechanical verify directly, emit payloads for the ready
    agent wave, invoke the runner per payload, recompute, repeat — until a
    gate, workflow completion, the --max-waves bound, or a wave that changed
    nothing. Payloads go to --wave-dir when given, otherwise the default
    <spec-dir>/spawns/wave-<N>/ (the same override --emit-spawns takes).
    The loop itself mutates no doc state; only the runner's own effects move
    the workflow, so human gates can never be auto-satisfied."""
    waves_done = 0
    while True:
        state = compute_state(spec_dir, repo_override)
        log_verify(state, repo_override)
        pause = find_pause(state, wave_dir)
        if pause:
            print(f"AWAITING HUMAN: {pause[0]}: {pause[1]}")
            return 0
        frontier = state["frontier"]
        if not any(node in AGENT_BRIEFS for node in frontier):
            print_complete_or_held(state)
            return 0
        wave = wave_number(state)
        print(f"== wave {wave} — frontier: {', '.join(frontier)}")
        written = write_wave_payloads(state, Path(spec_dir),
                                      resolved_repo(Path(spec_dir),
                                                    repo_override),
                                      Path(wave_dir) if wave_dir else None)
        if not written:
            print("   no runnable payloads this wave — nothing to invoke")
        for path, role, node in written:
            if runner == PRINT_RUNNER:
                print(f"   runner[print]: {role}: echo {path}  # "
                      f"node={node} spec_dir={spec_dir} "
                      f"skill_dir={SKILL_DIR}")
                continue
            invocation = substitute(runner, path, role, spec_dir, SKILL_DIR)
            if dry_run:
                print(f"   runner[dry-run]: {role}: {invocation}")
            else:
                r = subprocess.run(invocation, shell=True)
                print(f"   runner: {role}: {invocation} → exit "
                      f"{r.returncode}")
        waves_done += 1
        new_state = compute_state(spec_dir, repo_override)
        if max_waves is not None and waves_done >= max_waves:
            print(f"stopping: --max-waves {max_waves} bound reached "
                  f"({waves_done} wave(s) run)")
            return 0
        if new_state == state:
            print("no doc-state change after the wave — stopping (the "
                  "runner echoed without executing; run with --runner, or "
                  "act on the frontier, then re-run)")
            return 0


def emit_spawns(spec_dir: Path, repo_override: str | None,
                wave_dir: str | None) -> int:
    """--emit-spawns: write this wave's payloads and list them."""
    state = compute_state(spec_dir, repo_override)
    items = frontier_payloads(state, spec_dir,
                              resolved_repo(spec_dir, repo_override))
    if not items:
        print("no agent payloads to emit — the frontier holds no agent "
              f"node (frontier: {', '.join(state['frontier']) or 'empty'})")
        return 0
    target = Path(wave_dir) if wave_dir else None
    written = write_wave_payloads(state, spec_dir,
                                  resolved_repo(spec_dir, repo_override),
                                  target)
    print(f"emitted {len(written)} payload(s) for wave "
          f"{wave_number(state)} — spawns/ is derived: delete freely, "
          "check.py never reads it")
    return 0


def compute_state(spec_dir: Path, repo_override: str | None = None) -> dict:
    """Derive the full workflow-graph state from doc state alone — the same
    dict --state-json serializes. Pure reads: no doc file is ever written,
    and the subprocess probes (check.py, audit.py dod) only run once their
    node's inputs are in place."""
    spec_dir = Path(spec_dir)
    repo = Path(repo_override) if repo_override else spec_dir.parent.parent
    docs = {f: read_doc(spec_dir / f) for f in DOC_FILES}
    filled = {f: doc_filled(docs[f]) for f in DOC_FILES}

    git_ok = specstate.git_available(repo)
    head = specstate.head_sha(repo) if git_ok else None
    git_note = "" if git_ok else "SKIPPED (not a git repo)"

    spec_text = docs["spec.md"]
    status = specstate.spec_status(spec_text) if spec_text is not None else None
    markers = spec_text.count("NEEDS CLARIFICATION") if spec_text else 0
    task_text = docs["task.md"]
    entries = specstate.task_entries(task_text) if task_text else []
    ba = (specstate.before_audit_state(task_text)
          if task_text is not None else "missing")
    rstate = specstate.research_state(spec_dir / "research.md")

    nodes: dict[str, dict] = {}

    # -- spec (entry) ------------------------------------------------------
    if spec_text is None or not spec_text.strip():
        nodes["spec"] = {"state": BLOCKED, "reason":
                         "spec.md missing or empty — author the spec first"}
    elif is_unfilled(spec_text):
        nodes["spec"] = {"state": BLOCKED, "reason":
                         "spec.md is still the unfilled template — fill it "
                         "with the user"}
    elif markers:
        nodes["spec"] = {"state": BLOCKED, "reason":
                         f"{markers} open NEEDS CLARIFICATION marker(s) in "
                         "spec.md — resolve with the user, then remove them"}
    else:
        nodes["spec"] = {"state": DONE, "reason":
                         "spec.md present and filled; no open NEEDS "
                         "CLARIFICATION markers"}
    spec_done = nodes["spec"]["state"] == DONE

    # -- clarify (loop) ----------------------------------------------------
    if markers:
        nodes["clarify"] = {"state": READY, "reason":
                            f"clarify loop active: {markers} open NEEDS "
                            "CLARIFICATION marker(s) — resolve with the user"}
    else:
        nodes["clarify"] = {"state": DONE,
                            "reason": "no open NEEDS CLARIFICATION markers"}

    # -- research-gate (orchestrator judgment, never auto-decided) ---------
    if not spec_done:
        nodes["research-gate"] = {"state": BLOCKED, "reason":
                                  "waiting on: spec"}
    elif rstate == "skip":
        nodes["research-gate"] = {"state": DONE, "reason":
                                  "research.md records the skip marker — "
                                  "gate resolved: skip"}
    elif rstate == "done":
        nodes["research-gate"] = {"state": DONE, "reason":
                                  "research.md written — gate resolved: run"}
    else:
        nodes["research-gate"] = {"state": UNDETERMINED, "reason":
                                  "research.md absent or unfilled — decide: "
                                  "run the researcher, or record the skip "
                                  "marker"}
    gate = nodes["research-gate"]["state"]

    # -- research ----------------------------------------------------------
    if gate == UNDETERMINED:
        nodes["research"] = {"state": BLOCKED, "reason":
                             "research-gate undetermined — decide run or "
                             "skip first"}
    elif rstate == "skip":
        nodes["research"] = {"state": SKIPPED, "reason":
                             "gate resolved: skip — the researcher is not run"}
    elif rstate == "done":
        nodes["research"] = {"state": DONE, "reason":
                             "research.md holds real (non-marker) content"}
    else:
        nodes["research"] = {"state": BLOCKED, "reason":
                             "gate resolved run but research.md has no "
                             "content yet"}
    research_done = nodes["research"]["state"] == DONE

    # -- survey ------------------------------------------------------------
    if not spec_done:
        nodes["survey"] = {"state": BLOCKED,
                           "reason": "waiting on: spec"}
    elif docs["survey.md"] is None:
        nodes["survey"] = {"state": READY, "reason":
                           "no survey.md — the surveyor writes it from the "
                           "spec's FR list"}
    elif not filled["survey.md"]:
        nodes["survey"] = {"state": READY, "reason":
                           "survey.md is still the unfilled template — the "
                           "surveyor rewrites it from the spec's FR list"}
    else:
        rc = run_check(spec_dir, repo_override, ["--survey-only"])
        if rc == 0:
            nodes["survey"] = {"state": DONE, "reason":
                               "survey.md filled and `check.py --survey-only` "
                               "exits 0"}
        elif rc is None:
            nodes["survey"] = {"state": BLOCKED, "reason":
                               "check.py could not run — survey unverified"}
        else:
            nodes["survey"] = {"state": BLOCKED, "reason":
                               f"check.py --survey-only exits {rc} — fix the "
                               "survey evidence it names"}
    survey_done = nodes["survey"]["state"] == DONE

    def authored(node: str, filename: str, deps: list[str],
                 unmet_extra: list[str] | None = None) -> None:
        """Shared shape for the authoring nodes: blocked on unmet deps, READY
        while the output is missing/unfilled, done once it is filled."""
        unmet = [d for d in deps
                 if nodes[d]["state"] not in (DONE, SKIPPED)]
        if unmet_extra:
            unmet += unmet_extra
        if unmet:
            nodes[node] = {"state": BLOCKED,
                           "reason": f"waiting on: {'; '.join(unmet)}"}
        elif docs[filename] is None:
            nodes[node] = {"state": READY, "reason":
                           f"no {filename} — write it (see its agent brief)"}
        elif not filled[filename]:
            nodes[node] = {"state": READY, "reason":
                           f"{filename} is still the unfilled template — "
                           "rewrite it"}
        else:
            nodes[node] = {"state": DONE,
                           "reason": f"{filename} present and filled"}

    authored("plan", "plan.md", ["survey"])
    authored("tech", "tech-spec.md", ["survey"],
             None if research_done or rstate == "skip"
             else ["research (research-gate undetermined — decide run or "
                   "skip)"])
    authored("qa", "test.md", ["survey"])
    authored("tasks", "task.md", ["plan", "tech", "survey"])

    # -- verify (mechanical: runs check.py) --------------------------------
    verify_deps = [d for d in ("plan", "tech", "qa", "tasks", "survey")
                   if nodes[d]["state"] != DONE]
    if verify_deps:
        nodes["verify"] = {"state": BLOCKED,
                           "reason": f"waiting on: {', '.join(verify_deps)}"}
    else:
        rc = run_check(spec_dir, repo_override, [])
        if rc == 0:
            nodes["verify"] = {"state": DONE, "reason":
                               "check.py exits 0 — the docset is "
                               "mechanically consistent"}
        elif rc is None:
            nodes["verify"] = {"state": BLOCKED, "reason":
                               "check.py could not run — docset unverified"}
        else:
            nodes["verify"] = {"state": BLOCKED, "reason":
                               f"check.py exits {rc} — run "
                               f"`python3 scripts/check.py {spec_dir}` for "
                               "the failing checks"}
        nodes["verify"]["check_rc"] = rc
    verify_done = nodes["verify"]["state"] == DONE

    # -- before-audit ------------------------------------------------------
    if not verify_done:
        nodes["before-audit"] = {"state": BLOCKED,
                                 "reason": "waiting on: verify"}
    elif ba == "passed":
        nodes["before-audit"] = {"state": DONE, "reason":
                                 "Before-audit: passed recorded in task.md"}
    elif ba == "pending":
        nodes["before-audit"] = {"state": READY, "reason":
                                 "run the before-audit gates "
                                 "(gates/before-audit.md), then record "
                                 "`Before-audit: passed @ <sha>` (or "
                                 "`passed @ -` in a non-git repo) in task.md"}
    else:
        nodes["before-audit"] = {"state": READY, "reason":
                                 "no Before-audit line in task.md — run the "
                                 "gates and record the result"}
    ba_done = nodes["before-audit"]["state"] == DONE

    # -- approve (HUMAN) ---------------------------------------------------
    if not ba_done:
        nodes["approve"] = {"state": BLOCKED,
                            "reason": "waiting on: before-audit"}
    elif status in APPROVED_AND_LATER:
        nodes["approve"] = {"state": DONE, "reason": f"Status: {status}"}
    else:
        nodes["approve"] = {"state": READY, "reason":
                            "HUMAN GATE — review the docset with the user, "
                            f"then set spec.md Status: approved (currently: "
                            f"{status or 'no Status line'})"}
    approve_done = nodes["approve"]["state"] == DONE

    # -- execute (per-task frontier) ---------------------------------------
    per_task: list[dict] = []
    if not ba_done:
        nodes["execute"] = {"state": BLOCKED,
                            "reason": "waiting on: before-audit"}
    elif not approve_done:
        nodes["execute"] = {"state": BLOCKED, "reason":
                            f"waiting on: approve (spec Status: "
                            f"{status or 'none'} — approval is a human gate)"}
    elif not entries:
        nodes["execute"] = {"state": BLOCKED, "reason":
                            "task.md has no task entries — spawn the "
                            "task-breaker"}
    else:
        per_task = task_frontier(entries)
        open_tasks = [t for t in per_task
                      if t["state"] not in ("ticked", "struck")]
        n_run = sum(1 for t in open_tasks if t["state"] == "runnable")
        n_claim = sum(1 for t in open_tasks if t["state"] == "claimed")
        n_cap = sum(1 for t in open_tasks if t["state"] == "at-fix-cap")
        if not open_tasks:
            nodes["execute"] = {"state": DONE, "reason":
                                f"all {len(per_task)} task(s) ticked/struck"}
        else:
            nodes["execute"] = {"state": READY, "reason":
                                f"{n_run} of {len(per_task)} task(s) "
                                f"runnable ({len(open_tasks)} open: "
                                f"{n_claim} claimed/in flight, {n_cap} at "
                                "fix cap)"}
    execute_done = nodes["execute"]["state"] == DONE
    if per_task:
        nodes["execute"]["tasks"] = per_task

    counts = {
        "todo": sum(1 for e in entries
                    if not e.done and not e.struck and not e.claimed),
        "claimed": sum(1 for e in entries
                       if e.claimed and not e.done and not e.struck),
        "ticked": sum(1 for e in entries if e.done),
        "struck": sum(1 for e in entries if e.struck),
        "at-fix-cap": sum(1 for e in entries
                          if not e.done and not e.struck and e.fix_round
                          and e.fix_round >= FIX_CAP),
    }

    # -- closing-audit (orchestrator judgment + audit.py dod) ---------------
    if not execute_done:
        nodes["closing-audit"] = {"state": BLOCKED, "reason":
                                  f"waiting on: execute ({counts['todo']} "
                                  f"todo, {len(entries) - counts['ticked'] - counts['struck']} task(s) unticked)"}
    else:
        rc = run_dod(spec_dir, repo_override)
        if rc == 0:
            nodes["closing-audit"] = {"state": DONE, "reason":
                                      "audit.py dod — DoD mechanical gates "
                                      "pass (judgment gates stay with the "
                                      "orchestrator)"}
        elif rc is None:
            nodes["closing-audit"] = {"state": BLOCKED, "reason":
                                      "audit.py could not run — dod "
                                      "unverified"}
        else:
            nodes["closing-audit"] = {"state": BLOCKED, "reason":
                                      f"audit.py dod exits {rc} — run "
                                      f"`python3 scripts/audit.py dod "
                                      f"{spec_dir}` for the failing gates"}
    closing_done = nodes["closing-audit"]["state"] == DONE

    # -- tick-commit ---------------------------------------------------------
    if not closing_done:
        nodes["tick-commit"] = {"state": BLOCKED,
                                "reason": "waiting on: closing-audit"}
    else:
        commit_note = (f"commit per the delivery plan (HEAD {head})" if git_ok
                       else "commit SKIPPED (not a git repo)")
        nodes["tick-commit"] = {"state": DONE, "reason":
                                f"tasks ticked + burndown consistent — "
                                f"{commit_note}"}
    tick_done = nodes["tick-commit"]["state"] == DONE

    # -- archive -------------------------------------------------------------
    if not tick_done:
        nodes["archive"] = {"state": BLOCKED,
                            "reason": "waiting on: tick-commit"}
    elif status != "done":
        nodes["archive"] = {"state": BLOCKED, "reason":
                            "spec.md Status must be done before archiving "
                            "(archive.sh refuses otherwise)"}
    else:
        archived = sorted(
            p for p in (spec_dir.parent / "archive").glob(f"*-{spec_dir.name}")
            if (p / "spec.md").exists()) if (spec_dir.parent / "archive").is_dir() else []
        if archived:
            nodes["archive"] = {"state": DONE,
                                "reason": f"archived at {archived[0]}"}
        else:
            nodes["archive"] = {"state": READY, "reason":
                                "run archive.sh: moves the dir to "
                                "specs/archive/<date>-<name>/ and repoints "
                                "INDEX.md"}

    # -- loops -----------------------------------------------------------------
    if docs["survey.md"] and git_ok:
        base = specstate.survey_baseline(docs["survey.md"])
        if base is None:
            converge = "no survey baseline recorded — nothing to converge yet"
        elif head and base[1] == head:
            converge = f"fresh — survey baseline {base[1]} == HEAD {head}"
        else:
            converge = (f"stale — survey baseline {base[1]} != HEAD {head} — "
                        "re-run the survey, then audit.py converge, and "
                        "append tasks")
    elif not git_ok:
        converge = ("SKIPPED (not a git repo) — no HEAD to diff the survey "
                    "baseline against")
    else:
        converge = "no survey.md — nothing to converge yet"

    n_fix = sum(1 for e in entries if e.fix_round is not None
                and not e.done and not e.struck)
    loops = {
        "clarify": (f"active — {markers} open marker(s)" if markers
                    else "clear — no open markers"),
        "fix-round": (f"{n_fix} task(s) in fix rounds; "
                      f"{counts['at-fix-cap']} at cap ({FIX_CAP}/{FIX_CAP}) "
                      "— adjudicate" if n_fix
                      else "no fix rounds in progress"),
        "re-brief": ("orchestrator-driven on gap digests — documented, "
                     "not derived from doc state"),
        "converge": converge,
    }

    edges = [{"from": a, "to": b, "kind": "data"} for a, b in DATA_EDGES]
    edges += [{"from": a, "to": b, "kind": "conditional"}
              for a, b in CONDITIONAL_EDGES]
    edges += [{"from": a, "to": b, "kind": "loop", "label": label}
              for a, b, label in LOOP_EDGES]

    return {
        "spec_dir": str(spec_dir),
        "status": status,
        "git": {"available": git_ok, "head": head, "note": git_note},
        "nodes": {name: nodes[name] for name in NODES},
        "edges": edges,
        "frontier": [n for n in NODES if nodes[n]["state"] == READY],
        "loops": loops,
        "counts": counts,
    }


def render_report(s: dict) -> str:
    out = [f"workflow graph: {s['spec_dir']}",
           f"Status: {s['status'] or 'none'}  (lifecycle: draft → approved "
           "→ active → done)",
           "",
           "nodes:"]
    for name in NODES:
        n = s["nodes"][name]
        out.append(f"  {name:<14} {n['state']:<18} {n['reason']}")
        for t in n.get("tasks") or ():
            note = f"  [{t['note']}]" if t.get("note") else ""
            out.append(f"      {t['id'] or '—':<6} {t['state']:<11} "
                       f"{t['reason']}{note}")
    out.append("")
    out.append("frontier (run the wave together, then recompute):")
    if s["frontier"]:
        out.extend(f"  {name}" for name in s["frontier"])
    else:
        out.append("  (empty — workflow complete)")
    out.append("")
    out.append("loops:")
    out.extend(f"  {k:<10} {s['loops'][k]}" for k in ("clarify", "fix-round",
                                                      "re-brief", "converge"))
    c = s["counts"]
    out.append("")
    out.append(f"tasks: {c['todo']} todo · {c['claimed']} claimed · "
               f"{c['ticked']} ticked · {c['struck']} struck · "
               f"{c['at-fix-cap']} at fix-cap")
    g = s["git"]
    out.append("")
    out.append(f"git: available (HEAD {g['head']})" if g["available"]
               else "git: SKIPPED (not a git repo)")
    return "\n".join(out)


def render_mermaid(s: dict) -> str:
    def mid(name: str) -> str:
        return "n_" + name.replace("-", "_")

    cls = {DONE: "done", READY: "ready", BLOCKED: "blocked",
           UNDETERMINED: "undetermined", SKIPPED: "skipped"}
    out = ["flowchart LR",
           "    %% graph.py --mermaid: live state; solid = data edges, "
           "dotted = conditional/loop edges",
           "    classDef done fill:#1b5e20,color:#ffffff",
           "    classDef ready fill:#0d47a1,color:#ffffff",
           "    classDef blocked fill:#b26500,color:#ffffff",
           "    classDef undetermined fill:#6a1b9a,color:#ffffff",
           "    classDef skipped fill:#455a64,color:#ffffff"]
    for name in NODES:
        state = s["nodes"][name]["state"]
        out.append(f'    {mid(name)}["{name}"]:::{cls[state]}')
    for e in s["edges"]:
        if e["kind"] == "data":
            out.append(f"    {mid(e['from'])} --> {mid(e['to'])}")
        elif e["kind"] == "conditional":
            out.append(f"    {mid(e['from'])} -.->|conditional| {mid(e['to'])}")
        else:
            out.append(f"    {mid(e['from'])} -.->|{e['label']}| {mid(e['to'])}")
    return "\n".join(out)


def render_explain(s: dict, node: str) -> str:
    n = s["nodes"][node]
    lines = [f"{node}: {n['state']} — {n['reason']}",
             f"  ready when: {READY_WHEN[node]}",
             f"  done when: {DONE_WHEN[node]}"]
    for t in n.get("tasks") or ():
        note = f"  [{t['note']}]" if t.get("note") else ""
        lines.append(f"  {t['id'] or '—':<6} {t['state']:<11} "
                     f"{t['reason']}{note}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="graph.py",
        description="The dynamic workflow engine: derives the frontier, "
                    "loops, and lifecycle state of a spec folder from doc "
                    "state alone (see the module docstring for the node "
                    "model).",
        epilog="exit codes: 0 report produced (any state) · 1 unreadable "
               "spec-dir · 2 usage error")
    p.add_argument("spec_dir", help="path to specs/<name>")
    p.add_argument("--repo", metavar="PATH",
                   help="repo root for git-derived signals (default: the "
                        "spec dir's grandparent, like check.py/audit.py)")
    p.add_argument("--state-json", action="store_true",
                   help="print the full state as machine-readable JSON")
    p.add_argument("--mermaid", action="store_true",
                   help="render the live state graph as mermaid (dotted = "
                        "conditional/loop edges)")
    p.add_argument("--explain", metavar="NODE",
                   help="explain one node's current state and its ready/done "
                        f"conditions; nodes: {', '.join(NODES)}")
    p.add_argument("--emit-spawns", action="store_true",
                   help="write one self-contained spawn payload per frontier "
                        "agent node under <spec-dir>/spawns/wave-<N>/"
                        "<role>.md (derived artifact; safe to delete)")
    p.add_argument("--wave-dir", metavar="DIR",
                   help="with --emit-spawns or --run: write this wave's "
                        "payloads into DIR instead of "
                        "<spec-dir>/spawns/wave-<N>/")
    p.add_argument("--run", action="store_true",
                   help="auto-trigger loop: AWAITING HUMAN pauses at "
                        "judgment nodes, verify runs check.py directly, "
                        "agent waves go to --runner (default: print), "
                        "recompute, repeat")
    p.add_argument("--runner", metavar="TEMPLATE",
                   help="command template for --run with {prompt_file}, "
                        "{role}, {spec_dir}, {skill_dir} substituted "
                        "verbatim (default: print — echo invocations)")
    p.add_argument("--dry-run", action="store_true",
                   help="with --run: print the full wave plan and execute "
                        "nothing (payload files are still written)")
    p.add_argument("--max-waves", type=int, metavar="N",
                   help="with --run: stop after N waves")
    args = p.parse_args(argv)

    if args.explain is not None and args.explain not in NODES:
        p.error(f"unknown node: {args.explain!r} — valid nodes: "
                f"{', '.join(NODES)}")
    if (args.runner or args.dry_run or args.max_waves is not None) \
            and not args.run:
        p.error("--runner/--dry-run/--max-waves require --run")
    if args.emit_spawns and args.run:
        p.error("--emit-spawns and --run are separate modes")
    if args.max_waves is not None and args.max_waves < 1:
        p.error("--max-waves must be >= 1")
    if args.wave_dir and not (args.emit_spawns or args.run):
        p.error("--wave-dir requires --emit-spawns or --run")

    spec_dir = Path(args.spec_dir)
    if not spec_dir.exists():
        print(f"graph.py: spec dir not found: {spec_dir}", file=sys.stderr)
        return 1
    if not spec_dir.is_dir():
        print(f"graph.py: not a directory: {spec_dir}", file=sys.stderr)
        return 1

    if args.emit_spawns:
        return emit_spawns(spec_dir, args.repo, args.wave_dir)
    if args.run:
        return run_loop(spec_dir, args.repo, args.runner or PRINT_RUNNER,
                        args.dry_run, args.max_waves, args.wave_dir)

    state = compute_state(spec_dir, args.repo)
    if args.explain is not None:
        print(render_explain(state, args.explain))
    elif args.state_json:
        print(json.dumps(state, indent=2))
    elif args.mermaid:
        print(render_mermaid(state))
    else:
        print(render_report(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
