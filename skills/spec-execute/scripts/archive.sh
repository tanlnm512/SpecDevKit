#!/usr/bin/env bash
# Archive a completed spec: move specs/<name>/ to
# specs/archive/<date>-<name>/ and repoint its INDEX.md line.
# Usage: archive.sh <kebab-case-spec-name> [target-root]
set -euo pipefail

name="${1:?usage: archive.sh <kebab-case-spec-name> [target-root]}"
root="${2:-.}"

if ! [[ "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "ERROR: '$name' is not kebab-case (e.g. postgres-backend)" >&2
  exit 1
fi
spec="$root/specs/$name"

if [[ -L "$spec" ]]; then
  echo "ERROR: $spec is a symlink — refusing to archive" >&2
  exit 1
fi
if [[ ! -d "$spec" ]]; then
  echo "ERROR: $spec is not a directory" >&2
  exit 1
fi
# Canonical containment: compare resolved paths, not lexical prefixes.
specs_canon="$(cd "$root/specs" && pwd -P)"
spec_canon="$(cd "$spec" && pwd -P)"
if [[ "$spec_canon" != "$specs_canon/$name" ]]; then
  echo "ERROR: $spec resolves to $spec_canon, not a direct child of $specs_canon" >&2
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

# Journal the move until index and final validation succeed.
journal="$dest.journal"
if ! printf '%s\n%s\n' "$dest" "$spec" > "$journal"; then
  echo "ERROR: cannot write rollback journal $journal" >&2
  exit 1
fi

restore_source() {
  if mv "$dest" "$spec" 2>/dev/null; then
    rm -f "$journal"
    echo "recovered: $dest restored to $spec — nothing archived" >&2
  else
    echo "recovery needed: mv $dest $spec (journal: $journal)" >&2
  fi
}

if ! mv "$spec" "$dest"; then
  rm -f "$journal"
  echo "ERROR: move to $dest failed — $spec untouched" >&2
  exit 1
fi

if [[ ! -f "$dest/spec.md" ]] || ! grep -qE '^\*\*Status\*\*: done' "$dest/spec.md" 2>/dev/null; then
  echo "ERROR: final validation failed for $dest/spec.md" >&2
  restore_source
  exit 1
fi

# Repoint the INDEX line at the archived path. python3, not sed -i:
# BSD and GNU sed disagree on the in-place flag, and python3 is already
# a package requirement. Only touched when the line actually cites the
# spec (a hand-pruned INDEX is left alone).
index="$root/specs/INDEX.md"
if [[ -f "$index" ]] && grep -qF "($name/spec.md)" "$index"; then
  if ! python3 - "$index" "$name" "$day" <<'PY'
import sys
from pathlib import Path

p, name, day = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
p.write_text(p.read_text().replace(f"({name}/spec.md)", f"(archive/{day}-{name}/spec.md)"))
PY
  then
    echo "ERROR: INDEX repoint failed for $index" >&2
    restore_source
    exit 1
  fi
fi

rm -f "$journal"
echo "Archived specs/$name -> specs/archive/$day-$name (INDEX repointed)"
