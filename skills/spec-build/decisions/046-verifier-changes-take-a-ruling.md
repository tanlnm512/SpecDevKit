# D-046: a change to the verifier definitions is surfaced and ruled, never silent

The regression gate (gate.sh) runs the repository's own checks from the
working tree. When an implemented task edits the recipe that runs them —
a Makefile target, a CI workflow, the test-runner configuration — the
gate judging the change got weaker and nothing said so: a task could
drop suites from `make test` or swap the CI definition, and every later
gate read green against a weaker definition of green. Nothing else in
the delivery pass passes or blocks silently; this did.

**Decision** (the pattern D-037 set for hygiene suspects, exactly):

1. **`audit.py verifiers <spec-dir>`** lists every path in the
   implementation scope — the changed-path set `scope` computes against
   the approved base — that defines what the checks check, with what it
   is, lines added and removed, and its ruling state. The patterns are
   conservative and live in one documented place in audit.py: the make
   recipes (Makefile, makefile, GNUmakefile, justfile); CI definitions
   (.github/workflows/*.yml|yaml, .forgejo/workflows/*, .gitlab-ci.yml,
   .circleci/, Jenkinsfile, azure-pipelines.yml, .buildkite/);
   test-runner and lint configuration (pytest.ini, tox.ini, setup.cfg,
   any conftest.py, jest.config.*, vitest.config.*, .mocharc*,
   karma.conf.*, phpunit.xml*, .eslintrc*, .flake8, ruff.toml,
   .pre-commit-config.yaml, .coveragerc); and pyproject.toml /
   package.json only when the diff touches a `[tool.*]` table for
   pytest, coverage, ruff, mypy or tox, or the scripts block of
   package.json — a dependency-only change is not a verifier change
   (the `deps:` lines own dependencies). Outside paths (another
   change's work since approval) are not judged, like scope's. Exit 0
   when nothing is listed or everything is ruled; 1 while an unruled
   verifier change stands.
2. **Rulings live in the delivery block**, the D-037 shape:
   `- Verifier: <path> — <ruling>`, naming the path as `verifiers`
   prints it. `audit.py block` drafts one line per unruled verifier
   change; a covered row reads RULED. At Tier: tiny the same lines are
   read from spec.md's Evidence section, where the delivery block
   lives.
3. **dod grows gate 14 (VERIFIERS)** among the delivery-block gates:
   rows from the diff, rulings from the block; it counts only unruled
   verifier changes and fails while any stands. Gates 11–13 are
   unchanged; the burndown gate moves to 15. Detection is unchanged by
   a ruling: an unruled row still fails.

**Consequences**: the delivery block gains an optional fifth line, and
the owner reads what moved and rules it — revert, or accept with the
reason. Nothing passes silently and nothing blocks silently. A check
strengthening the spec itself commissioned lands through the same
line: the ruling says why the change is the point of the task.
