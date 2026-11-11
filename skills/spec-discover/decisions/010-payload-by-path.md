# D-010: The stage-2 payload passes paths, not retyped text

The payload contract had the session retype one lens section and
`protocol/panel-protocol.md` byte-verbatim into every spawn — unchecked
hand-assembly, three times per run. The panelist already has Read.

The payload now carries the problem restatement, the absolute path of
`protocol/lenses.md` plus the lens name, the absolute path of
`protocol/panel-protocol.md` (paths resolved from `scripts/skill-dir.sh`),
and the evidence pack. The panelist reads only its own
`## Lens: <name>` section, so independence (D-002) holds. Harnesses
whose subagents cannot read files fall back to inlining the section and
protocol byte-verbatim. Supersedes the inline-text clause of D-006/D-007's
payload; the digest grammar is unchanged.
