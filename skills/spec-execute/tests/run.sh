#!/usr/bin/env bash
# Run the full test suite: every tests/test_*.py. Prefers uvx (system
# python3 may be < 3.10); falls back to python3 where it is new enough.
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
rc=0
for t in tests/test_*.py; do
  echo "== $t"
  "${PY[@]}" "$t" || rc=1
done
exit "$rc"
