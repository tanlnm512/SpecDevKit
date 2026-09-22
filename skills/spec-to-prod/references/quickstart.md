# Quickstart

This is navigation, not a second contract. `SKILL.md`,
`contracts/docset.md`, and the role briefs remain canonical.

## Choose a tier

| Tier | Use when | Shape |
|---|---|---|
| Tiny | ≤1 requirement, ≤2 files, no unknowns, no migration/API break | Same seven artifacts and gates; inline authoring/execution; no research or parallel spawn |
| Standard | Small/medium feature or bugfix | Shallow artifacts; spawn only where independent depth pays |
| Large / high-risk | Multi-area, external input, auth, persistence, migration, security/privacy/performance NFR | Full waves, contract reviewer, implementation-diff reviewer, release handoff |

## Minimum safe path

1. `scripts/scaffold.sh <name>`
2. Fill `spec.md` with the user; triage every NFR family.
3. Resolve the research gate; run or skip explicitly.
4. Produce survey, plan, tech-spec, test, tasks.
5. `python3 scripts/check.py specs/<name>`
6. Run before-audit; record its SHA.
7. Get explicit user approval; run `scripts/freeze.py specs/<name> --record`.
8. Execute the task frontier; append D-### rulings only.
9. Closing audit: evidence, scope, hygiene, implementation review, proofs, regression, DoD.
10. Record `evidence/closing.md`; tick once; commit C1, then delivery-record C2.

## One-command state

```bash
python3 skills/spec-to-prod/scripts/graph.py specs/<name>
```

If unsure what to do next, run this and follow the printed frontier or human
gate. Do not trust remembered state.
