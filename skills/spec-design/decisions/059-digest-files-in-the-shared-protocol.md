# D-059: the digest file's one shared rule

spec-build D-040 has write-capable agents write their digest to
`digests/wave-<N>/<payload-stem>.md` as their final action. The write
permission lives in the shared protocol, whose bytes ship identically
in this skill too (test_parity pins them), so the shared side is
recorded here:

1. **"Your artifact is the deliverable"** gains the file: when the
   payload names a digest file, that file holds the same text as the
   returned digest, written as the agent's final action so it survives
   the session that spawned it.
2. **Rule 5 (one artifact per doc author)** names the digest file as
   the one second write every write-capable role gets — next to the
   implementer's note exception — and says what it is: evidence of
   what the agent reported, never status.

`graph.py` (shared) emits the `## Digest file` block on payloads whose
brief is write-capable; `specstate.py` (shared) owns
`latest_digest`, the one parser. Status stays in task.md only — the
digest file is evidence.
