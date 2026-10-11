---
description: One-release compatibility router — the retired monolithic /spec-to-prod verb surface as a thin forwarding table to the split successors (/spec-intent, /spec-shape, /spec-execute); retires after one release
argument-hint: <verb> <spec-name> [args…]
skills: spec-shape
---

The monolithic router retired with the split (FR-009); this alias
retires after one release (FR-010). Route $ARGUMENTS by verb:

| Verbs | Route to |
|-------|----------|
| scaffold, intake, idea | /spec-intent |
| authoring, plan, tech, qa, tasks, spec-shaping | /spec-shape |
| execute, build, test, review, ship, continue | /spec-execute |
