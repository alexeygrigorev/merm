#!/usr/bin/env bash
# Run mutation tests with mutmut on pymermaid source code.
#
# Usage:
#   ./scripts/run_mutation_tests.sh                              # Run on all configured modules
#   ./scripts/run_mutation_tests.sh src/merm/parser/flowchart.py # Run on a specific module
#
# Results are stored in .mutmut-cache/ and can be browsed with:
#   uv run mutmut results
#   uv run mutmut browse

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Running mutation tests ==="
echo ""

if [ $# -gt 0 ]; then
    MODULE="$1"
    echo "Running mutmut on module: $MODULE"
    uv run mutmut run --paths-to-mutate "$MODULE"
else
    echo "Running mutmut on all configured paths..."
    uv run mutmut run
fi

echo ""
echo "=== Mutation test results ==="
uv run mutmut results

echo ""
echo "=== Summary ==="
# Parse the results to show a clear score
RESULTS=$(uv run mutmut results 2>&1 || true)
KILLED=$(echo "$RESULTS" | grep -c "^Killed" || echo "0")
SURVIVED=$(echo "$RESULTS" | grep -c "^Survived" || echo "0")
TIMEOUT=$(echo "$RESULTS" | grep -c "^Timeout" || echo "0")
TOTAL=$((KILLED + SURVIVED + TIMEOUT))

if [ "$TOTAL" -gt 0 ]; then
    SCORE=$(echo "scale=1; $KILLED * 100 / $TOTAL" | bc)
    echo "Killed: $KILLED / $TOTAL ($SCORE%)"
    echo "Survived: $SURVIVED"
    echo "Timeout: $TIMEOUT"
else
    echo "No mutation results found."
fi
