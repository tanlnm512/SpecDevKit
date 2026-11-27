# D-013: the panelist's tools report is the reply's first line alone, and a reported name holds no separator

D-012 made the panelist open its reply with a tools report and refuse a
digest without Read. The reader, `tools_report`, took the first
`tools:` line anywhere in the text — a reply that opened with prose
passed on a line found further down, inside the digest — and a reported
name was taken as it came, though the kit joins reported names onto a
` · `-separated provenance line wherever one is written. spec-design
D-095 closes both.

**Decision**:

1. **The report is the line the reply opens with** — blank lines and
   an opening code fence aside. A `tools:` line anywhere else is text,
   never a report: the grammar skips it and the session reads no
   report, so the digest fails the handshake like one that carries
   none — exit 3 from `python3 <skill_dir>/scripts/digests.py validate
   panelist <lens> --require-tools`, a failed spawn.
2. **A reported name holding ` · ` refuses the whole digest as
   malformed**: exit 1 with the name — a fix and run again, handed back
   to the same panelist, never a failed spawn. A line break cannot
   reach a name: the report is read from one line.
3. **The lens sections and the schema are pinned together.**
   `tests/test_digests.py` builds each lens's digest from the fields
   its `### Output` names in `protocol/lenses.md`, in their order and
   within the `points:` line count the section states, checks them
   against the field table `contracts/run.md` pins, and asserts the
   schema accepts each lens and refuses a field dropped, a field
   renamed, a point count outside the stated range, and a second line
   under a one-line field.

**Consequences**: no panel digest is read on a report found in its own
prose, and no panelist's report can shape an orchestrator's line. The
cost if this is wrong: a panelist that opens with prose before its
report is re-spawned as a failed spawn — a read-only re-run — and one
that reports a name holding the separator is re-run with the problem.
