# Changelog — spec-code-review

Release history. The skill began life 2026-09-23 as the validated
`spec-code-review` dynamic workflow in the SpecDevKit repo (three-stage
review: mechanical gate → specialist panel with triage and independent
confirmation → synthesis), then became a portable sibling skill.


## 0.1.0 — 2026-09-23

First release. The review protocol of the validated workflow, packaged
for any repo and any coding agent: `scripts/gate.sh` detects and runs
the target repo's own checks (Makefile targets, npm scripts, cargo, go,
pytest/unittest, `bash -n` on the changed shell scripts) and reports a
JSON array callers can branch on; SKILL.md carries the full protocol —
defect-first flagging bar, severity ladder, exclusions, triage,
independent confirmation, the bounded fix loop, and the
merge/fix-first/human recommendation. The zcode workflow
(`workflows/spec-code-review.dwf.ts`) automates the stages on harnesses
that run dynamic workflows; agents without workflow support execute the
stages inline. Validated end-to-end twice in SpecDevKit: the review
pass confirmed 7 findings on a 20-file commit (risk medium), and the
fix loop resolved 7 of 8 tracked findings across 2 rounds with the gate
green and every fix independently verified.

Migration: none required — first release. `tools/sync.sh` installs the
skill tree and the workflow (as the saved zcode workflow
`spec-code-review`); repos that want a gate tuned to their exact CI set
keep a project-scoped workflow copy, which takes precedence there.
