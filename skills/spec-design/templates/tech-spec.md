# Tech Spec: <name>

**Spec**: [spec.md](spec.md) | **Created**: YYYY-MM-DD
**Baseline**: <version @ commit>
**Every file/symbol citation below must come verbatim from § Code state
or a grep run in this session — never from memory.**

## Code state
<!-- The grounding: one item per spec requirement — where the code stands
today. Evidence pasted verbatim from grep/read output in the session that
wrote it; can't find it → `unknown — verify`, never a guess. Status
derives from evidence, never intent: run every verify command. The
Baseline above is the HEAD this section was grounded against. -->
```
item <id>: "<one-line description>"
  evidence:   <file:symbol with line — copied verbatim from grep/read output>
  status:     DONE | PARTIAL | TODO
  verify:     <the exact command that proves the status>
  gap:        <if PARTIAL/TODO: the precise missing piece>
```

### Supporting evidence
<Load-bearing symbols/counts the sections below cite: machinery,
couplings, consumer lists, counts. Same verbatim rule.>

## Architecture
<Components and data flow for this feature — a mermaid diagram plus one
paragraph. Show how it sits in the existing system (grounded in § Code
state).>

## Solution
### Chosen approach
<What we're building and why this shape. Map FR-### coverage. Informed by
§ Questions & options when it holds real findings.>

### Alternatives rejected
| Alternative | Why rejected |
|-------------|--------------|
| <...>       | <one line>   |

## Questions & options
<!-- The research gate's artifact (one owner end to end — there is no
     separate research.md). Ships pre-filled with the resolved skip form:
     the gate's common case. When the spec has real open questions, the
     orchestrator replaces this form — one block per question in the
     Questions subsection, every claim carrying **source** (URL/DOI) ·
     retrieval date · one-sentence claim · relevance · confidence — and
     the credible candidates with one-line trade-offs in the Options
     summary subsection (no recommendation — choosing is § Solution's
     job with this data). -->
### Questions
not applicable — no open questions at Stage 0

### Options summary
None — <why>

## Impact analysis
<!-- Blast radius: what existing code/symbols this touches, who calls them,
what breaks if the approach is wrong. Use the workspace's graph /
code-intelligence tool when one is available, else grep. Ground every
claim in § Code state evidence. -->

## Interfaces & data
<!-- What callers and stored data see change: API shapes (endpoints,
signatures, CLI flags, events, file formats), data-model changes,
migrations, and compatibility. Required — write `none — <reason>` when
nothing of the kind changes. A user-facing UI (an applicable
Accessibility NFR) adds a `### UX` subsection: flows, every state
(empty, error, loading), accessibility notes. -->
- **Interfaces**: <changed surfaces and their shapes>
- **Data and migrations**: <model changes and migration order>
- **Compatibility**: <who breaks and how they move>

## Quality, threats, and rollback
<!-- Map every applicable NFR-### to a concrete design consequence. A
security-relevant trigger — auth, secrets, untrusted input, persistence
of personal data, migration, privileged operation — needs a threat row
(asset, threat, mitigation, residual risk) and a rollback or recovery
strategy: the contract review BLOCKs a trigger with none. -->
| Requirement | Design consequence / threat mitigation | Rollback or verification |
|-------------|----------------------------------------|--------------------------|
| NFR-###     | <...>                                  | <...>                    |

## Code guide
<!-- Per area: where work lands, verified to exist in § Code state. -->
### <Area 1>
- Touches: `the \`symbol\` function in <file>` (§ Code state evidence)
- Approach: <...>
- Verify before implementing: `<exact command>`
- Pitfalls: <known traps, from § Code state or history>

### <Area 2>
...

## References
<Docs, issues, benchmarks, prior art, related specs — each with URL/path
and one line on why it matters. External grounding found while answering
§ Questions & options lives there, not here.>

## Decisions
<!-- ADR-lite. Append-only: decisions made during implementation land here too. -->
### D-001: <decision>
- **Context**: <why this needed deciding>
- **Decision**: <what was chosen>
- **Consequences**: <what this commits us to / rules out>
