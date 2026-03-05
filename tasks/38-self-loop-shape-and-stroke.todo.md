# Task 38: Fix Self-Loop Shape, Stroke Width, and Arrowhead Placement

## Problem

The self-loop rendering has multiple issues compared to the mermaid.js reference:

### Current (pymermaid) vs Reference (mermaid.js)

1. **Shape is wrong**: Our loop is a narrow V/teardrop. The reference is a wider leaf/oval shape with more horizontal spread
2. **Arrowhead placement wrong**: Our arrowhead points upward at the top-right corner of the node. The reference arrowhead re-enters from below, pointing upward into the bottom-right area of the node
3. **Edge stroke too thick**: The self-loop line is noticeably thicker than in the reference
4. **Loop too narrow**: The horizontal spread of the loop is much less than the node width. Reference loop is roughly as wide as the node

### PNG Evidence

- Current: `docs/comparisons/basic/self_loop_pymermaid.png`
- Reference: `tests/reference/corpus/basic/self_loop.svg` (render to PNG to compare)

## Acceptance Criteria

- [ ] Self-loop has a wider leaf/oval shape, roughly as wide as the node
- [ ] Arrowhead re-enters the node from below (bottom-right area), not from the top
- [ ] Edge stroke width matches normal edges (stroke-width: 1, not thicker)
- [ ] Loop exits from bottom-left of node, curves down and outward, then back up to bottom-right
- [ ] Loop drop below node is proportional (~1.5-2x node height)
- [ ] Self-loop with edge label renders the label centered below the node inside the loop

### PNG Verification (mandatory)
- [ ] Render `basic/self_loop` to PNG and verify shape matches mermaid.js reference
- [ ] Render a self-loop with label (`A -->|loop| A`) to PNG and verify label is readable
- [ ] Verify stroke width visually matches normal edges in the same diagram

## Test Scenarios

### Unit: Loop geometry
- Self-loop horizontal spread >= 50% of node width
- Self-loop exit point is on bottom edge of node (not side)
- Self-loop re-entry point is on bottom edge of node (not top)
- Arrowhead orientation points upward (into node from below)

### Unit: Stroke width
- Self-loop edge has same stroke-width attribute as normal edges

### Visual: Comparison
- Render to PNG, compare side-by-side with mmdc reference

## Dependencies
- Task 37 (arrow-node gap) — arrowhead refX fix may affect self-loop marker placement
