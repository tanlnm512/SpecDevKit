# D-096: a digest line's last key absorbs nothing, and a count is checked against what the digest lists

D-074 made the last key of a line grammar run to the end of the line:
with no next key to end it, free text there held the separator by
design — and so did anything after it. `digest: BLOCK 0 · WARN 0 · NIT
0 · worst none · extra` validated as a clean audit, and an auditor's
`worst`, an architect's `blast radius`, `serial spine` and `ungrounded`
and an analyst's `options` each took every trailing segment silently.
A count was typed and never counted: BLOCK 0 above a listed BLOCK, a
`constitution 3 proposed` above two proposals, and an integrator's
`summary` that disagreed with its own thread blocks all validated.

**Decision** (canonical for the kit; adopted in spec-build D-062 and
spec-ship D-010; amends D-074 §2):

1. **The last key of a line grammar holds no ` · `.** A value still
   ends where the next key begins, so free text inside the line may
   hold the separator; the last key, which has none, may not — refused
   with the key and the value. A block grammar needs no such rule: its
   typed lines are matched whole, so a trailing segment was already
   refused, and its free-text lines are single fields.
2. **A count is read against what the digest lists.** The auditor's
   BLOCK, WARN and NIT against the finding lines beside the line; the
   constitution line's `<n> proposed` against the numbered proposals
   after it; the integrator's `summary:` against the thread blocks it
   counts. The auditor's and the constitution's line alone — the form
   a review record folds and `freeze.py` reads — lists nothing and is
   not checked.
3. **Not checked, and why.** A count whose content the digest does not
   carry — the developer's `files`, the tester's `TCs` and coverage,
   the architect's `statuses`, `tasks` and `TCs owned`, the intent
   line's four counts, the integrator's `changed` — belongs to an
   artifact or a payload the schema never sees. A list is not counted
   either until its document names a delimiter: the architect's
   `milestones <n>: <names>` names none, and the research line's
   `<n> open` names neither the shape of `options` when nothing is
   open.
4. **The research lens names its join.** Its digest line said "one
   line" per open choice inside a one-line digest and named no way to
   write two; the lens was the wrong side — a second choice on a line
   of its own is not on the digest line the parser reads — so
   `protocol/lenses.md` states it: choices joined with `;`, which is
   not the separator.
5. **The brief and the schema are pinned together.** `tests/test_digests.py`
   reads each documented grammar from its brief or lens section, fills
   it, and asserts the schema accepts it — each alternative of each
   alternation — and refuses it with a part dropped, a part added, or
   two swapped; an unmapped metavariable fails the fill by name.

**Consequences**: a line that carries more than its grammar declares is
refused instead of read, and a summary that disagrees with its own
content is malformed. The costs: an auditor whose `worst` holds ` · `
is re-run and told why — free text in a last field now needs another
punctuation; an auditor or constitution reply read as a whole is
refused for listing fewer findings or proposals than it counts, where
the line alone still passes; and a grammar whose count should be
checked against a list needs a documented delimiter first.
