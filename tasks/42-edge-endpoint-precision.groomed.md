# Task 42: Edge Endpoint Precision -- Arrows Must Start/End Exactly at Node Rect

## Problem

Arrow edges don't start and end exactly at node rectangle boundaries. There's a visible gap between where the edge path begins/ends and the node rect edge. This is most visible on diagrams with longer edges (e.g. cross-boundary subgraph edges).

### PNG Evidence

- `docs/gallery/gallery_cross.png` -- arrows from A->D and B->C visibly don't touch the source/target rects
- Visible on most diagrams but especially noticeable on cross-boundary and diagonal edges
- Confirmed by rendering `corpus/edges/arrow.mmd`, `corpus/subgraphs/cross_boundary_edges.mmd`, `corpus/basic/diamond.mmd`, and `corpus/direction/lr.mmd` to PNG -- all show the gap at the source end

### Root Cause (confirmed)

In `src/pymermaid/layout/sugiyama.py`, function `_route_edge_on_boundary()` (line 345), a `gap=3.0` parameter pulls BOTH the source and target endpoints inward along the edge direction (lines 382-383):

```python
src_point = Point(src_point.x + ux * gap, src_point.y + uy * gap)   # line 382
tgt_point = Point(tgt_point.x - ux * gap, tgt_point.y - uy * gap)   # line 383
```

This gap was added in task 37 to prevent arrowhead markers from overlapping nodes, but:
1. The source endpoint (which has no marker) should touch the rect boundary exactly -- it should get zero gap.
2. The target endpoint gap should match the actual marker geometry, not a hardcoded 3px.
3. For open-link edges (`A --- B`), which have no marker on either end, both endpoints should touch their respective node boundaries exactly.

Additionally, the arrow marker in `src/pymermaid/render/edges.py` uses `refX="10"` with `markerWidth="8"` and `markerUnits="userSpaceOnUse"`. Since `refX` is the point on the marker that aligns with the path endpoint, the arrowhead tip is already at the path endpoint and the marker body extends backward. This means the target gap should ideally be zero or near-zero as well, with the marker `refX` doing the visual alignment.

### Implementation Note

The layout function `_route_edges()` currently receives edges as `list[tuple[str, str]]` (source, target) without edge type information. The fix has two viable approaches:
1. **Layout-only fix**: Remove the source gap entirely (set to 0). For the target gap, either remove it too (relying on marker `refX` for visual alignment) or keep a small gap calibrated to the marker size.
2. **Layout + renderer fix**: Pass edge type info into layout so the gap can be conditional (zero for open links, marker-sized for arrow edges). Adjust marker `refX` if needed.

The simpler approach (option 1) is preferred: set source gap to 0, and tune the target gap to work with the current marker `refX` values.

## Acceptance Criteria

- [ ] Edge source endpoint lies exactly on the source node rect boundary (within 0.5px tolerance) for all edge types
- [ ] Edge target endpoint for arrow edges: the arrowhead tip visually touches the target node rect boundary (no visible gap, no penetration)
- [ ] Edge target endpoint for open-link edges (`---`): the path endpoint lies exactly on the target node rect boundary (within 0.5px tolerance, since there is no marker)
- [ ] No visible gap between edge start and source node on any direction (TB, BT, LR, RL)
- [ ] No arrowhead penetrating into target node rect
- [ ] Circle endpoint (`--o`) and cross endpoint (`--x`) markers also visually touch the target rect
- [ ] `uv run pytest` passes with no regressions
- [ ] The `_boundary_point()` function continues to compute mathematically correct ray-rectangle intersections (no precision regressions)

### Testable / Automatable Checks

These should be pytest tests that parse the SVG output:

- [ ] For each edge in a rendered diagram, extract the path `d` attribute, compute the start point (first `M` command), and verify it lies on the source node's rect boundary (within 1px)
- [ ] For arrow edges, extract the end point (last coordinate in path), verify it is within `marker_size + 1px` of the target node's rect boundary
- [ ] For open-link edges, extract the end point and verify it lies on the target node's rect boundary (within 1px)
- [ ] Test with `corpus/subgraphs/cross_boundary_edges.mmd` -- all 4 edges checked
- [ ] Test with `corpus/direction/lr.mmd` and `corpus/direction/rl.mmd` -- horizontal edges checked
- [ ] Test with `corpus/basic/diamond.mmd` -- fan-out/fan-in edges checked
- [ ] Test with `corpus/edges/open_link.mmd` -- open-link edges have zero gap at both ends
- [ ] Unit test `_route_edge_on_boundary()` directly: given known node positions and sizes, verify the returned source point lies on the source rect boundary
- [ ] Unit test `_boundary_point()` directly: vertical, horizontal, and diagonal cases all return points exactly on the rect edge

### PNG Verification (mandatory)

- [ ] Render `cross_boundary_edges` to PNG -- arrows visually touch both source and target rects
- [ ] Render `diamond` to PNG -- fan-out edges start exactly at source rect bottom
- [ ] Render all 4 directions (TB, BT, LR, RL) to PNG -- consistent behavior
- [ ] Render `open_link` to PNG -- line endpoints touch node rects on both ends

## Test Scenarios

### Unit: _boundary_point precision
- Vertical edge (dx=0): returns point at top or bottom center of rect
- Horizontal edge (dy=0): returns point at left or right center of rect
- 45-degree diagonal: returns correct corner-adjacent point
- Near-vertical edge (small dx): returns point on top/bottom edge, not side edge

### Unit: _route_edge_on_boundary gap behavior
- Source point has zero gap (lies on boundary)
- Target point gap matches expected marker offset
- When `gap=0`, both points lie exactly on boundaries
- Same-position nodes (dx=dy=0): returns sensible fallback points
- Very short edges (length < 2*gap): no overshoot or crossing

### Unit: open-link edges
- Open-link edges get zero gap on both source and target
- Path endpoints for `A --- B` both lie on their respective node rects

### Integration: SVG edge endpoint validation
- Parse SVG for `corpus/edges/arrow.mmd`, extract path start points, verify on source rect boundary
- Parse SVG for `corpus/edges/open_link.mmd`, verify both endpoints on rect boundaries
- Parse SVG for `corpus/subgraphs/cross_boundary_edges.mmd`, all 4 edges validated
- Parse SVG for `corpus/basic/diamond.mmd`, fan-out source points validated
- Parse SVG for each direction (TB, BT, LR, RL), direction-appropriate edges validated

### Integration: marker alignment
- For arrow edges, verify the SVG marker `refX` value is consistent with the target gap
- Circle and cross endpoint markers also produce visually correct results

## Dependencies

- Task 37 (arrow-node-gap) -- done, this task refines that fix

## Scope

- Primary change: `_route_edge_on_boundary()` in `src/pymermaid/layout/sugiyama.py` -- remove source gap, tune target gap
- Possibly adjust marker `refX` values in `src/pymermaid/render/edges.py` to coordinate with the new gap
- Does NOT change edge routing (waypoints between source and target)
- Does NOT affect self-loops (separate task 38)
- Does NOT change `_boundary_point()` unless a precision bug is found there
