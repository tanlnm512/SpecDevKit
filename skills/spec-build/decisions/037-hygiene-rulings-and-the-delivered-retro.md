# D-037: hygiene suspects take a recorded ruling, and the retro reflects the delivered state

Live eval runs (E7, E9) surfaced two delivery-pass gaps:

- `audit.py clean` flags a CLI's own `print(...)` lines as
  `[debug print]`, and dod gate 7 then read FAIL with no way to record
  that the lines are the product's output.
- The retro ran before the tick and C1, so retro.md listed every task
  open, nothing parked, and `Delivered: commit @ -`; archive reused
  that file because retro.py returns early when retro.md exists.
  The first retro also counted three fix rounds for one round: the
  notes file held `## Fix round 1`, `… — attempt` and `… — closed`
  headings, each counted.

**Decision**:

1. **Rulings live in the delivery block.** `- Hygiene: <path> [<kind>]
   — <ruling>` follows the block's existing `Rollback: <row> —
   <ruling>` shape, one line per path and kind as `clean` prints them.
   `audit.py clean <spec-dir>` prints a ruled suspect as RULED; dod
   gate 7 counts only unruled suspects and shows how many were ruled.
   Detection is unchanged: a suspect with no line still fails.
2. **The retro moves into C2.** The delivery pass runs retro.py once
   the ticks, parked lines and the `Delivered:` record are on disk and
   stages retro.md with the record commit. The old step 4 is gone and
   later steps renumber.
3. **A pre-delivery retro is refreshed.** retro.py still reuses an
   existing retro.md, except one stamped `Delivered: commit @ -` while
   the spec now records a commit SHA; that snapshot is rewritten.
4. **A fix round counts once.** The notes headings are counted by
   distinct round number.

**Consequences**: the delivery block gains an optional fourth line.
Archive's retro call reuses C2's file. Non-git specs, which legitimately
record `-`, are never rewritten.
