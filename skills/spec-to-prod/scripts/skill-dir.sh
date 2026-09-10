#!/usr/bin/env bash
# Print the active spec-to-prod skill directory — the first existing root
# in SKILL.md's Spawn-mechanics priority order (project before home;
# omp-native roots first, mirroring omp's provider precedence: only omp
# reads .omp, and its native provider outranks the .claude/.agents
# adapters, so in an omp session the ~/.omp copy is the live one. All
# roots are byte-identical — sync.sh is the only copier — so a
# cross-harness hit is harmless).
# The orchestrator runs this once per session instead of eyeballing
# eight paths; its output is the `skill_dir` carried in every spawn
# payload.
set -euo pipefail

for root in .omp .claude .zcode .agents; do
  if [ -d "$root/skills/spec-to-prod" ]; then
    cd "$root/skills/spec-to-prod" && pwd
    exit 0
  fi
done
for root in "$HOME/.omp/agent" "$HOME/.claude" "$HOME/.zcode" "$HOME/.agents"; do
  if [ -d "$root/skills/spec-to-prod" ]; then
    cd "$root/skills/spec-to-prod" && pwd
    exit 0
  fi
done
# Antigravity (agy) sessions: the live copy is inside the agy plugin
# install (workspace .agents/plugins/ or ~/.gemini/config/plugins/).
for root in .agents/plugins/spec-dev-kit "$HOME/.gemini/config/plugins/spec-dev-kit"; do
  if [ -d "$root/skills/spec-to-prod" ]; then
    cd "$root/skills/spec-to-prod" && pwd
    exit 0
  fi
done
echo "ERROR: no spec-to-prod skill dir (checked ./.omp, ./.claude, ./.zcode, ./.agents, then the same order under \$HOME with ~/.omp/agent for .omp, then the agy plugin roots)" >&2
exit 1
