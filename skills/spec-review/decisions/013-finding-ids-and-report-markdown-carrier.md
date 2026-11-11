# D-013: Stable finding ids and the report markdown as fix_from carrier

A finding's identity is its `id`, minted the moment it becomes
tracked — `<lens>-<n>` at confirmation, `gate-N` / `fix-review-N`
inside the loop — never minted by reviewers. The id rides every later
representation: the findings board key, the report heading
(`### [correctness-1 · HIGH · verified · lens] …`), the returned
findings JSON, the fixer's `addressed`/`skipped` replies, and the
fix_from payload, where a carried id is kept and an id-less item
(human-edited JSON, a pre-0.13 report) gets `carried-N`. Second, the
fix_from carrier widens from JSON only to **the saved report markdown
itself**: when the payload is not JSON, `parseFindingsMd` reads the
findings section back (both the id-bearing 0.13 heading and the pre-id
0.12 heading), so the review-then-ask flow hands over the artifact the
user actually saved. Third, the fixer now reads the target repo's
AGENTS.md/CLAUDE.md before its first edit — the reviewers already did;
the repo's own rules bind the fixes too (Principle 8).

**Why**: `where` was doing double duty as evidence and identity, and
it is bad at identity — two findings can share a `path:line`, lines
move under the very fixes the loop lands (so a carried `where` points
at stale coordinates), and the fixer's progress replies had to match
`what`-strings verbatim to be joinable. The cairn fix-audit run of
2026-10-02 (141 findings fixed through a bespoke orchestrator) showed
the working alternative: short stable ids per finding are what make
tracking, dedup, and flagged-only re-verification cheap at scale. And
its carrier was the audit markdown itself — the report a human actually
reads and saves — not a JSON sidecar the workflow alone emits. D-005's
continuation contract keeps its shape (review, present, ask, fix from
the report); this widens what "from the report" accepts and tightens
the join key.

**Cost if wrong**: an id that is not truly stable (reused prefixes
within a run, renumbering across fix rounds) breaks the board and the
fix_from join silently — the minting helpers (`nextId`, per-lens
`<lens>-<n>` at confirmation) are the guard, and the markdown parser
is pinned by executed parity tests in both dialects. A markdown carrier
that over-accepts (parsing headings the workflow never emitted) would
invent findings from prose — the parser matches exactly the heading
shapes `findingsMd` emits and drops items without `where`/`what`.
