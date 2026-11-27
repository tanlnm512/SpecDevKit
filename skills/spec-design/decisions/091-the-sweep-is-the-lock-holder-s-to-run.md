# D-091: the sweep runs under the reader's lock — a skipped sweep is a refusal, never a warning

D-075 decision 3 sweeps at the start of every invocation and D-086
decision 3 again at every wave boundary; `mark.py land` swept once more
before its own gate. That last sweep ran outside the lock the gate
reads under, and a held lock inside it was swallowed into a warning —
so under contention the sweep was skipped and the landing went on to
judge whatever was on disk.

**Decision** (amends D-075 decision 3's lock discipline and D-086
decision 2's reader shape; spec-build's D-071 carries the verb side):

1. **A caller holding the spec's task lock sweeps without taking it.**
   `sweep_digests` grows a locked form; `mark.py land` sweeps inside
   its lock hold, after acquiring and before judging. The digest state
   a gate reads is always the state its own sweep left.
2. **A digest no ledger row records is refused at the source.** The
   sweep vouches a file only where the ledger records the request — the
   `wave` row of its wave and stem, or the `claim` row that claimed the
   task there. A parse-valid file neither carries gains no provenance
   line: recorded `digest_malformed`, outcome `unverified`, once per
   content, named. D-075's `none`-facts line for a request-less digest
   is gone: nothing vouches it, so nothing renders it.
3. **Every reader of that refusal names it the same way.**
   `digest_refusal_line` renders the state word — `unverified at <path>`
   beside `malformed at <path>` — so the sweep's stderr, a held node's
   reason, and a landing's refusal are one line.

**Consequences**: a request-less digest is loud at every boundary
instead of silently vouched. The costs if this is wrong: a spec whose
run's ledger write failed names its digests unverified at every
boundary until it is re-emitted — the ledger warning is the trace; and
an analyst run reading another spec's digests/ tree records nothing —
rows are written under the file's own spec's lock only. Pinned by
`tests/test_specstate.py`
`DigestVouchTests::test_a_digest_no_row_records_is_unverified` and
`tests/test_execute_gates.py`
`Gate011RunLedgerTests::test_a_hand_written_digest_is_swept_before_every_read`.
