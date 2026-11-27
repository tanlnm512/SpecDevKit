# D-082: `freeze.py --approve` confirms on the terminal — the spec and the fingerprint are typed back, on /dev/tty only

`--approve` is the owner's own-terminal step (D-071): a phrase in a
document, nothing mechanical. The call signed without asking anything,
so a session that reached the installed freeze.py and a passphrase-less
listed key produced a valid signature with one shell command.

**Decision** (freeze.py `approve` is canonical):

1. **Before writing or signing, `--approve` asks the terminal.** After
   every precondition passes — no `NEEDS CLARIFICATION`, the review at
   the current fingerprint, no existing record without `--force`, no
   nested approver list, a listed key — it prints the record, then
   writes to `/dev/tty` a prompt naming the spec, the docset
   fingerprint and the signing principal, and the exact phrase to type:
   `approve <name> <fingerprint>`.
2. **The typed line must equal that phrase.** A bare "y", a different
   line, an empty line, or an end of file exits 1 with nothing written:
   the record, its signature and the `approvals/` directory come only
   after the phrase.
3. **`/dev/tty` is the only channel that answers.** With no controlling
   terminal — opening it fails — `--approve` exits 1 saying it runs
   only in the owner's own terminal. No flag, environment variable or
   stdin pipe satisfies the confirmation; stdin is left alone, so a
   passphrase-protected key still prompts.
4. **D-071 paragraph 2 is amended:** "the owner's own-terminal step" is
   now a property the command enforces, not only a phrase.

**Consequences**: a non-interactive `--approve` — an agent's shell
call, a script, a piped `yes` — signs nothing. It costs: a real
terminal for every approval, and one line typed by hand; an owner who
ran `--approve` through a wrapper, a remote session without a tty
(`ssh -T`), or an editor task with no pseudo-terminal must change how
they run it. The cost if wrong is that of any terminal prompt: it
proves a terminal answered, not a person. A shell-capable agent whose
calls are given a controlling terminal can drive the prompt through a
pty of its own, and an agent that can read the key can sign a record
with `ssh-keygen -Y sign` directly, around `--approve` altogether. What
neither crosses is the key (a passphrase or hardware) and the approver
list outside the workspace (D-081) — both of which the kit recommends
and cannot enforce.
