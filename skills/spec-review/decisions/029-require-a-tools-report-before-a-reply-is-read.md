# D-029: Every reply opens with a tools report, and a reply without Read is a failed spawn

Every agent the oracle asks — the scout, the lens reviewers, the
triage editor, the judges, the fixer, the final assessor — opens its
reply with `tools: <the tools it actually holds, comma-separated>`:
the ask's first line asks for it, the rule is stated once in
`protocol/panel-protocol.md` § Your reply opens with your tools and in
the two judge briefs, and the session reads that line before anything
else in the reply. A reply whose line lacks Read is refused whole: it
is a failed spawn — the spawn could not read the code — never a
finding, never a fix round, and the ask is spawned again on a type or
harness that holds Read. Nothing else is required. A reply handed to
`findings-parse` whole is read for its findings alone: the oracle
skips the leading report, which is never a finding.

**Why**: under omp a spawned subagent's reachable surface is narrower
than its frontmatter (HARNESS-FACTS.md), and a reader that cannot open
a file reports a clean diff — an empty findings list is the expected
answer for clean code, so nothing downstream can tell it from a reader
that saw nothing. The report is the agent's own claim, and it is read
before its verdict.

**Cost if wrong**: a reader that held Read under another name is
asked again — one wasted turn — and every reply is one line longer.
No script in this skill reads the line; whether a spawned agent can
see and name its own tools at all stays an open assumption in
HARNESS-FACTS.md.
