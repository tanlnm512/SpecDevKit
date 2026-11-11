# D-019: A clarify round rides the harness's structured question tool where one exists

The grilling round's ask channel is now conditional, not
plain-text-only. Where the harness offers a structured question tool
(an option-picker ask), the round goes through it: each question
becomes one ask — its 2–3 viable options the choices, the ➡️
recommended answer first and marked; where the tool caps questions
per call, the round splits across consecutive calls and never
truncates the frontier. With no such tool — and on any non-answer —
the printed ❓ round is the form: grilling.md's block stays
verbatim-valid, and D-018's hard stop fires exactly as before (a
tool call the harness resolves without waiting is the case D-018
was written from). SKILL.md §3 and the router command name the
channel; grilling.md pins the rules.

**Why**: an audit of every user-choice surface in the kit found
options rendered as plain text throughout — the round's 2–3 viable
options included — making the user retype what the harness can
render as tappable choices with the recommendation marked. The
picker channel is a conditional clause, not a per-harness dialect:
it names no harness, so the kit's one-shape-for-every-harness rule
(the dialect retirement, D-035) stays honored, and the ❓ block
remains the one fallback and transcript every path shares — the
run still resumes from printed doc state.

**What's preserved, not overridden**: D-018 entire — the HUMAN
gate, the verbatim-print-and-stop on non-answer, the tri-state
closure rule, the empty-frontier termination. Free-text answers
(the tool's Other, or a typed reply outside the tool) ride the
same gate, and "yes accepts the ➡️" stays the wording discipline
because the printed fallback still needs it.

**Cost if wrong**: a picker that renders badly or silently drops a
question could hide frontier items — mitigated by
split-never-truncate and by the verbatim print the non-answer rule
already mandates. Prose-only change: nothing in `check.py` /
`graph.py` gates on the channel, and no eval case changes (I2 pins
the surviving-marker refusal, not the ask's medium).
