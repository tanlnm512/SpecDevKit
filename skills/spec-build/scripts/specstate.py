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
research_state/git helpers and `task_lock`, which take an explicit
path). Text arguments
are the already-read file contents; check.py strips invisible/control
characters at read time before any parser sees the text, so the patterns
below can stay simple.

Exit-code/CLI contracts live in the tooling scripts, not here.
"""
from __future__ import annotations

import contextlib
import datetime
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

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

# The developer digest line (agents/developer.md's contract, D-040):
# `digest: task T### · status <…> · files <n> · commit-line … ·
# deviation … · note …` — one line, middle-dot separated. Agents write
# it verbatim into specs/<name>/digests/wave-<N>/<payload-stem>.md as
# their final action; latest_digest parses it back. Run scratch, not
# archived contract (archive.sh removes digests/ with spawns/).
#
# The deviation field is TYPED (D-043): `scope:<paths>` (the change
# genuinely needs files outside the task's Touches set), `spec-defect:
# <why>` (the task itself is wrong — a retry would fail again), or
# `other:<summary needing D-###>` (anything else). An untyped
# deviation string (older digests) parses with no kind and keeps the
# free-form D-### routing.
DIGEST_DIR = "digests"
DIGEST_TASK = re.compile(r"^digest:\s*task\s+(T\d{3})\b")
DEVIATION_KIND = re.compile(r"^(scope|spec-defect|other):")

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


def _parse_digest_line(line: str) -> dict | None:
    """One `digest: task T### · status … · …` line → its middle-dot
    segments as a dict (task, status, and whatever optional fields
    follow). None when the line names no task and status."""
    m = re.match(r"^digest:\s*(.+)$", line.strip())
    if not m:
        return None
    out: dict = {}
    for seg in m.group(1).split("\u00b7"):
        seg = seg.strip()
        for key, width in (("task", 5), ("status", 7), ("files", 6),
                           ("commit-line", 12), ("deviation", 10),
                           ("note", 5)):
            if seg.startswith(key + " "):
                out[key.replace("-", "_")] = seg[width:].strip()
                break
    if out.get("task") and out.get("status"):
        kind = DEVIATION_KIND.match(out.get("deviation") or "")
        if kind:
            out["deviation_kind"] = kind.group(1)
        return out
    return None


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
    not the tier."""
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


def latest_digest(spec_dir: Path | str, task_id: str) -> dict | None:
    """The newest developer digest on file for `task_id`, or None.

    Digests live at `specs/<name>/digests/wave-<N>/implementer-T###.md`
    (D-040) — one per wave, so a fix-round re-spawn never overwrites an
    earlier wave's record. Highest wave wins; within it the parsed
    digest line's `task` must name `task_id` (a stem can lie; the line
    cannot). The dict carries the parsed fields plus `wave` and `path`.
    Pure read: a missing or unreadable digests/ tree is simply None."""
    base = Path(spec_dir) / DIGEST_DIR
    if not base.is_dir():
        return None
    best: dict | None = None
    for path in sorted(base.glob("wave-*/implementer-*.md")):
        m = re.match(r"wave-(\d+)", path.parent.name)
        if not m:
            continue
        wave = int(m.group(1))
        text = _read_doc_text(path)
        if not text:
            continue
        line = next((ln for ln in text.splitlines()
                     if ln.strip().startswith("digest:")), None)
        if line is None:
            continue
        parsed = _parse_digest_line(line)
        if not parsed or parsed.get("task") != task_id:
            continue
        if best is None or wave >= best["wave"]:
            parsed["wave"] = wave
            parsed["path"] = str(path)
            best = parsed
    return best


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
    spec_dir = Path(spec_dir)
    lock = spec_dir / TASK_LOCK_NAME
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
                print(f"warning: broke stale task lock {lock} "
                      f"({age:.0f}s old, pid {owner or 'unknown'})",
                      file=sys.stderr)
                continue
            if time.monotonic() >= deadline:
                raise TaskLockBusy(
                    f"{lock} is held by another writer — retry shortly")
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


def _lock_owner(lock: Path) -> str | None:
    """The pid a lock file names, for the stale-lock warning; None when
    unreadable or the file was already unlinked by the breaking race."""
    try:
        head = lock.read_text(encoding="utf-8",
                              errors="replace").split(" ", 1)[0].strip()
    except OSError:
        return None
    return head or None
