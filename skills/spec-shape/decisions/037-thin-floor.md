# D-037 — The thin floor: a one-file contract tier

- **Context**: every spec — even a one-line bugfix — scaffolded seven
  files and ran the full docset contract; effort tiers shrank agent
  COUNT, never contract SIZE. The default cost of "fix this small
  thing properly" was the same as "build a subsystem", which pushes
  users to skip the kit for small work entirely — the worst outcome a
  spec kit can have.
- **Decision**: spec.md gains a `**Tier**:` header. `tiny` is the
  ONE-FILE contract and the scaffold's default
  (`scaffold.sh [--tier tiny|full]`, default tiny): the task list
  lives in spec.md `## Tasks` (the same checkbox grammar task.md
  uses — one grammar, two homes), an `## Evidence` section carries
  the delivery record, and the graph SKIPPEDs survey/research-already-
  gated/plan/tech/qa/tasks with `tier: tiny` reasons; verify gates on
  a dedicated tiny checker (placeholders, open clarify markers, task
  grammar: bare T### ids, FR/NFR citations, proof-note ticks); tick
  lands inside spec.md (tick.py rewrites it in place); audit's TC/
  burndown/freeze surfaces do not exist at this tier by design.
  Absent or unknown Tier reads `full`: every pre-existing docset keeps
  today's graph byte-for-byte. `migrate.py grow <spec-dir>` promotes
  tiny→full: § Tasks blocks move verbatim into task.md Phase 1 (ids
  never renumbered), authoring docs scaffold from templates, Tier
  flips — structure moves, content re-enters authoring (the fresh
  templates fail check.py by design; nothing is inferred). This
  amends C-01's letter for the tiny tier: one status surface per
  spec, whichever file holds it — never two.
- **Consequences**: small work gets the full discipline (evidence,
  citations, tick proofs, human approve, archive) at one file's cost;
  risk appears → grow, and the docset the standard tier expects
  appears with ids intact. The seven-file contract, check.py's full
  gate, freeze/audit surfaces are unchanged. Serves new eval case
  e7 (tiny tier end-to-end: scaffold→check→graph skips→tick→grow)
  and holds e1/e2 (full tier untouched, no Tier header).
