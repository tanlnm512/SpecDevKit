# D-026: No audit gates — verify → approve → execute → tick-commit, one delivery pass

The two audit stops were the pipeline's heaviest human cost and its
widest doc surface: the before-audit (six gates, its own marker line,
its own gate doc, D-023's one-stop session semantics) and the closing
audit (marker line, evidence/closing.md, closing-evidence digest, ack
session, five workflow steps keyed to it). Both existed to batch
judgment around implementation — but the same evidence already lives in
cheaper places: verify runs check.py over the whole docset, approval is
its own explicit human gate, and every tick must carry its own fresh
`done <date> — <proof>` note regardless. Two marker lines, two gate
docs, three audit.py modes, and every doc that had to explain them were
paying rent on a stop the user no longer wanted to make.

**Decision**: (1) The graph loses the `before-audit` and `closing-audit`
nodes: 16 → 14 nodes, `verify → approve → execute → tick-commit`. The
human-gate set is clarify · an undetermined research-gate · approve ·
tick-commit; find_pause, `--launch-check`, `--run`, and both workflow
dialects mirror exactly that. (2) The approval session keeps a one-line
pre-flight (baseline commands green, clean tree, the spec's named
branch, already-done sweep) as prose — no marker, no stop of its own;
constitution is read at approval and rides every implementer payload.
(3) One proof-and-delivery pass replaces the closing audit, at the
tick-commit gate: `audit.py proofs --run` + regression make every tick's
proof note fresh evidence; the review instruments (`scope`, `clean`,
`dod`, and the implementation-diff reviewer from `reviewer-diff.md`,
which `--emit-spawns` now prepares while delivery is pending — base =
the approval freeze's Approved-at SHA, replacing the Before-audit SHA)
gather findings for adjudication — instruments, not gates: no marker,
no evidence/closing.md, no separate ack. Then tick (tick.py), C1, C2.
`/test` = proofs + regression, `/review` = the instruments, `/ship` =
tick + C1/C2 — steps of the ONE pass, never three gates. (4) audit.py
keeps scope/clean/proofs/dod/converge/archived and loses `pre-execute`
and `evidence`; check.py stops enforcing the marker lines;
specstate drops their parsers and gains `approval_sha` (the freeze's
Approved-at anchor). (5) Legacy docsets carrying `Before-audit`/
`Closing-audit` lines are inert under the new graph — the lines are
simply no longer read; no migration is required.

**Consequences**: two fewer human stops per plan; task.md's header
shrinks to the Delivered record; the DoD scorecard (gates/dod.md)
becomes the delivery checklist instead of the closing audit's verdict
table. What is genuinely lost: a recorded, SHA-anchored pre-implementation
audit trail and a durable post-implementation evidence file — the tick
proof notes and the delivery summary now carry that weight, which is
weaker on paper and sufficient in practice for this pipeline's users.
Supersedes D-023 (one-stop gates, pipelined closing pre-check, marker
records) and the audit halves of D-021's hardening.
