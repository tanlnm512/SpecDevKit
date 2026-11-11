# D-055: doc trees, re-delivery, and the shapes of the gate records

A review of the engine against the documented path (discover → define
→ commit → design → build → merge) found gates that failed on the
path's own steps and records that passed with nothing in them:
committing the discover handoff staled a green intent; a squash-merge
or rebase orphaned the delivery commit with no way back; a review.md
holding only the fingerprint froze; `Effort: tiny` was advertised but
ran the heaviest wave; the scaffold pre-skipped the research gate and
put its own example markers to the user; and nobody owned filling the
constitution.

**Decision**:

1. **The kit's doc trees never stale a baseline.** The specs tree and
   the `brainstorms/` handoff dir beside it are both exempt from the
   code-changed-since comparison (intent and survey baselines, and
   the converge delta). `specstate.doc_tree_prefixes` is the one list.
2. **A delivery record can be re-pointed.** spec-build's
   `tick.py <spec-dir> --redeliver <new-sha>` rewrites the record as
   `Delivered: commit @ <new-sha> (was <old-sha>)`. It refuses when
   the recorded commit is still an ancestor of HEAD, and when the new
   sha is not. check.py's lost-sha failure names the command. Once a
   docset records its delivery, the approval freeze's `Approved-at`
   commit is history and is no longer required to resolve; the
   manifest hashes still are. Before delivery a lost anchor still
   fails and is re-approved (`freeze.py --record --force`).
3. **approvals/review.md has a shape.** `freeze.py --record` requires
   the current docset fingerprint, the auditor's digest line
   (`digest: BLOCK <n> · …`), and after the last digest one
   `ruling: …` line per BLOCK it counts. The last digest is the
   current review, so a re-review is appended.
4. **Effort is `standard | large`.** `tiny` is a contract Tier only.
   A doc still carrying `Effort: tiny` reads `standard`. Missing or
   unknown still reads `large`.
5. **One draft path from an intent.** Choose the tier, then
   `scaffold.sh --tier <tiny|full> --into-existing <name>`, then fill
   spec.md. At full tier `--into-existing` leaves research.md absent,
   so the research gate is judged (amends D-025 for that one call; a
   fresh scaffold and every tiny one still ship the skip marker).
   While spec.md is still the template, `clarify` is BLOCKED behind
   `spec`: the template's example markers are never put to the user.
6. **The constitution has an owning step.** spec-design drafts
   `specs/CONSTITUTION.md` with the user before the approve gate
   (SKILL.md § The constitution). check.py's WARN and FAIL name the
   step. Payloads cite the constitution only once `check.py
   --constitution` reads it as filled.
7. **A wave dir holds one wave.** A wave emit removes the kit's own
   earlier payload files from the wave dir first; a `--repair` emit
   removes nothing. Execute payloads are always
   `implementer-T###.md` (amends D-054's unchanged-names list: the
   single-task `implementer.md` is gone).
8. **`approved` covers execution.** Nothing writes `Status: active`;
   it stays a legal word, and check.py no longer warns when an
   approved spec has work in flight. `tick.py` drops `(implemented)`
   from an entry it ticks.

**Consequences**: a review.md written before this decision that holds
only a fingerprint no longer freezes — add the digest line. Tools that
looked for `spawns/*/implementer.md` must glob `implementer-T*.md`.
The intent payload file keeps the name `surveyor.md` (D-054; pinned
by spec-define's flow tests). A history rewrite before delivery is
not covered by `--redeliver`; it is still a re-approval.
