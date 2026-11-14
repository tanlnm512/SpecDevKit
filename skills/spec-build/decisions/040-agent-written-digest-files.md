# D-040: agent-written digest files are evidence, never status

A digest existed only in the orchestrator's conversation. If the session
died after a developer finished but before its marker was written, what
was lost was whether it reported `implemented` or `blocked:why`, its
D-### deviation, and its `note` about a failure in another task's file —
resume fell back to reading the diff and guessing.

**Decision**:

1. **Write-capable roles write their digest to a file as their final
   action**: `specs/<name>/digests/wave-<N>/<payload-stem>.md`, the
   same text as the returned digest. The path is per wave, so a
   fix-round re-spawn of T001 in wave 6 never overwrites its wave-4
   digest. `graph.py build_payload` adds the `## Digest file` block to
   every payload whose brief is write-capable (developer, analyst,
   architect, tester — the merged designer rides architect).
2. **Read-only roles keep conversation-only digests**: auditor,
   panelist, integrator, release-manager and the review lenses hold no
   Write tool, and their passes re-run in full on resume anyway. Adding
   a write tool to them would weaken the guarantee that they write
   nothing. That trade is declined.
3. **The digest file is evidence, never status**: nothing reads it as
   the task marker (the markers stay task.md's, D-039). It feeds
   `mark.py land` (the file is primary; `--digest` is the override when
   the file is missing, printed as a warning — never a way to talk over
   a file that says blocked) and `--explain execute`'s resume column
   (`digest on file: implemented|blocked:…|none` per claimed task).
   `specstate.latest_digest` is the one parser; the digest line's own
   `task` field must match the requested id (a stem can lie).
4. **Digests are run scratch, not archived contract**: archive removes
   `digests/` with `spawns/`; before that, `retro.py` folds their
   counts (tasks on file, blocked, deviations) into `retro.md`, which
   IS archived.
5. **The shared protocol carries the rule once** (byte-shared across
   the three skills, pinned by test_parity): the digest file is the one
   second write every write-capable role gets, next to the implementer
   note exception — evidence of what the agent reported, never status.
   spec-design D-059 records the shared side.

**Consequences**: a crash between "developer done" and "marker
written" loses nothing: the resume path becomes mechanical (an
`implemented` digest → `land` re-runs the proofs; a `blocked:` digest →
`release` and rule; no digest → read the diff as before). This is the
input the headless execute lift (D-041) lands on.
