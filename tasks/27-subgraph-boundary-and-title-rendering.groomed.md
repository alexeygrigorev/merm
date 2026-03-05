# Task 27: Fix Subgraph Boundary Calculation and Title Positioning

## Problem

Subgraph containers are incorrectly sized and positioned relative to their child nodes, and subgraph titles are clipped or mispositioned. This affects all subgraph-related comparisons.

### Specific Observations

1. **`subgraphs/subgraph_with_title`** (SSIM 0.33 -- worst overall): Pymermaid renders the "Database Layer" subgraph title partially visible, but the subgraph boundary box is too narrow and extends below the diagram. The outer subgraph boundary appears to wrap incorrectly around nodes that partially overlap its edges. In mermaid.js, the two subgraphs (one containing Server, another containing Primary/Cache/Replica) are arranged as two separate side-by-side boxes with clean boundaries.

2. **`subgraphs/cross_boundary_edges`** (SSIM 0.34): Pymermaid renders nodes A, B, C, D vertically stacked with overlapping subgraph boundaries. The "Group 2" subgraph's boundary cuts through the middle of the diagram. In mermaid.js, the two subgroups are clearly separated side-by-side.

3. **`subgraphs/sibling_subgraphs`** (SSIM 0.64): Pymermaid renders "Left Side" and "Right Side" subgraphs stacked vertically as a single column. Mermaid.js renders them as two separate boxes stacked vertically but properly separated with clear titles.

4. **`subgraphs/nested_subgraphs`** (SSIM 0.70): The "Outer" label is clipped at the left edge ("uter" is visible). The subgraph boundaries are too narrow to contain their title text.

5. **Title clipping**: Subgraph titles (e.g., "Outer", "Database Layer") are positioned at the top-left of the subgraph boundary but the boundary box does not account for the title width, causing text to overflow to the left.

### Root Cause

Multiple interacting issues:
- `_compute_subgraph_layouts()` in `src/pymermaid/layout/sugiyama.py` computes boundary width/height purely from child node positions without considering the measured width of the title text. The boundary must be at least as wide as the title.
- The fallback bbox computation in `_render_subgraph_recursive()` in `src/pymermaid/render/svg.py` has the same deficiency.
- Title text is placed at `(sx + 8, sy + 14)` without verifying that `sx + 8 + title_text_width <= sx + sw`. If the boundary is narrower than the title, the title overflows.
- Sibling subgraphs are not laid out side-by-side (same issue as disconnected components in Task 23, but within the subgraph context).
- Cross-boundary edges cause subgraph boxes to overlap because the layout does not properly separate subgraph regions.

### Key Files

- `src/pymermaid/layout/sugiyama.py` -- `_compute_subgraph_layouts()` (line ~702) computes subgraph bounding boxes
- `src/pymermaid/render/svg.py` -- `_render_subgraph_recursive()` (line ~326) renders the rect + title
- `tests/test_subgraph.py` -- existing subgraph tests (extend these)

## Acceptance Criteria

### Boundary containment
- [ ] Every child node's bounding box (x, y, width, height) is fully contained within its parent subgraph boundary rect, verifiable by: `node.x >= sg.x` and `node.y >= sg.y` and `node.x + node.width <= sg.x + sg.width` and `node.y + node.height <= sg.y + sg.height`
- [ ] Subgraph boundary provides at least 12px of padding on all sides between the boundary edge and the nearest child node edge
- [ ] Subgraph boundary provides at least 20px of top padding (above the topmost child node) to leave room for the title text

### Title rendering
- [ ] The title text element's x attribute is >= the boundary rect's x attribute (no leftward overflow)
- [ ] The subgraph boundary width is >= the measured title text width + 16px (8px margin on each side), so the title never extends beyond the right edge of the boundary
- [ ] The title text baseline (y attribute) is positioned within the top padding area, above any child nodes

### Nested subgraph containment
- [ ] For nested subgraphs, the inner subgraph boundary rect is fully contained within the outer subgraph boundary rect (same containment check as nodes)
- [ ] Outer subgraph boundary has additional padding beyond the inner subgraph boundary (not flush)

### Sibling subgraph separation
- [ ] Two sibling subgraphs at the same nesting level do not overlap (their boundary rects have zero intersection area)
- [ ] There is visible spacing (>= 8px gap) between sibling subgraph boundary rects

### No regressions
- [ ] `uv run pytest` passes with no regressions in existing tests
- [ ] Non-subgraph diagrams (basic, text, edges, shapes, styling categories) are not affected by these changes

### SSIM improvement targets
- [ ] The `subgraphs/subgraph_with_title` SSIM improves from 0.33 to at least 0.55
- [ ] The `subgraphs/nested_subgraphs` SSIM improves from 0.70 to at least 0.78

## Test Scenarios

### Unit: Boundary fully contains child nodes (extend TestLayoutSubgraphGrouping)
- Create a subgraph with 3 nodes of varying sizes; verify all node bounding boxes are strictly within the subgraph boundary
- Create a subgraph with a single wide node (long label); verify the boundary width >= node width + 2 * padding

### Unit: Boundary width accounts for title text
- Create a subgraph with title "Database Layer" and a single small node (label "A"); verify `sgl.width >= measure_text("Database Layer", 12)[0] + 16`
- Create a subgraph with a very short title ("X") and wide nodes; verify the boundary width is driven by the nodes, not the title
- Create a subgraph with no title (title=None); verify the boundary is computed from nodes alone without error

### Unit: Title positioned within boundary (extend TestRendererSubgraph)
- Render a subgraph with title "Outer Group"; parse the SVG; verify `text_el.x >= rect.x` and `float(text_el.x) + title_text_width <= float(rect.x) + float(rect.width)`
- Render a subgraph with a long title "This Is A Very Long Subgraph Title"; verify the boundary rect is wide enough that the title does not overflow

### Unit: Nested subgraph containment (extend TestLayoutSubgraphGrouping)
- Create outer subgraph containing inner subgraph; verify inner boundary is strictly within outer boundary with padding on all four sides
- Create 3 levels of nesting (outer > middle > inner); verify each level is contained within its parent

### Unit: Sibling subgraph non-overlap
- Create two sibling subgraphs at the same level, each with 2 nodes; verify their boundary rects do not overlap (max(sg1.x, sg2.x) >= min(sg1.x + sg1.width, sg2.x + sg2.width) OR max(sg1.y, sg2.y) >= min(sg1.y + sg1.height, sg2.y + sg2.height))
- Create three sibling subgraphs; verify no pair overlaps

### Integration: End-to-end subgraph rendering
- Parse, layout, and render `subgraphs/subgraph_with_title` fixture; parse the SVG output; verify all subgraph `<rect>` elements contain their child `<g class="node">` elements positionally
- Parse, layout, and render `subgraphs/nested_subgraphs` fixture; find the `<text>` element containing "Outer"; verify its x coordinate is >= the corresponding `<rect>` x coordinate

### Visual: subgraph comparisons
- Re-render `subgraphs/subgraph_with_title` and confirm title is visible and boundaries are correct
- Re-render `subgraphs/nested_subgraphs` and confirm "Outer" label is not clipped
- Re-render `subgraphs/cross_boundary_edges` and confirm boundaries do not overlap

## Dependencies

- Task 22 (node sizing) -- boundary calculations depend on correct node dimensions. **Status: todo.** This task can proceed independently but final SSIM targets may require Task 22 to be done.
- Task 23 (disconnected components) -- sibling subgraphs may benefit from side-by-side layout logic. **Status: todo.** Overlapping sibling subgraph separation is in-scope for this task regardless.

## Estimated Impact

**Very High** -- directly fixes the 4 worst subgraph cases (SSIM 0.33, 0.34, 0.64, 0.70) and improves all 6 subgraph comparisons.
