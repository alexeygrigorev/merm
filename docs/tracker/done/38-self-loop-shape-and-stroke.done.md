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

## Scope

This task covers the self-loop path geometry (shape and width), stroke styling, and arrowhead re-entry placement. Changes are expected in:
- `src/pymermaid/layout/sugiyama.py` -- self-loop point generation (the 13-point Bezier control points around line 533)
- `src/pymermaid/render/edges.py` -- possibly `_self_loop_path_d()` if point count changes, and stroke-width handling for self-loop edges

Does NOT cover: general edge routing, node sizing, or non-self-loop arrowhead issues (those are task 37).

## Acceptance Criteria

- [ ] Self-loop horizontal spread (max x minus min x of the loop path points) is >= 80% of the node width
- [ ] The self-loop end point (p12) has y-coordinate equal to `cy + h/2` (node bottom edge), NOT `cy - h/2` (node top edge) -- the arrowhead must re-enter from below
- [ ] The self-loop start point (p0) has y-coordinate equal to `cy + h/2` (node bottom edge)
- [ ] The SVG `<path>` element for a self-loop edge has `stroke-width` equal to `"1"` (same as `EdgeType.arrow` normal edges, not thicker)
- [ ] Loop drop below node bottom is between 1.5x and 2.5x node height (bottom apex y > node bottom y + 1.5*h)
- [ ] The loop path does not cross through or overlap the node rectangle
- [ ] Self-loop with edge label (`A -->|text| A`) renders the label centered below the node, inside the loop area
- [ ] `uv run pytest` passes with no regressions
- [ ] For LR/RL directions, the self-loop geometry is correctly transformed (loop appears beside the node, not below)

### PNG Verification (mandatory)

- [ ] Render `tests/fixtures/corpus/basic/self_loop.mmd` to SVG then to PNG with cairosvg and visually verify the loop has a wide leaf/oval shape roughly as wide as the node, matching `tests/reference/corpus/basic/self_loop.svg`
- [ ] Render a self-loop with label (`graph TD\n    A -->|loop| A`) to SVG then to PNG with cairosvg and visually verify the label text is readable and centered below the node
- [ ] Render a diagram with both a self-loop and a normal edge (`graph TD\n    A --> A\n    A --> B`) to PNG with cairosvg and visually verify the self-loop stroke width matches the normal edge stroke width (they should look the same thickness)

## Test Scenarios

### Unit: Loop geometry (layout points)
- Parse `graph TD\n    A --> A`, run layout, get the self-loop `EdgeLayout`
- Verify `edge_layout.source == edge_layout.target == "A"`
- Verify start point (p0) y == node center y + node height / 2 (bottom edge)
- Verify end point (p12) y == node center y + node height / 2 (bottom edge), NOT the top edge
- Verify the maximum x spread of loop points (max_x - min_x) >= 0.8 * node_width
- Verify the bottom apex point y is between `bot + 1.5*h` and `bot + 2.5*h`
- Verify no loop control point has y < node top (loop does not go above node)

### Unit: Stroke width in SVG
- Render `graph TD\n    A --> A` to SVG, parse the SVG XML
- Find the self-loop `<path>` element (inside the `<g>` with `data-edge-source == data-edge-target`)
- Assert `stroke-width` attribute == `"1"`
- Render `graph TD\n    A --> A\n    A --> B`, parse SVG, verify both the self-loop and normal edge paths have identical `stroke-width`

### Unit: Arrowhead marker on self-loop
- Render `graph TD\n    A --> A` to SVG, parse it
- Verify the self-loop path has a `marker-end` attribute (arrowhead is present)

### Unit: Self-loop with label
- Render `graph TD\n    A -->|loop text| A` to SVG
- Verify the SVG contains a `<text>` element with content "loop text"
- Verify the label y-coordinate is below the node bottom edge

### Unit: LR direction
- Parse `graph LR\n    A --> A`, run layout
- Verify the self-loop points are transformed so the loop extends horizontally (to the right or left of the node), not vertically below

### Regression
- Verify `graph TD\n    A --> B` (normal edge, no self-loop) still renders correctly
- Verify `graph TD\n    A --> A\n    A --> B` (mixed) renders without errors and both edges are present in SVG

## Dependencies

- Task 37 (arrow-node gap) is in-progress -- arrowhead refX fix may affect self-loop marker placement. If task 37 changes marker definitions, self-loop arrowhead alignment may need adjustment. However, this task can proceed independently since the core work is on loop geometry and stroke width.
