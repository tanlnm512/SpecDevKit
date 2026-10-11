---
description: Spec authoring - run the gated authoring waves (survey, plan ∥ tech ∥ qa, tasks, verify) over a validated intent.md or an existing docset, stopping at the human approve gate; never executes
argument-hint: <verb> <spec-name>
skills: spec-shape
---

Run the spec-shape skill (auto-mounted) for this request: $ARGUMENTS

Verb routing (`$1` = verb; a bare spec name is the default authoring
run):

- *(no verb / a spec name)* → the full authoring run: intake-gated by
  `graph.py --span shape` (a stale, red, or malformed intent.md
  refuses with exit 4 — route those to /spec-intent), then the
  frontier waves — survey → plan ∥ tech ∥ qa → tasks → verify — and
  the hard stop at the approve gate: present the spec-set digest,
  record the user's explicit yes (`Status: approved` + the approval
  freeze), hand off to `/spec-execute <name>`.
- `continue <spec>` / an authoring ask on an existing docset → same
  run, resumed from doc state (the intent.md-absent path is the
  FR-008 legacy shape — no intent demanded).
- `plan` / `tech` / `qa` / `tasks` / `re-survey <spec>` → the
  single-agent repair run for that node (`--emit-spawns --repair
  <node>`): one artifact refreshed, IDs never renumbered, `check.py`
  after.
- execute asks (build, test, review, ship, implement) → not here;
  route to `/spec-execute` — this skill never implements or commits.
