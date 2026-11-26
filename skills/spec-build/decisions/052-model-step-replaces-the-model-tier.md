# D-052: a model's strength is a model step — `tier` is the contract tier alone

`tier` carried two meanings through this skill's documents. `Tier:
tiny | full` on spec.md names the contract's shape, and the fix-round
text said rounds 1–3 "run at your capability tier" and round 4 goes
"one tier up" — a model's strength. An executing model that reads
"at Tier: tiny … at the same capability tier … a stronger tier" in one
section has to guess which ladder each sentence climbs, and the
guess misroutes a fix round: the contract tier cannot be stepped up
by a re-spawn, and a model step is not `migrate.py grow`.

**Decision**:

1. **`tier` means the contract tier only** — `**Tier**: tiny | full`
   (D-037) — in every instruction, brief, message and document this
   skill ships. The `**Effort**` header's value stays the "effort
   tier", always written with its qualifier.
2. **A model's strength is a `model step`.** "One model step up"
   names the round-4 escalation: a model stronger than the one the
   brief's `model:` line pins (D-051). The kit names no model id; each
   harness dialect maps the brief's model its own way.
3. **Where it changed**: `rules/agent-limits.md`'s fix-round budget
   (and so both carriers), this SKILL.md's § Fix rounds and the
   typed-deviation sentence, `mark.py`'s module docstring and its
   round-4 and same-signature lines, and the same-signature text in the
   engine (spec-design D-070 records that side).

**Consequences**: one word, one ladder. An agent reading a fix-round
instruction now knows whether it is being told the contract grew or
the model should; `mark.py fail` printing `spawn one model step up`
names the thing the orchestrator must actually change. Decision
records and changelogs written before this keep the old words — they
are history. The cost if wrong is only a reader's habit: nothing in
the engine keys on either word.
