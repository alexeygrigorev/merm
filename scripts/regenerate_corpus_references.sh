#!/usr/bin/env bash
# Regenerate reference PNGs for the corpus fixtures using mermaid-cli (mmdc).
#
# We render directly to PNG (not SVG) because mmdc v11 uses <foreignObject>
# with HTML labels, which cairosvg cannot render. Direct PNG output via
# Puppeteer preserves all text labels.
#
# Prerequisites:
#   npm install -g @mermaid-js/mermaid-cli
#
# Usage:
#   bash scripts/regenerate_corpus_references.sh
#   bash scripts/regenerate_corpus_references.sh -j 4   # parallel with 4 jobs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CORPUS_DIR="$PROJECT_ROOT/tests/fixtures/corpus"
REFERENCE_DIR="$PROJECT_ROOT/tests/reference/corpus"
MMDC_CONFIG="$PROJECT_ROOT/tests/mmdc-config.json"
PUPPETEER_CONFIG="$PROJECT_ROOT/tests/puppeteer-config.json"

JOBS=1
while getopts "j:" opt; do
    case $opt in
        j) JOBS="$OPTARG" ;;
        *) echo "Usage: $0 [-j JOBS]"; exit 1 ;;
    esac
done

if ! command -v mmdc &> /dev/null; then
    echo "Warning: mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli"
    echo "Skipping reference generation."
    exit 0
fi

render_one() {
    local fixture="$1"
    local relpath="${fixture#$CORPUS_DIR/}"
    local outdir="$REFERENCE_DIR/$(dirname "$relpath")"
    local name
    name="$(basename "$fixture" .mmd)"

    mkdir -p "$outdir"

    if mmdc -i "$fixture" -o "$outdir/${name}.png" \
        -t default \
        -b white \
        -c "$MMDC_CONFIG" \
        -p "$PUPPETEER_CONFIG" 2>/dev/null; then
        echo "OK: $relpath"
    else
        echo "FAILED: $relpath" >&2
        return 1
    fi
}
export -f render_one
export CORPUS_DIR REFERENCE_DIR MMDC_CONFIG PUPPETEER_CONFIG

FIXTURES=$(find "$CORPUS_DIR" -name "*.mmd" | sort)
TOTAL=$(echo "$FIXTURES" | wc -l)

echo "Rendering $TOTAL fixtures with $JOBS parallel job(s)..."

if [ "$JOBS" -gt 1 ] && command -v parallel &> /dev/null; then
    # GNU parallel available
    echo "$FIXTURES" | parallel -j "$JOBS" render_one
elif [ "$JOBS" -gt 1 ]; then
    # Fallback to xargs -P
    echo "$FIXTURES" | xargs -P "$JOBS" -I {} bash -c 'render_one "$@"' _ {}
else
    # Sequential
    success=0
    fail=0
    for fixture in $FIXTURES; do
        if render_one "$fixture"; then
            success=$((success + 1))
        else
            fail=$((fail + 1))
        fi
    done
    echo ""
    echo "Done. Success: $success, Failed: $fail"
fi
