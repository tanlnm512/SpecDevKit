# D-050: An approval is its records; payloads carry what their reader can use

A review of the shaped suite found the approve gate and several spawn
payloads promising more than the engine enforced:

- `check.py` verified the approval freeze only when task.md carried
  `**Lifecycle**: v2`, and graph.py read approve DONE on the Status
  word alone — a hand-flipped `Status: approved` passed the check and
  opened `--span execute`.
- The contract review left no record, and nothing said who resolves a
  BLOCK the orchestrator does not repair.
- Payloads addressed the wrong reader: the reviewer (no shell) was told
  to run git; a tiny-tier review was told to read five files that do
  not exist; the intent scout got spec.md's requirement list in place
  of the idea; `--repair NODE` emitted the whole frontier wave.
- The intent gate went red when intent.md itself was committed, passed
  a title-and-baseline stub, and passed an invented baseline sha.

**Decision**:

1. **The freeze is the approval.** At full tier a Status of approved,
   active, or done without `approvals/approval.md` fails `check.py`,
   and the approve node is BLOCKED — the `**Lifecycle**` header no
   longer gates this. Tiny tier keeps its one-file contract (no
   freeze). Docsets approved before the freeze existed are re-approved
   once.
2. **The contract review is recorded, by the orchestrator.** The
   reviewer stays write-free; the orchestrator persists its findings
   digest, one ruling per BLOCK, and the payload's `Docset
   fingerprint` to `approvals/review.md`. A BLOCK is repaired (then
   re-reviewed once) or ruled by the user — never by the orchestrator.
   `freeze.py --record` refuses a full-tier docset whose review.md is
   absent or names another fingerprint, so a repair after the review
   forces the re-review mechanically. The fingerprint hashes the
   frozen manifest plus task.md.
3. **`--repair NODE` emits that node alone**, in or out of the
   frontier, and is a usage error when the package ships no brief or
   lens for the node. `research` and `approve` are repairable: the
   researcher payload for a `run` decision, the contract review for a
   re-approval.
4. **The research gate is the orchestrator's**: `--run` pauses
   `AWAITING ORCHESTRATOR: research-gate`; `AWAITING HUMAN` is
   reserved for the user's gates.
5. **A span handoff means its gate is behind it.** `span drained — …
   handoff` prints only when intent is green (intent span) or approve
   is done (shape span). A shape span with no spec prints `AWAITING …
   route to /spec-intake` (exit 0); one held on blocked nodes prints
   `span held` and exits 1. The print runner stops after one emitted
   wave and each payload line names its agent type.
6. **Payloads fit their reader.** The implementation review's diff is
   written beside its payload (`reviewer-diff.patch`: `git diff
   <approval base>` under a header listing untracked files); the
   contract review payload is tier-aware; the intent scout's payload
   carries intent.md § Problem.
7. **intent.md is the session's; the scout adds evidence to it.** The
   scout records the baseline, grounded constraints, and candidate
   gaps as open markers, and exits with open-marker FAILs standing —
   only the user closes a question. The session owns the grill and the
   green gate.
8. **The intent gate checks substance and code staleness.**
   `--intent-only` requires non-empty Problem, Audience, Constraints,
   and FR seeds sections with ≥1 FR seed, fails a baseline sha the
   repo cannot resolve, and reads stale only when a path outside the
   specs tree changed since the baseline. intent.md's Status field is
   dropped: the green gate is the validation.

**Consequences**: flipping Status no longer admits execution; every
approval leaves two files (review.md, approval.md). Test fixtures that
approve a docset record both. Re-approval needs a fresh review
(`--emit-spawns --repair approve`). The `**Lifecycle**: v2` header in
the task template is inert for check.py. Survey-baseline staleness
(a WARN) still compares sha to HEAD.
