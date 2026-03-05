# Task 25: Fix Arrowhead Size and Edge Stroke Width

## Problem

Arrowheads in pymermaid are dramatically oversized compared to the mermaid.js reference. Edge stroke widths are also too thick. This affects every diagram that has edges.

### Specific Observations

1. **Arrowheads are ~5x too large**: In `basic/two_nodes`, the arrowhead from A to B is a huge triangle roughly 30-40px wide. In mermaid.js, arrowheads are small and sleek, roughly 8-10px wide.

2. **Edge strokes too thick**: The edge lines in pymermaid appear to be 3-5px stroke width. Mermaid.js uses approximately 1-2px strokes for normal edges and ~3px for thick edges.

3. **Thick edges (`==>`) are disproportionately heavy**: In `edges/labeled_edges`, the thick edge from D to E has an enormous arrowhead and very heavy stroke.

4. **Visible across all diagrams**: The oversized arrowheads are visible in every comparison that has edges -- `basic/two_nodes`, `basic/linear_chain`, `basic/diamond`, `basic/fan_in`, `basic/fan_out`, all `edges/*`, all `direction/*`, etc.

### Root Cause

The SVG marker definitions for arrowheads use `markerWidth`/`markerHeight` values and/or `viewBox` dimensions that are too large. The `stroke-width` on edge `<path>` or `<line>` elements is also set too high.

## Acceptance Criteria

- [ ] Normal arrow markers (`-->`) render at approximately 10px x 7px (matching mermaid.js)
- [ ] Edge stroke width for normal edges is ~2px
- [ ] Edge stroke width for thick edges (`==>`) is ~3.5px
- [ ] Edge stroke width for dotted edges (`.->`) is ~2px with appropriate dash pattern
- [ ] Circle endpoints (`--o`) and cross endpoints (`--x`) are proportionally sized
- [ ] The `basic/two_nodes` arrowhead is visually similar to the mermaid.js reference
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: Marker definition dimensions
- Arrow marker SVG element has markerWidth <= 12 and markerHeight <= 10
- Circle endpoint marker is approximately 8px diameter
- Cross endpoint marker arms are approximately 8px

### Unit: Edge stroke widths
- Normal edge (`-->`) has stroke-width of 2
- Thick edge (`==>`) has stroke-width of 3.5
- Dotted edge (`.->`) has stroke-width of 2

### Visual: edge comparisons
- Re-render `basic/two_nodes` and verify arrowhead proportions
- Re-render `edges/thick` and verify thick edge is heavier but not grotesquely so

## Dependencies

- Task 22 (node sizing) should be done first since arrowhead size should be proportional to node size

## Estimated Impact

**Very High** -- affects all 45+ diagrams that have edges. Combined with node sizing fix, this addresses the two most universal issues.
