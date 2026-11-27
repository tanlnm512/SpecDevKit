# D-074: one schema per digest grammar — validate before reading, never parse by half

Every role's digest grammar was defined in prose and read loosely, or
not at all. The developer's line had the kit's one parser — a prefix
match that dropped unrecognized segments and took `status` as anything
up to the next middle dot (spec-build D-040); the architect's and the
analyst's lens digests and the tester's were written to files no code
read; the auditor's line had a second reader in `freeze.py` that kept
the BLOCK count and nothing else; the panelist's, the integrator's and
the release manager's blocks had no reader at all, so a digest with a
field missing or out of order was as readable as a good one.

**Decision**:

1. **`scripts/digests.py` is the one schema per digest grammar.** The
   line grammars — developer; architect tech, plan, tasks; analyst
   intent, research, constitution; tester; auditor — and the block
   grammars of the conversation-only roles — panelist per lens,
   integrator pr-text and threads, release-manager — are quoted there
   as data from the places that define them, never invented. The
   module joins the parity closure by import and ships byte-identical
   in every skill whose roles have a digest grammar; spec-review ships
   none (its roles return finding carriers the oracle already parses);
   `tools/tests/test_parity.py` pins every copy.
2. **`validate` returns a digest's problems; `parse` returns its
   fields only when there are none.** Strict: every key present, in
   order, no unknown key, every value of its kind; a block with a
   missing, unknown, or misordered top-level field is malformed.
   Tolerant only of leading markup on a line — review files quote the
   auditor line. A line value ends where the next key begins, so free
   text may hold the separator and a typed value may not.
3. **Every reader goes through the schema.** `specstate.latest_digest`
   returns three outcomes — valid, malformed (the file exists, its
   problems ride along), absent — and `mark.py land` refuses a
   malformed file that `--digest` cannot talk over (spec-build D-054).
   `freeze.py --approve` validates the auditor's line with the auditor
   grammar instead of the BLOCK-count regex and names the problems in
   its refusal.
4. **A signed record verifies on the BLOCK count it carries.** The
   review a record froze cannot be re-run without re-approving, which
   breaks a docset still in execution — the precedent that a docset
   approved before a rule existed does not go red mid-run. `--verify`
   therefore reads the folded line for its count; a line that carries
   none is still refused.
5. **The rule is stated once per skill** where the skill already
   states its digest contract (`protocol/shared-protocol.md` here and
   across the trio, `contracts/run.md` and `protocol/panel-protocol.md`
   in spec-discover, `contracts/run.md` in spec-ship and
   spec-release): every returned digest is validated with its schema
   before anything is read from it; a malformed digest is a
   fix-and-run-again refusal — the problems go back to the same agent
   and the spawn re-runs, never a fix round. The runnable form is
   `python3 <skill_dir>/scripts/digests.py validate <role>
   [<variant>] [file]` — exit 0 valid, 1 malformed with the problems.

**Consequences**: no script acts on a digest it has not validated
whole, and an agent that drops or mistypes a field is told which. The
costs: a schema stricter than what a brief's agents really write turns
correct digests into re-runs — every committed literal is valid, and a
grammar edit must be a schema edit in the one module, made in the
master and replicated. An unknown `name: value` line that follows a
multi-line field of a block digest is read as one more line of that
field, not named as an unknown field. A record signed before this
decision with a loose auditor line still verifies, by design.
