# D-011: omp native execution — use the harness's own primitives, not just harness-neutral ones

1.8.0 made the skill *discoverable* inside omp: an omp-native skill copy,
and `tools/omp-defs.py` regenerating the eight `spec-*` task-agent defs
with omp frontmatter. That closed the install-time gap. The *execution*-time
mechanics — spawn payload shape, digest collection, frontier recompute —
were still written harness-neutral only, which under omp specifically left
real capability on the table: every wave recompute paid a fresh `python3
scripts/graph.py` process (interpreter start, module import, and — inside
that — up to two more subprocess spawns for its own check.py/audit.py
probes) with no path to run any of it in-process, because `check.py`'s and
`audit.py`'s `main()` hardcoded `sys.argv` — nothing outside a fresh CLI
process could call them at all. The digest contract stayed prose-only
even though the harness can mechanically validate structured output.

**Decision**: bring omp's own primitives into the parts of the skill that
run inside it, without changing the harness-neutral contract underneath:

1. `check.py`/`audit.py`'s `main()` takes an optional `argv` (default
   `None` → `sys.argv[1:]`, byte-identical CLI behavior — the existing
   `unittest.mock.patch.object(sys, "argv", …)` test pattern is untouched)
   so a persistent process can call them directly. `graph.py`'s `main()`
   already had this shape; this brings the other two scripts to parity.
   New `MainArgvTests` in both test files lock the new path against the
   CLI path and against ambient-`sys.argv` leaking through.
2. SKILL.md gains "Running under omp (native execution)": the wave as the
   `task` tool's `tasks[]` array (shared payload once in `context`, not
   repeated per entry); `outputSchema` as *optional* mechanical validation
   of a brief's existing `digest:` shape (the fields are still defined by
   the brief — contracts/docset.md's return-contract item now says this
   explicitly, so the harness-neutral contract and the omp enforcement
   layer can't drift into two different definitions); auto-delivered
   `task` results (no polling); the observation that `tools/omp-defs.py`
   grants no `spec-*` role a `hub` tool, so "no peer-to-peer messaging"
   (§ Independent spawns) is harness-enforced under omp, the same shape as
   the reviewer's read-only guarantee; and the eval-kernel recipe (item 1
   is what makes it legal) for in-process frontier recompute.
3. Surveyor and implementer briefs stay scoped to what a spawned
   subagent can actually reach: a repo-specific code-intelligence CLI,
   invoked through the subagent's own tools, when the repo ships one —
   not a claim that the harness's own `lsp`/`ast_edit` devices are
   reachable by the subagent itself. Verified, not assumed: spawning a
   real `spec-surveyor` and asking it to call `write path=xd://lsp`
   returned `Mounted devices: .` (empty) even though its frontmatter
   grants `write` — device mounting is a separate mechanism from the
   base tool allowlist, and a default task spawn gets none. Where the
   *orchestrator's own* session has these devices mounted (as this one
   does), SKILL.md's "Running under omp" section names them for the
   orchestrator's own inline work — never as something to tell a
   spawned subagent to reach for.

**What stays unchanged, deliberately**: `graph.py`'s own internal probes
(the survey node's `check.py --survey-only`, the verify node's `check.py`,
the closing-audit node's `audit.py dod`) keep shelling out via
`subprocess`, not the new in-process path — that isolates their own
prints/argv from graph.py's return value, and graph.py already has 81
passing tests built around that shape; the eval-kernel recipe is for the
*orchestrator's own* repeated top-level `graph.py` calls (the actual hot
loop — "run the wave, recompute, repeat" pays one per wave, and a real
multi-phase spec runs many waves), not a rewrite of graph.py's internals.
The digest **contract** (per-role field shapes) is unchanged either:
`outputSchema` is enforcement bolted onto an existing shape, never a
redefinition of it, and a harness without schema support runs the
identical prose contract.

**Why**: the frontier loop is the pipeline's literal hot path, and
process-per-call is exactly the overhead a persistent kernel exists to
avoid — this is a real, compounding cost (every wave boundary, every
resume, every `--explain` check pays it), not a micro-optimization.
`outputSchema` directly closes anti-pattern #2 (telephone-game drift from
a malformed prose digest) wherever the harness offers it, at zero cost to
harnesses that don't. The `lsp`/`ast_edit` scoping matters for the same
reason the surveyor brief's self-check step exists at all: it narrates a
real incident where hand-counted grep citations were off by hundreds of
lines, and an unverified claim about which tool is reachable is the same
failure mode one level up — asserted, not checked.

**Cost if wrong**: the eval-kernel recipe goes stale if `scripts/*.py`'s
CLI contract (argv shape, exit codes) changes without a matching update —
mitigated because the recipe calls the same `main(argv)` the CLI itself
uses, so a CLI-breaking change already fails the existing test suite
before this recipe would silently drift out of sync. Treating
`outputSchema` as load-bearing (skipping the prose `digest:` contract
because "the schema already validates it") would re-couple the
harness-neutral brief contract to one harness's optional feature —
mitigated by contracts/docset.md now stating plainly that the schema
enforces, never redefines, the fields. The `lsp`/`ast_edit`-reachability
claim already cost once: the first draft of this decision asserted
subagent reachability from an inference chain (surveyor/implementer hold
`write`; `write` routes to `xd://` devices) without spawning anything to
check it — exactly anti-pattern 9 (inherited numbers laundered as
evidence), just about tool capability instead of a count. A single
throwaway `spec-surveyor` spawn disproved it before this file was ever
read as settled history; item 3 above is the corrected result. The
mitigation this ADR stands on now: don't assert a spawned subagent's
tool reach without spawning one to check.
