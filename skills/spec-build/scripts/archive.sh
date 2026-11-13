#!/usr/bin/env bash
# Archive a delivered spec: move specs/<name>/ to
# specs/archive/<date>-<name>/, repoint its INDEX.md line and mark it
# done there. Refuses unless spec.md says Status: done AND the delivery
# record (task.md, or spec.md at Tier: tiny) names a commit. Drops the
# regenerable spawns/ payloads; writes retro.md into the archived dir
# (reusing the one the delivery pass wrote at C2) and rolls its
# D-### titles up to specs/context/decisions.md (retro.py); commits
# nothing.
# Usage: archive.sh <kebab-case-spec-name> [target-root]
set -euo pipefail

scripts_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

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
if ! python3 - "$scripts_dir" "$spec" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import specstate

spec = Path(sys.argv[2])
spec_md = (spec / "spec.md").read_text(encoding="utf-8", errors="replace")
holder = spec / ("spec.md" if specstate.spec_tier(spec_md) == "tiny" else "task.md")
text = holder.read_text(encoding="utf-8", errors="replace") if holder.exists() else ""
if specstate.delivery_state(text)[0] != "delivered":
    print(f"ERROR: {holder} has no `Delivered: commit @ <sha>` record — "
          "archive only delivered specs (C2 writes it)", file=sys.stderr)
    sys.exit(1)
PY
then
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

rm -rf "$spec/spawns"

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

# Repoint the INDEX line at the archived path and set its status word
# to done. python3, not sed -i: BSD and GNU sed disagree on the in-place
# flag, and python3 is already a package requirement. Only touched when
# the line actually cites the spec (a hand-pruned INDEX is left alone).
index="$root/specs/INDEX.md"
if [[ -f "$index" ]] && grep -qF "($name/spec.md)" "$index"; then
  if ! python3 - "$index" "$name" "$day" <<'PY'
import re
import sys
from pathlib import Path

p, name, day = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
lines = []
for line in p.read_text().splitlines(keepends=True):
    if f"({name}/spec.md)" in line:
        line = line.replace(f"({name}/spec.md)", f"(archive/{day}-{name}/spec.md)")
        line = re.sub(r"( — )[A-Za-z]+", r"\1done", line, count=1)
    lines.append(line)
p.write_text("".join(lines))
PY
  then
    echo "ERROR: INDEX repoint failed for $index" >&2
    restore_source
    exit 1
  fi
fi

rm -f "$journal"
echo "Archived specs/$name -> specs/archive/$day-$name (INDEX repointed, marked done)"
# The move has landed; a retro failure is reported, never rolled back.
if ! python3 "$scripts_dir/retro.py" "$dest" "$name" "$root"; then
  echo "ERROR: retro.md not written — rerun: python3 $scripts_dir/retro.py $dest $name $root" >&2
  exit 1
fi
echo "next: the move is uncommitted — ask the user before committing it, e.g."
echo "  git add -A specs/$name specs/archive/$day-$name specs/INDEX.md specs/context/decisions.md"
echo "  git commit -m \"chore(specs): archive $name\""
