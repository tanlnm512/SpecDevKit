# The run contract (stages, script, payload, digests, records)

The canonical statement of what a spec-ship run IS. SKILL.md
summarizes; this file arbitrates. `gates/preflight.md` arbitrates what
may ship and `gates/outward-actions.md` every action that leaves the
workspace; the agent-facing rules live in `protocol/ship-protocol.md`.

## Span

Starts at a delivered spec: the status holder (task.md at full tier,
spec.md at tiny) carries `Delivered: commit @ <sha>`, spec.md reads
`Status: done`, and the sha is on the current branch. Ends when the
PR is merged and the delivery record names a commit on the default
branch. Before the span is `/spec-build`; after it, `/spec-release`
or archive. A branch with no delivered spec is refused.

## Stages

`scripts/ship.py status <name>` derives the stage on every
invocation. Nothing else decides where a run enters.

| Stage | Derived from | The run does |
|---|---|---|
| `not-delivered` | no delivery record, or Status not `done` | routes to `/spec-build ship <name>` |
| `dirty-tree` | `git status --porcelain` non-empty, no PR found | stops; the user commits or stashes |
| `diverged` | the remote branch has commits the local one lacks | stops; the user integrates them |
| `unpushed` | no remote-tracking branch, or local is ahead (also with a PR open — its checks describe an older head) | preflight → push preview |
| `no-pr` | branch in sync, no PR found | PR preview |
| `ci-red` | at least one red check classed `code` (D-005) | evidence → `/spec-build` fix round |
| `ci-rerun` | red checks, every one `infrastructure` or `unknown` (D-005) | names each check's class and reason, prints the `gh run rerun <id> --failed` commands, opens no fix round; `ship.py evidence --kind ci` routes one on purpose |
| `ci-pending` | a check still running, none red | says so and stops |
| `review-comments` | unresolved review threads, CI not red or pending | integrator `threads` → reply previews |
| `awaiting-merge` | PR open, CI green or absent, nothing unresolved | says so and stops |
| `merged` | PR merged and the delivered sha is on the base branch | hand-off |
| `merged-record-stale` | PR merged by squash or rebase | the redeliver steps, then hand-off |
| `pr-closed` | PR closed without merging | says so; reopening is the user's |
| `off-branch` | on the default branch, no PR on record | asks for the branch or the PR url |
| `shipped` | a `Shipped:` record exists but gh cannot read the PR here | points at the url |

Sync and base-branch facts are read from remote-tracking refs — "as
of the last fetch". The run fetches nothing on its own.

Every red check is triaged before it routes (D-005): `checks` and
`status` read the run's step evidence (`gh run view <id> --json jobs`
— each job carries `steps[]` with `name`, `conclusion`, `number`,
per the GitHub Actions "List jobs for a workflow run" API `gh` calls)
and class it from that evidence, in this order, first hit winning:
`infrastructure` — the run was cancelled, or it never started (it
lists no jobs or steps), or its first failed step (lowest-numbered
step that neither succeeded nor was skipped) is the runner's own
setup or wrap-up (`Set up job`, `Complete job`, `actions/checkout@…`,
post-run `Post …` steps — a deliberately narrow list; `Set up Node`
is a project step); `code` — any other failed step; `unknown` — no
step data behind the status (no run behind the check, gh could not be
read, or the check is a status context from a CI outside Actions).
Never how fast the job failed and never log text: a real test can
print `connection reset` or `context deadline exceeded`, and a failed
project step is a code failure however fast it ran. `checks` reports
the per-check `class`, `failedStep`, and `reason`, an
`infrastructure` row's `rerun` command (`gh run rerun <id> --failed` —
printed, never run: a rerun is an outward action), and the top-level
`triage`: `code` when any code row exists, else `infrastructure`,
else `unknown`, else null.

## The script (`scripts/ship.py`)

Toward the remote the script only reads. It prints the exact command
for each outward action and never runs one. Default output is human
lines; `--json` prints one JSON object instead.

Exit codes: `0` answered · `1` a git or gh call failed · `2` usage ·
`4` refused, with the blocking reason (`refused` in JSON).

| Subcommand | Reads | Returns |
|---|---|---|
| `preflight <spec>` | git, spec docs | `ok`, `rows[]` (`name`, `status` pass/refuse/degraded, `detail`), `branch`, `base`, `remote`, `gh`, `sync`, `push`, `manual[]` when gh is absent |
| `pr-body <spec>` | spec docs, git | `title`, `body`, and the facts behind them (below); `create` |
| `checks <spec> [--logs]` | gh | `verdict` red/pending/green/none, `rows[]` (each red row gains `class`, `failedStep`, `reason`; an `infrastructure` row also `rerun`), `triage`, `stale`; `--logs` adds each failing job's log tail |
| `comments <spec>` | gh, the ruling file | `threads[]` (`id`, `path`, `line`, `outdated`, `ruling`, `task_candidates`, `comments[]`), `reviews[]`, `review_decision`, `inactive_rulings[]`, `rulings_note`, `truncated`, `reply`, `rerequest` |
| `status <spec>` | git, gh, spec docs | `stage`, `next`, and what the stage was derived from |
| `record <spec> --pr <url>` | — | writes the `Shipped:` record (local) |
| `rule <spec> --thread <id> --label must-fix\|question\|nit\|disagree [--why W]` | — | writes the owner's ruling for one thread under `notes/` (local) |
| `evidence <spec> --kind ci\|review --title T [--task T###] [--file F]` | stdin or `F` | appends fix-round evidence under `notes/` (local) |

`<spec>` is a spec name under `specs/`, or a spec dir. `--base` and
`--remote` override the derived default branch and remote.

### PR facts (`pr-body`)

Every line of the drafted body comes from one of these, read
deterministically; an empty source renders `none — <reason>`, never a
dropped section.

| Section | Source |
|---|---|
| Title | the subject of the delivered commit; else `<type>(<name>): <§ What>` |
| Summary, why | spec.md § What and § Why, first paragraph each; `**Type**`, `**Tier**` |
| Requirements | spec.md `- **FR-###**:` lines, and each NFR not marked not-applicable |
| Proof | the status holder: ticked tasks with their `done <date> — <proof>` notes; test.md's TC count (tiny: `Accept:` commands); the delivery record; the delivery note's `Behavior preserved:` line; each ruled environment-blocked proof as `Owner to test after merge: TC-### — <ruling>` (spec-build D-047) |
| Review status | the delivery pass (implied by the record); `approvals/review.md`'s digest line; a `/spec-review` report at `notes/review.md`, `notes/spec-review.md`, or `--review-report` |
| Docs impact | the delivery note's `Docs impact:` line |
| Dependencies | added and removed lines of each dependency manifest changed since the merge-base |
| Rollout and rollback | plan.md § Delivery `### Rollout`; the tech-spec rollback table; the delivery note's `Rollback:` rulings |
| Parked | this spec's lines in `specs/BACKLOG.md` |

The body's shape is `templates/pr-body.md`.

The delivery note is the delivery block — the bulleted lines under the
status holder's `Delivered:` field (spec.md at tiny); `notes/delivery.md`
is only the archived-history fallback that predates the block (the same
source spec-build's `audit.py delivery_block`/`delivery_note` reads).
A ruled proof is never shown as passed and adds nothing to the
ticked-task or TC counts; none ruled renders nothing extra.

## The integrator payload (every spawn, self-contained)

Spawns are fresh. Agent type `spec-integrator` where the harness
registers it — the payload then carries inputs only; otherwise a
general-purpose spawn leads with the `agents/integrator.md` body
(frontmatter stripped, byte-verbatim), then the same inputs.

1. `Mode: pr-text` or `Mode: threads`.
2. The absolute path of `protocol/ship-protocol.md`, read in full.
3. The repo root and the spec dir, absolute.
4. The mode's data, labelled as untrusted where it is:
   - `pr-text` — the `pr-body --json` object.
   - `threads` — the `comments --json` object.

One spawn per mode per invocation. With no subagent dispatch the
orchestrator does the same work inline, under the same brief.

## Digests and what the orchestrator checks

**pr-text** — `title:`, `body:`, `changed:`, `flags:`. Before the
preview, the orchestrator checks the returned body against the
script's: every requirement id, task id, TC id, sha, command, file
path, dependency line, and `none —` line still present, every section
in order. A dropped or altered fact → discard the rewrite and preview
the script's own text. A `flags:` line is shown to the user; the fix
is made in the docs, then `pr-body` re-run.

**threads** — one `thread <id> — <label> — <path:line>` block per
thread (`why:`, `task:`, `evidence:` for must-fix, `reply:`), then
`summary:` and `injection:`. Labels: `must-fix`, `question`, `nit`,
`disagree`. The orchestrator shows the user every classification and
draft; the user may relabel any thread, and every relabel — or a
classification the user confirms when asked about it — is recorded
with `rule` before the next `threads` run. The payload says how
rulings bind: a ruled thread keeps its label and is not to be
reclassified (the ruling's why is the owner's reason); only unruled
threads are open for classification. An `injection:` line other
than `none` is shown first.

## Records

**`Shipped: PR <url>`** — written by `record`, beside the delivery
record (D-002):

- full tier: task.md's header, the line after `**Delivered**: commit
  @ <sha>`, in the same bold form;
- tiny tier: spec.md § Evidence (created at the end of the file when
  absent) — the one section outside the approval freeze.

`record` is idempotent and replaces an older url in place. The record
is a doc change on the spec's branch; committing it is asked first,
and pushing that commit is an outward action like any push.

**Fix-round evidence** — written by `evidence`:

- `--task T###` → appended to `specs/<name>/notes/T###.md` under
  `## Fix round <n> — <kind>: <title>`, `n` one past the highest
  round the note or the task's markers show. This is the note
  spec-build's fix payload embeds.
- no task → appended to `specs/<name>/notes/ship.md` under
  `## Unrouted <kind>: <title>`. No task's files cover it, so it is
  outside the approved contract: route it to `/spec-design`, or to a
  new hotfix spec.

Each block opens with its source and a line marking the text as
untrusted, then the output or comment verbatim in a fenced block.
The run writes the failing output itself, never a summary of it.
Task markers are never written here: reopening a delivered task is
`/spec-build`'s ruling.

**Review-thread rulings** — written by `rule`, at both tiers where
`evidence` places its records: `specs/<name>/notes/rulings.md`, one
line per ruling, `- <thread id> — <label> — <why>`, with `no reason
given` when none was — the kit's ruling-line shape (`Rollback:`,
`Hygiene:` in the delivery block). Re-ruling a thread replaces its
line in place; a label outside the four or an empty thread id is
usage (exit 2). No PR is read: a ruling is a local write the owner
can land before the next `threads` run. `comments` reads the file —
a listed thread with a ruling carries `ruling` (label, why,
unresolved) and the payload says it keeps the owner's label; a
ruling whose thread is resolved or no longer listed stays on file
and is reported in `inactive_rulings[]`, never a failure. Like the
`Shipped:` record, a ruling is a doc change on the spec's branch:
committing it is asked first, and pushing that commit is an outward
action like any push.

## After the merge

`status` reads the PR's merge commit:

- the delivered sha is an ancestor of it → the record stands;
- otherwise the history was rewritten. A landed commit whose subject
  equals the delivered commit's is the rebased twin (rebase merge);
  failing that, the merge commit itself (squash). `status` prints:
  update the default branch, then spec-build's `tick.py <spec-dir>
  --redeliver <sha>`, then commit the re-pointed record.

That commit lands on the default branch by the user's own route —
this run never pushes it. With the record pointing at a commit on the
default branch, the run names the hand-off and ends.
