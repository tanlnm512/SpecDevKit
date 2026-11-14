# D-020: review runs checkpoint to a self-ignored run folder; a changed target refuses to resume

A full review is the scout, three lenses, triage per lens, a cross-lens
pass, one confirmer per kept finding, an assessment, and optional fix
rounds — often 10+ agent turns, all of it in conversation. A crash
restarted from zero; the only way back in was `fix_from` with a
finished report.

**Decision**:

1. **The run folder** is `<repo>/.spec-review/runs/<run-id>/`, created
   by `run-init` (run right after `scope`, with scope's args). It holds
   `run.json` — run_id, the target args, `base_sha`, `head_sha`,
   `diff_sha256` over the exact diff AND the untracked files scope
   lists, mode, creation time — and one `<stage>.json` per saved stage.
   Its own `.gitignore` contains `*`: a run is never committed and the
   user's `.gitignore` is never edited.
2. **`run-save --run-dir D --stage S --data @F`** writes one stage's
   JSON atomically (temp file + `os.replace`). The stage vocabulary is
   the oracle's `STAGES` tuple: `scope, scout, review-<lens>,
   triage-<lens>, crosslens, confirm-<F-id>, assessment, report,
   fix-<n>-{snapshot, fixer, check, gate, verify, review}` —
   `contracts/run-sequence.md` lists the same order, and a drift test
   keeps the two in step.
3. **`run-resume --run-dir D`** re-computes the fingerprint (the target
   re-resolves from the run record's own args). A mismatch is
   `status: error` — "target changed since the run started — start a
   new run (or continue from the saved report with fix_from)"; a stale
   resume would review a different change than the findings describe. A
   match returns `{completed, next, data}`: `next` is the first
   skeleton slot with no save (lens set = the saved scope's
   `fast_mode_default` → `general`, else every LENSES lens; confirm
   slots from the saved crosslens kept ids; `None` = the skeleton is
   exhausted, continue from the data).
4. **Confirmation stays independent on resume**: `run-resume` returns
   stage data to the ORCHESTRATOR, never into an `ask`. The ask
   builders keep choosing their own context — a resumed confirmer
   still never sees the scout map or the stated intent (panel.md says
   so explicitly).
5. **`run-gc --keep N`** (default 5) runs at `run-init`, so folders
   don't pile up; run names are date-prefixed, so name order is age
   order.

**Consequences**: every stage's oracle contract is unchanged (one JSON
object, `status ok|error`); the checkpointing adds three subcommands
and one folder. The fix loop's dynamic rounds save under their
`fix-<n>-*` names. A resumed run re-fetches `systems` and rebuilds
every ask exactly as a fresh run does.
