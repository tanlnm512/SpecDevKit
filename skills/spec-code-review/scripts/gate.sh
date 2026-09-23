#!/usr/bin/env bash
# gate.sh — spec-code-review's mechanical gate, portable across repos.
# It detects the target repo's OWN checks, runs them, and reports one
# JSON array on stdout (human progress goes to stderr). Callers branch
# on the per-check exit codes; the script's own exit status is 0 only
# when every detected check passed (or none were detected).
#
# Usage: gate.sh [--repo <dir>] [--base <ref>] [--plan]
#   --repo   target repository (default: the working directory)
#   --base   diff base for path-scoped checks such as bash -n
#            (default: HEAD — the working-tree changes)
#   --plan   print the detection plan as JSON without running anything
#            (every check carries "exit_code": null)
#
# Detection — first marker wins per family, families stack:
#   Makefile targets (test, check, lint)        → make <target>
#   package.json scripts (test, lint, typecheck)→ npm run <script>
#   Cargo.toml                                  → cargo test
#   go.mod                                      → go test ./...
#   python (pyproject/setup.py + tests)         → pytest, falling back
#                                                to unittest discover
#   always, when git is available: bash -n on every *.sh the diff
#   against --base touches (committed or working-tree).
# A family is skipped when its tool is not on PATH — a check that
# cannot run is never silently invented. When nothing is detected the
# JSON array is empty and the gate is green; the skill's SKILL.md tells
# the calling agent to ask the repo for its documented check in that
# case, rather than reviewing with no mechanical floor.
set -uo pipefail

REPO="$(pwd)"
BASE="HEAD"
PLAN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --repo)  REPO="$2"; shift 2 ;;
    --base)  BASE="$2"; shift 2 ;;
    --plan)  PLAN=1; shift ;;
    *) echo "gate.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done
REPO="$(cd "$REPO" 2>/dev/null && pwd)" || {
  echo "gate.sh: --repo is not a directory" >&2; exit 2; }

# Per-check timeout where a timeout binary exists (macOS ships none by
# default; gtimeout from coreutils is honored).
TIMEOUT_BIN="$(command -v timeout || command -v gtimeout || true)"
CHECK_TIMEOUT="${GATE_CHECK_TIMEOUT:-600}"

TALLY="$(mktemp)"
TAILDIR="$(mktemp -d)"
trap 'rm -rf "$TALLY" "$TAILDIR"' EXIT

record() {  # <name> <exit|PLAN> — captures the last check's tail
  local name="$1" code="$2" tf
  tf="$(mktemp "$TAILDIR/tail.XXXXXX")"
  tail -c 8192 "$LAST_OUT" 2>/dev/null > "$tf"
  printf '%s\t%s\t%s\n' "$name" "$code" "${tf##*/}" >> "$TALLY"
}

LAST_OUT="$(mktemp)"

run_check() {  # <name> <cmd...> — runs in the repo, records one row
  local name="$1"; shift
  echo "gate: running $name" >&2
  if [ "$PLAN" = 1 ]; then
    record "$name" "PLAN"
    return 0
  fi
  if [ -n "$TIMEOUT_BIN" ]; then
    (cd "$REPO" && "$TIMEOUT_BIN" "$CHECK_TIMEOUT" "$@") \
      > "$LAST_OUT" 2>&1
  else
    (cd "$REPO" && "$@") > "$LAST_OUT" 2>&1
  fi
  record "$name" "$?"
}

# --- Makefile targets ------------------------------------------------------
if [ -f "$REPO/Makefile" ]; then
  for t in test check lint; do
    grep -Eq "^${t}:" "$REPO/Makefile" && run_check "make ${t}" make "$t"
  done
fi

# --- package.json scripts --------------------------------------------------
if [ -f "$REPO/package.json" ] && command -v npm >/dev/null 2>&1; then
  for s in test lint typecheck; do
    grep -Eq "\"${s}\"[[:space:]]*:" "$REPO/package.json" \
      && run_check "npm run ${s}" npm run "$s" --silent
  done
fi

# --- Rust ------------------------------------------------------------------
if [ -f "$REPO/Cargo.toml" ] && command -v cargo >/dev/null 2>&1; then
  run_check "cargo test" cargo test
fi

# --- Go --------------------------------------------------------------------
if [ -f "$REPO/go.mod" ] && command -v go >/dev/null 2>&1; then
  run_check "go test ./..." go test ./...
fi

# --- Python ----------------------------------------------------------------
if [ -f "$REPO/pyproject.toml" ] || [ -f "$REPO/setup.py" ] \
   || [ -f "$REPO/setup.cfg" ]; then
  # compgen -G, not ls: ls with one missing glob argument exits nonzero
  # even when the other matches, silently skipping the whole family
  if compgen -G "$REPO/tests/test_*.py" >/dev/null \
     || compgen -G "$REPO/test_*.py" >/dev/null; then
    if command -v pytest >/dev/null 2>&1; then
      run_check "pytest" pytest -q
    elif command -v python3 >/dev/null 2>&1; then
      if compgen -G "$REPO/tests/test_*.py" >/dev/null; then
        if [ -f "$REPO/tests/__init__.py" ]; then
          run_check "unittest discover (tests/)" \
            python3 -m unittest discover -s tests -t .
        else
          # a plain tests/ dir is only importable as its own top level
          run_check "unittest discover (tests/)" \
            python3 -m unittest discover -s tests
        fi
      else
        run_check "unittest discover" python3 -m unittest discover
      fi
    fi
  fi
fi

# --- Shell syntax on the diff (always on, git-gated) ------------------------
if command -v git >/dev/null 2>&1 \
   && git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  SH_FILES="$(
    { git -C "$REPO" diff --name-only "$BASE" -- '*.sh' 2>/dev/null
      git -C "$REPO" ls-files --others --exclude-standard -- '*.sh' \
        2>/dev/null
    } | sort -u
  )"
  if [ -n "$SH_FILES" ]; then
    if [ "$PLAN" = 1 ]; then
      record "shell syntax (bash -n, $(printf '%s\n' "$SH_FILES" \
        | grep -c .) changed files)" "PLAN"
    else
      BAD=""
      n=0
      while IFS= read -r f; do
        [ -n "$f" ] || continue
        n=$((n + 1))
        bash -n "$REPO/$f" 2>"$LAST_OUT" || BAD="${BAD}${f} "
      done <<EOF
$SH_FILES
EOF
      printf 'failing: %s\n' "${BAD:-none}" > "$LAST_OUT"
      if [ -n "$BAD" ]; then
        record "shell syntax (bash -n, ${n} changed files)" 1
      else
        record "shell syntax (bash -n, ${n} changed files)" 0
      fi
    fi
  fi
fi

# --- JSON report on stdout, progress already on stderr ----------------------
python3 - "$TALLY" "$TAILDIR" <<'PY'
import json, sys, pathlib
tally, taildir = sys.argv[1], sys.argv[2]
out = []
for line in pathlib.Path(tally).read_text().splitlines():
    if not line.strip():
        continue
    name, code, tfile = line.split("\t", 2)
    tail = ""
    p = pathlib.Path(taildir) / tfile
    if p.is_file():
        tail = "\n".join(p.read_text(errors="replace").splitlines()[-8:])
    out.append({
        "name": name,
        "exit_code": None if code == "PLAN" else int(code),
        "tail": tail,
    })
print(json.dumps(out, indent=2))
PY

if [ "$PLAN" = 1 ]; then
  exit 0
fi
FAILS="$(awk -F'\t' '$2 != "PLAN" && $2 != 0 {n++} END {print n+0}' "$TALLY")"
echo "gate: $FAILS failing check(s)" >&2
[ "$FAILS" -eq 0 ]
