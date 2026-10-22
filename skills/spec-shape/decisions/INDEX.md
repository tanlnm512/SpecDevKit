# Decision index — spec-shape

ADRs are append-only. The split reused four numbers, so a bare
`D-002`, `D-003`, `D-005`, or `D-006` is ambiguous — cite the file.

| ID | File | Era |
|----|------|-----|
| D-002 | `002-state-in-docs.md` | monolith — state lives in docs |
| D-002 | `002-retirement-of-spec-to-prod.md` | split — the move map |
| D-003 | `003-researcher-gate.md` | monolith — conditional researcher |
| D-003 | `003-intent-node-and-spans.md` | split — intent node, phase spans |
| D-005 | `005-thin-pointer-defs.md` | monolith — thin agent defs |
| D-005 | `005-telemetry-naming.md` | split — derived telemetry name |
| D-006 | `006-parallel-by-default.md` | monolith — parallel waves |
| D-006 | `006-command-rename-spec-gen-alias-removal.md` | split — `/spec-gen` rename |

New decisions continue from the highest number (D-044 is the latest).
