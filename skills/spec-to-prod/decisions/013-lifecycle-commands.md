# D-013: Lifecycle commands are thin wrappers; the router verb space is untouched

The six-verb development lifecycle popularized by addyosmani/agent-skills
(DEFINE `/spec` → PLAN `/plan` → BUILD `/build` → VERIFY `/test` →
REVIEW `/review` → SHIP `/ship`) ships as six thin command files in
`commands/`, each delegating into the workflow graph at a node. The
router's own verbs keep their established meanings — `plan`/`tech`/`qa`
are single-agent authoring repair runs, `review` is the docs reviewer —
so the same words never mean different things on two surfaces of one
package.

**Why**: adopting the surface by redefining router verbs (`plan` =
"run to approve", `review` = "closing-audit half") silently changes what
documented commands do — a habitual `plan auth` expecting a planner
re-run would get a full pipeline run instead. Wrapper files give the
lifecycle its own namespace, mirror how the source repo ships the
surface (top-level command files over skills), and cost one allowlist
entry plus a foreign-file guard in tools/sync.sh. `/test`, `/review`,
and `/ship` are defined as portions of the ONE closing audit, never
three audits — the source surface's per-task commits and per-task
verification are explicitly not adopted.

**Cost if wrong**: bare names land flat in shared global command roots
where anything — a hand-written note, another plugin — may already
live. Governed, not assumed: tools/sync.sh installs bare names only
through the explicit `extra_commands()` allowlist (never a glob),
refuses a destination that exists, differs from the master, and is not
a prior recorded deploy of ours (per-root provenance ledger — foreign
file → loud failure, manual resolution; a ledger, not git history,
because deploys routinely run from uncommitted trees),
rename-or-namespace decision recorded here.
