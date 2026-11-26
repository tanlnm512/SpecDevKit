# D-072: approval writes are guarded by a generated hook the kit recommends and never registers

An approval is a signature (D-071): the record and its `.sig` pass
`freeze.py --verify` only when a key in `specs/.approvers` signed them.
The signature is the boundary, but it is checked late — a session that
writes `approvals/approval.md` and flips `Status: approved` is stopped
at verify and at the execute gate, after the files are already wrong.
The hardening plan's item 2.1 asks for the earlier stop: a generated
PreToolUse hook per harness, under `tools/` (C-03), denying spawned
agents writes to `specs/**/approvals/**` and to `Status:` lines.

No harness hook contract is verified by this repository. The kit ships
zero hooks and `HARNESS-FACTS.md` has no hook row: which file a harness
reads a hook from, what it passes one, and how a hook denies a call are
open assumptions here, not facts.

**Decision**:

1. **The kit generates a guard and never registers it.** `tools/hooks.py`
   renders `spec-kit-guard.py` and `REGISTER.md`, the exact text to
   paste. sync installs both under a kit-owned directory
   (`~/.claude/spec-dev-kit/`, `~/.zcode/spec-dev-kit/`) through the
   same ownership ledger every kit deploy uses — planned before the
   first write, a foreign file refused and kept, `--check`
   byte-comparing a fresh render, the stale sweep covering them — and
   ends a plain run with one `recommended:` line naming the file to
   paste each `REGISTER.md` into. sync never writes `settings.json` or
   `config.json`. Whether a harness honors the registration is the
   owner's live check: a session that tries
   `echo x >> specs/<name>/approvals/approval.md` is denied with the P1
   line.
2. **Two harnesses get a guard; the rest get none.** claude — a command
   hook in `~/.claude/settings.json` — and zcode — a process hook in
   `~/.zcode/cli/config.json` or `<repo>/.zcode/config.json` — whose
   hook contracts are Claude-shaped in what a hook reads and how it
   answers. Codex, Gemini CLI, OpenCode, omp, Kilo and Droid get none:
   their hook contracts are unknown here.
3. **The guard answers with exit codes and fails open.** It reads one
   JSON object on stdin: `0` allows, `2` denies with one reason line on
   stderr naming the rule and its remedy. Unreadable input, a missing
   field, or any internal error allows and prints the error — a broken
   guard must never brick a session. It writes no file and runs nothing
   but the installed `freeze.py <spec-dir> --verify`.
4. **P1 — approval records and the approver list are written only by
   `freeze.py --approve`.** A file-writing call (Write, Edit,
   MultiEdit, NotebookEdit, ApplyPatch, or any call carrying `content`
   or `new_string`) whose target lies under `specs/<name>/approvals/`
   or is `specs/.approvers` is denied. A call that carries none of the
   typed fields — ApplyPatch, whose input is a patch — is read as text
   instead: denied when its text mentions an approval path. That is a
   text tripwire, not a parse, and P2 reads the same text — a
   `specs/<name>/spec.md` it names together with a `**Status**:` line
   reading approved, active or done.
5. **P2 — `Status: approved` follows a verifying approval.** A
   file-writing call on `specs/<name>/spec.md` whose new text sets
   `**Status**:` to `approved`, `active` or `done` is denied unless the
   installed `freeze.py <spec-dir> --verify` exits 0; any other Status
   edit runs nothing. The generator bakes in the installed `freeze.py`
   path — the one line on which the two targets' scripts differ.
6. **P3 — the same two rules for the shell, as a tripwire.** A command
   naming one of those paths is allowed only as a read-only use: every
   simple command one of a fixed read-only list or an invocation of
   the installed `freeze.py`, no redirect that writes, no command
   substitution. This is a tripwire, not a boundary — the signature is
   the boundary. A command that reaches a record without naming it
   (`cd` into the spec dir) is not seen, and a forged record still
   stops at verify.
7. **A primary root, installed unconditionally.** The guard installs
   for claude and zcode on every sync, like the skills and commands
   beside it: those two are the kit's primary roots, written without
   asking whether the harness is there. A gate on the config home was
   declined — sync itself creates `~/.claude` and `~/.zcode`, so the
   gate could only be unstable from one run to the next.
8. **No gate is added and no committed surface changes.** The guard is
   machine-installed, never committed: `tools/drift-check.py` has no
   `guards` set, `tools/hooks.py --check` verifies an installed root,
   and `tools/sync.sh --check` runs it.

**Consequences**: the common forgery — a Write or Edit on the record,
an `echo >>`, a `sed -i` on the Status line — is denied where the owner
registered the guard, and the reason line names the remedy. It costs:
two files per harness root on every machine, a ZCode guard and its
`recommended:` line on a machine without ZCode included; one paste per
harness by the owner; and a shell allowlist that also denies some
harmless commands naming those paths (`git add` of a signed record
among them) — the owner runs those in their own terminal or lifts the
registration. The cost if wrong is
silence: a harness whose hook payload differs from the assumed shape,
or that ignores the registration, runs unguarded with nothing failing
here. So the guard is a recommended tripwire, and the signature
(D-071) stays the one thing an approval rests on.
