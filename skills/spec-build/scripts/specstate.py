"""Shared doc-state parsers for a spec folder under specs/<name>/.

Every scheduling-relevant signal the tooling layer reads out of the docset
lives here as a pure function: spec Status, task entries (checkboxes,
phases, parallel markers, dependency chains, fix rounds, implemented
markers), the Delivered header line and the approval-freeze anchor, the
baseline header and tech-spec Code state item list, the hotfix lineage headers, the
researcher-skip marker, next-free-ID allocation, ID definitions, and the
git availability probes.
check.py, audit.py, and graph.py import from this module instead
of inlining their own copies — one canonical regex per doc shape, so the
validators and the workflow engine can never drift apart on what the docs
say.

Pure functions, stdlib only, no CLI: importing this module has no side
effects — no output, no file writes (the file-reading exceptions are
research_state/git helpers, the run ledger and `task_lock`, which take
an explicit path). Text arguments
are the already-read file contents; check.py strips invisible/control
characters at read time before any parser sees the text, so the patterns
below can stay simple.

Exit-code/CLI contracts live in the tooling scripts, not here.
"""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import NamedTuple

# The digest schemas live in digests.py beside this script. The
# scripts dir goes on sys.path locally (no install step): tests load
# this file by path via importlib, which does not put scripts/ on it.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import digests  # noqa: E402 - the sys.path setup above runs first

# An ID is "defined" when it introduces its entity on one of these line shapes.
# Single source of truth for FR/AC/US/TC/D — check.py's traceability graph,
# its checklist builder, and graph.py's ID bookkeeping all read this table.
DEFINITIONS = {
    "FR": re.compile(r"^-\s+\*\*(FR-\d{3})\*\*"),
    "NFR": re.compile(r"^-\s+\*\*(NFR-\d{3})\*\*"),
    "AC": re.compile(r"^-\s+(AC\d+):"),
    "US": re.compile(r"^###\s+(US\d{1,2})\b"),
    "TC": re.compile(r"^#{2,3}\s+(TC-\d{3})"),
    "D": re.compile(r"^###\s+(D-\d{3})"),
}

# Template placeholders: <name>, <verb phrase>, <initial state> ... (letters,
# spaces, hyphens only — real markdown like <br> or <a href> won't match).
PLACEHOLDER = re.compile(r"<[a-z][a-z -]{2,}>")
CODE_SPAN = re.compile(r"`[^`]*`")
QUOTE_SPAN = re.compile(r'"[^"\n]*"')
HTML_COMMENT = re.compile(r"<!--.*?-->")

# spec.md lifecycle: `**Status**: <word>` (backticked words tolerated).
STATUS_LINE = re.compile(r"^\*\*Status\*\*:\s*`?([A-Za-z]+)", re.M)

# spec.md effort tier: `**Effort**: <word>` — the mechanical handle for the
# effort-scaling tiers. Absent or unknown reads "large" so docsets without
# the field keep the full-wave graph unchanged. `tiny` is a contract Tier,
# never an effort: a doc still carrying it as one reads as the lightest
# effort, not the heaviest.
EFFORT_LINE = re.compile(r"^\*\*Effort\*\*:\s*`?([A-Za-z]+)", re.M)
EFFORT_TIERS = ("standard", "large")
EFFORT_ALIASES = {"tiny": "standard"}
# Thin floor: `**Tier**: tiny` on spec.md — the contract is ONE
# file (tasks live in spec.md § Tasks); absent/unknown reads "full",
# so docsets without the field keep the full-contract graph.
TIER_LINE = re.compile(r"^\*\*Tier\*\*:\s*`?([A-Za-z]+)", re.M)
# `**Mode**: fast` (D-066): the session implements a tiny spec's tasks
# itself instead of spawning a developer per task; absent/unknown reads
# "standard", and only Tier: tiny honors fast.
MODE_LINE = re.compile(r"^\*\*Mode\*\*:\s*`?([A-Za-z]+)", re.M)
TASKS_HEADING = "## Tasks"

# Work type: `**Type**: <word>` on spec.md (and intent.md, which seeds
# it). Absent reads "feature"; an unknown word is returned as written so
# the checker can refuse it by name. hotfix is the tiny-tier bugfix.
TYPE_LINE = re.compile(r"^\*\*Type\*\*:\s*`?([A-Za-z]+)", re.M)
WORK_TYPES = ("feature", "bugfix", "hotfix", "refactor", "upgrade")
# Types whose contract is "nothing observable changes": user stories and
# ACs are optional, behavior-preservation test cases are not.
PRESERVING_TYPES = ("refactor", "upgrade")

# Hotfix lineage on a hotfix spec.md: `**Hotfix for**: <tag>` and/or
# `**Fixes spec**: <name>` — the target its release note groups under.
# The `<`-exclusive capture (DEPENDS_LINE precedent) keeps the unfilled
# template placeholder reading as absent.
HOTFIX_FOR_LINE = re.compile(r"^\*\*Hotfix for\*\*:[ \t]*([^\n<]*)", re.M)
FIXES_SPEC_LINE = re.compile(r"^\*\*Fixes spec\*\*:[ \t]*([^\n<]*)", re.M)

# Cross-spec ordering: `**Depends on**: <spec-name>[, <spec-name>…]` on
# spec.md. Optional; `none`, a dash, or an absent line names nothing.
DEPENDS_LINE = re.compile(r"^\*\*Depends on\*\*:[ \t]*([^\n<]*)", re.M)

# task.md entry shapes (the Conventions block in templates/task.md is the
# normative wording): `- [x]` done, `(in-progress)` claimed, `~~T###~~`
# struck/dropped, `[P]` parallelizable, `(after T###)` dependency chain,
# `(fix <n>/5)` an OPEN fix round. `(implemented)` records landed work on
# an unticked entry — durable before the delivery step's ticks, and read
# independently of claimed/done/struck. An open fix round voids the
# landing beside it: the round closes by rewriting the marker
# `(fixed <n>/5)`, which no parser here reads as open.
TASK_ID = re.compile(r"- \[[ x]\]\s*(T\d{3})")
TASK_DONE = re.compile(r"- \[x\]")
AFTER_REF = re.compile(r"\(after\s+(T\d{3})")
FIX_ROUND = re.compile(r"\(fix\s+(\d+)/\d+\)")
STRIKETHROUGH = re.compile(r"~~[^~]*~~")

# task.md tick proof: the `done <date> — <proof>` sub-line a ticked entry
# carries (em dash U+2014; tick.py writes it bulleted, the conventions show
# it indented — both shapes read). A tick without it is bookkeeping, not
# durable evidence.
DONE_NOTE = re.compile(r"^\s*(?:-\s*)?done \d{4}-\d{2}-\d{2} \u2014", re.M)

# Fix-round note sub-lines (em dash U+2014, same two written shapes): the
# `fix` line opens a round with the verbatim failure digest; the sibling
# `fixed` line closes it with resolution and proof. Durable round evidence
# beside the `(fix n/5)` marker, which stays the round-count holder.
FIX_NOTE_OPEN = re.compile(r"^\s*(?:-\s*)?fix (\d+) \u2014 (.+)$", re.M)
FIX_NOTE_CLOSED = re.compile(
    r"^\s*(?:-\s*)?fixed (\d+) \u2014 (.+?) \u2014 (.+)$", re.M)

# The claim stamp (spec-build D-039): `  - claimed <UTC ISO> — run <id>`,
# a sub-line under a claimed entry written by mark.py claim. A sub-line —
# not an inline `(in-progress r-id)` — on purpose: the claim stays
# detected by the `(in-progress)` substring and the freeze's marker
# regex keeps matching only the exact marker words, the same way the fix
# sub-lines work. History of round sub-lines is durable; a stamp is not —
# land, release and tick remove it. A claim with no stamp stays valid
# (older docsets); a stamp with no claim is the checker's finding.
CLAIM_NOTE = re.compile(
    r"^\s*(?:-\s*)?claimed (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
    r" \u2014 run (\S+)$", re.M)

# task.md header: the delivery record — `commit @ <sha>` once the plan's
# end-of-spec commit exists, `commit @ -` the explicit non-git skip. The
# record must name `commit` directly after the colon, so the scaffold's
# `pending` placeholder — and its backticked example text — cannot read
# as delivered.
DELIVERED_COMMIT = re.compile(
    r"Delivered\*{0,2}\s*:\s*commit\s+@\s*`?([0-9a-f]{7,40}|-)"
)

# approvals/approval.md: the `**Approved-at**: <sha>` anchor freeze.py
# records at approval — the commit the approved docset was signed against,
# and the default diff base for the post-execute review instruments.
APPROVED_AT = re.compile(
    r"\*\*Approved-at\*\*\s*:\s*`?([0-9a-f]{7,40})`?", re.I)

# Exact lifecycle evidence values. State helpers answer only whether a marker
# was recorded; these parsers expose the SHA (or explicit non-git dash) so
# integrity checks can prove it exists and belongs to the repository instead
# of trusting any hex-looking text.
LIFECYCLE_VALUES = {
    "delivered": DELIVERED_COMMIT,
}

# spec.md coverage-floor header: `**Coverage**: 80` (percent sign
# tolerated, value clamped by the reader) — the minimum line coverage
# audit.py's coverage mode enforces over the tasks' intended files when
# the repo ships coverage tooling. Absent → the 80 default.
COVERAGE_FLOOR = re.compile(
    r"^\*\*Coverage\*\*\s*:\s*(\d{1,3})\s*%?", re.M)

# Baseline header (tech-spec.md, intent.md): `**Baseline**: <version> @ <sha>`,
# backticks on the sha tolerated; the second shape matches a bare
# angle-bracketed baseline header carrying a real hash (e.g. `<v2 @ abc1234>`).
# The unfilled template's `<version @ commit>` placeholder has no hex chars
# and cannot match either shape — it reads None (see doc_baseline).
BASELINE_HEADER = re.compile(r"Baseline\*\*([^@\n]*)@\s*`?([0-9a-f]{7,40})`?")
BASELINE_PLACEHOLDER = re.compile(r"<\s*([^<>@\n]{1,40})\s*@\s*([0-9a-f]{7,40})\s*>")

# tech-spec.md § Code state item shape: `item <id>: "<desc>"` with a
# following `status:` line. Malformed/missing status reads "unknown" rather
# than raising — converge diffs two possibly-messy snapshots.
CODE_STATE_SECTION = re.compile(r"^##\s+Code state\s*$", re.M)

# TC ownership in task.md: a task entry's `Proves: TC-###, …` sub-line
# names the test cases whose tests that task writes; a `- TC-### — <why>`
# line under `## Regression guards` names a case whose requirement Code
# state already reads DONE (an existing test guards it).
PROVES_LINE = re.compile(r"^\s*-\s*Proves:\s*(.+)$", re.M)
GUARDS_SECTION = re.compile(r"^##\s+Regression guards\s*$", re.M)
GUARD_LINE = re.compile(r"^-\s+(TC-\d{3})\b", re.M)
STATE_ITEM = re.compile(r'^item\s+(\S+):\s*"([^"]*)"', re.M)
STATE_ITEM_STATUS = re.compile(r"^\s*status:\s*(DONE|PARTIAL|TODO)", re.M)

# The researcher-gate skip record (byte-exact, em dash U+2014). Canonical
# home: tech-spec.md `## Questions & options` (a pre-migration research.md
# is read through the legacy fallback). Every occurrence anywhere must
# match this sequence exactly; research_state matches it as a whole
# stripped line.
RESEARCH_SKIP_MARKER = "not applicable — no open questions at Stage 0"

# The developer digest file (spec-build D-040): a write-capable agent
# writes its digest to specs/<name>/digests/wave-<N>/<payload-stem>.md
# as its final action. The line's grammar is digests.py's `developer`
# schema — a file that exists but carries no valid digest line is
# malformed, never read as absent. The deviation field is TYPED
# (spec-build D-043): `scope:<paths>`, `spec-defect:<why>` or
# `other:<summary>`; its type routes the block and rides beside the
# parsed value as `deviation_kind`. Run scratch, not archived contract
# (archive.sh removes digests/ with spawns/).
DIGEST_DIR = "digests"
DIGEST_FILE = re.compile(r"^implementer-(T\d{3})\.md$")
DIGEST_VALID = "valid"
DIGEST_MALFORMED = "malformed"
DIGEST_UNVERIFIED = "unverified"

# The research gate's artifact in tech-spec.md: one section, two
# subsections. The heading is matched anywhere in the file (no
# positional coupling); everything to the next `## ` is the section.
QUESTIONS_SECTION = re.compile(r"^##\s+Questions & options\s*$", re.M)


# NamedTuple, not dataclass: the suite loads scripts by file path via
# importlib without sys.modules registration, which breaks dataclass
# annotation processing — a plain record keeps the module loadable either way.
class FixRound(NamedTuple):
    """One fix round's note sub-lines from a task entry block: the round
    number, the failure digest recorded at open, and — once closed — the
    resolution and its proof. `closed` stays False while only the open
    sub-line exists."""

    n: int
    digest: str
    resolution: str
    proof: str
    closed: bool


class ClaimStamp(NamedTuple):
    """A claimed entry's claim stamp (spec-build D-039): the UTC ISO time
    mark.py claimed the task and the run id whose wave holds it. `at` is
    informational (the resume view prints its age); `run` tells orphan
    reports which dead run left the claim behind."""

    at: str
    run: str


class TaskEntry(NamedTuple):
    """One `- [ ]`-anchored task entry from task.md's `## Phase N` sections.

    `block` is the entry's raw text (trimmed at the first blank line, so
    trailing prose after the section's last entry is not swallowed); the
    flag fields are parsed views onto it. `id` is None for entries whose
    first line doesn't open with a T-ID (e.g. the struck form
    `- [ ] ~~T005~~ …`) and `phase` is None under an unnumbered phase
    header — both stay in the list so consumers count them where the
    source file counts them. `claim` is the entry's claim stamp, None
    when the entry carries none (hand-written claims and older docsets)."""

    id: str | None
    phase: int | None
    block: str
    first_line: str
    done: bool
    claimed: bool
    struck: bool
    parallel: bool
    after: list[str]
    fix_round: int | None
    implemented: bool = False
    rounds: tuple[FixRound, ...] = ()
    claim: ClaimStamp | None = None


class StateItem(NamedTuple):
    """One `item <id>: "…"` block from tech-spec.md § Code state."""

    id: str
    description: str
    status: str  # DONE | PARTIAL | TODO | unknown


class HotfixTarget(NamedTuple):
    """A hotfix spec.md's declared lineage targets: the patched release
    tag and the fixed spec name, verbatim; an undeclared field reads ""."""

    tag: str
    spec: str


class TickEvidence(NamedTuple):
    """task.md's durable tick record: entry counts plus the ids whose
    evidence is missing. `unticked` holds open (not ticked, not struck)
    task ids in file order; `noteless` holds ticked ids whose entry block
    carries no done-proof sub-line."""

    total: int
    ticked: int
    struck: int
    unticked: list[str]
    noteless: list[str]


def spec_status(spec_md: str) -> str | None:
    """The spec.md lifecycle word (draft/approved/active/done), lowercased;
    None when no line-leading `**Status**:` header exists."""
    m = STATUS_LINE.search(spec_md)
    return m.group(1).lower() if m else None


def spec_effort(spec_md: str) -> str:
    """The spec.md effort tier (standard/large), lowercased; "large"
    when no `**Effort**:` header exists or the word is not a known tier —
    the full-wave behavior, so docsets without the field keep the
    existing graph."""
    m = EFFORT_LINE.search(spec_md) if spec_md else None
    word = m.group(1).lower() if m else ""
    word = EFFORT_ALIASES.get(word, word)
    return word if word in EFFORT_TIERS else "large"


def spec_tier(spec_md: str) -> str:
    """The spec.md contract tier — `tiny` (one file: the task list lives
    in spec.md § Tasks) or `full` (the seven-file docset). Absent or
    unknown reads `full`: docsets without the field keep the full graph."""
    m = TIER_LINE.search(spec_md) if spec_md else None
    word = m.group(1).lower() if m else ""
    return word if word in ("tiny", "full") else "full"


def spec_mode(spec_md: str) -> str:
    """The spec.md run mode as written — `fast` or `standard`; absent or
    unknown reads `standard`. Whether the tier honors it is the engine's
    call (fast holds only at Tier: tiny)."""
    m = MODE_LINE.search(spec_md) if spec_md else None
    word = m.group(1).lower() if m else ""
    return word if word in ("fast", "standard") else "standard"


def spec_type(spec_md: str) -> str:
    """The spec.md work type, lowercased — one of WORK_TYPES, or the
    unknown word as written. "feature" when no `**Type**:` header exists."""
    m = TYPE_LINE.search(spec_md) if spec_md else None
    return m.group(1).lower() if m else "feature"


def hotfix_target(spec_md: str) -> HotfixTarget:
    """The declared `**Hotfix for**` tag and `**Fixes spec**` name from
    spec.md, empty when a header (or its value) is absent. Whether these
    headers belong on this spec is the checker's verdict, never the
    parser's."""
    if not spec_md:
        return HotfixTarget("", "")
    fm = HOTFIX_FOR_LINE.search(spec_md)
    sm = FIXES_SPEC_LINE.search(spec_md)
    return HotfixTarget(
        fm.group(1).strip().strip("`") if fm else "",
        sm.group(1).strip().strip("`") if sm else "",
    )


def spec_depends(spec_md: str) -> list[str]:
    """Spec names on the `**Depends on**:` header, in written order —
    verbatim, so the checker reports a typo instead of dropping it."""
    m = DEPENDS_LINE.search(spec_md) if spec_md else None
    if not m:
        return []
    names = [n.strip().strip("`") for n in m.group(1).split(",")]
    return [n for n in names if n and n.lower() != "none" and n.strip("—–-")]


def tasks_section(spec_md: str) -> str | None:
    """The text of spec.md's `## Tasks` section (the tiny tier's task
    list), or None when the spec carries no such section. Section ends
    at the next `## ` heading."""
    if not spec_md:
        return None
    start = spec_md.find(TASKS_HEADING)
    if start < 0:
        return None
    body = spec_md[start + len(TASKS_HEADING):]
    end = body.find("\n## ")
    return body[:end] if end >= 0 else body


def tiny_task_text(spec_md: str) -> str | None:
    """The tiny tier's task-source text: the § Tasks section wrapped in
    a `## Phase 1` header so task_entries/tick_evidence — the same
    parsers task.md uses — read it unchanged (one grammar, two homes)."""
    section = tasks_section(spec_md)
    if section is None:
        return None
    return "## Phase 1\n" + section.lstrip("\n")


def coverage_floor(spec_md: str, default: int = 80) -> int:
    """The spec.md coverage floor (`**Coverage**: <int>` percent), clamped
    to 0–100; `default` (80) when the header is absent — the minimum line
    coverage audit.py's coverage mode demands over the tasks' intended
    files."""
    m = COVERAGE_FLOOR.search(spec_md) if spec_md else None
    if not m:
        return default
    return max(0, min(100, int(m.group(1))))


def fix_rounds(block: str) -> tuple[FixRound, ...]:
    """A task entry block's fix rounds in round order. The `fix` sub-line
    opens a round with its failure digest; the `fixed` sibling closes it
    with resolution and proof. A close without a matching open keeps an
    empty digest — shape mismatches are the checker's verdict, never the
    parser's."""
    opened: dict[int, FixRound] = {}
    for m in FIX_NOTE_OPEN.finditer(block):
        n = int(m.group(1))
        opened[n] = FixRound(n, m.group(2).strip(), "", "", False)
    for m in FIX_NOTE_CLOSED.finditer(block):
        n = int(m.group(1))
        prior = opened.get(n)
        opened[n] = FixRound(
            n, prior.digest if prior else "",
            m.group(2).strip(), m.group(3).strip(), True)
    return tuple(opened[n] for n in sorted(opened))


def task_entries(task_md: str) -> list[TaskEntry]:
    """Parse task.md's phase sections into TaskEntry records, in file order.

    Only `- [ ]`-anchored blocks inside `## Phase …` sections count — the
    burndown table and the Conventions examples must not become entries.
    An entry's continuation is the indented lines directly under it; the
    block ends at the first blank line (never a blank-line-separated
    paragraph after the entry)."""
    entries: list[TaskEntry] = []
    for sec in re.split(r"^## ", task_md, flags=re.M):
        header = sec.split("\n", 1)[0].strip()
        # `## Tasks` is the tiny tier's phase-1 section inside spec.md
        # task.md parsers read either home unchanged. An unnumbered
        # `## Phase …` header keeps phase=None.
        if header == "Tasks":
            phase = 1
        elif header.lower().startswith("phase"):
            hm = re.match(r"phase\s+(\d+)", header, re.I)
            phase = int(hm.group(1)) if hm else None
        else:
            continue
        for block in re.split(r"^(?=- \[)", sec, flags=re.M):
            if not re.match(r"- \[", block):
                continue
            block = block.split("\n\n", 1)[0]
            first_line = block.split("\n", 1)[0]
            own = TASK_ID.match(block)
            fix = FIX_ROUND.search(block)
            cm = CLAIM_NOTE.search(block)
            entries.append(TaskEntry(
                id=own.group(1) if own else None,
                phase=phase,
                block=block,
                first_line=first_line,
                done=bool(TASK_DONE.match(block)),
                claimed="(in-progress)" in block,
                struck=bool(STRIKETHROUGH.search(first_line)),
                parallel="[P]" in first_line,
                after=AFTER_REF.findall(block),
                fix_round=int(fix.group(1)) if fix else None,
                implemented="(implemented)" in block and fix is None,
                rounds=fix_rounds(block),
                claim=ClaimStamp(cm.group(1), cm.group(2)) if cm else None,
            ))
    return entries


def delivery_state(task_md: str) -> tuple[str, str | None]:
    """(state, evidence) for task.md's Delivered header line.

    delivered = a commit record exists — evidence is the recorded sha, or
    `-` for the explicit non-git skip; pending = a Delivered line exists
    but records no commit (the scaffold's placeholder reads pending, never
    delivered); missing = no Delivered line at all. evidence is None
    unless delivered."""
    if "Delivered" not in task_md:
        return "missing", None
    m = DELIVERED_COMMIT.search(task_md)
    if not m:
        return "pending", None
    return "delivered", m.group(1)


def lifecycle_shas(task_md: str) -> dict[str, str | None]:
    """Exact recorded values for delivered evidence.

    A value is a commit SHA or the explicit non-git dash. None means the
    marker has not been recorded yet. These values are inputs to integrity
    checks, not themselves proof: a hex string must still resolve to a commit.
    """
    out: dict[str, str | None] = {}
    for name, pattern in LIFECYCLE_VALUES.items():
        m = pattern.search(task_md)
        out[name] = m.group(1) if m else None
    return out


def approval_sha(spec_dir: Path) -> str | None:
    """The `**Approved-at**` commit freeze.py recorded at approval —
    approvals/approval.md's anchor for the approved docset. None when no
    freeze exists yet (pre-approval) or the file is unreadable; never the
    dash form (a non-git freeze records `-`, which names no diff base)."""
    try:
        text = (Path(spec_dir) / "approvals" / "approval.md").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text:
        return None
    m = APPROVED_AT.search(text)
    return m.group(1) if m else None


def tick_evidence(task_md: str) -> TickEvidence:
    """The durable task-tick evidence for the tick-commit transition: the
    transition is fully evidenced only when `unticked` and `noteless` are
    both empty — every task ticked or struck, every tick carrying its
    `done <date> — <proof>` sub-line."""
    entries = task_entries(task_md)
    return TickEvidence(
        total=len(entries),
        ticked=sum(1 for e in entries if e.done),
        struck=sum(1 for e in entries if e.struck),
        unticked=[e.id for e in entries
                  if e.id and not e.done and not e.struck],
        noteless=[e.id for e in entries
                  if e.id and e.done and not DONE_NOTE.search(e.block)],
    )


def failure_signature_run(note_text: str) -> tuple[str | None, int]:
    """(command, trailing-run length) of a task's fix-round evidence:
    each `## Fix round n` section a `mark.py fail` wrote holds the
    failing command and its output verbatim, the command on the first
    `$ `-prefixed line — that line is the round's failure signature.
    The run counts how many trailing rounds (highest numbers backward)
    share one command; a round with no command line ends the run, and
    (None, 0) means the newest round carries none.
    D-044: a repeated signature means another round, or a stronger
    model, re-runs the same failing command — the plan is the suspect,
    not the model."""
    sigs: dict[int, str | None] = {}
    current: int | None = None
    for ln in note_text.splitlines():
        m = re.match(r"^## Fix round (\d+)\b", ln)
        if m:
            current = int(m.group(1))
            sigs.setdefault(current, None)
            continue
        # the developer may append its own sections after a round
        if ln.startswith("## "):
            current = None
            continue
        if current is not None and sigs[current] is None \
                and ln.startswith("$ "):
            sigs[current] = ln.strip()
    if not sigs:
        return None, 0
    order = sorted(sigs, reverse=True)
    last = sigs[order[0]]
    if last is None:
        return None, 0
    run = 0
    for n in order:
        if sigs[n] != last:
            break
        run += 1
    return last, run


def digests_on_file(spec_dir: Path | str) -> dict[str, dict]:
    """Per task id, the developer digest the run ledger names. `state`
    is `valid` — the digest's fields plus `wave` and `path` — or the
    refusal that holds the task: `malformed`, the file fails its schema
    or its `provenance:` line is one no ledger row vouches for, or
    `unverified` — no `wave` or `claim` row records the file's digest,
    so nothing vouches its content. The newest file the sweep leaves
    valid is the task's; a refused file newer than every valid one holds
    the task in its place (at one wave the valid file outranks it). An
    unverified file holds only while nothing vouches a digest for the
    task — a hand-placed or dead-run file beside a vouched one is
    ignored. Pure read, in the state the sweep would leave: a missing or
    unreadable digests/ tree is an empty dict."""
    base = Path(spec_dir) / DIGEST_DIR
    if not base.is_dir():
        return {}
    rows = ledger_rows(spec_dir)
    seen: dict[str, list[tuple[int, int, dict]]] = {}
    for path in sorted(base.glob("wave-*/implementer-*.md")):
        wave = re.match(r"wave-(\d+)", path.parent.name)
        stem = DIGEST_FILE.match(path.name)
        if not wave or not stem:
            continue
        on_wave = int(wave.group(1))
        text = _read_doc_text(path) or ""
        refusal = _refusal(path, on_wave, rows, text)
        if refusal is not None:
            rank = 0 if refusal.state == DIGEST_UNVERIFIED else 1
            seen.setdefault(stem.group(1), []).append((on_wave, rank, dict(
                state=refusal.state, wave=on_wave, path=str(path),
                problems=refusal.problems)))
            continue
        parsed = digests.parse("developer", None, text)
        seen.setdefault(parsed["task"], []).append((
            on_wave, 2, dict(parsed, state=DIGEST_VALID, wave=on_wave,
                             path=str(path))))
    named: dict[str, dict] = {}
    for task_id, items in seen.items():
        vouched = max((w for w, r, _e in items if r == 2), default=-1)
        holds = [(w, r, e) for w, r, e in items
                 if r == 2 or (r == 1 and w > vouched)
                 or (r == 0 and vouched < 0)]
        named[task_id] = max(holds, key=lambda item: (item[0], item[1]))[2]
    return named


def latest_digest(spec_dir: Path | str, task_id: str) -> dict | None:
    """The developer digest the run ledger names for `task_id` — one of
    digests_on_file's entries — or None when it names none for it: a
    file alone proves nothing."""
    return digests_on_file(spec_dir).get(task_id)


# ---------------------------------------------------------------------------
# The run ledger (spec-build D-055, spec-design D-075).
# specs/<name>/runs/ledger.jsonl: append-only, one row per orchestrator
# event, written only by orchestrator scripts — each append under the
# spec's task lock, one line per write. Evidence, never status: no
# reader takes workflow state from it. A digest file is its agent's
# alone; the provenance line is the orchestrator's one append, built
# from the ledger row that recorded the request, and a line no row
# vouches for makes its file malformed.
# ---------------------------------------------------------------------------

LEDGER_DIR = "runs"
LEDGER_NAME = "ledger.jsonl"
LEDGER_FIELDS = ("run", "wave", "task", "node", "role", "lens", "stem",
                 "payload", "input", "model", "harness", "digest",
                 "outcome", "tools-reported")
UNKNOWN_HARNESS = "unknown"
INHERIT_MODEL = "inherit"
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
PROVENANCE_KEY = "provenance"
PROVENANCE_FIELDS = ("run", "role", "lens", "model", "harness",
                     "payload", "input", "recorded")
# `tools-reported` rides a provenance line and its row only when the
# digest reports tools: the agent's claim of what it held, never a fact.
TOOLS_FIELD = "tools-reported"
CAPABILITY_MISSING = "capability_missing"
PROVENANCE_NONE = "none"
PROVENANCE_SEP = re.compile(r"[ \t]*\u00b7[ \t]*")
UNVERIFIED = "unverified"
UNVOUCHED_PROBLEM = ("it carries no `provenance:` line and no ledger row "
                     "records its digest — nothing vouches its content")

# A digest file's stem names the payload that asked for it and the
# schema its role validates with; a role with several grammars takes
# the request's lens as its variant when the ledger has one.
DIGEST_SCHEMAS = {
    "implementer": ("developer", None),
    "tech": ("architect", "tech"),
    "planner": ("architect", "plan"),
    "task-breaker": ("architect", "tasks"),
    "designer": ("architect", None),
    "analyst": ("analyst", "intent"),
    "researcher": ("analyst", "research"),
    "constitution": ("analyst", "constitution"),
    "qa": ("tester", None),
}
WAVE_DIR_NAME = re.compile(r"wave-(\d+)$")


def sha12(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def file_sha(path: Path | str) -> str | None:
    try:
        return sha12(Path(path).read_bytes())
    except OSError:
        return None


def digest_sha(text: str) -> str:
    """sha256-12 of a digest file's own content — every `provenance:`
    line removed and a newline ensured at the end: what is left once
    the orchestrator's appended line is stripped back off."""
    body = "\n".join(ln for ln in text.split("\n")
                     if not ln.startswith(PROVENANCE_KEY + ":"))
    return sha12((body if body.endswith("\n") else body + "\n")
                 .encode("utf-8"))


def brief_model(brief: Path | str) -> str | None:
    """The brief's frontmatter `model:` value; `inherit` when the
    frontmatter names none; None when there is no frontmatter to
    read."""
    raw = _read_doc_text(brief)
    front = FRONTMATTER.match(raw) if raw else None
    if front is None:
        return None
    m = re.search(r"^model:[ \t]*(\S+)", front.group(0), re.M)
    return m.group(1) if m else INHERIT_MODEL


def ledger_path(spec_dir: Path | str) -> Path:
    return Path(spec_dir) / LEDGER_DIR / LEDGER_NAME


# The chain fields ride a row but are never part of its content hash
LEDGER_CHAIN_FIELDS = ("prev", "chain")


def row_hash(row: dict) -> str:
    """The content hash one ledger row chains from: sha256-12 of the
    row's sorted-key JSON without the chain fields — stable whatever
    `prev` the row itself carries."""
    canonical = {k: row[k] for k in sorted(row)
                 if k not in LEDGER_CHAIN_FIELDS}
    return sha12(json.dumps(canonical, sort_keys=True).encode("utf-8"))


def ledger_rows(spec_dir: Path | str) -> list[dict]:
    """The ledger's rows in the order they were appended, each carrying
    `prev` (None for a row written before the chain existed); a line
    that is not a JSON object is not a row."""
    rows: list[dict] = []
    for line in (_read_doc_text(ledger_path(spec_dir)) or "").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            row.setdefault("prev", None)
            rows.append(row)
    return rows


def ledger_chain_problems(spec_dir: Path | str) -> list[str]:
    """Where the ledger's row chain is broken, one `line <n>: <why>`
    each: a row appended without its `prev`, or whose `prev` no longer
    matches the row before it — an edit. Rows before the first chained
    one are a pre-chain ledger and read fine. The chain detects
    tampering, it cannot prevent it: a ledger rewritten whole chains
    consistently."""
    rows: list[tuple[int, dict | None]] = []
    for n, line in enumerate(
            (_read_doc_text(ledger_path(spec_dir)) or "").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            rows.append((n, None))
            continue
        if isinstance(row, dict):
            rows.append((n, row))
    problems: list[str] = []
    chained = False
    for i, (n, row) in enumerate(rows):
        if row is None:
            problems.append(f"line {n}: not a ledger row — the line "
                            "is not JSON")
            continue
        prev = row.get("prev")
        if prev is not None:
            chained = True
        elif chained:
            problems.append(f"line {n}: appended without its `prev` — "
                            "the row is not chained to the row before it")
            continue
        if chained:
            before = rows[i - 1][1] if i else None
            expected = row_hash(before) if before is not None else None
            if prev != expected:
                why = ("names no row before it" if expected is None
                       else "does not match the row before it — the row "
                            "was edited after it was written")
                problems.append(f"line {n}: its `prev` {why}")
    return problems


def ledger_row(skill: str, event: str, **fields) -> dict:
    """One event's row: `ts`, `skill`, `event`, then whichever of the
    ledger's fields the event carries, in the ledger's order — a null
    field is omitted, never written."""
    unknown = set(fields) - set(LEDGER_FIELDS)
    if unknown:
        raise KeyError(f"not run-ledger fields: {', '.join(sorted(unknown))}")
    row = {"ts": utc_now().isoformat(),
           "skill": skill, "event": event}
    row.update({name: fields[name] for name in LEDGER_FIELDS
                if fields.get(name) is not None})
    return row


def ledger_append(spec_dir: Path | str, row: dict) -> None:
    """Append one row as one line, chained to the ledger's last line:
    the row carries `prev`, the row_hash of the row before it, None on
    an empty ledger. The caller holds the spec's task lock, so two
    writers never interleave and a reader never sees a partial line."""
    path = ledger_path(spec_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = None
    try:
        written = [ln for ln in path.read_text(
            encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    except OSError:
        written = []
    if written:
        try:
            prev = row_hash(json.loads(written[-1]))
        except ValueError:
            prev = None
    fd = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_APPEND)
    try:
        os.write(fd, (json.dumps({**row, "prev": prev}) + "\n")
                .encode("utf-8"))
    finally:
        os.close(fd)


def ledger_event(spec_dir: Path | str, *rows: dict) -> bool:
    """Append rows under the spec's task lock; False, with a warning,
    when they could not be written — the ledger is evidence and never
    holds the workflow back."""
    if not rows:
        return True
    try:
        with task_lock(spec_dir):
            for row in rows:
                ledger_append(spec_dir, row)
    except (TaskLockBusy, OSError) as exc:
        print(f"warning: run ledger not written — {exc}", file=sys.stderr)
        return False
    return True


# ---------------------------------------------------------------------------
# Run budgets (spec-build D-059, spec-design D-080). Two countable
# ceilings on an unattended execute run — implementer spawns and
# wall-clock minutes — read from the ledger's `claim` rows. Spawns
# count twice, over the run and over the spec's whole ledger, so a new
# run id restarts the run's count and never the spec's; minutes count
# per run alone, since an unattended span is one run. Tokens are not a
# budget: no harness reports them to the kit. A budget of 0 is none.
# ---------------------------------------------------------------------------

BUDGET_SPAWNS = 30
BUDGET_MINUTES = 120
BUDGET_STOP = "AWAITING HUMAN: run budget — "
BUDGET_STOP_TAIL = (
    "   why it matters (medium): the budget is the ceiling an "
    "unattended",
    "   run may spend — past it every spawn may be a task failing "
    "again,",
    "   costing time and tokens the kit cannot count; a spec with "
    "more",
    "   tasks than the budget needs a higher one",
    "   ways on: raise a budget with --budget-spawns N / "
    "--budget-minutes N",
    "   on the next run or claim (0 lifts it), or adjudicate the "
    "tasks",
    "   that keep failing (mark.py fail with the evidence, "
    "release, or",
    "   drop with a D-###) before running again")


def utc_now() -> datetime.datetime:
    """The run ledger's clock, UTC: the stamp of every row and the time
    a run budget counts to. The one place both read it, so a test
    moves the clock instead of waiting."""
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_ts(ts) -> datetime.datetime | None:
    """A ledger row's `ts` as an aware datetime, a naive stamp read as
    UTC; None when it is missing or does not parse."""
    try:
        then = datetime.datetime.fromisoformat(
            str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return then if then.tzinfo else then.replace(
        tzinfo=datetime.timezone.utc)


def budget_spent(spec_dir: Path | str, run_id: str | None,
                 now: datetime.datetime | None = None) -> dict:
    """What the run budgets count, read from the spec's run ledger:
    `{"run": {"spawns": n, "minutes": m}, "spec": {"spawns": n}}`.
    Spawns are the implementer `claim` rows: the spec's every one, the
    run's those carrying `run_id`. The minutes are the run's alone,
    from its first claim row that carries a readable `ts` to `now`
    (the kit's clock unless a test moves it). A run with no such row
    has spent no minutes; a row whose `ts` is missing or does not
    parse is still a spawn."""
    now = now if now is not None else utc_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    spent = {"run": {"spawns": 0, "minutes": 0}, "spec": {"spawns": 0}}
    started: datetime.datetime | None = None
    for row in ledger_rows(spec_dir):
        if row.get("event") != "claim":
            continue
        spent["spec"]["spawns"] += 1
        if run_id and row.get("run") == run_id:
            spent["run"]["spawns"] += 1
            then = _parse_ts(row.get("ts"))
            if started is None and then is not None:
                started = then
    if started is not None:
        spent["run"]["minutes"] = max(
            0, int((now - started).total_seconds() // 60))
    return spent


def budget_stop(spec_dir: Path | str, run_id: str | None,
                spawns: int, minutes: int,
                now: datetime.datetime | None = None) -> list[str]:
    """The lines a spent run budget prints — empty while every budget
    holds. The first line names the first budget spent, in the order
    the run's spawns, the run's minutes, the spec's spawns; the next
    name the others spent; then come why it matters and the two ways
    on (the kit's consequential stop)."""
    spent = budget_spent(spec_dir, run_id, now)
    over = [(f"{kind} in this {scope}", spent[scope][kind], limit)
            for scope, kind, limit in (("run", "spawns", spawns),
                                       ("run", "minutes", minutes),
                                       ("spec", "spawns", spawns))
            if limit and spent[scope][kind] >= limit]
    if not over:
        return []
    what, used, limit = over[0]
    lines = [f"{BUDGET_STOP}{what} used {used} of {limit}"]
    lines += [f"   also spent: {what} used {used} of {limit}"
              for what, used, limit in over[1:]]
    return lines + list(BUDGET_STOP_TAIL)


def budget_overrun(spec_dir: Path | str, run_id: str | None,
                   spawns: int, needed: int,
                   now: datetime.datetime | None = None) -> list[str]:
    """The lines for a wave whose `needed` spawns would take a spawn
    budget past its limit — empty while the wave fits, in every budget.
    The first line names the first budget the wave would pass, the
    run's spawns before the spec's, as `would use <n> of <limit>`;
    then one line for the wave's need, what remains and the shortfall;
    then why it matters and the ways on. Minutes are never compared: no
    wave can be cut to the time it will take."""
    if not needed:
        return []
    spent = budget_spent(spec_dir, run_id, now)
    over = [(f"spawns in this {scope}", spent[scope]["spawns"] + needed,
             spawns, spawns - spent[scope]["spawns"])
            for scope in ("run", "spec")
            if spawns and spent[scope]["spawns"] + needed > spawns]
    if not over:
        return []
    what, would, limit, left = over[0]
    lines = [f"{BUDGET_STOP}{what} would use {would} of {limit}"]
    lines += [f"   also over: {what} would use {would} of {limit}"
              for what, would, limit, _left in over[1:]]
    spawn = "spawn" if needed == 1 else "spawns"
    lines.append(f"   this wave needs {needed} {spawn} of the {left} "
                 f"remaining: {needed - left} short")
    return lines + list(BUDGET_STOP_TAIL)


def digest_schema(stem: str,
                  lens: str | None = None) -> tuple[str, str | None] | None:
    """(schema role, grammar variant) a digest file's stem names, or
    None for a file no role's digest is named as."""
    role = "implementer" if stem.startswith("implementer-") else stem
    if role not in DIGEST_SCHEMAS:
        return None
    schema, default = DIGEST_SCHEMAS[role]
    return schema, (lens if lens in digests.GRAMMARS[schema] else default)


def tools_reported(reported: set[str]) -> str | None:
    """A report as a ledger row's `tools-reported` value: the names
    comma-joined; None — omitted, never written — when none came."""
    return ", ".join(sorted(reported)) or None


def provenance_line(row: dict) -> str:
    """The line the sweep appends to a digest file, built from the
    `digest` row that vouches for it and nothing else."""
    values = (row.get("run") or PROVENANCE_NONE,
              row.get("role") or PROVENANCE_NONE,
              row.get("lens") or PROVENANCE_NONE,
              row.get("model") or PROVENANCE_NONE,
              row.get("harness") or UNKNOWN_HARNESS,
              row.get("payload") or PROVENANCE_NONE,
              row.get("input") or PROVENANCE_NONE,
              row["ts"])
    line = (PROVENANCE_KEY + ": " + " \u00b7 ".join(
        f"{name} {value}"
        for name, value in zip(PROVENANCE_FIELDS, values)))
    tools = row.get(TOOLS_FIELD)
    return f"{line} \u00b7 {TOOLS_FIELD} {tools}" if tools else line


def _provenance_verifies(line: str, rows: list[dict], wave: int,
                         stem: str, text: str) -> bool:
    claimed: dict[str, str] = {}
    for segment in PROVENANCE_SEP.split(line[len(PROVENANCE_KEY) + 1:]):
        key, sep, value = segment.strip().partition(" ")
        if not sep or key in claimed:
            return False
        claimed[key] = value
    if tuple(claimed) not in (PROVENANCE_FIELDS,
                              PROVENANCE_FIELDS + (TOOLS_FIELD,)):
        return False
    digest = digest_sha(text)
    return any(row.get("event") == "digest" and row.get("wave") == wave
               and row.get("stem") == stem and row.get("digest") == digest
               and provenance_line(row) == line for row in rows)


def provenance_problems(text: str, rows: list[dict], wave: int,
                        stem: str) -> list[str]:
    """Why a digest file's `provenance:` line is not the orchestrator's:
    empty when the file carries none, or exactly one a `digest` row
    vouches for."""
    lines = [ln for ln in text.split("\n")
             if ln.startswith(PROVENANCE_KEY + ":")]
    if not lines:
        return []
    if len(lines) > 1:
        return [f"{len(lines)} `provenance:` lines — one expected"]
    if _provenance_verifies(lines[0], rows, wave, stem, text):
        return []
    return ["its `provenance:` line is not one the run ledger records "
            "— the line is the orchestrator's to write"]


def _append_provenance(path: Path, line: str) -> None:
    with open(path, "rb") as f:
        raw = f.read()
    lead = b"" if not raw or raw.endswith(b"\n") else b"\n"
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND)
    try:
        os.write(fd, lead + line.encode("utf-8"))
    finally:
        os.close(fd)


class RefusedDigest(NamedTuple):
    """What the orchestrator refuses a digest file for: the sighting's
    `state`, the ledger outcome it is recorded under, the problems that
    name it, and the tools the file reported."""

    state: str
    outcome: str
    problems: list[str]
    reported: set[str]


def _digest_request(rows: list[dict], wave: int, stem: str) -> dict | None:
    """The ledger's record of the request a digest file answers: the
    `wave` row for its wave and stem — the payload the emit wrote — or,
    when none, the `claim` row of the same wave and stem, which records
    the task claimed there. Neither: nothing vouches the file."""
    for event in ("wave", "claim"):
        found = next((row for row in reversed(rows)
                      if row.get("event") == event
                      and row.get("wave") == wave
                      and row.get("stem") == stem), None)
        if found is not None:
            return found
    return None


def _refusal(path: Path, wave: int, rows: list[dict],
             text: str) -> RefusedDigest | None:
    """Why the orchestrator refuses the digest file at `path`, or None
    for one it does not: no role's digest, valid with its tools, already
    carrying the line a ledger row vouches for, or — line-less — a
    digest an emit or claim asked for, which the sweep vouches. One
    definition for the sweep, which records it, and the state reader,
    which only names it."""
    schema = digest_schema(path.stem)
    if schema is None:
        return None
    role = schema[0]
    if any(ln.startswith(PROVENANCE_KEY + ":") for ln in text.split("\n")):
        unvouched = provenance_problems(text, rows, wave, path.stem)
        if unvouched:
            return RefusedDigest(DIGEST_MALFORMED, UNVERIFIED, unvouched,
                                 set())
        # the line itself predates the grammar read: validate the body,
        # so a vouched file whose body the current schema refuses is a
        # malformed sighting, never a crash beside the readers
        body = "\n".join(ln for ln in text.split("\n")
                         if not ln.startswith(PROVENANCE_KEY + ":"))
        request = next((row for row in reversed(rows)
                        if row.get("event") == "wave"
                        and row.get("wave") == wave
                        and row.get("stem") == path.stem), {})
        role, variant = digest_schema(path.stem, request.get("lens"))
        problems = digests.validate(role, variant, body)
        if problems:
            return RefusedDigest(DIGEST_MALFORMED, DIGEST_MALFORMED,
                                 problems, set())
        return None
    request = next((row for row in reversed(rows)
                    if row.get("event") == "wave"
                    and row.get("wave") == wave
                    and row.get("stem") == path.stem), {})
    variant = digest_schema(path.stem, request.get("lens"))[1]
    parsed = digests.parse(role, variant, text)
    problems = digests.validate(role, variant, text) if parsed is None else []
    named = DIGEST_FILE.match(path.name)
    if not problems and role == "developer":
        if named is None:
            problems = ["its stem names no task — a developer digest "
                        "file is implementer-T###.md"]
        elif parsed["task"] != named.group(1):
            problems = [f"it names task {parsed['task']}, "
                        f"not {named.group(1)}"]
    if problems:
        return RefusedDigest(DIGEST_MALFORMED, DIGEST_MALFORMED, problems,
                             set())
    if _digest_request(rows, wave, path.stem) is None:
        return RefusedDigest(DIGEST_UNVERIFIED, UNVERIFIED,
                             [UNVOUCHED_PROBLEM], set())
    reported = digests.tools_report(text)
    # the developer's report is mark.py land's to refuse: it names the
    # task and its release, and no file lands past it
    missing = () if role == "developer" else digests.tools_missing(
        role, reported)
    if missing:
        return RefusedDigest(
            CAPABILITY_MISSING, ", ".join(missing),
            [digests.tools_refusal(role, reported, missing)], reported)
    return None


def digest_refusal_line(seen: dict) -> str:
    """How a refused digest file is named, after `digest: ` — the
    sweep's line and the run's stop share it."""
    at = f" at {seen['path']}"
    if seen["state"] == CAPABILITY_MISSING:
        return (f"{seen['problems'][0]} —{at}: no provenance line is "
                "written and nothing reads this digest")
    return (f"{seen['state']}{at} — {'; '.join(seen['problems'])} — fix "
            "and run again: re-spawn the same payload to rewrite its "
            "digest file")


def _sweep_digest(path: Path, wave: int, rows: list[dict],
                  skill: str) -> tuple[dict | None, dict | None]:
    """(malformed sighting, appended row) for one digest file under
    digests/wave-<n>/ — (None, None) for a file that is no role's
    digest, already carries the line a ledger row vouches for, or was
    refused by the capability handshake."""
    schema = digest_schema(path.stem)
    text = _read_doc_text(path) if schema else None
    if schema is None or text is None:
        return None, None
    role = schema[0]
    payload_role = "implementer" if path.stem.startswith("implementer-") \
        else path.stem
    request = next((row for row in reversed(rows)
                    if row.get("event") == "wave"
                    and row.get("wave") == wave
                    and row.get("stem") == path.stem), {})
    named = DIGEST_FILE.match(path.name)
    facts = {name: request.get(name) or fallback for name, fallback in (
        ("run", None), ("role", payload_role), ("lens", None),
        ("payload", None), ("input", None), ("model", None),
        ("harness", UNKNOWN_HARNESS))}
    facts.update(wave=wave, task=named.group(1) if named else None,
                 stem=path.stem, digest=digest_sha(text))

    def recorded(event: str, outcome: str) -> bool:
        return any(row.get("event") == event
                   and row.get("outcome") == outcome
                   and all(row.get(k) == facts[k]
                           for k in ("wave", "stem", "digest"))
                   for row in rows)

    refusal = _refusal(path, wave, rows, text)
    if refusal is not None:
        seen = dict(state=refusal.state, wave=wave, path=str(path),
                    problems=refusal.problems)
        event = (CAPABILITY_MISSING if refusal.state == CAPABILITY_MISSING
                 else "digest_malformed")
        if not recorded(event, refusal.outcome):
            ledger_append(path.parents[2], ledger_row(
                skill, event, outcome=refusal.outcome, **facts,
                **{TOOLS_FIELD: tools_reported(refusal.reported)}))
        if refusal.state == CAPABILITY_MISSING:
            print(f"digest: {digest_refusal_line(seen)}", file=sys.stderr)
            return None, None
        return seen, None
    if any(ln.startswith(PROVENANCE_KEY + ":") for ln in text.split("\n")):
        # vouched for: an earlier sweep appended the line
        return None, None
    parsed = digests.parse(
        role, digest_schema(path.stem, facts["lens"])[1], text)
    reported = digests.tools_report(text)
    outcome = (parsed["status"].split(":", 1)[0].strip()
               if role == "developer" else None)
    row = ledger_row(skill, "digest", outcome=outcome, **facts,
                     **{TOOLS_FIELD: tools_reported(reported)})
    ledger_append(path.parents[2], row)
    _append_provenance(path, provenance_line(row) + "\n")
    return None, row


def sweep_digests(spec_dir: Path | str, skill: str,
                  locked: bool = False) -> list[dict]:
    """The orchestrator's provenance sweep over digests/wave-*/. Every
    digest file with no provenance line yet is validated with its
    role's schema; a valid one gains ONE line and a `digest` row —
    both from the `wave` row that recorded the payload it answers,
    when the ledger has one, and from the file's own name when not —
    each carrying the file's `tools:` report as `tools-reported`. A
    malformed file, one whose line no ledger row vouches for, or one no
    `wave` or `claim` row records, is left untouched and recorded as
    `digest_malformed` (once per content). An analyst, architect or
    tester file whose report lacks a required tool is refused: recorded
    as `capability_missing` (once per content), the refusal printed, no
    line written. Returns the refused files as digests_on_file-shaped
    entries. The sweep takes the spec's task lock; `locked` skips that
    for a caller — mark.py land — already holding it, so the judged
    state is the swept state."""
    base = Path(spec_dir) / DIGEST_DIR
    if not base.is_dir():
        return []
    seen: list[dict] = []

    def swept() -> None:
        rows = ledger_rows(spec_dir)
        for path in sorted(base.glob("wave-*/*.md")):
            wave = WAVE_DIR_NAME.fullmatch(path.parent.name)
            if not wave:
                continue
            sighting, row = _sweep_digest(
                path, int(wave.group(1)), rows, skill)
            if sighting is not None:
                seen.append(sighting)
            elif row is not None:
                rows.append(row)

    try:
        if locked:
            swept()
        else:
            with task_lock(spec_dir):
                swept()
    except (TaskLockBusy, OSError) as exc:
        print(f"warning: provenance sweep stopped — {exc}", file=sys.stderr)
    return seen


def refused_digests(spec_dir: Path | str, stems) -> dict[str, dict]:
    """`{stem: sighting}` for each stem in `stems` whose digest — the
    one the run ledger names, the newest file the sweep leaves valid —
    the orchestrator refuses: `state` is malformed, unverified or
    capability_missing, beside `wave`, `path` and `problems`. A stem
    with no file, or whose named digest is valid, is absent; an
    unverified file beside a vouched one is ignored. Pure read: the
    refusal the sweep would name, without sweeping."""
    base = Path(spec_dir) / DIGEST_DIR
    if not base.is_dir():
        return {}
    rows = ledger_rows(spec_dir)
    seen: dict[str, list[tuple[int, int, dict]]] = {}
    for path in base.glob("wave-*/*.md"):
        wave = WAVE_DIR_NAME.fullmatch(path.parent.name)
        if not wave or path.stem not in stems:
            continue
        on_wave = int(wave.group(1))
        text = _read_doc_text(path) or ""
        refusal = _refusal(path, on_wave, rows, text)
        if refusal is not None:
            rank = 0 if refusal.state == DIGEST_UNVERIFIED else 1
            seen.setdefault(path.stem, []).append((on_wave, rank, dict(
                state=refusal.state, wave=on_wave, path=str(path),
                problems=refusal.problems)))
        else:
            seen.setdefault(path.stem, []).append((on_wave, 2, None))
    found: dict[str, dict] = {}
    for stem, items in seen.items():
        vouched = max((w for w, r, _e in items if r == 2), default=-1)
        holds = [(w, r, e) for w, r, e in items
                 if r == 2 or (r == 1 and w > vouched)
                 or (r == 0 and vouched < 0)]
        entry = max(holds, key=lambda item: (item[0], item[1]))[2]
        if entry is not None:
            found[stem] = entry
    return found


def doc_baseline(text: str) -> tuple[str, str] | None:
    """(version, sha) from a doc's baseline header, or None.

    Handles the filled `**Baseline**: <version> @ <sha>` form (backticked
    sha tolerated) and the template's `<version @ commit>` placeholder
    shape — the placeholder carries no real hash, so it reads None and the
    caller decides how to report an unfilled header."""
    m = BASELINE_HEADER.search(text) or BASELINE_PLACEHOLDER.search(text)
    if not m:
        return None
    ver = m.group(1).strip().lstrip(":").strip()
    return ver, m.group(2)


def task_proves(entry_block: str) -> list[str]:
    """The TC ids a task entry's `Proves:` sub-line names, in order."""
    return [tc for m in PROVES_LINE.finditer(entry_block)
            for tc in re.findall(r"\bTC-\d{3}\b", m.group(1))]


def regression_guards(task_md: str) -> set[str]:
    """TC ids listed under task.md's `## Regression guards` section."""
    m = GUARDS_SECTION.search(task_md)
    if not m:
        return set()
    rest = task_md[m.end():]
    end = re.search(r"^## ", rest, re.M)
    return set(GUARD_LINE.findall(rest[:end.start()] if end else rest))


def code_state(tech_md: str) -> str:
    """The body of tech-spec.md's `## Code state` section, up to the next
    H2 — empty when the section is absent."""
    m = CODE_STATE_SECTION.search(tech_md)
    if not m:
        return ""
    rest = tech_md[m.end():]
    end = re.search(r"^## ", rest, re.M)
    return rest[:end.start()] if end else rest


def state_items(tech_md: str) -> list[StateItem]:
    """tech-spec.md § Code state's item list: id, quoted description, and
    status (unknown when the status line is absent or malformed). Blocks
    that don't open with the `item <id>: "…"` shape are skipped, not
    raised."""
    items: list[StateItem] = []
    for block in re.split(r'(?=^item\s+\S+:)', code_state(tech_md),
                          flags=re.M):
        m = STATE_ITEM.match(block)
        if not m:
            continue
        sm = STATE_ITEM_STATUS.search(block)
        items.append(
            StateItem(m.group(1), m.group(2), sm.group(1) if sm else "unknown"))
    return items


def _read_doc_text(path: Path) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _marker_in(text: str) -> bool:
    return any(line.strip() == RESEARCH_SKIP_MARKER
               for line in text.splitlines())


def _section_state(text: str) -> str:
    m = QUESTIONS_SECTION.search(text)
    if m is None:
        return "pending"
    body = text[m.end():]
    end = body.find("\n## ")
    body = body[:end] if end >= 0 else body
    if _marker_in(body):
        return "skip"
    prose = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    if any(line.strip() and not line.strip().startswith("#")
           for line in prose.splitlines()):
        return "done"
    return "pending"


def research_state(spec_dir: Path | str | None) -> str:
    """'done' | 'skip' | 'pending' | 'missing' for the research gate's
    artifact — the `## Questions & options` section of specs/<name>/
    tech-spec.md.

    skip = the section carries the canonical skip-marker line (byte-exact,
    em dash — RESEARCH_SKIP_MARKER; the marker wins over prose since
    writing it is the orchestrator's explicit record). done = the section
    holds real (non-marker, non-heading) content. pending = tech-spec.md
    exists but the section is absent or empty — the gate stays
    undetermined. missing = no tech-spec.md.

    A pre-migration docset keeps its research.md: while the section has
    not been authored, the legacy file's marker/content resolves the gate
    the old way (archived history is never migrated). A resolved section
    wins, so a leftover research.md beside a migrated docset is inert."""
    if spec_dir is None:
        return "missing"
    base = Path(spec_dir)
    tech = _read_doc_text(base / "tech-spec.md")
    if tech is not None and QUESTIONS_SECTION.search(tech):
        return _section_state(tech)
    legacy = _read_doc_text(base / "research.md")
    if legacy is not None:
        if _marker_in(legacy):
            return "skip"
        if not legacy.strip():
            return "pending"
        return "done"
    return "missing" if tech is None else "pending"


def defined_ids(text: str) -> dict[str, set[str]]:
    """IDs defined in one file's text, per family: {"FR": {"FR-001", …}, …}.

    A definition is the family's line shape in DEFINITIONS; a mere mention
    in prose never defines."""
    out: dict[str, set[str]] = {kind: set() for kind in DEFINITIONS}
    for line in text.splitlines():
        stripped = line.strip()
        for kind, pat in DEFINITIONS.items():
            m = pat.match(stripped)
            if m:
                out[kind].add(m.group(1))
    return out


def next_ids(texts: dict[str, str]) -> dict[str, str]:
    """Next free ID per family — the append-scope helper behind check.py
    --next-ids. IDs are never renumbered, so a collision is the only
    failure mode to prevent. Missing/empty sources allocate the first ID."""
    def nxt(pat: str, text: str, fmt: str) -> str:
        nums = [int(m) for m in re.findall(pat, text)]
        return fmt.format((max(nums) + 1) if nums else 1)

    return {
        "FR": nxt(r"FR-(\d{3})", texts.get("spec.md", ""), "FR-{:03d}"),
        "NFR": nxt(r"NFR-(\d{3})", texts.get("spec.md", ""), "NFR-{:03d}"),
        "AC": nxt(r"\bAC(\d+)\b", texts.get("spec.md", ""), "AC{}"),
        "US": nxt(r"\bUS(\d+)\b", texts.get("spec.md", ""), "US{}"),
        "T": nxt(r"\bT(\d{3})\b", texts.get("task.md", ""), "T{:03d}"),
        "TC": nxt(r"TC-(\d{3})", texts.get("test.md", ""), "TC-{:03d}"),
        "D": nxt(r"D-(\d{3})", texts.get("tech-spec.md", ""), "D-{:03d}"),
    }


PATH_EXTENSION = re.compile(r"\.[A-Za-z0-9]{1,12}$")


def _pathish(span: str) -> bool:
    span = span.strip().strip("'\"")
    return bool(span) and " " not in span and "://" not in span and (
        "/" in span or span.endswith("/") or PATH_EXTENSION.search(span)
    )


def _normalize_path(span: str) -> str:
    span = span.strip().strip("'\"")
    if span.startswith("./"):
        span = span[2:]
    return span.rstrip("/")


def task_touches(entry: TaskEntry) -> list[str]:
    """Intended file/directory/glob touches for one task.

    Reads the complete entry, not only its first line. Explicit `Touches:`
    bullets are authoritative; path-shaped backticks remain supported
    so existing docsets do not silently lose overlap detection.
    """
    touches: set[str] = set()
    in_touches = False
    for line in entry.block.splitlines():
        if re.match(r"^\s*-\s*Touches:\s*$", line):
            in_touches = True
            continue
        if in_touches:
            if not line.strip():
                break
            m = re.match(r"^\s*-\s+(.*)$", line)
            if not m:
                break
            for span in re.findall(r"`([^`]+)`", m.group(1)):
                if _pathish(span):
                    touches.add(_normalize_path(span))
            continue
        for span in re.findall(r"`([^`]+)`", line):
            if _pathish(span):
                touches.add(_normalize_path(span))
    return sorted(touches)


def paths_overlap(left: str, right: str) -> bool:
    """Conservative overlap for exact paths, directories, and glob prefixes."""
    a, b = _normalize_path(left), _normalize_path(right)
    if not a or not b:
        return False
    if a == b:
        return True
    if a.startswith(b + "/") or b.startswith(a + "/"):
        return True

    def prefix(path: str) -> str | None:
        m = re.search(r"[*?\[]", path)
        return path[:m.start()] if m else None

    # a leading wildcard has the empty prefix: it can match anything
    ap, bp = prefix(a), prefix(b)
    if ap is not None and bp is not None:
        return ap.startswith(bp) or bp.startswith(ap)
    if ap is not None:
        return b.startswith(ap)
    if bp is not None:
        return a.startswith(bp)
    return False


# The spec-discover handoff tree, beside the specs tree.
HANDOFF_DIR = "brainstorms"


def doc_tree_prefixes(repo: Path | str, specs_root: Path | str) -> list[str]:
    """Repo-relative prefixes (trailing slash) of the kit's own doc
    trees — the specs tree and the brainstorm handoff dir beside it. A
    commit confined to them moves HEAD without moving the code a
    baseline was probed against. Empty when the specs tree is the repo
    root or sits outside the repo: nothing can be told apart from code."""
    specs_root = Path(specs_root).resolve()
    prefixes: list[str] = []
    for tree in (specs_root, specs_root.parent / HANDOFF_DIR):
        try:
            rel = tree.relative_to(Path(repo).resolve()).as_posix()
        except ValueError:
            return []
        if rel == ".":
            return []
        prefixes.append(rel + "/")
    return prefixes


def code_paths(paths: list[str], prefixes: list[str]) -> list[str]:
    """The paths outside every doc-tree prefix — the only ones that can
    move a code citation."""
    return [p for p in paths if not p.startswith(tuple(prefixes))]


def git_available(repo: Path | str) -> bool:
    """True iff `repo` sits inside a working git repository — the
    availability probe every git-derived verdict consults first. A missing
    or broken git degrades to False (callers print an explicit SKIPPED
    notice; a failing probe is never read as a clean result)."""
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--git-dir"],
            capture_output=True, text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def head_sha(repo: Path | str) -> str | None:
    """The repo's short HEAD sha (lowercased), or None when there is no
    repository, no history, or git is unavailable."""
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip().lower() or None


def diff_paths(repo: Path | str, base: str, head: str) -> list[str] | None:
    """Paths changed between two commits (`base..head`), sorted — the
    delta scope for a stale-baseline re-ground (graph.py's DELTA
    RE-GROUND payload). None when git cannot answer (no repository,
    unknown sha, git unavailable): callers degrade to a full re-ground,
    never to an empty-delta verdict. Committed range only, matching the
    converge staleness comparison (baseline sha vs HEAD); uncommitted
    work is the audits' business (audit.py changed_paths), not the
    Code state's."""
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "diff", "--name-only", base, head],
            capture_output=True, text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return sorted({l.strip() for l in r.stdout.splitlines() if l.strip()})


# ---------------------------------------------------------------------------
# The marker-writers' lock (spec-build D-039). mark.py and tick.py are the
# only sanctioned writers of task markers; the lock serializes them so two
# sessions cannot read-rewrite task.md (or a tiny spec's § Tasks) at once.
# Hand edits skip it — no tool can stop those — and the SKILL's rule says so.
# ---------------------------------------------------------------------------

class TaskLockBusy(RuntimeError):
    """task_lock timed out waiting for the spec's marker-writer lock."""


TASK_LOCK_NAME = ".task.lock"
TASK_LOCK_STALE_SECONDS = 60.0
TASK_LOCK_TIMEOUT_SECONDS = 5.0
TASK_LOCK_RETRY_SECONDS = 0.05


@contextlib.contextmanager
def task_lock(spec_dir: Path | str,
              timeout: float = TASK_LOCK_TIMEOUT_SECONDS):
    """The one cross-writer lock over a spec's task markers.

    Lock file `<spec-dir>/.task.lock`, created with O_CREAT|O_EXCL (the
    one atomic create every supported platform gives us), holding the
    owner pid and its UTC timestamp. A held lock is waited on for
    `timeout` seconds (retry every 50 ms), then TaskLockBusy is raised —
    callers turn that into their own exit code. A lock older than 60 s is
    stale: the lock is held for milliseconds, so only a crash mid-write
    leaves one behind — it is broken (and a warning printed) rather than
    waited on forever. The holder reads, rewrites and os.replace()s the
    status file inside the `with`, so a reader never sees half a file."""
    with _lock_file(Path(spec_dir) / TASK_LOCK_NAME, timeout, "task",
                    TaskLockBusy) as lock:
        yield lock


@contextlib.contextmanager
def _lock_file(lock: Path, timeout: float, kind: str,
               busy: type[RuntimeError]):
    """task_lock's discipline, over one lock file: O_CREAT|O_EXCL, the
    owner pid and UTC timestamp inside, a stale lock broken past 60 s."""
    deadline = time.monotonic() + timeout
    fd: int | None = None
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
            except OSError:
                age = 0.0
            if age > TASK_LOCK_STALE_SECONDS:
                # only a crash mid-write leaves one — break it and say so
                owner = _lock_owner(lock)
                with contextlib.suppress(OSError):
                    lock.unlink()
                print(f"warning: broke stale {kind} lock {lock} "
                      f"({age:.0f}s old, pid {owner or 'unknown'})",
                      file=sys.stderr)
                continue
            if time.monotonic() >= deadline:
                raise busy(f"{lock} is held by another writer — "
                           "retry shortly")
            time.sleep(TASK_LOCK_RETRY_SECONDS)
    try:
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with contextlib.suppress(OSError):
            os.write(fd, f"{os.getpid()} {stamp}".encode())
    finally:
        os.close(fd)
    try:
        yield lock
    finally:
        with contextlib.suppress(OSError):
            lock.unlink()


# ---------------------------------------------------------------------------
# The cross-spec claim registry (spec-build D-057, spec-design D-078).
# schedule_wave reads one spec's doc state, so two specs executing at once
# could edit one file. The registry names every claimed task in the repo:
# mark.py's verbs write it, graph.py reads it. It is a cache, never status
# — a row is live only while its spec's status holder still shows the task
# (in-progress) or in a fix round; a row whose task does not is stale. A
# failed task keeps its half-done edits in the tree, so its round holds its
# files like a claim does.
# ---------------------------------------------------------------------------

CLAIMS_DIR = ".claims"
CLAIMS_REGISTRY = "registry.json"
CLAIMS_LOCK_NAME = ".claims.lock"
CLAIM_KEY = re.compile(r"^.+/T\d{3}$")


class ClaimsLockBusy(TaskLockBusy):
    """claims_lock timed out waiting for the repo's registry lock."""


class ClaimsRegistryError(RuntimeError):
    """The claim registry exists but cannot be read or parsed."""


def claims_root(spec_dir: Path | str) -> Path:
    """The specs tree the spec lives under — an archived spec's
    grandparent, every other spec's parent (index.specs_root's rule)."""
    parent = Path(spec_dir).parent
    return parent.parent if parent.name == "archive" else parent


def claims_registry_path(spec_dir: Path | str) -> Path:
    return claims_root(spec_dir) / CLAIMS_DIR / CLAIMS_REGISTRY


def claim_key(spec_dir: Path | str, task_id: str) -> str:
    """`<spec>/<T###>`, the spec named by its dir path under the specs
    tree so an archived spec shares no key with a live one."""
    rel = Path(spec_dir).relative_to(claims_root(spec_dir)).as_posix()
    return f"{rel}/{task_id}"


@contextlib.contextmanager
def claims_lock(spec_dir: Path | str,
                timeout: float = TASK_LOCK_TIMEOUT_SECONDS):
    """The one lock over the repo's claim registry: `specs/.claims.lock`,
    task_lock's discipline. It is taken outside a spec's task_lock and
    never inside one, so a claim waiting on a spec lock is the only
    place the two are held together."""
    with _lock_file(claims_root(spec_dir) / CLAIMS_LOCK_NAME, timeout,
                    "claims", ClaimsLockBusy) as lock:
        yield lock


def claims_read(spec_dir: Path | str) -> dict:
    """The registry's rows, `<spec>/<T###>` → {run, at, paths}; the caller
    holds claims_lock. No file yet reads as empty. A file that cannot be
    read, or is not that shape, raises ClaimsRegistryError — never an
    empty registry, which would let two specs claim one file."""
    path = claims_registry_path(spec_dir)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise ClaimsRegistryError(
            f"the claim registry {path} cannot be read — remove or "
            "repair it") from exc
    try:
        rows = json.loads(raw)
        for key, row in rows.items():
            if (not CLAIM_KEY.match(key)
                    or not isinstance(row, dict)
                    or not isinstance(row.get("run"), str)
                    or not isinstance(row.get("at"), str)
                    or not isinstance(row.get("paths"), list)
                    or not all(isinstance(p, str)
                               for p in row["paths"])):
                raise ValueError(key)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ClaimsRegistryError(
            f"the claim registry {path} is not `<spec>/<T###>` rows of "
            "{run, at, paths} — remove or repair it") from exc
    return rows


def claims_live(spec_dir: Path | str, rows: dict) -> dict:
    """The rows whose task is still open on its own spec's status holder —
    `(in-progress)`, or in a fix round, the cap included — the docs stay
    the only status."""
    root = claims_root(spec_dir)
    return {key: row for key, row in rows.items()
            if _claim_open(root, key)}


def _claim_open(root: Path, key: str) -> bool:
    """Open: claimed, or in a fix round — the cap included; never done or
    struck."""
    spec, task_id = key.rsplit("/", 1)
    spec_dir = root / spec
    spec_md, task_md = spec_dir / "spec.md", spec_dir / "task.md"
    try:
        tiny = (spec_md.is_file() and spec_tier(spec_md.read_text(
            encoding="utf-8", errors="replace")) == "tiny")
        entries = task_entries((spec_md if tiny else task_md).read_text(
            encoding="utf-8", errors="replace"))
    except OSError:
        return False
    return any(e.id == task_id and not (e.done or e.struck)
               and (e.claimed or e.fix_round is not None) for e in entries)


def claims_held(spec_dir: Path | str) -> dict:
    """The paths every OTHER spec's live claim holds, `<spec>/<T###>` →
    paths: what schedule_wave defers against. No registry on disk holds
    nothing and takes no lock — the claim under the lock decides again."""
    if not claims_registry_path(spec_dir).exists():
        return {}
    with claims_lock(spec_dir):
        live = claims_live(spec_dir, claims_read(spec_dir))
    own = claim_key(spec_dir, "")
    return {key: row["paths"] for key, row in live.items()
            if not key.startswith(own)}


def claims_without(rows: dict, spec_dir: Path | str, task_ids) -> dict:
    """`rows` less this spec's rows for `task_ids`."""
    keys = {claim_key(spec_dir, tid) for tid in task_ids}
    return {key: row for key, row in rows.items() if key not in keys}


def claims_write(spec_dir: Path | str, rows: dict) -> None:
    """Replace the registry atomically; the caller holds claims_lock. The
    first write makes `specs/.claims/` and its own `.gitignore` (`*`):
    run state, never committed."""
    path = claims_registry_path(spec_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    ignore = path.parent / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(str(tmp), os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(rows, indent=2, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp)


def claims_forget(spec_dir: Path | str, task_ids) -> bool:
    """Drop this spec's rows for `task_ids`, under claims_lock alone —
    land and tick call it once their task_lock is free, so the registry
    lock is never taken inside that one. False, with a warning, when the
    registry could not be read or written: the row is stale from the
    moment its marker leaves and the next claim sweeps it, so a busy or
    damaged registry never undoes a marker."""
    path = claims_registry_path(spec_dir)
    try:
        if not path.exists():
            return True
        with claims_lock(spec_dir):
            rows = claims_read(spec_dir)
            kept = claims_without(rows, spec_dir, task_ids)
            if len(kept) != len(rows):
                claims_write(spec_dir, kept)
    except (ClaimsLockBusy, ClaimsRegistryError, OSError) as exc:
        print(f"warning: claim registry not updated — {exc}",
              file=sys.stderr)
        return False
    return True


def _lock_owner(lock: Path) -> str | None:
    """The pid a lock file names, for the stale-lock warning; None when
    unreadable or the file was already unlinked by the breaking race."""
    try:
        head = lock.read_text(encoding="utf-8",
                              errors="replace").split(" ", 1)[0].strip()
    except OSError:
        return None
    return head or None


# ---------------------------------------------------------------------------
# The isolated worktree (spec-build D-058, spec-design D-079). Under
# `--isolate worktree` each implementer payload works in its own detached
# worktree at `<repo>/.spec-kit/worktrees/<spec>/<T###>/`, checked out at a
# snapshot of the main working tree: a commit built through a temporary
# index, on no branch and in no reflog, so the main tree's index, HEAD and
# branches do not move. graph.py creates and prunes these worktrees; mark.py
# lands a task's delta into the main tree, or discards it with the worktree.
# The folder ignores itself: never staged, never committed.
# ---------------------------------------------------------------------------

ISOLATE_DIR = ".spec-kit"
WORKTREES_DIR = "worktrees"
# What this spec's landings merged into the main tree, one file per
# spec: a landing proves its worktree, never the main tree it joins, so
# the next landing reads the main tree against its own cut and needs to
# tell that work from an edit nobody proved.
LANDED_DIR = "landed"
WORKTREE_ID = re.compile(r"^T\d{3}$")
SNAPSHOT_FILE = "spec-kit-snapshot"
SNAPSHOT_MESSAGE = "spec-kit worktree snapshot"
# the snapshot's author is always the kit and it is never signed: it is
# an object, not a commit of the user's, and must not wait on a key
SNAPSHOT_AUTHOR = ("-c", "user.name=spec-kit",
                   "-c", "user.email=spec-kit@localhost",
                   "-c", "commit.gpgsign=false")
# the landing is byte-for-byte: no whitespace policy of the repository's
# config rewrites or rejects the delta on its way into the tree
PATCH_OPTIONS = ("-c", "apply.whitespace=nowarn", "apply", "-p0")


class WorktreeError(RuntimeError):
    """A worktree operation git refused or could not finish."""


def _git(cwd: Path | str, *args: str, env: dict | None = None,
         out=None) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(
            ["git", "-C", str(cwd), *args],
            stdout=subprocess.PIPE if out is None else out,
            stderr=subprocess.PIPE, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        raise WorktreeError(
            f"git {args[0]} could not run in {cwd}: {exc}") from exc
    if r.returncode != 0:
        lines = r.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise WorktreeError(
            f"git {' '.join(args[:2])} in {cwd} exited {r.returncode}"
            + (f": {lines[-1]}" if lines else ""))
    return r


def _sha(r: subprocess.CompletedProcess) -> str:
    return r.stdout.decode("utf-8", errors="replace").strip()


@contextlib.contextmanager
def _scratch_index(prefix: str):
    """A temporary GIT_INDEX_FILE over the repository's object store:
    whatever git stages lands in a throwaway index, never in the tree's
    own."""
    with tempfile.TemporaryDirectory(prefix=prefix) as tmp:
        yield {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}


def _worktree_gitdir(path: Path | str) -> Path:
    gitdir = Path(_sha(_git(path, "rev-parse", "--git-dir")))
    return gitdir if gitdir.is_absolute() else Path(path) / gitdir


def worktree_root(repo: Path | str) -> Path:
    """`<repo>/.spec-kit/worktrees` — every isolated worktree lives under
    it, in one folder per spec and one per task under that."""
    return Path(repo) / ISOLATE_DIR / WORKTREES_DIR


def worktree_path(repo: Path | str, spec_name: str, task_id: str) -> Path:
    """Where the task's isolated worktree lives, present or not."""
    return worktree_root(repo) / spec_name / task_id


def worktrees_present(repo: Path | str, spec_name: str) -> dict[str, Path]:
    """`<T###>` → path for every isolated worktree of the spec on disk,
    in task-id order."""
    try:
        entries = sorted((worktree_root(repo) / spec_name).iterdir())
    except OSError:
        return {}
    return {p.name: p for p in entries
            if WORKTREE_ID.fullmatch(p.name) and p.is_dir()}


def _working_tree(repo: Path | str) -> str:
    """The tree of the main working tree as it stands, taken through a
    scratch index: tracked edits and deletions, untracked files too,
    ignored ones excluded."""
    with _scratch_index("spec-kit-index-") as env:
        _git(repo, "add", "-A", env=env)
        return _sha(_git(repo, "write-tree", env=env))


def worktree_snapshot(repo: Path | str) -> str:
    """A commit holding the main working tree as it stands — tracked
    edits and deletions, untracked files too, ignored ones excluded —
    parented on HEAD (a root commit where HEAD is unborn)."""
    tree = _working_tree(repo)
    try:
        parents = ["-p", _sha(_git(repo, "rev-parse", "--verify", "HEAD"))]
    except WorktreeError:
        parents = []
    return _sha(_git(repo, *SNAPSHOT_AUTHOR, "commit-tree", tree, *parents,
                     "-m", SNAPSHOT_MESSAGE))


def worktree_create(repo: Path | str, path: Path) -> None:
    """Create the detached worktree at `path` from a fresh snapshot of the
    main tree, recording the snapshot's sha in the worktree's own git
    dir: a task's delta is measured from there, so a commit made inside
    the worktree loses no work."""
    ignore = Path(repo) / ISOLATE_DIR / ".gitignore"
    try:
        ignore.parent.mkdir(parents=True, exist_ok=True)
        if not ignore.exists():
            ignore.write_text("*\n", encoding="utf-8")
    except OSError as exc:
        raise WorktreeError(f"{ignore} cannot be written: {exc}") from exc
    commit = worktree_snapshot(repo)
    _git(repo, "worktree", "add", "--detach", "--quiet", str(path), commit)
    with contextlib.suppress(OSError):
        (_worktree_gitdir(path) / SNAPSHOT_FILE).write_text(
            commit + "\n", encoding="utf-8")


def _recorded_snapshot(path: Path | str) -> str | None:
    try:
        sha = (_worktree_gitdir(path) / SNAPSHOT_FILE).read_text(
            encoding="utf-8").strip()
    except OSError:
        return None
    return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else None


def worktree_base(path: Path | str) -> str:
    """The snapshot the worktree was created from: the sha recorded in
    its git dir, else its HEAD (a worktree this kit did not create)."""
    return (_recorded_snapshot(path)
            or _sha(_git(path, "rev-parse", "HEAD")))


def worktree_untouched(path: Path | str) -> bool:
    """True when nothing was ever done in the worktree: its HEAD is
    still the snapshot it was cut from and no file differs from it."""
    snapshot = _recorded_snapshot(path)
    if (snapshot is not None
            and _sha(_git(path, "rev-parse", "HEAD")) != snapshot):
        return False
    return not _git(path, "status", "--porcelain").stdout.strip()


def worktree_refresh(repo: Path | str, path: Path) -> None:
    """Replace an untouched worktree with one cut from the main tree as
    it stands now; a worktree git will not remove refuses the wave."""
    why = worktree_remove(repo, path)
    if why:
        raise WorktreeError(why)
    worktree_create(repo, path)


def _tree_diff(repo: Path | str, before: str, after: str
               ) -> dict[str, str | None]:
    """`{path: "<mode> <blob sha>"}` for every path tree `after` holds
    differently from tree `before` — None where `after` lacks it."""
    raw = _git(repo, "diff", "--raw", "--no-abbrev", "--no-renames", "-z",
               before, after).stdout
    fields = raw.decode("utf-8", "surrogateescape").split("\0")
    changed: dict[str, str | None] = {}
    for meta, path in zip(fields[::2], fields[1::2]):
        if meta:
            _old, mode, _old_sha, sha, _status = meta[1:].split(" ")
            changed[path] = None if mode == "0" * 6 else f"{mode} {sha}"
    return changed


def landings_path(repo: Path | str, spec_name: str) -> Path:
    return Path(repo) / ISOLATE_DIR / LANDED_DIR / f"{spec_name}.json"


def landings_read(repo: Path | str, spec_name: str
                  ) -> dict[str, dict[str, str | None]]:
    """What each landing of the spec merged into the main tree, by task:
    `{path: "<mode> <blob sha>"}`, None where the landing deleted the
    path. A file that is missing or cannot be parsed reads as no
    landings: the next landing then names every such path — the
    refusing side, never a landing over unproven work."""
    try:
        rows = json.loads(
            landings_path(repo, spec_name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(rows, dict):
        return {}
    return {task: landing for task, landing in rows.items()
            if isinstance(landing, dict)}


def _record_landing(repo: Path | str, worktree: Path | str, base: str,
                    merged: list[str]) -> None:
    """Fold what the merge just left in the main tree at the delta's
    paths into the spec's landings, content-exact. A record that cannot
    be written is reported and never undoes the merge."""
    spec_name = Path(worktree).parent.name
    merged_set = set(merged)
    landing = {path: entry for path, entry in _tree_diff(
        repo, base, _working_tree(repo)).items() if path in merged_set}
    path = landings_path(repo, spec_name)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        fd = os.open(str(tmp), os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({**landings_read(repo, spec_name),
                       Path(worktree).name: landing}, f, indent=2,
                      sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        print(f"warning: landings not recorded — {exc}; the next landing "
              "refuses on these paths until they are committed",
              file=sys.stderr)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp)


def _run_state_prefixes(repo: Path | str, spec_dir: Path | str
                        ) -> tuple[str, ...]:
    """The paths, relative to the repository, under which a change in
    the main tree is run state: the spec's own dir and the kit's
    `.spec-kit/`."""
    top = Path(os.path.realpath(_sha(
        _git(repo, "rev-parse", "--show-toplevel"))))
    prefixes = []
    for path in (Path(spec_dir), Path(repo) / ISOLATE_DIR):
        real = Path(os.path.realpath(path))
        if top not in real.parents:
            raise WorktreeError(f"{path} is not inside the repository {top}")
        prefixes.append(real.relative_to(top).as_posix() + "/")
    return tuple(prefixes)


def worktree_unproven(repo: Path | str, worktree: Path | str,
                      spec_dir: Path | str) -> list[str]:
    """The main tree's uncommitted changes an isolated landing must
    refuse: the paths that differ from the snapshot the worktree was cut
    from, are not committed since, and no landing of the spec merged —
    work the worktree's proofs never ran on. What the main tree held at
    the cut was in the proof's tree, a landing's own delta was proven in
    its worktree, and run state is never named."""
    base = worktree_base(worktree)
    drift = _tree_diff(repo, base, _working_tree(repo))
    if not drift:
        return []
    committed: dict[str, str | None] = {}
    with contextlib.suppress(WorktreeError):
        committed = _tree_diff(
            repo, base, _sha(_git(repo, "rev-parse", "--verify", "--quiet",
                                  "HEAD^{tree}")))
    proven = set(committed.items()) | {
        (path, entry)
        for landing in landings_read(repo, Path(worktree).parent.name).values()
        for path, entry in landing.items()}
    run_state = _run_state_prefixes(repo, spec_dir)
    return sorted(path for path, entry in drift.items()
                  if (path, entry) not in proven
                  and not path.startswith(run_state))


def worktree_merge(repo: Path | str, worktree: Path | str
                   ) -> tuple[list[str], list[str]]:
    """Fold the worktree's delta against its snapshot — tracked edits,
    deletions and new files, binary content included — into the main
    working tree: (paths merged, paths refused). An empty delta merges
    nothing and refuses nothing. The tree alone is written: the index,
    HEAD and every branch stay as they are, so the work lands as
    uncommitted changes, exactly where a shared-tree task's would; what
    the merge left at those paths is recorded for the next landing's
    check (`worktree_unproven`). A delta the tree would not take clean
    writes nothing and names the touched paths `git apply --check`
    refused (git's own error lines when none of them matches)."""
    base = worktree_base(worktree)
    with tempfile.TemporaryDirectory(prefix="spec-kit-delta-") as tmp, \
            _scratch_index("spec-kit-index-") as env:
        _git(worktree, "read-tree", base, env=env)
        _git(worktree, "add", "-A", env=env)
        listed = _git(worktree, "diff", "--cached", "--name-only", "-z",
                      "--no-renames", base, env=env).stdout
        paths = sorted({p.decode("utf-8", "surrogateescape")
                        for p in listed.split(b"\0") if p})
        if paths:
            patch = Path(tmp) / "delta.patch"
            with patch.open("wb") as out:
                _git(worktree, "diff", "--cached", "--binary", "--no-prefix",
                     "--no-ext-diff", "--no-textconv", "--no-renames",
                     base, env=env, out=out)
            top = _sha(_git(repo, "rev-parse", "--show-toplevel"))
            check = subprocess.run(
                ["git", "-C", top, *PATCH_OPTIONS, "--check", "--verbose",
                 str(patch)], capture_output=True)
            if check.returncode != 0:
                errors = [line for line in check.stderr.decode(
                    "utf-8", errors="surrogateescape").splitlines()
                    if line.startswith("error:")]
                refused = [p for p in paths if any(
                    err.startswith(f"error: {p}:")
                    or err.startswith(f"error: patch failed: {p}:")
                    for err in errors)]
                return [], refused or [e.strip() for e in errors]
            _git(top, *PATCH_OPTIONS, str(patch))
            _record_landing(repo, worktree, base, paths)
    return paths, []


def worktree_remove(repo: Path | str, path: Path) -> str | None:
    """Remove the worktree with everything uncommitted in it; None once
    it is gone, or the reason git could not (a path already gone is
    nothing's error). A worktree someone locked stays: git's own
    refusal is the reason."""
    if not path.exists():
        return None
    try:
        _git(repo, "worktree", "remove", "--force", str(path))
    except WorktreeError as exc:
        return str(exc) if path.exists() else None
    for parent in (path.parent, worktree_root(repo)):
        try:
            parent.rmdir()
        except OSError:
            break
    return None
