# Intent: spec-status-router

**Type**: feature
**Effort**: standard
**Created**: 2026-11-26
**Baseline**: spec-dev-kit 0.1.1–0.2.0 @ 91b226a

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

A draft, seeded unattended from `plans/kit-hardening.md` § 5 (row 5.1):
no grill has run and nothing below is closed. Every line under
§ Questions is a live marker for the owner; § Scope out and
§ Assumptions fill in only at that grill.

## Problem
> "5.1 `/spec` status router" — "one command reading graph/ship/release
> state, naming the next skill" — feeds "all".
> (`plans/kit-hardening.md` § 5, the row's three cells.)

The state a router would read already exists, and each reader names a
next step for its own span. `graph.py specs/<name>` prints per-node
state, the frontier and the printed next step
(`skills/spec-design/scripts/graph.py:25-29`, `:1677`). `ship.py status`
answers for one delivered spec
(`skills/spec-ship/scripts/ship.py:1193`). `release.py status` answers
for the repo since its last tag
(`skills/spec-release/scripts/release.py:1388`). Nothing joins them:
with several specs in a repo, a human still runs three readers, each
with its own scope, and works out which skill comes next.

## Audience
- The owner returning to a repo that holds several specs at different
  stages — needs one line per spec saying where it stands and which
  skill is next; today they run three readers with two scopes and
  reconcile the answers by hand.
- An unattended orchestrator between waves — needs a mechanical "what
  is next" it may act on; today `graph.py` names the next step only
  inside the spec suite (`skills/spec-design/scripts/graph.py:1677`),
  and its `AWAITING HUMAN: <node>` line (`:110`) names the gate, not
  the skill that resumes it.

## Constraints
- Scout-verified — the three readers exist and only read: `graph.py`
  (the default report, or `--state-json`, "the authoritative oracle
  for tests and validators",
  `skills/spec-design/scripts/graph.py:25-32`), `ship.py status`
  (`skills/spec-ship/scripts/ship.py:17`) and `release.py status`
  (`skills/spec-release/scripts/release.py:18`).
- The scopes differ: `graph.py` and `ship.py` answer per spec dir;
  `release.py status` answers per repo, from the last tag
  (`skills/spec-release/scripts/release.py:1390-1391`).
- Each reader degrades its own way: `ship.py` prints "gh CLI not
  found" and refuses a read that needs it
  (`skills/spec-ship/scripts/ship.py:479-480`, `:832`), exiting 1 or
  4; `graph.py` prints `SKIPPED (not a git repo)`, never a silent
  false result (`skills/spec-design/scripts/graph.py:28-29`).
- Naming precedent cuts two ways: skill names equal command names and
  skills are named after SDLC phases (spec-design D-048, D-054), while
  the lifecycle verbs ride one command per skill (spec-build D-033).
- The kit's scripts call no harness API (C-03, `AGENTS.md`); `gh` is a
  CLI the ship and release scripts already shell out to.
- A third repo-level state exists beside graph, ship and release: the
  cross-spec claim registry `specs/.claims/registry.json` (spec-design
  D-078; `skills/spec-design/scripts/specstate.py:1365`).
- Version sources: the repo has no single VERSION file — RELEASE.md §2
  names `skills/<name>/VERSION` per skill (spec-build 0.2.0,
  spec-define and spec-design 0.1.2, the other four 0.1.1), which is
  why the Baseline above names a range.

## Questions
- [NEEDS CLARIFICATION: is `/spec` a new skill dir (its own SKILL.md,
  evals and install surface) or a verb on an existing skill, and which
  precedent governs the name — D-054 (skills are named after SDLC
  phases, and "spec" is not one) or spec-build D-033 (one command per
  skill)? The packaging hangs on it: parity, the drift-check sets, the
  marketplace manifest.]
- [NEEDS CLARIFICATION: what is the command's argument — no argument,
  a portfolio line for every dir under `specs/`, or `/spec <name>` for
  one spec? The output shape and the ranking rule hang on it.]
- [NEEDS CLARIFICATION: with several specs, which one is "next" — by
  what order (a pending human gate first, the oldest ready node, the
  largest frontier), and does the command name one skill or list every
  spec's next skill? The scheduling rule hangs on it: the frontier is
  the only scheduler today (GLOSSARY "frontier").]
- [NEEDS CLARIFICATION: how are the two scopes joined — per spec
  (graph, ship) and per repo (release, since the last tag) — in one
  report: is the release state printed once, or attached to each
  delivered spec? The report's shape hangs on it.]
- [NEEDS CLARIFICATION: what is printed when a reader cannot answer —
  no `gh`, an unreachable remote, not a git repo — and which exit code
  carries it? Whether the command can be trusted unattended hangs on
  it: a silent omission would read as "nothing to do".]
- [NEEDS CLARIFICATION: does the command only read and print the exact
  next command (as `ship.py` prints the exact command for each outward
  action, `skills/spec-ship/scripts/ship.py:8-9`), or may it start the
  next skill itself? Whether it needs a yes-to-a-preview gate hangs on
  it.]

## Scope out
Nothing yet — a deferral is listed here only with the owner's assent
at the grill, and none has been given.

## Assumptions
None yet — a named assumption closes a question only with the owner's
assent at the grill, and none has been given.

## FR seeds
- **FR-001**: The status router shall report, for every spec under
  `specs/`, the doc state `graph.py` derives and the next skill that
  state calls for.
- **FR-002**: WHEN a spec is delivered, the status router shall report
  the state `ship.py status` derives and the step it names.
- **FR-003**: WHEN the repo holds a delivered spec no tag covers, the
  status router shall report the state `release.py status` derives.
- **FR-004**: WHEN one of the three readers cannot answer, the status
  router shall name that gap on its line.
- **FR-005**: The status router shall write nothing under `specs/` and
  call no harness API.
- **NFR seeds**: reliability (a reader that cannot answer is named,
  never dropped) and observability (each line says which reader
  produced it); their bounds are the owner's at the grill.

## Handoff
Next: `/spec-design spec-status-router` — the docset (spec.md onward)
is authored there, never here. The Baseline above is what
spec-design's tech step re-baselines against.
