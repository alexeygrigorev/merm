# Task 23: Fix Disconnected Component Layout -- Vertical Centering

## Status

The core fix (side-by-side placement instead of vertical stacking) was already implemented in commit `5067455`. The `basic/parallel_paths` SSIM improved from 0.44 to 0.74, meeting the original 0.70 target.

**What remains**: components of unequal height are top-aligned instead of vertically centered relative to each other. Mermaid.js vertically centers them, so there is a visual discrepancy when components have significantly different numbers of layers.

## Problem Statement

When disconnected components have different heights (e.g., a 4-layer chain next to a 2-layer chain), all components start at y=0 (top-aligned). Mermaid.js vertically centers shorter components relative to the tallest one, producing a more balanced visual layout.

### Root Cause

In `/home/alexey/git/pymermaid/src/pymermaid/layout/sugiyama.py`, lines 1360-1366, the side-by-side placement loop applies an `x_offset` but keeps the original `y` values unchanged. Since `_assign_coordinates` always starts each component from y=0, all components are top-aligned:

```python
x_offset = 0.0
for i, positions in enumerate(component_positions):
    for n, (x, y) in positions.items():
        all_positions[n] = (x + x_offset, y)     # <-- no y_offset applied
    comp_w, _comp_h = component_sizes[i]
    x_offset += comp_w + config.node_sep
```

## Implementation Plan

### File: `/home/alexey/git/pymermaid/src/pymermaid/layout/sugiyama.py`

**Step 1**: Fix the bounding box computation (lines 1339-1347) to also track the minimum x/y coordinates of each component, so the true width/height is `(max_right - min_left, max_bottom - min_top)`:

```python
min_x = float("inf")
min_y = float("inf")
max_x = float("-inf")
max_y = float("-inf")
for n in positions:
    pos = positions[n]
    size = all_node_sizes.get(n, (40.0, 30.0))
    min_x = min(min_x, pos[0] - size[0] / 2.0)
    min_y = min(min_y, pos[1] - size[1] / 2.0)
    max_x = max(max_x, pos[0] + size[0] / 2.0)
    max_y = max(max_y, pos[1] + size[1] / 2.0)
comp_width = max_x - min_x
comp_height = max_y - min_y
```

**Step 2**: In the side-by-side placement loop (lines 1360-1366), compute `max_height` across all components and vertically center each component:

```python
max_comp_height = max(h for _, h in component_sizes)
x_offset = 0.0
for i, positions in enumerate(component_positions):
    comp_w, comp_h = component_sizes[i]
    y_offset = (max_comp_height - comp_h) / 2.0
    for n, (x, y) in positions.items():
        all_positions[n] = (x + x_offset, y + y_offset)
    x_offset += comp_w + config.node_sep
```

**Step 3**: Make sure the x_offset calculation accounts for the actual component width (not just the max right coordinate), by normalizing each component's positions so the leftmost edge starts at x=0 before applying the offset. This may already be the case due to `_assign_coordinates` behavior, but verify and add normalization if needed.

## Acceptance Criteria

- [ ] Two disconnected components of equal height have the same y-offset for their topmost nodes
- [ ] Two disconnected components of unequal height are vertically centered (shorter component's top y > 0, centered relative to taller component)
- [ ] Three or more disconnected components are all vertically centered relative to the tallest
- [ ] Single-component diagrams are unaffected (no regression)
- [ ] The horizontal gap between components equals `config.node_sep` (currently 30px)
- [ ] `uv run pytest` passes with no regressions
- [ ] The `basic/parallel_paths` fixture (two equal-height components) still renders correctly side-by-side

## Test Scenarios

### Unit: Vertical centering of unequal components

Test in `/home/alexey/git/pymermaid/tests/test_layout.py`.

**test_disconnected_components_vertical_centering**:
- Diagram: `graph TD\n  A-->B\n  B-->C\n  D-->E` (3-layer component + 2-layer component)
- Assert: component {D,E} is vertically centered relative to component {A,B,C}
- Specifically: D's top y should be approximately `(height_of_ABC - height_of_DE) / 2`

**test_disconnected_components_equal_height_same_y**:
- Diagram: `graph TD\n  A-->B\n  C-->D` (two 2-layer components)
- Assert: A.y == C.y and B.y == D.y (same vertical positions)
- Assert: C.x > A.x (side-by-side, C to the right)

**test_disconnected_three_components_centered**:
- Diagram: `graph TD\n  A-->B\n  B-->C\n  D-->E\n  F` (3-layer, 2-layer, 1-layer)
- Assert: all three are side-by-side (increasing x)
- Assert: shorter components are vertically centered relative to tallest

**test_single_component_unaffected**:
- Diagram: `graph TD\n  A-->B\n  B-->C` (single connected component)
- Assert: layout matches previous behavior (no y-offset applied)

### Unit: Component detection (already passing, verify no regression)

**test_find_components_two**:
- `_find_components(["A","B","C","D"], [("A","B",0), ("C","D",1)])` returns 2 groups

**test_find_components_single**:
- `_find_components(["A","B"], [("A","B",0)])` returns 1 group

**test_find_components_three**:
- `_find_components(["A","B","C","D","E"], [("A","B",0), ("C","D",1)])` returns 3 groups (E is isolated)

## Dependencies

- None -- the core side-by-side placement is already implemented. This task only adds vertical centering.
