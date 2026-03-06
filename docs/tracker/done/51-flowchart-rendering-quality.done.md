# Task 51: Flowchart Rendering Quality Improvements

## Problem

Visual inspection of complex flowcharts (e.g. registration.mmd) reveals several rendering quality issues that make the output hard to read.

### Issues

1. **Back-edge bundle is indistinguishable** -- When multiple back-edges route along the same side, they stack nearly on top of each other. The 3 return-to-form edges in registration.mmd are barely distinguishable. Need more horizontal separation between parallel back-edge curves.

2. **Back-edge arrows converge to same point** -- All back-edges targeting the same node land at the exact same attachment point, creating an arrowhead blob. They should fan out to different anchor points along the target node's edge.

3. **Node horizontal alignment** -- Nodes that are in a direct parent-child chain (e.g. "Display registration form" -> "User submits form") are not center-aligned. Child nodes shift left/right unnecessarily, making the flow feel unbalanced.

4. **Edge labels overlap crossing edges** -- Edge labels (Yes/No) can sit directly on top of crossing back-edge lines, making them hard to read. Labels should avoid overlapping with any edge path, not just other labels.

5. **No edge crossing gaps** -- When edges cross, they draw straight through each other with no visual indication. Standard flowchart practice is to add a small gap/bridge at crossing points.

6. **Parallelogram width** -- Parallelogram/trapezoid shapes are excessively wide relative to their text content, creating visual imbalance.

7. **Inconsistent vertical spacing** -- Gaps between consecutive nodes vary noticeably even when there are no intervening edges or labels.

## Test Fixture

Primary test: `tests/fixtures/corpus/flowchart/registration.mmd` -- a 12-node flowchart with 3 back-edges (`EmailError->Form`, `ExistsError->Form`, `PasswordError->Form`), diamond decisions, cylinder, parallelogram, and stadium shapes.

## Source Files to Modify

- `/home/alexey/git/pymermaid/src/pymermaid/layout/sugiyama.py` -- Layout engine. Contains `_assign_coordinates()` (issue 3, 7), `_offset_back_edge_dummies()` (issues 1, 2), node sizing for parallelogram/trapezoid (issue 6, lines ~1224-1235), and `_BACK_EDGE_CHANNEL_OFFSET` constant.
- `/home/alexey/git/pymermaid/src/pymermaid/layout/config.py` -- `LayoutConfig` dataclass with `rank_sep` and `node_sep` (issue 7).
- `/home/alexey/git/pymermaid/src/pymermaid/render/edges.py` -- Edge rendering. Contains `render_edge()`, `resolve_label_positions()` (issue 4), `points_to_path_d()` and `_catmull_rom_to_bezier()` (issue 5).
- `/home/alexey/git/pymermaid/src/pymermaid/render/shapes.py` -- `ParallelogramRenderer._SKEW = 0.15` and `TrapezoidRenderer._INSET = 0.15` (issue 6).
- `/home/alexey/git/pymermaid/src/pymermaid/render/svg.py` -- Top-level `render_svg()` function that orchestrates rendering.

## Test File to Create

`/home/alexey/git/pymermaid/tests/test_flowchart_rendering_quality.py`

## Existing Related Tests (Reference for Patterns)

- `/home/alexey/git/pymermaid/tests/test_back_edge_routing.py` -- Has helpers for building test diagrams, extracting edge layouts, and checking back-edge separation. Reuse patterns from this file.
- `/home/alexey/git/pymermaid/tests/test_edge_label_positioning.py` -- Label overlap testing patterns.
- `/home/alexey/git/pymermaid/tests/test_text_overflow_shapes.py` -- Shape sizing assertions.

## Methodology: TDD -- Test First

For EACH issue below, follow this strict sequence:
1. Write a failing test that asserts the correct behavior.
2. Run `uv run pytest tests/test_flowchart_rendering_quality.py -x` and confirm the test FAILS.
3. Fix the production code.
4. Run `uv run pytest tests/test_flowchart_rendering_quality.py -x` and confirm the test PASSES.
5. Run `uv run pytest` (full suite) and confirm no regressions.

## Acceptance Criteria

### Issue 1: Back-edge separation (layout)

- [ ] Render `registration.mmd` with `from pymermaid import render_diagram`. Parse the SVG with `xml.etree.ElementTree`. Extract the three back-edge `<g class="edge">` elements by `data-edge-source`/`data-edge-target` for pairs (`EmailError`, `Form`), (`ExistsError`, `Form`), (`PasswordError`, `Form`).
- [ ] Extract the `d` attribute from each back-edge's `<path>` element. Parse the x-coordinates from the path data.
- [ ] For each pair of back-edges, the maximum x-coordinates in their path waypoints must differ by at least 15px. This means `abs(max_x_edge_A - max_x_edge_B) >= 15.0` for all three pairwise comparisons.
- [ ] Also verify at the layout level: call `layout_diagram()` directly, get `EdgeLayout` objects for the three back-edges, and assert that the average x-coordinate of intermediate points (excluding first and last) differs by >= 20px pairwise (the existing `_BACK_EDGE_CHANNEL_OFFSET` is 30px).

### Issue 2: Back-edge anchor point fan-out (layout)

- [ ] For the three back-edges in `registration.mmd` that all target `Form`, extract the final point (last point in `EdgeLayout.points`) for each back-edge.
- [ ] The y-coordinates of these final points must be identical (they all attach to the same node), but the x-coordinates must differ pairwise by at least 8px. That is: `abs(final_x_edge_A - final_x_edge_B) >= 8.0` for all three pairs.
- [ ] Write a second test with a synthetic diagram (4 back-edges to the same target) and verify the fan-out scales: 4 distinct attachment x-coordinates, minimum 8px apart pairwise.

### Issue 3: Parent-child horizontal alignment (layout)

- [ ] Build a synthetic diagram with a linear chain: `A -> B -> C -> D` (no branching). Call `layout_diagram()`. Assert that all four nodes share the same center-x coordinate: `abs(cx_A - cx_B) < 1.0` for all pairs.
- [ ] Render `registration.mmd`. The `Start -> Form -> Submit` chain should have `Start`, `Form`, and `Submit` within 5px of each other's center-x. Extract center-x from each node's position in the layout result or from SVG node element positions.
- [ ] A diamond pattern (`A -> B`, `A -> C`, `B -> D`, `C -> D`) should NOT force B and D to the same x (they are siblings, not a direct chain), so this test just checks that the layout does not crash and all nodes are present.

### Issue 4: Edge labels avoid crossing back-edge paths (render)

- [ ] Render `registration.mmd`. For each edge label (`No`, `Yes`), compute the label's bounding box from its SVG `<rect>` element (the background rect inside the edge `<g>`).
- [ ] For each back-edge path, compute a simplified bounding box from its path `d` attribute (min/max x and y of all coordinates in the path data).
- [ ] Assert that no label bounding box overlaps with any back-edge path bounding box. Use axis-aligned bounding box (AABB) overlap check: two rectangles overlap if `ax < bx+bw && ax+aw > bx && ay < by+bh && ay+ah > by`.
- [ ] If the current code already passes this test, that is fine -- the test documents the requirement.

### Issue 5: Edge crossing gaps (render)

- [ ] This is a visual polish feature. Build a synthetic diagram that forces a crossing: `A -> C`, `B -> D`, `A -> D`, `B -> C` where A,B are on layer 0 and C,D are on layer 1. Render to SVG.
- [ ] If crossing gaps are implemented: verify that crossing points in the SVG path data contain a gap (a `M` move command near the crossing point, or a separate `<path>` segment). The gap should be 4-8px wide.
- [ ] If crossing gaps are NOT implemented in this task: mark this test as `pytest.mark.skip(reason="crossing gaps deferred")` and add a TODO comment. This issue is the lowest priority and may be deferred.

### Issue 6: Parallelogram/trapezoid width (layout + shapes)

- [ ] Build a synthetic diagram with a parallelogram node containing short text (e.g. "Hi"). Compute the node width from `layout_diagram()`. The width should be no more than 2.5x the text width plus standard padding. Currently the formula is `tw / 0.7 + 32` which makes a node with `tw=20` get `w=60.6`, acceptable. But verify that the `_SKEW` factor in `ParallelogramRenderer` (currently 0.15) and the layout sizing formula are consistent.
- [ ] Render a parallelogram node and measure the ratio of the polygon's bounding box width to the text element's approximate width (character count * 7px). The ratio should be <= 2.0 for text longer than 10 characters.
- [ ] Same test for trapezoid nodes using `TrapezoidRenderer._INSET`.
- [ ] If the current sizing is already reasonable, the tests document the constraint and pass. If the width is excessive, reduce `_SKEW`/`_INSET` from 0.15 to 0.10 and update the layout formula from `tw / 0.7` to `tw / 0.8`.

### Issue 7: Consistent vertical spacing (layout)

- [ ] Build a synthetic diagram with a linear chain of 5 nodes: `A -> B -> C -> D -> E`. Call `layout_diagram()`. Compute the vertical gap between each consecutive pair: `gap_i = cy_{i+1} - cy_i`. All gaps should be equal within 1px tolerance: `abs(gap_i - gap_j) < 1.0` for all pairs.
- [ ] Render `registration.mmd`. For nodes that are on consecutive layers with no branching between them (`Start -> Form -> Submit`), verify that vertical gaps are consistent within 5px tolerance (allowing for different node heights).

## Test Scenarios

### Unit: Back-edge channel separation (Issue 1)
- Synthetic 3-back-edge diagram: intermediate waypoint x-coords differ pairwise by >= 20px
- registration.mmd: SVG path x-coords differ pairwise by >= 15px

### Unit: Back-edge anchor fan-out (Issue 2)
- registration.mmd: 3 back-edges to Form have final-point x-coords >= 8px apart pairwise
- Synthetic 4-back-edge diagram: 4 distinct attachment points >= 8px apart

### Unit: Parent-child alignment (Issue 3)
- Linear chain A->B->C->D: all nodes share center-x within 1px
- registration.mmd: Start/Form/Submit share center-x within 5px

### Unit: Label-path overlap avoidance (Issue 4)
- registration.mmd: no label bbox overlaps any back-edge path bbox

### Unit: Edge crossing gaps (Issue 5)
- Forced-crossing diagram: gap in path at crossing (or skip if deferred)

### Unit: Parallelogram/trapezoid sizing (Issue 6)
- Short-text parallelogram: width <= 2.5x text width + padding
- Long-text parallelogram: bbox-to-text ratio <= 2.0
- Same for trapezoid

### Unit: Vertical spacing consistency (Issue 7)
- Linear 5-node chain: all vertical gaps equal within 1px
- registration.mmd: consecutive-layer gaps consistent within 5px

### Integration: Full regression
- `uv run pytest` full suite passes with no regressions
- `render_diagram(open("tests/fixtures/corpus/flowchart/registration.mmd").read())` produces valid SVG with `<svg` and `</svg>` tags

## Dependencies

None -- these are improvements to existing layout and rendering code.

## Estimated Complexity

Medium-High -- touches layout (`sugiyama.py`), edge rendering (`edges.py`), and node shape renderers (`shapes.py`). The issues are independent of each other and can be tackled in order (1 through 7), with issue 5 (crossing gaps) being deferrable.

## Implementation Notes

- Use `from pymermaid import render_diagram` for end-to-end rendering.
- Use `from pymermaid.layout import layout_diagram` for layout-level assertions.
- Use `from pymermaid.ir import Diagram, DiagramType, Direction, Edge, Node` to build synthetic test diagrams.
- Parse SVG with `xml.etree.ElementTree.fromstring(svg_string)`.
- SVG elements: nodes have `class="node"` and `data-node-id="X"`, edges have `class="edge"` with `data-edge-source` and `data-edge-target`.
- See `/home/alexey/git/pymermaid/tests/test_back_edge_routing.py` for reusable helpers (`_measure`, `_make_diagram`, `_get_edge_layout`, `_intermediate_points`).
- The parallelogram skew is controlled by `ParallelogramRenderer._SKEW` (0.15) in `shapes.py` and the corresponding layout formula `tw / 0.7` in `sugiyama.py` line ~1227. If reducing skew, both must be updated in lockstep.
- Back-edge anchor fan-out requires changes to the edge routing logic in `sugiyama.py` where back-edge endpoints are computed. Currently all back-edges to the same target share the target node's center-x as their final point.
