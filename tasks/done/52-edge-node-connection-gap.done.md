# Task 52: Fix Edge-to-Node Connection Gap

## Problem

Edges don't connect to node boundaries. There's a visible gap between arrowheads and node borders -- arrows float in empty space instead of touching the node.

In `basic/diamond.mmd`: node A's bottom edge is at y=54, but the A->B edge starts at y=56.6 (2.6px below). Node B's top edge is at y=104, but the edge ends at y=101.4 (2.6px above). This creates ~5px total gap per edge.

## Root Cause

The layout engine or edge renderer is applying incorrect padding/offset when computing edge start and end points. The edge endpoints need to land exactly on the node boundary (accounting for marker/arrowhead size on the target end only).

## Scope

Fix the edge endpoint calculation so that:
1. The edge path starts exactly on the source node boundary (no gap).
2. The arrowhead tip touches the target node boundary (no gap).
3. The arrowhead triangle is cleanly pointy -- no line stub visible behind/through the arrowhead base.

This task does NOT require changing node shapes or layout positions -- only the edge endpoint computation and marker alignment.

## Files to Modify

- `/home/alexey/git/pymermaid/src/pymermaid/layout/sugiyama.py` -- `_route_edge_on_boundary()`, `_boundary_point()`, and `_route_edges()` compute edge start/end coordinates
- `/home/alexey/git/pymermaid/src/pymermaid/render/edges.py` -- `_marker_arrow()` defines the arrowhead marker (refX, viewBox, path); `points_to_path_d()` generates the SVG path d-string

## Files to Read for Context

- `/home/alexey/git/pymermaid/src/pymermaid/layout/types.py` -- `Point`, `EdgeLayout`, `NodeLayout` dataclasses
- `/home/alexey/git/pymermaid/src/pymermaid/render/svg.py` -- `render_svg()` orchestrates the full render pipeline
- `/home/alexey/git/pymermaid/tests/test_arrow_node_gap.py` -- existing tests for edge gap (Task 37)
- `/home/alexey/git/pymermaid/tests/test_edge_endpoint_precision.py` -- existing tests for endpoint precision (Task 42)
- `/home/alexey/git/pymermaid/src/pymermaid/__init__.py` -- `render_diagram()` public API

## Test Fixtures

- `/home/alexey/git/pymermaid/tests/fixtures/corpus/basic/diamond.mmd` -- 4 diagonal edges (fan-out + fan-in)
- `/home/alexey/git/pymermaid/tests/fixtures/corpus/basic/linear_chain.mmd` -- straight vertical chain
- `/home/alexey/git/pymermaid/tests/fixtures/corpus/basic/two_nodes.mmd` -- simplest case, 1 edge
- `/home/alexey/git/pymermaid/tests/fixtures/corpus/direction/lr.mmd` -- horizontal layout
- `/home/alexey/git/pymermaid/tests/fixtures/corpus/direction/rl.mmd` -- reverse horizontal
- `/home/alexey/git/pymermaid/tests/fixtures/corpus/direction/bt.mmd` -- bottom-to-top
- `/home/alexey/git/pymermaid/tests/fixtures/corpus/flowchart/registration.mmd` -- has back-edges (curves)

## Acceptance Criteria

- [ ] For every edge in `basic/two_nodes.mmd` (TD): the path start point (M coordinate) is within 1px of the source node's bounding rect boundary
- [ ] For every edge in `basic/two_nodes.mmd` (TD): the path end point (last coordinate) is within 1px of the target node's bounding rect boundary
- [ ] For every edge in `basic/diamond.mmd` (TD, diagonal edges): path start within 1px of source boundary AND path end within 1px of target boundary
- [ ] For every edge in `basic/linear_chain.mmd` (TD, straight vertical): path start within 1px of source boundary AND path end within 1px of target boundary
- [ ] For every edge in `direction/lr.mmd` (LR): path start within 1px of source boundary AND path end within 1px of target boundary
- [ ] For every edge in `direction/bt.mmd` (BT): path start within 1px of source boundary AND path end within 1px of target boundary
- [ ] No edge path endpoint is inside the node interior (overshoot check): for TD, source endpoint y >= source node bottom edge; target endpoint y <= target node top edge
- [ ] The arrowhead is cleanly pointy: the SVG line path ends at the arrowhead base, not the tip. Either (a) `refX` in the arrow marker equals the base position (e.g., `refX="0"` with the triangle path `M 0 0 L 10 5 L 0 10 z`) so the line terminates at the triangle base, or (b) the path endpoint is shortened by the marker length so the line does not extend through the arrowhead triangle. The result: no visible line stub behind the arrowhead.
- [ ] `uv run pytest tests/test_edge_connection_gap.py -v` passes with all tests green
- [ ] Existing tests still pass: `uv run pytest tests/test_arrow_node_gap.py tests/test_edge_endpoint_precision.py -v`

## Test Scenarios

Create test file: `/home/alexey/git/pymermaid/tests/test_edge_connection_gap.py`

### Helpers needed

Write these SVG parsing helpers (or reuse from `test_edge_endpoint_precision.py`):
- `_parse_node_bboxes(svg_str) -> dict[str, dict]` -- parse all `g.node[data-node-id]` elements, extract the child rect/polygon/circle bounding box as `{"x": float, "y": float, "w": float, "h": float}`
- `_parse_edge_endpoints(svg_str) -> list[dict]` -- parse all `g.edge` elements, extract `data-edge-source`, `data-edge-target`, path d-string start (M x,y) and end (last coordinate pair)
- `_point_on_rect_boundary(px, py, rx, ry, rw, rh, tolerance=1.0) -> bool` -- True if point (px,py) is within `tolerance` pixels of the rect boundary

Use SVG namespace `{http://www.w3.org/2000/svg}` for all element lookups. Use `data-node-id` (not `data-id`) for node identification.

### Unit: _route_edge_on_boundary produces boundary-touching points

```
from pymermaid.layout.sugiyama import _route_edge_on_boundary
```

- TD layout (src above tgt): source endpoint y == src_center_y + src_h/2 (within 0.5px), target endpoint y == tgt_center_y - tgt_h/2 (within 0.5px)
- LR layout (src left of tgt): source endpoint x == src_center_x + src_w/2 (within 0.5px), target endpoint x == tgt_center_x - tgt_w/2 (within 0.5px)
- Diagonal (src at (50,50), tgt at (200,200), both 80x54): both endpoints on respective rect boundaries (within 0.5px)

### Integration: two_nodes.mmd gap check

- Render `basic/two_nodes.mmd` with `render_diagram()`
- Parse SVG, extract node bboxes and edge endpoints
- Assert source path start within 1px of source node boundary
- Assert target path end within 1px of target node boundary

### Integration: diamond.mmd diagonal edges

- Render `basic/diamond.mmd`
- For each of the 4 edges: assert source start within 1px of source boundary, target end within 1px of target boundary

### Integration: linear_chain.mmd straight edges

- Render `basic/linear_chain.mmd`
- For each edge: assert both endpoints within 1px of their respective node boundaries

### Integration: LR direction

- Render `direction/lr.mmd`
- For each edge: assert both endpoints within 1px of boundaries

### Integration: BT direction

- Render `direction/bt.mmd`
- For each edge: assert both endpoints within 1px of boundaries

### Integration: no overshoot into node interior

- Render `basic/two_nodes.mmd` (TD)
- For the edge: source start y >= source node bottom - 1px (not above the node bottom); target end y <= target node top + 1px (not below the node top)

### Unit: arrowhead marker alignment

- Parse the arrow marker from `make_edge_defs()` output
- Verify that either: refX is set to 0 (line ends at triangle base), OR the path endpoint is shortened by marker size
- Render `basic/two_nodes.mmd`, visually verify (via coordinate math) that the line path does not extend past the arrowhead base

### Integration: back-edge (curve) connection

- Render `flowchart/registration.mmd`
- For each edge (including any back-edges): source start within 2px of source boundary, target end within 2px of target boundary (relaxed tolerance for curves)

## Methodology

**TDD -- write failing tests FIRST, then fix code.**

1. Create `/home/alexey/git/pymermaid/tests/test_edge_connection_gap.py` with all test scenarios above
2. Run `uv run pytest tests/test_edge_connection_gap.py -v` and confirm tests FAIL (because the gap bug exists)
3. Fix the code in `sugiyama.py` and/or `edges.py`
4. Run `uv run pytest tests/test_edge_connection_gap.py -v` and confirm all tests PASS
5. Run `uv run pytest tests/test_arrow_node_gap.py tests/test_edge_endpoint_precision.py -v` and confirm no regressions

## Dependencies

None -- all prerequisite tasks (layout engine, edge rendering, SVG renderer) are already implemented.

## Estimated Complexity

Medium -- likely a fix in edge endpoint calculation in `_route_edge_on_boundary` or `_route_edges` in `sugiyama.py`, plus possible marker `refX` adjustment in `edges.py`.
