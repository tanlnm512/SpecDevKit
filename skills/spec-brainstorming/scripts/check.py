#!/usr/bin/env python3
"""Mechanical handoff checks for a written design-spec artifact.

Usage: check.py ARTIFACT
Exit:  0 = every mechanical criterion green · 1 = any failure
"""
import argparse
import re
import sys
from pathlib import Path

SECTIONS = (
    "Direction",
    "Problem Statement",
    "User Personas",
    "Core MVP Features",
    "Potential Risk Mitigations",
)

# Case-sensitive stems pinned to PLACEHOLDER_STEMS in tests/test_flow_contracts.py;
# other angle brackets (e.g. a CLI's <term> argument) are legitimate.
PLACEHOLDER_STEMS = (
    "<Name>", "<date>", "<persona>", "<angle", "<feature", "<the ",
    "<risk", "<why", "<mitigation", "<the one",
)

DIRECTION_FIELDS = (
    ("Selected", re.compile(r"(?m)^- Selected:.*\S")),
    ("Rationale", re.compile(r"(?m)^- Rationale:.*\S")),
    ("Rejected with a reason after an em dash",
     re.compile(r"(?m)^- Rejected:.*\S.* — .*\S")),
)
NUMBERED_FEATURE = re.compile(r"(?m)^\d+\.\s+\S")
H2_HEADING = re.compile(r"^## (.+?)\s*$")
SEPARATOR_ROW = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")
RISK_HEADER = "| Risk (from the panel) | Early warning | Mitigation or acceptance |"
RISK_CELLS = ("risk name", "early warning", "mitigation or acceptance")
OUT_OF_SCOPE_MARKER = "**Out of scope (day-one cut list)**:"
KILL_MARKER = "**Kill criteria**:"
ELLIPSIS_ONLY = {"…", "..."}

GREEN_SUMMARY = (
    "Direction, Problem Statement, User Personas, Core MVP Features, "
    "Potential Risk Mitigations present in pinned order and non-empty; no "
    "surviving template placeholders; Direction selection, rationale, and "
    "rejection recorded; numbered feature list and out-of-scope cut list "
    "present; every risk row complete; kill criteria stated"
)

JUDGMENT = (
    "JUDGMENT: criteria this check does not decide — digest-to-artifact "
    "dealbreaker mapping (every Cynic dealbreaker from the digest appears in "
    "the risk table; the digest is not part of the artifact); whether the "
    "rationale is in the user's terms (the panel's favorite is not the "
    "direction); whether kill criteria are observable (stated so the evidence "
    "could actually be seen)"
)


def split_sections(lines):
    sections = {}
    duplicate_required = []
    body = None
    for number, line in enumerate(lines, 1):
        heading = H2_HEADING.match(line)
        if heading:
            title = heading.group(1)
            if title not in sections:
                sections[title] = {"line": number, "body": []}
            elif title in SECTIONS:
                duplicate_required.append((number, title))
            body = sections[title]["body"]
            continue
        if body is not None:
            body.append((number, line))
    return sections, duplicate_required


def section_text(section):
    return "\n".join(line for _, line in section["body"])


def has_content(section):
    return any(line.strip() for _, line in section["body"])


def marker_value(section, marker):
    body = section["body"]
    for index, (_, line) in enumerate(body):
        if marker not in line:
            continue
        value = [line.split(marker, 1)[1]]
        for _, following in body[index + 1:]:
            if not following.strip():
                break
            value.append(following)
        return " ".join(value).strip()
    return None


def is_unfilled(value):
    stripped = (value or "").strip()
    return not stripped or stripped in ELLIPSIS_ONLY


def placeholder_failures(lines):
    failures = []
    for number, line in enumerate(lines, 1):
        for stem in PLACEHOLDER_STEMS:
            start = line.find(stem)
            if start == -1:
                continue
            end = line.find(">", start)
            token = line[start:end + 1] if end != -1 else stem
            failures.append((number, "placeholder", f"{token} (stem {stem}) survived"))
    return failures


def direction_failures(section):
    text = section_text(section)
    failures = []
    for label, pattern in DIRECTION_FIELDS:
        if not pattern.search(text):
            failures.append((section["line"], "Direction", f"{label} missing or incomplete"))
    return failures


def feature_failures(section):
    failures = []
    if not NUMBERED_FEATURE.search(section_text(section)):
        failures.append((section["line"], "feature-list", "no numbered feature item"))
    if is_unfilled(marker_value(section, OUT_OF_SCOPE_MARKER)):
        failures.append((section["line"], "out-of-scope", "cut list missing or empty"))
    return failures


def risk_failures(section):
    failures = []
    has_header = False
    has_data_row = False
    in_table = False
    for number, line in section["body"]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue
        if RISK_HEADER in stripped:
            has_header = True
            in_table = True
            continue
        if SEPARATOR_ROW.match(stripped):
            in_table = True
            continue
        if not in_table:
            continue
        has_data_row = True
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        cells += [""] * (3 - len(cells))
        missing = [name for name, cell in zip(RISK_CELLS, cells) if not cell]
        if missing:
            risk = cells[0] or "unnamed"
            failures.append((number, "risk-row", f"'{risk}' missing {' and '.join(missing)}"))
    if not has_header:
        failures.append((section["line"], "risk-table", "pinned three-column header missing"))
    elif not has_data_row:
        failures.append((section["line"], "risk-table", "no risk data rows"))
    return failures


def content_failures(lines):
    failures = []
    sections, duplicate_required = split_sections(lines)
    for number, title in duplicate_required:
        failures.append((number, "section", f"{title} duplicated"))
    found = []
    for title in SECTIONS:
        section = sections.get(title)
        if section is None:
            failures.append((0, "section", f"{title} missing"))
            continue
        found.append(section)
        if not has_content(section):
            failures.append((section["line"], "section", f"{title} empty"))
    positions = [section["line"] for section in found]
    if len(positions) > 1 and positions != sorted(positions):
        misplaced = next(positions[i] for i in range(1, len(positions))
                         if positions[i] < positions[i - 1])
        failures.append((misplaced, "section-order", "sections not in the pinned order"))
    if "Direction" in sections:
        failures.extend(direction_failures(sections["Direction"]))
    if "Core MVP Features" in sections:
        failures.extend(feature_failures(sections["Core MVP Features"]))
    if "Potential Risk Mitigations" in sections:
        risks = sections["Potential Risk Mitigations"]
        failures.extend(risk_failures(risks))
        if is_unfilled(marker_value(risks, KILL_MARKER)):
            failures.append((risks["line"], "kill-criteria", "not stated or empty"))
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="check a written design-spec artifact against the handoff gate's mechanical criteria")
    parser.add_argument("artifact", help="path to the design-spec artifact")
    args = parser.parse_args(argv)
    named = args.artifact
    try:
        text = Path(named).read_text(encoding="utf-8")
    except FileNotFoundError:
        failures = [(0, "artifact", "file not found")]
    except IsADirectoryError:
        failures = [(0, "artifact", "not a regular file")]
    except PermissionError:
        failures = [(0, "artifact", "not readable")]
    except UnicodeDecodeError:
        failures = [(0, "artifact", "not UTF-8 text")]
    except OSError:
        failures = [(0, "artifact", "not readable")]
    else:
        lines = text.splitlines()
        failures = content_failures(lines) + placeholder_failures(lines)

    for number, criterion, detail in failures:
        print(f"FAIL {named}:{number} {criterion}: {detail}")
    if not failures:
        print(f"PASS {named}: {GREEN_SUMMARY}")
    print(JUDGMENT)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
