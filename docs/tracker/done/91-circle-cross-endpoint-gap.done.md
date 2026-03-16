# Issue 91: Circle and cross endpoint markers don't touch target node

## Problem

Edges with circle (`--o`) or cross (`--x`) endpoint markers have a visible gap between the marker and the target node. The path is shortened by `_MARKER_SHORTEN=8` (designed for arrow markers), but circle-end (`refX=5`) and cross-end (`refX=5.5`) markers are smaller and don't extend far enough to reach the node border.

Reproduction: `tests/fixtures/corpus/edges/circle_endpoint.mmd` and `cross_endpoint.mmd`

## Root Cause

In `src/merm/render/edges.py`, the `_MARKER_SHORTEN` constant was originally a single value (8px) applied to all edge types. A per-marker-type dictionary `_MARKER_SHORTEN_BY_ARROW` was added with values: arrow=8.0, circle=5.0, cross=5.5. However, these values may still not produce correct visual results -- the markers may still leave a gap or overshoot depending on how refX interacts with the path endpoint after shortening.

The correct relationship: path is shortened by N pixels, and the marker's refX positions the marker shape relative to the new path endpoint. For the marker to appear to touch the node border, the shortening distance plus the marker's forward extent (from refX to the marker's leading edge) must equal the original distance from path end to node border.

## Dependencies

None.

## Acceptance Criteria

- [ ] Circle endpoint markers (`--o`) visually touch the target node border with no visible gap
- [ ] Cross endpoint markers (`--x`) visually touch the target node border with no visible gap
- [ ] Arrow markers (`-->`) continue to work correctly -- arrowhead tip touches the node border
- [ ] The fix uses per-marker-type shortening values (already partially implemented in `_MARKER_SHORTEN_BY_ARROW`)
- [ ] Edges with no marker (e.g., `---`) still terminate exactly at the node border
- [ ] Existing tests continue to pass (`uv run pytest`)
- [ ] Render circle and cross endpoint fixtures to PNG with cairosvg and visually verify markers touch nodes

## PNG Verification Checklist

- [ ] Render `tests/fixtures/corpus/edges/circle_endpoint.mmd` to SVG, then convert to PNG with cairosvg
- [ ] Render `tests/fixtures/corpus/edges/cross_endpoint.mmd` to SVG, then convert to PNG with cairosvg
- [ ] Render a mixed-marker flowchart (`A -->|arrow| B --o|circle| C --x|cross| D`) to PNG
- [ ] Visually verify in each PNG that markers touch the target node border with no gap
- [ ] Visually verify arrow markers have not regressed (tip still touches node)
- [ ] Compare against mmdc reference PNGs if available

## Test Scenarios

### Unit: Per-marker shortening values
- Verify `_marker_shorten(ArrowType.arrow)` returns 8.0
- Verify `_marker_shorten(ArrowType.circle)` returns the correct value for circle markers to touch the node
- Verify `_marker_shorten(ArrowType.cross)` returns the correct value for cross markers to touch the node
- Verify `_marker_shorten(ArrowType.none)` returns 0.0

### Unit: Path shortening applied correctly
- Create a simple vertical edge from (100, 0) to (100, 100)
- Apply `_shorten_end` with circle shortening value; verify the endpoint moves inward by exactly that amount
- Apply `_shorten_end` with cross shortening value; verify the endpoint moves inward by exactly that amount

### Integration: SVG marker attributes
- Render `circle_endpoint.mmd` to SVG; verify the `<marker id="circle-end">` has the correct refX value
- Render `cross_endpoint.mmd` to SVG; verify the `<marker id="cross-end">` has the correct refX value
- Verify the edge path's final point is shortened by the correct per-marker amount (not the generic 8px)

### Integration: Mixed marker types
- Render a flowchart with arrow, circle, cross, and no-marker edges in the same diagram
- Verify each edge type uses its own shortening value
- Verify no markers overlap or leave gaps with their target nodes

### Visual: PNG verification
- Render circle and cross endpoint fixtures to PNG using cairosvg
- Visually confirm circle markers touch the target node border
- Visually confirm cross markers touch the target node border
- Visually confirm arrow markers have not regressed
