# D-042: a proof of a test nobody wrote is PENDING, never a pass

A TC pass condition names its test (`mvn test -Dtest=FooTest#bar
-Dsurefire.failIfNoSpecifiedTests=false`). While the test did not exist
the command still exited 0 — the flag tolerates an empty selection, and a
quiet run prints nothing — so `audit.py proofs` read PASS, `mark.py
land` accepted it, and a plan whose tests were all written by its last
task landed every earlier task on proofs that had proved nothing. The
delivery pass was the first time the tests ran.

**Decision**:

1. **`audit.missing_named_tests(cmd, repo)`** reads the test selectors a
   proof command names (Maven `-Dtest=`, Gradle `--tests`, pytest node
   ids) and returns those no source in the repo defines. A command that
   names no selector is not judged.
2. **`proofs_data` does not run such a proof.** It records it under
   `pending`, prints `PENDING … not run: no source defines …`, and the
   proofs run exits 1. `dod` gate 1 fails while any proof is pending.
3. **`mark.py land` refuses a task none of whose proofs ran** — the tests
   belong with the task. `--allow-pending` is the explicit escape for a
   plan whose tests a later task owns: the landing is `(implemented)`,
   printed as unproven, and the delivery pass stays red until the pending
   proofs run. A task with some proofs run and some pending lands with a
   note.
4. **`audit.py preflight <spec>`** names missing prerequisites before the
   first wave (a program not on PATH, a Docker engine that does not
   answer when the docset leans on it) and lists the pending proofs.
5. **Delivery-pass friction fixed with it**: `scope` counts a path named
   by a glob the docs spell (`HoldWindow*Test.java`); `Docs impact:`
   tolerates a trailing parenthetical per file; `audit.py block` drafts
   the delivery block (docs, unruled rollback rows, hygiene suspects).

**Consequences**: a green proof means a test ran. The marker grammar and
`tick.py` are unchanged. A plan that lands code tasks before its test
task now says so at every landing instead of at the end.
