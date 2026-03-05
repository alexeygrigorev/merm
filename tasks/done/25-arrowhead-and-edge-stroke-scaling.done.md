# Task 25: Calibrate Edge Stroke Width and Marker Sizing

## Problem

Edge stroke widths in pymermaid do not match mermaid.js defaults. Normal edges (`-->`) use `stroke-width: 1` but mermaid.js uses approximately 2px. Dotted edges also use 1px when they should be 2px. The arrow markers and their sizing are mostly correct (addressed partially by task 37 which fixed arrow-node gaps), but the visual weight of edges is too thin.

### Current State (verified 2026-03-05)

Rendering edges to PNG and inspecting:

1. **Normal edge stroke too thin**: `_STYLE_MAP[EdgeType.arrow]` uses `stroke-width: 1`. Mermaid.js uses approximately 2px for normal edges. The thin stroke makes edges appear faint against the node outlines.

2. **Dotted edge stroke too thin**: `_STYLE_MAP[EdgeType.dotted]` and `EdgeType.dotted_arrow` use `stroke-width: 1` with `stroke-dasharray: 3`. Mermaid.js uses 2px stroke for dotted edges with a `stroke-dasharray` of approximately `3`.

3. **Open link stroke too thin**: `_STYLE_MAP[EdgeType.open]` uses `stroke-width: 1`. Should be 2px.

4. **Thick edge stroke is correct**: `stroke-width: 3.5` for thick edges matches mermaid.js.

5. **Arrow marker dimensions are correct**: The arrow marker uses `markerWidth=8`, `markerHeight=8`, `viewBox="0 0 10 10"`, `refX=10`, `markerUnits=userSpaceOnUse`. This produces well-proportioned arrowheads. No change needed for marker geometry.

6. **Circle endpoint marker is slightly large**: `markerWidth=11`, `markerHeight=11` -- the circle is somewhat prominent. Could be reduced to 8-9 for a more subtle look matching mermaid.js.

7. **Dash pattern for dotted edges**: The current `stroke-dasharray: 3` produces very short dashes. Mermaid.js uses approximately `stroke-dasharray: 3` as well, so this is acceptable.

### Key Code Locations

- **Edge style map**: `src/pymermaid/render/edges.py` lines 180-188 (`_STYLE_MAP`)
- **Arrow marker definition**: `src/pymermaid/render/edges.py` lines 43-57 (`_marker_arrow`)
- **Circle marker definition**: `src/pymermaid/render/edges.py` lines 60-74 (`_marker_circle`)
- **Cross marker definition**: `src/pymermaid/render/edges.py` lines 77-90 (`_marker_cross`)
- **CSS edge stroke**: `src/pymermaid/render/svg.py` line 62 (`.edge path` CSS rule references `theme.edge_stroke`)

### What NOT to Change

- Arrow marker geometry (triangle path, viewBox, refX, refY) -- these are working correctly after task 37
- Catmull-Rom smoothing / edge path generation -- working correctly
- Self-loop path generation -- that is tasks 24/38
- Edge label rendering -- working correctly

## Acceptance Criteria

- [ ] Normal edge (`-->`) renders with `stroke-width` of 2
- [ ] Open link (`---`) renders with `stroke-width` of 2
- [ ] Dotted edge (`-.->`) renders with `stroke-width` of 2 and `stroke-dasharray` of `3`
- [ ] Dotted arrow (`-.->`) renders with `stroke-width` of 2 and `stroke-dasharray` of `3`
- [ ] Thick edge (`==>`) remains at `stroke-width` of 3.5 (no change)
- [ ] Circle endpoint marker (`--o`) has `markerWidth` and `markerHeight` reduced to 8 (from 11)
- [ ] Cross endpoint marker (`--x`) has `markerWidth` and `markerHeight` adjusted to 8 (from 11)
- [ ] Edge stroke is visually balanced with node stroke-width (node is 1px, edge is 2px -- this matches mermaid.js proportions)
- [ ] `uv run pytest` passes with no regressions

### PNG Verification (mandatory)

- [ ] Render `edges/arrow.mmd` to PNG -- edges are clearly visible, not faint
- [ ] Render `edges/thick.mmd` to PNG -- thick edges are heavier than normal but not grotesque
- [ ] Render `edges/dotted.mmd` to PNG -- dashed pattern is clear, not too thin to see
- [ ] Render `edges/circle_endpoint.mmd` to PNG -- circle markers are proportional (not oversized)
- [ ] Render `edges/cross_endpoint.mmd` to PNG -- cross markers are proportional
- [ ] Render `edges/labeled_edges.mmd` to PNG -- all edge types render with correct weights, labels readable

## Test Scenarios

### Unit: Edge stroke widths in SVG output
- Render `graph TD\n    A --> B`, extract `<path>` element, verify `stroke-width="2"` (or absence means CSS default of 2)
- Render `graph TD\n    A ==> B`, extract `<path>`, verify `stroke-width="3.5"`
- Render `graph TD\n    A -.-> B`, extract `<path>`, verify `stroke-width="2"` and `stroke-dasharray="3"`
- Render `graph TD\n    A --- B`, extract `<path>`, verify `stroke-width="2"`

### Unit: Marker dimensions in SVG defs
- Parse SVG output, find `<marker id="arrow">`, verify `markerWidth="8"` and `markerHeight="8"` (unchanged)
- Parse SVG output, find `<marker id="circle-end">`, verify `markerWidth` is 8 (reduced from 11)
- Parse SVG output, find `<marker id="cross-end">`, verify `markerWidth` is 8 (reduced from 11)

### Unit: _STYLE_MAP values
- Import `_STYLE_MAP` from `pymermaid.render.edges`, verify `EdgeType.arrow` maps to `stroke-width: 2`
- Verify `EdgeType.thick_arrow` maps to `stroke-width: 3.5`
- Verify `EdgeType.dotted_arrow` maps to `stroke-width: 2` with dasharray

### Integration: Visual weight balance
- Render `basic/two_nodes.mmd` to SVG, verify edge stroke-width (2) is thicker than node stroke-width (1) -- this is the mermaid.js pattern where edges are visually prominent against lighter node borders

### Integration: All edge types in one diagram
- Render `edges/labeled_edges.mmd` (has normal, dotted, thick edges), verify each edge path has the correct stroke-width attribute

## Dependencies

- Task 22 (node sizing) should ideally be done first, since edge visual weight should be proportional to node size. However, this task can proceed independently since it only modifies stroke widths and marker sizes, not positions.
- Task 37 (arrow-node gap) is done -- marker refX values are correct.

## Estimated Impact

**Medium-High** -- affects all 45+ diagrams with edges. Increasing normal edge stroke from 1 to 2 makes edges more visible and matches mermaid.js proportions. Reducing circle/cross marker size makes endpoint markers less distracting.
