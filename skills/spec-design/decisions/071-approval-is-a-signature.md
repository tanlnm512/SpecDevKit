# D-071: an approval is a signature — `freeze.py --approve` signs the record and verify refuses an unsigned one

The freeze was the approval (D-050): `approvals/approval.md` beside
`Status: approved`. Any write-capable agent could author both. The
contract review `freeze.py --record` validated was a file the agent
could write itself — a docset fingerprint anyone can compute, a typed
digest line, typed rulings — `--by` was free text no code ever read,
and nothing distinguished the owner's record from a session's own.
spec-build D-021 said so: the freeze proves what was approved, not
independently who typed the yes.

**Decision**:

1. **An approval is a signature.** `approvals/approval.md` passes
   `freeze.py --verify` only when `approvals/approval.md.sig` holds a
   valid SSH signature (SSHSIG, namespace `spec-dev-kit-approval`) over
   the record's canonical text, made by a key in the repo's approver
   list `specs/.approvers` — ssh `allowed_signers` form, one
   `<principal> <key-type> <key-blob>` line per approver, `#` a
   comment. The canonical text is the file with LF line endings and
   exactly one trailing newline; verify re-canonicalizes first, so a
   CRLF checkout still verifies and any other change to the record
   breaks it.
2. **`--approve` is the owner's own-terminal step and the only writer
   of the record.** It runs every precondition the freeze had — no
   `NEEDS CLARIFICATION` in a frozen file; at full tier a contract
   review naming the current docset fingerprint, a digest line, and
   one ruling per BLOCK — prints the record before signing, signs it
   with `ssh-keygen -Y sign`, and writes `approval.md` and
   `approval.md.sig` together, both or neither. `--key` defaults to the
   first of `~/.ssh/id_ed25519`, `~/.ssh/id_ecdsa`, `~/.ssh/id_rsa`
   that exists and its public half must be listed, or the step refuses
   naming the mismatch and the remedy. The record's `**Approved-by**`
   line carries the signing key's principal — inside the signed text.
   `--by` is removed, and `--record` refuses (exit 1) naming
   `--approve`.
3. **Commit identity and PR approval were declined as forgeable.** An
   agent commits as the configured user, so the `Approved-at` commit's
   author proves nothing; an agent can post a PR approval with the
   owner's own `gh` login, and the approve gate runs before any PR
   exists. A signature by a key the agent does not hold is the one
   binding that holds.
4. **`--verify` names which of three things failed, each with its
   remedy**: no `specs/.approvers` (create it with your SSH public
   key), no `approval.md.sig` (the owner re-approves in their own
   terminal), or a signature that does not verify (the first line of
   ssh-keygen's stderr). `ssh-keygen` absent is the first case's
   sibling: refuse, naming the missing program.
5. **The trust root and its limits.** The approver list and the key
   are what the signature rests on: a passphrase-less key the agent
   can read, or an edited `specs/.approvers`, defeat it. So
   `specs/.approvers` and `specs/**/approvals/` belong under a
   CODEOWNERS rule and the key under a passphrase or in hardware. The
   kit recommends and never writes: `scaffold.sh` prints the two
   pattern lines once per repo, and this skill's SKILL.md § approve
   says it in one sentence.
6. **An unsigned record is history only when a commit carries it.**
   That is the whole grandfather: a delivered docset whose record is
   byte-for-byte what the delivery commit — or HEAD — holds in this
   repo's ancestry still verifies, so ship, release and archive keep
   working on specs approved before this decision and on the committed
   example. A `Delivered:` line alone proves nothing, since any writer
   can add one: an unsigned record that no commit carries is a verify
   failure whatever the docset claims, and an old-grammar record
   (`## Frozen contract`) gets no other exemption — the owner
   re-approves.
7. **Enforcement is the existing chain; no gate is added.**
   `freeze.verify` → `check.py`'s approval evidence → the verify node
   not DONE → approve BLOCKED → `--span execute` exits 4 (spec-build
   D-053 holds the acceptance test). graph.py changes only where its
   printed guidance was wrong: the approve pause now hands the step to
   the owner's terminal and sets Status only after `--verify` passes.
   check.py's migration detector drops "the unfolded approval record"
   from its elements, because nothing converts a record now but the
   owner's signature.

**Consequences**: an approval is attributable — the record names a
principal whose key the repo lists — and a forged or edited record
stops at the same gate as a bare Status flip. It costs: one contract
review at the current fingerprint and one `--approve` for every
in-flight spec that carries an unsigned record, before its next
execute; a `specs/.approvers` in every repo before its first approval;
`ssh-keygen -Y` on the machine that approves and on every machine that
verifies (an open assumption in HARNESS-FACTS.md). The cost if wrong is
that the signature binds the docset to a key, not to a person's intent:
with the key unencrypted in the agent's reach or the approver list
agent-writable, this is no stronger than D-050 was. The legacy
grandfather keys on a commit — the one act the kit already treats as
the user's (ADR-014) — not on a `Delivered:` line, which any writer can
add: a session that forges a record must also put it in the user's
history, in view.
