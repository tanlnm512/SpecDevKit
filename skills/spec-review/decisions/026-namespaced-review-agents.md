# D-026: the review agents are namespaced — `spec-review-<role>`

Every kit agent is `spec-<role>` — `spec-analyst`, `spec-architect`,
`spec-tester`, `spec-developer`, `spec-auditor`, `spec-panelist`,
`spec-integrator`, `spec-release-manager` — except the five this
skill ships, which spec-design D-054 named `review-<role>`. A bare
`review-` prefix is shared turf: another plugin's `review-security`
lands in the same flat agent roots (`~/.claude/agents/`, the
opencode, droid and Kilo agent dirs), where the file name or the
frontmatter `name:` is the agent's identity, and `tools/sync.sh`
refuses to overwrite a file at a kit name that the root's ledger does
not prove a prior deploy — so the collision stops the install until
someone resolves it by hand.

**Decision** (one naming rule kit-wide — agents are `spec-<role>`;
a review role keeps its skill segment, as `spec-release-manager`
keeps its phase):

1. **The five agents are renamed**: `review-correctness` →
   `spec-review-correctness`, `review-security` →
   `spec-review-security`, `review-quality` → `spec-review-quality`,
   `review-scout` → `spec-review-scout`, `review-fixer` →
   `spec-review-fixer`. Supersedes the review row of spec-design
   D-054's rename table.
2. **The brief files move with the names**
   (`agents/spec-review-<role>.md`) and each frontmatter `name:`
   follows its stem: the opencode and Kilo roots take the agent name
   from the file name, so a `review-<role>.md` brief would install
   there as `review-<role>` whatever its frontmatter says. No body
   changes — none of the five referred to itself or a sibling by
   name. `contracts/run-sequence.md` § Who runs each role and
   SKILL.md's brief pointers follow; the root `agents/` personas are
   regenerated from the briefs.
3. **Unchanged on purpose**: the lens labels (`correctness`,
   `security`, `quality`, `general`) and the checkpoint stages built
   from them (`review-<lens>`, `triage-<lens>` — the `STAGES`
   vocabulary, D-020) name a lens and a stage, never an agent type,
   and the oracle holds no agent-type name — the session picks the
   type from the role table. A run saved before this decision
   resumes under the names it was saved with.
4. **A user with a registered native type renames it.** A prompt,
   config, or workflow that names `review-<role>` as a subagent type
   names `spec-review-<role>` from now on. The next `tools/sync.sh`
   prunes the old def from every root a prior sync installed it to —
   `~/.claude/agents` and the opencode, droid and Kilo agent dirs
   through the ledger-proven stale-def prune of spec-design D-054's
   migration, the omp root through `tools/omp-defs.py`'s per-skill
   manifest — and installs the new one; `--check` reports each old
   def as `STALE` until then. A file at an old name that no ledger
   or manifest proves to be the kit's is someone else's and stays
   untouched. Pinned by `tools/tests/test_sync.py`
   (`StaleCommandPruneTests`,
   `test_namespaced_review_def_is_pruned_and_a_foreign_one_survives`).
5. **History keeps the old names.** Earlier ADRs, changelog entries,
   and recorded eval results read as written; `GLOSSARY.md` lists the
   five under "Retired agent names".

**Consequences**: the kit has one agent-naming rule, and its review
agents no longer sit on names any plugin may use. The cost is a
breaking rename of five registered types (a **Breaking** changelog
entry): a project that pinned the old names updates them once, and
after its next sync an old name resolves to no kit def.
