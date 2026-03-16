# Issue 92: ER diagram "all cardinalities" has overlapping text

## Problem

In the ER `all_cardinalities.mmd` fixture, relationship labels and cardinality markers overlap each other, making text unreadable. The cardinality SVG markers (defined via `<marker>` elements with `refX`/`refY` offsets) visually collide with the relationship label text and its background rectangle, especially on edges where both source and target cardinalities are complex (e.g., crow's foot + circle markers).

Reproduction: `tests/fixtures/corpus/er/all_cardinalities.mmd`

## Root Cause Analysis

The issue likely involves one or more of:
1. Edge endpoints land too close to the label midpoint, causing markers to overlap the label background rect
2. The label is placed at the geometric midpoint of the edge, which may coincide with where markers are drawn
3. Marker `refX` values don't account for the label background rect width
4. When edges are short (entities close together), there is insufficient space between the cardinality markers at each end and the centered label

## Scope

- Fix label and marker positioning so they do not visually overlap in ER diagrams
- May involve adjusting label offset from the midpoint, increasing minimum edge length, or adding clearance between markers and labels
- Must not break existing ER diagram tests (`tests/test_erdiag.py`, `tests/test_issue_92_er_label_overlap.py`)

## Dependencies

- None (existing ER rendering infrastructure is complete through issue 85)

## Acceptance Criteria

- [ ] Render `tests/fixtures/corpus/er/all_cardinalities.mmd` to SVG -- all 5 relationship labels are fully readable
- [ ] No label background rect overlaps with any other label background rect (already tested in `test_issue_92_er_label_overlap.py`)
- [ ] No cardinality marker visually overlaps a label background rect -- markers must end before the label region begins
- [ ] All cardinality markers (exactly-one bar, zero-or-one circle+bar, one-or-more crow's-foot+bar, zero-or-more crow's-foot+circle) are visible and distinguishable
- [ ] Render `tests/fixtures/corpus/er/basic.mmd` and `er/complex.mmd` -- no regressions in label readability
- [ ] `uv run pytest tests/test_erdiag.py tests/test_issue_92_er_label_overlap.py` passes
- [ ] Render to PNG with cairosvg and visually verify: (a) all 5 labels are readable without zooming, (b) cardinality markers do not overlap label backgrounds, (c) markers at entity boundaries are visible and correctly oriented

## Test Scenarios

### Unit: Label-to-marker clearance
- For each relationship in `all_cardinalities.mmd`, compute the distance from the label background rect edges to the nearest marker endpoint; assert distance > 0
- For edges with large markers (crow's foot variants), verify the label is offset away from the marker zone

### Unit: Label background rects do not overlap (existing)
- Existing tests in `test_issue_92_er_label_overlap.py` already cover label-vs-label overlap -- these must continue to pass

### Unit: All labels within viewBox (existing)
- Existing `test_labels_within_viewbox` must continue to pass

### Integration: Multi-entity ER diagrams
- Render `basic.mmd` (3 entities) and `complex.mmd` -- verify no overlapping text elements
- Render `all_cardinalities.mmd` -- verify all 5 labels and all 10 cardinality markers are present and non-overlapping

### Visual: PNG verification
- Render `all_cardinalities.mmd` to PNG via cairosvg, save to `.tmp/`, visually confirm labels and markers are clearly separated
- Compare with mmdc reference PNG if available
