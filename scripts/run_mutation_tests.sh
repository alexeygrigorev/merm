#!/usr/bin/env bash
# Run mutation tests with mutmut on pymermaid source code.
#
# Usage:
#   ./scripts/run_mutation_tests.sh              # Run on all configured modules
#   ./scripts/run_mutation_tests.sh theme.py     # Run on a specific module
#
# Results are stored in .mutmut-cache/ and can be browsed with:
#   uv run mutmut results
#   uv run mutmut browse

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Running mutation tests ==="
echo ""

if [ $# -gt 0 ]; then
    echo "Running mutmut on specific mutants: $*"
    uv run mutmut run "$@"
else
    echo "Running mutmut on all configured paths..."
    uv run mutmut run
fi

echo ""
echo "=== Mutation test results ==="
uv run mutmut results
