# D-095: the tools report is the reply's first line alone, and a reported name holds no separator

D-076 asks every spawned role for a tools report and makes a missing
required tool a failed spawn. It says the report is the first line of
the reply — and of the digest file, above the `digest:` line — but the
reader, `tools_report`, took the first `tools:` line it met anywhere in
the text: a reply that opened with prose, or a digest whose body held a
line beginning `tools:`, was read as a report of the same weight. And a
reported name was taken as it came. D-075 renders the names onto the
provenance line the sweep appends — `… · tools-reported <names>` — a
line whose fields are split on ` · `; a name holding the separator
(`Read · payload <sha>`) would add a field to that line or split one,
from the agent's own report.

**Decision** (canonical for the kit; adopted in spec-build D-061,
spec-define D-026, spec-discover D-013, spec-ship D-010 and
spec-release D-008; amends D-076 §2 and D-075's `tools-reported`
field):

1. **The report is the line the reply opens with, alone.** Blank lines
   and an opening code fence do not count as opening it — the validator
   tolerates a fenced digest — and the line's leading markup is
   stripped as everywhere else. A `tools:` line anywhere else is text:
   the grammars keep skipping it, and `tools_report` never reads it, so
   a digest whose report stands elsewhere carries no report and fails
   the handshake like one that carries none.
2. **A reported name holds no ` · `.** `tools_problem` names every such
   name; `validate` returns it as a problem and `parse` returns
   nothing, so the whole digest is malformed — exit 1 through the
   validator, a fix and run again, never exit 3 (the harness is not
   what is wrong). The sweep and `digests_on_file` validate a digest
   file before they read its report, so a forged name never reaches
   `tools_reported`, a ledger row or a provenance line.
3. **A line break is not a case to refuse.** The report is read from
   one line; a break ends it there, and no name can carry one.

**Consequences**: a forged report can no longer shape the orchestrator's
line, and a report found in ordinary text no longer vouches for a
spawn. The costs: a reply that opens with prose before its report is
now a failed spawn — exit 3, or `capability_missing` for a digest file —
where it used to pass; and `tools_report` stays a plain reader, so a
caller that skips the schema still sees the names as written —
`freeze.py` does, with one line and for `tools_missing` alone.
