# D-074: mark.py writes no marker onto a broken ledger chain

D-055 made every verb append its row to `specs/<name>/runs/ledger.jsonl`
inside the lock hold that wrote its marker. Nothing bound the tail a
verb appended to: a row appended by hand, or a field edited in place,
was invisible, and the next verb chained its evidence onto it as if
nothing had happened.

**Decision** (amends D-055 decision 3 — a broken chain is the one
ledger state that does hold a verb back; spec-design's D-093 is
canonical for the chain itself: `prev`, the sha256-12 of the row's
sorted-key JSON without the chain fields, written by `ledger_append`):

1. **Every verb checks the chain before it writes.** claim, land, fail,
   release and drop walk the ledger's rows inside their lock hold,
   first of all; a break — an appended row without its `prev`, a row
   whose `prev` no longer matches the row before it — refuses the verb:
   exit 1, nothing written, the entry's marker unchanged, no row
   appended. The refusal names each problem's line and the way on:
   repair or truncate the ledger, then run the verb again.
2. **The refusal is the refused-transition class.** The ledger is not
   status and the marker is not in question — but a marker whose
   evidence would chain onto an edited tail is not a record this kit
   can stand behind, so the verb stops as any refused transition does.
   Nothing is written on either side.

**Consequences**: a broken ledger surfaces at the next verb instead of
silently accumulating. The costs if this is wrong: repair or truncate
is by hand — the kit offers no ledger editor; the pre-chain rows of a
spec that predates the chain read fine, so only an actually broken tail
refuses; and `--digest`-free flows (a `fail` after a hand-edit of the
ledger) refuse with everything else. Pinned by `tests/test_mark.py`
`RunLedgerTests::test_a_broken_ledger_chain_refuses_the_verbs_nothing_written`.
