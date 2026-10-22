#!/usr/bin/env bash
# Scaffold a spec folder from the skill's templates.
# Usage: scaffold.sh [--tier tiny|full] <kebab-case-spec-name> [target-root]
# Default tier: tiny — the ONE-FILE contract (spec.md carries the task
# list in § Tasks). --tier full scaffolds the 7-file docset. Both
# register in <target-root>/specs/INDEX.md.
set -euo pipefail

tier=tiny
if [ "${1:-}" = "--tier" ]; then
  tier="${2:?--tier needs tiny|full}"
  case "$tier" in tiny|full) ;; *) echo "ERROR: --tier must be tiny|full" >&2; exit 2 ;; esac
  shift 2
fi

name="${1:?usage: scaffold.sh [--tier tiny|full] <kebab-case-spec-name> [target-root]}"
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
if [ "$tier" = tiny ]; then
  cp "$skill_dir/templates/spec-tiny.md" "$target/spec.md"
else
  for f in spec plan tech-spec task test survey; do
    cp "$skill_dir/templates/$f.md" "$target/$f.md"
  done
fi
# research.md ships as the resolved skip marker, not the template: the
# research-gate's common case (no real open questions — most bugfixes) is
# the default, so no run ever pauses "undetermined" on a fresh scaffold.
# The orchestrator flips it to run by replacing this file with
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
# per repo; filled WITH the user — read at approval, carried in every
# implementer payload.
constitution="$root/specs/CONSTITUTION.md"
if [[ ! -e "$constitution" ]]; then
  cp "$skill_dir/templates/constitution.md" "$constitution"
fi

echo "Scaffolded $target (tier: $tier)"
echo "Note: check.py FAILs on a fresh scaffold by design — templates ship"
echo "      example IDs (FR-001…) that must be replaced. It verifies the"
echo "      finished docset."
echo "Next: 0) fill specs/CONSTITUTION.md with the user (articles bind every spec)"
echo "      1) fill spec.md with the user (intent is human)"
if [ "$tier" = tiny ]; then
  echo "      2) author § Tasks with the user, then run the graph — the"
  echo "         analysis/authoring nodes are SKIPPED at this tier"
  echo "      Grow to the full docset when risk appears:"
  echo "         python3 $skill_dir/scripts/migrate.py grow $target"
else
  echo "      2) spawn the analysis wave (see SKILL.md workflow graph)"
fi
