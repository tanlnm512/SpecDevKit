#!/usr/bin/env bash
# Print the skill directory this script belongs to: its own location first,
# then ${CLAUDE_PLUGIN_ROOT}, then a scan of harness roots (project before
# home) only when neither holds a SKILL.md — a scan can land on another
# harness's copy, so it is the last resort.
set -euo pipefail

is_skill_root() { [ -f "$1/SKILL.md" ]; }

own="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if is_skill_root "$own"; then
  echo "$own"
  exit 0
fi

if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  for candidate in "$CLAUDE_PLUGIN_ROOT" "$CLAUDE_PLUGIN_ROOT/skills/spec-ship"; do
    if is_skill_root "$candidate"; then
      cd "$candidate" && pwd
      exit 0
    fi
  done
fi

for root in .omp .claude .zcode .agents .kilo \
            "$HOME/.omp/agent" "$HOME/.claude" "$HOME/.zcode" "$HOME/.agents" "$HOME/.config/kilo" \
            .agents/plugins/spec-dev-kit "$HOME/.gemini/config/plugins/spec-dev-kit"; do
  if is_skill_root "$root/skills/spec-ship"; then
    cd "$root/skills/spec-ship" && pwd
    exit 0
  fi
done
echo "ERROR: no spec-ship skill dir (checked the script's own dir, \$CLAUDE_PLUGIN_ROOT, then ./.omp ./.claude ./.zcode ./.agents ./.kilo, the same under \$HOME, and the agy plugin roots)" >&2
exit 1
