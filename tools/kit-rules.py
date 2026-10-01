#!/usr/bin/env python3
"""Kit-wide engineering rules — one canonical source, injected carrier
views.

The rules text lives ONCE in rules/engineering-rules.md (the browsable,
editable file). This tool injects it verbatim as the
"## Engineering rules (kit-wide)" section into the two carrier files the
kit's spawn channels already load:

  skills/spec-to-prod/agents/_shared-protocol.md   (embedded into every
                                                    spawn payload by
                                                    graph.py build_payload)
  skills/spec-code-review/agents/code-review-fixer.md
                                                   (runtime-loaded into
                                                    the fix loop by both
                                                    workflow dialects)

Edit the rules in the source file, run this tool, re-run drift-check.
--check verifies the committed carriers match a fresh injection (this is
the drift-check.py "kit-rules" category); no argument rewrites them.

See skills/spec-to-prod/decisions/028-kit-wide-engineering-rules.md and
rules/engineering-rules.md's role as the single source of truth.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PKG_ROOT / "rules" / "engineering-rules.md"
HEADING = "## Engineering rules (kit-wide)"
CARRIERS = (
    PKG_ROOT / "skills" / "spec-to-prod" / "agents" / "_shared-protocol.md",
    PKG_ROOT / "skills" / "spec-code-review" / "agents"
    / "code-review-fixer.md",
)


def section_span(text: str) -> tuple[int, int]:
    """(start, end) of the injected section: from the heading to the
    next same-level heading, or end of file."""
    start = text.find(HEADING)
    if start < 0:
        raise ValueError(f"{HEADING!r} not found")
    end = text.find("\n## ", start + len(HEADING))
    if end < 0:
        end = len(text)
    else:
        end += 1  # the newline belongs to the separator, not the section
    return start, end


def inject(text: str, body: str) -> str:
    """Replace the carrier's section span with the source body, keeping
    exactly one blank line before a following heading."""
    start, end = section_span(text)
    if end >= len(text):
        return text[:start] + body.rstrip("\n") + "\n"
    return text[:start] + body.rstrip("\n") + "\n\n" + text[end:]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="kit-rules.py",
        description="Inject rules/engineering-rules.md into the two "
                    "carrier sections, or --check them against a fresh "
                    "injection.")
    p.add_argument("--check", action="store_true",
                   help="verify carriers match the source; exit 1 on drift")
    args = p.parse_args(argv)

    body = SOURCE.read_text(encoding="utf-8")
    rc = 0
    for carrier in CARRIERS:
        current = carrier.read_text(encoding="utf-8")
        fresh = inject(current, body)
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
        print("kit rules: OK — carriers match rules/engineering-rules.md")
    return rc


if __name__ == "__main__":
    sys.exit(main())
