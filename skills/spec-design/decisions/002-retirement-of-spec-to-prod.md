# D-002 — spec-to-prod retires: the move map

- **Context**: FR-009 — the monolith retires in the same release
  the trio ships (the resolved clarify round: no coexistence
  window), because three phase products replace one bundled
  surface and a lingering fourth skill would re-offer the
  monolithic entry the split exists to retire. Before the split,
  `skills/spec-to-prod/` owned all three concerns: eight
  commands, the only engine copy, 39 append-only ADRs, the
  docset templates, the mini-spec example, and the whole eval
  corpus. This ADR is the recorded move map every retirement
  task executes against (spec `specs/spec-to-prod-split`,
  tasks T020–T023).
- **Decision**: same-release cutover, history moves — never
  deletes (C-05). The map:
  - **Commands** — `/spec` → spec-intent (T010:
    `commands/extra.txt` claim + `commands/spec.md` intake
    verb); `/spec-plan`, `/spec-build`, `/spec-test`,
    `/spec-review`, `/spec-ship` → spec-execute (T016: five
    bare-name claims, the monolith's `extra.txt` drops them);
    `/spec-to-prod` → a thin verb-only alias router at
    spec-shape for exactly ONE release (T017, FR-010, split
    D-006: scaffold/intake → `/spec-intent`, authoring →
    `/spec-shape`, execute verbs → `/spec-execute`), then it
    retires with the next release; the monolith's full router
    file was deleted in the same task so the bare name has
    exactly one claimant.
  - **Shared core** — the canonical master lives at
    `skills/spec-shape/scripts/` (T001); `tools/parity.py`
    regenerates the closure into every graph.py-shipping skill
    as committed regenerate-only views (T002, split D-004). The
    monolith's copies die with the skill (T023); the parity pin
    auto-narrows to the trio (discovery keyed on `graph.py`).
  - **Eval cases** — the authoring classes E1–E3 + E7 →
    `skills/spec-shape/evals/cases.md` (T013); the
    resume/fix-round/delivery classes E4–E6 →
    `skills/spec-execute/evals/cases.md` (T015); the new intake
    cases I1–I3 → `skills/spec-intent/evals/cases.md` (T010);
    the `tools/tests/test_evals.py` selector and count pins
    updated in the same tasks. The monolith's `cases.md` is a
    pointer until the tree goes (T022/T023).
  - **History (successor homes, per T022)** — the 39 append-only
    decision files (`001-batched-audits.md` …
    `040-kilo-native-skills-root.md`, 034 absent from the
    numbering) move verbatim — filenames and D-numbers unchanged
    — to `skills/spec-shape/decisions/`, this skill being the
    retirement ADR's, the docset's, and the parity master's
    home. The moved `D-###` namespace is historical, retired
    with the monolith; each successor's own `D-001…` sequence is
    a new per-skill namespace (the same pattern as
    spec-brainstorming and spec-code-review each owning a
    D-001). `examples/mini-spec` moves to
    `skills/spec-shape/examples/` with every baked reference
    updated in the same task (the AGENTS.md docset-contract row,
    `tools/drift-check.py`, `tools/grade.py` dogfood paths); the
    existing-dir probe must pass from its new home.
  - **Kit-rules carriers** — the § Engineering rules section
    moves from the monolith's `agents/_shared-protocol.md` to
    the three successors' carriers (T011/T013/T015); canonical
    text stays `rules/engineering-rules.md`, injected by
    `tools/kit-rules.py`.
  - **Back-compat (FR-008)** — existing on-disk spec dirs stay
    valid with no migration: the docset contract is unchanged,
    the default span is `full` (bare-invocation semantics
    preserved), and an absent intent.md reads SKIPPED citing
    FR-008. Shape and execute accept any dir satisfying the
    contract — check.py is contract-shaped, never
    provenance-shaped.
  - **The sweep (T020, split D-007)** — `tools/retired-skills.txt`
    names `spec-to-prod`; `tools/sync.sh` sweeps each retired
    skill's installed trees at every root (including Kilo
    native) with no master — deleting only files the provenance
    ledger proves were this kit's deploys, refusing anything
    foreign. The stale-command prune already exists. Every
    generate-only surface regenerates in the same release:
    `marketplace.json` and the per-skill plugin manifests
    (`tools/plugin-manifest.py`), the root `agents/` personas
    (`tools/agent-defs.py` — the monolith's must not linger),
    and the drift-check/grade path pins (T023).
- **Consequences**: FR-009, FR-010, FR-008 hold; `ls skills/`
  shows five skills, none named spec-to-prod, with the thin
  alias still installing. Rollback is symmetric: reverting the
  release commit + `bash tools/sync.sh` re-installs the monolith
  and the sweep prunes the trio's deploys. The split's other
  surfaces are recorded beside this ADR: intent birth + profile
  (spec-intent D-001/D-002), shape birth (D-001 here), node/
  spans + parity + telemetry naming (D-003–D-005 here), execute
  birth + command claims (spec-execute D-001/D-002). The
  brainstorm's kill criteria stay live against the trio — 30
  days of telemetry with zero solo-phase invocations fails the
  split's driver.
