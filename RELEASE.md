# Release checklist

One ordered pass from a clean tree to a tagged release. A release
requires five agreeing surfaces — semantic version, changelog, manifest
versions, migration note, and end-to-end lifecycle evidence — and every
claim the changelog entry makes must be provable by one of the gates
below. Support claims (platforms, harnesses, dependencies) name only what
the CI matrix actually exercises; a claim with no gate behind it does not
ship.

Work top to bottom; do not tag until every step is green. Run from the
repo root.

## 1. Base

- On `main`, working tree clean: `git status --porcelain` is empty.
- The CI workflow is green on **both** Linux and macOS for the commit
  being released (both test suites, compilation, shell syntax,
  generated-artifact drift, and representative docset checks).

## 2. Version

Bump `skills/<name>/VERSION` and the `metadata.version` line in that
skill's `SKILL.md` frontmatter. The VERSION file is the source of truth;
the frontmatter and the generated manifests are kept equal to it
mechanically (step 5 fails on any mismatch). Pick the semver from the
change: behavior fix → patch, feature → minor, a rename or a contract
users must act on → major.

## 3. Changelog

Prepend a `## <version> — <date>` entry to that skill's `CHANGELOG.md`.
The entry states what changed and carries a `Migration:` note — a
paragraph starting exactly with `Migration:` that gives the upgrade path
and how existing user state is treated; "Migration: none required" spelled
out is still a note. Changelog entries are append-only: never rewrite
history.

## 4. Manifests

Regenerate, never hand-edit:

```bash
python3 tools/plugin-manifest.py
```

This rewrites every `skills/<name>/.claude-plugin/plugin.json` (version
read from the skill's VERSION file) and the marketplace catalog. A manual
edit to a generated manifest is drift, and step 5 catches it.

## 5. Alignment gates

Mechanical — all three must exit 0:

```bash
bash tools/tests/run.sh                   # version triple (VERSION · SKILL.md · plugin.json) + changelog alignment
python3 tools/workflow-defs.py --check    # generated workflows match their sources
python3 tools/plugin-manifest.py --check  # generated manifests match their sources
```

## 6. Quality gates

```bash
bash skills/spec-to-prod/tests/run.sh                                                # the skill's own suite
python3 skills/spec-to-prod/scripts/check.py skills/spec-to-prod/examples/mini-spec/specs/mini-spec   # docset fixture green
python3 tools/tests/test_release.py                                                  # end-to-end lifecycle fixture + release gate
```

This suite carries the lifecycle evidence: the migration fixture tests
(dry-run → apply → apply; the second apply is hash-stable and invents no
evidence) and the acceptance-coverage checker (every FR and acceptance
criterion maps to a test case).

## 7. Clean tree

`git status --porcelain` is empty again — the release changed nothing
that regeneration cannot reproduce. Then tag:

```bash
git tag -a v<version> -m "<version>"
```

Push and publish stay human gates — the pipeline ends at a verified
commit; tagging does not push anything by itself.
