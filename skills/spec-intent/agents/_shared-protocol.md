# Shared agent rules (prepended to every spawn)

Files on disk are the source of truth. You run independently — there is
no shared manifest, no sync log, and no peer-to-peer messaging with
whoever else is in this wave. Everything you need is in your own spawn
payload and the files it points you to; everything the orchestrator needs
back from you is your digest.

## Ownership is exclusive
Touch only the files you own: your one artifact (docs), or your task's
code/test files (implementers). If your work requires changing a file
someone else owns, do NOT edit it — report the gap in your digest instead;
the orchestrator re-briefs the owner.

## Your artifact is the deliverable
Your artifact on disk is the deliverable — not your reply. Ensure it is
complete before you stop; nothing you say back is read as the record.
Return your digest per your brief's contract.

## Universal rules (canonical — your brief does not repeat these)
1. **Citations verbatim** from survey.md, or from your own session's grep
   output — never from memory. A number in an existing doc is a claim;
   re-count it.
2. **Symbols over line numbers**; unknown → `unknown — verify`.
3. **Status lives only in task.md**, derived only from survey evidence — no
   checkboxes or status words in any other file.
4. **IDs (US/FR/AC/T/TC/D) are assigned once and never renumbered.** Dropped
   items are struck through with the `D-###` that killed them, never deleted.
5. **One file per agent.** You write exactly the artifact your brief names
   — nothing else.
6. **You never spawn agents, and you never commit or push.**

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
- Expected values come from an independent source of truth — a
  known-good literal, a worked example, or the spec — never from
  recomputing them with the same logic the code under test uses; a
  test whose assertion cannot disagree with the code proves nothing.
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
