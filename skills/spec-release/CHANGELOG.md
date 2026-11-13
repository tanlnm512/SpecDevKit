# Changelog — spec-release

Release history. The skill began life 2026-11-11 as the kit's release
phase: the `release` HUMAN node spec-build's D-014 deferred.

## 0.1.1 — 2026-11-13

- **Fix:** `cut` keeps the changelog section's `###` group headings in
  the annotated tag's message; git's default cleanup used to strip them.

Migration: none required.
## 0.1.0 — 2026-11-11

- **New skill.** `/spec-release [collect|notes|preflight|cut|verify|status]`
  cuts a release from merged, delivered work: collect the facts since
  the last version tag, propose the SemVer bump, write the changelog
  section and release notes from those facts, gate the cut, then
  commit + tag and publish on two separate yeses; end with a
  post-release checklist (D-001, D-003, D-004, D-005).
- `scripts/release.py` — collect, version, bump, notes, preflight,
  cut, record, publish, verify, status; stdlib-only, `--json` on every
  subcommand, fixed exit codes.
- `Released: <tag> @ <sha>` records on each included spec, beside its
  `Delivered:` record, in a record commit after the tag (D-002).
- One read-only role, `spec-release-manager`, tightens the wording of
  the generated section and traces every bullet to its fact.

Migration: none required — a new skill; install it with
`bash tools/sync.sh` or `/plugin install spec-release@spec-dev-kit`.
