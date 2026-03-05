# Task 42: Edge Endpoint Precision — Arrows Must Start/End Exactly at Node Rect

## Problem

Arrow edges don't start and end exactly at node rectangle boundaries. There's a visible gap between where the edge path begins/ends and the node rect edge. This is most visible on diagrams with longer edges (e.g. cross-boundary subgraph edges).

### PNG Evidence

- `docs/gallery/gallery_cross.png` — arrows from A→D and B→C visibly don't touch the source/target rects
- Visible on most diagrams but especially noticeable on cross-boundary and diagonal edges

### Root Cause (likely)

The 3px gap added in task 37 (arrow-node-gap fix) pulls edge endpoints inward via `_route_edge_on_boundary()` in `sugiyama.py`. This gap was meant to prevent arrowhead markers from overlapping nodes, but it affects BOTH the source endpoint (which has no marker) and the target endpoint (which has the arrowhead). The source end should touch the rect exactly; only the target end needs the marker offset.

Additionally, the boundary intersection calculation itself may have precision issues — the intersection point may not land exactly on the rect edge.

## Acceptance Criteria

- [ ] Edge source endpoint touches the source node rect boundary exactly (within 1px tolerance)
- [ ] Edge target endpoint: the arrowhead tip visually touches the target node rect (marker offset compensates for marker size)
- [ ] No visible gap between edge start and source node on any direction (TB, BT, LR, RL)
- [ ] No arrowhead penetrating into target node rect
- [ ] `uv run pytest` passes with no regressions

### Testable / Automatable Checks

These should be pytest tests that parse the SVG output:

- [ ] For each edge in a rendered diagram, extract the path `d` attribute, compute the start point (first M command), and verify it lies on the source node's rect boundary (within 1px)
- [ ] For each edge, extract the end point (last coordinate in path), verify it is within `marker_size + 2px` of the target node's rect boundary (accounts for marker offset)
- [ ] Test with `corpus/subgraphs/cross_boundary_edges.mmd` — all 4 edges checked
- [ ] Test with `corpus/direction/lr.mmd` and `corpus/direction/rl.mmd` — horizontal edges checked
- [ ] Test with `corpus/basic/diamond.mmd` — fan-out/fan-in edges checked

### PNG Verification (mandatory)

- [ ] Render `cross_boundary_edges` to PNG — arrows visually touch both source and target rects
- [ ] Render `diamond` to PNG — fan-out edges start exactly at source rect bottom
- [ ] Render all 4 directions (TB, BT, LR, RL) to PNG — consistent behavior

## Dependencies

- Task 37 (arrow-node-gap) — done, this task refines that fix

## Scope

- Only affects edge endpoint calculation in layout (`sugiyama.py`) and possibly marker `refX` in `edges.py`
- Does NOT change edge routing (waypoints between source and target)
- Does NOT affect self-loops (separate task 38)
