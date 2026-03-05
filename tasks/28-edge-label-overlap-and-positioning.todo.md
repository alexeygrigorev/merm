# Task 28: Fix Edge Label Overlap and Background Rendering

## Problem

Edge labels overlap each other when multiple labeled edges converge on the same node, and the label background styling differs from mermaid.js.

### Specific Observations

1. **`edges/labeled_edges`** (SSIM 0.78): Pymermaid renders edge labels ("yes", "no", "long label", "dotted label", "thick label") with gray rectangular backgrounds, positioned along the edge paths. However, when two labeled edges (B->D with "long label" and C->D with "dotted label") converge on node D, the labels overlap horizontally -- "long labe" and "dotted label" merge into an unreadable jumble.

2. **Label background**: Pymermaid uses a gray (#e8e8e8) filled rectangle behind each label. Mermaid.js uses a similar approach but the labels are spaced so they never overlap.

3. **Label positioning on converging edges**: When two edges meet the same target node, both labels are placed at approximately the same y-coordinate, causing horizontal overlap. Mermaid.js offsets them along their respective edge paths so they remain readable.

### Root Cause

The edge label positioning algorithm places labels at the midpoint of each edge path without checking for collisions with other labels. When multiple edges share similar paths (e.g., fan-in to a node), labels end up at the same position.

## Acceptance Criteria

- [ ] Edge labels on converging edges do not overlap
- [ ] Each edge label is positioned along its own edge path at a readable location
- [ ] Label backgrounds match mermaid.js style (light fill, thin border or no border)
- [ ] The `edges/labeled_edges` SSIM improves from 0.78 to at least 0.83
- [ ] Labels on straight vertical/horizontal edges are centered on the edge
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: Label collision detection
- Two labels at the same position are offset apart
- Labels on non-overlapping edges are not moved

### Unit: Label positioning
- Label on a vertical edge is centered horizontally on the edge
- Label on a diagonal edge is positioned at the midpoint of the path

### Visual: labeled_edges
- Re-render `edges/labeled_edges` and confirm no label overlap
- Confirm "long label" and "dotted label" are both fully readable

## Dependencies

- Task 22 (node sizing) and Task 25 (edge stroke) for overall proportions

## Estimated Impact

**Medium** -- directly improves `edges/labeled_edges` (0.78) and any other diagram with edge labels. Labeled edges are common in real-world flowcharts.
