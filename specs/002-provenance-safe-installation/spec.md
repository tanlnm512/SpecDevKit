# Spec: provenance-safe-installation

**Status**: done
**Created**: 2026-09-21
**Branch**: `fix/provenance-safe-installation`

## What
Make every installation and generated-agent deployment refuse unowned files,
stage changes before applying them, and update provenance atomically across all
supported harness roots.

## Why
The skill-tree sweep currently ignores same-path collisions before rsync, and
the optional-harness generator deletes all files sharing a role prefix. Both
behaviors can overwrite or remove user-owned configuration while reporting a
successful sync.

## Business value
Users can install, update, inspect, and remove SpecDevKit without risking other
skills, commands, agents, or locally customized files. Failed preflight leaves
every destination byte-identical.

## User stories
### US1 — Refuse foreign collisions (P1)
As a user with existing harness configuration, I want ownership proven before
any write or delete, so that installation cannot destroy my work.

**Acceptance criteria**:
- AC1: Given a same-path unledgered file, When sync runs, Then it is retained
  byte-for-byte and the install exits nonzero before modifying any root.
- AC2: Given an unrelated same-prefix agent file, When definitions regenerate,
  Then that file remains untouched.

### US2 — Apply validated changes atomically (P1)
As a maintainer, I want a complete install plan before mutation, so that a late
collision cannot leave earlier harness roots partially updated.

**Acceptance criteria**:
- AC3: Given any preflight failure, When sync exits, Then no content or ledger
  changed in any destination.
- AC4: Given every planned file is owned or absent, When sync runs twice, Then
  both installed content and ledgers are identical.

### US3 — Support literal filesystem paths (P2)
As a user, I want workflow baking to preserve unusual path characters, so that
installation works from valid directories containing spaces or metacharacters.

**Acceptance criteria**:
- AC5: Given a skill path containing spaces, ampersands, quotes, backslashes,
  or dollar syntax, When workflows bake, Then the exact path is represented as
  a valid language string.

## Requirements
- **FR-001**: BEFORE writing, the installer shall validate all sources,
  required tools, destinations, collisions, generated content, and ledgers.
- **FR-002**: IF any foreign collision or prerequisite failure exists, the installer shall exit nonzero without modifying any destination or ledger.
- **FR-003**: The system shall treat a destination as owned only when its
  relative path and current hash match its provenance ledger entry.
- **FR-004**: WHEN a same-path destination is foreign, the system shall refuse
  replacement before rsync, copy, generation, or removal.
- **FR-005**: WHEN a shipped file becomes stale, the system shall delete it
  only if its current hash still matches its ledgered deployed hash.
- **FR-006**: The agent-definition generator shall stage output and shall not
  use a role-name prefix as deletion authority.
- **FR-007**: WHEN applying a validated plan, the system shall use destination-
  local temporary files and atomic replacement for content and ledgers.
- **FR-008**: The workflow installer shall encode the resolved skill path with
  language-aware string generation rather than raw sed replacement.
- **FR-009**: `--dry-run` and `--check` shall report create, update, delete,
  refuse, and drift decisions without claiming ownership or writing files.

## Scope
**In**: skill trees, commands, Claude/OMP/opencode/Droid/agy definitions,
workflow files, ledgers, staging, preflight, dry-run/check, and installer tests.

**Out (deferred)**: workflow lifecycle semantics, archive behavior, CI release
policy, and redesign of harness destination layouts.

## Assumptions & risks
- Assumption: `.spec-dev-kit-deployed` remains the ledger filename.
- Risk: identical unledgered files surprise existing users — mitigation:
  report an explicit adoption command later; never silently claim ownership.
- Risk: shell staging is difficult to make cross-root atomic — mitigation:
  preflight all roots, then use per-file atomic replacements with rollback data.
