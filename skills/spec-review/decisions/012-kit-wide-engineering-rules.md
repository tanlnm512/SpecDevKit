# D-012: The fixer brief carries the kit-wide engineering rules

The panel's only role that writes code is the Stage-4 fixer, so the
kit-wide engineering rules (test discipline, backgrounded-job
discipline, strict code commenting — canonical in spec-to-prod's
`agents/_shared-protocol.md` § Engineering rules, this suite's
D-028) are carried verbatim in `agents/code-review-fixer.md`
§ Engineering rules. The brief is the one channel that reaches every
fixer path: runtime-loaded by both workflow dialects (`readBrief`
into the fix loop spawn, with graceful degrade to the inline
rubric), installed as a real agent def, and cited by SKILL.md §
Stage 4 for the inline path.

**Why**: the fixer edits the working tree under exactly the
pressures these rules govern — it adds or strengthens tests after
fixes (test discipline), runs a targeted test file that may be
auto-backgrounded (never poll), and writes code in someone else's
repo (commenting: why not what, no decision logs, no volatile
values). Restating them in the review bar instead would violate
Principle 8 (the repo owns its standards; the panel imposes nothing
of its own) and hand reviewers a ruleset the reviewed repo never
adopted. Compliance-side, not enforcement-side: the fixer follows
the rules, the lenses keep their own bar. The brief is a generated
view of the canonical source (`rules/engineering-rules.md`, injected
by `tools/kit-rules.py` — spec-to-prod's D-028), so the wording
cannot fork.

**Cost if wrong**: a fix could weaken a test or leave an essay
comment — but the fixer brief's own hard rules and the quality lens
already guard both; these rules tighten the floor, they do not
replace a guard. If the brief fails to load the workflow degrades
to the inline rubric — the SKILL.md Stage-4 pointer is the
fallback's fallback.
