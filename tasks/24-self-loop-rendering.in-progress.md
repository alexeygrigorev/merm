# Task 24: Fix Self-Loop Edge Rendering

## Problem

Self-loop edges (a node pointing to itself, e.g., `A --> A`) currently render as a massive teardrop-shaped loop below the node. The loop should be a compact curve below the node matching the mermaid.js reference at `tests/reference/corpus/basic/self_loop.svg`.

### Specific Observations

1. **`basic/self_loop`** (SSIM 0.56): Pymermaid renders a massive loop that extends far below the node. The loop path is disproportionately large relative to the node, and the end point (`p6`) incorrectly terminates at the top-right of the node instead of the bottom-right, causing the ascending path segment to cut across the node face.

2. **Mermaid.js reference**: The self-loop exits the bottom-left of the node, curves down through a bottom apex roughly 100px below node bottom, and re-enters at the bottom-right of the node. Mermaid.js implements this as three separate path segments routed through two invisible dummy nodes below the main node. The arrowhead appears on the final ascending segment, pointing into the node's right side.

### Root Cause

Two issues in `src/pymermaid/layout/sugiyama.py` function `_route_edges` (around line 523):

1. **End point is wrong**: `p6` is set to `(cx + side_offset, cy - h/2)` (node top), but it should be `(cx + side_offset, cy + h/2)` (node bottom) so the loop re-enters from below.
2. **Loop geometry is too simple**: The current 7-point cubic Bezier does not match the mermaid.js three-segment path shape. The control points need adjustment so the loop has a natural teardrop shape that stays compact below the node.

Additionally, the `_self_loop_path_d` function in `src/pymermaid/render/edges.py` (line 148) generates two cubic Bezier segments from 7 points, but the control point assignments may need revision to produce the correct curve shape.

## Scope

This task covers ONLY the self-loop path geometry and rendering. It does NOT cover:
- Node sizing (Task 22)
- Arrowhead scaling (Task 25)
- General edge routing

## Acceptance Criteria

- [ ] Self-loop edges render as a compact loop below the node for TD/TB graphs
- [ ] The loop path exits from the bottom-left of the node and re-enters at the bottom-right (both start and end y-coordinates equal `cy + h/2`, i.e., the node's bottom edge)
- [ ] The loop's bottom apex extends no more than 120px below the node bottom edge (for a default-sized node)
- [ ] The loop path does not cross through or overlap the node rectangle
- [ ] The arrowhead on the self-loop is the standard arrow marker (same `marker-end` URL as normal edges)
- [ ] The rendered SVG for `tests/fixtures/corpus/basic/self_loop.mmd` contains a valid path element with cubic Bezier commands (C or c) for the self-loop
- [ ] The `basic/self_loop` SSIM score improves from 0.56 to at least 0.65
- [ ] `uv run pytest` passes with no regressions
- [ ] For LR/RL graphs, the self-loop renders to the right/left of the node (direction transform is applied correctly to self-loop points)

## Test Scenarios

### Unit: Self-loop point generation (layout)
- Parse `graph TD\n    A --> A` and run layout; verify the self-loop `EdgeLayout` has `source == target == "A"`
- Verify self-loop start point (p0) y-coordinate equals node center y + node height / 2 (bottom edge)
- Verify self-loop end point (p6) y-coordinate equals node center y + node height / 2 (bottom edge), NOT the top edge
- Verify the bottom apex point has the maximum y-coordinate among all self-loop points
- Verify the bottom apex y-coordinate is between 60px and 120px below the node bottom edge
- Verify all self-loop points have x-coordinates within the range `[cx - w, cx + w]` (loop stays horizontally close to the node)

### Unit: Self-loop path rendering (SVG)
- Render `graph TD\n    A --> A` to SVG; parse the SVG and find the self-loop path element
- Verify the path `d` attribute starts with `M` and contains `C` (cubic Bezier) commands
- Verify the path element has a `marker-end` attribute (arrowhead is present)

### Unit: Self-loop with LR direction
- Parse `graph LR\n    A --> A` and run layout; verify the self-loop points are transformed so the loop goes to the side of the node rather than below

### Integration: Visual comparison
- Re-render `basic/self_loop` and confirm SSIM >= 0.65 against `tests/reference/corpus/basic/self_loop.svg`

### Regression
- Verify `graph TD\n    A --> B` (normal edge, no self-loop) still renders correctly
- Verify `graph TD\n    A --> A\n    A --> B` (mixed self-loop and normal edge) renders without errors

## Dependencies

- None strictly required. Task 22 (node sizing) would help SSIM scores further but is independent -- self-loop geometry should work correctly regardless of node size.

## Estimated Impact

**Medium** -- directly fixes `basic/self_loop` (currently 0.56 SSIM). Self-loops are uncommon but highly visible when broken.
