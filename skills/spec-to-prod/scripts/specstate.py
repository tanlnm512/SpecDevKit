"""Shared doc-state parsers for a spec folder under specs/<name>/.

Every scheduling-relevant signal the tooling layer reads out of the docset
lives here as a pure function: spec Status, task entries (checkboxes,
phases, parallel markers, dependency chains, fix rounds, implemented
markers), the Before-audit, Closing-audit, and Delivered header lines, the
survey baseline header and item list, the researcher-skip marker,
next-free-ID allocation, ID definitions, and the git availability probes.
check.py, audit.py, and graph.py import from this module instead
of inlining their own copies — one canonical regex per doc shape, so the
validators and the workflow engine can never drift apart on what the docs
say (the same drift-killer D-007 applied to agent defs/briefs).

Pure functions, stdlib only, no CLI: importing this module has no side
effects — no output, no file writes (the file-reading exceptions are
research_state/git helpers, which take an explicit path). Text arguments
are the already-read file contents; check.py strips invisible/control
characters at read time before any parser sees the text, so the patterns
below can stay simple.

Exit-code/CLI contracts live in the tooling scripts, not here.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import NamedTuple

# An ID is "defined" when it introduces its entity on one of these line shapes.
# Single source of truth for FR/AC/US/TC/D — check.py's traceability graph,
# its checklist builder, and graph.py's ID bookkeeping all read this table.
DEFINITIONS = {
    "FR": re.compile(r"^-\s+\*\*(FR-\d{3})\*\*"),
    "AC": re.compile(r"^-\s+(AC\d+):"),
    "US": re.compile(r"^###\s+(US\d{1,2})\b"),
    "TC": re.compile(r"^#{2,3}\s+(TC-\d{3})"),
    "D": re.compile(r"^###\s+(D-\d{3})"),
}

# Template placeholders: <name>, <verb phrase>, <initial state> ... (letters,
# spaces, hyphens only — real markdown like <br> or <a href> won't match).
PLACEHOLDER = re.compile(r"<[a-z][a-z -]{2,}>")
CODE_SPAN = re.compile(r"`[^`]*`")
HTML_COMMENT = re.compile(r"<!--.*?-->")

# spec.md lifecycle: `**Status**: <word>` (backticked words tolerated).
STATUS_LINE = re.compile(r"^\*\*Status\*\*:\s*`?([A-Za-z]+)", re.M)

# task.md entry shapes (the Conventions block in templates/task.md is the
# normative wording): `- [x]` done, `(in-progress)` claimed, `~~T###~~`
# struck/dropped, `[P]` parallelizable, `(after T###)` dependency chain,
# `(fix <n>/5)` fix-round counter. `(implemented)` records landed work on
# an unticked entry — durable before the closing audit's one all-at-once
# tick, and read independently of claimed/done/struck.
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

# task.md header: the before-audit recording line. `passed @ <sha>` after a
# real audit, `passed @ -` in a non-git repo (nothing to hash); the
# scaffold's `pending` placeholder — and its backticked `passed @ <sha>`
# example text — must not read as passed.
BEFORE_AUDIT_PASSED = re.compile(r"Before-audit\*{0,2}\s*:\s*passed\s+@")

# task.md header: the closing-audit approval record — `approved @ <sha>`
# after the closing audit's human gates pass, `approved @ -` in a non-git
# repo (the same dash form Before-audit accepts). The record is the durable
# human sign-off that proof, review, rulings, regression, and sign-off were
# ruled green under; the word must sit directly after the colon, so a
# `pending` placeholder — or its backticked `approved @ <sha>` example
# text — cannot read as approved.
CLOSING_AUDIT_APPROVED = re.compile(
    r"Closing-audit\*{0,2}\s*:\s*approved\s+@")

# task.md header: the delivery record — `commit @ <sha>` once the plan's
# end-of-spec commit exists, `commit @ -` the explicit non-git skip (the
# same dash form Before-audit accepts). The record must name `commit`
# directly after the colon, so the scaffold's `pending` placeholder — and
# its backticked example text — cannot read as delivered.
DELIVERED_COMMIT = re.compile(
    r"Delivered\*{0,2}\s*:\s*commit\s+@\s*`?([0-9a-f]{7,40}|-)")

# survey.md baseline header: `**Baseline**: <version> @ <sha>`, backticks on
# the sha tolerated; the second shape matches a bare angle-bracketed baseline
# header carrying a real hash (e.g. `<v2 @ abc1234>`). The unfilled
# template's `<version @ commit>` placeholder has no hex chars and cannot
# match either shape — it reads None (see survey_baseline).
BASELINE_HEADER = re.compile(r"Baseline\*\*([^@\n]*)@\s*`?([0-9a-f]{7,40})`?")
BASELINE_PLACEHOLDER = re.compile(r"<\s*([^<>@\n]{1,40})\s*@\s*([0-9a-f]{7,40})\s*>")

# survey.md item list shape (the surveyor's template): `item <id>: "<desc>"`
# with a following `status:` line. Malformed/missing status reads "unknown"
# rather than raising — converge diffs two possibly-messy snapshots.
SURVEY_ITEM = re.compile(r'^item\s+(\S+):\s*"([^"]*)"', re.M)
SURVEY_ITEM_STATUS = re.compile(r"^\s*status:\s*(DONE|PARTIAL|TODO)", re.M)

# The researcher-gate skip record (byte-exact, em dash U+2014). Canonical
# home: contracts/docset.md; every occurrence anywhere must match this
# sequence exactly. research_state matches it as a whole stripped line.
RESEARCH_SKIP_MARKER = "not applicable — no open questions at Stage 0"

# Substrings that survive only while research.md is still the unfilled
# scaffold template (scaffold.sh copies templates verbatim) — a file
# carrying any of these has not been filled, and the research gate must
# stay undetermined rather than misread the template as done research.
RESEARCH_TEMPLATE_GLUE = (
    "### <research question",
    "### <open choice>",
    "- **source**: <URL or DOI>",
)


# NamedTuple, not dataclass: the suite loads scripts by file path via
# importlib without sys.modules registration, which breaks dataclass
# annotation processing — a plain record keeps the module loadable either way.
class TaskEntry(NamedTuple):
    """One `- [ ]`-anchored task entry from task.md's `## Phase N` sections.

    `block` is the entry's raw text (trimmed at the first blank line, so
    trailing prose after the section's last entry is not swallowed); the
    flag fields are parsed views onto it. `id` is None for entries whose
    first line doesn't open with a T-ID (e.g. the struck form
    `- [ ] ~~T005~~ …`) and `phase` is None under an unnumbered phase
    header — both stay in the list so consumers count them where the
    source file counts them."""

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


class SurveyItem(NamedTuple):
    """One `item <id>: "…"` block from survey.md's item list."""

    id: str
    description: str
    status: str  # DONE | PARTIAL | TODO | unknown


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
        if not header.lower().startswith("phase"):
            continue
        hm = re.match(r"phase\s+(\d+)", header, re.I)
        phase = int(hm.group(1)) if hm else None
        for block in re.split(r"^(?=- \[)", sec, flags=re.M):
            if not re.match(r"- \[", block):
                continue
            block = block.split("\n\n", 1)[0]
            first_line = block.split("\n", 1)[0]
            own = TASK_ID.match(block)
            fix = FIX_ROUND.search(block)
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
                implemented="(implemented)" in block,
            ))
    return entries


def before_audit_state(task_md: str) -> str:
    """'passed' | 'pending' | 'missing' for task.md's Before-audit line.

    passed = the audit was recorded (`passed @ <sha>`, or `passed @ -` in a
    non-git repo); pending = a line exists but no passed record (the
    scaffold's placeholder reads pending, never passed); missing = no
    Before-audit line at all."""
    if "Before-audit" not in task_md:
        return "missing"
    if BEFORE_AUDIT_PASSED.search(task_md):
        return "passed"
    return "pending"


def closing_audit_state(task_md: str) -> str:
    """'approved' | 'pending' | 'missing' for task.md's Closing-audit line.

    approved = the closing audit's human record exists (`approved @ <sha>`,
    or `approved @ -` in a non-git repo) — the durable sign-off under which
    proof, review, rulings, regression, and sign-off were ruled green;
    pending = a line exists but records no approval; missing = no
    Closing-audit line at all. Mechanical pass conditions never imply this
    record: only the line the orchestrator writes does."""
    if "Closing-audit" not in task_md:
        return "missing"
    if CLOSING_AUDIT_APPROVED.search(task_md):
        return "approved"
    return "pending"


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


def tick_evidence(task_md: str) -> TickEvidence:
    """The durable task-tick evidence for the tick-commit transition: an
    approved tick transition is fully evidenced only when `unticked` and
    `noteless` are both empty — every task ticked or struck, every tick
    carrying its `done <date> — <proof>` sub-line."""
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


def survey_baseline(survey_md: str) -> tuple[str, str] | None:
    """(version, sha) from survey.md's baseline header, or None.

    Handles the filled `**Baseline**: <version> @ <sha>` form (backticked
    sha tolerated) and the template's `<version @ commit>` placeholder
    shape — the placeholder carries no real hash, so it reads None and the
    caller decides how to report an unfilled header."""
    m = BASELINE_HEADER.search(survey_md) or BASELINE_PLACEHOLDER.search(survey_md)
    if not m:
        return None
    ver = m.group(1).strip().lstrip(":").strip()
    return ver, m.group(2)


def survey_items(survey_md: str) -> list[SurveyItem]:
    """survey.md's item list: id, quoted description, and status (unknown
    when the status line is absent or malformed). Blocks that don't open
    with the `item <id>: "…"` shape are skipped, not raised."""
    items: list[SurveyItem] = []
    for block in re.split(r'(?=^item\s+\S+:)', survey_md, flags=re.M):
        m = SURVEY_ITEM.match(block)
        if not m:
            continue
        sm = SURVEY_ITEM_STATUS.search(block)
        items.append(
            SurveyItem(m.group(1), m.group(2), sm.group(1) if sm else "unknown"))
    return items


def research_state(research_path: Path | str | None) -> str:
    """'done' | 'skip' | 'pending' | 'missing' for specs/<name>/research.md.

    skip = the file carries the canonical skip-marker line (byte-exact, em
    dash — RESEARCH_SKIP_MARKER; the marker wins over template residue
    since writing it is the orchestrator's explicit record). pending = the
    file exists but is empty or still the unfilled scaffold template — the
    gate stays undetermined, never misreading the template as ran research.
    missing = no file (or an unreadable path)."""
    if research_path is None:
        return "missing"
    try:
        text = Path(research_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "missing"
    if any(line.strip() == RESEARCH_SKIP_MARKER for line in text.splitlines()):
        return "skip"
    if not text.strip():
        return "pending"
    if any(glue in text for glue in RESEARCH_TEMPLATE_GLUE):
        return "pending"
    return "done"


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
        "AC": nxt(r"\bAC(\d+)\b", texts.get("spec.md", ""), "AC{}"),
        "US": nxt(r"\bUS(\d+)\b", texts.get("spec.md", ""), "US{}"),
        "T": nxt(r"\bT(\d{3})\b", texts.get("task.md", ""), "T{:03d}"),
        "TC": nxt(r"TC-(\d{3})", texts.get("test.md", ""), "TC-{:03d}"),
        "D": nxt(r"D-(\d{3})", texts.get("tech-spec.md", ""), "D-{:03d}"),
    }


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
    delta scope for a stale-baseline re-survey (graph.py's DELTA
    RE-SURVEY payload). None when git cannot answer (no repository,
    unknown sha, git unavailable): callers degrade to a full re-survey,
    never to an empty-delta verdict. Committed range only, matching the
    converge staleness comparison (baseline sha vs HEAD); uncommitted
    work is the audits' business (audit.py changed_paths), not the
    survey's."""
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
