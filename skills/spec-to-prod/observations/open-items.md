# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. **Not yet run on a production repo.** Live end-to-end orchestration
   WAS validated in the 1.7.0 mission (two full pipeline runs in a
   scratch repo, 2026-09-09 — see the evals/cases.md header); the
   residual gap is one full run against a real, working repo.
   `evals/cases.md` E1–E2 remain the standing scenarios for it.
2. ~~**INSTALL.md deleted** (user, 2026-08-25). Restore-or-repoint
   pending — `tools/sync.sh` now mechanizes install, so a short INSTALL
   pointing at it may be enough.~~ Resolved 2026-09-10: root `README.md`'s
   Install section documents `tools/sync.sh` directly (now repo-root,
   shared across every skill) — no separate INSTALL.md needed.
3. **~/.claude skill copy is a real directory**, not a symlink (unlike
   sibling entries). Symlink conversion offered 2026-09-03, undecided —
   would make one edit propagate to both harnesses.
4. **Lower-rank competitor catalog open**: discovery routing + delta
   spec edits (cc-sdd/OpenSpec), cross-spec interface review (cc-sdd),
   sync tasks on spec change (Kiro), standards-extraction loop (Agent
   OS), line-level compliance matrix (CSDD — heavyweight).
5. **benchmarks/ intentionally absent**: no timed runs exist yet; create
   the dir when the first benchmark case is measured, not before.
6. **data/ intentionally absent**: the skill carries no runtime data;
   specs/context/ is generated per-project, not shipped.
