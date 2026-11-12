#!/usr/bin/env bash
# Scaffold a spec folder from the skill's templates.
# Usage: scaffold.sh [--tier tiny|full] [--into-existing] <kebab-case-spec-name> [target-root]
# Default tier: tiny — the ONE-FILE contract (spec.md carries the task
# list in § Tasks). --tier full scaffolds the docset. Both register in
# <target-root>/specs/INDEX.md.
# --into-existing fills an intake dir (intent.md already there) without
# overwriting any file that exists. At full tier it leaves the research
# gate open: the freshly copied tech-spec.md ships without its skip
# form, so the gate is judged, never pre-skipped.
set -euo pipefail

tier=tiny
existing=0
while [ "${1:-}" = "--tier" ] || [ "${1:-}" = "--into-existing" ]; do
  if [ "$1" = "--into-existing" ]; then
    existing=1
    shift
  else
    tier="${2:?--tier needs tiny|full}"
    case "$tier" in tiny|full) ;; *) echo "ERROR: --tier must be tiny|full" >&2; exit 2 ;; esac
    shift 2
  fi
done

name="${1:?usage: scaffold.sh [--tier tiny|full] [--into-existing] <kebab-case-spec-name> [target-root]}"
root="${2:-.}"
skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$root/specs/$name"

if ! [[ "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "ERROR: '$name' is not kebab-case (e.g. postgres-backend)" >&2
  exit 1
fi
if [[ -e "$target" && "$existing" = 0 ]]; then
  echo "ERROR: $target already exists — refusing to overwrite (--into-existing to fill it)" >&2
  exit 1
fi

# `cp -n` exits nonzero on an existing target on some platforms.
copy_new() { [ -e "$2" ] || cp "$1" "$2"; }

mkdir -p "$target"
fresh_tech=0
if [ "$tier" = tiny ]; then
  copy_new "$skill_dir/templates/spec-tiny.md" "$target/spec.md"
else
  for f in spec plan tech-spec task test survey; do
    if [ "$f" = tech-spec ] && [ ! -e "$target/tech-spec.md" ]; then
      fresh_tech=1
    fi
    copy_new "$skill_dir/templates/$f.md" "$target/$f.md"
  done
fi
# tech-spec.md's `## Questions & options` section ships as the resolved
# skip form, not an empty one: the research-gate's common case (no real
# open questions — most bugfixes) is the default, so no run ever pauses
# "undetermined" on a fresh scaffold. The orchestrator flips it to run by
# writing the real questions into the section. A full-tier draft from an
# intent is the exception: its gate stays open to be judged, so the fresh
# copy loses the skip lines (the judge_gate logic, applied one file
# deeper than the retired research.md write).
judge_gate=0
if [ "$existing" = 1 ] && [ "$tier" = full ]; then judge_gate=1; fi
if [ "$judge_gate" = 1 ] && [ "$fresh_tech" = 1 ]; then
  python3 - "$target/tech-spec.md" <<'PY'
import sys
path = sys.argv[1]
skip = "not applicable \u2014 no open questions at Stage 0"
with open(path, encoding="utf-8") as fh:
    lines = fh.readlines()
kept = [l for l in lines
        if l.strip() not in (skip, "None \u2014 <why>")]
with open(path, "w", encoding="utf-8") as fh:
    fh.writelines(kept)
PY
fi

# Register the spec in specs/INDEX.md — index.py is the one writer of
# its lines, so a later status, type, or dependency change re-renders
# the same way.
python3 "$skill_dir/scripts/index.py" "$target" > /dev/null

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
echo "Next: 0) draft specs/CONSTITUTION.md with the user before the approve"
echo "         gate (SKILL.md § The constitution; articles bind every spec)"
if [ "$existing" = 1 ]; then
  echo "      1) draft spec.md from intent.md, replacing every placeholder"
  echo "         and example line"
  if [ "$judge_gate" = 1 ]; then
    echo "         tech-spec.md § Questions & options ships without its"
    echo "         skip form on purpose — the research gate is yours to"
    echo "         judge (SKILL.md § The research gate)"
  fi
else
  echo "      1) fill spec.md with the user (intent is human)"
fi
if [ "$tier" = tiny ]; then
  echo "      2) author § Tasks with the user, then run the graph — the"
  echo "         analysis/authoring nodes are SKIPPED at this tier"
  echo "      Grow to the full docset when risk appears:"
  echo "         python3 <spec-build skill_dir>/scripts/migrate.py grow $target"
else
  echo "      2) spawn the analysis wave (see SKILL.md § The run)"
fi
