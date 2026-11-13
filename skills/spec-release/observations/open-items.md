# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. ~~**No tests yet.**~~ — `tests/test_release.py` proves the script
   behaviors `contracts/run.md` names, and R1–R4 ran live on
   2026-11-13 (results under `evals/results/`): R1, R2, and R4 passed
   every criterion; R3 failed one (item 9).
2. **check.py does not verify `Released:`.** `Delivered:` shas get
   existence and ancestry checks (check.py's lifecycle integrity);
   `Released:` and `Post-release check:` lines are inert to it. Adding
   a `released` entry to specstate's lifecycle values is a closure
   change in spec-design, owned there.
3. **No smoke marker in the docset templates.** `verify` reads a test
   case as smoke-worthy when its title says "smoke" or it carries a
   `**Smoke**:` line (tiny tier: a task whose block says "smoke"). No
   template offers either yet, so most checklists carry only the
   plan's `Post-release check`. A spec-design template change.
4. **One version per repo.** Monorepos with a version per package
   (this kit's own `skills/*/VERSION`) are out of scope: sources are
   read at the repo root, and `__version__` up to three levels deep.
5. **CI is read through gh only.** Other CI systems degrade to a WARN
   and a by-hand confirmation. `gh run list --commit` sees GitHub
   Actions runs, not third-party status checks.
6. **Must-fix backlog detection is a keyword heuristic** (must-fix,
   BLOCK, blocker, security, critical, high). `specs/BACKLOG.md`
   lines carry no severity field.
7. **Unsigned tags.** `cut` makes annotated tags; a project that signs
   tags (`git tag -s`) signs by hand today.
8. **No telemetry.** The other skills record local, content-free
   counts; this one records none yet.
9. **The changelog is written before it is shown** (R3, 2026-11-13).
   Step 3 runs `notes <v> --write` and then shows the section, so on
   a repo with no changelog the file exists, uncommitted, before the
   user has seen its content. R3's criterion asks for the reverse.
   Either the run shows a dry `notes <v>` first, or the criterion
   follows the contract — undecided.
10. ~~**The tag message loses its group headings**~~ — (R1,
    2026-11-13) `cut` now tags with `--cleanup=verbatim`, so `### Added`
    and its siblings stay in the tag message.
11. **Scratch-only eval corpus** — accepted limitation: R1–R4 ran in
    scratch repos with a bare local remote, so the GitHub release
    step ended in its documented failure path and no real-repo
    release run is recorded.
