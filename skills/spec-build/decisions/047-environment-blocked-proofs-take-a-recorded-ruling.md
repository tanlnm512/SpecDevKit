# D-047: a proof the environment cannot run is ENV-BLOCKED, and takes a recorded ruling

A proof whose environment is missing — a program not installed, a Docker
engine that does not answer, a variable the docset names but the shell
lacks — had two dishonest outs: `proofs --run` charged it as FAIL
(a failure of a change that never ran means nothing), or the proof could
not run at all and nothing said so. `preflight` could say NO-GO, but
when the user cannot supply the environment there was no recorded way to
proceed and no honest record that a proof never ran. A quiet skip was
never an option: nothing in the delivery pass passes or blocks silently.

**Decision** (the pattern D-037 set for hygiene suspects, and D-042 for
pending proofs, exactly):

1. **The fifth outcome, ENV-BLOCKED, is decided from evidence, never a
   guess**: the proof's program does not resolve (the check preflight
   has always run, now shared as `audit.env_block_reason`), a variable
   the command names is unset, its Docker engine does not answer, or the
   finished run ends exit 126/127 with the shell's `command not found`
   (`audit.run_env_block` reads it off the run). The outcome names what
   is missing — `ENV-BLOCKED TC-013 — missing: docker engine`. It is
   not a pass and not charged as a failure; `proofs --run` exits 1 and
   dod gate 1 stays red while it stands unruled. PENDING (D-042: the
   named tests do not exist) keeps its meaning and is judged first.
2. **Rulings live in the delivery block**, the D-037 shape:
   `- Proof: TC-### — <ruling>`. `audit.py block` drafts one line per
   unruled environment-blocked proof; the owner's ruling turns the row
   RULED in the `proofs` output and lets dod gate 1 pass with the
   ruling in view. A FAIL is never rulable this way.
3. **`mark.py land` treats an environment-blocked proof like a pending
   one**: it never ran, so land refuses a task none of whose proofs ran
   unless `--allow-pending` is given — naming what is missing when it
   refuses.
4. **`preflight` names the same thing in its NO-GO**: which proofs
   would run ENV-BLOCKED, and that the owner's recorded ruling is the
   way to proceed when the environment cannot be supplied.

**Consequences**: the delivery block gains an optional sixth line, and
the cost if wrong sits in the open: a ruled proof is an unproven claim
riding the owner's name, so the ruling says what is missing and why the
gap is accepted — the delivery record carries it, and `/spec-ship`
lists these recorded lines in the PR body. Detection is unchanged by a
ruling: supply the environment and re-run, and the proof is judged on
its own exit again.
