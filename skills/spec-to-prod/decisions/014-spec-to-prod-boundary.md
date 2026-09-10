# D-014: spec-to-prod — "prod" is production-ready; release stays a human gate

Renamed the skill spec-to-prod → spec-to-prod (directory, router
command, regenerated plugin manifests, README, briefs, scripts,
diagrams; historical CHANGELOG entries keep the old name). The rename
raises a question the old name didn't: does "to prod" promise
deployment? It does not, and the boundary is now explicit.

The graph's terminal path is execute → closing-audit → tick-commit →
archive. What leaves the pipeline is a fully verified, single-commit,
production-READY changeset in the local repo, with every D-### ruling
surfaced and acked. Push, PR, deploy, and publish are out-of-workspace
side effects — the rulings rule already stop-and-asks each one — and
they remain human/CI actions by design. There is no release node in
the graph.

**Why**: a release node whose done-signal is a marker string would add
contract surface (graph.py node table, check gates, tests) without
adding verification — deployment correctness lives in CI, environments,
and permissions this skill cannot see. Stopping at the verified commit
is where the skill's evidence chain is complete and honest.

**Cost if wrong**: the name can oversell — a reader may expect the flow
to end at a deployed system. Mitigated by stating the boundary wherever
SHIP is described (§ Lifecycle commands, the /ship command file, this
ADR). If real deployment orchestration is ever wanted, it is a new
decision recorded here — a `release` HUMAN node (done-signal: a
`Released:` marker in spec.md), not a silent extension.
