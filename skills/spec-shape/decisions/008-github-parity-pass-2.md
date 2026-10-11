# D-008: Second GitHub parity pass (spec-kit, BMAD-METHOD, Agent OS)

A repeat of the 1.2.0/1.3.0 parity passes (spec-kit/OpenSpec/Kiro/BMAD/
sweep, then ai-devkit): survey comparable GitHub projects, adopt only what
survives a "do we already do this?" check, reject the rest. This round
compared against `github/spec-kit`, `bmad-code-org/BMAD-METHOD`, and
`buildermethods/agent-os`.

**Rejected on arrival** (already covered, confirmed by reading
`scripts/check.py` before touching anything): a scripted reverse FR-
coverage check ("every FR has ≥1 task and ≥1 test case") — check.py
already asserts both directions per FR (`traceability: {fr} has no task` /
`has no test case`) since before this pass. spec-kit's closest analog,
`/speckit.analyze`, is itself an LLM pass rather than a script, so it can
miss what an LLM writer already missed — check.py's version predates and
subsumes it. No change made.

**Adopted, mechanically enforced (this skill's differentiator: a script,
not another LLM review pass, does the gating):**

1. **Constitution gate, scripted** (`check.py --constitution`,
   `constitution_status`/`other_specs_exist` in check.py) — presence/fill
   was WARN-only regardless of context; now FAILs once a second spec
   exists in the repo (scaffold.sh's auto-create on the *first* spec no
   longer excuses a missing constitution on the second). Mirrors
   spec-kit's constitution-first gate, but as a script check instead of a
   prose reminder.
2. **Converge verb** (`audit.py converge`, `gates/before-audit.md` cross-
   ref, SKILL.md § Run modes) — spec-kit's `/speckit.converge` re-scans
   for drift; ours diffs a freshly re-run survey.md against its last
   committed version via git and prints `NEW GAP`/`REGRESSED` items
   mechanically, rather than an agent eyeballing the diff.
3. **checklist.md** (`check.py --checklist`, `build_checklist`) — spec-
   kit's `/speckit.checklist`, ported as a regenerate-only derived file
   (never hand-edited, never read by check.py's status checks) so it
   can't become a second, driftable status representation — the same
   failure class D-007 killed for agent defs/briefs.
4. **Per-task scratch note** (`specs/<name>/notes/T###.md`, fix round 2+,
   own task ID only) — formalizes BMAD's durable story-file idea as one
   narrow, named exception to "implementers never touch specs/" (disjoint
   filenames, so it doesn't reopen the concurrency-safety hole that rule
   exists to close).
5. **Tagged context baseline** (`agents/spec-surveyor.md` § Method) —
   Agent OS's `standards/index.yml` selective-injection idea, as an
   optional `## area: <name>` tag in `specs/context/tech.md` once it stops
   fitting one screen. Prose guidance only — no script depends on the tag,
   so an untagged file degrades to today's behavior, not a failure.

**Why**: the comparison confirmed check.py has no analog in any of the
three projects surveyed (their equivalents are LLM passes); the risk this
pass exists to guard against is diluting that differentiator by porting
process advice that *sounds* like validation but isn't scriptable. Items
1–3 are script-enforced; 4–5 are narrow, low-risk conventions with no new
status semantics.

**Cost if wrong**: constitution FAILs could false-positive on a repo that
deliberately has no constitution yet with 2+ specs in flight — mitigated
by keeping it WARN for the first spec and requiring an actual second spec
dir (not just any file) to escalate. converge's git-diff approach reads
"unknown" status for any survey.md not yet committed — informational
only (exit 0 always), never gates. checklist.md/notes files are pure
additions; deleting either loses nothing check.py enforces.

Sources: github.com/github/spec-kit, github.com/bmad-code-org/BMAD-METHOD,
github.com/buildermethods/agent-os.
