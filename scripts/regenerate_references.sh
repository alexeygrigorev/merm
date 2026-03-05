#!/usr/bin/env bash
# Regenerate reference SVGs from fixture .mmd files using mermaid-cli (mmdc).
#
# Prerequisites:
#   npm install -g @mermaid-js/mermaid-cli
#
# Usage:
#   bash scripts/regenerate_references.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FIXTURES_DIR="$PROJECT_ROOT/tests/fixtures"
REFERENCE_DIR="$PROJECT_ROOT/tests/reference"
MMDC_CONFIG="$PROJECT_ROOT/tests/mmdc-config.json"
PUPPETEER_CONFIG="$PROJECT_ROOT/tests/puppeteer-config.json"

if ! command -v mmdc &> /dev/null; then
    echo "Error: mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli"
    exit 1
fi

mkdir -p "$REFERENCE_DIR"

count=0
for fixture in "$FIXTURES_DIR"/*.mmd; do
    name="$(basename "$fixture" .mmd)"
    echo "Rendering $name..."
    mmdc -i "$fixture" -o "$REFERENCE_DIR/${name}.svg" \
        -t default \
        -c "$MMDC_CONFIG" \
        -p "$PUPPETEER_CONFIG"
    count=$((count + 1))
done

echo "Done. Rendered $count reference SVGs."
