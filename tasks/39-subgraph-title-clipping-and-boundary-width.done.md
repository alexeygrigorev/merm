# Task 39: Fix Subgraph Title Clipping and Boundary Width

## Problem

Subgraph titles are clipped on the left side, and subgraph boundaries are too narrow — they don't expand to fit the title text or center around their child nodes.

### Specific Issues

1. **Title clipping**: Subgraph titles overflow to the left of the boundary rect. "outer" shows as "ter", "Left Side" is not visible at all, "inner" shows as "nner"
2. **Boundary too narrow**: The subgraph rect width is based only on child node positions, not accounting for the title text width
3. **Left-aligned instead of centered**: Subgraph boundaries are left-aligned to the leftmost node instead of centered with padding on both sides
4. **No left padding for title**: The title text starts at the very left edge of the rect with no margin

### Affected Files (check all as PNGs)

- `docs/comparisons/subgraphs/nested_subgraphs_pymermaid.svg` — "outer" clipped to "ter", "inner" clipped to "nner"
- `docs/comparisons/subgraphs/sibling_subgraphs_pymermaid.svg` — "Left Side" title missing, "Right Side" partly visible
- `docs/comparisons/subgraphs/single_subgraph_pymermaid.svg` — "My Subgraph" title overlaps the boundary left edge
- `docs/comparisons/subgraphs/subgraph_with_title_pymermaid.svg` — "Database Layer" partly clipped
- `docs/comparisons/subgraphs/cross_boundary_edges_pymermaid.svg` — group titles clipped
- `docs/comparisons/subgraphs/subgraph_direction_pymermaid.svg` — check for same issue

## Acceptance Criteria

- [ ] All subgraph titles are fully visible within the subgraph boundary rect
- [ ] Subgraph boundary rect width is at least as wide as the title text + padding
- [ ] Title text starts with a left margin (at least 8px inside the rect left edge)
- [ ] Subgraph boundaries are centered around child nodes with equal padding on both sides
- [ ] Nested subgraphs: inner boundary is fully contained within outer boundary
- [ ] `uv run pytest` passes with no regressions

### PNG Verification (mandatory)
- [ ] Render `subgraphs/nested_subgraphs` to PNG — "outer" and "inner" titles fully visible
- [ ] Render `subgraphs/sibling_subgraphs` to PNG — "Left Side" and "Right Side" titles fully visible
- [ ] Render `subgraphs/single_subgraph` to PNG — "My Subgraph" title fully visible inside rect
- [ ] Render `subgraphs/subgraph_with_title` to PNG — "Database Layer" and "App Layer" fully visible
- [ ] Render `subgraphs/cross_boundary_edges` to PNG — all group titles visible
- [ ] Render `subgraphs/subgraph_direction` to PNG — title visible

## Test Scenarios

### Unit: Title width drives boundary
- Subgraph with long title "This Is A Very Long Subgraph Title" and one small node — boundary rect width >= title text width + 16px padding
- Subgraph with short title "X" and wide nodes — boundary fits nodes, title is inside

### Unit: Title position
- Parse rendered SVG, verify title `<text>` x-coordinate is >= subgraph `<rect>` x + 8px
- Title y-coordinate is inside the rect (not above or on the top edge)

### Unit: Boundary centering
- Subgraph with one centered node — equal padding on left and right sides of boundary

## Dependencies
- None (supersedes parts of task 27 related to title clipping)
