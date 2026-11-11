# Lens sections (injected into scout payloads by graph.py)

One `## Lens: <name>` section per lens, byte-verbatim into the spawn
payload of the archetype that carries it — here the scout's intent
lens (the survey · research lenses belong to the shape phase's scout).
The section is the lens's contract: input payload, method,
parser-exact formats, digest. The archetype brief carries the spine;
this file carries the specialization.

## Lens: intent (scout → facts and candidate gaps in intent.md)

**Input payload**: the idea (intent.md § Problem, verbatim in the spawn
payload — the session records it before spawning you); the spec dir
path; repo root; the brainstorm handoff path when one exists.

**Ownership**: intent.md is the session's file. You record evidence in
it — the `**Baseline**:` header, § Constraints, and candidate gaps
under § Questions — and never rewrite § Problem, § Audience, or § FR
seeds, never close a question, never ask the user anything. The grill
is the session's.

**Method**:
1. Scope the idea's touched areas from § Problem: the modules, files,
   and concepts the idea names or plainly touches.
2. Survey-lens probing, scoped to those areas only: grep/read (`rg`)
   the codebase for each (see the spine's tool preference); paste
   evidence verbatim. For each area record: what exists, what's
   PARTIAL (the precise missing piece), and the constraints that bind
   the idea (conventions, contracts, couplings the code already pins).
3. Sort every gap: where the repo itself answers "already handled" it
   is a grounded fact — never a question; a genuine judgment call the
   idea leaves open is a candidate gap for the session's grill.
4. Record in intent.md: grounded facts and binding constraints under
   § Constraints (verbatim evidence each); each candidate gap under
   § Questions in the checker's open-marker vocabulary — `[NEEDS
   CLARIFICATION: <the open question>]` — so the marker scan reads it;
   the `**Baseline**:` header, version @ the commit the facts were
   probed at (survey.md's header shape).

**Exit**: run `check.py <spec-dir> --intent-only` and fix every FAIL
on your own writes (the baseline, a line you wrote). It will not exit
0 and must not: open-marker FAILs remain by design — each is a
question only the user closes — and so does any FAIL on a section the
session has not written yet. Count both in the digest.

**Digest**: `digest: intent grounded <n> facts · markers <n> open ·
session FAILs <n> · unknowns <n>`

**Guardrails**: facts are never asked of the user — anything the repo
can answer is probed and recorded as a fact; no docset authoring —
intent.md is the only file this lens ever writes into.
