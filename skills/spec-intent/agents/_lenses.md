# Lens sections (injected into scout payloads by graph.py)

One `## Lens: <name>` section per lens, byte-verbatim into the spawn
payload of the archetype that carries it — here the scout's intent
lens (the survey · research lenses belong to the shape phase's scout).
The section is the lens's contract: input payload, method,
parser-exact formats, digest. The archetype brief carries the spine;
this file carries the specialization (D-036).

## Lens: intent (scout → intent.md)

**Input payload**: the idea (the requirement list from the spawn
payload, verbatim); the spec dir path; repo root; the
`<skill_dir>/templates/intent.md` path — the template you fill.

**Method**:
1. Scope the idea's touched areas from its requirement list: the
   modules, files, and concepts the idea names or plainly touches.
2. Survey-lens probing, scoped to those areas only: grep/read (`rg`)
   the codebase for each (see the spine's tool preference); paste
   evidence verbatim. For each area record: what exists, what's
   PARTIAL (the precise missing piece), and the constraints that bind
   the idea (conventions, contracts, couplings the code already pins).
3. Derive the grilling questions from the gaps found: every place the
   repo itself answers "already handled" closes as a grounded fact —
   never a question; every genuine judgment call the idea leaves open
   becomes a question per `references/grilling.md` (design tree,
   frontier, batched rounds). Record open questions in intent.md in
   the checker's existing open-marker vocabulary — `[NEEDS
   CLARIFICATION: <the open question>]` — so the marker scan reads
   them; each closes only when the user answers it.
4. Write intent.md from the template: the grounded facts (verbatim
   evidence each), the open questions in marker form, the constraints;
   the `**Baseline**: <version @ commit>` header records the commit
   the facts were probed at (survey.md's header shape — the staleness
   diagnosis reads it unchanged).

**Digest**: `digest: intent grounded <n> facts · questions <n> open ·
unknowns <n>`

**Guardrails**: facts are never asked of the user — anything the repo
can answer is probed and recorded as a fact; no docset authoring —
intent.md is the only artifact this lens ever writes.
