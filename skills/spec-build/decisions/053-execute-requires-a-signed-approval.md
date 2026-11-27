# D-053: execute requires a signed approval — a forged record is refused like a draft

spec-build's invocation gate (D-021: the freeze is the approval)
admitted any directory that carried `approvals/approval.md` and
`Status: approved`, and any write-capable agent could write both: the
review the freeze validated was a file the agent wrote itself, and
`freeze.py --record` asked nothing of the session but a shell. D-021
already named the limit — the freeze proves what was approved, not who
typed the yes — and this skill's own gate fixtures modelled approval
the same way: a hand-written review, `--record`, a flipped Status.

**Decision** (the signature, `--approve`, the delivered-docset
grandfather and the trust root are canonical in spec-design's D-071;
adopted here in the same words — this skill's half is the gate
consequence and its test):

1. **No new gate: the existing one now means something.** `--span
   execute` still refuses unless approve and verify are DONE, and
   verify is DONE only when `check.py` exits 0 — which it cannot while
   `freeze.verify` refuses the record, as it does for an unsigned
   record that no commit in the repo's ancestry carries — a
   `Delivered:` line alone is not an approval. A forged approval is refused
   exactly like a draft: exit 4 naming the approve gate, zero
   implementation files, one `intake_refusal` event.
2. **The acceptance test is `Gate010ForgedApprovalTests`** in
   `tests/test_execute_gates.py`: an agent-forged approval — a
   self-authored review with a locally computed fingerprint and a
   typed digest line, an `approval.md` the renderer writes, no
   signature — exits 4 naming the approve gate, and the same docset
   passes once the owner runs a real `--approve`.
3. **`migrate.py upgrade` never writes the record.** It no longer
   folds an old-grammar record into one `approval.md`: that was a
   write to `approvals/` by something other than the owner, and it
   left an unsigned record anyway. An unsigned record or a lone
   `approvals/review.md` is left in place with a note naming the
   owner's re-approval. The record's shape is unchanged, so `retro.py`
   reads its manifest lines as before.
4. **Fixtures approve the way the owner does.** Every test that
   approves a docset goes through `tests/_approval.py`: a generated
   ed25519 key, `specs/.approvers`, `freeze.py --approve --key`. Only
   the forgery under test writes a record by hand. Where `ssh-keygen`
   is absent those tests skip with the reason; the unsigned-record
   refusal needs none and stays pinned.

**Consequences**: a session that writes its own approval and review
and flips the Status word gets exit 4 at the same gate as a draft —
the engine no longer opens execute on files the session itself wrote.
An in-flight spec approved before this carries an unsigned record and
is refused at its next execute until the owner re-approves (the
contract review at the current fingerprint, then `freeze.py
<spec-dir> --approve --force --review <payload>` in their own
terminal). The cost if wrong is a gate keyed on something the session
can write — a commit author, a PR approval — in which case the forgery
passes again; those were declined as forgeable (spec-design D-071).
