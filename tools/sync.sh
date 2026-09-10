#!/usr/bin/env bash
# Sync every skill in this repo (master source) to every install root,
# then SHA-verify the result.
#
# Topology — N skills (skills/<name>/) x the harness roots below:
#   skills/<name>/            -> ~/.agents/skills/<name>/
#                              -> ~/.claude/skills/<name>/
#                              -> ~/.zcode/skills/<name>/
#                              -> ~/.omp/agent/skills/<name>/
#                                 (omp-native root, priority-100 provider
#                                 — omp sessions load this copy)
#   skills/<name>/commands/<name>.md -> ~/.agents/commands/,
#                                 ~/.claude/commands/, ~/.zcode/commands/
#                                 (only if that skill ships a router
#                                 command; omp needs none — /skill:<name>
#                                 auto-registers)
#   skills/<name>/agents/*.md -> ~/.claude/agents/ (as-is; the harness
#                                 reads Claude-style frontmatter directly)
#                              -> ~/.omp/agent/agents/ (regenerated with
#                                 omp frontmatter by tools/omp-defs.py —
#                                 omp skips ~/.claude/agents and its tool
#                                 registry is lowercase). Files named with
#                                 a leading underscore (shared prose, e.g.
#                                 _shared-protocol.md) are not roles and
#                                 are skipped. zcode gets no agents/
#                                 install step: SKILL.md § Spawn mechanics
#                                 documents it as having no
#                                 user-installable agent types, so it
#                                 only gets skills/ + commands/.
#
# omp also reads ~/.agents/skills (its `agents` provider, priority 70),
# so that root alone would serve omp sessions; the ~/.omp copy makes
# every skill self-sufficient inside omp and wins omp's same-name dedup.
#
# A skill opts into this topology just by existing at skills/<name>/ with
# a SKILL.md — no registration step, no list to edit here.
#
# Run from anywhere: tools/sync.sh — edits always land in skills/<name>/
# first; this script is the only thing that copies out.
set -euo pipefail

PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

SKILLS_ROOTS=(
  "$HOME/.agents/skills"
  "$HOME/.claude/skills"
  "$HOME/.zcode/skills"
  "$HOME/.omp/agent/skills"
)
COMMANDS_ROOTS=(
  "$HOME/.agents/commands"
  "$HOME/.claude/commands"
  "$HOME/.zcode/commands"
)
CLAUDE_AGENTS_ROOT="$HOME/.claude/agents"
OMP_AGENTS_ROOT="$HOME/.omp/agent/agents"

SKILLS=()
for d in "$PKG_ROOT"/skills/*/; do
  [ -f "${d}SKILL.md" ] || continue
  SKILLS+=("$(basename "$d")")
done

install_skill_tree() {  # <skill-dir> <dest-root>
  mkdir -p "$2"
  rsync -a --delete --exclude '.DS_Store' --exclude '__pycache__/' \
    "$1/" "$2/$(basename "$1")/"
}

for name in "${SKILLS[@]}"; do
  skill_dir="$PKG_ROOT/skills/$name"

  for root in "${SKILLS_ROOTS[@]}"; do
    install_skill_tree "$skill_dir" "$root"
  done

  if [ -f "$skill_dir/commands/$name.md" ]; then
    for root in "${COMMANDS_ROOTS[@]}"; do
      mkdir -p "$root"
      cp "$skill_dir/commands/$name.md" "$root/$name.md"
    done
  fi

  if [ -d "$skill_dir/agents" ]; then
    mkdir -p "$CLAUDE_AGENTS_ROOT"
    for f in "$skill_dir"/agents/*.md; do
      base="$(basename "$f")"
      [[ "$base" == _* ]] && continue
      cp "$f" "$CLAUDE_AGENTS_ROOT/$base"
    done
    mkdir -p "$OMP_AGENTS_ROOT"
    python3 "$PKG_ROOT/tools/omp-defs.py" --skill-dir "$skill_dir" --out "$OMP_AGENTS_ROOT"
  fi
done

# --- verify ---------------------------------------------------------------

verify_tree() {  # <master> <copy> <label>
  local master="$1" copy="$2" label="$3" m c
  m="$(cd "$master" && find . -type f ! -name .DS_Store ! -path '*/__pycache__/*' -exec shasum -a 256 {} + | sort -k2)"
  c="$(cd "$copy" && find . -type f ! -name .DS_Store ! -path '*/__pycache__/*' -exec shasum -a 256 {} + | sort -k2)"
  if [[ "$m" == "$c" ]]; then
    echo "OK  $label — identical ($(printf '%s\n' "$m" | wc -l | tr -d ' ') files)"
  else
    echo "DRIFT $label"
    diff <(printf '%s\n' "$m") <(printf '%s\n' "$c") || true
    fail=1
  fi
}

for name in "${SKILLS[@]}"; do
  skill_dir="$PKG_ROOT/skills/$name"

  for root in "${SKILLS_ROOTS[@]}"; do
    verify_tree "$skill_dir" "$root/$name" "$root/$name"
  done

  if [ -f "$skill_dir/commands/$name.md" ]; then
    for root in "${COMMANDS_ROOTS[@]}"; do
      if cmp -s "$skill_dir/commands/$name.md" "$root/$name.md"; then
        echo "OK  $root/$name.md"
      else
        echo "DRIFT $root/$name.md"; fail=1
      fi
    done
  fi

  if [ -d "$skill_dir/agents" ]; then
    for f in "$skill_dir"/agents/*.md; do
      base="$(basename "$f")"
      [[ "$base" == _* ]] && continue
      if cmp -s "$f" "$CLAUDE_AGENTS_ROOT/$base"; then
        echo "OK  def $base"
      else
        echo "DRIFT def $base"; fail=1
      fi
    done

    # ~/.omp/agent/agents is a shared root (omp agent unpacks, other
    # skills' own roles, hand-added defs) — verify per this skill's own
    # generated file, never the whole directory. Regenerate fresh into a
    # scratch dir and diff content only: the stale-removal invariant
    # itself (an old/renamed role never lingers) is covered by
    # tools/tests/test_omp_defs.py against omp-defs.py directly, run on
    # a scratch dir rather than the live shared one.
    tmp="$(mktemp -d)"
    python3 "$PKG_ROOT/tools/omp-defs.py" --skill-dir "$skill_dir" --out "$tmp" >/dev/null
    for f in "$tmp"/*.md; do
      [ -e "$f" ] || continue
      base="$(basename "$f")"
      if cmp -s "$f" "$OMP_AGENTS_ROOT/$base"; then
        echo "OK  omp def $base"
      else
        echo "DRIFT omp def $base"; fail=1
      fi
    done
    rm -rf "$tmp"
  fi
done

exit $fail
