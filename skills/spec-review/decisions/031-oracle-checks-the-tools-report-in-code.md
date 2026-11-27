# D-031: the oracle checks the tools report in code, against the role's whole brief line

Amends D-029. D-029 made every reply open with a tools report and
called a reply without Read a failed spawn, but the check was prose the
session was asked to run. The one script that touched the line,
`findings-parse`, stripped it unchecked: a reply opening `tools:` or
`tools: Grep` was parsed into findings like any other, and a reply with
no line at all could not be told from a saved report. No path read the
report of any role that returns no findings — the scout, the triage
editor, the judges, the final assessor, the fixer — so "nothing else is
required" was, in code, "nothing is required". D-029's own cost-if-wrong
said so: "No script in this skill reads the line."

**Decision**:

1. **The brief is the table.** A role's required tools are every tool
   on its own brief's `tools:` line — the frontmatter's, never
   `disallowedTools:` and never a mention in the body — read from
   `agents/` at call time and copied nowhere: Read, Grep and Glob for
   each of the six readers; Read, Grep, Glob, Bash, Write and Edit for
   the fixer. A brief edited moves the check with it
   (`test_the_brief_is_the_table`). A brief that is missing, unreadable
   or without a `tools:` line refuses the check; it never requires
   nothing. This widens D-029's "nothing else is required": a reader
   with Read and no Grep cannot follow a call site, and still reports
   the empty list that reads as a clean diff.
2. **A required tool is met by any name a kit def dialect maps it to**,
   whatever its case — the aliases the digest schema knows
   (`TOOL_ALIASES` in spec-design's `digests.py`: Write is Create or
   ApplyPatch, Bash is Execute). spec-review ships alone and carries no
   `digests.py`, so the oracle carries the table;
   `tools/tests/test_review_handshake.py` pins it equal to the
   master's.
3. **Two paths read a reply, and both refuse the same way.**
   `handshake --role ROLE (--file PATH | --text STR)` is the gate every
   reply passes: it returns `tools` (the names the role reported, as it
   spelled them) and `reply` (the text past its tools line) and nothing
   else. `findings-parse --role ROLE` is that gate ahead of the parse.
   ROLE names the brief the spawn ran on, without its `spec-review-`
   prefix — a stage seated on a brief names that brief: the triage
   editor, the cross-lens pass and the two assessors run on `quality`,
   the fast-mode general reviewer and the fresh-eyes fix reviewer on the
   lens type the session picked. A report short of a tool, or a reply
   that opens with none, is `status: error` naming stage `handshake`,
   the role, what it reported and the tools missing, exit 1 — one
   refusal line from either path, carrying no findings and no reply.
4. **A reply is never read for its findings alone, and the caller says
   which of the two it hands over.** D-029's last sentence is withdrawn.
   A findings list and a `fix_from` payload are one shape, so
   `findings-parse` cannot tell a reply with no tools report from a
   saved report, and it does not guess: the caller declares the payload.
   `--role ROLE` is a role's reply and runs the gate; `--saved-report`
   is the `fix_from` input — the previous report's markdown or its
   findings JSON — which never opens with a tools report. Handed
   neither, the call is refused naming both
   (`test_an_undeclared_payload_is_refused_naming_both_kinds`); handed
   `--saved-report` and opening with a tools report, it is refused as a
   reply and told to name the role. A Read-only fallback was not kept:
   it would be D-029's gap under a new name.
5. **It is a failed call, and counts as nothing.** The refusal writes
   no stage file and no telemetry row, and the oracle holds no round or
   attempt to advance — D-025 keeps that count with the driving
   session, and this decision adds none (`test_a_refused_reply_advances_no_stage`:
   after a refusal the run folder is as it was and `run-resume` still
   names the same next stage). The session runs the same stage again
   under the failed-call bound, on a type or harness that holds the
   tools. `rounds_used` and the fixer's `round` are counts the session
   supplies, and a refused reply never becomes a completed stage to
   count.
6. **The records follow, in the same change.** SKILL.md § Run sequence
   states the ask and the calls. `contracts/run-sequence.md` carries
   the tools-report row, the declared `fix_from` call and the `--role`
   of each role, and names a refused report a failed call.
   `protocol/panel-protocol.md` § Your reply opens with your tools and
   the confirmer and verifier briefs require the brief's whole line.
   `observations/rule-ledger.md` holds the rule as machinery;
   `GLOSSARY.md` and `HARNESS-FACTS.md` name this skill's form of the
   handshake. The briefs' `tools:` lines are unchanged: they already
   said what this decision requires. `run-save` and `report` take JSON
   the session composed; a reply still carrying its tools line fails
   their JSON parse, so neither reads a report and neither gains a
   check.

**Consequences**: a spawn that could not see a tool is refused before
anything it returned is read, on every role and by the same test on
every harness — the agent's claim is now read by a script, not by a
session that may skip the line. Every role's reply costs one more
oracle call. `findings-parse` takes a declaration on every call — a
reviewer's reply names its role, the `fix_from` input says
`--saved-report` — so the gate can no longer be skipped by leaving a
flag off. What no reading of the text can catch is a false declaration:
a reply that opens with no tools report, handed over as
`--saved-report`, has the shape of the input that flag names. That is a
misstatement by the caller, where before it was an omission. The cost
if wrong: a role whose harness names a tool this kit does not know is
refused as short — the cure is an alias in `TOOL_ALIASES` here and in
the spec-design master, which the pinning test keeps one edit. The
handshake trusts the line as every kit handshake does: it catches a
spawn that cannot see a tool, not one that sees it and uses it badly,
and whether a spawned agent can name its own tools at all stays the
open assumption in `HARNESS-FACTS.md`.
