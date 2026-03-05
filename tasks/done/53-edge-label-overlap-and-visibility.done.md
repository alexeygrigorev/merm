# Task 53: Edge Label Overlap and Edge Style Visibility

## Problem

### Label overlap
In `edges/labeled_edges.mmd`, the "long label text" and "dotted label" background rects overlap each other (x=8.5,w=113 and x=79,w=92 -- they share the 79-121.5 range). The labels collide visually and you can't tell which belongs to which edge. The existing `resolve_label_positions()` nudges on y-axis only -- it doesn't handle x-axis overlap when labels are on diagonal edges side by side.

### Edge style visibility
- **Dotted edge**: `stroke-dasharray="3"` is too subtle -- dashes are too small to distinguish from solid at normal viewing size. Should use `stroke-dasharray="5,5"` or similar for visible dots/dashes.
- **Thick edge**: `stroke-width="3.5"` while normal is `2` -- the difference exists but is underwhelming. Consider increasing to match mermaid.js visual weight.
- **Dotted dash pattern**: `stroke-dasharray="3"` produces equal 3px dash/3px gap. Mermaid.js uses different patterns for dotted vs dashed.

## Scope

This task has two independent sub-problems:

1. **Fix label overlap resolution** in `resolve_label_positions()` so that it correctly handles x-axis overlap (not just y-axis). The current code has a logic bug: the y_overlap calculation always yields a positive value when rects overlap, so the `else` branch (x-axis nudge) is never reached.
2. **Improve edge style constants** in `_STYLE_MAP` so dotted and thick edges are visually distinct from normal edges.

Out of scope: changing layout algorithms, changing label font size, changing label background color.

## Key Files

- **Source to modify**: `/home/alexey/git/pymermaid/src/pymermaid/render/edges.py`
  - `_STYLE_MAP` dict (line ~180) -- change dash patterns and stroke widths
  - `resolve_label_positions()` function (line ~266) -- fix overlap resolution logic
- **Test fixture**: `/home/alexey/git/pymermaid/tests/fixtures/corpus/edges/labeled_edges.mmd`
- **Existing tests**: `/home/alexey/git/pymermaid/tests/test_edge_label_positioning.py`
- **New test file to create**: `/home/alexey/git/pymermaid/tests/test_task53_edge_label_overlap_and_visibility.py`
- **Public API**: `from pymermaid import render_diagram`

## Acceptance Criteria

- [ ] Rendering `labeled_edges.mmd` produces zero overlapping label background rects. Specifically: for every pair of `<rect>` elements inside `<g class="edge">` groups, the axis-aligned bounding boxes `(x, y, w, h)` must not intersect (i.e., `_rects_overlap()` returns `False`).
- [ ] The "long label text" rect and the "dotted label" rect no longer share any x-range. Currently they overlap in the x-range [79, 121.5]. After the fix, the right edge of one must be less than or equal to the left edge of the other (or they must be vertically separated enough that the rects do not intersect).
- [ ] Dotted edges (`EdgeType.dotted` and `EdgeType.dotted_arrow`) use `stroke-dasharray` with individual dash and gap values each >= 5 (e.g., `"5,5"` or `"6,4"`). The value must NOT be the single-number `"3"`.
- [ ] Thick edges (`EdgeType.thick` and `EdgeType.thick_arrow`) use `stroke-width` with a numeric value >= 3.5 (the current value is acceptable, but verify it is clearly thicker than the normal edge `stroke-width` of `"2"`).
- [ ] All 5 expected labels (`"yes"`, `"no"`, `"long label text"`, `"dotted label"`, `"thick label"`) are still present in the rendered SVG after the fix.
- [ ] Existing tests in `tests/test_edge_label_positioning.py` continue to pass.
- [ ] `uv run pytest tests/test_task53_edge_label_overlap_and_visibility.py` passes with all new tests green.

## Test Scenarios

Write all tests in `/home/alexey/git/pymermaid/tests/test_task53_edge_label_overlap_and_visibility.py`.

Use `xml.etree.ElementTree` to parse SVG output. Use `from pymermaid import render_diagram` to render. Reuse the SVG namespace helper pattern from the existing test file (see `_iter_edge_groups`, `_find_child` in `tests/test_edge_label_positioning.py`).

### Unit: resolve_label_positions x-axis overlap fix
- Two edges with overlapping x-ranges but same y midpoint: after `resolve_label_positions()`, their label bounding boxes (via `_label_bbox()`) must not overlap. Use `_rects_overlap()` to assert.
- Two edges with labels "long label text" and "dotted label" placed at positions that reproduce the bug (cx close together, cy close together): verify bounding boxes do not overlap after resolution.

### Unit: _STYLE_MAP dash pattern values
- Assert `_STYLE_MAP[EdgeType.dotted]["stroke-dasharray"]` contains comma-separated values (not a single number `"3"`).
- Assert each numeric component of the dash array is >= 5.
- Assert `_STYLE_MAP[EdgeType.dotted_arrow]["stroke-dasharray"]` has the same pattern.
- Assert `_STYLE_MAP[EdgeType.thick]["stroke-width"]` is a string whose float value >= 3.5.
- Assert `_STYLE_MAP[EdgeType.thick_arrow]["stroke-width"]` is a string whose float value >= 3.5.

### Integration: labeled_edges.mmd full render -- no label overlap
- Render the fixture content (inline string matching `labeled_edges.mmd`).
- Parse SVG, find all `<g class="edge">` groups containing both `<rect>` and `<text>`.
- Extract `(x, y, width, height)` from each rect.
- Assert all 5 labels are present.
- Assert no pairwise rect overlap.

### Integration: labeled_edges.mmd -- dotted edge has visible dash pattern
- Render `labeled_edges.mmd`.
- Find the `<path>` inside the edge group with `data-edge-source="C"` and `data-edge-target="D"` (the dotted edge).
- Assert the path has a `stroke-dasharray` attribute.
- Parse the dash array value and assert each component >= 5.

### Integration: labeled_edges.mmd -- thick edge has visible stroke
- Render `labeled_edges.mmd`.
- Find the `<path>` inside the edge group with `data-edge-source="D"` and `data-edge-target="E"` (the thick edge).
- Assert `float(path.get("stroke-width")) >= 3.5`.

## Methodology

**TDD -- write failing tests FIRST, then fix code.**

1. Create `/home/alexey/git/pymermaid/tests/test_task53_edge_label_overlap_and_visibility.py` with all test scenarios above.
2. Run `uv run pytest tests/test_task53_edge_label_overlap_and_visibility.py -v` and confirm the overlap and dash-pattern tests FAIL.
3. Fix `_STYLE_MAP` in `edges.py` -- update `stroke-dasharray` for dotted types from `"3"` to `"5,5"` (or similar with components >= 5).
4. Fix `resolve_label_positions()` in `edges.py` -- the overlap resolution must handle x-axis nudging when labels overlap horizontally. The current bug: `y_overlap = iy_bottom - jy_top + gap` is always positive when rects overlap (because `iy_bottom > jy_top` is guaranteed by the overlap condition), so the `else` branch for x-axis nudging is dead code. Fix the logic so that when labels overlap primarily on the x-axis, they are nudged horizontally.
5. Run `uv run pytest tests/test_task53_edge_label_overlap_and_visibility.py -v` and confirm all tests PASS.
6. Run `uv run pytest tests/test_edge_label_positioning.py -v` and confirm no regressions.
7. Run `uv run pytest` (full suite) and confirm no regressions.

## Dependencies

None.

## Estimated Complexity

Low-Medium -- dash pattern constants are a one-line change each; the overlap resolution fix requires understanding and correcting the nudge logic in `resolve_label_positions()`.
