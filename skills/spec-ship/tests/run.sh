#!/usr/bin/env bash
# Run the spec-ship suite: every tests/test_*.py.
# Prefers a local python3 >= 3.10 (works in restricted environments);
# falls back to uvx python@3.12 only when python3 is missing or too old.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if command -v python3 >/dev/null 2>&1 \
   && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  PY=(python3)
elif command -v uvx >/dev/null 2>&1; then
  PY=(uvx python@3.12)
else
  echo "error: need python3 >= 3.10 on PATH, or uvx" >&2
  exit 2
fi
shopt -s nullglob
tests=(tests/test_*.py)
if [ "${#tests[@]}" -eq 0 ]; then
  echo "TODO: spec-ship has no tests/test_*.py yet — nothing was run, nothing is proven"
  exit 0
fi
rc=0
for t in "${tests[@]}"; do
  echo "== $t"
  "${PY[@]}" "$t" || rc=1
done
exit "$rc"
