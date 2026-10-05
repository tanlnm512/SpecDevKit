# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. **E2–E6 not yet run on a production repo.** Live end-to-end
   orchestration is validated — twice in scratch repos at 1.7.0
   (2026-09-09), all six eval cases live on 2026-10-04 (scratch
   `/tmp` repos, transcripts in
   `specs/archive/2026-10-04-kit-level-up/notes/`), and the real-repo
   E1 happy path on this repo itself (2026-10-05, result in
   `evals/results/2026-10-05-e1.md` — its discovery fixed as 2.14.1's
   quoted-evidence residue bar). Remaining gap: E2–E6 on a real,
   working repo.
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
