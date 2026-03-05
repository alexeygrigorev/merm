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
- Subgraph boundary rectangles are calculated based only on child node positions, without accounting for title text width
- Sibling subgraphs are not laid out side-by-side (same issue as disconnected components in Task 23, but within the subgraph context)
- Cross-boundary edges cause subgraph boxes to overlap because the layout does not properly separate subgraph regions

## Acceptance Criteria

- [ ] Subgraph boundary rectangles fully contain all child nodes with appropriate padding (~16px)
- [ ] Subgraph titles are fully visible and do not overflow the subgraph boundary
- [ ] Subgraph title is positioned inside the top-left of the boundary with proper margin
- [ ] The subgraph boundary width is at least as wide as the title text
- [ ] Sibling subgraphs at the same nesting level are separated with clear spacing
- [ ] The `subgraphs/subgraph_with_title` SSIM improves from 0.33 to at least 0.55
- [ ] The `subgraphs/nested_subgraphs` SSIM improves from 0.70 to at least 0.78
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: Boundary calculation
- Subgraph with two nodes has boundary that fully encloses both nodes plus padding
- Subgraph with a long title has boundary at least as wide as the title
- Nested subgraph has outer boundary enclosing inner boundary plus padding

### Unit: Title positioning
- Title text x-coordinate is >= subgraph boundary left edge + margin
- Title text is fully within the subgraph boundary (no overflow)

### Visual: subgraph comparisons
- Re-render `subgraphs/subgraph_with_title` and confirm title is visible and boundaries are correct
- Re-render `subgraphs/nested_subgraphs` and confirm "Outer" label is not clipped

## Dependencies

- Task 22 (node sizing) -- boundary calculations depend on correct node dimensions
- Task 23 (disconnected components) -- sibling subgraphs may benefit from side-by-side logic

## Estimated Impact

**Very High** -- directly fixes the 4 worst subgraph cases (SSIM 0.33, 0.34, 0.64, 0.70) and improves all 6 subgraph comparisons.
