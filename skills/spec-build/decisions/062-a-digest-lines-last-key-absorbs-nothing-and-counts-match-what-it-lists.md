# D-062: a digest line's last key absorbs nothing, and the auditor's counts match the findings it lists

D-054 adopted the strict schemas and let free text hold the separator
because a value ends where the next key begins. The last key has no
next key: it ran to the end of the line, so the auditor's `worst` took
every segment after it, and the free tail of a developer's `note`
(`acceptance command red outside my files: <command> — <file>`) took
any more. An audit line that counted no finding was never compared with
the findings listed under it: `BLOCK 0` above a listed BLOCK read as a
clean audit.

**Decision** (the rule is canonical in spec-design D-096; adopted here
in the same words — this skill's half is the two grammars this skill
spawns; amends D-054 §1):

1. **The last key of a line grammar holds no ` · `.** The auditor's
   `worst` and the developer's `note` are refused when they hold the
   separator, with the key and the value named. The developer's
   `deviation` is unchanged: it ends where `note` begins, so
   `scope: repo/a.py · repo/b.py` still validates.
2. **The auditor's BLOCK, WARN and NIT are counted against the finding
   lines beside the line** — a numbered or bulleted line opening with
   the level. A mismatch is malformed: the problems go back to the
   auditor and the review runs again. The line alone, the form
   `freeze.py` folds into a record, lists nothing and is not checked,
   so every signed record still verifies.
3. **The brief and the schema are pinned together.** `tests/test_digests.py`
   reads the developer's and the auditor's grammar — the auditor's with
   the finding line its brief states — from `agents/`, fills each, and
   asserts the schema accepts every documented alternative and refuses
   a dropped, an added, and two swapped segments.

**Consequences**: a digest that carries more than its grammar declares
is refused instead of read, and an audit that under-counts its own
findings is malformed. The cost if this is wrong: an auditor whose
`worst` holds ` · ` is re-run and told why, and a developer whose note
names two files with the separator rewrites the note with another
punctuation — the cure for a grammar that is too strict is an edit in
the spec-design master, replicated.
