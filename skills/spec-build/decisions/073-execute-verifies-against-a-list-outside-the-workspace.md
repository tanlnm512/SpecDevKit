# D-073: execute verifies against an approver list the workspace cannot write — and the fixtures approve the way the owner now does

The gate (D-053) admits a docset only when `freeze.verify` passes, and
D-053 adopted spec-design's D-071 in the same words: the list is the
repo's `specs/.approvers`, and every test fixture approves through
`tests/_approval.py` with a generated key, that list and
`freeze.py --approve --key`. Three forgeries got past that gate: a
nested `specs/<name>/specs/.approvers` holding the agent's own key
(spec-design D-081), a shell call of `--approve --force` with no
confirmation (spec-design D-082), and a `Delivered:` line beside a
locally committed unsigned record (spec-design D-083).

**Decision** (spec-design's D-081, D-082 and D-083 are canonical; this
record is the gate's half and its fixtures):

1. **No new gate; the existing one means more.** `--span execute` still
   refuses unless approve and verify are DONE, and verify is DONE only
   when `check.py` exits 0 — which it cannot while `freeze.verify`
   refuses the record, as it now does for a signer outside the machine
   approver list, for a workspace list standing in for one, for a
   nested `.approvers` anywhere under `specs/`, and for an unsigned
   record the remote default branch does not carry.
2. **The acceptance test keeps its shape.**
   `Gate010ForgedApprovalTests` still refuses the hand-written record
   and admits the docset after a real `--approve`; the three forgeries
   above are pinned in spec-design's `ApprovalSignatureTests`, beside
   the resolver they attack.
3. **Fixtures approve the way the owner does.** Every test that approves
   a docset goes through `tests/_approval.py`: a generated ed25519 key,
   the machine approver list under a throwaway HOME — importing the
   module points HOME there for the rest of the process, so no test
   reads or writes the real one — and `freeze.py --approve` on a pty,
   typing back the phrase the prompt names. An unsigned legacy record
   counts as history only after `_approval.publish` gives the repo a
   bare origin whose default branch carries it.
4. **D-053 paragraphs 1 and 4 are amended.** "A commit in the repo's
   ancestry carries" becomes "the remote default branch carries";
   `specs/.approvers` becomes the machine approver list.

**Consequences**: a session cannot open execute with a record it
produced itself, whichever of the three ways it tries. The gate costs
what spec-design's decisions cost — a machine list on every machine
that runs the gate's tests, a terminal for every approval, and a remote
default branch for every unsigned legacy record — and nothing of its
own. The cost if wrong is theirs.
