#!/usr/bin/env python3
"""graph.py — the dynamic workflow engine for a spec folder under specs/<name>/.

The doc state under specs/<name>/ is the only state:
graph.py derives every node's mechanical signal from it via specstate.py and
prints the workflow graph's live picture. Judgment (brief quality, gate
decisions, rulings) stays with the orchestrator and the human; this script is
the mechanical truth about what is done, what is ready, and what is blocked.

The node model (names and ready/done conditions) is contractual — see
architecture.md §2.1/§2.2 and the READY_WHEN/DONE_WHEN tables below. In sum:

  spec → clarify? → research-gate? → (research) → intent? →
  tech → plan, with qa ∥ beside them from spec → tasks → verify →
  approve(HUMAN) → execute (per-task frontier, fix-round loops ≤4) →
  tick-commit → archive, with loop edges: clarify, fix-round, re-brief,
  converge (Code state staleness).
  intent? is the optional evidence node: intent.md absent → SKIPPED,
  present-but-red → BLOCKED, green → authoring proceeds. It is an
  intake-time gate: once spec.md is filled, a lost or stale intent
  baseline is a note on a DONE node and tech-spec.md's Baseline owns
  freshness.

Modes:
  default        human-readable report: per-node state + reason, the frontier
                 wave (run it as one wave, then recompute), loop-edge status,
                 the lifecycle Status, task counts, and a git line. Git-derived
                 signals degrade loudly: `SKIPPED (not a git repo)` — never a
                 silent false result.
  --state-json   the same state as machine-readable JSON: nodes (state+reason
                 each), edges, frontier, loops, counts, git, status. The
                 authoritative oracle for tests and validators.
  --launch-check  the dynamic-workflow launch advisory as JSON: whether the dynamic
                 workflow should be launched for this doc state at all.
                 weight `wave` (a multi-payload wave, an execute span, or
                 the merged design payload — the heavy spans the loop
                 automation exists for) is the
                 only launch_workflow=true; `gate` (a human gate is
                 pending — the workflow would read state once and stop
                 AWAITING HUMAN seconds later, deciding nothing), `single`
                 (exactly one light doc node — the single-agent run mode),
                 `complete`, and `held` are handled inline by the
                 orchestrator. Pure read: payloads are counted via the
                 same frontier enumeration --emit-spawns writes, without
                 writing anything.
  --mermaid      the live state graph as mermaid: solid arrows are data edges,
                 dotted arrows are conditional/loop edges, node classes encode
                 the state (done/ready/blocked/undetermined/skipped).
  --explain NODE why that node is in its state right now — the same reason the
                 JSON carries, plus the node's ready/done conditions; for
                 execute, the per-task frontier and the isolated worktrees
                 on disk: a claimed task's, where its uncommitted work
                 sits (an orphaned claim is resumed from that path), and
                 one whose task is no longer open, which is removable.
  --emit-spawns  write one self-contained spawn payload per frontier
                 agent node to specs/<name>/spawns/wave-<N>/<role>.md (or
                 --wave-dir): frontmatter-stripped brief body byte-verbatim +
                 `protocol/shared-protocol.md` verbatim (the auditor is the
                 exempt role) + the input payload filled from doc state (spec dir,
                 requirement list, task entry verbatim + TC acceptance commands,
                 research questions) + the resolved skill_dir. spawns/ is
                 derived and regenerate-only: safe to delete, never read by
                 check.py, never status. A wave emit first removes the
                 kit's earlier payloads from the wave dir, so the dir
                 holds exactly the current wave (a --repair emit adds
                 its one file and removes nothing). Execute emits one
                 wave, one implementer-T###.md per task: the
                 runnable tasks in task-id order whose files are disjoint
                 (a task naming no files runs alone); every other runnable
                 task prints `deferred: T### (<why>)` and waits for the
                 next emit, and a claimed task is flagged as a possible
                 orphan. With a claim registry on disk, a task whose
                 files overlap a live claim of another spec in the repo
                 is deferred the same way — `shares <path> with
                 <spec>/T###` — and takes no wave-mate's place. A
                 fix-round payload carries notes/T###.md, the
                 round's failure evidence, verbatim, then the rounds'
                 arithmetic and — from the second round on — the
                 same-signature rule. The payload of the
                 round that runs a model step above the developer brief's
                 model (round 4) also carries a `Model:` line in its
                 header, and the emit's payload line names the step.
                 --native-agents is for a harness that registers this
                 package's agents: the payload names its agent type and
                 omits the brief body that type already carries (the
                 default stays self-contained) — except that round's
                 payload, which keeps the brief for a harness whose spawn
                 cannot override the registered type's model.
                 --repair NODE emits ONLY that
                 agent node's payload, in or out of the frontier — the
                 single-agent repair-run instrument (`research` emits
                 the researcher alone, `approve` the contract review
                 for a re-approval — the authoring package's alone,
                 `constitution` the analyst's constitution lens, which
                 proposes articles from the repo's conventions for the
                 user to confirm); it
                 is refused when this package ships no brief or lens for
                 the node. The
                 tech repair payload carries a DELTA RE-GROUND block
                 (files changed since tech-spec.md's stale Baseline) so a
                 converge re-ground merges § Code state instead of
                 rebuilding it. At effort tier `standard` (spec.md
                 `**Effort**: standard`) the tech → plan stretch collapses
                 into ONE merged architect payload authoring
                 tech-spec/plan in a single spawn, with qa as its own
                 implementation-blind spawn alongside; tasks stays its
                 own spawn, after qa;
                 while delivery is pending (execute done,
                 delivery not yet recorded), the reviewer-diff.md payload
                 (implementation-diff mode) is prepared the same way the
                 undetermined gate's researcher payload is, with the
                 final diff written beside it as reviewer-diff.patch
                 (the auditor holds no shell).
  --run          the auto-trigger loop: compute the frontier; pause
                 `AWAITING HUMAN: <node>` at every human gate (clarify,
                 approve, tick-commit) and `AWAITING ORCHESTRATOR:
                 research-gate` at the orchestrator's own judgment, or
                 `AWAITING ORCHESTRATOR: execute` when no task can be
                 spawned (claimed, blocked, or at the fix cap — each
                 named with what it needs) —
                 gates are never auto-satisfied and this loop mutates no
                 doc state of its own EXCEPT through mark.py, the single
                 marker writer (the headless execute wave: mark.py
                 claims, the runner runs, mark.py lands — spec-build
                 D-041; where this package ships no mark.py a custom
                 runner is refused with exit 2 before any invocation,
                 spec-build D-038); run the mechanical verify node
                 (check.py) directly; emit payloads for the ready agent
                 wave; invoke --runner per payload (default `print`: echo
                 the invocation, then stop after the one emitted wave —
                 the orchestrator spawns it and re-runs); a template's
                 {model} takes the brief's model, and the same with `+1`
                 on the fix round that runs a model step — a template
                 without {model} stops that wave `AWAITING
                 ORCHESTRATOR` before the round is claimed, exit 0; a
                 runner that exits nonzero or raises
                 stops the loop with a role/node diagnostic and exit 3, so
                  no later wave starts; recompute and repeat until a gate,
                  workflow completion, --max-waves, or a wave that moved
                  no doc state. Before every wave after the first the
                  digests are swept again — they land between waves —
                  and a refused one stops the loop `AWAITING
                  ORCHESTRATOR` on the fix-and-run-again line, exit 0.
  --span PHASE   with --run/--emit-spawns: bound the wave to one phase's
                 frontier — `intent` (the analyst node; spec/clarify
                 mechanics unchanged), `shape` (intent + the authoring wave
                 tech/plan/qa/tasks + verify + the approve display;
                 a drained shape span stops at the approve handoff; a
                 shape span with no spec to author prints AWAITING and
                 routes to intake; one held on blocked nodes exits 1),
                 `execute` (execute + tick-commit + archive mechanics),
                 `full` (default — bare-invocation semantics, byte-identical
                 for existing dirs). A span is a frontier filter only: node
                 states compute identically under every span; spans gate
                 which payloads are written and where --run stops as
                 drained. Span entry refuses (exit 4, the blocking gate and
                 its reason printed, an intake_refusal telemetry event under
                 the derived skill name): shape when the intent node is
                 BLOCKED; execute unless approve AND verify are DONE.
  --harness NAME with --run/--emit-spawns: the harness running this
                 session, recorded verbatim in the spec's run ledger
                 beside every payload these modes write and every run
                 they start (`specs/<name>/runs/ledger.jsonl` — one row
                 per orchestrator event, append-only, never status;
                 default `unknown`). The same invocation first sweeps
                 digests/wave-*/: each digest file with no provenance
                 line is validated and, when valid, gains the one line
                 the ledger vouches for; a malformed file is left as it
                 is and named, and so is one whose `tools:` report lacks
                 a tool its role requires (a failed spawn, not a fix
                 round). Either holds the node its spawn answers —
                 tech, plan, qa, tasks, the merged design's through
                 tech: the node is neither done nor runnable, so the
                 wave after it waits until the digest is re-spawned. A
                 signed approval ends the hold.
  --isolate worktree
                 with --emit-spawns or --run: every implementer payload
                 of the wave works in its own detached git worktree at
                 `<repo>/.spec-kit/worktrees/<spec>/<T###>/`, checked out
                 at a snapshot of the main working tree — landed,
                 still-uncommitted work included — and the payload's
                 `- repo:` line names that worktree as the developer's
                 only working tree (spec-build D-058); the digest file
                 and the fix round's note are its two exceptions, written
                 in the main tree's spec dir where land reads them. The
                 emit creates
                 a missing worktree, rebuilds one nothing was ever done
                 in from the current tree — a task re-emitted after a
                 deferral starts from everything landed since — keeps one
                 that holds work as it is (a fix round continues there),
                 and removes the worktrees of tasks no longer open.
                 mark.py land runs the proofs in the worktree and merges
                 its delta into the main tree, working tree only;
                 mark.py release and drop discard it. Outside a git
                 repository
                 the flag refuses with exit 2, nothing written; --dry-run
                 prints the plan and creates nothing.
  --budget-spawns N, --budget-minutes N
                 with --run: the run budgets (spec-build D-059,
                 spec-design D-080) — 30 implementer spawns and 120
                 wall-clock minutes by default, 0 lifts a budget.
                 Counted from the spec's run ledger before every wave
                 that would claim: spawns over this run (its `claim`
                 rows) and again over the spec's whole ledger, so a
                 spec re-run under new run ids still stops; minutes
                 over this run alone, since its first claim — an
                 unattended span is one run. Spent, the loop parks
                 `AWAITING HUMAN: run budget — <what> used <n> of <n>`
                 before the wave, claiming nothing; `mark.py claim`
                 takes the same two flags and refuses on the same
                 line, so the budget holds however the run is driven.
                 Tokens are not budgeted: no harness reports them to
                 the kit.

Mechanical probes: the tech node runs `check.py <spec-dir> --code-state-only`
and the verify node runs `check.py <spec-dir>` — skill-owned contract
checkers, each only once its inputs are in place; the intent node probes
`check.py <spec-dir> --intent-only` only when intent.md is present (absent
→ SKIPPED), and once spec.md is filled a red probe still reads DONE when
only the baseline pair failed. No inspection mode ever
executes repository or `test.md` commands, and proofs execute only on the
explicit audit.py CLI. Human gates (clarify, approve, an undetermined
research-gate, tick-commit) are never auto-satisfied by this script.

Usage: graph.py <spec-dir> [--repo <path>] [--state-json] [--mermaid]
                [--explain <node>] [--wave-dir <dir>] [--launch-check]
                [--emit-spawns] [--repair <node>] [--native-agents]
                [--run [--runner '<template>'] [--dry-run] [--max-waves N]
                [--parallel N] [--harness <name>]
                [--budget-spawns N] [--budget-minutes N]]
                [--span intent|shape|execute|full] [--isolate worktree]
Exit:  0 = report produced (any workflow state) · 1 = unreadable spec-dir,
       or a phase span stopped red/held (verify RED, blocked nodes) ·
       2 = usage error (unknown flag, unknown --explain node, missing
       args, a --repair node this package cannot emit), or --run refused:
       a custom runner met execute payloads (D-038, nothing invoked) —
       or --isolate worktree outside a git repository (nothing written)
       · 3 = --run stopped: a runner exited nonzero or raised
       · 4 = span entry refused (the blocking gate and its reason printed)
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# Shared parsers live in specstate.py beside this script; the invisible-char
# strip and the code-span/comment/placeholder regexes are check.py's canonical
# copies (one definition each — graph.py must not grow its own). The scripts
# dir goes on sys.path locally (no install step): tests load this file by path
# via importlib, which does not put scripts/ on sys.path.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from telemetry import record as _record  # noqa: E402 - local run telemetry

from check import (  # noqa: E402
    CODE_SPAN,
    HTML_COMMENT,
    INVISIBLE,
    PLACEHOLDER,
    QUOTE_SPAN,
    constitution_status,
    intent_failures,
)
import freeze  # noqa: E402
import specstate  # noqa: E402

# The workflow graph's nodes, in canonical (dependency) order. Names must
# match SKILL.md's table.
NODES = [
    "spec", "clarify", "research-gate", "research", "intent", "tech",
    "plan", "qa", "tasks", "verify", "approve", "execute",
    "tick-commit", "archive",
]

DOC_FILES = ["spec.md", "intent.md",
             "plan.md", "tech-spec.md", "task.md", "test.md"]

# Fix-round cap: `(fix n/5)` — the cap lives in the task.md annotation, so a
# task at cap is surfaced for adjudication, never auto-retried past it.
FIX_CAP = 5

# The one fix round that runs a model step above the developer brief's
# model: the round after three came back wrong at that model — the
# fourth, and the last that spawns. Its payload is the only one that
# names a model — relative to the brief, never a model id, since each
# harness resolves the step its own way.
MODEL_STEP_ROUND = 4
MODEL_STEP_LINE = (
    "- Model: this round runs one model step above the developer brief's "
    f"model — fix round {MODEL_STEP_ROUND}, the last round that spawns, "
    f"after rounds 1–{MODEL_STEP_ROUND - 1} came back wrong at that "
    "model: four rounds spawn, the fifth failure stops")

# The note a --native-agents payload carries on that round, above the
# brief it alone still embeds: a spawn that cannot override the
# registered type's model hands the payload to a general-purpose agent.
NATIVE_MODEL_STEP_NOTE = (
    "Fix round {round} — the `Model:` line above asks for one model step "
    "above this brief's model. Two routes: (i) spawn this payload as "
    "agent type `{type}` with a spawn-time model override, where the "
    "harness's spawn call allows it — this brief is then already that "
    "type's system prompt; (ii) otherwise spawn it on a general-purpose "
    "agent on the stronger model, given this payload — the brief is "
    "embedded below for exactly this route.\n\n")

# The header line an isolated implementer payload adds under its `- repo:`
# line (spec-build D-058): the brief it embeds still describes a shared
# tree, so the payload says which tree is the developer's and that the
# brief's rule against moving a tree holds there too. The worktree
# carries a copy of the spec dir, and nothing reads a digest or a note
# written in that copy: both belong in the main tree's.
ISOLATED_WORKTREE_LINE = (
    "- isolated worktree: {path} is your ONLY working tree — create, edit "
    "and delete files there and nowhere else; the main tree ({repo}) is "
    "not yours to touch. Two exceptions, both under the main tree's spec "
    "dir ({spec_dir}): your digest file (the `## Digest file` section's "
    "path), and on a fix round the note `notes/T###.md` the brief lets "
    "you append to — written there and never in this tree's copy of it, "
    "where nothing reads them. Your work reaches the main tree only "
    "through `mark.py land`, which merges this tree's delta; `mark.py "
    "release` discards it. The brief's ban on stash/reset/checkout still "
    "binds — its HEAD is a snapshot, not a commit of yours.")

# Every payload's first instruction (spec-design D-076): the rule itself
# lives in protocol/shared-protocol.md — this line only asks for the
# report, so it reaches the auditor too, whose payload carries no protocol.
TOOLS_ASK = (
    "The first line of your reply — and, when your payload names a digest "
    "file, of that file, above the `digest:` line — is `tools: <the tools "
    "you actually hold, comma-separated>`.")

# D-044 same-failure thresholds, read from each fix round's evidence
# (specstate.failure_signature_run over notes/T###.md): at ADVISORY rounds
# of one repeated failing command, mark.py's fail and the at-cap reason say
# the plan is the suspect — another round or a stronger model re-runs the
# same command. The WATCH bound is the earlier, never-blocking signal the
# per-task lines print.
SAME_FAILURE_ADVISORY = 3
SAME_FAILURE_WATCH = 2

# Payload cap for a fix round's evidence note: the newest round is
# appended last, so the tail is what the developer needs.
FIX_NOTE_LINE_CAP = 200

# The fix-round payload's closing lines: the rounds' arithmetic, then —
# from the second round on, the first with a round to compare against —
# the rule the round history is read with, said of this task once its
# own last rounds repeat one command.
ROUNDS_LINE = ("- Rounds: four rounds spawn, the fifth failure stops — this "
               "is round {round}")
SAME_SIGNATURE_RULE = (
    "- Same-signature rule: when the newest `## Fix round` section's `$ "
    "<command>` line is the same command as the round before it, another "
    "round re-runs it — the plan, not the model, is the suspect "
    "(`contracts/execution.md` § Fix rounds)")
SAME_SIGNATURE_FACT = (
    ". This task is there: `{command}` failed the last {run} round(s) — "
    "suspect the plan, not the model, before spending this round")

# Payload cap for the DELTA RE-GROUND file list: a mass refactor's delta
# is the whole repo — the payload says so instead of listing thousands of
# paths the architect would re-read one grep at a time anyway.
DELTA_FILE_CAP = 200

# Lifecycle words that mean the approval gate is behind us (approve's done
# condition is "Status: approved (or later)").
APPROVED_AND_LATER = ("approved", "active", "done")

# Data edges: node B ready ⟺ all in-neighbors done (§2.2).
DATA_EDGES = [
    ("spec", "intent"),
    ("intent", "tech"), ("intent", "qa"),
    ("tech", "plan"),
    ("plan", "tasks"), ("tech", "tasks"), ("qa", "tasks"),
    ("tech", "verify"), ("plan", "verify"),
    ("qa", "verify"), ("tasks", "verify"),
    ("verify", "approve"), ("approve", "execute"),
    ("execute", "tick-commit"),
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
    ("execute", "execute", "fix-round cap: four rounds spawn, the fifth "
     "failure stops"),
    ("tech", "tasks", "converge staleness"),
]

# The node/ready/done contract (architecture §2.1), kept as data so --explain
# states it exactly and tests compare against one surface.
# Single source: scripts/contract.py owns every node's identity,
# readiness, and done-signal — SKILL.md's node table is
# generated from the same table (`contract.py --render skill-table`).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import DONE_WHEN, READY_WHEN  # noqa: E402

# Report token per node state — the same vocabulary --state-json carries.
DONE, READY, BLOCKED, UNDETERMINED, SKIPPED = (
    "done", "READY", "blocked", "gate:undetermined", "SKIPPED")

# Frontier agent nodes → (spawn role, brief file under agents/). Payloads are
# named <role>.md (execute: one per runnable task). The auditor is never a
# frontier node — it rides the tick-commit orchestrator judgment — but the
# payload builder still knows its protocol exemption.
AGENT_BRIEFS = {
    # node -> (role, archetype brief, lens); five archetypes,
    # lens specializations ride the payload from protocol/lenses.md
    "intent": ("analyst", "analyst.md", "intent"),
    "tech": ("tech", "architect.md", "tech"),
    "plan": ("planner", "architect.md", "plan"),
    "qa": ("qa", "tester.md", "qa"),
    "tasks": ("task-breaker", "architect.md", "tasks"),
    "execute": ("implementer", "developer.md", "build"),
}

# The digest-file stems each authoring node's spawns answer with. The
# newest file of a stem that the orchestrator refuses holds its node:
# the artifact on disk is not witness enough for the wave after it.
NODE_DIGEST_STEMS = {
    "tech": ("tech", "designer"), "plan": ("planner",), "qa": ("qa",),
    "tasks": ("task-breaker",),
}

# The research node never reaches the frontier (its gate is a judgment),
# so its payload wiring lives beside the frontier nodes' only for --repair
# and the undetermined-gate emit.
RESEARCH_BRIEF = ("researcher", "analyst.md", "research")

# --repair's single-node instruments. Execute is never repaired: its
# payloads are per task. `approve` re-emits the contract review when a
# corrected spec is re-approved and approve is no longer the frontier.
# `constitution` is no graph node: it is the constitution step's
# on-demand instrument, proposing articles for the user to confirm.
REPAIR_BRIEFS = {
    **{n: v for n, v in AGENT_BRIEFS.items() if n != "execute"},
    "research": RESEARCH_BRIEF,
    "approve": ("reviewer", "auditor.md", None),
    "constitution": ("constitution", "analyst.md", "constitution"),
}

# The contract review belongs to the package that authors docsets: a
# package without the architect brief may hold the auditor for its own
# span (the implementation diff) and still must not review for approval.
AUTHORING_BRIEF = "architect.md"

# Archetypes whose brief is the whole contract; every other brief needs
# its lens section from this package's protocol/lenses.md.
LENSLESS_BRIEFS = frozenset({"tester.md", "developer.md", "auditor.md"})

# This script IS the running skill's — its own root is the resolved skill_dir
# every payload carries (never guessed, never hardcoded in a brief).
SKILL_DIR = _SCRIPTS_DIR.parent

# The telemetry skill name every event records under — the engine's own
# resolved root, so each shipping skill's replica reports as itself.
SKILL_NAME = SKILL_DIR.name

# Default --run runner: echo the invocation instead of executing it —
# equivalent to --dry-run with payloads emitted (architecture §4.5).
PRINT_RUNNER = "print"

# --run's failure exit: the first runner that exits nonzero or raises stops
# the loop (0/1/2 keep their documented meanings).
RUNNER_FAILED_EXIT = 3

# --run's execute refusal (spec-build D-038): a custom runner never invokes
# execute payloads — claiming and landing tasks is the orchestrator's move.
# The refusal sits in front of the subprocess call, so no edit happens.
EXECUTE_RUNNER_REFUSED_EXIT = 2

# --span's refusal exit: the span-entry gate read an already-computed node
# state and refused the invocation — distinct from every runner or
# usage failure so callers can route it to the right phase.
SPAN_REFUSED_EXIT = 4

# --isolate worktree's refusal: no git repository, or git could not build,
# check out or keep a worktree — a usage exit, before anything is written.
ISOLATE_REFUSED_EXIT = 2

# Phase spans: a span bounds which frontier/payload nodes a run may
# touch — a filter on the frontier, never a node's ready/done vocabulary
# (states compute identically under every span). `design` is the collapsed
# tech → plan stretch, admitted wherever its tech constituent is;
# `research` rides the full span alone (the intent phase never decides it,
# and shape's authoring resolves the gate out-of-band); the auditor's
# tick-commit mechanics belong to execute.
SPAN_AGENT_NODES = {
    "intent": frozenset({"intent"}),
    "shape": frozenset({"tech", "plan", "qa", "tasks", "approve"}),
    "execute": frozenset({"execute", "tick-commit"}),
}

# What a drained span hands off to, and the command that continues it —
# the approve gate is shape's named handoff; intent hands to shape,
# shape to execute.
SPAN_HANDOFF = {"intent": ("shape", "/spec-design"),
                "shape": ("execute", "/spec-build")}


def span_allows(span: str, node: str) -> bool:
    """Whether a frontier/payload node may run under the span. `full`
    admits everything (bare-invocation semantics); a phase admits its own nodes
    only, so no span ever changes a node's state."""
    if span == "full":
        return True
    if node == "design":
        node = "tech"
    return node in SPAN_AGENT_NODES[span]


def span_entry_refusals(state: dict, span: str) -> list[tuple[str, str]]:
    """The invocation-time span gates: span entry reads the
    already-computed node states — shape refuses on a BLOCKED intent
    (absent reads SKIPPED and passes); execute
    refuses unless approve is DONE (APPROVED_AND_LATER) AND verify is
    DONE. One (gate, reason) pair per blocking gate; empty = allowed."""
    n = state["nodes"]
    if span == "shape":
        if n["intent"]["state"] == BLOCKED:
            return [("intent", n["intent"]["reason"])]
        return []
    if span == "execute":
        return [(g, n[g]["reason"]) for g in ("approve", "verify")
                if n[g]["state"] != DONE]
    return []


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
    return bool(unfilled_hits(text))


def unfilled_hits(text: str, cap: int = 5) -> str:
    """The evidence behind is_unfilled: `token@line` entries for every
    placeholder-shaped token (or literal YYYY-MM-DD) outside code spans,
    quoted spans, and HTML comments. Fenced-block content IS scanned —
    matches hiding there
    are the recurring false-'unfilled' failure. Empty string = filled."""
    hits: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        s = HTML_COMMENT.sub(
            " ", QUOTE_SPAN.sub(" ", CODE_SPAN.sub(" ", line)))
        if "YYYY-MM-DD" in s:
            hits.append(f"YYYY-MM-DD@{lineno}")
        for m in PLACEHOLDER.finditer(s):
            hits.append(f"{m.group(0)}@{lineno}")
    if len(hits) <= cap:
        return ", ".join(hits)
    return ", ".join(hits[:cap]) + f"… (+{len(hits) - cap} more)"


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


def task_files(entry: specstate.TaskEntry) -> list[str]:
    """Intended touches from the complete entry, including `Touches:` blocks."""
    return specstate.task_touches(entry)


def claim_age(iso: str) -> str:
    """A claim stamp's age as a coarse human delta (`12s`, `4m`, `3h`,
    `2d`) — the resume view's "how long has this claim been sitting
    there". Unparseable stamps read `unknown age`, never raise."""
    try:
        then = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        secs = max(0, int(datetime.datetime.now(
            datetime.timezone.utc).timestamp() - then.timestamp()))
    except ValueError:
        return "unknown age"
    if secs < 90:
        return f"{secs}s"
    if secs < 5400:
        return f"{secs // 60}m"
    if secs < 129600:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


def failure_run(spec_dir: Path, task_id: str) -> tuple[str | None, int]:
    try:
        note = (spec_dir / "notes" / f"{task_id}.md").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return None, 0
    return specstate.failure_signature_run(note)


def task_frontier(entries: list[specstate.TaskEntry],
                  run_id: str | None = None,
                  spec_dir: Path | None = None,
                  held: dict | None = None) -> list[dict]:
    """The per-task frontier inside execute (§2.1): a task is runnable when
    it is `- [ ]`, unimplemented, its `(after T###)` deps are all
    implemented, ticked, or struck, and it is not at the fix-round cap. An
    `(implemented)` entry has landed: it reads `implemented`, never
    runnable, and counts toward execute's completion — unless an open
    `(fix n/5)` sits beside it, which makes the task runnable again.
    At-cap tasks are surfaced for adjudication, never runnable. Runnable
    tasks whose files overlap each other's, or a claimed task's, cannot
    share a wave: `deferred` names why a runnable task waits for the
    next one (schedule_wave). `run_id` is the calling run's own claim
    stamp id, when it has one: a claim stamped with that id is this
    run's wave still in flight, not an orphan; every other claim —
    stamped with a different run id, or unstamped (hand-written,
    older docset) — reads as a possible orphan as before.
    `spec_dir`, when given, lets an at-cap task's reason name a repeated
    failure signature (D-044): the same failing command across rounds
    means the plan is the suspect, not the model. `held`, the live claims
    of the repo's other specs (`specstate.claims_held`, D-078), defers a
    runnable task whose files overlap one of them."""
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
        elif e.implemented:
            state, why = "implemented", (
                "landed unticked — the plan-wide tick follows the "
                "pre-tick proof pass")
        elif e.claimed:
            held = (f" (claimed {claim_age(e.claim.at)} ago by run "
                    f"{e.claim.run})" if e.claim else "")
            if e.claim and run_id and e.claim.run == run_id:
                state, why = "claimed", (
                    "marked (in-progress) — held by this run's wave"
                    f"{held}: its payload ran or is out; land it with "
                    "mark.py land, or mark.py release it to re-run")
            else:
                state, why = "claimed", (
                    "marked (in-progress) — a developer holds it"
                    f"{held}; with no developer running (a killed "
                    "session) it is an orphan: re-run its acceptance "
                    "commands and mark it (implemented), or clear the "
                    "claim to re-run it")
        elif e.id is None:
            state, why = "blocked", "entry line has no T-### id — fix the entry"
        else:
            missing = [d for d in e.after if d not in by_id]
            unmet = [d for d in e.after if d in by_id
                     and not (by_id[d].done or by_id[d].struck
                              or by_id[d].implemented)]
            if missing:
                state, why = "blocked", (
                    f"dependency not defined in task.md: {', '.join(missing)}")
            elif unmet:
                state, why = "blocked", (
                    f"waiting on {', '.join(unmet)} "
                    "(unticked, unimplemented)")
            elif e.fix_round is not None and e.fix_round >= FIX_CAP:
                state, why = "at-fix-cap", (
                    f"fix cap reached ({e.fix_round}/{FIX_CAP}) — adjudicate "
                    "before another round (plan-suspect → re-brief tech)")
                if spec_dir is not None and e.id:
                    sig, run = failure_run(spec_dir, e.id)
                    if sig and run >= SAME_FAILURE_ADVISORY:
                        why = (f"fix cap reached ({e.fix_round}/{FIX_CAP}) — "
                               f"the same failing command has failed {run} "
                               f"rounds ({sig}): another round re-runs it; "
                               "adjudicate (wrong → park D-###, isolated → "
                               "defer, load-bearing → /spec-design)")
            elif e.fix_round is not None:
                state, why = "runnable", (
                    f"fix round {e.fix_round}/{FIX_CAP} open — re-run with "
                    "the failure evidence")
            else:
                state, why = "runnable", "deps satisfied — ready for an implementer"
        out.append({"id": e.id, "state": state, "reason": why,
                    "files": files, "note": None, "deferred": None})

    runnable = [t for t in out if t["state"] == "runnable"]
    for t in runnable:
        mates = sorted({o["id"] for o in runnable if o is not t and any(
            specstate.paths_overlap(x, y)
            for x in o["files"] for y in t["files"]
        )})
        if mates:
            t["note"] = (f"shares files with {', '.join(mates)} — "
                         "they take separate waves")
        elif not t["files"]:
            t["note"] = "no parseable Touches: — runs alone"
    schedule_wave(runnable, [t for t in out if t["state"] == "claimed"],
                  held)
    return out


def _wave_conflict(task: dict, wave: list[dict]) -> str | None:
    """Why `task` cannot join the wave, or None. A task naming no files
    could touch anything, so it conflicts with every wave-mate."""
    for mate in wave:
        who = (mate["id"] or "—") + (
            " (in-progress)" if mate["state"] == "claimed" else "")
        if not mate["files"]:
            return f"{who} has no parseable Touches: and runs alone"
        if not task["files"]:
            return "no parseable Touches: — runs alone"
        for theirs in mate["files"]:
            for ours in task["files"]:
                if specstate.paths_overlap(theirs, ours):
                    shared = max(theirs, ours, key=len)
                    return f"shares {shared} with {who}"
    return None


def _cross_conflict(task: dict, held: dict) -> tuple[str, str] | None:
    """(`spec/T###`, why) for the live claim of another spec that holds
    `task` off, or None. Either side naming no files could touch
    anything, so it holds against all (D-078)."""
    for key in sorted(held):
        theirs = held[key]
        if not theirs:
            return key, f"{key} has no parseable Touches: and runs alone"
        if not task["files"]:
            return (key, "no parseable Touches: — runs alone while "
                    f"{key} is open")
        for other in theirs:
            for ours in task["files"]:
                if specstate.paths_overlap(other, ours):
                    shared = max(other, ours, key=len)
                    return key, f"shares {shared} with {key}"
    return None


def schedule_wave(runnable: list[dict], in_flight: list[dict],
                  held: dict | None = None) -> None:
    """Pick the wave: runnable tasks in task-id order, each admitted only
    when file-disjoint from every task already in and from every claimed
    task still holding its files — and from every live claim of the
    repo's other specs when `held` is given; the rest carry `deferred`
    and wait for the next wave. A task another spec holds off also
    carries `held_by`, the `<spec>/<T###>` that holds it, and takes no
    wave-mate's place."""
    wave: list[dict] = list(in_flight)
    for task in sorted(runnable, key=lambda t: t["id"]):
        cross = _cross_conflict(task, held) if held else None
        task["deferred"] = (cross[1] if cross else None) \
            or _wave_conflict(task, wave)
        if cross:
            task["held_by"] = cross[0]
        if task["deferred"] is None:
            wave.append(task)


def task_line(t: dict) -> str:
    """One per-task report line: id, state, reason, and the wave note —
    claimed tasks add their digest-file reading (D-040), a typed
    deviation riding beside it (D-043), and a watch suffix when the
    same failing command recurs across fix rounds (D-044)."""
    note = (f"deferred: {t['deferred']}" if t.get("deferred")
            else t.get("note"))
    line = (f"{t['id'] or '—':<6} {t['state']:<11} {t['reason']}"
            + (f"  [{note}]" if note else ""))
    if t["state"] == "claimed" and "digest" in t:
        line += f"  [digest on file: {t['digest'] or 'none'}]"
        if t.get("deviation"):
            line += f"  [deviation {t['deviation']}]"
    if t.get("watch"):
        line += f"  [watch: {t['watch']}]"
    return line


def execute_holds(state: dict, every: bool = False) -> list[str]:
    """Lines naming what this wave leaves behind and what the
    orchestrator owes each: deferred runnables and claimed tasks
    always; with `every`, the blocked and at-cap tasks too."""
    lines: list[str] = []
    for t in state["nodes"]["execute"].get("tasks") or ():
        if t.get("deferred"):
            lines.append(f"   deferred: {t['id']} ({t['deferred']})")
        elif t["state"] == "claimed" or (
                every and t["state"] in ("blocked", "at-fix-cap")):
            lines.append(f"   {t['state']}: {t['id'] or '—'} — "
                         f"{t['reason']}")
    return lines


# ---------------------------------------------------------------------------
# Executor: --emit-spawns payloads and the --run auto-trigger loop
# (architecture §4.4–§4.5). Everything here is derived from doc state —
# the same state compute_state returns — so both modes always agree on
# wave numbering and payload paths, and neither ever writes doc state.
# ---------------------------------------------------------------------------

FRONTMATTER = specstate.FRONTMATTER
FR_ENTRY = re.compile(r"^-\s+\*\*(?:FR|NFR)-\d{3}\*\*", re.M)
PASS_CONDITION = re.compile(r"\*\*Pass condition\*\*:?(.*)")


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
    the same state. Waves advance as milestone groups complete:
    grounding (research + tech ∥ qa), the plan, the task list, then one
    per executed task batch (ticked/struck count)."""
    n = state["nodes"]
    settled = lambda name: n[name]["state"] in (DONE, SKIPPED)
    wave = 1
    if all(settled(x) for x in ("research", "tech", "qa")):
        wave += 1
    if settled("plan"):
        wave += 1
    if settled("tasks"):
        wave += 1
    return wave + state["counts"]["ticked"] + state["counts"]["struck"]


def fr_entries(spec_text: str) -> list[str]:
    """The spec's FR/NFR entries verbatim (a line plus wrapped
    continuation lines) — the payload's requirement list."""
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


def research_questions(tech_text: str) -> list[str]:
    """The tech-spec's recorded research questions — bullet lines under
    `## Questions & options` → `### Questions`. Empty when the section
    records none (a skip-form section has no bullets): the researcher
    brief derives 3–6 from the open technical choices, so the payload
    says so instead of inventing questions."""
    m = specstate.QUESTIONS_SECTION.search(tech_text)
    if not m:
        return []
    body = tech_text[m.end():]
    end = body.find("\n## ")
    body = body[:end] if end >= 0 else body
    qm = re.search(r"^###\s+Questions\s*$", body, re.I | re.M)
    if not qm:
        return []
    out: list[str] = []
    for line in body[qm.end():].splitlines():
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
        rm = re.match(r"\|\s*((?:FR|NFR)-\d{3})\s*\|", line)
        if rm:
            for tc in re.findall(r"TC-\d{3}", line):
                out.setdefault(tc, {"frs": set(), "commands": [],
                                    "note": "(observation only — MANUAL)"})
                out[tc]["frs"].add(rm.group(1))
    return out


def acceptance_for(entry_block: str, test_text: str) -> list[str]:
    """The TC pass-condition command(s) a task entry answers for — the
    implementer's acceptance list (always for code tasks): the cases its
    `Proves:` line names, else those tracing to the requirements it
    cites. MANUAL TCs are named; a missing test.md says so instead of
    inventing a command."""
    if not test_text.strip():
        return ["(test.md not written yet — no TC pass conditions)"]
    frs = set(re.findall(r"\b(?:FR|NFR)-\d{3}\b", entry_block))
    tcs = tc_conditions(test_text)
    proves = set(specstate.task_proves(entry_block))
    matched = ([tc for tc in sorted(tcs) if tc in proves] if proves else
               [tc for tc in sorted(tcs) if not frs or tcs[tc]["frs"] & frs])
    lines: list[str] = []
    for tc in matched:
        info = tcs[tc]
        if info["commands"]:
            lines += [f"{tc}: `{c}`" for c in info["commands"]]
        else:
            lines.append(f"{tc}: {info['note']}")
    return lines or ["(no TC pass conditions match this task's requirements)"]


def _indent(text: str, pad: str = "   ") -> str:
    return "\n".join(pad + ln for ln in text.splitlines())


def code_delta(repo: Path, spec_dir: Path, base_sha: str,
               head: str) -> tuple[list[str] | None, list[str] | None]:
    """(every path, the paths outside the kit's doc trees) changed
    between the baseline and HEAD — (None, None) when git cannot say.
    Only the second list can move a code citation."""
    raw = specstate.diff_paths(repo, base_sha, head)
    if raw is None:
        return None, None
    return raw, specstate.code_paths(
        raw, specstate.doc_tree_prefixes(repo, spec_dir.parent))


def _reground_delta_lines(base: tuple[str, str] | None, repo: Path,
                          spec_dir: Path) -> list[str]:
    """The DELTA RE-GROUND block for a stale tech-spec Baseline (the
    converge loop's cost fix): the files git says changed since the
    baseline commit, so the architect MERGES into the existing § Code
    state instead of rebuilding it — a citation in an unchanged file
    cannot have moved. The kit's doc trees are excluded: a docs-only
    commit (task ticks, tech-spec.md's own refresh) can't invalidate a
    code citation, and a delta that lists it would force the exact
    re-ground this block exists to save. Fresh/absent baseline, or a git that
    cannot scope the delta, yields either nothing or an explicit degrade
    line — never a silent empty-delta verdict read as 'nothing to
    re-check'."""
    if not base or not specstate.git_available(repo):
        return []
    head = specstate.head_sha(repo)
    if not head or base[1] == head:
        return []
    raw, paths = code_delta(repo, spec_dir, base[1], head)
    if raw is None:
        return [f"- delta: unavailable (git diff {base[1]}..{head} "
                "failed) — re-ground § Code state in full and merge it "
                "yourself"]
    if not paths:
        return [f"- DELTA RE-GROUND: baseline {base[1]} != HEAD {head} "
                "but no code files changed "
                + ("(the diff touches only the kit's doc trees) "
                   if raw else "(no files changed) ")
                + "— refresh tech-spec.md's Baseline "
                f"header to HEAD {head} and re-run the self-check; no "
                "item needs re-grepping"]
    shown = paths[:DELTA_FILE_CAP]
    more = len(paths) - len(shown)
    out = [
        f"- DELTA RE-GROUND: baseline {base[1]} != HEAD {head} — merge "
        "into the existing § Code state, do NOT rebuild it:",
        "  - re-grep ONLY items whose evidence cites a changed file "
        "below (a citation in an unchanged file cannot have moved);",
        "  - re-run the re-checked items' verify commands;",
        "  - keep every untouched item byte-identical; refresh the "
        f"Baseline header to HEAD {head};",
        "  - the --code-state-only self-check stays full-strength over "
        "the merged section.",
        f"  Files changed since the baseline ({len(paths)}):",
    ]
    out += [f"     {p}" for p in shown]
    if more:
        out.append(f"     … +{more} more (payload cap {DELTA_FILE_CAP}) "
                   "— the delta is effectively the whole repo")
    return out


def _intent_seed_lines(spec_dir: Path, repo: Path) -> list[str]:
    """The INTENT SEED block for a first grounding (D-065): intake already
    grepped the touched areas and pasted verbatim evidence into intent.md
    § Constraints at its baseline. Evidence in a file unchanged since that
    baseline cannot have moved, so the architect re-runs the item's verify
    command instead of re-grepping; changed files and uncovered items
    are grounded fresh. Statuses never carry over — only evidence."""
    intent = read_doc(spec_dir / "intent.md")
    base = specstate.doc_baseline(intent) if intent else None
    if not base or not specstate.git_available(repo):
        return []
    head = specstate.head_sha(repo)
    if not head:
        return []
    intent_ref = spec_dir / "intent.md"
    if base[1].startswith(head) or head.startswith(base[1]):
        paths: list[str] = []
    else:
        raw, paths = code_delta(repo, spec_dir, base[1], head)
        if raw is None:
            return [f"- intent seed: unavailable (git diff {base[1]}..{head} "
                    "failed) — ground every item fresh"]
    out = [
        f"- INTENT SEED: {intent_ref} § Constraints holds verbatim evidence "
        f"probed at {base[1]} (HEAD {head}) — start from it:",
        "  - an item that evidence already grounds, citing a file NOT "
        "listed below: copy the evidence line as-is and re-run the item's "
        "verify command — do not re-grep;",
        "  - grep fresh every item it does not cover, and every item whose "
        "evidence cites a listed file;",
        "  - intent facts are evidence only, never statuses: every status "
        "comes from a verify command you ran.",
    ]
    if not paths:
        out.append("  No code files changed since the intent baseline.")
        return out
    shown = paths[:DELTA_FILE_CAP]
    out.append(f"  Files changed since the intent baseline ({len(paths)}):")
    out += [f"     {p}" for p in shown]
    if len(paths) > len(shown):
        out.append(f"     … +{len(paths) - len(shown)} more (payload cap "
                   f"{DELTA_FILE_CAP}) — ground every item fresh")
    return out


def grounding_lines(spec_dir: Path, repo: Path) -> list[str]:
    """The tech payload's grounding facts: repo root, tech-spec.md's
    recorded Baseline, the DELTA RE-GROUND block when it is stale, and
    on a first grounding the INTENT SEED block (D-065)."""
    tech_text = read_doc(spec_dir / "tech-spec.md")
    base = specstate.doc_baseline(tech_text) if tech_text else None
    return [
        f"- repo root: {repo}",
        "- baseline: " + (f"{base[0]} @ {base[1]}" if base
                          else "none recorded yet (first grounding)"),
        *(_reground_delta_lines(base, repo, spec_dir) if base
          else _intent_seed_lines(spec_dir, repo)),
    ]


def input_payload_for(node: str, spec_dir: Path, repo: Path,
                      entry: specstate.TaskEntry | None,
                      diff_file: Path | None = None) -> str:
    """The filled input payload (SKILL.md § Spawn mechanics step 3): the
    doc-state facts each brief's `Input payload` section asks the
    orchestrator to embed — verbatim where the brief says verbatim. Every
    payload names the spec dir and carries the requirement list; the
    role-specific facts come first."""
    spec_text = read_doc(spec_dir / "spec.md") or ""
    test_text = read_doc(spec_dir / "test.md") or ""
    fr_lines = [f"   {b}" for b in fr_entries(spec_text)]
    if not fr_lines:
        fr_lines = ["   (no FR/NFR-### entries in spec.md)"]
    work_type_line = (
        f"- Work type: `**Type**: {specstate.spec_type(spec_text)}` "
        "(spec.md header; absent reads feature)")
    constitution = spec_dir.parent / "CONSTITUTION.md"
    # the template's example articles are not rules: an agent is pointed
    # at the constitution only once check.py reads it as filled
    constitution_filled = constitution_status(repo)[0]
    constitution_gap = ([] if constitution_filled else [
        "- specs/CONSTITUTION.md: absent or still the unfilled template "
        "— it binds nothing yet. Say so in your digest; never apply its "
        "placeholder articles"])
    constitution_read = ("specs/CONSTITUTION.md under the spec dir's "
                         "parent" if constitution_filled else None)

    if node == "intent":
        intent_path = spec_dir / "intent.md"
        problem = spec_section(read_doc(intent_path) or "", "Problem")
        idea = re.sub(r"<!--.*?-->", "", problem or "", flags=re.S).strip()
        lines = [
            f"- spec_dir: {spec_dir}",
            f"- repo root: {repo}",
            f"- intent.md: {intent_path} — the session's file: record "
            "your facts and candidate gaps in it, never rewrite its "
            "Problem, Audience, or FR seeds",
        ]
        if idea and not is_unfilled(idea):
            lines += ["- The idea (intent.md § Problem, verbatim):",
                      _indent(idea)]
        else:
            lines += ["- The idea: NOT RECORDED — intent.md § Problem is "
                      "still the template. Probe nothing; return `digest: "
                      "intent blocked — no idea in § Problem` so the "
                      "session writes the user's ask there first."]
        brainstorm = (repo / specstate.HANDOFF_DIR
                      / f"{spec_dir.name}.md")
        if brainstorm.exists():
            lines.append(f"- Brainstorm handoff: {brainstorm}")
        return "\n".join(lines)

    if node == "constitution":
        lines = [
            f"- repo root: {repo}",
            f"- specs/CONSTITUTION.md: {constitution} — "
            + ("filled: propose amendments only, for conventions its "
               "articles do not cover yet" if constitution_filled
               else "absent or still the unfilled template: its example "
                    "articles are not rules"),
        ]
        if (spec_dir / "intent.md").exists():
            lines.append(f"- Stated bounds: {spec_dir / 'intent.md'} "
                         "§ Constraints")
        return "\n".join(lines)

    if node == "research":
        what = spec_section(spec_text, "What")
        why = spec_section(spec_text, "Why")
        questions = research_questions(
            read_doc(spec_dir / "tech-spec.md") or "")
        lines = [f"- spec_dir: {spec_dir}"]
        if what:
            lines += ["- What (verbatim):", _indent(what)]
        if why:
            lines += ["- Why (verbatim):", _indent(why)]
        if questions:
            lines += ["- Research questions (recorded in tech-spec.md § "
                      "Questions & options):"]
            lines += [_indent(q) for q in questions]
        else:
            lines += ["- Research questions: none recorded in tech-spec.md "
                      "§ Questions & options — derive 3-6 from the open "
                      "technical choices in the requirement list below; the "
                      "orchestrator writes them into the section and "
                      "confirms them."]
        lines += ["- Your findings land in that section — under "
                  "### Questions (one block per question), with the open "
                  "choices' candidates and one-line trade-offs under "
                  "### Options summary; never a separate research.md file."]
        lines += ["- Requirement list (verbatim):", *fr_lines]
        return "\n".join(lines)

    if node == "plan":
        lines = [
            f"- spec_dir: {spec_dir} (read spec.md and tech-spec.md "
            "yourself — § Code state is the code-state truth)",
            "- Team context: none recorded — assume solo, PR-per-milestone "
            "unless the spawn digest says otherwise",
        ]
    elif node == "tech":
        lines = [
            f"- spec_dir: {spec_dir} (read spec.md and your file's own "
            "§ Questions & options — the research record — yourself; "
            "intent.md § Constraints when present)",
            *grounding_lines(spec_dir, repo),
            "- Architecture constraints: "
            + (f"specs/CONSTITUTION.md at {constitution}"
               if constitution_filled
               else "none recorded (specs/CONSTITUTION.md is absent or "
                    "unfilled)"),
        ]
    elif node == "qa":
        lines = [
            f"- spec_dir: {spec_dir}",
            "- Read spec.md ONLY — never tech-spec.md, plan.md, or the "
            "code (implementation blindness)",
        ]
    elif node == "tasks":
        lines = [f"- spec_dir: {spec_dir} (read spec.md, plan.md, "
                 "tech-spec.md, test.md yourself — every TC gets an "
                 "owning task's `Proves:` line or a regression-guard "
                 "line)"]
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
            + (str(constitution) if constitution_filled
               else "absent or unfilled — it binds nothing yet; report "
                    "that in your digest"),
        ]
        if specstate.spec_tier(spec_text) == "tiny":
            lines.append("- Acceptance commands: the entry's `Accept:` "
                         "line(s) above — tiny tier has no test.md")
        else:
            lines.append(
                "- Acceptance commands (always for code tasks — run them "
                "while implementing; the pre-tick proof pass re-runs them):")
            lines += [_indent(c)
                      for c in acceptance_for(entry.block, test_text)]
        if entry.fix_round:
            lines += fix_evidence_lines(spec_dir, entry)
    elif node == "design":
        lines = [
            f"- spec_dir: {spec_dir} (read spec.md and tech-spec.md "
            "§ Questions & options — the research record — yourself; "
            "intent.md § Constraints when present)",
            *grounding_lines(spec_dir, repo),
            "- Effort: standard — ONE spawn authors "
            "tech-spec.md → plan.md in that order. task.md is NOT yours "
            "here: it waits for test.md and comes as its own spawn. The "
            "tech → plan stretch is collapsed at this effort; check.py, "
            "the approve gate, and qa independence are not.",
            "- Team context: none recorded — assume solo, PR-per-milestone "
            "unless the spawn digest says otherwise",
            "- Architecture constraints: "
            + (f"specs/CONSTITUTION.md at {constitution}"
               if constitution_filled
               else "none recorded (specs/CONSTITUTION.md is absent or "
                    "unfilled)"),
            "- test.md belongs to the parallel qa spawn — NEVER write "
            "it; qa stays implementation-blind at every tier",
        ]
    elif node == "approve":
        lines = [
            f"- spec_dir: {spec_dir}",
            "- Mode: contract — the pre-approve review of the docset "
            "(findings only, edit nothing)",
        ]
        if specstate.spec_tier(spec_text) == "tiny":
            lines.append(
                "- Tier: tiny — the one-file contract. Read spec.md only "
                "(its § Tasks holds the task list; each task's Accept "
                "line is its evidence)"
                + (f" plus {constitution_read}" if constitution_read
                   else "")
                + ". No plan.md, tech-spec.md, "
                "task.md, or test.md exists at this tier — "
                "their absence is never a finding")
            lines += constitution_gap
        else:
            lines += [
                "- Read spec.md, plan.md, tech-spec.md, task.md, and "
                "test.md under the spec dir"
                + (f", plus {constitution_read}" if constitution_read
                   else "")
                + "; tech-spec.md § Code state is the evidence baseline",
                *constitution_gap,
                f"- Docset fingerprint: {freeze.docset_fingerprint(spec_dir)}"
                " — save this payload for the owner: they run `freeze.py "
                "<spec-dir> --approve --review <payload-path>` in their "
                "own terminal; the freeze refuses a review of any other "
                "docset",
            ]
    elif node == "tick-commit":
        # The auditor's diff anchor: the approval freeze's Approved-at
        # commit — a real SHA read from approvals/approval.md, never raw
        # marker text, because it is interpolated into a git command
        # (`HEAD~2;id`-shaped text must not survive). No approval SHA (a
        # non-git freeze's dash — or no freeze at all) leaves no diff
        # base: anchor the review on every task's intended-files union
        # instead, never raw HEAD. The auditor holds no Bash, so the
        # diff reaches it as a file the emit wrote.
        base = specstate.approval_sha(spec_dir)
        base_line = (
            f"- Base: the approval-freeze anchor `{base}`" if base else
            "- Base: none (non-git — anchor the review on every task's "
            "intended-files union instead)")
        lines = [
            f"- spec_dir: {spec_dir}",
            "- Mode: implementation-diff — the pre-tick implementation "
            "review (findings only, edit nothing)",
            base_line,
        ]
        if base and diff_file:
            lines.append(
                f"- The complete final diff: {diff_file} — `git diff "
                f"{base}` (tracked changes since base), written beside "
                "this payload. Its header lists the untracked files the "
                "diff omits: Read each of those in full")
        elif base:
            lines.append(
                f"- The final diff: unavailable (`git diff {base}` could "
                f"not be written from {repo}) — say so in your digest "
                "and anchor the review on every task's intended-files "
                "union instead")
        lines += [
            "- Plan-side truth: read task.md, tech-spec.md (its § Code "
            "state included), and test.md"
            + (f", and {constitution_read}" if constitution_read else ""),
            *constitution_gap,
            "- Review for semantic/security/rollback issues and wording "
            "drift",
        ]
    else:
        lines = [f"- spec_dir: {spec_dir}"]

    lines += [work_type_line,
              "- Requirement list (verbatim from spec.md):", *fr_lines]
    return "\n".join(lines)


def status_holder_text(spec_dir: Path) -> str:
    """The task list's text: task.md, or spec.md § Tasks at tiny tier."""
    spec_text = read_doc(spec_dir / "spec.md") or ""
    if specstate.spec_tier(spec_text) == "tiny":
        return specstate.tiny_task_text(spec_text) or ""
    return read_doc(spec_dir / "task.md") or ""


def fix_note_path(spec_dir: Path, entry: specstate.TaskEntry) -> Path:
    return spec_dir / "notes" / f"{entry.id}.md"


def round_sublines(entry: specstate.TaskEntry) -> list[str]:
    """The entry's fix/fixed note sub-lines, verbatim from its block."""
    return [ln for ln in entry.block.splitlines()
            if specstate.FIX_NOTE_OPEN.match(ln)
            or specstate.FIX_NOTE_CLOSED.match(ln)]


def fix_evidence_lines(spec_dir: Path,
                       entry: specstate.TaskEntry) -> list[str]:
    """The fix round's evidence: the entry's round sub-lines verbatim,
    then the notes/T###.md tail — the orchestrator records each round's
    digest beside the marker and its failing command and output in the
    note, so a fresh developer gets what a continued one would remember
    — then the rounds' arithmetic and, from the second round on, the
    same-signature rule."""
    head = f"- Fix round {entry.fix_round}"
    lines: list[str] = []
    rounds = round_sublines(entry)
    if rounds:
        lines += [f"{head} — round history (the entry's fix/fixed note "
                  "lines, verbatim):",
                  _indent("\n".join(rounds))]
    note = fix_note_path(spec_dir, entry)
    kept = (read_raw(note) or "").rstrip().splitlines()
    if not kept:
        lines.append(f"{head}: FAILURE EVIDENCE NOT RECORDED — {note} is "
                     "absent or empty. Do not implement from this payload: "
                     "return `blocked: no failure evidence` so the "
                     "orchestrator records the failing command and its "
                     "output there and re-emits")
        return lines
    cut = len(kept) - FIX_NOTE_LINE_CAP
    scope = (f"the last {FIX_NOTE_LINE_CAP} of {len(kept)} lines — Read "
             "the file for the rest" if cut > 0 else "verbatim")
    lines += [f"{head} — failure evidence and prior attempts ({note}, "
              f"{scope}):",
              _indent("\n".join(kept[-FIX_NOTE_LINE_CAP:]))]
    lines.append(ROUNDS_LINE.format(round=entry.fix_round))
    if entry.fix_round >= SAME_FAILURE_WATCH:
        rule = SAME_SIGNATURE_RULE
        sig, run = failure_run(spec_dir, entry.id)
        if sig and run >= SAME_FAILURE_WATCH:
            rule += SAME_SIGNATURE_FACT.format(command=sig, run=run)
        lines.append(rule)
    return lines


def frontier_payloads(state: dict, spec_dir: Path,
                      repo: Path, span: str = "full") -> list[dict]:
    """One record per payload this wave writes: one per frontier agent node,
    one per task in execute's file-disjoint wave (always named
    implementer-T###.md), plus — while the research-gate is
    undetermined — the researcher payload, and — while delivery is pending
    (execute done, delivery not yet recorded) — the implementation-diff
    reviewer payload (the instruments of a `run` decision and of the
    pre-tick review; --run still pauses at the tick-commit gate and never
    spawns them). At effort tier `standard` the tech → plan stretch
    collapses into ONE merged design payload — one spawn writes
    tech-spec.md then plan.md; qa stays its own implementation-blind
    spawn in the same wave, so test.md always comes from qa alone, and
    tasks follows as its own spawn once test.md exists. Docset,
    check.py, and the gates are unchanged.
    `span` filters the emitted payloads to the phase's nodes —
    a filter on payloads only, never on node states."""
    items: list[dict] = []
    merge_design = (
        state.get("effort") == "standard"
        and "tech" in state["frontier"]
        and state["nodes"]["plan"]["state"] != DONE
        and span_allows(span, "design"))
    for node in state["frontier"]:
        if node not in AGENT_BRIEFS:
            continue
        if not span_allows(span, node):
            continue
        if merge_design and node in ("plan", "tech"):
            continue
        role, brief, lens = AGENT_BRIEFS[node]
        if node == "execute":
            entries = specstate.task_entries(status_holder_text(spec_dir))
            runnables = [t for t in state["nodes"]["execute"].get("tasks", [])
                         if t["state"] == "runnable" and t["id"]
                         and not t["deferred"]]
            for t in runnables:
                entry = next((e for e in entries if e.id == t["id"]), None)
                items.append({
                    "node": node, "role": role, "brief": brief,
                    "lens": lens,
                    "filename": f"{role}-{t['id']}.md",
                    "entry": entry,
                })
        else:
            items.append({"node": node, "role": role, "brief": brief,
                          "lens": lens,
                          "filename": f"{role}.md", "entry": None})
    if merge_design:
        items.insert(0, {
            "node": "design", "role": "designer", "brief": None,
            "briefs": ["architect.md"],
            "lenses": [AGENT_BRIEFS[n][2] for n in ("tech", "plan")],
            "filename": "designer.md", "entry": None,
        })
    if (state["nodes"]["research-gate"]["state"] == UNDETERMINED
            and span_allows(span, "research")):
        items.append(repair_item("research"))
    if (state["nodes"]["approve"]["state"] == READY
            and span_allows(span, "approve")
            and repair_refusal("approve") is None):
        items.append(repair_item("approve"))
    if (state["nodes"]["execute"]["state"] == DONE
            and state["nodes"]["tick-commit"]["state"] != DONE
            and span_allows(span, "tick-commit")):
        items.append({"node": "tick-commit", "role": "reviewer",
                      "brief": "auditor.md",
                      "filename": "reviewer-diff.md", "entry": None})
    return items


def repair_item(node: str) -> dict:
    """The single-role payload record for one repairable node — never
    the merged architect: a repair must not re-author the whole docset."""
    role, brief, lens = REPAIR_BRIEFS[node]
    filename = "reviewer-contract.md" if node == "approve" else f"{role}.md"
    return {"node": node, "role": role, "brief": brief, "lens": lens,
            "filename": filename, "entry": None}


def repair_refusal(node: str) -> str | None:
    """Why this package cannot emit the node's payload, or None. Each
    skill ships only its own span's briefs and lens sections, so a node
    owned by a sibling skill has nothing to carry here."""
    _role, brief, lens = REPAIR_BRIEFS[node]
    if read_raw(SKILL_DIR / "agents" / brief) is None:
        missing = f"agents/{brief}"
    elif (node == "approve"
          and read_raw(SKILL_DIR / "agents" / AUTHORING_BRIEF) is None):
        missing = (f"agents/{AUTHORING_BRIEF} (the contract review is "
                   "the authoring package's)")
    elif brief not in LENSLESS_BRIEFS and lens_section(lens) is None:
        missing = f"the {lens} lens (protocol/lenses.md)"
    else:
        return None
    owner = "/spec-define" if node == "intent" else "/spec-design"
    return (f"--repair {node}: this package ({SKILL_NAME}) does not ship "
            f"{missing} — run the repair from {owner}")


def agent_type(item: dict) -> str | None:
    """The harness agent type the payload's brief registers as — its
    frontmatter `name:` — so the spawner need not map roles to types."""
    brief = item.get("brief") or (item.get("briefs") or [None])[0]
    raw = read_raw(SKILL_DIR / "agents" / brief) if brief else None
    front = FRONTMATTER.match(raw or "")
    name = re.search(r"^name:\s*(\S+)", front.group(0), re.M) if front else None
    return name.group(1) if name else None


def brief_model(item: dict) -> str | None:
    """The `model:` the payload's brief frontmatter names — `inherit`
    when it names none; None when no brief can be read."""
    brief = item.get("brief") or (item.get("briefs") or [None])[0]
    return specstate.brief_model(SKILL_DIR / "agents" / brief) if brief \
        else None


def model_step(item: dict) -> bool:
    """Whether this implementer payload's open fix round is the one that
    runs a model step above the developer brief's model."""
    entry = item.get("entry")
    return (item["node"] == "execute" and entry is not None
            and entry.fix_round == MODEL_STEP_ROUND)


# What `{model}` carries on the model-step round: the brief's model with
# the step's suffix, since the kit names no model id and each harness
# resolves the step its own way — the runner's to resolve.
MODEL_STEP_SUFFIX = "+1"


def payload_model(item: dict) -> str:
    """What `{model}` takes for a payload: the brief's model, and on the
    model-step round the same one step up."""
    model = brief_model(item) or specstate.INHERIT_MODEL
    return model + MODEL_STEP_SUFFIX if model_step(item) else model


class WrittenPayload(NamedTuple):
    """A payload file the emit wrote: its path, the spawn's role and
    node, and what `{model}` takes for it."""
    path: Path
    role: str
    node: str
    model: str


def write_review_diff(spec_dir: Path, repo: Path, target: Path) -> Path | None:
    """Write the implementation review's diff beside its payload: `git
    diff <approval base>` under a header naming the untracked files git
    leaves out of it. None when there is no base or git cannot answer."""
    base = specstate.approval_sha(spec_dir)
    if not base:
        return None
    try:
        diff = subprocess.run(
            ["git", "-C", str(repo), "diff", base],
            capture_output=True, text=True, timeout=120)
        others = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--others",
             "--exclude-standard"],
            capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if diff.returncode != 0 or others.returncode != 0:
        return None
    derived = [target.resolve(), (spec_dir / "spawns").resolve()]
    untracked = [
        rel for rel in others.stdout.splitlines()
        if rel.strip() and not any(
            root == (repo / rel).resolve() or root in (repo / rel).resolve().parents
            for root in derived)]
    header = [f"# Final diff for the implementation review — base {base}",
              "# Untracked files (absent from the diff below — Read each "
              "in full):"]
    header += [f"#   {rel}" for rel in untracked] or ["#   (none)"]
    header.append(f"# ---- git diff {base} ----")
    target.mkdir(parents=True, exist_ok=True)
    path = target / "reviewer-diff.patch"
    path.write_text("\n".join(header) + "\n" + diff.stdout,
                    encoding="utf-8")
    return path


def stale_payloads(target: Path) -> list[Path]:
    """Kit-written payload files an earlier emit left in the wave dir.
    Execute waves share one dir until the delivery ticks, so without
    this a fix-round emit sits beside payloads of tasks already landed.
    Matched by the kit's own file names only — anything else there is
    not ours to delete."""
    roles = {role for role, _brief, _lens in REPAIR_BRIEFS.values()}
    names = {f"{role}.md" for role in roles} | {
        "designer.md", "reviewer-contract.md", "reviewer-diff.md",
        "reviewer-diff.patch"}
    per_task = re.compile(r"implementer(?:-T\d{3})?\.md\Z")
    try:
        return sorted(f for f in target.iterdir() if f.is_file()
                      and (f.name in names or per_task.match(f.name)))
    except OSError:
        return []


def lens_section(lens: str) -> str | None:
    """The `## Lens: <name>` section from protocol/lenses.md, verbatim:
    the archetype's specialization riding the payload."""
    raw = read_raw(SKILL_DIR / "protocol" / "lenses.md")
    if raw is None:
        return None
    marker = f"## Lens: {lens}"
    start = raw.find(marker)
    if start < 0:
        return None
    end = raw.find("\n## ", start + len(marker))
    return raw[start:end if end >= 0 else len(raw)].rstrip() + "\n"


def protocol_for(brief_body: str) -> tuple[str | None, list[str]]:
    """(shared-protocol.md for this brief, the section titles left out):
    a `## ` protocol section whose title the brief already carries as a
    heading is dropped, so no rule reaches one agent twice."""
    raw = read_raw(SKILL_DIR / "protocol" / "shared-protocol.md")
    if raw is None:
        return None, []
    carried = set(re.findall(r"^#{2,4}\s+(.+?)\s*$", brief_body, re.M))
    kept: list[str] = []
    dropped: list[str] = []
    for section in re.split(r"^(?=## )", raw, flags=re.M):
        title = section[3:].split("\n", 1)[0].strip()
        if section.startswith("## ") and title in carried:
            dropped.append(title)
        else:
            kept.append(section)
    return "".join(kept), dropped


def build_payload(item: dict, spec_dir: Path, repo: Path, wave: int,
                  native: bool = False,
                  worktree: Path | None = None) -> str | None:
    """One self-contained spawn payload: header (spec_dir / repo /
    skill_dir, plus the `Model:` line on the fix round that steps up the
    model), then the capability handshake's `tools:` ask — the first
    instruction of every payload — + filled input payload + the
    frontmatter-stripped brief body
    byte-verbatim + the carried lens sections from `protocol/lenses.md` +
    `protocol/shared-protocol.md` — except the auditor, the one
    exempt role (its brief states it needs no shared protocol). A merged-design
    item carries the architect archetype once with its two lens
    sections in authoring order and the protocol once. `native` is for a
    harness that registers this package's agents: the brief is already
    that agent type's system prompt, so the payload names the type and
    carries the inputs, lenses, and protocol only — except on the
    model-step round, whose payload keeps the brief for a harness that
    cannot override the registered type's model. `worktree`, when given,
    is the isolated tree the payload names as its repo — every
    repo-relative path in it — under a line making it the developer's
    only working tree (spec-build D-058)."""
    if item.get("briefs") is not None:
        bodies = []
        for bf in item["briefs"]:
            raw = read_raw(SKILL_DIR / "agents" / bf)
            if raw is None:
                return None
            bodies.append(f"### agents/{bf} (body; frontmatter stripped)\n\n"
                          + strip_frontmatter(raw))
        brief_title = ("## Briefs — the architect archetype "
                       "(body; frontmatter stripped)")
        brief_body = "\n\n".join(bodies)
    else:
        brief_raw = read_raw(SKILL_DIR / "agents" / item["brief"])
        if brief_raw is None:
            return None
        brief_title = (f"## Brief — agents/{item['brief']} "
                       "(body; frontmatter stripped)")
        brief_body = strip_frontmatter(brief_raw)
    protocol, omitted = protocol_for(brief_body)
    registered = agent_type(item) if native else None
    step_up = model_step(item)
    if registered and not step_up:
        brief_title = "## Brief — not embedded"
        brief_body = (
            f"Spawn this payload as agent type `{registered}`: that "
            "registered agent's definition is the brief. On a harness "
            "without it, re-emit without --native-agents for the "
            "self-contained form.\n")
    elif registered:
        brief_body = (NATIVE_MODEL_STEP_NOTE.format(
            round=MODEL_STEP_ROUND, type=registered) + brief_body)
    main_tree, repo = repo, (worktree or repo)
    header = [f"- spec_dir: {spec_dir}", f"- repo: {repo}"]
    if worktree is not None:
        header.append(ISOLATED_WORKTREE_LINE.format(
            path=worktree, repo=main_tree, spec_dir=spec_dir))
    header.append(f"- skill_dir: {SKILL_DIR}")
    if step_up:
        header.append(MODEL_STEP_LINE)
    parts = [
        f"# Spawn payload — {item['role']} · node {item['node']} · "
        f"wave {wave}",
        "",
        "Generated by `scripts/graph.py --emit-spawns` from doc state "
        "alone. Derived artifact: regenerate-only — safe to delete, never "
        "read by check.py, never status.",
        "",
        *header,
        "",
        TOOLS_ASK,
        "",
        "## Input payload (filled from doc state)",
        "",
        input_payload_for(item["node"], spec_dir, repo, item["entry"],
                          item.get("diff_file")),
        "",
        brief_title,
        "",
        brief_body,
    ]
    for lens in item.get("lenses") or ([item["lens"]] if item.get("lens") else []):
        section = lens_section(lens)
        # qa/build carry no lens section — their archetypes ARE the
        # whole contract; the analyst/architect lenses must exist
        # (test_graph pins the set).
        if section is not None:
            parts += ["",
                      f"## Carried lens — {lens} (from protocol/lenses.md, "
                      "verbatim)",
                      "",
                      section]
    if protocol is not None and item["role"] != "reviewer":
        scope = ("verbatim" if not omitted else
                 "verbatim, less what your brief already carries: § "
                 + ", § ".join(omitted))
        parts += ["",
                  f"## Shared protocol — protocol/shared-protocol.md ({scope})",
                  "",
                  protocol]
    if digest_capable(item):
        stem = Path(item["filename"]).stem
        parts += ["",
                  "## Digest file",
                  "",
                  f"Write your digest, exactly as returned, to "
                  f"`{spec_dir}/digests/wave-{wave}/{stem}.md` as your "
                  "final action — it survives whatever happens to this "
                  "session, and the orchestrator lands, releases and "
                  "resumes from that file (spec-build D-040)."]
    return "\n".join(parts)


# The write-capable archetypes (spec-build D-040): developer, analyst,
# architect, tester — the roles whose digest is evidence worth a file.
# The read-only roles (auditor/reviewer, panelist, integrator,
# release-manager) keep conversation-only digests: adding a write tool
# to them would weaken the guarantee that they write nothing.
DIGEST_CAPABLE_BRIEFS = frozenset(
    {"analyst.md", "architect.md", "tester.md", "developer.md"})


def digest_capable(item: dict) -> bool:
    """True when the payload's role may write its digest file."""
    brief = item.get("brief") or next(iter(item.get("briefs") or []), None)
    return brief in DIGEST_CAPABLE_BRIEFS


def isolate_wave(state: dict, spec_dir: Path, repo: Path,
                 items: list[dict], plan_only: bool = False
                 ) -> dict[str, Path]:
    """The worktree each implementer payload of this wave works in, by
    task id (spec-build D-058). The worktrees of tasks no longer open
    are removed first; then a payload's task gets a worktree created, or
    its existing one rebuilt from the current tree when nothing was ever
    done in it — a task re-emitted after a deferral starts from
    everything landed since — or kept as it stands when it holds work,
    since a fix round continues there. `plan_only` prints what would
    happen and touches nothing. A WorktreeError is the caller's: it
    leaves before any payload of the wave is written."""
    entries = specstate.task_entries(status_holder_text(spec_dir))
    open_ids = {e.id for e in entries if e.id and not (
        e.done or e.struck or e.implemented)}
    for tid, path in specstate.worktrees_present(repo, spec_dir.name).items():
        if tid in open_ids:
            continue
        why = None if plan_only else specstate.worktree_remove(repo, path)
        verb = ("would remove" if plan_only else
                "removed" if why is None else "NOT removed")
        print(f"   worktree: {verb} {path} ({tid} is no longer open)"
              + (f" — {why}" if why else ""))
    trees: dict[str, Path] = {}
    for item in items:
        entry = item.get("entry")
        if item["node"] != "execute" or entry is None:
            continue
        path = specstate.worktree_path(repo, spec_dir.name, entry.id)
        if path.exists() and specstate.worktree_untouched(path):
            if plan_only:
                print(f"   would refresh worktree: {path} (clean — would "
                      "be rebuilt from the current tree)")
            else:
                specstate.worktree_refresh(repo, path)
                print(f"   refreshed worktree: {path} (clean — rebuilt "
                      "from the current tree)")
            trees[entry.id] = path
            continue
        if not path.exists() and not plan_only:
            specstate.worktree_create(repo, path)
            what = "created — a detached snapshot of the main tree"
        elif not path.exists():
            what = "would create — a detached snapshot of the main tree"
        else:
            what = ("kept — it holds uncommitted work; the round "
                    "continues there")
        print(f"   worktree: {what}: {path}")
        trees[entry.id] = path
    return trees


def worktree_lines(state: dict, repo: Path) -> list[str]:
    """The isolated worktrees of this spec on disk, each with what it
    owes: an open task's is the tree its work is written in — an
    orphaned claim is resumed from that path — and one whose task is no
    longer open is removable."""
    present = specstate.worktrees_present(repo, Path(state["spec_dir"]).name)
    if not present:
        return []
    tasks = {t["id"]: t for t in state["nodes"]["execute"].get("tasks") or ()}
    lines = ["  isolated worktrees (the next emit with --isolate worktree "
             "removes the ones no longer open):"]
    for tid, path in sorted(present.items()):
        task = tasks.get(tid)
        if task is None or task["state"] in ("ticked", "struck",
                                             "implemented"):
            lines.append(f"    {tid}  {path} — no longer open: removable")
        else:
            lines.append(
                f"    {tid}  {path} — {task['state']}: the tree the "
                "task's work is written in — mark.py land merges its "
                "delta into the main tree, mark.py release discards it; "
                "an orphaned claim is resumed from this path")
    return lines


def write_wave_payloads(state: dict, spec_dir: Path, repo: Path,
                        wave_dir: Path | None,
                        repair: str | None = None,
                        span: str = "full",
                        native: bool = False,
                        run_id: str | None = None,
                        harness: str = specstate.UNKNOWN_HARNESS,
                        isolate: bool = False,
                        plan_only: bool = False
                        ) -> list[WrittenPayload]:
    """Write the wave's payloads; returns one WrittenPayload per file.
    `repair` names one agent node and emits that node's payload ALONE,
    whether or not it is in the frontier (--emit-spawns --repair NODE,
    the single-agent repair-run instrument — e.g. a stale-Baseline
    converge re-ground, whose payload carries the DELTA RE-GROUND
    block). `span` rides through to frontier_payloads; the repair item
    is the orchestrator's explicit instrument, so it bypasses the span
    filter. A wave emit first clears the kit's earlier payloads from the
    wave dir, so the dir holds exactly this wave; a repair emit adds its
    one file and clears nothing (a wave may be in flight beside it).
    `run_id` only shapes the printed next step: an execute wave's last
    line names the exact mark.py claim command, so the next move cannot
    be missed (spec-build D-039). Every payload written is one `wave`
    row in the spec's run ledger — the request the digest file that
    answers it is later joined to — with `harness` as it was passed.
    `isolate` gives every implementer payload its own worktree and makes
    it the payload's repo (isolate_wave, spec-build D-058); `plan_only`
    prints that step and does none of it."""
    wave = wave_number(state)
    target = Path(wave_dir) if wave_dir else (
        spec_dir / "spawns" / f"wave-{wave}")
    written: list[WrittenPayload] = []
    rows: list[dict] = []
    try:
        fingerprint = freeze.docset_fingerprint(spec_dir)
    except OSError:
        fingerprint = None
    items = ([repair_item(repair)] if repair else
             frontier_payloads(state, spec_dir, repo, span=span))
    worktrees: dict[str, Path] = {}
    if isolate:
        # a package that ships no developer brief writes no implementer
        # payload (the skip below): it builds no worktree either
        worktrees = isolate_wave(state, spec_dir, repo, [
            item for item in items if item["node"] != "execute" or read_raw(
                SKILL_DIR / "agents" / item["brief"]) is not None], plan_only)
    if not repair:
        for stale in stale_payloads(target):
            stale.unlink(missing_ok=True)
    for item in items:
        if item["node"] == "tick-commit":
            item = {**item,
                    "diff_file": write_review_diff(spec_dir, repo, target)}
        text = build_payload(
            item, spec_dir, repo, wave, native,
            worktrees.get(item["entry"].id) if item["node"] == "execute"
            and item.get("entry") else None)
        if text is None:
            # build_payload's None does not say which of a merged item's
            # briefs was unreadable (its brief field is None) — re-resolve
            # so the skip line names the real file
            names = item.get("briefs") or [item["brief"]]
            missing = next((b for b in names
                            if read_raw(SKILL_DIR / "agents" / b) is None),
                           names[0])
            print(f"   payload: SKIPPED (brief not found: "
                  f"agents/{missing})")
            continue
        target.mkdir(parents=True, exist_ok=True)
        path = target / item["filename"]
        path.write_text(text, encoding="utf-8")
        written.append(WrittenPayload(path, item["role"], item["node"],
                                      payload_model(item)))
        rows.append(specstate.ledger_row(
            SKILL_NAME, "wave", run=run_id, wave=wave, node=item["node"],
            role=item["role"],
            lens=item.get("lens") or ", ".join(item.get("lenses") or [])
            or None,
            stem=path.stem, payload=specstate.file_sha(path),
            input=fingerprint, model=brief_model(item), harness=harness))
        agent = agent_type(item)
        print(f"   payload: {path} (role: {item['role']}, "
              f"node: {item['node']})"
              + (f" — agent type {agent}" if agent else "")
              + (f" — fix round {MODEL_STEP_ROUND}: runs one model step "
                 "above the developer brief's model"
                 if model_step(item) else ""))
        entry = item.get("entry")
        if (entry is not None and entry.fix_round
                and not fix_note_path(spec_dir, entry).exists()):
            print(f"   evidence missing: {entry.id} fix round "
                  f"{entry.fix_round} — record the failing command and "
                  f"its output in {fix_note_path(spec_dir, entry)}, then "
                  "re-emit before spawning")
    specstate.ledger_event(spec_dir, *rows)
    if not repair and span_allows(span, "execute"):
        for line in execute_holds(state):
            print(line)
    if any(payload.node == "execute" for payload in written):
        claim = (f"python3 {SKILL_DIR / 'scripts' / 'mark.py'} claim "
                 f"{spec_dir} --wave {target}"
                 + (f" --run-id {run_id}" if run_id else "")
                 + (f" --harness {harness}"
                    if harness != specstate.UNKNOWN_HARNESS else ""))
        print(f"   next: {claim}")
        if state.get("mode") == "fast":
            print("   Mode: fast — claim, then implement each "
                  "implementer-T### payload YOURSELF in this session, in "
                  "task-id order, exactly as its developer brief says "
                  "(digest file included); spawn no developer")
        else:
            print("   (claim --wave claims exactly this wave's "
                  "implementer-T### files — run it before spawning them)")
            if state.get("mode_note"):
                print(f"   {state['mode_note']}")
    return written


def substitute(template: str, prompt_file: Path, role: str,
               spec_dir: Path, skill_dir: Path, model: str) -> str:
    """Placeholders substituted verbatim — no shell quoting, no residual
    braces ({prompt_file}/{role}/{spec_dir}/{skill_dir}/{model})."""
    return (template.replace("{prompt_file}", str(prompt_file))
            .replace("{role}", role)
            .replace("{spec_dir}", str(spec_dir))
            .replace("{skill_dir}", str(skill_dir))
            .replace("{model}", model))


def digest_holds(spec_dir: Path) -> dict[str, dict]:
    """`{node: sighting}` for each authoring node whose newest refused
    digest holds it; of a node's stems, the refusal from the highest
    wave is the one that names it."""
    refused = specstate.refused_digests(spec_dir, [
        stem for stems in NODE_DIGEST_STEMS.values() for stem in stems])
    return {
        node: max((refused[stem] for stem in stems if stem in refused),
                  key=lambda seen: seen["wave"])
        for node, stems in NODE_DIGEST_STEMS.items()
        if any(stem in refused for stem in stems)}


def sweep(spec_dir: Path) -> None:
    """The provenance sweep before state is read: each malformed file it
    left in place is named."""
    for seen in specstate.sweep_digests(spec_dir, SKILL_NAME):
        print(f"digest: {specstate.digest_refusal_line(seen)}",
              file=sys.stderr)


def find_pause(state: dict) -> tuple[str, str] | None:
    """The first judgment node --run must stop at, as (node, what is needed).
    The human gates (clarify, approve, tick-commit) and the
    orchestrator's research-gate are never auto-satisfied. Order is the
    canonical node order; at most one applies per state."""
    n = state["nodes"]
    if n["clarify"]["state"] == READY:
        return "clarify", n["clarify"]["reason"]
    if n["research-gate"]["state"] == UNDETERMINED:
        return "research-gate", (
            n["research-gate"]["reason"]
            + " — run: `--emit-spawns --repair research` writes the "
            "researcher payload alone")
    if n["approve"]["state"] == READY:
        return "approve", (n["approve"]["reason"]
                           + " — "
                           + freeze.approval_steps(Path(state["spec_dir"]))
                           + "; then wait — set spec.md Status: approved "
                           "only once `freeze.py <spec-dir> --verify` "
                           "passes on the owner's record")
    if (n["execute"]["state"] == DONE
            and n["tick-commit"]["state"] != DONE):
        commit_note = ("make implementation commit C1, then commit C2 "
                       "— C2 carries the delivery record (`Delivered: "
                       "commit @ <C1>`), spec.md Status: done, and the "
                       "INDEX.md repoint" if state["git"]["available"]
                       else "commit SKIPPED (not a git repo) — set spec.md "
                            "Status: done and repoint INDEX.md")
        return "tick-commit", ("prove and tick: run `audit.py proofs "
                               "<spec-dir> --run` + regression so every "
                               "tick's proof note is fresh evidence, run "
                               "the review instruments, and present the "
                               "delivery summary; only on the user's "
                               "explicit yes tick every task `- [x]` with "
                               "its proof note, recompute the burndown "
                               "(`check.py --fix-burndown`), then "
                               + commit_note)
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


def launch_check(state: dict, spec_dir: Path, repo: Path) -> dict:
    """--launch-check: should the dynamic workflow be launched for
    this doc state, or is the span light enough to run inline? The
    workflow's value is the multi-wave loop with parallel fan-out; a launch
    on a light state reads state once and stops seconds later, deciding
    nothing (on Claude Code that single fetch is a whole probe agent). The
    same doc-state oracle as every other mode — find_pause first (a pending
    human gate can never be worked past by launching), then the payload
    count from frontier_payloads (read-only: nothing is written). Only
    `wave` — a multi-payload wave, any execute span, or the merged design
    payload (briefs authoring the docset) — says launch."""
    n = state["nodes"]
    advisory = {"spec_dir": str(spec_dir),
                "launch_workflow": False, "gate": None,
                "frontier_agents": [x for x in state["frontier"]
                                    if x in AGENT_BRIEFS], "payloads": 0}
    pause = find_pause(state)
    if pause is not None:
        gate, need = pause
        how = ("your judgment, made inline" if gate == "research-gate"
               else "answer the gate inline with the user")
        return {**advisory, "weight": "gate", "gate": gate,
                "reason": f"{need} — {how}; a workflow launch cannot "
                          "work past a gate"}
    if not advisory["frontier_agents"]:
        if n["archive"]["state"] == READY:
            weight, reason = ("complete", "archive-ready — run "
                              f"scripts/archive.sh {Path(spec_dir).name} "
                              "inline")
        elif all(n[x]["state"] == DONE for x in NODES):
            weight, reason = "complete", "every node done — nothing to run"
        else:
            blocked = "; ".join(
                f"{x}: {n[x]['reason']}" for x in NODES
                if n[x]["state"] == BLOCKED)
            weight, reason = ("held", "no agent node runnable — unblock "
                              f"inline first: {blocked}")
        return {**advisory, "weight": weight, "reason": reason}
    payloads = frontier_payloads(state, spec_dir, repo)
    advisory["payloads"] = len(payloads)
    if not payloads:
        return {**advisory, "weight": "held",
                "reason": "execute is ready but no task can be spawned — "
                          "settle the claimed, blocked, or at-cap tasks "
                          "inline first (--explain execute)"}
    if len(payloads) == 1 and payloads[0]["node"] == "design":
        # the merged architect is one payload but not a light node: two
        # lenses + protocol authoring tech-spec and plan — the design
        # stretch stays a workflow wave, only collapsed to one spawn (qa
        # already done — its own payload rides alongside when it isn't)
        return {**advisory, "weight": "wave", "launch_workflow": True,
                "reason": "one merged design payload — two lenses "
                          "(tech/plan) authoring tech-spec and plan — "
                          "heavy span, launch a dynamic workflow"}
    if state.get("mode") == "fast" and all(
            x["node"] == "execute" for x in payloads):
        return {**advisory, "weight": "single",
                "reason": f"Mode: fast — {len(payloads)} task payload(s) "
                          "implemented inline by this session, no "
                          "developer spawn and no workflow launch"}
    if len(payloads) == 1 and payloads[0]["node"] != "execute":
        return {**advisory, "weight": "single",
                "reason": "one light doc node ("
                          f"{payloads[0]['node']}/{payloads[0]['role']}) — "
                          "run it inline: --emit-spawns + one spawn "
                          "(single-agent run mode)"}
    return {**advisory, "weight": "wave", "launch_workflow": True,
            "reason": f"{len(payloads)} payload(s) across "
                      f"{', '.join(advisory['frontier_agents'])} — heavy "
                      "span, launch a dynamic workflow"}


def span_stop(state: dict, span: str, waves_done: int) -> int:
    """Why a phase span with nothing runnable stopped, and its exit: the
    exit code and the stop reason the run ledger's `run_end` row
    carries. The
    handoff line is reserved for a span whose own gate is behind it
    (intent green; approve done) — a span that merely has nothing to run
    names what it is waiting on instead: a red intent names its own
    gate, never the spec draft behind it."""
    n = state["nodes"]
    name = Path(state["spec_dir"]).name
    frontier = ", ".join(state["frontier"]) or "empty"
    # a legacy docset (spec done, no intent.md) leaves intake nothing to do
    drained = {"intent": (n["intent"]["state"] == DONE
                          or (n["intent"]["state"] == SKIPPED
                              and n["spec"]["state"] == DONE)),
               "shape": n["approve"]["state"] == DONE}.get(span)
    rc = 0
    reason = "awaiting"
    if drained:
        reason = "drained"
        phase, command = SPAN_HANDOFF[span]
        print(f"span drained — {phase} handoff: continue with "
              f"`{command} {name}` (frontier: {frontier})")
    elif span == "intent" and n["intent"]["state"] == BLOCKED:
        print(f"AWAITING: intent: {n['intent']['reason']} (open markers: "
              "re-ask the user; stale baseline: `--emit-spawns --repair "
              "intent`) — spec.md waits on a green intent")
    elif n["spec"]["state"] == READY:
        print(f"AWAITING: {n['spec']['reason']}")
    elif span == "shape" and n["spec"]["state"] == BLOCKED:
        route = ("" if n["intent"]["state"] == DONE
                 else f" — route to `/spec-define {name}`")
        print(f"AWAITING: {n['spec']['reason']}{route}")
    elif span == "shape" and n["intent"]["state"] == READY:
        print("AWAITING: intent.md is still the unfilled template "
              f"— fill and gate it with `/spec-define {name}`")
    elif span == "intent" and n["intent"]["state"] == SKIPPED:
        print("AWAITING: no intent.md — copy templates/intent.md to "
              f"{Path(state['spec_dir']) / 'intent.md'} and record the "
              "idea in § Problem, then re-run")
    elif (span == "shape"
          and n["verify"].get("check_rc") not in (0, None)):
        print(f"verify RED — check.py exits {n['verify']['check_rc']}; "
              "fix the FAILs above, then re-run")
        rc, reason = 1, "verify_red"
    elif span == "execute":
        reason = "drained"
        print(f"span drained: no {span}-span agent node is runnable "
              f"(frontier: {frontier})")
    else:
        reason = "held"
        print(f"span held — no {span}-span agent node is runnable; the "
              "blocked nodes:")
        for node in NODES:
            if n[node]["state"] == BLOCKED:
                print(f"  {node}: {n[node]['reason']}")
        rc = 1
    _record(SKILL_NAME, "run_end", waves=waves_done, complete=False,
            span=span)
    return rc, reason


def _headless_execute_wave(spec_dir: Path, written: list[WrittenPayload],
                           runner: str, parallel: int,
                           run_id: str | None,
                           harness: str = specstate.UNKNOWN_HARNESS,
                           budget_spawns: int = specstate.BUDGET_SPAWNS,
                           budget_minutes: int = specstate.BUDGET_MINUTES) -> int | None:
    """One headless execute wave (spec-build D-041): mark.py claims the
    wave, the runner runs the payloads (batched --parallel at a time —
    schedule_wave already made the wave file-disjoint), then mark.py
    lands each task whose digest reports implemented. Returns None to
    continue the loop (every task landed), or an exit code to stop:
    RUNNER_FAILED_EXIT when the claim or a runner fails — a claim that
    refuses on a spent run budget (spec-build D-059) among them, never
    a deferred wave, which is exit 0 — 0 with AWAITING ORCHESTRATOR
    when any task is left claimed (blocked digest, no digest, red
    proofs) — fix rounds and adjudication stay with the orchestrator.
    The run's two budgets ride the claim command, so the claim counts
    against what the loop counted."""
    mark = SKILL_DIR / "scripts" / "mark.py"
    wave_dir = written[0].path.parent
    ids = sorted({payload.path.stem.replace("implementer-", "")
                  for payload in written if payload.node == "execute"})
    claim = [sys.executable, str(mark), "claim", str(spec_dir),
             "--wave", str(wave_dir)]
    if run_id:
        claim += ["--run-id", run_id]
    if harness != specstate.UNKNOWN_HARNESS:
        claim += ["--harness", harness]
    claim += ["--budget-spawns", str(budget_spawns),
              "--budget-minutes", str(budget_minutes)]
    print("   headless: mark.py claim")
    r = subprocess.run(claim, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        print(f"stopping: the wave's claim was refused (exit "
              f"{r.returncode}) — settle the tasks mark.py named, then "
              "re-run; no later wave starts")
        return RUNNER_FAILED_EXIT
    # a task another spec's claim held off was dropped by the claim
    # (mark.py prints it deferred): only what the claim took may run
    m = re.search(r"^claimed \d+: (.*)$", r.stdout, re.M)
    if m:
        ids = sorted(filter(None, m.group(1).split(", ")))
        written = [payload for payload in written if payload.node != "execute"
                   or payload.path.stem.replace("implementer-", "") in ids]
    if not ids or "nothing claimed" in r.stdout:
        return None
    this_run = run_id
    m = re.search(r"run id: (r-\S+)", r.stdout)
    if m:
        this_run = m.group(1)
        print(f"   headless: run id {this_run} (reused for this "
              "session's waves)")
    pending = list(written)
    failed: list[tuple[str, int]] = []
    while pending:
        batch, pending = pending[:parallel], pending[parallel:]
        procs = []
        for payload in batch:
            invocation = substitute(runner, payload.path, payload.role,
                                    spec_dir, SKILL_DIR, payload.model)
            print(f"   runner: {payload.role}: {invocation}")
            procs.append((subprocess.Popen(invocation, shell=True),
                          payload.role, invocation))
        for proc, role, invocation in procs:
            rc = proc.wait()
            print(f"   runner: {role}: {invocation} → exit {rc}")
            if rc != 0 and not failed:
                failed.append((role, rc))
    if failed:
        role, rc = failed[0]
        print(f"stopping: runner for role {role} exited {rc} — the "
              "wave's tasks stay CLAIMED; settle them "
              "(mark.py land on a green digest, or mark.py release), "
              "then re-run. No later wave starts.")
        return RUNNER_FAILED_EXIT
    print(f"   headless: landing {len(ids)} task(s)")
    held: list[str] = []
    for tid in ids:
        r = subprocess.run(
            [sys.executable, str(mark), "land", str(spec_dir), tid],
            capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stderr.write(r.stderr)
            held.append(tid)
    if held:
        print(f"AWAITING ORCHESTRATOR: execute — {len(held)} task(s) "
              "left CLAIMED (a blocked, malformed or missing digest, a "
              "failed capability handshake, or red proofs — mark.py's "
              "output above names each):")
        for tid in held:
            print(f"   held: {tid}")
        print("fix rounds and adjudication stay with you: settle each "
              "held task (land on a green digest, release and rule, or "
              "mark.py fail with the evidence), then re-run. A typed "
              "deviation names its route (D-043): scope: → widen "
              "Touches under the D-### and re-emit; spec-defect: → "
              "/spec-design — neither opens a fix round")
        return 0
    return None


def run_loop(spec_dir: Path, repo_override: str | None, runner: str,
             dry_run: bool, max_waves: int | None,
             wave_dir: str | None = None,
             span: str = "full", native: bool = False,
             run_id: str | None = None,
             parallel: int = 1,
             harness: str = specstate.UNKNOWN_HARNESS,
             isolate: bool = False,
             budget_spawns: int = specstate.BUDGET_SPAWNS,
             budget_minutes: int = specstate.BUDGET_MINUTES) -> int:
    """The auto-trigger loop (architecture §4.5): pause at every judgment
    node, run the mechanical verify directly, emit payloads for the ready
    agent wave, invoke the runner per payload — the first runner that exits
    nonzero or raises stops the loop with a role/node diagnostic and exit
    RUNNER_FAILED_EXIT, so no later wave starts — recompute, repeat until a
    gate, workflow completion, the --max-waves bound, or a wave that changed
    nothing. Payloads go to --wave-dir when given, otherwise the default
    <spec-dir>/spawns/wave-<N>/ (the same override --emit-spawns takes).
    The loop itself mutates no doc state; only the runner's own effects move
    the workflow, so human gates can never be auto-satisfied.
    `span` bounds the wave to the phase's frontier nodes: gates
    still pause (the intent span never decides research, so its
    gate is not the intent phase's to answer), a drained shape span stops
    at the approve handoff, and a span with nothing left to run stops
    through span_stop. The print runner executes nothing, so it stops
    after one emitted wave. A custom runner never invokes execute
    payloads DIRECTLY: where mark.py ships beside this script, the loop
    runs the wave headlessly — mark.py claims it, the runner runs the
    payloads (batched --parallel at a time), mark.py lands each task
    whose digest reports implemented, and the loop continues; any task
    left claimed stops the loop AWAITING ORCHESTRATOR (spec-build
    D-041). Without mark.py (this package ships none) the wave is
    refused with EXECUTE_RUNNER_REFUSED_EXIT before any subprocess
    starts (spec-build D-038 — only the orchestrator claims and lands
    tasks). The loop mutates doc state only through mark.py, the single
    marker writer. `run_id` stamps the printed claim command, marks
    this run's claims, and scopes orphan reports to other runs' claims;
    a generated one is reused across the session's waves.
    `parallel` batches the headless wave's runner subprocesses. The run
    opens and closes the spec's run ledger with a `run_start` and a
    `run_end` row carrying its stop reason; `harness` rides both and
    every `wave` row the loop writes. `isolate` hands each execute
    wave's payloads their own worktrees (spec-build D-058) — planned
    only under --dry-run. `budget_spawns` and `budget_minutes` are the
    run budgets (spec-build D-059, spec-design D-080): before every
    wave that would claim, the loop counts the spawns over this run
    and over the spec's whole ledger and the minutes over this run
    alone, and a spent one parks AWAITING HUMAN before the wave, exit
    0, the `run_end` row saying `run_budget`. A digest the sweep
    refuses holds its node; the loop stops before the wave after it,
    exit 0, the `run_end` row saying `digest_refused`. A wave holding
    the fix round that runs a model step needs a template with
    `{model}`: without it the loop stops before anything is claimed,
    exit 0, the row saying `model_step_refused`."""
    if run_id is None and runner != PRINT_RUNNER:
        import secrets
        run_id = f"r-{secrets.token_hex(2)}"
    specstate.ledger_event(spec_dir, specstate.ledger_row(
        SKILL_NAME, "run_start", run=run_id, harness=harness))
    rc, reason, gate = _run_loop(
        spec_dir, repo_override, runner, dry_run, max_waves, wave_dir,
        span, native, run_id, parallel, harness, isolate,
        budget_spawns, budget_minutes)
    specstate.ledger_event(spec_dir, specstate.ledger_row(
        SKILL_NAME, "run_end", run=run_id, node=gate, harness=harness,
        outcome=reason))
    return rc


def _run_loop(spec_dir: Path, repo_override: str | None, runner: str,
              dry_run: bool, max_waves: int | None,
              wave_dir: str | None, span: str, native: bool,
              run_id: str | None, parallel: int, harness: str,
              isolate: bool, budget_spawns: int,
              budget_minutes: int) -> tuple[int, str, str | None]:
    """The loop behind run_loop: its exit code, the stop reason the
    `run_end` row carries, and the gate it paused at (None elsewhere)."""
    waves_done = 0
    swept = False
    while True:
        # the invocation's own sweep ran before the loop; every later
        # wave boundary sweeps again, since digests land between waves
        if swept:
            sweep(Path(spec_dir))
        swept = True
        state = compute_state(spec_dir, repo_override, run_id)
        held = [(name, state["nodes"][name]["digest"]) for name in NODES
                if "digest" in state["nodes"][name]]
        if held:
            print("AWAITING ORCHESTRATOR: a refused digest holds "
                  + ", ".join(name for name, _ in held)
                  + " — the wave after it is not emitted:")
            for name, seen in held:
                print(f"   {name}: digest: "
                      f"{specstate.digest_refusal_line(seen)}")
            _record(SKILL_NAME, "gate_pause", node=held[0][0],
                    wave=waves_done + 1)
            return 0, "digest_refused", held[0][0]
        log_verify(state, repo_override)
        pause = find_pause(state)
        if pause and not (span == "intent" and pause[0] == "research-gate"):
            gate, need = pause
            if span == "shape" and gate == "approve":
                print(f"span drained — approve handoff: {need} — "
                      f"continue with `/spec-build {Path(spec_dir).name}` "
                      "once approved")
                _record(SKILL_NAME, "gate_pause", node=gate,
                        wave=waves_done + 1)
                return 0, "gate_pause", gate
            owner = "ORCHESTRATOR" if gate == "research-gate" else "HUMAN"
            print(f"AWAITING {owner}: {gate}: {need}")
            _record(SKILL_NAME, "gate_pause", node=gate,
                    wave=waves_done + 1)
            return 0, "gate_pause", gate
        frontier = state["frontier"]
        runnable = [x for x in frontier
                    if x in AGENT_BRIEFS and span_allows(span, x)]
        if not runnable:
            n = state["nodes"]
            if (span == "full" or n["archive"]["state"] == READY
                    or all(n[x]["state"] == DONE for x in NODES)):
                print_complete_or_held(state)
                _record(SKILL_NAME, "run_end", waves=waves_done,
                        complete=True)
                return 0, "complete", None
            rc, reason = span_stop(state, span, waves_done)
            return rc, reason, None
        repo = resolved_repo(Path(spec_dir), repo_override)
        payloads = (frontier_payloads(state, Path(spec_dir), repo, span=span)
                    if "execute" in runnable else [])
        if runnable == ["execute"] and not payloads:
            print_execute_held(state)
            _record(SKILL_NAME, "gate_pause", node="execute",
                    wave=waves_done + 1)
            return 0, "held", "execute"
        if any(item["node"] == "execute" for item in payloads):
            stop = specstate.budget_stop(spec_dir, run_id, budget_spawns,
                                         budget_minutes)
            if stop:
                print("\n".join(stop))
                return 0, "run_budget", None
        stepping = [item for item in payloads if model_step(item)]
        if (stepping and runner != PRINT_RUNNER and not dry_run
                and "{model}" not in runner):
            tasks = {t["id"]: t for t in
                     state["nodes"]["execute"].get("tasks") or ()}
            print("AWAITING ORCHESTRATOR: execute: the --runner template "
                  "names no {model} — "
                  + ", ".join(item["entry"].id for item in stepping)
                  + (" is" if len(stepping) == 1 else " are")
                  + f" at fix round {MODEL_STEP_ROUND}, the round that runs "
                  "one model step above the developer brief's model: run "
                  "as is, it would spend the round on the same model. "
                  "Nothing is claimed:")
            for item in stepping:
                task = tasks[item["entry"].id]
                print(f"   held: {task['id']} — {task['reason']}")
            print("   ways on: add {model} to the template — it takes the "
                  "brief's model, and `"
                  + payload_model(stepping[0]) + "` on this round, for the "
                  "runner to resolve — or spawn the round yourself from "
                  "the print runner's wave; then re-run")
            _record(SKILL_NAME, "gate_pause", node="execute",
                    wave=waves_done + 1)
            return 0, "model_step_refused", "execute"
        wave = wave_number(state)
        print(f"== wave {wave} — frontier: "
              f"{', '.join(frontier if span == 'full' else runnable)}")
        written = write_wave_payloads(state, Path(spec_dir), repo,
                                      Path(wave_dir) if wave_dir else None,
                                      span=span, native=native,
                                      run_id=run_id, harness=harness,
                                      isolate=isolate, plan_only=dry_run)
        _record(SKILL_NAME, "wave", wave=wave,
                roles=sorted(frontier if span == "full" else runnable),
                payloads=len(written))
        if (runner != PRINT_RUNNER and not dry_run
                and any(payload.node == "execute" for payload in written)):
            if not (SKILL_DIR / "scripts" / "mark.py").is_file():
                print("execute payloads need the orchestrator to claim and "
                      "land tasks (spec-build § Task markers) — use the "
                      "print runner and spawn them yourself")
                return EXECUTE_RUNNER_REFUSED_EXIT, "execute_refused", None
            rc = _headless_execute_wave(spec_dir, written, runner,
                                        parallel, run_id, harness,
                                        budget_spawns, budget_minutes)
            if rc is not None:
                return rc, ("tasks_held" if rc == 0 else "runner_failed"), None
            waves_done += 1
            if max_waves is not None and waves_done >= max_waves:
                print(f"stopping: --max-waves {max_waves} bound reached "
                      f"({waves_done} wave(s) run)")
                return 0, "max_waves", None
            continue
        if not written:
            print("   no runnable payloads this wave — nothing to invoke")
        for payload in written:
            if runner == PRINT_RUNNER:
                print(f"   runner[print]: {payload.role}: echo {payload.path}"
                      f"  # node={payload.node} spec_dir={spec_dir} "
                      f"skill_dir={SKILL_DIR}")
                continue
            invocation = substitute(runner, payload.path, payload.role,
                                    Path(spec_dir), SKILL_DIR, payload.model)
            if dry_run:
                print(f"   runner[dry-run]: {payload.role}: {invocation}")
                continue
            try:
                r = subprocess.run(invocation, shell=True)
            except (OSError, subprocess.SubprocessError) as exc:
                print(f"   runner: {payload.role}: {invocation} → raised "
                      f"{exc!r}")
                print(f"stopping: runner for role {payload.role} (node "
                      f"{payload.node}, payload {payload.path}) raised — no "
                      "later wave starts")
                return RUNNER_FAILED_EXIT, "runner_failed", None
            print(f"   runner: {payload.role}: {invocation} → exit {r.returncode}")
            if r.returncode != 0:
                print(f"stopping: runner for role {payload.role} (node "
                      f"{payload.node}, payload {payload.path}) exited "
                      f"{r.returncode} — no later wave starts")
                return RUNNER_FAILED_EXIT, "runner_failed", None
        waves_done += 1
        if (runner == PRINT_RUNNER and written and state.get("mode") == "fast"
                and all(payload.node == "execute" for payload in written)):
            print("wave emitted — Mode: fast: implement these payloads "
                  "inline (no spawn), land each, then re-run")
        elif runner == PRINT_RUNNER and written:
            how = ("as the agent type beside each role" if native else
                   "agent type beside each role — these embed the brief: "
                   "add --native-agents before spawning as that type")
            print("wave emitted — spawn these payloads in one message "
                  f"({how}), then re-run")
        if max_waves is not None and waves_done >= max_waves:
            print(f"stopping: --max-waves {max_waves} bound reached "
                  f"({waves_done} wave(s) run)")
            return 0, "max_waves", None
        # the print runner executes nothing, so a second pass would only
        # re-emit the same wave
        if runner == PRINT_RUNNER:
            return 0, "wave_emitted", None
        if compute_state(spec_dir, repo_override) == state:
            print("stopping: doc state did not move after the wave — "
                  "act on the frontier, then re-run")
            return 0, "no_progress", None


def print_execute_held(state: dict) -> None:
    """Execute is ready and no task can be spawned: the orchestrator owes
    each held task a move before any wave exists (a resumed session's
    orphaned claims land here)."""
    print("AWAITING ORCHESTRATOR: execute: no task is runnable — resolve "
          "the held tasks, then re-run:")
    for line in execute_holds(state, every=True):
        print(line)
    if any(t.get("held_by") for t in
           state["nodes"]["execute"].get("tasks") or ()):
        print("   a task another spec's claim holds off needs nothing "
              "here: re-emit once that task lands or is released")


def emit_spawns(spec_dir: Path, repo_override: str | None,
                wave_dir: str | None, repair: str | None = None,
                span: str = "full", native: bool = False,
                run_id: str | None = None,
                harness: str = specstate.UNKNOWN_HARNESS,
                isolate: bool = False) -> int:
    """--emit-spawns: write this wave's payloads and list them. With
    --repair NODE, exactly that node's payload is emitted, in or out of
    the frontier (single-agent repair run — a single-role payload, never
    the merged architect). `span` bounds the emitted payloads to the
    phase's frontier nodes. `run_id` stamps the printed claim command on
    an execute wave; both it and `harness` ride the wave rows the emit
    writes to the spec's run ledger. `isolate` gives every implementer
    payload its own worktree and makes it the payload's repo (spec-build
    D-058)."""
    state = compute_state(spec_dir, repo_override, run_id)
    repo = resolved_repo(spec_dir, repo_override)
    if not repair and not frontier_payloads(state, spec_dir, repo, span=span):
        if "execute" in state["frontier"] and span_allows(span, "execute"):
            print_execute_held(state)
            return 0
        scope = "" if span == "full" else f"{span}-span "
        print(f"no {scope}agent payloads to emit — the frontier holds no "
              f"{scope}agent node (frontier: "
              f"{', '.join(state['frontier']) or 'empty'})")
        return 0
    written = write_wave_payloads(state, spec_dir, repo,
                                  Path(wave_dir) if wave_dir else None,
                                  repair, span=span, native=native,
                                  run_id=run_id, harness=harness,
                                  isolate=isolate)
    note = f" (repair: {repair} — single-node emit)" if repair else ""
    print(f"emitted {len(written)} payload(s) for wave "
          f"{wave_number(state)}{note} — spawns/ is derived: delete "
          "freely, check.py never reads it")
    return 0


def compute_state(spec_dir: Path, repo_override: str | None = None,
                  run_id: str | None = None) -> dict:
    """Derive the full workflow-graph state from doc state alone — the same
    dict --state-json serializes. Pure reads: no doc file is ever written and
    no repository or test.md command ever executes — the check.py probes run
    only once their node's inputs are in place. `run_id` is this run's own
    claim-stamp id, when the caller has one: it only changes how claimed
    tasks are phrased (this run's wave vs a possible orphan), never any
    node state."""
    spec_dir = Path(spec_dir)
    repo = Path(repo_override) if repo_override else spec_dir.parent.parent
    docs = {f: read_doc(spec_dir / f) for f in DOC_FILES}
    filled = {f: doc_filled(docs[f]) for f in DOC_FILES}

    git_ok = specstate.git_available(repo)
    head = specstate.head_sha(repo) if git_ok else None
    git_note = "" if git_ok else "SKIPPED (not a git repo)"

    spec_text = docs["spec.md"]
    status = specstate.spec_status(spec_text) if spec_text is not None else None
    effort = specstate.spec_effort(spec_text)
    tier = specstate.spec_tier(spec_text) if spec_text is not None else "full"
    written_mode = specstate.spec_mode(spec_text)
    mode = "fast" if written_mode == "fast" and tier == "tiny" else "standard"
    markers = spec_text.count("NEEDS CLARIFICATION") if spec_text else 0
    # an unfilled template's markers are its examples, not questions
    template_spec = bool(spec_text and spec_text.strip()
                         and is_unfilled(spec_text))
    # Thin floor: at tiny tier the task list lives in spec.md
    # § Tasks — same parsers, one grammar, two homes.
    task_text = docs["task.md"] if tier == "full" else (
        specstate.tiny_task_text(spec_text) if spec_text else None)
    entries = specstate.task_entries(task_text) if task_text else []
    rstate = specstate.research_state(spec_dir)

    nodes: dict[str, dict] = {}

    # -- intent (optional evidence node) -----------------------------------
    # Absent intent.md reads SKIPPED: docsets without it keep the existing
    # graph (no new blockers, authoring readiness unchanged); present-but-red
    # is the ungated artifact the shape span gate refuses; present-and-green
    # reads DONE. Computed first: a missing spec.md is drafted only from a
    # green intent. The baseline gates that handoff alone: under a filled
    # spec.md the repo moves on by design (a teammate's commit, a squash).
    if docs["intent.md"] is None:
        intent_node = {"state": SKIPPED, "reason":
                       "no intent.md — legacy path: the "
                       "docset contract is unchanged, shape and "
                       "execute accept this dir as-is"}
    elif not filled["intent.md"]:
        intent_node = {"state": READY, "reason":
                       "intent.md is still the unfilled template — the "
                       "session writes the idea into § Problem and grills "
                       "the rest; the analyst only records facts and "
                       "candidate gaps "
                       f"(residue: {unfilled_hits(docs['intent.md']) or 'none'})"}
    else:
        irc = run_check(spec_dir, repo_override, ["--intent-only"])
        baseline_history = None
        if irc and filled["spec.md"]:
            still_failing, baseline_notes = intent_failures(
                docs["intent.md"], repo, specs_root=spec_dir.parent)
            if not still_failing:
                baseline_history = "; ".join(baseline_notes)
        if irc == 0:
            intent_node = {"state": DONE, "reason":
                           "intent.md filled and `check.py "
                           "--intent-only` exits 0"}
        elif irc is None:
            intent_node = {"state": BLOCKED, "reason":
                           "check.py could not run — intent unverified"}
        elif baseline_history is not None:
            intent_node = {"state": DONE, "reason":
                           "intent.md gated the intake handoff; spec.md "
                           "is filled, so its baseline is history — "
                           f"{baseline_history}"}
        else:
            intent_node = {"state": BLOCKED, "reason":
                           f"check.py --intent-only exits {irc} — fix "
                           "the intent artifact it names"}

    # -- spec (entry) ------------------------------------------------------
    if spec_text is None or not spec_text.strip():
        if intent_node["state"] == DONE:
            nodes["spec"] = {"state": READY, "reason":
                             "spec.md missing — draft it from intent.md: "
                             "choose the tier, scaffold with `scripts/"
                             "scaffold.sh --tier tiny|full --into-existing "
                             f"{spec_dir.name}`, fill it, then re-run"}
        elif intent_node["state"] == BLOCKED:
            nodes["spec"] = {"state": BLOCKED, "reason":
                             "spec.md missing — waiting on: intent (no "
                             "spec is drafted from a red intent.md)"}
        else:
            nodes["spec"] = {"state": BLOCKED, "reason":
                             "spec.md missing or empty — author the spec "
                             "first"}
    elif template_spec:
        source = ("draft it from intent.md"
                  if intent_node["state"] == DONE else "fill it with the user")
        nodes["spec"] = {"state": BLOCKED, "reason":
                         "spec.md is still the unfilled template — "
                         f"{source}, replacing every placeholder and "
                         "example line (residue: "
                         f"{unfilled_hits(spec_text) or 'none'})"}
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
    if markers and template_spec:
        nodes["clarify"] = {"state": BLOCKED, "reason":
                            "waiting on: spec (the markers in an unfilled "
                            "template are its examples — nothing to ask "
                            "the user yet)"}
    elif markers:
        nodes["clarify"] = {"state": READY, "reason":
                            f"clarify loop active: {markers} open NEEDS "
                            "CLARIFICATION marker(s) — resolve with the user"}
    else:
        nodes["clarify"] = {"state": DONE,
                            "reason": "no open NEEDS CLARIFICATION markers"}

    # -- research-gate (orchestrator judgment, never auto-decided) ---------
    if tier == "tiny":
        nodes["research-gate"] = {"state": SKIPPED, "reason":
                                  "tier: tiny — no research gate; the "
                                  "one-file contract has no research "
                                  "artifact"}
    elif not spec_done:
        nodes["research-gate"] = {"state": BLOCKED, "reason":
                                  "waiting on: spec"}
    elif rstate == "skip":
        nodes["research-gate"] = {"state": DONE, "reason":
                                  "tech-spec.md § Questions & options "
                                  "records the skip marker — gate "
                                  "resolved: skip"}
    elif rstate == "done":
        nodes["research-gate"] = {"state": DONE, "reason":
                                  "tech-spec.md § Questions & options "
                                  "written — gate resolved: run"}
    else:
        nodes["research-gate"] = {"state": UNDETERMINED, "reason":
                                  "tech-spec.md § Questions & options "
                                  "absent or unfilled — decide: run the "
                                  "researcher, or record the skip marker"}
    gate = nodes["research-gate"]["state"]

    # -- research ----------------------------------------------------------
    if tier == "tiny":
        nodes["research"] = {"state": SKIPPED, "reason":
                             "tier: tiny — no research gate to resolve"}
    elif gate == UNDETERMINED:
        nodes["research"] = {"state": BLOCKED, "reason":
                             "research-gate undetermined — decide run or "
                             "skip first"}
    elif rstate == "skip":
        nodes["research"] = {"state": SKIPPED, "reason":
                             "gate resolved: skip — the researcher is not run"}
    elif rstate == "done":
        nodes["research"] = {"state": DONE, "reason":
                             "the research record holds real (non-marker) "
                             "content"}
    else:
        nodes["research"] = {"state": BLOCKED, "reason":
                             "gate resolved run but the research record has "
                             "no content yet"}
    research_done = nodes["research"]["state"] == DONE

    nodes["intent"] = intent_node
    intent_settled = nodes["intent"]["state"] in (DONE, SKIPPED)


    entry_unmet = ([] if spec_done else ["spec"]) + (
        [] if intent_settled else ["intent"])

    def authored(node: str, filename: str, deps: list[str],
                 unmet_extra: list[str] | None = None) -> None:
        """Shared shape for the authoring nodes: blocked on unmet deps, READY
        while the output is missing/unfilled, done once it is filled —
        unless a refused digest holds it."""
        unmet = entry_unmet + [d for d in deps
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
                           f"rewrite it (residue: {unfilled_hits(docs[filename]) or 'none'})"}
        elif node in holds:
            seen = holds[node]
            nodes[node] = {
                "state": BLOCKED,
                "reason": "its digest on file is refused — digest: "
                          + specstate.digest_refusal_line(seen),
                "digest": seen}
        else:
            nodes[node] = {"state": DONE,
                           "reason": f"{filename} present and filled"}

    # A refused digest holds its node only while authoring is open: the
    # signed docset is the contract past the approval, its authors'
    # digests history.
    signed = (spec_dir / "approvals" / "approval.md").exists()
    holds = ({} if tier == "tiny" or (
        status in APPROVED_AND_LATER and signed) else digest_holds(spec_dir))
    if tier == "tiny":
        for node, doc in (("plan", "plan.md"), ("tech", "tech-spec.md"),
                          ("qa", "test.md"), ("tasks", "task.md")):
            nodes[node] = {"state": SKIPPED, "reason":
                           f"tier: tiny — no {doc}; the one-file contract "
                           "holds tasks in spec.md § Tasks"}
    else:
        authored("tech", "tech-spec.md", [],
                 None if research_done or rstate == "skip"
                 else ["research (research-gate undetermined — decide run or "
                       "skip)"])
        if nodes["tech"]["state"] == DONE:
            rc = run_check(spec_dir, repo_override, ["--code-state-only"])
            if rc is None:
                nodes["tech"] = {"state": BLOCKED, "reason":
                                 "check.py could not run — Code state "
                                 "unverified"}
            elif rc:
                nodes["tech"] = {"state": BLOCKED, "reason":
                                 f"check.py --code-state-only exits {rc} — "
                                 "fix the § Code state evidence it names"}
            else:
                nodes["tech"]["reason"] = (
                    "tech-spec.md filled and `check.py --code-state-only` "
                    "exits 0")
        authored("plan", "plan.md", ["tech"])
        authored("qa", "test.md", [])
        authored("tasks", "task.md", ["plan", "tech", "qa"])

    # -- verify (mechanical: runs check.py) --------------------------------
    verify_deps = [d for d in ("tech", "plan", "qa", "tasks")
                   if nodes[d]["state"] not in (DONE, SKIPPED)]
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

    # -- approve (HUMAN) ---------------------------------------------------
    # A Status word alone is not an approval: the freeze is the gate's
    # record, so a hand-flipped Status never opens execute.
    unfrozen = status in APPROVED_AND_LATER and not signed
    if unfrozen:
        nodes["approve"] = {"state": BLOCKED, "reason":
                            f"Status: {status} without the approval freeze "
                            "(approvals/approval.md) — never approved: set "
                            "Status back to draft; approved before the "
                            "freeze existed: re-approve once — "
                            + freeze.approval_steps(spec_dir)}
    elif not verify_done:
        nodes["approve"] = {"state": BLOCKED,
                            "reason": "waiting on: verify"}
    elif status in APPROVED_AND_LATER:
        nodes["approve"] = {"state": DONE, "reason": f"Status: {status}"}
    else:
        nodes["approve"] = {"state": READY, "reason":
                            "HUMAN GATE — present the reviewed docset; "
                            "approval is the user's explicit yes (Status "
                            f"currently: {status or 'no Status line'})"}
    approve_done = nodes["approve"]["state"] == DONE

    # -- execute (per-task frontier) ---------------------------------------
    per_task: list[dict] = []
    if not approve_done:
        nodes["execute"] = {"state": BLOCKED, "reason":
                            f"waiting on: approve (spec Status: "
                            f"{status or 'none'} — approval is a human gate)"}
    elif not entries:
        nodes["execute"] = {"state": BLOCKED, "reason":
                            ("spec.md § Tasks has no task entries — "
                             "author them with the user" if tier == "tiny"
                             else "task.md has no task entries — spawn "
                                  "the task-breaker")}
    else:
        per_task = task_frontier(entries, run_id, spec_dir,
                                 held=specstate.claims_held(spec_dir))
        open_tasks = [t for t in per_task
                      if t["state"] not in ("ticked", "struck",
                                           "implemented")]
        n_run = sum(1 for t in open_tasks if t["state"] == "runnable")
        n_claim = sum(1 for t in open_tasks if t["state"] == "claimed")
        n_cap = sum(1 for t in open_tasks if t["state"] == "at-fix-cap")
        if not open_tasks:
            nodes["execute"] = {"state": DONE, "reason":
                                f"all {len(per_task)} task(s) "
                                "implemented/ticked/struck"}
        else:
            nodes["execute"] = {"state": READY, "reason":
                                f"{n_run} of {len(per_task)} task(s) "
                                f"runnable ({len(open_tasks)} open: "
                                f"{n_claim} claimed/in flight, {n_cap} at "
                                "fix cap)"}
    execute_done = nodes["execute"]["state"] == DONE
    if per_task:
        # the resume view's digest column (spec-build D-040): a claimed
        # task shows whether a developer digest is on file and what it
        # reported — pure doc reads, never status. A file the digest
        # schema rejects reads as malformed, never as none (spec-build
        # D-054). A typed deviation (D-043) rides along: scope → widen
        # Touches + D-###; spec-defect → /spec-design; neither opens a
        # fix round.
        for t in per_task:
            if t["state"] == "claimed" and t["id"]:
                d = specstate.latest_digest(spec_dir, t["id"])
                if d is None:
                    t["digest"] = None
                elif d["state"] == specstate.DIGEST_MALFORMED:
                    t["digest"] = "malformed — fix and run again"
                else:
                    t["digest"] = d["status"]
                    if d.get("deviation_kind"):
                        t["deviation"] = d["deviation"]
        # D-044 watch, once per report per task, never blocking: the
        # same failing command recurring across a task's fix rounds —
        # the early signal (>= SAME_FAILURE_WATCH) before the advisory
        # bound makes the plan the suspect
        for t in per_task:
            if not t.get("id") or t["state"] in ("ticked", "struck",
                                                 "implemented"):
                continue
            sig, run = failure_run(spec_dir, t["id"])
            if sig and run >= SAME_FAILURE_WATCH:
                t["watch"] = f"same failing command {run} round(s): {sig}"
        nodes["execute"]["tasks"] = per_task

    counts = {
        "todo": sum(1 for e in entries
                    if not e.done and not e.struck and not e.claimed
                    and not e.implemented),
        "claimed": sum(1 for e in entries
                       if e.claimed and not e.done and not e.struck
                       and not e.implemented),
        "implemented": sum(1 for e in entries
                           if e.implemented and not e.done and not e.struck),
        "ticked": sum(1 for e in entries if e.done),
        "struck": sum(1 for e in entries if e.struck),
        "at-fix-cap": sum(1 for e in entries
                          if not e.done and not e.struck
                          and not e.implemented and e.fix_round
                          and e.fix_round >= FIX_CAP),
    }

    # -- tick-commit ---------------------------------------------------------
    if not execute_done:
        nodes["tick-commit"] = {"state": BLOCKED,
                                "reason": "waiting on: execute"}
    else:
        ticks = specstate.tick_evidence(task_text or "")
        if ticks.unticked:
            nodes["tick-commit"] = {"state": READY, "reason":
                                    "HUMAN GATE — every task landed: prove "
                                    "green (audit.py proofs --run + "
                                    "regression), review, and present the "
                                    "delivery summary; on the user's "
                                    "explicit yes tick every task `- [x]` "
                                    "with its proof note "
                                    f"({len(ticks.unticked)} unticked: "
                                    f"{', '.join(ticks.unticked)}), "
                                    "recompute the burndown, and commit"}
        elif ticks.noteless:
            nodes["tick-commit"] = {"state": READY, "reason":
                                    "tick evidence incomplete — ticked "
                                    "without proof notes: "
                                    f"{', '.join(ticks.noteless)}; add the "
                                    "`done <date> — <proof>` sub-lines"}
        elif not git_ok:
            nodes["tick-commit"] = {"state": DONE, "reason":
                                    f"task.md cites {ticks.ticked} ticked + "
                                    f"{ticks.struck} struck of {ticks.total}, "
                                    "every tick with its proof note — "
                                    "commit SKIPPED (not a git repo)"}
        else:
            holder = "spec.md" if tier == "tiny" else "task.md"
            delivery = specstate.delivery_state(
                (spec_text if tier == "tiny" else task_text) or "")
            if delivery[0] == "delivered" and delivery[1] != "-":
                nodes["tick-commit"] = {"state": DONE, "reason":
                                        f"task.md cites {ticks.ticked} ticked "
                                        f"+ {ticks.struck} struck of "
                                        f"{ticks.total}, every tick with its "
                                        "proof note — Delivered: commit @ "
                                        f"{delivery[1]} recorded in {holder}"}
            else:
                nodes["tick-commit"] = {"state": READY, "reason":
                                        "tick transition due — "
                                        f"task.md cites {ticks.ticked} ticked "
                                        f"+ {ticks.struck} struck of "
                                        f"{ticks.total}, every tick with its "
                                        "proof note; delivery unproven: no "
                                        "commit SHA observed — commit the "
                                        "plan and record the delivery "
                                        "evidence"}
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
    if docs["tech-spec.md"] and git_ok:
        base = specstate.doc_baseline(docs["tech-spec.md"])
        if base is None:
            converge = "no tech-spec Baseline recorded — nothing to converge yet"
        elif head and base[1] == head:
            converge = f"fresh — tech-spec Baseline {base[1]} == HEAD {head}"
        elif head and code_delta(repo, spec_dir, base[1], head)[1] == []:
            converge = ("fresh — only the kit's doc trees changed since "
                        f"tech-spec Baseline {base[1]} (HEAD {head})")
        else:
            converge = (f"stale — tech-spec Baseline {base[1]} != HEAD {head} "
                        "— re-ground § Code state delta-scoped (--emit-spawns "
                        "--repair tech), then audit.py converge, and "
                        "append tasks")
    elif not git_ok:
        converge = ("SKIPPED (not a git repo) — no HEAD to diff the tech-spec "
                    "baseline against")
    else:
        converge = "no tech-spec.md — nothing to converge yet"

    n_fix = sum(1 for e in entries if e.fix_round is not None
                and not e.done and not e.struck and not e.implemented)
    loops = {
        "clarify": ("idle — spec.md is still the unfilled template"
                    if markers and template_spec
                    else f"active — {markers} open marker(s)" if markers
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
        "effort": effort,
        "mode": mode,
        **({"mode_note": "Mode: fast is honored only at Tier: tiny — "
                         "execute spawns developers as usual"}
           if written_mode == "fast" and mode != "fast" else {}),
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
            out.append(f"      {task_line(t)}")
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
               f"{c['implemented']} implemented · {c['ticked']} ticked · "
               f"{c['struck']} struck · {c['at-fix-cap']} at fix-cap")
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


def render_explain(s: dict, node: str, repo: Path | None = None) -> str:
    """`--explain NODE`'s text; with `repo`, the execute node adds the
    isolated worktrees on disk (spec-build D-058)."""
    n = s["nodes"][node]
    lines = [f"{node}: {n['state']} — {n['reason']}",
             f"  ready when: {READY_WHEN[node]}",
             f"  done when: {DONE_WHEN[node]}"]
    lines += [f"  {task_line(t)}" for t in n.get("tasks") or ()]
    if node == "execute" and repo is not None:
        lines += worktree_lines(s, repo)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Every mode reads the claim registry through compute_state: one
    that cannot be read, or whose lock is held, refuses the whole
    invocation before anything is written (D-078)."""
    try:
        return _main(argv)
    except specstate.ClaimsLockBusy as exc:
        print(f"lock busy: {exc}", file=sys.stderr)
        return 1
    except specstate.ClaimsRegistryError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except specstate.WorktreeError as exc:
        print(f"refused: --isolate worktree — {exc}", file=sys.stderr)
        return ISOLATE_REFUSED_EXIT


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="graph.py",
        description="The dynamic workflow engine: derives the frontier, "
                    "loops, and lifecycle state of a spec folder from doc "
                    "state alone (see the module docstring for the node "
                    "model).",
        epilog="exit codes: 0 report produced (any state) · 1 unreadable "
               "spec-dir, or a phase span stopped red/held · 2 usage error "
               "· 3 --run runner failure (later "
               "waves stopped) · 4 span entry refused (blocking gate "
               "printed)")
    p.add_argument("spec_dir", help="path to specs/<name>")
    p.add_argument("--repo", metavar="PATH",
                   help="repo root for git-derived signals (default: the "
                        "spec dir's grandparent, like check.py/audit.py)")
    p.add_argument("--state-json", action="store_true",
                   help="print the full state as machine-readable JSON")
    p.add_argument("--launch-check", action="store_true",
                   help="print the dynamic-workflow launch advisory as JSON — "
                        "launch the dynamic workflow only on weight "
                        "`wave`; `gate`/`single`/`complete`/`held` spans "
                        "run inline (pure read, nothing written)")
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
    p.add_argument("--repair", metavar="NODE",
                   help="with --emit-spawns: emit ONLY this agent node's "
                        "payload, in or out of the frontier — the "
                        "single-agent repair-run instrument (a stale-"
                        "Baseline converge re-ground: --repair tech "
                        "emits a DELTA-scoped tech payload; --repair "
                        "research emits the researcher alone; --repair "
                        "approve re-emits the contract review; --repair "
                        "constitution emits the analyst's article "
                        "proposals); refused "
                        "when this package ships no brief or lens for "
                        "the node")
    p.add_argument("--native-agents", action="store_true",
                   help="with --emit-spawns or --run: the harness registers "
                        "this package's agents, so each payload names its "
                        "agent type and omits the brief body that type "
                        "already carries (default: self-contained payloads "
                        "for a harness without registered agents); a "
                        "round-4 fix payload keeps the brief — it names "
                        "the model step and both spawn routes")
    p.add_argument("--wave-dir", metavar="DIR",
                   help="with --emit-spawns or --run: write this wave's "
                        "payloads into DIR instead of "
                        "<spec-dir>/spawns/wave-<N>/")
    p.add_argument("--run", action="store_true",
                   help="auto-trigger loop: AWAITING HUMAN (or AWAITING "
                        "ORCHESTRATOR at the research gate) pauses at "
                        "judgment nodes, verify runs check.py directly, "
                        "agent waves go to --runner (default: print), "
                        "recompute, repeat")
    p.add_argument("--runner", metavar="TEMPLATE",
                   help="command template for --run with {prompt_file}, "
                        "{role}, {spec_dir}, {skill_dir}, {model} "
                        "substituted verbatim (default: print — echo "
                        "invocations); {model} is the brief's model, and "
                        "the same with +1 on the fix round that runs a "
                        "model step — a template without {model} stops "
                        "AWAITING ORCHESTRATOR before that round is "
                        "claimed")
    p.add_argument("--dry-run", action="store_true",
                   help="with --run: print the full wave plan and execute "
                        "nothing (payload files are still written)")
    p.add_argument("--max-waves", type=int, metavar="N",
                    help="with --run: stop after N waves")
    p.add_argument("--parallel", type=int, default=1, metavar="N",
                   help="with --run: run up to N payload subprocesses "
                        "concurrently per wave (the headless execute wave "
                        "batches its runners with it; default 1)")
    p.add_argument("--run-id", metavar="ID",
                   help="this session's run id, reused across waves — the "
                        "orchestrator generates one (mark.py prints it) "
                        "and passes it here so --explain execute and the "
                        "orphan notices only flag claims from OTHER runs")
    p.add_argument("--harness", metavar="NAME",
                   help="with --emit-spawns or --run: the harness running "
                        "this session — your harness name — recorded "
                        "verbatim in the spec's run ledger beside every "
                        "payload these modes write (default: unknown)")
    p.add_argument("--span", choices=("intent", "shape", "execute", "full"),
                   default=None, metavar="PHASE",
                   help="bound the wave to one phase's frontier "
                        "with --run/--emit-spawns: intent (the analyst node), "
                        "shape (intent + authoring + verify + the approve "
                        "handoff), execute (execute + tick-commit + "
                        "archive; refuses unless approve AND verify are "
                        "done), full (default — bare-invocation "
                        "semantics); span entry refuses (exit 4) naming "
                        "the blocking gate: shape when intent is blocked")
    p.add_argument("--isolate", choices=("worktree",), metavar="MODE",
                   help="with --emit-spawns or --run: `worktree` gives each "
                        "implementer payload its own detached git worktree "
                        "under <repo>/.spec-kit/worktrees/<spec>/<T###>/, "
                        "a snapshot of the main working tree, named as the "
                        "payload's repo — mark.py land merges the delta "
                        "back into the main tree, mark.py release discards "
                        "it; refused (exit 2) outside a git repository")
    p.add_argument("--budget-spawns", type=int,
                   default=specstate.BUDGET_SPAWNS, metavar="N",
                   help="with --run: implementer spawns a run may claim "
                        "before it parks AWAITING HUMAN — counted over this "
                        "run's claims and again over the spec's whole run "
                        "ledger (default 30; 0 lifts the budget; "
                        "spec-build D-059)")
    p.add_argument("--budget-minutes", type=int,
                   default=specstate.BUDGET_MINUTES, metavar="N",
                   help="with --run: wall-clock minutes since its first "
                        "claim a run may run before it parks AWAITING "
                        "HUMAN — this run's count alone, never the spec's "
                        "(default 120; 0 lifts the budget; spec-build D-059)")
    args = p.parse_args(argv)

    if args.explain is not None and args.explain not in NODES:
        p.error(f"unknown node: {args.explain!r} — valid nodes: "
                f"{', '.join(NODES)}")
    if (args.runner or args.dry_run or args.max_waves is not None
            or args.parallel != 1) and not args.run:
        p.error("--runner/--dry-run/--max-waves/--parallel require --run")
    if args.parallel < 1:
        p.error("--parallel must be >= 1")
    if args.launch_check and (args.state_json or args.emit_spawns
                              or args.run):
        p.error("--launch-check is its own mode — not combinable with "
                "--state-json, --emit-spawns, or --run")
    if args.emit_spawns and args.run:
        p.error("--emit-spawns and --run are separate modes")
    if args.repair and not args.emit_spawns:
        p.error("--repair requires --emit-spawns (repair is a "
                "single-agent emit, never part of --run)")
    if args.repair is not None:
        if args.repair not in REPAIR_BRIEFS:
            p.error(f"--repair: {args.repair!r} is not a repairable agent "
                    "node — valid: " + ", ".join(REPAIR_BRIEFS))
        refusal = repair_refusal(args.repair)
        if refusal:
            p.error(refusal)
    if args.max_waves is not None and args.max_waves < 1:
        p.error("--max-waves must be >= 1")
    if args.wave_dir and not (args.emit_spawns or args.run):
        p.error("--wave-dir requires --emit-spawns or --run")
    if args.native_agents and not (args.emit_spawns or args.run):
        p.error("--native-agents requires --emit-spawns or --run")
    if args.harness and not (args.emit_spawns or args.run):
        p.error("--harness requires --emit-spawns or --run")
    if args.span is not None and not (args.emit_spawns or args.run):
        p.error("--span requires --emit-spawns or --run (a span bounds "
                "the executor modes; the report modes are spanless)")
    if args.isolate and not (args.emit_spawns or args.run):
        p.error("--isolate requires --emit-spawns or --run (only an "
                "implementer payload is isolated)")
    if ((args.budget_spawns != specstate.BUDGET_SPAWNS
         or args.budget_minutes != specstate.BUDGET_MINUTES)
            and not args.run):
        p.error("--budget-spawns/--budget-minutes require --run")
    if args.budget_spawns < 0 or args.budget_minutes < 0:
        p.error("--budget-spawns/--budget-minutes must be >= 0 "
                "(0 lifts the budget)")

    span = args.span or "full"

    spec_dir = Path(args.spec_dir)
    if not spec_dir.exists():
        print(f"graph.py: spec dir not found: {spec_dir}", file=sys.stderr)
        return 1
    if not spec_dir.is_dir():
        print(f"graph.py: not a directory: {spec_dir}", file=sys.stderr)
        return 1

    if args.isolate and not specstate.git_available(
            resolved_repo(spec_dir, args.repo)):
        print(f"refused: --isolate worktree needs a git repository — "
              f"{resolved_repo(spec_dir, args.repo)} is not in one. Re-run "
              "without the flag to work in the shared tree, or initialize "
              "git first; nothing was written", file=sys.stderr)
        return ISOLATE_REFUSED_EXIT

    if span != "full":
        refusals = span_entry_refusals(
            compute_state(spec_dir, args.repo), span)
        if refusals:
            for gate, reason in refusals:
                print(f"span entry refused — --span {span}: blocking gate "
                      f"{gate}: {reason}")
            _record(SKILL_NAME, "intake_refusal", span=span,
                    gates=[g for g, _ in refusals])
            return SPAN_REFUSED_EXIT

    if not args.launch_check:
        sweep(spec_dir)

    if args.emit_spawns:
        return emit_spawns(spec_dir, args.repo, args.wave_dir, args.repair,
                           span, args.native_agents, args.run_id,
                           args.harness or specstate.UNKNOWN_HARNESS,
                           bool(args.isolate))
    if args.run:
        return run_loop(spec_dir, args.repo, args.runner or PRINT_RUNNER,
                        args.dry_run, args.max_waves, args.wave_dir,
                        span=span, native=args.native_agents,
                        run_id=args.run_id, parallel=args.parallel,
                        harness=args.harness or specstate.UNKNOWN_HARNESS,
                        isolate=bool(args.isolate),
                        budget_spawns=args.budget_spawns,
                        budget_minutes=args.budget_minutes)

    state = compute_state(spec_dir, args.repo, args.run_id)

    if args.launch_check:
        print(json.dumps(
            launch_check(state, spec_dir,
                         resolved_repo(spec_dir, args.repo)), indent=2))
        return 0

    if args.explain is not None:
        print(render_explain(state, args.explain,
                            resolved_repo(spec_dir, args.repo)))
    elif args.state_json:
        print(json.dumps(state, indent=2))
    elif args.mermaid:
        print(render_mermaid(state))
    else:
        print(render_report(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
