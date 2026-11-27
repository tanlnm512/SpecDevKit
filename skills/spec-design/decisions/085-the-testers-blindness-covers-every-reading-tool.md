# D-085: the tester's blindness covers every reading tool — Read, Grep, Glob and the shell

P4 (D-073) denies the tester a `Read`, `NotebookRead` or `view` of
tech-spec.md, plan.md and task.md. The tester also holds `Grep` and
`Bash`: a Grep over `specs/<name>/plan.md`, a Glob for `task.md`, a
`cat` of either — none is a file-writing call or a Read, so none was
denied. The blindness was a rule for two of the tester's four tools.

**Decision** (tools/hooks.py is canonical):

1. **A search is judged by what it names.** When the caller identity
   names the tester, a `Grep` or `Glob` call whose `path` or `pattern`
   argument names `specs/<name>/{tech-spec.md,plan.md,task.md}` is
   denied with the P4 reason line.
2. **A shell command naming one of the three files is denied
   outright.** When the caller identity names the tester and the
   command's text names one of them, the call is denied whatever it
   would do with the file — a write, a redirect, a command substitution
   and a `cat` alike, because a read is what the rule exists to stop
   and the tester never needs to name those files (`check.py` takes the
   spec dir). This is stricter than the read-only allowance P3 gives the
   approval paths, on purpose.
3. **It is a tripwire, best effort, like P3.** A path is matched on its
   components as the text spells them: a glob pattern
   (`specs/<name>/*.md`), a directory with the file named only in
   another argument, a `cd` into the spec dir followed by a bare
   filename, or a command that reaches a file without naming it are not
   seen. With no caller identity in the payload P4 allows and says
   nothing, as before.
4. **`Grep` and `Glob` join the registration's matcher.** A harness runs
   the hook only for the tools its matcher names, so without them the
   new rule never fires; the owner pastes the updated REGISTER.md after
   a sync.
5. **The stronger branch stays open.** Dropping `Bash` from the tester —
   running `check.py` from the orchestrator instead — closes the shell
   half without a tripwire. It changes the tester's brief and payload,
   so it is a change to that role, not to the guard.
6. **D-073 paragraph 1 is amended:** "a `Read`, `NotebookRead` or `view`"
   becomes "every reading tool the tester holds".

**Consequences**: where the owner registered the guard and the harness
names the caller, the tester's Grep, Glob and shell are blind too. The
matcher grew by two tools, so the guard runs on every search call of
every session — pure Python, no subprocess unless P2 fires. The cost if
wrong is D-073's silence: a harness that names the caller under a field
the guard does not read, or that was registered with the old matcher,
runs the new half as a no-op. Its opposite is D-073's: an identity that
names a tester forbids no read the tester needs. A tester that must
name one of those three files in a command, for a reason this decision
did not foresee, is denied and told why.
