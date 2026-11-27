#!/usr/bin/env python3
"""Kit-wide engineering rules and agent budgets — canonical sources,
injected carrier views.

The rules text lives ONCE in rules/engineering-rules.md and the
per-role budget numbers ONCE in rules/agent-limits.md (the browsable,
editable files). This tool injects them into the carrier files the
kit's spawn channels already load:

  skills/spec-build/agents/developer.md             (the code-writing
                                                     archetype — the only
                                                     spec-suite role that
                                                     writes code or tests)
  skills/spec-review/agents/spec-review-fixer.md
                                                     (the fix loop's
                                                      author agent)

as two generated sections: "## Engineering rules (kit-wide)" (the whole
source, both carriers) and "## Budgets (kit-enforced)" (the carrier's
own `## <role key>` subsection of agent-limits.md, so each brief states
only the numbers it owes). An agent learns a limit by reading its
brief, never by hitting it.

Edit the sources, run this tool, re-run drift-check. --check verifies
the committed carriers match a fresh injection (this is the
drift-check.py "kit-rules" category); no argument rewrites them.

"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PKG_ROOT / "rules" / "engineering-rules.md"
LIMITS_SOURCE = PKG_ROOT / "rules" / "agent-limits.md"
HEADING = "## Engineering rules (kit-wide)"
BUDGETS_HEADING = "## Budgets (kit-enforced)"
CARRIERS = (
    (PKG_ROOT / "skills" / "spec-build" / "agents" / "developer.md",
     "spec-build developer"),
    (PKG_ROOT / "skills" / "spec-review" / "agents" / "spec-review-fixer.md",
     "spec-review fixer"),
)


def section_span(text: str, heading: str = HEADING) -> tuple[int, int]:
    """(start, end) of the injected section: from the heading to the
    next same-level heading, or end of file."""
    start = text.find(heading)
    if start < 0:
        raise ValueError(f"{heading!r} not found")
    end = text.find("\n## ", start + len(heading))
    if end < 0:
        end = len(text)
    else:
        end += 1  # the newline belongs to the separator, not the section
    return start, end


def inject(text: str, body: str, heading: str = HEADING) -> str:
    """Replace the carrier's section span with the source body, keeping
    exactly one blank line before a following heading. A heading the
    carrier does not carry yet lands at end of file."""
    try:
        start, end = section_span(text, heading)
    except ValueError:
        return text.rstrip("\n") + "\n\n" + body.rstrip("\n") + "\n"
    if end >= len(text):
        return text[:start] + body.rstrip("\n") + "\n"
    return text[:start] + body.rstrip("\n") + "\n\n" + text[end:]


def budgets_section(role_key: str) -> str:
    """The role's subsection of rules/agent-limits.md as the carrier's
    Budgets section body: the `## <role key>` heading is replaced by the
    kit-level heading, the bullets kept verbatim."""
    text = LIMITS_SOURCE.read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(role_key)}[ \t]*\n"
                  rf"(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        raise ValueError(f"no '## {role_key}' section in {LIMITS_SOURCE}")
    return BUDGETS_HEADING + "\n\n" + m.group(1).strip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="kit-rules.py",
        description="Inject rules/engineering-rules.md and the role's "
                    "rules/agent-limits.md budgets into the carrier "
                    "sections, or --check them against a fresh injection.")
    p.add_argument("--check", action="store_true",
                   help="verify carriers match the sources; exit 1 on drift")
    args = p.parse_args(argv)

    body = SOURCE.read_text(encoding="utf-8")
    rc = 0
    for carrier, role_key in CARRIERS:
        current = carrier.read_text(encoding="utf-8")
        fresh = inject(inject(current, body), budgets_section(role_key),
                       BUDGETS_HEADING)
        rel = carrier.relative_to(PKG_ROOT)
        if current == fresh:
            print(f"OK  {rel}")
        elif args.check:
            print(f"DRIFT {rel} — rerun tools/kit-rules.py")
            rc = 1
        else:
            carrier.write_text(fresh, encoding="utf-8")
            print(f"wrote {rel}")
    if args.check and not rc:
        print("kit rules: OK — carriers match rules/engineering-rules.md "
              "and rules/agent-limits.md")
    return rc


if __name__ == "__main__":
    sys.exit(main())
