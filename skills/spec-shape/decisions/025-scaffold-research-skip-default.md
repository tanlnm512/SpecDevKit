# D-025: The scaffold ships research.md as the resolved skip marker

Every fresh scaffold carried the unfilled research template, so the
research-gate read `gate:undetermined` until the orchestrator wrote
something — and the skip form (the gate's own documented common case:
"most bugfixes, most single-known-pattern internal changes") still cost
an explicit authoring step per spec. In workflow mode an undetermined
gate is a stop.

**Decision**: `scaffold.sh` writes research.md containing exactly the
canonical skip line (`not applicable — no open questions at Stage 0`)
instead of copying the template. The gate resolves `skip` on scaffold;
the orchestrator flips it to `run` by replacing the file with the filled
template when the spec has ≥1 real open question — the authoring
instruction (derive questions, then decide) is unchanged, and
manufacturing questions to justify the spawn remains the failure mode
the gate exists to prevent.

**Why**: the default should match the common case; a deliberate skip
needs zero actions and a deliberate run needs one (replacing a one-line
file), which is strictly less work than today's write-the-marker-by-hand
in the skip case and identical in the run case.

**Cost if wrong**: an unexamined default could skip research that was
needed. The guard is the authoring flow itself (the clarify/research
derivation happens with the user before the gate is ever read) and the
tier choice next to it — research-heavy work is exactly the `large`
tier, whose authoring pass explicitly revisits the gate. The template's
research questions remain available in templates/research.md.
