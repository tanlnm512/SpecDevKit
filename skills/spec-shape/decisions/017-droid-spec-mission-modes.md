# D-017: Droid spec/mission support is a separate surface, not a SKILL.md section

Factory Droid splits a session two ways no other harness does: Spec
Mode is hard read-only (spawned subagents clamp to read-only and
low-risk shell too), and subagents cannot spawn subagents — the Task
tool is not available to them. The pipeline's authoring phase therefore
lands inside Spec Mode on paper only, and only a session holding Task
can run waves. The mapping — spec mode = spec/clarify/research-gate on
paper, ExitSpecMode approval ≠ `Status: approved`; mission mode =
orchestrator-session-only execution, workers excluded, mission
scrutiny/user-testing skipped by default; Task `complexity` as the
model tier — is Droid-specific knowledge. Every other harness runs the
SKILL.md playbook unchanged, which is exactly why this does not belong
in it.

**Decision**: the adaptation lives in `references/droid-modes.md`, the
mission-planning skeleton in `references/mission-brief.md`; SKILL.md
carries only a pointer section. `tools/sync.sh` installs the router +
`extra.txt` bare names to `~/.factory/commands` from a separate,
`~/.factory`-gated block with its own verify pass — the shared
COMMANDS_ROOTS install/verify path is untouched. Task `complexity`
mirrors the briefs' `model:` frontmatter (the D-016 cheap tier maps to
`light`), keeping the tiering signal single-sourced.

**Cost if wrong**: the mode mapping drifts from harness reality — the
subagent read-only clamp and the no-Task-nesting rule are empirical
harness facts; re-verify both on any harness update before trusting
the mapping again. Or the generic command names collide in Droid's
global command root (`~/.factory/commands`) — rename-or-namespace per
D-013's policy, which this extends to the droid root.
