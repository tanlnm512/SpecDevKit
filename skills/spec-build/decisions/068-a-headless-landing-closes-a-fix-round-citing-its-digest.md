# D-068: a headless landing closes a fix round citing its digest — `--resolution-from-digest`, and a resolution the close line cannot hold is refused

D-039 decision 4 gives `land` two gates and one more condition: "An
open round needs `--resolution`". D-041 decision 2 sends every task
whose digest reports `implemented` through `mark.py land` at the end of
a headless wave — with no `--resolution`, since there is nobody in the
loop to write what closed the round. So a fix round under `graph.py
--run --runner` always ended CLAIMED: the digest green, the proofs
green, the landing refused with exit 2, and the loop stopped `AWAITING
ORCHESTRATOR` on a task that only needed a sentence someone could have
written (the cost recorded in spec-design's D-087).

**Decision** (amends D-039 decision 4 and D-041 decision 2; mark.py is
canonical, the headless wave's call is graph.py's):

1. **`land --resolution-from-digest` closes an open round with a
   resolution that only points at the evidence.** On an entry with an
   open round the landing composes `headless round <n>: digest <path>
   (<sha12>) reports <status>` — `<path>` the digest file relative to
   the spec dir, `<sha12>` the digest's own content sha, the value the
   landing's ledger row records, `<status>` what the file reports. It
   is a pointer, never a description of the fix: the loop cannot say
   what closed a round, and it does not pretend to. An entry with no
   open round ignores the flag.
2. **The flag needs a digest file.** With an open round and no file on
   record — the `--digest` override is an attestation, not a file —
   `land` refuses, exit 2, naming it: nothing is written. `--resolution`
   and `--resolution-from-digest` together are a usage error, exit 2.
3. **A resolution holding an em dash (U+2014) or a line break is
   refused — exit 2, nothing written.** The round's close sub-line is
   `  - fixed <n> — <resolution> — <proof>`, and the parser
   (`specstate.FIX_NOTE_CLOSED`) splits on the first ` — ` after the
   round number: such a text moves the rest of itself into the proof,
   and the shape gate stays green over a corrupted line. The check sits
   in the CLI, before the lock, the sweep or the proofs.
4. **Nothing else moves.** Without the flag and without
   `--resolution`, `land` on an open round refuses exactly as before.
   The headless wave passes the flag on every landing; a landing it
   holds for any other reason stops the loop as before.

**Consequences**: a fix round that a headless run brought back green
lands, and the close line says which digest closed it. The costs if this
is wrong: the resolution records that a digest reported `implemented`
and a proof ran green — not why the fix worked — so a reader of the
round's history learns what from the digest file and the note, and
nothing from the line itself; a hand-written `--resolution` now refuses
a text that used to land and corrupt the line, so an orchestrator that
quoted an em dash must reword; and the `<sha12>` changes if the digest
file's content is rewritten, so the line cites the file as it stood at
the landing. Pinned by `tests/test_mark.py`
`LandProofGateTests::test_a_headless_landing_closes_the_round_citing_its_digest`
and `::test_a_resolution_the_close_line_cannot_hold_is_refused`, and by
`tests/test_execute_gates.py`
`Gate009HeadlessExecuteTests::test_a_fix_round_lands_from_a_headless_wave`.
