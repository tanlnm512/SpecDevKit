# D-084: the guard admits the installed freeze.py only to verify, denies every `--approve` call, and treats the machine approver list as an approval path

The guard's P3 (D-072) let any invocation of the installed freeze.py
through to the read-only list, `--approve --force` included, and a
command naming no guarded path was not judged at all:
`freeze.py specs/<name> --approve --force` was admitted because it names
no record and no `spec.md`. With the list inside the workspace and a
passphrase-less key, one admitted call produced a valid signature. P1
guarded `specs/.approvers`; D-081 moved the trust root to the machine
list, which no rule named.

**Decision** (tools/hooks.py is canonical; the guard stays a
recommended tripwire the kit never registers):

1. **The installed freeze.py is admitted only to verify.** P3 counts a
   simple command as read-only when it runs the installed freeze.py
   with `--verify` and none of `--approve`, `--force`, `--review`,
   `--key`. Every other invocation is judged like any other command.
2. **No shell call approves.** A simple command that runs any script
   named `freeze.py` — by basename, directly or under a Python
   interpreter, wherever it sits — with `--approve` is denied with the
   P3 reason line, even when the command names no other guarded path.
3. **The machine approver list is an approval path.** P1 and P3 treat a
   path ending `spec-dev-kit/approvers` as they treat
   `specs/.approvers`: the owner's to write, by hand — freeze.py never
   writes it.
4. **The reason lines say what to do instead.** P1 names the owner as
   the writer of the record and of the lists; P3 tells a session to
   print the command for the owner and wait. REGISTER.md carries both
   and adds the `--approve` call to its live check.
5. **D-072 paragraphs 4 and 6 are amended.** P1's path set gains the
   machine list; P3's "an invocation of the installed freeze.py" becomes
   "the installed freeze.py run with --verify".

**Consequences**: where the owner registered the guard, an agent's
`freeze.py --approve` is denied before it runs and is told to hand the
step back; where it is not registered, the terminal confirmation
(D-082) and the signature check (D-071) hold. It costs nothing beyond
D-072's shell allowlist. The cost if wrong is D-072's silence, and P3's
own limits: a wrapped command (`sh -c "…"`, `env`, `sudo`, a copy under
another name) is not parsed through, a call that never names the script
is not seen, and the guard denies nothing on a harness whose hook
payload or registration differs from the assumed shape.
