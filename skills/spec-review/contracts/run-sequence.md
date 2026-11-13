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
| gate re-run | `O gate --base <merge_base or base> [--pr N]` (project: `--tree`) | the same `gate` object |
| prompts | `O systems`, once | system text per role; `lenses[]`, `general` |
| asks | `O ask --kind K --ctx @ctx.json` — `{"batch": [{kind, ctx}, …]}` renders a wave | one ask per spawn |
| ids | `O id-next --prefix <lens> --used N` | the id minted at confirmation |
| fix_from | `O findings-parse --file F` | `tracked[]` |
| fix guard | `O fix-snapshot` before each fixer turn; `O fix-check --head H --stash-count N --tree T` after it | error `fixer-moved-head` / `fixer-touched-stash` → abort the loop and report it; `test_hunks` → the verify and fix-review ctx |
| report | `O report --kind review\|fix --data @report.json` | `markdown`, `reported_findings`, `backlog_offer` |

Ask ctx keys (`gate_line` = the gate object's `note`):

- `scout`: base, project, files, repo_abs
- `review`: base, files_n, lines, over_cap, untracked, lens (a
  `systems.lenses` entry, or `systems.general` in fast mode),
  gate_line, intent, scout_map
- `review-project`: files (one part), part, parts, candidates, lens,
  gate_line, repo_abs, scout_map
- `triage` / `triage-project`: base, lens_label, findings, intent
- `cross-lens`: base, kept
- `confirm` / `confirm-project`: base, finding, untracked — never
  intent or scout_map
- `final` / `final-project`: base, summary, gate_line, untracked,
  intent, scout_map (project: files, repo_abs)
- `fixer`: round, project, base, unresolved, intent, repo_abs,
  gate_feedback (round ≥ 2)
- `verify`: tracked (one item), project, base, notes, repo_abs,
  test_hunks
- `fix-review`: paths, base, gate_green, repo_abs, test_hunks
- `loop-final`: tracked, rounds_used, gate_green, changed_paths,
  project, base, scout_map

Report data: title, mode_line, tracked[] (`{finding: {id, where,
what, evidence, severity, lens, impact, confirmation: {status, note,
self_checked}}, fix, fixNote}`), gate_rows (verbatim — keep
`source` and `status`), gate_green, repo_abs, backlog_label (the
spec or branch name for `backlog_offer`), assessment `{verdict, testGaps,
residualRisks}`, dropped[], checked[], fix_checked[], rounds_used,
fixer_notes[], conclusion. `fix` is one of `pending` (default when
absent or null), `fixed`, `unfixed`, `worse`.

**Who runs each role** — a fresh spawn per ask, never the instance
that wrote what it now judges:

| Role | Agent type |
|---|---|
| Scout | `review-scout` |
| Lens reviewer | `review-correctness` / `-security` / `-quality` (fast mode: one of them with the `general` lens) |
| Fixer | `review-fixer` — the only role allowed to write |
| Triage editor, final assessor | `review-quality` (read-only), with `systems.triage` ahead of the ask |
| Confirmer, fix verifier | a read-only lens type — for a confirmer, not the finding's own lens — with `systems.verify` ahead of the ask |
| Fresh-eyes fix reviewer | a read-only lens type with `systems.fix_review` ahead of the ask |

**Mode** — `auto` (default) is `fast` when scope's
`fast_mode_default` holds (≤ 400 added lines and ≤ 5 files), else
`full`. `full`: the three lens spawns, per-lens triage, cross-lens
pass, one independent confirmer per kept finding. `fast`: one general
reviewer and inline confirmation, so every finding is `unconfirmed
(self-checked)`. Without subagent dispatch every mode confirms inline.

**Order**:

1. `scope … --include-gate`. No files → "nothing to review". pr mode
   with `gate_deferred` (a fork PR): tell the user the gate runs the
   PR author's code and run `O gate` only on their go-ahead. Project
   mode with `confirm_before_spawn`: print the part count and
   `reviewer_spawns`, then wait for a go-ahead or narrower `paths`;
   name `excluded` under notCovered.
2. Gate red → stop (except a project audit and fix_from).
   `repo_checks: 0` → find and run the documented check command
   (README, CI config, AGENTS.md) or report "no repo checks detected".
3. `systems`; the scout ask → the scout.
4. The review wave (`batch`; project mode: every lens × every part).
5. Triage per lens → cross-lens → confirm each kept finding.
6. The final ask → `report --kind review`. `backlog_offer` present
   (the repo keeps `specs/BACKLOG.md`) → offer its residual-risk lines
   for that file; append only on the user's yes.
7. Fix loop, per round: `fix-snapshot` → fixer → `fix-check` → `gate`
   → verify each finding → fix-review → next round; then `loop-final`
   → `report --kind fix`.
8. pr mode with `previous_ref`: `git checkout <previous_ref>` once the
   report is out, or tell the user the PR head is still checked out.
