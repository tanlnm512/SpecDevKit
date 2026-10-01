## Engineering rules (kit-wide)

These bind every agent and orchestrator in this kit. A rule whose action
you never perform does not apply to you; the one whose action you are
taking right now binds absolutely.

### Before adding a test
- A test must protect observable behavior, a contract, or a credible
  regression. Use the smallest test that reliably proves it.
- Not every change needs a new test. Skip tests that only mirror small,
  reversible implementation changes; renames, copies, config, docs, and
  pure refactors usually need none. Cover only the paths the change
  puts at risk, not every failure or edge case.
- Each contract has one owner test at the strongest boundary. Prefer
  extending an existing case or table over a near-duplicate test; avoid
  combinatorial matrices.
- Do not create exports, wrappers, or seams that only tests use.
- Bug fixes: the regression test must fail on the pre-fix code for the
  intended reason.

### Long foreground tasks
A long foreground call may be auto-backgrounded by the harness; its
result arrives as a follow-up when the job finishes. NEVER poll a
backgrounded job (`sleep`, `ps`, `pgrep`, `top`) — do other work or end
your reply; you will be woken with its output. `timeout: 0` disables
the job deadline; otherwise the timeout sets the deadline without
extending foreground waiting.

### Strict code commenting
1. Do not comment on the obvious: never narrate what a line does or
   summarize loops, conditionals, or standard-library usage.
2. Self-documenting code first: if a comment feels needed to explain
   how code works, refactor instead — well-named locals over narration,
   intent-driven functions over long blocks.
3. Explain why, not what: comment only implicit business rules,
   non-obvious constraints, or tricky edge cases the code cannot show.
4. Minimal docstrings: concise docstrings only for public-facing module
   APIs, entry points, or primary export classes — none for internal
   helpers, private methods, or self-explanatory utilities.
5. Absolute brevity: an allowed comment is one line or a short, precise
   phrase — no conversational fluff.
6. No decision logs or stale data: never record why a change was made,
   what was changed or removed, alternatives considered, or task/PR/
   ticket references — git history owns that. Never embed volatile
   values (version numbers, dates, URLs, usernames, environment names,
   real payload examples) that will go stale.
