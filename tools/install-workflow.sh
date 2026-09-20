#!/usr/bin/env bash
# Install the skill's dynamic-workflow dialects into each coding agent's
# own workflow root (ADR-019).
#
#   *.dwf.ts  -> zcode   : ~/.zcode/workflows/            (--user, default)
#                          <repo>/.zcode/workflows/        (--project)
#   *.js      -> claude  : ~/.claude/workflows/            (--user, default)
#                          <repo>/.claude/workflows/       (--project)
#
# Every master lives at skills/<name>/workflows/ and carries a literal
# __SKILL_DIR__ placeholder; the installed copy gets the target's own
# skill directory baked in (tools/workflow-defs.py regenerates the
# masters — never hand-edit them). A destination that differs from the
# expected content is overwritten only when its hash sits in the root's
# provenance ledger (a previous deploy of ours); anything else is
# foreign — refused loudly, never clobbered (same discipline as
# tools/sync.sh). A user-mode harness whose home root (~/.zcode,
# ~/.claude) does not exist is skipped loudly and never fabricated:
# exit 1 for an explicitly named target, honest signal for `all`.
#
# Usage: tools/install-workflow.sh <zcode|claude|all> [--user|--project]
#                                 [--repo <path>] [--skill-dir <path>]
#                                 [--dry-run] [--check]
#   --user       install into ~/.<harness>/workflows (default)
#   --project    install into <repo>/.<harness>/workflows (repo = cwd,
#                or --repo); the project dir is created — an explicit
#                opt-in, distinct from user mode's never-fabricate rule
#   --skill-dir  bake this skill dir instead of auto-resolving one
#   --dry-run    print the plan, write nothing
#   --check      verify installed copies match a fresh bake; no writes;
#                exit 1 on drift or a missing copy (an absent harness
#                home is a skip, not a drift)
# Exit: 0 installed/verified · 1 refused, drifted, absent home, or no
#       skill copy to bake · 2 usage error.
set -euo pipefail

PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEDGER_NAME=".spec-dev-kit-deployed"
MODE=user
REPO="$PWD"
SKILL_DIR_OVERRIDE=""
DRY_RUN=0
CHECK=0
WANT=()

usage() {
  sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    zcode|claude|all) WANT+=("$1") ;;
    --user) MODE=user ;;
    --project) MODE=project ;;
    --repo) REPO="${2:?--repo needs a path}"; shift ;;
    --skill-dir) SKILL_DIR_OVERRIDE="${2:?--skill-dir needs a path}"; shift ;;
    --dry-run) DRY_RUN=1 ;;
    --check) CHECK=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
[ "${#WANT[@]}" -gt 0 ] || { echo "ERROR: name a target (zcode|claude|all)" >&2; usage >&2; exit 2; }

targets=()
for w in "${WANT[@]}"; do
  if [ "$w" = all ]; then targets+=(zcode claude); else targets+=("$w"); fi
done

sha() { shasum -a 256 < "$1" | cut -d' ' -f1; }

# A dest is ours-and-stale iff its hash sits in the root's ledger under
# the same name (previous deploy of ours); anything else is foreign.
ledger_has() {  # <ledger> <name> <dest-file>
  [ -f "$1" ] || return 1
  awk -v n="$2" -v h="$(sha "$3")" '$1 == h && $2 == n {found = 1}
        END {exit found ? 0 : 1}' "$1"
}

ledger_record() {  # <ledger> <name> <file-deployed>
  local h; h="$(sha "$3")"
  touch "$1"
  grep -v " $2\$" "$1" > "$1.tmp" || true
  printf '%s %s\n' "$h" "$2" >> "$1.tmp"
  mv "$1.tmp" "$1"
}

# The skill dir baked into the installed copy: explicit override wins,
# then the target harness's own root, then the ~/.agents compatibility
# root, then the remaining roots — validated by scripts/graph.py's
# presence, so a bare dir never bakes in.
resolve_skill_dir() {  # <harness> <skill-name>
  local h="$1" name="$2" d
  if [ -n "$SKILL_DIR_OVERRIDE" ]; then
    [ -f "$SKILL_DIR_OVERRIDE/scripts/graph.py" ] && { echo "$SKILL_DIR_OVERRIDE"; return 0; }
    echo "ERROR: --skill-dir has no scripts/graph.py: $SKILL_DIR_OVERRIDE" >&2
    return 1
  fi
  local roots=()
  if [ "$MODE" = project ]; then
    roots+=("$REPO/.$h/skills/$name" "$REPO/.agents/skills/$name" "$REPO/.omp/skills/$name")
  fi
  roots+=("$HOME/.$h/skills/$name" "$HOME/.agents/skills/$name")
  case "$h" in
    zcode)  roots+=("$HOME/.claude/skills/$name" "$HOME/.omp/agent/skills/$name") ;;
    claude) roots+=("$HOME/.zcode/skills/$name"  "$HOME/.omp/agent/skills/$name") ;;
  esac
  for d in "${roots[@]}"; do
    [ -f "$d/scripts/graph.py" ] && { echo "$d"; return 0; }
  done
  echo "ERROR: no installed copy of $name found to bake (checked the .$h, .agents, and sibling roots)" >&2
  echo "       run tools/sync.sh first, or pass --skill-dir <path>" >&2
  return 1
}

dest_root() {  # <harness>
  if [ "$MODE" = project ]; then echo "$REPO/.$1/workflows"
  else echo "$HOME/.$1/workflows"; fi
}

install_master() {  # <master-file> <harness> <skill-name>
  local master="$1" h="$2" name="$3" base root dest skill_dir expected
  base="$(basename "$master")"
  root="$(dest_root "$h")"
  dest="$root/$base"

  # User mode never fabricates a harness directory (D-015); an absent
  # home is a loud skip. In --check the skip is neutral (nothing was
  # ever installed there to drift); in install mode it fails the run.
  if [ "$MODE" = user ] && [ ! -d "$HOME/.$h" ]; then
    echo "skip  $h workflows — $HOME/.$h absent (harness not installed)"
    [ "$CHECK" = 1 ] && return 0 || return 1
  fi

  skill_dir="$(resolve_skill_dir "$h" "$name")" || return 1
  expected="$(mktemp)"
  trap 'rm -f "$expected"' RETURN
  sed "s|__SKILL_DIR__|$skill_dir|g" "$master" > "$expected"

  if [ "$CHECK" = 1 ]; then
    if [ ! -e "$dest" ]; then
      echo "MISSING $dest (skill_dir would be: $skill_dir)"; return 1
    fi
    if cmp -s "$expected" "$dest"; then
      echo "OK  $dest"; return 0
    fi
    echo "DRIFT $dest — reinstall (tools/install-workflow.sh $h) or fix the master"; return 1
  fi

  if [ "$DRY_RUN" = 1 ]; then
    echo "would install $dest (skill_dir: $skill_dir)"; return 0
  fi

  mkdir -p "$root"
  if [ -e "$dest" ] && ! cmp -s "$expected" "$dest" \
     && ! ledger_has "$root/$LEDGER_NAME" "$base" "$dest"; then
    echo "REFUSE $dest — foreign file (differs from a fresh bake, not a prior deploy); resolve manually"
    return 1
  fi
  cp "$expected" "$dest"
  ledger_record "$root/$LEDGER_NAME" "$base" "$dest"
  echo "install $dest (skill_dir: $skill_dir)"
}

fail=0
for h in "${targets[@]}"; do
  # Each skill that ships a workflows/ dir contributes its dialect files
  # for this harness: *.dwf.ts belongs to zcode, *.js to claude. Other
  # extensions are named and skipped — never silently ignored.
  found=0
  for master in "$PKG_ROOT"/skills/*/workflows/*; do
    [ -f "$master" ] || continue
    skill="$(basename "$(dirname "$(dirname "$master")")")"
    case "$master" in
      *.dwf.ts) [ "$h" = zcode ] || continue ;;
      *.js)     [ "$h" = claude ] || continue ;;
      *) echo "note  $master: unknown workflow extension — skipped"; continue ;;
    esac
    found=1
    install_master "$master" "$h" "$skill" || fail=1
  done
  if [ "$found" = 0 ] && [ "$MODE" = user ] && [ -d "$HOME/.$h" ]; then
    echo "note  no workflow dialect files for $h under skills/*/workflows/"
  fi
done

exit $fail
