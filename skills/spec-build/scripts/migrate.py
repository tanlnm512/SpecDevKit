#!/usr/bin/env python3
"""migrate.py — bring an older active docset's task.md to the template's
contract header shape: dry-run, idempotent, evidence-neutral.

The task template IS the target shape: every `**Field**:` line in the
template's preamble that the docset's task.md lacks is inserted verbatim —
pending placeholders only, so migration never fabricates mechanical-audit,
human-acknowledgement, or delivery evidence. Existing lines (filled
evidence included) are never moved, rewritten, or removed. A second apply
finds nothing missing and changes nothing.

Refused (exit 1, nothing written): a missing spec.md/task.md or template,
an unrecognizable spec.md Status, a done Status (a done plan is a record),
and any path under specs/archive/ — archived history is never migrated.
draft, approved, and active docsets migrate: task.md is the status holder,
outside the approval freeze. Migration never approves: a Status of
approved, active, or done with no approvals/approval.md prints the
one-time re-approval steps.

`upgrade` converts a pre-change-grammar docset (the grammar check.py's
migration detector warns about) to the current one, in place, in order:
the burndown grows the Verified column; research.md folds into
tech-spec.md's `## Questions & options` section; the approval record
folds into one approval.md (`## Contract review` + `## Freeze`, manifest
entry lines transplanted byte-identically); a notes/delivery.md record
transplants into the status holder's delivery block; the per-spec-dir
`.grammar-v1-warned` marker is removed last. Each retired file is
deleted only after its content is carried over, and a second apply finds
nothing left to convert and changes nothing. Writes touch only unfrozen
bytes — task.md, tech-spec.md appends beyond the recorded prefix length,
and approvals/* / notes/* — so a recorded freeze still verifies after
the upgrade. Evidence is never fabricated: missing hotfix targets and
fix digests stay missing for their owners to record. The upgrade runs
dry by default; `--apply` writes.

Usage: migrate.py <spec-dir> [--template <path>] [--dry-run]
       migrate.py <spec-dir> upgrade [--apply]
       migrate.py grow <spec-dir>
       migrate.py -h | --help        (prints this text, exit 0)
Exit:  0 = migrated, previewed (the dry default), or already at the
       target grammar · 1 = validation failure (nothing written) ·
       2 = usage error
"""
from __future__ import annotations

import re
import sys
from collections.abc import Callable
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import audit  # noqa: E402 - the sys.path setup above runs first
import check  # noqa: E402 - the migration detector's shapes live here
import freeze  # noqa: E402 - the sys.path setup above runs first
import specstate  # noqa: E402
from tick import _durable_replace, _fsync_dir, _rollback  # noqa: E402

DEFAULT_TEMPLATE = Path(_SCRIPTS_DIR).parent / "templates" / "task.md"
FIELD_LINE = re.compile(r"^\*\*([^*]+)\*\*:")
MIGRATABLE_STATUS = ("draft", "approved", "active")
FROZEN_STATUS = ("approved", "active", "done")


def body_start(lines: list[str]) -> int | None:
    """Index of the first '## ' section line — the preamble's end."""
    for i, line in enumerate(lines):
        if line.startswith("## "):
            return i
    return None


def header_fields(text: str) -> tuple[int | None, list[tuple[str, str]]]:
    """(body start or None, ordered unique `**Name**:` preamble fields)."""
    lines = text.split("\n")
    start = body_start(lines)
    if start is None:
        return None, []
    seen: set[str] = set()
    fields: list[tuple[str, str]] = []
    for line in lines[:start]:
        m = FIELD_LINE.match(line)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            fields.append((m.group(1), line))
    return start, fields


def plan_migration(task_text: str, template_text: str) -> tuple[str | None, list[str]]:
    """(problem or None, additions) — additions are the template's preamble
    field lines the task text lacks, in template order. problem names which
    text has no '## ' section ('task' or 'template')."""
    t_start, t_fields = header_fields(template_text)
    if t_start is None:
        return "template", []
    start, fields = header_fields(task_text)
    if start is None:
        return "task", []
    present = {name for name, _ in fields}
    return None, [line for name, line in t_fields if name not in present]


def insert_lines(text: str, additions: list[str]) -> str:
    """Splice additions into the preamble after its last non-blank line —
    purely additive: every original line keeps its order and bytes."""
    lines = text.split("\n")
    start = body_start(lines)
    at = (start or 0) - 1
    while at >= 0 and not lines[at].strip():
        at -= 1
    return "\n".join(lines[: at + 1] + list(additions) + lines[at + 1 :])


def verify_text(original: str, candidate: str, additions: list[str]) -> list[str]:
    """The invariants that make the splice trustworthy: the original lines
    survive in order, the line count grows by exactly the insertion count,
    every inserted line is present, and the candidate stays a recognizable
    plan. Runs identically on the prospective text (pre-write) and the
    promoted text (postcheck)."""
    problems: list[str] = []
    orig = original.split("\n")
    new = candidate.split("\n")
    if len(new) != len(orig) + len(additions):
        problems.append(
            f"line count {len(new)} != original {len(orig)} + {len(additions)} inserted")
    it = iter(new)
    for line in orig:
        for cand in it:
            if cand == line:
                break
        else:
            problems.append("an original line is missing or reordered")
            break
    for added in additions:
        if added not in new:
            problems.append(f"inserted line not found: {added[:60]}")
    if body_start(new) is None:
        problems.append("no '## ' section after insertion")
    return problems


# ------------------------------------------------------------- grow ----
def grow(spec_dir: Path) -> int:
    """tiny -> full: move the § Tasks blocks into task.md
    verbatim (IDs never renumbered), scaffold the four
    authoring docs from templates, flip the Tier header to full, and
    drop § Tasks. Structure moves; CONTENT re-enters authoring: the
    fresh templates fail check.py by design, and the graph's authoring
    nodes are READY again. Nothing is inferred."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import specstate
    spec_path = spec_dir / "spec.md"
    text = spec_path.read_text(encoding="utf-8")
    if specstate.spec_tier(text) != "tiny":
        print("grow: spec is not Tier: tiny — nothing to do", file=sys.stderr)
        return 1
    section = specstate.tasks_section(text)
    if section is None or not specstate.task_entries(
            specstate.tiny_task_text(text) or ""):
        print("grow: spec.md § Tasks has no task entries — author them "
              "before growing", file=sys.stderr)
        return 1

    skill_dir = Path(__file__).resolve().parent.parent
    blocks = section.strip("\n")
    task_md = (
        f"# Task — {spec_dir.name}\n\n"
        f"**Watershed**: implementation commit C1\n\n"
        f"## Phase 1\n\n{blocks}\n\n"
        f"| Phase | Total | Done | Verified |\n"
        f"|-------|-------|------|----------|\n"
        f"| 1     | 0     | 0    |          |\n\n"
        f"| **Σ** | 0     | 0    |          |\n"
    )
    n_tasks = len(specstate.task_entries(
        specstate.tiny_task_text(text) or ""))
    task_md = task_md.replace("| 1     | 0     | 0    |          |",
                              f"| 1     | {n_tasks}     | 0    |          |")
    task_md = task_md.replace("| **Σ** | 0     | 0    |          |",
                              f"| **Σ** | {n_tasks}     | 0    |          |")

    (spec_dir / "task.md").write_text(task_md, encoding="utf-8")
    for f in ("plan", "tech-spec", "test", "survey"):
        src = skill_dir / "templates" / f"{f}.md"
        if not (spec_dir / f"{f}.md").exists():
            (spec_dir / f"{f}.md").write_text(
                src.read_text(encoding="utf-8"), encoding="utf-8")

    start = text.find(specstate.TASKS_HEADING)
    end = text.find("\n## ", start + 3)
    grown = text[:start].rstrip("\n")
    if end >= 0:
        grown += "\n" + text[end + 1:]
    grown = grown.replace("**Tier**: tiny", "**Tier**: full", 1)
    spec_path.write_text(grown.rstrip("\n") + "\n", encoding="utf-8")
    print(f"grown: {n_tasks} task(s) moved to task.md (Phase 1, ids "
          f"preserved); plan/tech-spec/test/survey scaffolded from "
          f"templates; Tier: full")
    print("next: the authoring nodes are READY — re-run the graph; "
          "check.py fails on the fresh templates by design")
    if (spec_dir / "approvals" / "approval.md").exists():
        print("next: the recorded approval froze the one-file contract and "
              "no longer matches — set Status back to draft; once the "
              "docset is check-green, re-approve through /spec-design: "
              "the contract review, then on the user's explicit yes "
              "`freeze.py <spec-dir> --record --force`")
    return 0


# ----------------------------------------------------------- upgrade ----
PENDING_DELIVERED = "**Delivered**: pending — delivery evidence"
UNFILLED_SECTION = (
    "## Questions & options\n\n### Questions\n\n### Options summary\n")


def _write_fold(path: Path, original: str, candidate: str) -> str | None:
    """Durable replace plus a byte postcheck; None on success, else a
    failure message (the original has been restored)."""
    try:
        _durable_replace(path, candidate)
        if path.read_bytes() != candidate.encode("utf-8"):
            _rollback(path, original)
            return f"{path.name} on disk differs from the verified candidate"
        _fsync_dir(path)
    except OSError as exc:
        try:
            _rollback(path, original)
        except OSError:
            pass
        return f"write/replace failed, original preserved: {exc}"
    return None


def _unlink(path: Path) -> str | None:
    try:
        path.unlink()
    except OSError as exc:
        return f"could not delete {path}: {exc}"
    return None


def _two_column_run(lines: list[str]) -> tuple[int, int] | None:
    """(first, past-last) of the table run a two-column burndown header
    opens — the row shape check.py's detector fails on."""
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
        if (cells and cells[0] == "phase" and "total" in cells
                and "done" in cells and "verified" not in cells):
            end = i + 1
            while end < len(lines) and lines[end].lstrip().startswith("|"):
                end += 1
            return i, end
    return None


def grow_burndown(task_text: str) -> str | None:
    """task.md with every two-column burndown table grown the Verified
    column — recorded counts carried, never recomputed; None when the
    tables already read the four-column grammar."""
    lines = task_text.split("\n")
    changed = False
    run = _two_column_run(lines)
    while run is not None:
        start, end = run
        for j in range(start, end):
            row = lines[j].rstrip()
            cells = row.strip().strip("|").split("|")
            if len(cells) != 3:
                continue
            if j == start:
                lines[j] = row + " Verified |"
            elif all(c.strip() and set(c.strip()) <= set("-:")
                     for c in cells):
                lines[j] = row + "----------|"
            else:
                lines[j] = row + "          |"
        changed = True
        run = _two_column_run(lines)
    return "\n".join(lines) if changed else None


def questions_section(research_text: str | None) -> str:
    """The `## Questions & options` section for tech-spec.md: research.md's
    content carried over (H2 subsections demoted one level, so the
    section parser reads them inside this section), or the unfilled
    section when there is nothing to carry — never a fabricated skip
    record."""
    if research_text is None:
        return UNFILLED_SECTION
    carried = []
    for line in research_text.splitlines():
        if line.startswith("# "):
            continue
        carried.append("#" + line if line.startswith("## ") else line)
    return "## Questions & options\n\n" + "\n".join(carried).strip("\n") + "\n"


def append_section(text: str, section: str) -> str:
    """Strictly append-only: the original bytes stay the candidate's
    prefix, which is what a recorded tech-spec prefix hash anchors."""
    glue = "" if text.endswith("\n") else "\n"
    return text + glue + "\n" + section


def folded_approval(approval_text: str,
                    review_lines: tuple[str, ...] | None) -> str:
    """The old-grammar record folded: the `## Frozen contract` manifest
    becomes `## Freeze` with its entry lines byte-identical, and at full
    tier the review sidecar's trio lands in `## Contract review` ahead of
    it. The **Approved-at** preamble survives untouched."""
    if review_lines is None:
        return check.FROZEN_CONTRACT_HEADING.sub(
            "## Freeze", approval_text, count=1)
    m = check.FROZEN_CONTRACT_HEADING.search(approval_text)
    return (approval_text[:m.start()]
            + "## Contract review\n\n" + "\n".join(review_lines)
            + "\n\n## Freeze\n\n" + approval_text[m.end():].lstrip("\n"))


def _last_line(pattern: re.Pattern[str], text: str) -> str | None:
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    m = matches[-1]
    start = text.rfind("\n", 0, m.start()) + 1
    end = text.find("\n", m.end())
    return text[start:len(text) if end < 0 else end].strip()


def delivery_facts(note_text: str) -> list[str]:
    """The note's delivery-fact lines in the block's canonical order; a
    re-delivery appends, so the last line of each fact wins."""
    facts = []
    for pattern in (audit.DOCS_IMPACT, audit.ROLLBACK_RULING,
                    audit.BEHAVIOR_PRESERVED):
        line = _last_line(pattern, note_text)
        if line is not None:
            facts.append(line)
    return facts


def transplant_delivery(holder_text: str, facts: list[str]) -> str:
    """The facts as block bullets under the **Delivered** field — inserted
    right after the record line when one exists, else under the
    template's pending placeholder (a pending marker is not evidence;
    the bullets carried under it are the note's own lines)."""
    lines = holder_text.split("\n")
    bullets = [f"- {line}" for line in facts]
    m = audit.DELIVERED_FIELD.search(holder_text)
    if m is None:
        start = body_start(lines)
        at = start if start is not None else len(lines)
        lines[at:at] = [PENDING_DELIVERED, "", *bullets, ""]
        return "\n".join(lines)
    at = holder_text[:m.start()].count("\n") + 1
    lines[at:at] = bullets
    return "\n".join(lines)


def upgrade(spec_dir: Path, apply: bool) -> int:
    """The four mechanical folds, every candidate text computed and
    checked before the first write, applied in order, warn marker removed
    last. Dry-run prints the plan; a refusal writes nothing."""
    def refuse(msg: str) -> int:
        print(f"refusing: {msg}", file=sys.stderr)
        return 1

    if not spec_dir.is_dir():
        return refuse(f"{spec_dir} is not a directory")
    parts = spec_dir.resolve().parts
    if ("specs", "archive") in zip(parts, parts[1:]):
        return refuse(f"{spec_dir} is under specs/archive/ — archived "
                      "history is never migrated")
    task_path = spec_dir / "task.md"
    spec_path = spec_dir / "spec.md"
    if not task_path.is_file():
        return refuse(f"no task.md under {spec_dir}")
    if not spec_path.is_file():
        return refuse(f"no spec.md under {spec_dir} — the lifecycle state "
                      "cannot be verified")
    spec_text = spec_path.read_text(encoding="utf-8", errors="replace")
    status = specstate.spec_status(spec_text)
    if status is None:
        return refuse("spec.md has no recognizable **Status**: line")
    if status not in MIGRATABLE_STATUS:
        return refuse(f"spec.md Status is {status} — only draft, approved, "
                      "or active docsets migrate; a done plan is a record")

    repo = spec_dir.resolve().parent.parent
    tiny = specstate.spec_tier(spec_text) == "tiny"
    task_text = task_path.read_text(encoding="utf-8")
    plan: list[tuple[str, Callable[[], str | None]]] = []
    notes: list[str] = []

    grown = grow_burndown(task_text)
    if grown is not None:
        plan.append((
            "burndown: grow the table the Verified column (task.md)",
            lambda: _write_fold(task_path, task_text, grown)))

    research_path = spec_dir / "research.md"
    tech_path = spec_dir / "tech-spec.md"
    if not tiny and tech_path.is_file() and research_path.is_file():
        tech_text = tech_path.read_text(encoding="utf-8")
        if specstate.QUESTIONS_SECTION.search(tech_text) is None:
            research_text = research_path.read_text(encoding="utf-8")
            candidate = append_section(tech_text,
                                       questions_section(research_text))

            def run_research(tech_text=tech_text, candidate=candidate):
                err = _write_fold(tech_path, tech_text, candidate)
                if err:
                    return err
                err = _unlink(research_path)
                if err:
                    return err
                print("research: folded research.md into tech-spec.md's "
                      "`## Questions & options`; deleted research.md")
                return None

            plan.append(("research: fold research.md into tech-spec.md's "
                         "`## Questions & options`, delete research.md",
                         run_research))
    elif not tiny and tech_path.is_file() and not research_path.is_file():
        tech_text = tech_path.read_text(encoding="utf-8")
        if specstate.QUESTIONS_SECTION.search(tech_text) is None:
            candidate = append_section(tech_text, questions_section(None))

            def run_research(tech_text=tech_text, candidate=candidate):
                return _write_fold(tech_path, tech_text, candidate) or print(
                    "research: appended the `## Questions & options` "
                    "section (unfilled — the gate's states are the "
                    "owner's to record)")

            plan.append(("research: append the `## Questions & options` "
                         "section (unfilled — never a fabricated skip "
                         "record)", run_research))

    approval_path = spec_dir / "approvals" / "approval.md"
    review_path = spec_dir / "approvals" / "review.md"
    approval_text = (approval_path.read_text(encoding="utf-8")
                     if approval_path.is_file() else None)
    if approval_text is None and review_path.exists():
        notes.append(
            "approvals/review.md has no approval.md record to fold into — "
            "kept: the freeze folds it at re-approval (`freeze.py <spec-dir>"
            " --record --review <payload>`)")
    elif (approval_text is not None
          and check.FREEZE_HEADING.search(approval_text) is None):
        if not check.FROZEN_CONTRACT_HEADING.search(approval_text):
            return refuse(
                "approvals/approval.md has no `## Frozen contract` manifest "
                "to fold — re-approve on the user's yes: `freeze.py "
                "<spec-dir> --record --force --review <payload>`")
        review_lines: tuple[str, ...] | None = None
        done_line = ("approval: renamed the manifest to `## Freeze` "
                     "(tiny tier has no review section)")
        if not tiny:
            if not review_path.is_file():
                return refuse(
                    "the old-grammar approval record needs its "
                    "approvals/review.md sidecar to fold — restore it, or "
                    "re-approve on the user's yes: `freeze.py <spec-dir> "
                    "--record --force --review <payload>`")
            review_lines = freeze.fold_review(
                review_path.read_text(encoding="utf-8"))
            problem = freeze.review_shape_problem("\n".join(review_lines))
            if problem:
                return refuse(f"approvals/review.md cannot fold: {problem}")
            done_line = ("approval: folded the review into one "
                         "approvals/approval.md (`## Contract review` + "
                         "`## Freeze`); deleted approvals/review.md")
        verify_before = freeze.verify(spec_dir, repo)

        def run_approval(approval_text=approval_text,
                         review_lines=review_lines,
                         verify_before=verify_before,
                         done_line=done_line):
            err = _write_fold(approval_path, approval_text,
                              folded_approval(approval_text, review_lines))
            if err:
                return err
            fresh = [p for p in freeze.verify(spec_dir, repo)
                     if p not in verify_before]
            if fresh:
                _rollback(approval_path, approval_text)
                return ("postcheck: the folded record fails freeze verify "
                        f"— {fresh[0]}")
            if not tiny and review_path.exists():
                err = _unlink(review_path)
                if err:
                    return err
            print(done_line)
            return None

        plan.append(("approval: fold the old-grammar record into one "
                     "approval.md, delete approvals/review.md", run_approval))

    note_path = spec_dir / "notes" / "delivery.md"
    if note_path.is_file():
        holder_text = task_text if not tiny else spec_text
        if check.has_delivery_block(holder_text):
            pass  # the block wins; the note is an inert leftover
        elif tiny:
            notes.append(
                "notes/delivery.md has no block to transplant into at tiny "
                "tier — the holder is spec.md, frozen; transplant by hand")
        else:
            note_text = note_path.read_text(encoding="utf-8")
            facts = delivery_facts(note_text)
            if not facts:
                notes.append(
                    "notes/delivery.md carries no recognizable "
                    "delivery-fact lines — kept; transplant by hand")
            else:
                candidate = transplant_delivery(
                    grown if grown is not None else task_text, facts)
                if not check.has_delivery_block(candidate):
                    return refuse("the transplanted delivery block would "
                                  "not parse — nothing written")

                def run_delivery(candidate=candidate):
                    err = _write_fold(task_path, task_text, candidate)
                    if err:
                        return err
                    err = _unlink(note_path)
                    if err:
                        return err
                    print("delivery: transplanted notes/delivery.md into "
                          "the delivery block; deleted notes/delivery.md")
                    return None

                plan.append(("delivery: transplant notes/delivery.md's "
                             "facts into the delivery block, delete "
                             "notes/delivery.md", run_delivery))

    marker = spec_dir / check.WARN_MARKER
    if marker.exists():
        def run_marker():
            err = _unlink(marker)
            return err or print(f"removed the {check.WARN_MARKER} marker")

        plan.append((f"remove the {check.WARN_MARKER} marker", run_marker))

    for note in notes:
        print(f"note: {note}")
    if not plan:
        print(f"already upgraded: no pre-change grammar remains under "
              f"{spec_dir}")
        return 0
    for line, _ in plan:
        print(f"  - {line}")
    if not apply:
        print(f"dry-run: {len(plan)} step(s) planned — nothing written "
              "(--apply writes)")
        return 0
    for _, run in plan:
        err = run()
        if err:
            print(err, file=sys.stderr)
            print("upgrade aborted — the landed step(s) keep their state",
                  file=sys.stderr)
            return 1
    print(f"upgraded: {len(plan)} step(s) applied")
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    if argv and argv[0] == "grow":
        if len(argv) != 2:
            print("usage: migrate.py grow <spec-dir>", file=sys.stderr)
            return 2
        return grow(Path(argv[1]))
    if "upgrade" in argv:
        apply = False
        target = None
        verb_seen = False
        for a in argv:
            if a == "upgrade" and not verb_seen:
                verb_seen = True
            elif a == "--apply":
                apply = True
            elif a == "--dry-run":
                apply = False
            elif not a.startswith("-") and target is None:
                target = a
            else:
                print(f"unexpected argument: {a}", file=sys.stderr)
                return 2
        if not verb_seen or target is None:
            print("usage: migrate.py <spec-dir> upgrade [--apply]",
                  file=sys.stderr)
            return 2
        return upgrade(Path(target), apply)
    spec_dir_arg = None
    template_arg = None
    dry = False
    it = iter(argv)
    for a in it:
        if a == "--template":
            template_arg = next(it, None)
            if not template_arg:
                print("--template needs a path", file=sys.stderr)
                return 2
        elif a == "--dry-run":
            dry = True
        elif spec_dir_arg is None:
            spec_dir_arg = a
        else:
            print(f"unexpected argument: {a}", file=sys.stderr)
            return 2
    if spec_dir_arg is None:
        print("usage: migrate.py <spec-dir> [--template <path>] [--dry-run]",
              file=sys.stderr)
        return 2

    def refuse(msg: str) -> int:
        print(f"refusing: {msg}", file=sys.stderr)
        return 1

    spec_dir = Path(spec_dir_arg)
    template_path = Path(template_arg) if template_arg else DEFAULT_TEMPLATE
    if not spec_dir.is_dir():
        return refuse(f"{spec_dir} is not a directory")
    if not template_path.is_file():
        return refuse(f"template not found: {template_path}")
    parts = spec_dir.resolve().parts
    if ("specs", "archive") in zip(parts, parts[1:]):
        return refuse(f"{spec_dir} is under specs/archive/ — archived history "
                      "is never migrated")
    task_path = spec_dir / "task.md"
    if not task_path.is_file():
        return refuse(f"no task.md under {spec_dir}")
    spec_path = spec_dir / "spec.md"
    if not spec_path.is_file():
        return refuse(f"no spec.md under {spec_dir} — the lifecycle state "
                      "cannot be verified")
    status = specstate.spec_status(
        spec_path.read_text(encoding="utf-8", errors="replace"))
    if status is None:
        return refuse("spec.md has no recognizable **Status**: line")
    if status in FROZEN_STATUS and not (
            spec_dir / "approvals" / "approval.md").exists():
        print(f"note: Status {status} with no approvals/approval.md — "
              "migration does not approve: check.py fails this docset "
              "until it is re-approved once — "
              + freeze.approval_steps(spec_dir))
    if status not in MIGRATABLE_STATUS:
        return refuse(f"spec.md Status is {status} — only draft, approved, "
                      "or active docsets migrate; a done plan is a record")

    original = task_path.read_text(encoding="utf-8")
    template_text = template_path.read_text(encoding="utf-8")
    problem, additions = plan_migration(original, template_text)
    if problem == "task":
        return refuse("task.md has no '## ' section — not a recognizable plan")
    if problem == "template":
        return refuse("template has no '## ' section — not a recognizable "
                      "task template")

    if not additions:
        print("already migrated: task.md has every header field the template declares")
        return 0

    for line in additions:
        print(f"  + {line}")
    if dry:
        print(f"dry-run: {len(additions)} header line(s) would be inserted "
              "— nothing written")
        return 0

    prospective = insert_lines(original, additions)
    problems = verify_text(original, prospective, additions)
    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return refuse("prospective text failed verification — nothing written")

    try:
        _durable_replace(task_path, prospective)
    except OSError as exc:
        print(f"migrate aborted: write/replace failed, original preserved: {exc}",
              file=sys.stderr)
        return 1

    problems = []
    try:
        landed_bytes = task_path.read_bytes()
    except OSError as exc:
        landed_bytes = None
        problems.append(f"postcheck: replaced task.md unreadable: {exc}")
    if landed_bytes is not None:
        if landed_bytes != prospective.encode("utf-8"):
            problems.append(
                "postcheck: task.md on disk differs from the verified "
                "prospective text")
        problems += verify_text(original,
                                landed_bytes.decode("utf-8", errors="replace"),
                                additions)
    if not problems:
        try:
            _fsync_dir(task_path)
        except OSError as exc:
            problems = [f"postcheck: directory sync failed after replace: {exc}"]
    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print("postcheck failed — rolling back", file=sys.stderr)
        _rollback(task_path, original)
        return 1

    print(f"migrated: {len(additions)} header line(s) inserted into task.md")
    print("evidence fields stay pending until the normal lifecycle records "
          "them — nothing is inferred")
    return 0


if __name__ == "__main__":
    sys.exit(main())
