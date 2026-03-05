# Task 24: Fix Self-Loop Edge Rendering

## Problem

Self-loop edges (a node pointing to itself, e.g., `A --> A`) are rendered with a grossly oversized loop and arrowhead that obscures the node. The loop should be a small, compact curve to one side of the node.

### Specific Observations

1. **`basic/self_loop`** (SSIM 0.56): Pymermaid renders a massive loop that extends far above and to the right of the node, with an enormous arrowhead that covers the top-left corner of the node. The loop path is taller than the node itself.

2. **Mermaid.js reference**: The self-loop is a compact oval that exits the bottom-left of the node, curves down and around below the node, and re-enters from the bottom-right. The arrowhead is small and proportional.

### Root Cause

The self-loop edge rendering uses a curve path that is scaled relative to the (already oversized) node dimensions, and the arrowhead marker is not scaled down for self-loops. The loop routing algorithm needs a dedicated path for self-edges: exit from one side, make a small loop, re-enter from the same or adjacent side.

## Acceptance Criteria

- [ ] Self-loop edges render as a compact loop below (for TD/TB) or to the side (for LR/RL) of the node
- [ ] The loop size is proportional: roughly 30-40px radius, not larger than the node
- [ ] The arrowhead on self-loops is the same small size as on normal edges
- [ ] The loop does not overlap or obscure the node content
- [ ] The `basic/self_loop` SSIM score improves from 0.56 to at least 0.70
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: Self-loop path generation
- Self-loop on a TD graph produces a path that goes below the node
- Self-loop path start and end points are on the node boundary (not at the center)
- Self-loop path bounding box is no larger than 2x the node dimensions

### Visual: self_loop
- Re-render `basic/self_loop` and confirm loop is compact and proportional

## Dependencies

- Task 22 (node sizing) -- the loop size should be relative to correctly-sized nodes

## Estimated Impact

**Medium** -- directly fixes `basic/self_loop` (0.56). Self-loops are uncommon but highly visible when broken.
