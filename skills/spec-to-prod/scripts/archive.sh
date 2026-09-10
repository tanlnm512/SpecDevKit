#!/usr/bin/env bash
# Archive a completed spec: move specs/<name>/ to
# specs/archive/<date>-<name>/ and repoint its INDEX.md line.
# Usage: archive.sh <kebab-case-spec-name> [target-root]
set -euo pipefail

name="${1:?usage: archive.sh <kebab-case-spec-name> [target-root]}"
root="${2:-.}"
spec="$root/specs/$name"

if [[ ! -d "$spec" ]]; then
  echo "ERROR: $spec is not a directory" >&2
  exit 1
fi
# Only completed specs leave the active tree — Status is the state
# machine's source of truth (check.py keys off the same line).
if ! grep -qE '^\*\*Status\*\*: done' "$spec/spec.md" 2>/dev/null; then
  echo "ERROR: $spec/spec.md is not '**Status**: done' — archive only completed specs" >&2
  exit 1
fi

day="$(date +%F)"
dest="$root/specs/archive/$day-$name"
if [[ -e "$dest" ]]; then
  echo "ERROR: $dest already exists — refusing to overwrite" >&2
  exit 1
fi

mkdir -p "$root/specs/archive"
mv "$spec" "$dest"

# Repoint the INDEX line at the archived path. python3, not sed -i:
# BSD and GNU sed disagree on the in-place flag, and python3 is already
# a package requirement. Only touched when the line actually cites the
# spec (a hand-pruned INDEX is left alone).
index="$root/specs/INDEX.md"
if [[ -f "$index" ]] && grep -qF "($name/spec.md)" "$index"; then
  python3 - "$index" "$name" "$day" <<'PY'
import sys
from pathlib import Path

p, name, day = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
p.write_text(p.read_text().replace(f"({name}/spec.md)", f"(archive/{day}-{name}/spec.md)"))
PY
fi

echo "Archived specs/$name -> specs/archive/$day-$name (INDEX repointed)"
