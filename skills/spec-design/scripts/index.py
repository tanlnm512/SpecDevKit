#!/usr/bin/env python3
"""specs/INDEX.md — the cross-spec view, one derived line per spec.

    - [<name>](<name>/spec.md) — <status> · <type> · <tier>[ · depends on <a>, <b>]

Every field is read from the spec's own spec.md headers, so the line is
rendered, never hand-maintained: scaffold.sh registers a new spec
through this module, check.py compares the committed line against a
fresh render and names this command when they differ, and an archived
spec renders with its `archive/<date>-<name>/` link. Lines for other
specs, and anything else in the file, are left untouched.

Usage: index.py <spec-dir> [<spec-dir> ...]   upsert those specs' lines
       index.py --all <specs-root>            upsert every spec under the
                                              root, archive included
Exit:  0 = INDEX.md current · 1 = a named dir holds no spec.md · 2 = usage
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specstate  # noqa: E402

ARCHIVE_DIR = "archive"
NON_SPEC_DIRS = (ARCHIVE_DIR, "context")
ARCHIVED_NAME = re.compile(r"\d{4}-\d{2}-\d{2}-(.+)\Z")
HEADER = "# Specs index\n"


def spec_name(spec_dir: Path) -> str:
    """The spec's name: its dir name, less an archive date prefix."""
    if spec_dir.parent.name == ARCHIVE_DIR:
        m = ARCHIVED_NAME.match(spec_dir.name)
        if m:
            return m.group(1)
    return spec_dir.name


def specs_root(spec_dir: Path) -> Path:
    parent = spec_dir.parent
    return parent.parent if parent.name == ARCHIVE_DIR else parent


def render_line(spec_dir: Path) -> str | None:
    """The INDEX.md line for one spec dir; None when it holds no spec.md."""
    try:
        text = (spec_dir / "spec.md").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return None
    link = spec_dir.relative_to(specs_root(spec_dir)).as_posix()
    fields = [specstate.spec_status(text) or "draft",
              specstate.spec_type(text), specstate.spec_tier(text)]
    depends = specstate.spec_depends(text)
    if depends:
        fields.append("depends on " + ", ".join(depends))
    return (f"- [{spec_name(spec_dir)}]({link}/spec.md) — "
            + " · ".join(fields))


def line_pattern(name: str) -> re.Pattern[str]:
    """Matches the spec's link wherever it lives — active or archived."""
    return re.compile(
        rf"\((?:{ARCHIVE_DIR}/\d{{4}}-\d{{2}}-\d{{2}}-)?{re.escape(name)}"
        r"/spec\.md\)")


def committed_line(index_text: str, name: str) -> str | None:
    pattern = line_pattern(name)
    return next((line for line in index_text.splitlines()
                 if pattern.search(line)), None)


def upsert(index_text: str, name: str, line: str) -> str:
    """index_text with the spec's line replaced in place, or appended."""
    pattern = line_pattern(name)
    lines = index_text.splitlines()
    for i, existing in enumerate(lines):
        if pattern.search(existing):
            lines[i] = line
            break
    else:
        lines.append(line)
    return "\n".join(lines) + "\n"


def all_spec_dirs(root: Path) -> list[Path]:
    active = [p for p in root.iterdir()
              if p.is_dir() and p.name not in NON_SPEC_DIRS]
    archive = root / ARCHIVE_DIR
    archived = list(archive.iterdir()) if archive.is_dir() else []
    return sorted(p for p in active + archived
                  if (p / "spec.md").is_file())


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    if len(argv) == 2 and argv[0] == "--all" and Path(argv[1]).is_dir():
        spec_dirs = all_spec_dirs(Path(argv[1]))
    elif argv and not any(a.startswith("-") for a in argv):
        spec_dirs = [Path(a) for a in argv]
    else:
        print(__doc__, file=sys.stderr)
        return 2
    rc = 0
    for spec_dir in spec_dirs:
        spec_dir = spec_dir.resolve()
        line = render_line(spec_dir)
        if line is None:
            print(f"FAIL: {spec_dir} holds no spec.md", file=sys.stderr)
            rc = 1
            continue
        path = specs_root(spec_dir) / "INDEX.md"
        current = (path.read_text(encoding="utf-8") if path.exists()
                   else HEADER)
        updated = upsert(current, spec_name(spec_dir), line)
        if updated != current or not path.exists():
            path.write_text(updated, encoding="utf-8")
        print(line)
    return rc


if __name__ == "__main__":
    sys.exit(main())
