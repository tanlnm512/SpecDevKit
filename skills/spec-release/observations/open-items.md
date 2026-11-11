# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. **No tests yet.** `tests/run.sh` exits 1 until the testing pass
   lands `tests/test_*.py`. Every script behavior in
   `contracts/run.md` is unproven until then; R1–R4 have never run
   live.
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
