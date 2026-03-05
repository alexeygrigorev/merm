#!/usr/bin/env bash
# Regenerate reference SVGs for the corpus fixtures using mermaid-cli (mmdc).
#
# Prerequisites:
#   npm install -g @mermaid-js/mermaid-cli
#
# Usage:
#   bash scripts/regenerate_corpus_references.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CORPUS_DIR="$PROJECT_ROOT/tests/fixtures/corpus"
REFERENCE_DIR="$PROJECT_ROOT/tests/reference/corpus"
MMDC_CONFIG="$PROJECT_ROOT/tests/mmdc-config.json"
PUPPETEER_CONFIG="$PROJECT_ROOT/tests/puppeteer-config.json"

if ! command -v mmdc &> /dev/null; then
    echo "Warning: mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli"
    echo "Skipping reference generation."
    exit 0
fi

success=0
fail=0

for fixture in $(find "$CORPUS_DIR" -name "*.mmd" | sort); do
    # Compute relative path from corpus dir for output structure
    relpath="${fixture#$CORPUS_DIR/}"
    outdir="$REFERENCE_DIR/$(dirname "$relpath")"
    name="$(basename "$fixture" .mmd)"

    mkdir -p "$outdir"
    echo "Rendering $relpath..."

    if mmdc -i "$fixture" -o "$outdir/${name}.svg" \
        -t default \
        -c "$MMDC_CONFIG" \
        -p "$PUPPETEER_CONFIG" 2>/dev/null; then
        success=$((success + 1))
    else
        echo "  FAILED: $relpath"
        fail=$((fail + 1))
    fi
done

echo ""
echo "Done. Success: $success, Failed: $fail"
