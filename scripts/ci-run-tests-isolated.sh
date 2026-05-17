#!/bin/bash
# Run the familydiagram test suite with one pytest process per test file.
#
# Why: the suite has a pre-existing test-isolation defect — running all files
# in a single pytest process leaks Qt resources (threads/timers/NAMs) that
# accumulate and deadlock the process ~5-8% in (a native hang no Python-level
# timeout can interrupt). Every file passes on its own. A fresh process per
# file resets that accumulation, so the suite runs deterministically. An OS
# `timeout` bounds any genuinely hung file instead of stalling the job.
#
# Env:
#   TEST_JOBS         parallel files (default: CPU count)
#   TEST_FILE_TIMEOUT per-file wall timeout seconds (default: 240)
#   TEST_PATH         test root (default: pkdiagram/tests)
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
TEST_PATH="${TEST_PATH:-pkdiagram/tests}"
TIMEOUT="${TEST_FILE_TIMEOUT:-240}"
if [ -z "${TEST_JOBS:-}" ]; then
  TEST_JOBS="$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 3)"
fi

RESULTS_DIR="$(mktemp -d)"
trap 'rm -rf "$RESULTS_DIR"' EXIT

# macOS runners have no GNU `timeout`. Prefer timeout/gtimeout if present,
# else fall back to a perl alarm wrapper (SIGALRM default-terminates the
# child — kills even a native Qt hang since pytest installs no SIGALRM handler).
if command -v timeout >/dev/null 2>&1; then
  RUNTO() { timeout "$1" "${@:2}"; }
elif command -v gtimeout >/dev/null 2>&1; then
  RUNTO() { gtimeout "$1" "${@:2}"; }
else
  RUNTO() { perl -e 'alarm shift; exec @ARGV' "$@"; }
fi
export PY TIMEOUT RESULTS_DIR
export -f RUNTO

run_one() {
  f="$1"
  safe="$(echo "$f" | tr '/.' '__')"
  out="$(QT_QPA_PLATFORM=offscreen RUNTO "$TIMEOUT" \
        "$PY" -m pytest "$f" -q --tb=short -p no:cacheprovider 2>&1)"
  rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "PASS $f"
  elif [ "$rc" -eq 5 ]; then
    echo "PASS $f (no tests collected)"
  elif [ "$rc" -eq 124 ] || [ "$rc" -eq 142 ]; then
    echo "TIMEOUT $f"
    { echo "### TIMEOUT after ${TIMEOUT}s: $f"; echo "$out" | tail -20; } \
      > "$RESULTS_DIR/$safe.fail"
  else
    echo "FAIL($rc) $f"
    { echo "### FAIL($rc): $f"; echo "$out" | tail -40; } \
      > "$RESULTS_DIR/$safe.fail"
  fi
}
export -f run_one

echo "Isolated test run: jobs=$TEST_JOBS file-timeout=${TIMEOUT}s path=$TEST_PATH"
find "$TEST_PATH" -name 'test_*.py' | sort \
  | xargs -P "$TEST_JOBS" -I{} bash -c 'run_one "{}"'

fails=$(ls "$RESULTS_DIR"/*.fail 2>/dev/null | wc -l | tr -d ' ')
echo ""
echo "================ ISOLATED SUITE SUMMARY ================"
if [ "$fails" -eq 0 ]; then
  echo "All test files passed."
  exit 0
fi
echo "$fails file(s) failed or timed out:"
for ff in "$RESULTS_DIR"/*.fail; do
  echo ""
  cat "$ff"
done
exit 1
