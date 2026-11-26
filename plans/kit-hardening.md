# Kit hardening plan — round 2: close the gaps the implementation review found

Source: the review of 4913c41 ("harden skills and agents for the
anonymous-agent SDLC") against the round-1 plan. All suites,
`tools/tests/run.sh`, `drift-check.py` and the mini-spec check pass;
phase 1, the claim registry, the reader shell removal, the
confirmer/verifier briefs and the SKILL.md slimming hold. What remains
is below, highest risk first.

Every item that changes a doc contract lands with its own D-### in the
owning skill's `decisions/` (C-05); scripts are edited in one skill and
copied byte-identically (parity tests); generated surfaces are
regenerated, never hand-edited. Done for every item: all seven skill
suites, `tools/tests/run.sh`, `python3 tools/drift-check.py` green, and
each fix's regression test fails on 4913c41 for the intended reason.

## Phase A — An agent must not be able to produce an approval (blocking)

Do this before any spec is approved under the signature scheme.

### A1 Pin the approver list to one trusted location
- **Gap**: `freeze.py` `_approvers_file` takes the nearest
  `specs/.approvers` walking up from the spec dir. A nested
  `specs/<name>/specs/.approvers` shadows the root list (reproduced),
  and the recommended CODEOWNERS pattern does not cover it.
- **Do**: read the list from the repo root only; refuse verify when any
  other `.approvers` exists under `specs/`. Prefer a trust root the
  workspace cannot edit: a machine-level list
  (`~/.config/spec-dev-kit/approvers`) for local runs, and the list as it
  stands at the remote default branch for CI.
- **Accept**: a test with a nested list holding an agent key — verify
  fails naming the shadow file.

### A2 Keep `--approve` in the owner's terminal
- **Gap**: the guard's P3 admits any invocation of the installed
  `freeze.py` (`tools/hooks.py` `_is_freeze_call`), `--approve --force`
  included; `approve()` signs without a confirmation. With a
  passphrase-less listed key, an agent's own call yields a valid
  signature.
- **Do**: P3 admits `freeze.py` only with `--verify` (and other
  read-only flags); `--approve` requires a confirmation typed on
  `/dev/tty` — refused with no controlling terminal — naming the spec
  and fingerprint being approved.
- **Accept**: hook test denying `freeze.py … --approve`; freeze test
  where `--approve` with no tty exits 1.

### A3 Close the unsigned-record grandfather
- **Gap**: `_record_is_history` accepts an unsigned record when the
  docset carries a `Delivered:` line and HEAD holds the record byte for
  byte. An agent can add the line and `git commit -a` (no path named,
  so the guard is blind).
- **Do**: resolve the grandfather against the remote default branch
  (`origin/<default>`), not HEAD or the claimed delivery sha — or only
  for records whose introducing commit predates signing.
- **Accept**: a test where a forged, locally committed, `Delivered:`
  docset fails verify.

## Phase B — Make 2.5/2.6 enforced outside spec-build

### B1 spec-design stops on a refused digest
- **Gap**: `graph.py` `sweep_digests` output goes to stderr and the run
  emits the next wave anyway; `--run` sweeps once at startup only.
- **Do**: a malformed or `capability_missing` digest holds its node
  (the frontier treats it as not done) and `--run` re-sweeps between
  waves; exit with the fix-and-run-again line.
- **Accept**: graph test — a malformed tech digest blocks the plan wave.

### B2 spec-review checks the tools report in code
- **Gap**: `review_orchestrator.py` `findings-parse` strips the
  `tools:` line without checking it; D-029 is prose. The fixer's
  required set is `Read` only.
- **Do**: the oracle validates the report per role against the brief's
  `tools:` line (fixer: Read, Grep, Glob, Bash, Write, Edit); a missing
  tool is a failed call, not a finding or a round.

## Phase C — Wiring and contradictions

### C1 Headless `--run` honors or refuses the model step
- `graph.py` runner substitution has no `{model}`; round 4 runs on the
  same model silently. Add a `{model}` placeholder; a runner template
  without it stops `AWAITING ORCHESTRATOR` on a round-4 payload rather
  than spending the round.

### C2 Fix the worktree payload contradiction
- `ISOLATED_WORKTREE_LINE` forbids writing outside the worktree while
  the same payload asks for the digest (and the brief allows
  `notes/T###.md`) in the main tree. State the two exceptions in the
  line; test that `land` finds an isolated developer's digest.

### C3 Tester blindness covers every reading tool
- P4 guards `Read`/`NotebookRead`/`view` only; the tester holds `Grep`
  and `Bash`. Either drop Bash from the tester (it needs check.py — run
  it from the orchestrator instead) or extend P4 to `Grep`/`Glob` paths
  and shell commands naming the three files. Update D-073.

### C4 Move the eight draft intents out of `specs/`
- They carry six open markers each and a baseline of the parent commit,
  so they can never be green and drop `tools/grade.py`'s spec-define
  dogfood to 1/9. Move them to `plans/intents/` (or teach grade.py to
  skip parked drafts) until each enters through `/spec-define`.

## Phase D — Provenance and schema tightening

- **D1 Unvouched digests**: a digest file with no matching ledger
  `wave` row is marked `unverified`, never given an orchestrator line;
  the latest digest is the one the ledger names, not the highest
  `wave-N/` directory.
- **D2 Escape reported tool names**: reject `·` (and newlines) in a
  `tools:` report before it enters the provenance line.
- **D3 Land never reads an unswept digest**: on `TaskLockBusy`, `land`
  refuses instead of proceeding; a digest with no provenance line is
  not valid at land.
- **D4 Ledger tamper evidence**: chain each ledger row to the previous
  row's hash so an appended or edited row is detectable; state in D-055
  that this detects, not prevents.
- **D5 Schema strictness**: no trailing segment absorbed by the last
  free-text field; summary counts checked against the content (threads,
  auditor findings); the `tools:` report read from the first line only.
- **D6 Schema ↔ brief test**: extract each digest grammar from its brief
  or `protocol/lenses.md` and assert `digests.py` accepts it, so a brief
  edit cannot drift silently.

## Phase E — Coordination edges

- **E1 Budget is a ceiling**: truncate a wave to the remaining budget
  (or refuse the claim) instead of overshooting by a wave; test with a
  multi-task wave.
- **E2 Failed tasks keep their files**: a task at `(fix n/5)` — and at
  the cap while adjudicated — keeps its registry row live so another
  spec cannot claim its files.
- **E3 `drop` removes the task's worktree**, as land and release do.
- **E4 Proof location**: `land` proves the tree the digest says the
  work is in; a main-tree edit with an existing worktree is refused,
  not landed unproven.

## Phase F — Docs and process

- **F1** Remove the ADR ids added to SKILL.md bodies (spec-design
  2 → 7, spec-build D-053/D-057) per D-060.
- **F2** Point to the same-signature rule from fix rounds 2–3, not only
  at the cap.
- **F3** Drop "or directly for a …-only pass" from the four reader
  descriptions — without a shell they need the oracle's diff files.
- **F4** Attempt wording: "four rounds spawn, the fifth failure stops"
  everywhere (`rules/agent-limits.md`, developer.md, `MODEL_STEP_LINE`,
  D-051 title).
- **F5** Note the spec-design D-077 gap in `decisions/INDEX.md`; fix
  "tiered spawn" at `HARNESS-FACTS.md:62`.
- **F6** Re-record the live evals (the round-1 4.1 acceptance, and the
  seven results D-067 marks stale); decide the VERSION/CHANGELOG bump.
- **F7** Run `bash tools/sync.sh` then `--check` on each machine: the
  retired `review-*` agents (still holding Bash) are installed and the
  guard is not.
- **F8** Land future rounds as one PR per phase — a single 21k-line
  commit is not reviewable or revertible piecemeal.

## Order

1. Phase A (blocking).
2. Phase B.
3. Phase C.
4. Phases D and E.
5. Phase F alongside, F7 immediately.
