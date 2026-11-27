# D-026 — the analyst's tools report is the reply's first line alone, and a reported name holds no separator

- **Context**: D-025 made the intent payload ask for a `tools:` line
  and refuse a digest without a file writer. The reader,
  `tools_report`, took the first `tools:` line anywhere in the text, so
  a reply that opened with prose passed on a line found further down;
  and a reported name was taken as it came, though the provenance sweep
  joins the names onto a ` · `-separated line — a name such as `Write ·
  payload <sha>` would add or split a field on the orchestrator's own
  record. spec-design D-095 closes both.
- **Decision**: adopt spec-design D-095. The report is the line the
  reply opens with — blank lines and an opening code fence aside; a
  `tools:` line anywhere else is text, never a report, so a digest
  whose report stands elsewhere fails the handshake like one that
  carries none: exit 3, a failed spawn. A reported name holding ` · `
  refuses the whole digest as malformed — exit 1 from
  `python3 <skill_dir>/scripts/digests.py validate analyst intent
  --require-tools`, naming the name — a fix and run again, never a
  failed spawn; the sweep validates a digest file before it reads the
  report, so the name reaches no ledger row and no provenance line. A
  line break cannot reach a name: the report is read from one line.
  The intent grammar is unchanged, and `tests/test_digests.py` now
  reads it from `protocol/lenses.md` and asserts the schema accepts it.
- **Consequences**: no count is taken from a digest whose report was
  found in its prose, and an analyst's report cannot shape the
  orchestrator's provenance line. Cost if wrong: an analyst that opens
  its reply with prose before the report is re-spawned as a failed
  spawn, and one that reports a name holding the separator is re-run
  with the problem — the cure for both is in the analyst's reply, and
  for a grammar that is too strict an edit in the spec-design master,
  replicated.
