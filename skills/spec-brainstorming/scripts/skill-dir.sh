#!/usr/bin/env bash
# Print the active spec-brainstorming skill directory — the first existing
# root in SKILL.md's spawn-payload priority order (project before home;
# omp-native roots first, mirroring omp's provider precedence).
# Callers run this once instead of eyeballing eight paths; its output is
# the skill_dir the stage-2 spawn payload would otherwise carry.
set -euo pipefail

for root in .omp .claude .zcode .agents .kilo; do
  if [ -d "$root/skills/spec-brainstorming" ]; then
    cd "$root/skills/spec-brainstorming" && pwd
    exit 0
  fi
done
for root in "$HOME/.omp/agent" "$HOME/.claude" "$HOME/.zcode" "$HOME/.agents" "$HOME/.config/kilo"; do
  if [ -d "$root/skills/spec-brainstorming" ]; then
    cd "$root/skills/spec-brainstorming" && pwd
    exit 0
  fi
done
# Antigravity (agy) sessions: the live copy is inside the agy plugin
# install (workspace .agents/plugins/ or ~/.gemini/config/plugins/).
for root in .agents/plugins/spec-dev-kit "$HOME/.gemini/config/plugins/spec-dev-kit"; do
  if [ -d "$root/skills/spec-brainstorming" ]; then
    cd "$root/skills/spec-brainstorming" && pwd
    exit 0
  fi
done
echo "ERROR: no spec-brainstorming skill dir (checked ./.omp, ./.claude, ./.zcode, ./.agents, ./.kilo, then the same order under \$HOME with ~/.omp/agent for .omp and ~/.config/kilo, then the agy plugin roots)" >&2
exit 1
