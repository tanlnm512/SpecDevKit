# Survey: loop-ready-docset

**Created**: 2026-11-11 | **Baseline**: 0.1.0 @ 98fa893d4018592624c23f8fcf0b7e3855fe3989
The survey node's output — the single source of truth for code state. Every citation
in the other four docs must trace to a line here. Evidence is pasted
verbatim from grep/read output in the session that wrote it.
First survey of this repo (specs/context/ written alongside this file).
Paths are relative to the repo root. The engine scripts are byte-shared
across skills/spec-design/scripts/, skills/spec-build/scripts/, and
skills/spec-define/scripts/ (see Supporting evidence) — citations below
name one copy; the identical copies in the other two skills carry the
same lines.

## Items

```
item FR-001: "fix rounds on a task — marker grammar, cap, writer, gates"
  evidence:   skills/spec-design/scripts/specstate.py:task_entries:286 parses each task block into TaskEntry; specstate.py:90 `FIX_ROUND = re.compile(r"\(fix\s+(\d+)/\d+\)")` fills `fix_round=int(fix.group(1))` at specstate.py:324 (field `fix_round: int | None` at specstate.py:182). The grammar comment, specstate.py:82-86: "`(fix <n>/5)` an OPEN fix round. ... An open fix round voids the landing beside it: the round closes by rewriting the marker `(fixed <n>/5)`, which no parser here reads as open." Cap: spec-build graph.py:198 `FIX_CAP = 5` under the comment graph.py:196-197 "Fix-round cap: `(fix n/5)` — the cap lives in the task.md annotation, so a task at cap is surfaced for adjudication, never auto-retried past it."; skills/spec-build/scripts/graph.py:task_frontier:431 makes "not at the fix-round cap" part of runnable (graph.py:434-438) and graph.py:483-486 emits state "at-fix-cap" / "fix cap reached ({e.fix_round}/{FIX_CAP}) — adjudicate before another round (plan-suspect → re-brief tech)". The tick-commit gate refuses an open round, tick.py:383-386: "fix round {e.fix_round} is open — land it and rewrite the marker (fixed {e.fix_round}/5) first". Today's writer is the orchestrator's hand-edit, not a script — skills/spec-build/SKILL.md:121 "| `(in-progress)` or `(implemented)` | it came back wrong | `(fix n/5)` — in place of the claim, or beside `(implemented)` |"; SKILL.md:150 "2. Write `(fix n/5)` on the entry, re-emit, and spawn."; escalation SKILL.md:159 "tier up. Round 4 failing writes `(fix 5/5)`, the cap — the engine never re-spawns it." Round evidence lives beside the task in notes/T###.md, not as note sub-lines on it: spec-build graph.py:1051-1055 "The fix round's evidence, verbatim from notes/T###.md — the" with the tail cap `FIX_NOTE_LINE_CAP = 200` at graph.py:202.
  status:     PARTIAL
  verify:     rg -n 'FIX_ROUND' skills/spec-design/scripts/specstate.py && rg -n 'FIX_CAP = ' skills/spec-build/scripts/graph.py && (rg -n 'fix_round' skills/spec-design/scripts/check.py || echo "check.py: no fix-round parsing")
  gap:        no writer emits a `fix <n> — <digest>` note sub-line on the task entry — the round is only the bare marker plus a notes/T###.md file; `(fixed n/5)` is read by retro.py:28 only (`FIXED = re.compile(r"\(fixed (\d)/5\)")`), never by specstate; check.py has zero fix-round parsing, so "check.py counts them" is new machinery.

item FR-002: "tick evidence — done-note sub-lines, tick-commit gate, graph consumer"
  evidence:   skills/spec-design/scripts/specstate.py:tick_evidence:376 — "The durable task-tick evidence for the tick-commit transition: the transition is fully evidenced only when `unticked` and `noteless` are both empty — every task ticked or struck, every tick carrying its `done <date> — <proof>` sub-line."; the sub-line writer is skills/spec-build/scripts/tick.py:_apply_ticks:79 — tick.py:92 `out.append(f"  - done {date} — {proof}")`; the tick-commit node consumes it at spec-build graph.py:2120 `ticks = specstate.tick_evidence(task_text or "")`; the DONE_NOTE contract comment sits at specstate.py:93-95 ("task.md tick proof: the `done <date> — <proof>` sub-line a ticked entry carries ... A tick without it is bookkeeping, not").
  status:     DONE
  verify:     rg -n 'def tick_evidence' skills/spec-design/scripts/specstate.py && rg -n 'specstate\.tick_evidence' skills/spec-build/scripts/graph.py
  gap:        this evidence class covers `done` proof notes only — fix-round sub-lines are outside it and have no check.py counter (that is FR-002's delta).

item FR-003: "retro.md — writer at archive, readers"
  evidence:   the writer is retro.py, invoked by archive.sh (archive.sh does not write the file itself): skills/spec-build/scripts/retro.py:main:119; docstring retro.py:2-9 "Writes <spec-dir>/retro.md, assembled only from the spec's own records: task states and (fixed n/5) markers, notes/T###.md fix-round headings, the D-### decisions (...), the delivery note, the spec's specs/BACKLOG.md lines, and the local telemetry counts for the spec. ... Both writes are idempotent; nothing is committed."; retro.py:28-29 `FIXED = re.compile(r"\(fixed (\d)/5\)")` / `FIX_ROUND_HEADING = re.compile(r"^## Fix round \d+", re.M)`. Caller: skills/spec-build/scripts/archive.sh:133-134 `if ! python3 "$scripts_dir/retro.py" "$dest" "$name" "$root"; then echo "ERROR: retro.md not written — rerun: python3 $scripts_dir/retro.py $dest $name $root" >&2`; archive.sh:6-7 "writes retro.md into the archived dir and rolls its D-### titles up to specs/context/decisions.md (retro.py)". Reader: none — audit.py's archive gate skills/spec-build/scripts/audit.py:mode_archived:1318 checks only task closure and the `Delivered:` record (audit.py:1339 `delivered = delivery_state(delivery_source(d))[0] == "delivered"`, audit.py:1343 "— archived before delivery"); `rg -n 'retro\.md'` over audit.py, spec-design check.py, and release.py returns no hits.
  status:     PARTIAL
  verify:     rg -n 'retro' skills/spec-build/scripts/archive.sh && (rg -n 'retro\.md' skills/spec-build/scripts/audit.py skills/spec-design/scripts/check.py skills/spec-release/scripts/release.py || echo "no reader hits")
  gap:        retro.md is written once at archive, never at ship; no script or gate reads it back; FR-003's ship-time write and archive-reuse-never-a-second are both new.

item FR-004: "burndown table — parser, repair mode, Verified column"
  evidence:   the table has two data columns — skills/spec-design/templates/task.md:9 `| Phase | Total | Done |` (task.md:8 comment "Recompute on every status change; `check.py` verifies the arithmetic."). Parser: check.py:180 `BD_ROW = re.compile(r"^\|([^|]+)\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*$")`; row classifier skills/spec-design/scripts/check.py:bd_label:350. Repair mode: check.py:39 "--fix-burndown repairs the burndown table from the actual task entries"; skills/spec-design/scripts/check.py:burndown_rewrite:769 ("Row labels, header, and separator lines are left byte-identical; only the two number cells of attributable data rows and the Σ row change."); skills/spec-design/scripts/check.py:fix_burndown:826 "burndown_rewrite plus the printed fix messages and file write the --fix-burndown CLI mode owns", invoked at check.py:1332-1333. tick.py cross-checks the same table before a tick commit (tick.py:136-138 "burndown: table totals ... != prospective tasks").
  status:     PARTIAL
  verify:     sed -n '7,11p' skills/spec-design/templates/task.md && rg -n 'BD_ROW = ' skills/spec-design/scripts/check.py
  gap:        no `Verified` column exists in the template or either parser; BD_ROW and burndown_rewrite hard-code the two-cell row shape (`(\d+)\s*\|\s*(\d+)`), so the column is a parser change, and nothing stamps per-phase pass/fail today.

item FR-005+006: "hotfix target headers — grammar and resolution"
  evidence:   the work-type grammar exists: specstate.py:69 `TYPE_LINE = re.compile(r"^\*\*Type\*\*:\s*`?([A-Za-z]+)", re.M)`, specstate.py:70 `WORK_TYPES = ("feature", "bugfix", "hotfix", "refactor", "upgrade")`, with the comment specstate.py:68 "the checker can refuse it by name. hotfix is the tiny-tier bugfix." check.py's only hotfix-specific behavior is a tier warning, check.py:1480-1482: `if spec_type(spec) == "hotfix": warns.append("type: hotfix is the tiny-tier bugfix — a full-tier docset is a `**Type**: bugfix`")`. The headers `**Hotfix for**` / `**Fixes spec**` exist nowhere in the kit: `rg -n 'Hotfix for|Fixes spec' skills/` returns no hits (the only repo hits are this spec's own docs). intent seeds the header: skills/spec-define/SKILL.md:51 "`**Type**` header set from the ask (feature | bugfix | hotfix | refactor | upgrade; spec.md inherits it)".
  status:     TODO
  verify:     (rg -n 'Hotfix for|Fixes spec' skills/ || echo "skills/: no hits") && rg -n 'hotfix' skills/spec-design/scripts/check.py
  gap:        no target header, no parser, no tag-reachability or spec-name resolution, no failure path — FR-005/FR-006 are entirely new grammar and a new check.

item FR-007: "release grouping of collected specs"
  evidence:   skills/spec-release/scripts/release.py:70 `LEVEL_BY_TYPE = {"feature": "minor", "bugfix": "patch", "hotfix": "patch",`; release.py:72 `GROUP_BY_TYPE = {"feature": "added", "bugfix": "fixed", "hotfix": "fixed", "refactor": "changed", "upgrade": "changed"}`. Rendering: skills/spec-release/scripts/release.py:generated_section:719 — release.py:722 `groups = {"added": [], "fixed": [], "changed": []}` and release.py:724 `groups[GROUP_BY_TYPE.get(s["type"], "added")].append(f"- {mark}{text} ({s['name']})")`. Each collected spec's facts land in one flat record at release.py:461 (`"delivery_note": delivery_note(spec_dir)` among them).
  status:     PARTIAL
  verify:     rg -n 'GROUP_BY_TYPE|LEVEL_BY_TYPE' skills/spec-release/scripts/release.py
  gap:        a hotfix lands in the generic `### fixed` bucket beside bugfixes; nothing keys it to the patched tag or the named spec — the group set has no per-release/per-spec subsections.

item FR-008: "delivery facts — Docs impact / Rollback / Behavior preserved lines"
  evidence:   the writer is the delivery pass's prose contract, not a script: skills/spec-build/SKILL.md:250 "**The delivery note** — `specs/<name>/notes/delivery.md`, one line per fact, each allowed to say `none — <reason>`:" with the three line shapes at SKILL.md:253-262 (`Docs impact: <files>`, `Rollback: <row> — <ruling>`, `Behavior preserved: <TCs> green at <Approved-at> and now`). The delivery record commit C2 is separate and writes `Delivered: commit @ <C1>` (SKILL.md:232). Reader 1 — dod gates 11-13: audit.py:209 `DELIVERY_NOTE = ("notes", "delivery.md")`; skills/spec-build/scripts/audit.py:delivery_gates:1072 "(name, status, detail) for the delivery note's gates: docs impact, rollback, and the spec's work type", wired at audit.py:1232 `enumerate(delivery_gates(spec_dir, repo, paths, git_ok), 11)`. Reader 2 — release collect: skills/spec-release/scripts/release.py:delivery_note:363 `pick("Docs impact")` → `{"docs_impact": ..., "rollback": pick("Rollback"), "behavior_preserved": pick("Behavior preserved")}`; breaking_markers also reads the note (release.py:401 `for name in ("spec.md", "tech-spec.md", "notes/delivery.md")`).
  status:     DONE
  verify:     rg -n 'DELIVERY_NOTE = ' skills/spec-build/scripts/audit.py && rg -n 'def delivery_note' skills/spec-release/scripts/release.py
  gap:        the facts are notes/delivery.md lines today — FR-008 relocates them into the task.md delivery block, changing the writer's target and both readers' paths (existing archived specs keep note files, so readers may need both shapes).

item FR-009: "approval record — approval.md + review.md, writer, verifier, gate"
  evidence:   writer: skills/spec-design/scripts/freeze.py:record:260 — freeze.py:37-38 "--record is run only after explicit user approval. It writes specs/<name>/approvals/approval.md atomically. --verify writes nothing."; atomic tempfile + os.replace at freeze.py:274-283; refuses an existing record without --force (freeze.py:276-281 "FAIL: ... already exists — a replacement requires a fresh user approval and --force"). review.md verifier: skills/spec-design/scripts/freeze.py:review_problem:184; freeze.py:30-34 "Three things must be on it: the docset fingerprint the review payload named, the auditor's digest line (`digest: BLOCK <n> · WARN <n> · NIT <n> · worst …`), and after that digest one `ruling:` line per BLOCK it counts."; fingerprint mismatch refuses (freeze.py:199-203 "reviews a different docset ... re-review, and record the new digest and fingerprint"). Gate: skills/spec-design/scripts/check.py:approval_failures:1038 — "An approved-or-later Status must be backed by the approval freeze, intact — at every tier" (check.py:1044-1048 fail when approval.md missing; check.py:1049-1050 `for problem in freeze.verify(spec_dir, repo_root)`); skills/spec-design/scripts/freeze.py:verify:326 is that verifier. Review recording is the orchestrator's hand-write: skills/spec-design/SKILL.md:278-285 "3. **Record** — the auditor writes nothing, so you write `approvals/review.md`, in this order: the payload's `Docset fingerprint: <hash>` line; the auditor's digest verbatim ...; then one line per BLOCK"; SKILL.md:296-298 "The freeze refuses a full-tier docset whose review.md lacks the current fingerprint, the digest line, or a ruling line per BLOCK". Tiny tier has no review (freeze.py:188-189 "(tiny tier has no contract review)"; SKILL.md:303-304 "At `Tier: tiny` ... no review.md is demanded").
  status:     DONE
  verify:     rg -n 'def record|def verify|def review_problem' skills/spec-design/scripts/freeze.py && rg -n 'def approval_failures' skills/spec-design/scripts/check.py
  gap:        the record spans two files with two writers — freeze.py writes approval.md, the orchestrator hand-writes review.md; FR-009 folds both into one approval.md (`## Contract review` + `## Freeze`), so freeze.py gains section rendering and check.py's integrity read moves with it.

item FR-010: "research gate — scaffold marker, parser, check handling, payload"
  evidence:   scaffold: skills/spec-design/scripts/scaffold.sh:60-61 `printf 'not applicable — no open questions at Stage 0\n' > "$target/research.md"` under scaffold.sh:51-57 "research.md ships as the resolved skip marker, not the template ... A full-tier draft from an intent is the exception: its gate stays open to be judged"; intent-sourced full-tier drafts leave it absent (scaffold.sh:8-9 "At full tier it leaves research.md absent"; judge_gate at scaffold.sh:58-59). Parser: skills/spec-design/scripts/specstate.py:research_state:422 → "'done' | 'skip' | 'pending' | 'missing'"; marker constant specstate.py:146 `RESEARCH_SKIP_MARKER = "not applicable — no open questions at Stage 0"`, template-residue glue specstate.py:152-156 `RESEARCH_TEMPLATE_GLUE`. check.py handling: check.py:144 `INPUT_FILES = ["survey.md", "research.md"]` — optional input, missing is a WARN carrying the skip-marker hint (check.py:1185-1189). Payload assembly: spec-design graph.py:1810 `rstate = specstate.research_state(spec_dir / "research.md")`; research is a real graph node — graph.py:229-231 edges `("spec", "research-gate")`, `("research-gate", "research")`, `("research-gate", "tech")`, graph.py:272 `RESEARCH_BRIEF = ("researcher", "analyst.md", "research")`; question harvesting skills/spec-design/scripts/graph.py:research_questions:648.
  status:     DONE
  verify:     rg -n 'research' skills/spec-design/scripts/scaffold.sh && rg -n 'research_state' skills/spec-design/scripts/graph.py
  gap:        research.md is a standalone artifact with four coupled sites — scaffold write, specstate parser, check.py optional input, graph node + payload; FR-010 folds it into tech-spec.md `## Questions & options` and retires the file, so all four move or disappear together (skip form included).

item FR-011+NFR-004: "migration precedent — migrate.py grow path; gate+reader pattern"
  evidence:   skills/spec-build/scripts/migrate.py:main:188; docstring migrate.py:2-8 "bring an older active docset's task.md to the template's contract header shape: dry-run, idempotent, evidence-neutral ... every `**Field**:` line in the template's preamble that the docset's task.md lacks is inserted verbatim — pending placeholders only ... A second apply finds nothing missing and changes nothing."; refusals migrate.py:9-13 "a missing spec.md/task.md or template, an unrecognizable spec.md Status, a done Status (a done plan is a record), and any path under specs/archive/ — archived history is never migrated"; migrate.py:41-42 `MIGRATABLE_STATUS = ("draft", "approved", "active")` / `FROZEN_STATUS = ("approved", "active", "done")`; field detection migrate.py:40 `FIELD_LINE`; header scan skills/spec-build/scripts/migrate.py:header_fields:53. Precedent limit: migrate.py:14-15 "draft, approved, and active docsets migrate: task.md is the status holder, outside the approval freeze." Gate+reader pattern: every grammar element has a specstate reader; fix rounds are the one element with no check.py side (rg 'fix_round' check.py: no hits), while research/burndown/freeze have both (check.py:144 + 1185; check.py:180 + 769; check.py:1038).
  status:     PARTIAL
  verify:     python3 skills/spec-build/scripts/migrate.py -h && rg -n 'MIGRATABLE_STATUS|FROZEN_STATUS' skills/spec-build/scripts/migrate.py
  gap:        migrate.py grows task.md preamble fields only and never touches frozen contract files; FR-011's grammar-wide in-place upgrade (round sub-lines, Verified column, hotfix headers, folded sections) and the WARN-once → FAIL-next-cycle pre-change-grammar detector have no precedent here; freeze preservation is untested ground (an upgrade that rewrites frozen sections contradicts freeze.verify's anchor).

item baseline: "baseline version source and HEAD"
  evidence:   RELEASE.md:23-24 "Bump `skills/<name>/VERSION` and the `metadata.version` line in that skill's SKILL.md frontmatter. The VERSION file is the source of truth"; `cat skills/spec-design/VERSION` → `0.1.0` (spec-build, spec-define, spec-release VERSION files read the same); `git rev-parse HEAD` → `98fa893d4018592624c23f8fcf0b7e3855fe3989` (`git log -1`: "feat(kit)!: kit review fixes — SDLC-named skills, deeper define/design/build, spec-ship + spec-release (#1)"). The survey header shape itself is parsed by skills/spec-design/scripts/specstate.py:survey_baseline:393 with `BASELINE_HEADER` at specstate.py:134.
  status:     DONE
  verify:     cat skills/spec-design/VERSION && git rev-parse HEAD
  gap:        none.
```

## Supporting evidence

Parity — the engine scripts ship as three byte-identical copies: in
skills/spec-design/scripts/, skills/spec-build/scripts/, and
skills/spec-define/scripts/ (`cmp -s` over each pair, design↔define and
build↔define; pasted verbatim from this session's run):

```
=== cmp spec-design vs spec-define ===
specstate.py IDENTICAL (design↔define)
check.py IDENTICAL (design↔define)
freeze.py IDENTICAL (design↔define)
graph.py IDENTICAL (design↔define)
index.py IDENTICAL (design↔define)
contract.py IDENTICAL (design↔define)
telemetry.py IDENTICAL (design↔define)
=== cmp spec-build vs spec-define ===
specstate.py IDENTICAL (build↔define)
check.py IDENTICAL (build↔define)
freeze.py IDENTICAL (build↔define)
graph.py IDENTICAL (build↔define)
index.py IDENTICAL (build↔define)
contract.py IDENTICAL (build↔define)
telemetry.py IDENTICAL (build↔define)
```

(Spec-design↔spec-build identity for the same seven files was cmp'd in
the session that first wrote this survey — all seven IDENTICAL.)

Script ownership (from `ls`, verbatim): `skills/spec-design/scripts/`
carries `check.py contract.py freeze.py graph.py index.py scaffold.sh
specstate.py telemetry.py`; `skills/spec-build/scripts/` carries the
shared seven plus the runtime-only `archive.sh audit.py gate.sh
gate_helpers.py migrate.py retro.py tick.py`; `skills/spec-define/scripts/`
carries the shared seven (`check.py contract.py freeze.py graph.py
index.py specstate.py telemetry.py`); `skills/spec-release/scripts/`
carries `release.py skill-dir.sh`.

Spec registration (specs/INDEX.md:2, verbatim):
`- [loop-ready-docset](loop-ready-docset/spec.md) — draft · feature · full`

Repo doc state at the baseline: `specs/` holds `CONSTITUTION.md`,
`INDEX.md`, and the one live spec `loop-ready-docset/` (intent.md,
plan.md, research.md, spec.md, survey.md, task.md, tech-spec.md, test.md,
spawns/) — no `specs/archive/`, no `specs/BACKLOG.md`; `specs/context/`
did not exist and was written with this survey (structure.md, tech.md).

Burndown template block (skills/spec-design/templates/task.md:7-11,
verbatim):

```
## Burndown
<!-- Recompute on every status change; `check.py` verifies the arithmetic. -->
| Phase | Total | Done |
|-------|-------|------|
| 1     | 3     | 0    |
```

Template residue worth knowing for FR-010: all three skills ship a
`templates/research.md` — spec-design, spec-build, and spec-define
(spec-define/templates/ also lists `research.md`, and
`cmp skills/{spec-design,spec-build}/templates/research.md
skills/spec-define/templates/research.md` reports both pairs IDENTICAL)
— the unfilled template whose residue RESEARCH_TEMPLATE_GLUE detects;
retiring research.md retires the template copies and the glue list with
them.

## Rules

- Every `file:line` pasted from grep/read in this survey — never from memory.
  Can't find it → write `unknown — verify`, don't guess.
- Status derives from evidence, not intent. Run every verify command.
- A number in an old doc is a claim, not evidence — re-count it.
