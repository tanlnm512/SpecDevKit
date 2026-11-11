# Testing

How this kit is tested, and what is still untested. The first half is
durable guidance; the backlog at the end is a work list — delete each
item when its test lands, and delete the section when it is empty.

## Running the checks

Run all of these before declaring work done. Each exits non-zero on
failure; `tools/tests/run.sh` prints many sections, so read its exit
code, not its last lines.

| Check | Command |
|---|---|
| Skill suites (one per skill) | `skills/<name>/tests/run.sh` |
| Tooling suite | `bash tools/tests/run.sh` |
| Generated surfaces | `python3 tools/drift-check.py` |
| Shared-script replicas | `python3 tools/parity.py --check` |
| Docset contract | `python3 skills/spec-design/scripts/check.py skills/spec-design/examples/mini-spec/specs/mini-spec` |
| Install plan (read-only) | `bash tools/sync.sh --check` |

The suites need `python3` 3.10 or newer on PATH, or `uvx`.

## What deserves a test

The kit-wide rules in `rules/engineering-rules.md` § Before adding a
test are canonical. In short:

- A test protects observable behavior, a contract, or a credible
  regression. Use the smallest test that reliably proves it.
- Not every change needs one. Renames, copy, config, docs, and pure
  refactors usually need none. Cover the paths the change puts at
  risk, not every edge case.
- Each contract has one owner test at the strongest boundary. Extend
  an existing case or table before adding a near-duplicate; avoid
  combinatorial matrices.
- Never add exports, wrappers, or seams that only tests use.
- A test whose assertion cannot disagree with the code proves nothing:
  do not recompute the expected value with the logic under test.
- A bug fix's regression test must fail on the pre-fix code for the
  intended reason. Verify this; do not assume it.

## How tests are written here

**Shape.** Python stdlib `unittest` only (no third-party packages),
one `tests/test_<area>.py` per area, discovered by the skill's
`tests/run.sh`. A new skill ships its own `tests/run.sh` and a CI step
in `.github/workflows/ci.yml`.

**Boundary.** Test scripts at the command line: run the script as a
subprocess and assert its exit code and the one line a model acts on
(`AWAITING …`, `deferred: …`, a `FAIL`/`PASS` row). Models read that
output, so that is the contract. Import a module directly only for a
pure helper with no CLI path.

**Isolation.**
- Work in a temp directory. Copy a fixture from `examples/` and
  `git init` it there; never run a mutating script against the repo's
  own tree.
- Never touch the real home directory. Install tests point `HOME` at a
  temp directory.
- Never reach a real remote. Push and tag tests use a bare repository
  on local disk as the remote.
- Never call the real `gh`. Put a stub `gh` first on `PATH` that
  prints canned JSON, and assert the degraded path with `gh` absent.
- Pin git behavior the script depends on (`diff.noprefix`,
  `diff.mnemonicPrefix`, default branch name) inside the test repo, so
  a developer's global git config cannot change the result.

**Gates.** For every gate, cover the refusal and the pass: a fixture
missing the thing must fail with a message naming the fix, and the
honest minimal fixture must pass. Where a section may say
`none — <reason>`, test that form too. Check both tiers when the
behavior differs (`Tier: tiny` reads spec.md; full reads the docset).

**Proving a regression test.** Copy the pre-fix script into a scratch
copy of the skill (or `git stash` the fix), run the new test there,
and confirm it fails with the bug's own symptom — not an import error
or a missing fixture.

**Shared and generated files.**
- The shared-script closure lives in `skills/spec-design/scripts/` and
  is replicated by `tools/parity.py`. Test it once, in spec-design;
  the replicas are covered by `parity.py --check`.
- A file duplicated across skills on purpose is pinned byte-identical
  by `tools/tests/test_parity.py`. Add a pin when you add a duplicate.
- After changing a brief, a SKILL.md description, or
  `rules/engineering-rules.md`, regenerate (`tools/agent-defs.py`,
  `tools/plugin-manifest.py`, `tools/kit-rules.py`) before running
  `drift-check.py`.
- Example docsets under `examples/` are fixtures: when a check gets
  stricter, update them honestly, and re-record a freeze with
  `freeze.py --record --force` instead of editing a hash.

**Eval cases.** `evals/cases.md` holds conversational cases a person
or a recording runner walks through; they are not unit tests.
`tools/tests/test_evals.py` pins the total case count — update it when
you add or remove a case.

**Housekeeping.** Tests leave nothing behind in the repo: no
`spawns/`, no `notes/`, no caches. Remove `__pycache__` before judging
a scope or untracked-file assertion.

## Backlog

The rename to phase names and the defect fixes are verified. The
additions below were implemented without tests; nothing here is proven
to work until its item is closed.

### 1. Make the existing suites green

Known or expected failures from the untested additions:

- [ ] `skills/spec-build/tests/test_delivery_pass.py` — a SyntaxError
      in the `calc.py` the fixture generates; the retro test; an INDEX
      fixture line in the old `— done (created …)` shape (~line 168).
- [ ] `tools/tests/test_release.py` — `INDEX_MD` fixture uses the old
      INDEX line shape and now draws a stale-index warning.
- [ ] `tools/tests/test_chain.py`, `test_dogfood.py` — any full-tier
      draft built by hand without NFR triage, `## Interfaces & data`
      and `### Rollout` now fails verify.
- [ ] Any test asserting a scaffolded INDEX line contains `(created`.
- [ ] `skills/spec-release/tests/run.sh` exits 1 until its tests
      exist (deliberate); `skills/spec-ship/tests/run.sh` is a
      placeholder that exits 0.

### 2. Reconcile before writing tests

- [ ] Refactor and upgrade specs: spec-design requires a TC line
      `- **Preserves**: <existing behavior>`; spec-build's delivery
      check requires a `Behavior preserved:` line in the delivery
      note. Confirm these are two halves of one rule, or align them.
- [ ] Work type reaches the developer two ways: the payload's
      `Work type:` line and the spec.md `**Type**:` header. Pick the
      one the developer brief keys on.
- [ ] Rollback rulings key on the bold labels of the plan's
      `### Rollout` bullets; the tech-spec rollback cell should invite
      a `TC-###`.
- [ ] `archive.sh` and the delivery-record step still edit
      `specs/INDEX.md` in place; `index.py` should be the one writer.
- [ ] **Decision needed.** spec-ship turns a red CI run or a must-fix
      PR comment into a spec-build fix round, but the engine reads any
      ticked task as done, so a delivered task cannot be reopened.
      Decide what reopening a delivered task means, then build it.

### 3. Tests to write — spec-define and spec-design

- [ ] spec-define `test_intent_flow.py`: `--repair constitution` is
      refused (exit 2) and names `/spec-design`.
- [ ] spec-define `test_intent_flow.py`: an intent that keeps the
      `NFR seeds` placeholder fails the gate.
- [ ] spec-design `test_graph.py`: `scaffold.sh` registers the spec
      through `index.py` (`— draft · feature · <tier>`).
- [ ] spec-design `test_check.py`: `Type: hotfix` at full tier warns.
- [ ] spec-design `test_check.py`: the overlap warning is suppressed
      when the other spec depends on this one.
- [ ] spec-design `test_check.py`: `index.py` leaves other lines
      untouched and exits 1 on a directory with no spec.md.
- [ ] spec-design `test_check.py`: a wrapped `not applicable` NFR
      skips coverage.

### 4. Tests to write — spec-build and spec-review

- [ ] `tick.py --park`: appends, never repeats, lists the spec's
      lines, and is refused alongside `--redeliver`
      (`test_delivery_pass.py`).
- [ ] `audit.py regression`: exit codes 1 and 3, and the `--dry-run`
      plan output (`test_delivery_pass.py`).
- [ ] Delivery gates: a refactor without `Behavior preserved:` fails;
      a `Docs impact:` line listing an unchanged file fails.
- [ ] The developer brief's work-type rule keys on the literal chosen
      in section 2.
- [ ] spec-review `test_gate.py`: `safety` is detected only as an
      invocation or a dependency spec.
- [ ] spec-review `test_review_orchestrator.py`: a pending CI row is
      shown but does not fail the gate.

### 5. Tests to write — spec-ship

`scripts/ship.py` has been syntax-checked only; it has never run.

- [ ] `preflight` rows and exit 4: dirty tree, default branch,
      `**Branch**` mismatch, undelivered spec, `commit @ -`, no
      remote, diverged branch; `gh` absent degrades instead of
      refusing.
- [ ] `pr-body`: the facts per tier, including `none —` lines.
- [ ] `record`: per tier, idempotent, and `check.py` plus
      `freeze.py --verify` stay green afterwards.
- [ ] `evidence`: round numbering, fencing, and the unrouted path
      (`notes/ship.md`).
- [ ] `checks` verdicts and `comments` parsing against a stub `gh`.
- [ ] Merge detection: merge commit, squash, rebase.
- [ ] `skill-dir.sh` resolution.

### 6. Tests to write — spec-release

`scripts/release.py` has been syntax-checked only; it has never run.
Use temp repos and a bare local remote.

- [ ] Tag families, and a first release with no prior tag.
- [ ] `collect`: which specs are included or excluded (unreachable,
      archived, already released) and commits outside the spec flow.
- [ ] The bump table, including the pre-1.0 rule.
- [ ] Finding and writing each version file; a dirty tree is refused.
- [ ] Changelog insertion: merging `Unreleased`, the link footer,
      heading style, and a new file.
- [ ] `notes --check` and `notes --body`.
- [ ] Every preflight row.
- [ ] `cut`: plan versus confirm; `check.py` stays green after the
      `Released:` record at both tiers.
- [ ] Publish: a rejected push, and no `gh`.
- [ ] `verify` records and the hotfix route; `status` next step.

### 7. Whole-kit pass

- [ ] Every check in § Running the checks exits 0.
- [ ] Walk each new skill's eval cases once in a scratch repo.
- [ ] An independent review of everything added since the defect
      fixes: gates that deadlock or can be bypassed, prose that
      disagrees with script output, and anything spec-ship or
      spec-release would do outward without the user's yes.
