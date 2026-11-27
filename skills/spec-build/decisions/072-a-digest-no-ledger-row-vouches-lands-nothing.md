# D-072: land lands only a digest the ledger vouches — and the ledger, not the highest wave directory, names it

D-041 made the digest file the landing's evidence and D-071 put the
sweep under land's lock. What the sweep vouched was still "any file
that parses": one whose request row was missing gained a line of
`none` facts and read exactly like a vouched answer. A file placed by
hand at `digests/wave-9/` outranked everything the ledger had vouched —
`latest_digest` took the highest `wave-N/` directory as the newest —
so a dead run's leftover, or a planted file, was what a landing cited.

**Decision** (amends D-041 decision 2 — the file is the evidence only
when the ledger vouches it; extends spec-build D-071 decision 3 to the
"latest" convention; spec-design's D-092 is canonical for the
classification and the selection, and amends D-086 by reference):

1. **land refuses an unverified digest.** The gate sees the
   `unverified` classification beside `malformed`: exit 1, the file
   named with what is missing, the entry stays claimed. The resume
   view shows it as unverified, the retro folds it as refused, and no
   `--digest` talks over it.
2. **The digest land reads is the one the ledger names.** When the
   ledger vouches a digest for the task — the newest `wave` or `claim`
   row of its stem — that file is the latest, even when a higher
   `wave-N/` directory holds a newer file: the higher file is
   unverified and ignored. When the ledger names none, there is no
   latest: a file alone proves nothing, and the newest such file is the
   unverified refusal land refuses on. A refused file newer than every
   vouched one still holds the task for its own reasons (malformed,
   capability missing, a provenance line no row vouches for) — those
   are answers to real requests, never skipped.

**Consequences**: a landing cites what the orchestrator's own ledger
vouches, however many stray files sit in `digests/`. The costs if this
is wrong: a genuine digest is lost when its run's ledger write failed —
re-emit and re-spawn; and a file tampered after vouching at a higher
wave is refused by the sweep and ignored by the latest — the older
vouched digest governs until the newest is rewritten. Pinned by
`tests/test_mark.py`
`LandProofGateTests::test_a_digest_no_request_row_vouches_refuses_the_landing`
and `tests/test_digests.py`
`SchemaTests::test_a_digest_file_is_valid_malformed_or_absent`.
