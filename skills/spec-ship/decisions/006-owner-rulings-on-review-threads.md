# D-006 — The owner's thread rulings are recorded, and `comments` reads them back

**Status**: accepted (2026-11-25)

## Context

`comments` was stateless by contract: the integrator classified every
unresolved thread `must-fix`, `question`, `nit`, or `disagree`, the
user relabeled one, and on the next `threads` run the same threads
were classified again from the same comment text — the owner's word
evaporated with the session, and the user relabeled it again. The kit
already keeps owner rulings as one-line records in the docs
(`Rollback: <row> — <ruling>`, `Hygiene: <path> [<kind>] — <ruling>`
in the delivery block), so a thread label has a natural shape; it
only lacked a writer and a reader.

## Decision

- **`ship.py rule <spec> --thread <id> --label <label> [--why <text>]`
  is the writer**, to `specs/<name>/notes/rulings.md` — where
  `evidence` places its records, the same home at both tiers. One
  line per ruling, `- <thread id> — <label> — <why>`, with `no reason
  given` when none was; re-ruling a thread replaces its line in
  place. A label outside the four or an empty thread id is usage
  (exit 2). No PR is read: like `record` and `evidence`, it is a
  local write, landed before the next `threads` run.
- **`comments` reads the file.** A listed thread with a ruling
  carries `ruling` (label, why, unresolved), and the payload says a
  ruled thread keeps its label and is not to be reclassified — the
  ruling's why is the owner's reason — while only unruled threads are
  open for classification. A ruling whose thread is resolved or no
  longer listed stays on file and is reported in
  `inactive_rulings[]`; it never fails the run.
- **When to record**: whenever the user relabels a thread, or
  confirms a classification they were asked about, before the next
  `threads` run. SKILL.md step 5 and the protocol say so.
- The ruling is a doc change on the spec's branch, like the
  `Shipped:` record: its commit is asked first, and pushing it is one
  more previewed push.

## Consequences

The owner's relabels survive the session: the next `threads` run
echoes them instead of re-deriving, and the user rules once. Cost if
wrong: a stale ruling shields a thread from reclassification after
the code changed under it — `rule` again is the cure, and `comments`
still shows the thread's comments and reports inactive rulings, so
the drift is visible rather than silent. The file is one line per
ruling with no block structure, so it never collides with the
fix-round evidence appended beside it.
