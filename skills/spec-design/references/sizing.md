# Sizing a spec — tier, effort, and the scaffold

## Choosing tier and effort

Two spec.md headers right-size the artifacts, never the gates (a
third, `**Type**: feature | bugfix | hotfix | refactor | upgrade`,
names the work type the lenses and check.py key on — the template's
header comment has the rules; absent reads feature):

- **`Tier: tiny`** — a small, single-area, low-risk change: SKIPs the
  authoring nodes, the task list lives in spec.md § Tasks, the one
  file is the contract. Absent means full (the seven-file docset);
  growing a tiny spec later is `migrate.py grow`. Tiny is approved
  and frozen like full: `freeze.py --record` writes
  `approvals/approval.md` and is required before execute — a bare
  `Status: approved` fails `check.py`. Only the record's
  `## Contract review` section is waived at tiny (`--record` without
  `--review`). The freeze covers § Tasks:
  status markers move freely, but an added, edited, or struck task
  or requirement is a re-approval (`--record --force`).
- **`Effort: standard`** (the template default) — one merged architect
  payload authors plan + tech + tasks, with the tester separate in the same
  wave. Use for work inside one area.
- **`Effort: large`** — the full plan ∥ tech ∥ qa wave, then a separate
  tasks wave. Use for multi-area, auth, persistence, migration, or
  research-heavy work. A missing or unknown Effort reads large.

Effort has exactly these two values. `tiny` is a Tier, never an
effort; a doc still carrying `Effort: tiny` reads standard. The
intent's `**Effort**` line is the intake's guess; spec.md's header is
the one the engine reads — confirm it when drafting spec.md.

## Templates and scaffolding

`scripts/scaffold.sh [--tier tiny|full] [--into-existing] <name>`
writes the skeleton from `templates/` (default `tiny`: spec.md with
§ Tasks, constitution; `full`: spec, plan, tech-spec, task, test,
survey too — tech-spec ships the research gate's `## Questions &
options` pre-filled with the skip form). `--into-existing` fills an
intake dir without overwriting anything and, at full tier, strips that
skip form so the section stays open for the research gate. Growing a
tiny spec to full:
spec-build's `scripts/migrate.py grow <spec-dir>`. intent.md's
template belongs to spec-define.

`specs/INDEX.md` is the cross-spec view — one rendered line per spec
(status · type · tier · `**Depends on**` names). `scripts/index.py
<spec-dir>` is its only writer: run it when check.py reports the line
stale, never hand-edit it. A `**Depends on**` header orders specs;
check.py refuses a name that is no spec and warns when another
in-flight spec's `Touches:` overlap this one's.
