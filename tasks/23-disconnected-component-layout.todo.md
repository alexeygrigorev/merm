# Task 23: Fix Disconnected Component Layout (Place Side-by-Side Instead of Stacked)

## Problem

When a graph has disconnected components (subgraphs of nodes with no edges between them), pymermaid stacks them vertically with a large gap. Mermaid.js places them side-by-side horizontally.

### Specific Observations

1. **`basic/parallel_paths`** (SSIM 0.44): The diagram has two independent chains: `A-->B` and `C-->D`. Pymermaid renders them stacked vertically (A->B on top, then a big gap, then C->D below). Mermaid.js renders them side-by-side: A->B on the left, C->D on the right, both at the same vertical position.

2. This is one of the lowest SSIM scores (0.44) because the overall layout shape is completely different -- tall and narrow vs. short and wide.

### Root Cause

The Sugiyama layout algorithm likely processes all nodes in a single connected graph. When there are multiple connected components, they need to be laid out independently and then arranged horizontally (or in a grid for many components) rather than simply stacking vertically in the same layering.

## Acceptance Criteria

- [ ] Disconnected components are placed side-by-side horizontally, not stacked vertically
- [ ] Each component is independently laid out with its own layer assignment
- [ ] A configurable gap (default ~50px) separates horizontally-placed components
- [ ] The `basic/parallel_paths` SSIM score improves from 0.44 to at least 0.70
- [ ] Diagrams with a single connected component are unaffected
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: Component detection
- Graph with two disconnected components returns two separate component lists
- Graph with one connected component returns a single list
- Graph with three disconnected components returns three lists

### Unit: Side-by-side placement
- Two components of equal height are placed at the same y-offset
- Two components of different heights are vertically centered relative to each other
- Horizontal gap between components matches the configured spacing

### Visual: parallel_paths
- Re-render `basic/parallel_paths` and confirm side-by-side layout matches mermaid.js

## Dependencies

- Task 22 (node sizing) should ideally be done first so that component sizes are reasonable

## Estimated Impact

**High** -- directly fixes `basic/parallel_paths` (0.44). May also help any other cases where independent subgraphs exist.
