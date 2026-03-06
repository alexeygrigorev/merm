# Task 26: Fix LR and RL Direction Layout (Edges Missing in RL)

## Problem

LR (Left-to-Right) and RL (Right-to-Left) direction layouts have two issues: (1) edges are missing or invisible in the RL case, and (2) the overall aspect ratio and node arrangement differ from mermaid.js.

### Specific Observations

1. **`direction/rl`** (SSIM 0.55): Pymermaid renders three nodes (C, B, A) in a horizontal row but with NO visible edges between them. The mermaid.js reference shows `C <-- B <-- A` with clear left-pointing arrows. The edges are simply absent from the pymermaid output.

2. **`direction/lr`** (SSIM 0.54): Pymermaid renders `A --> B --> C` horizontally, which is correct, but the nodes are oversized (related to Task 22) and the arrowheads are oversized (related to Task 25). With those fixes, LR should score much higher.

3. **RL edge routing bug**: The RL direction likely has a bug where edges are not rendered at all, or are routed to coordinates that place them outside the SVG viewBox.

### Root Cause

For RL: The layout engine may be correctly positioning nodes right-to-left, but the edge routing does not account for the reversed direction, causing edges to be drawn off-screen or with zero length. Alternatively, the SVG viewBox calculation may clip the edges.

For LR: Primarily impacted by the global node-size and arrowhead-size issues (Tasks 22 and 25).

## Acceptance Criteria

- [ ] `direction/rl` renders with visible edges (arrows pointing left) between all connected nodes
- [ ] `direction/lr` renders with visible edges (arrows pointing right) between all connected nodes
- [ ] Node order in RL is reversed compared to LR (rightmost node is first in the flow)
- [ ] The `direction/rl` SSIM score improves from 0.55 to at least 0.70
- [ ] The `direction/lr` SSIM score improves from 0.54 to at least 0.70
- [ ] `direction/bt` continues to render correctly (arrows pointing up)
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: RL edge generation
- Parse `graph RL; A --> B --> C` and render SVG
- Verify SVG contains edge path elements (not zero)
- Verify edge paths have arrowhead markers

### Unit: LR/RL coordinate ranges
- All edge paths fall within the SVG viewBox boundaries
- Edge start/end points connect to node boundaries (not node centers or off-screen)

### Visual: direction comparisons
- Re-render `direction/rl` and confirm edges are visible
- Re-render `direction/lr` and confirm layout matches mermaid.js

## Dependencies

- Task 22 (node sizing) and Task 25 (arrowheads) for full visual match
- But the RL edge-missing bug should be fixed independently

## Estimated Impact

**High** -- directly fixes `direction/lr` (0.54) and `direction/rl` (0.55). Also affects any diagram that uses horizontal direction within subgraphs (e.g., `subgraphs/subgraph_direction`).
