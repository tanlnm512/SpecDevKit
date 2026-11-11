# D-019 — Dependency audits, dependency changes, CI rows, and the backlog offer

**Status**: accepted (2026-11-11)

## Context

The gate ran the repo's tests and lints but not a dependency audit
the repo had configured. A new dependency in a diff was visible only
if a reviewer happened to read the manifest. In pr mode the PR's own
CI status was never read, so a red CI could sit behind a green local
gate. A review's residual risks ended in the report and went no
further. spec-build now needs the same gate as its regression gate
(spec-build D-036).

## Decision

- **The gate is shared.** spec-build ships `gate.sh` and
  `gate_helpers.py` as byte-identical copies, pinned by
  `tools/tests/test_parity.py`; this skill's copies are the master.
  `GATE_TELEMETRY_SKILL` names the calling skill in telemetry.
- **A dependency audit runs when the repo's own config names it.** An
  npm `audit` script joins the npm family. pip-audit or safety
  mentioned in pyproject, setup.cfg, tox, the Makefile,
  requirements files, pre-commit, or CI workflows runs from the repo
  venv, else PATH. These are `source: repo` rows. The gate detects
  these tools and never installs them. safety counts only as an
  invocation or a dependency spec, because it is also an ordinary
  word.
- **The dependency-manifest row.** In diff mode the gate adds a
  `status: info` built-in row listing the added and removed lines of
  each changed package.json, pyproject.toml, requirements*.txt, go.mod
  and Cargo.toml (capped to fit the row tail). The row is never red.
  The report prints its lines and the gate note asks for every new
  dependency to be named.
- **CI rows in pr mode.** With `gh` on PATH, `gh pr checks` adds one
  `source: ci` row per check. A failing or cancelled check fails the
  gate. A pending check is shown as pending and is not a failure.
  `O gate --pr N` re-reads them.
- **The backlog offer.** When the repo keeps `specs/BACKLOG.md`,
  `report` returns `backlog_offer`, one line per residual risk in the
  kit's backlog shape. The session offers these lines and appends
  them only on the user's yes.

## Consequences

Gate rows gain the statuses `info`, `pending`, and `skipped`, and the
source `ci`. The report header counts CI rows apart from built-in
rows. A repo whose only detected check is its dependency audit has a
mechanical floor of that audit alone. The note says what ran.
