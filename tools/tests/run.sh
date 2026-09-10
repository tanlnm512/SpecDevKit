#!/usr/bin/env bash
# Run the shared install-tooling suite: every tools/tests/test_*.py (as
# opposed to skills/<name>/tests/, each skill's own scripts' suite).
# Prefers uvx (system python3 may be < 3.10); falls back to python3
# where it is new enough.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if command -v uvx >/dev/null 2>&1; then
  PY=(uvx python@3.12)
else
  PY=(python3)
fi
rc=0
for t in tests/test_*.py; do
  echo "== $t"
  "${PY[@]}" "$t" || rc=1
done
exit "$rc"
