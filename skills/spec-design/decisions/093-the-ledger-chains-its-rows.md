# D-093: the ledger chains its rows — tampering is detected, not prevented

D-075 made `runs/ledger.jsonl` append-only repo evidence, but nothing
about a line bound it to the line before it: a row appended by hand, or
a field edited in place, read exactly like a row the orchestrator
wrote. The ledger is not status, so no workflow decision rode on it —
but every provenance line, budget count and retro table is folded from
it, and none of them could tell evidence from a quiet edit.

**Decision** (amends D-055/D-075 decision 1's row shape, which carried
no chain; spec-build's D-074 carries the verb side; the landing record
of D-090 is not part of this — only the run ledger chains):

1. **Each row carries `prev` — the content hash of the row before it.**
   The hash is sha256-12 of the row's sorted-key JSON without the chain
   fields (`prev`, `chain`), taken at append time from the ledger's
   last line by `ledger_append` itself, so every writer — verbs, the
   sweep, `ledger_event` — chains without remembering to. The first row
   of an empty ledger carries `prev: null`.
2. **A reader can name every break.** `ledger_chain_problems` walks the
   lines and reports `line <n>: …` for a row appended without its
   `prev` (a hand-appended row after a chained one) and for a row whose
   `prev` no longer matches the row before it (a field edited in
   place). Rows before the first chained one are a pre-chain ledger and
   read fine; `ledger_rows` keeps working, rows just carry `prev: null`.
3. **This detects, it cannot prevent.** A ledger rewritten whole chains
   consistently; the chain makes quiet appends and in-place edits
   visible, not tampering impossible. The record stays evidence, never
   status.
4. **The readers that act on it refuse a broken chain.** `mark.py`'s
   verbs — claim, land, fail, release, drop — check the chain inside
   their lock hold, before anything is written, and refuse (exit 1,
   nothing written) while it is broken: nothing appends onto a tail
   that no longer chains. `graph.py`'s report prints a `run ledger:`
   tamper line naming each problem; the headless run inherits the bite
   through its own claim. The sweep keeps writing evidence — the chain
   never holds provenance back — and `budget_spent`/`budget_stop` read
   as before.

**Consequences**: a quiet append or edit is named at the next verb and
in every report. The costs if this is wrong: a broken chain stops every
verb until the ledger is repaired or truncated — evidence now does hold
markers back, the one place D-055 decision 3's "never holds the
workflow back" gives way; the sweep appends onto a broken tail, so the
break stays visible rather than healed; and a removed `prev` on a
chained row demotes it to legacy, the one edit the chain cannot see.
Pinned by `tests/test_specstate.py` `LedgerChainTests` and
`tests/test_mark.py`
`RunLedgerTests::test_a_broken_ledger_chain_refuses_the_verbs_nothing_written`,
`tests/test_graph.py`
`RunLedgerTests::test_the_report_names_a_broken_ledger_chain`.
