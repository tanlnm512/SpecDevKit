# The run contract (steps, script interface, facts, section, record)

The canonical statement of what a spec-release run IS. SKILL.md
summarizes; this file arbitrates. `gates/preflight.md` arbitrates
whether a version may be cut; `gates/cut.md` arbitrates the two
yeses. The shared role rules live in `protocol/release-protocol.md`.

## Steps

| Step | Script | Writes | Ends when |
|---|---|---|---|
| collect | `release.py collect` | nothing | the facts are shown; exit 3 ends the run ("nothing to release") |
| version | `release.py version` | nothing | the user confirms or overrides the proposed version, and rules any disagreeing version source |
| bump | `release.py bump <v> [--only F,…] --write` | the version files | every source the user kept reads `<v>` |
| notes | `release.py notes <v> --write` → release manager → `notes <v> --check` | the changelog | the user accepts the section and `--check` exits 0 |
| preflight | `release.py preflight <v>` | nothing | every row passes, or each red row is fixed and the gate re-run |
| cut | `release.py cut <v>` → yes → `--confirm <tag>` | release commit, annotated tag, record commit | `cut` exits 0 after `--confirm` |
| publish | `release.py publish <tag>` → yes → `--confirm <tag>` | pushes, the GitHub release | `publish` exits 0 after `--confirm` |
| verify | `release.py verify <tag>` → human checks → `--outcome … --write` | the outcome line | the user reports the outcome; a fail routes to a hotfix spec |

Every verb re-derives its state from git and the doc state. The
default run asks `release.py status` for the next step and continues
from there.

## Exit codes

| Code | Meaning | One-line reason names |
|---|---|---|
| 0 | ok, or the gate is green | — |
| 1 | the gate is red (preflight, `notes --check`, an unreachable delivery record in collect) | each failing row |
| 2 | usage or environment: not a git repo, no commits, a bad version, a missing tag, a plan/confirm mismatch, an existing section | the problem |
| 3 | nothing to release since the last tag | the last tag |
| 4 | refused: a dirty tree, a detached HEAD, a git or gh step that failed mid-cut or mid-publish | the step and git's own reason |

Errors print `ERROR: <reason>` on stderr. `--json` prints one JSON
object on stdout for every exit but 2 and 4.

## The facts (collect JSON)

- `range` — `<last-tag>..HEAD`, or `HEAD` for a first release.
- `tag` — `prefix` (the tag family in use: `v`, empty, `pkg-v`, …),
  `last_tag`, `last_version`, `families`, `note` (several families or
  none — the user picks with `--tag-prefix`).
- `included` — delivered specs, live or archived, whose `Delivered:
  commit @ <sha>` is reachable from HEAD, not reachable from the last
  tag, and that carry no `Released:` line. Each: `name`, `path`,
  `archived`, `tier`, `type` (absent reads feature), `status`,
  `title`, `what` (§ What's first sentence), `frs`, `holder`,
  `delivered`, `breaking` (each marker with its source line),
  `delivery_note` (`docs_impact`, `rollback`, `behavior_preserved`),
  `rollout` (plan.md § Delivery `### Rollout`: `none` or labelled
  `items`), `rollback_table` (tech-spec's rollback column, filled
  rows), `smoke` (smoke-tagged test cases), `backlog`, `commits`.
- `unreachable` — a delivery record whose commit is not an ancestor of
  HEAD (a squash-merge or rebase replaced it): re-point it with
  spec-build's `tick.py --redeliver` (`/spec-ship` does this after a
  squash-merge). Collect exits 1 while any remain.
- `untraceable` — delivered without git (`commit @ -`); listed, never
  included.
- `in_flight` — undelivered specs with commits in range; a warning.
- `outside` — commits in range that no included or in-flight spec owns
  and that touch more than `specs/`, less this skill's own
  `chore(release):` commits. A commit belongs to a spec when it is the
  delivery commit, its subject carries `(<spec-name>)` or the scope
  `<spec-name>`, or it touches the spec's dir.
- `deps` — added and removed lines of dependency manifests between the
  last tag and HEAD (none on a first release).
- `backlog` — the included specs' `specs/BACKLOG.md` lines.
- `notes` — what the run must say out loud: no `specs/` dir (nothing
  traced), a first release, a dirty tree.

## The bump

| Included work | Level |
|---|---|
| any breaking marker — a spec's `**Breaking**:` line or a `**Compatibility**:` bullet naming a break, a commit with `!:` or a `BREAKING CHANGE:` footer | major |
| a `feature` spec, a `feat` commit outside the flow | minor |
| `bugfix`, `hotfix`, `refactor`, `upgrade` specs; any other commit | patch |

The highest level wins. Before 1.0.0 a breaking change bumps minor
(SemVer §4); 1.0.0 is always the user's call. A last tag that is a
pre-release proposes its final version. With no tag, the version
already written in the project is proposed as the first release, else
0.1.0. Every version source is listed — `VERSION`, `package.json`,
`pyproject.toml` (`[project]` or `[tool.poetry]`; `dynamic` is listed
as unwritable), `Cargo.toml` (`[package]` or `[workspace.package]`),
`__version__` in `__init__.py`/`_version.py`/`version.py`/
`__about__.py` up to three levels deep. Sources that disagree are
shown; the user rules which ones `bump` writes (`--only`).

## The changelog section

The changelog is the first of `CHANGELOG.md`, `CHANGELOG`,
`CHANGES.md`, `HISTORY.md` at the repo root; none → `CHANGELOG.md`
from `templates/changelog.md`, created only by `notes --write`.

- **Heading**: the newest version heading is the model — its version
  and ISO date replaced; none → `## [<version>] - <date>`.
- **Placement**: an `Unreleased` heading stays, empty; its entries move
  into the new section verbatim, merged under the same group headings
  (the release manager dedupes them against the generated bullets).
  Otherwise the section goes above the newest version. A trailing
  Keep a Changelog link block stays last; its `[Unreleased]` compare
  link moves to the new tag and gains a `[<version>]` line.
- **Groups**, in `templates/changelog-section.md` order, empty ones
  dropped: Added (feature), Fixed (bugfix, hotfix), Changed
  (refactor, upgrade), Dependencies, Upgrade notes (breaking markers,
  rollout exposure and migration order), Known issues (parked items),
  Outside the spec flow (commit subjects).
- **Bullets** end with a trace token — `(<spec-name>)` or
  `(<short-sha>)`. A breaking spec's bullet starts `**Breaking**:`.

`notes --check` fails when an included spec is missing from the
section, a bullet's trace token names a spec outside this release or a
commit outside the range, or a placeholder survives.

`notes --body` renders the GitHub release body from the section —
read from the tag's own changelog once the tag exists — wrapped in
`templates/release-notes.md` with the delivered-spec list and, for a
GitHub remote, the compare link.

## The release manager

Spawned once, after `notes --write`; agent type `spec-release-manager`
where the harness registers it, else a generic spawn leading with
`agents/release-manager.md`'s body. Payload: the collect JSON, the
drafted section, the version and tag, one prior changelog section for
voice, and the absolute path of `protocol/release-protocol.md`. Its
digest (`section:`, `trace:`, `dropped:`, `watch:`) is the whole
reply. The session shows the user the tightened section and every
`dropped:` and `watch:` line, replaces the draft on the user's
acceptance, and re-runs `notes --check`.

## The record

| Line | Written by | Where |
|---|---|---|
| `Released: <tag> @ <sha12>` | `cut --confirm` (or `record <tag> --write`) | full tier: task.md's header, below `**Delivered**:` (bold, `**Released**:`); tiny tier: spec.md § Evidence, the section created at the end when absent |
| `Post-release check: <tag> pass\|fail <date> — <note>` | `verify --outcome … --write` | below that spec's `Released:` line (same placement rules) |

`<sha12>` is the release commit the tag points to. The record commit
`chore(release): record <tag> on delivered specs` follows the tagged
release commit `chore(release): <tag>`, so the tag never carries its
own record (D-002). Archived specs take the record in their archived
dir. check.py and the approval freeze ignore both lines at both tiers
(task.md is unfrozen; § Evidence is outside a tiny spec's freeze).

## Status

`release.py status` derives, in order: stray changes → refuse; a cut
that stopped after the tag (HEAD is the release commit) with specs
missing their record → `record`; the last tag not
on the remote → `publish`; drafted release files → `preflight`, then
`cut`; unreleased work → `collect`; the last tag with no recorded
outcome → `verify`; otherwise nothing to release.
