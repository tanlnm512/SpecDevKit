#!/usr/bin/env bash
# Scaffold a spec folder from the skill's templates.
# Usage: scaffold.sh <kebab-case-spec-name> [target-root]
# Creates <target-root>/specs/<name>/ with the 7 template files
# and registers it in <target-root>/specs/INDEX.md.
set -euo pipefail

name="${1:?usage: scaffold.sh <kebab-case-spec-name> [target-root]}"
root="${2:-.}"
skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$root/specs/$name"

if ! [[ "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "ERROR: '$name' is not kebab-case (e.g. postgres-backend)" >&2
  exit 1
fi
if [[ -e "$target" ]]; then
  echo "ERROR: $target already exists — refusing to overwrite" >&2
  exit 1
fi

mkdir -p "$target"
for f in spec plan tech-spec task test survey; do
  cp "$skill_dir/templates/$f.md" "$target/$f.md"
done
# research.md ships as the resolved skip marker, not the template: the
# research-gate's common case (no real open questions — most bugfixes) is
# the default, so no run ever pauses "undetermined" on a fresh scaffold
# (D-025). The orchestrator flips it to run by replacing this file with
# the filled template when the spec has real open questions.
printf 'not applicable — no open questions at Stage 0\n' \
  > "$target/research.md"

# Register the new spec in the INDEX registry (create if absent, no duplicates).
index="$root/specs/INDEX.md"
if [[ ! -e "$index" ]]; then
  printf '# Specs index\n' > "$index"
fi
if ! grep -qF "($name/spec.md)" "$index"; then
  printf -- '- [%s](%s/spec.md) — draft (created %s)\n' "$name" "$name" "$(date +%F)" >> "$index"
fi

# Shared project constitution (cross-spec non-negotiables). Created once
# per repo; filled WITH the user — checked at the before-audit.
constitution="$root/specs/CONSTITUTION.md"
if [[ ! -e "$constitution" ]]; then
  cp "$skill_dir/templates/constitution.md" "$constitution"
fi

echo "Scaffolded $target"
echo "Note: check.py FAILs on a fresh scaffold by design — templates ship"
echo "      example IDs (FR-001…) that must be replaced. It verifies the"
echo "      finished docset."
echo "Next: 0) fill specs/CONSTITUTION.md with the user (articles bind every spec)"
echo "      1) fill spec.md with the user (intent is human)"
echo "      2) spawn the analysis wave (see SKILL.md workflow graph)"
