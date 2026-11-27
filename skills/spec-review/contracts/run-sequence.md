# Run sequence — driving the oracle

The command-level statement of a review run: SKILL.md § Run
sequence summarizes it; this file arbitrates the commands, the ask
context keys, the report data, and the order.

`O` = `python3 <skill-dir>/scripts/review_orchestrator.py`. Every call
prints one JSON object; `status: error` stops the run, naming its
`stage`.

| Phase | Command | Read from the result |
|---|---|---|
| scope + gate | `O scope --target diff\|branch\|pr\|project [--base R] [--pr N] [--repo D] [--paths P] --include-gate` | `files` (tracked + `untracked`), `added`, `fast_mode_default`, `suggest_split`, `gate{rows, green, repo_checks, note}`; pr: `previous_ref`, `gate_deferred`; project: `parts`, `excluded`, `reviewer_spawns`, `confirm_before_spawn` |
| checkpoint | `O run-init --target …` (scope's args) right after scope; `O run-save --run-dir D --stage S --data @F.json` after EVERY stage | `run_dir` (also in every later result); a crash mid-run resumes (see Resume) |
| gate re-run | `O gate --base <merge_base or base> [--pr N]` (project: `--tree`) | the same `gate` object |
| prompts | `O systems`, once | system text per role; `lenses[]`, `general` |
| asks | `O ask --kind K --ctx @ctx.json` — `{"batch": [{kind, ctx}, …]}` renders a wave | one ask per spawn |
| tools report | `O handshake --role R --file F` on every reply before anything else in it is read; a reviewer's reply: `O findings-parse --role R --file F` (R: § Who runs each role) | `{tools, reply}` — the reply past its tools line; `status: error` with stage `handshake` is a failed call (§ A failed call is not a round) |
| ids | `O id-next --prefix <lens> --used N` | the id minted at confirmation |
| fix_from | `O findings-parse --saved-report --file F` — the previous report's markdown or its findings JSON, declared a saved report; a payload handed over with neither `--role` nor `--saved-report` is refused | `tracked[]` |
| fix guard | `O fix-snapshot` before each fixer turn; `O fix-check --head H --stash-count N --tree T` after it | error `fixer-moved-head` / `fixer-touched-stash` → abort the loop and report it; `test_hunks` → the verify and fix-review ctx |
| report | `O report --kind review\|fix --data @report.json` | `markdown`, `reported_findings`, `backlog_offer`; kind fix also `derived_conclusion` (D-021: a `conclusion` below it is an error — re-run `report` with a claim at or above the floor) and `stopAsk` (D-024, null when nothing waits on judgment): put it to the user through the harness's structured question tool where one exists — the options as choices, a recommended one first and marked — otherwise print it, and stop: an unanswered ask is not an answer (spec-define D-018) |

**Stage order** — the `--stage` vocabulary and the run's checkpoint
order; the oracle's `STAGES` tuple is the executable form and a drift
test keeps the two in step:

```
scope, scout, review-<lens>, triage-<lens>, crosslens, confirm-<F-id>,
assessment, report, fix-<n>-{snapshot, fixer, check, gate, verify, review}
```

`<lens>` is a lens label (`correctness|security|quality`, or
`general` in fast mode), `<F-id>` a confirmed finding's id, `<n>` the
fix round. **Resume** — a crashed run continues instead of restarting:
`O run-resume --run-dir D` re-computes the target's fingerprint; a
changed target is refused (`status: error`, start a new run — or
continue from the saved report with `fix_from`), a match returns
`{completed, next, data}` and the run continues at `next`, replaying
`run-save` after every stage from there. The stage data goes back to
the ORCHESTRATOR, never into an `ask` — the ask builders keep choosing
their own context (D-020, panel.md), so a resumed confirmer still
never sees the scout map or the stated intent.

**A failed call is not a round** — a fixer, reviewer or verifier
spawn that returned nothing usable (a rate limit, a timeout, a lost
session, a permission prompt nobody answered), or whose reply the
handshake refused (stage `handshake`: its tools report lacks a tool on
the role's brief `tools:` line, or opens with none), opens no fix round
and changes no finding's status; the orchestrator runs the same stage
again, counts these retries against a bound of three per stage, and at
the bound stops and tells the owner which stage, which error and how
many times. A refusal by policy is final: report it, never work
around it. A gate or ask that refuses because of what an agent
produced is not final: fix what it names and run it again — and
neither is a call refused for what the caller left out: a payload
handed to `findings-parse` undeclared is declared and handed over
again.

Ask ctx keys (`gate_line` = the gate object's `note`):

- `scout`: base, project, files, repo_abs, run_dir
- `review`: base, run_dir, files_n, lines, over_cap, untracked, lens (a
  `systems.lenses` entry, or `systems.general` in fast mode),
  gate_line, intent, scout_map
- `review-project`: files (one part), part, parts, candidates, lens,
  gate_line, repo_abs, scout_map, run_dir
- `triage` / `triage-project`: base, lens_label, findings, intent
- `cross-lens`: base, kept
- `confirm` / `confirm-project`: base, finding, untracked — never
  intent or scout_map (a diff-shaped `confirm` also carries `run_dir`)
- `final` / `final-project`: base, summary, gate_line, untracked,
  intent, scout_map (project: files, repo_abs; a diff-shaped `final`
  also carries `run_dir`)
- `fixer`: round, project, base, unresolved, intent, repo_abs,
  gate_feedback (round ≥ 2) — `unresolved` never carries an
  `out-of-scope` item (it waits on the user, not on a round) or a
  `rejected-valid` one (withdrawn)
- `verify`: tracked (one item), project, base, notes, repo_abs,
  test_hunks — a skipped item is RULED on here (D-022:
  `rejected-valid` | `rejected-invalid`, never a fix verdict)
- `fix-review`: paths, base, gate_green, repo_abs, test_hunks, run_dir
- `loop-final`: tracked, rounds_used, gate_green, changed_paths,
  project, base, scout_map (a diff-shaped target also `run_dir`)

A reader holds no shell (D-028), so every ask but `fixer`'s names a
file, never a git command: the oracle writes the diff, the change to
one path and the file lists into `<run_dir>/reader-files/` when it
renders the ask. An ask with no run folder is `status: error` naming
stage `ask`; a diff that cannot be produced is a named absence in the
ask.

Report data: title, mode_line, tracked[] (`{finding: {id, where,
what, evidence, severity, lens, impact, confirmation: {status, note,
self_checked}}, fix, fixNote}`), gate_rows (verbatim — keep
`source` and `status`), gate_green, repo_abs, backlog_label (the
spec or branch name for `backlog_offer`), assessment `{verdict, testGaps,
residualRisks}`, dropped[], checked[], fix_checked[], rounds_used,
fixer_notes[], conclusion, changed_since (fix runs only: what changed
since the last fix attempt, recorded when the workflow observed one —
a skip the owner overturned, a hand fix; it alone makes another fix
round an option in the stop ask, D-024). `fix` is one of `pending` (default when
absent or null), `fixed`, `unfixed`, `worse`, `rejected-valid`,
`rejected-invalid`, `out-of-scope` (D-022: `fixed` and `rejected-valid`
resolve a finding; a carried item already resolved is dropped at
parse). `conclusion` (fix runs) is checked against the derived floor
(D-021, `gates/recommendation.md`): below it the call errors; at or
above it the claim stands; absent it is filled with the floor.

**Who runs each role** — a fresh spawn per ask, never the instance
that wrote what it now judges. The last column is the `--role` every
reply of that role is handed over with — the brief the spawn ran on:

| Role | Agent type | `--role` |
|---|---|---|
| Scout | `spec-review-scout` | `scout` |
| Lens reviewer | `spec-review-correctness` / `spec-review-security` / `spec-review-quality` (fast mode: one of them with the `general` lens) | the one spawned: `correctness`, `security` or `quality` |
| Fixer | `spec-review-fixer` — the only role allowed to write | `fixer` |
| Triage editor, final assessor | `spec-review-quality` (read-only), with `systems.triage` ahead of the ask | `quality` |
| Confirmer | `spec-review-confirmer` — the brief `agents/spec-review-confirmer.md`, whose body `O systems` returns as `systems.confirm`, ahead of the ask | `confirmer` |
| Fix verifier | `spec-review-verifier` — the brief `agents/spec-review-verifier.md`, whose body `O systems` returns as `systems.verify`, ahead of the ask | `verifier` |
| Fresh-eyes fix reviewer | a read-only lens type with `systems.fix_review` ahead of the ask | the lens type spawned: `correctness`, `security` or `quality` |

**Mode** — `auto` (default) is `fast` when scope's
`fast_mode_default` holds (≤ 400 added lines and ≤ 5 files), else
`full`. `full`: the three lens spawns, per-lens triage, cross-lens
pass, one independent confirmer per kept finding. `fast`: one general
reviewer and inline confirmation, so every finding is `unconfirmed
(self-checked)`. Without subagent dispatch every mode confirms inline.

**Order**:

1. `scope … --include-gate`, then `run-init` with the same args (the
   checkpoint starts here; `run-save --stage scope` right after). No
   files → "nothing to review". pr mode with `gate_deferred` (a fork
   PR): tell the user the gate runs the PR author's code and run
   `O gate` only on their go-ahead. Project mode with
   `confirm_before_spawn`: print the part count and
   `reviewer_spawns`, then wait for a go-ahead or narrower `paths`;
   name `excluded` under notCovered.
2. Gate red → stop (except a project audit and fix_from).
   `repo_checks: 0` → find and run the documented check command
   (README, CI config, AGENTS.md) or report "no repo checks detected".
3. `systems`; the scout ask → the scout; `run-save --stage scout`.
4. The review wave (`batch`; project mode: every lens × every part);
   `run-save --stage review-<lens>` per lens result.
5. Triage per lens (`run-save --stage triage-<lens>`) → cross-lens
   (`run-save --stage crosslens`) → confirm each kept finding
   (`run-save --stage confirm-<F-id>` each).
6. The final ask → `report --kind review` (`run-save --stage
   assessment` for the assessment, `--stage report` for the report).
   `backlog_offer` present (the repo keeps `specs/BACKLOG.md`) →
   offer its residual-risk lines for that file; append only on the
   user's yes.
7. Fix loop, per round n: `run-save --stage fix-<n>-snapshot` →
   fixer → `fix-<n>-check` → `fix-<n>-gate` → verify each finding
   (`fix-<n>-verify`) → fix-review (`fix-<n>-review`) → next round;
   then `loop-final` → `report --kind fix`.
8. pr mode with `previous_ref`: `git checkout <previous_ref>` once the
   report is out, or tell the user the PR head is still checked out.

**Resume** (a session killed mid-run): run `O run-resume --run-dir D`
for the latest run dir. `status: error` naming a changed target → the
diff moved; start a new run (or continue from the saved report with
fix_from). A match returns `completed`, `next` and every saved stage's
`data`: re-fetch `systems`, then continue AT `next` — re-running no
saved stage, `run-save`-ing each result from there as in the order
above. The saved data goes back to the orchestrator only; asks are
rebuilt through `ask` exactly as a fresh run builds them.
