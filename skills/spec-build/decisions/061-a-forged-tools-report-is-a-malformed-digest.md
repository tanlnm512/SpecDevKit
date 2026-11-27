# D-061: a developer's tools report is the file's first line and holds no separator — a forged one is a malformed digest

D-055 made the provenance line the sweep appends carry a digest's
`tools:` report as `tools-reported`, and D-056 made a report that lacks
a required tool a failed spawn. Neither asked where the report was read
from or what a name could hold: `tools_report` took the first `tools:`
line anywhere in the file, and a name such as `Write · payload <sha>`
went onto the line the orchestrator writes — a line whose fields are
split on ` · `.

**Decision** (the report reader and its refusal are canonical in
spec-design D-095; adopted here in the same words — this skill's half
is what `land` and the sweep do with it; amends D-055 §4 and D-056 §2):

1. **A file whose report holds the separator is a malformed digest.**
   `specstate.latest_digest` reads the file through the schema, and the
   schema refuses the report naming the name, so `land` refuses with
   D-054's `refused: malformed digest at <path> — tools report refused:
   `<name>` … — fix and run again`: nothing is written, no
   `capability_missing` row is appended, and no provenance line or
   ledger row carries the name.
2. **A report that is not the file's first line is no report.** The
   file then fails the handshake like one that carries none: D-056's
   refusal — the task stays claimed, `mark.py release` and spawn again.
3. **The file's shape is unchanged**: `tools: <the tools you actually
   hold, comma-separated>` above the `digest:` line, the first line of
   the file.

**Consequences**: what a developer reports can no longer add or split a
field on the orchestrator's line. The cost if this is wrong: a file
that opened with the report on a later line lands nothing until it is
rewritten with the report first — the spawn re-runs, as D-056 already
asks of a file written before it.
