# Task 43: Edge Label Positioning and Overlap

## Related Tasks

- Task 28 (`tasks/28-edge-label-overlap-and-positioning.todo.md`) covers the same issue. This task supersedes it with a more specific implementation plan.

## Problem

When multiple labeled edges converge on the same target node (e.g., `B-->|"long label"|D` and `C-.->|"dotted label"|D`), their labels are placed at nearly the same (x, y) position by `_edge_midpoint()`, causing them to overlap and become unreadable.

### What Already Works

The background rectangle behind edge labels is **already implemented** in `_render_edge_label()` (lines 301-349 of `src/pymermaid/render/edges.py`). Each label gets a `<rect>` with `fill="rgba(232,232,232,0.8)"` rendered before the `<text>` element. This part does NOT need changes.

### Root Cause

`_edge_midpoint()` (lines 222-231 of `src/pymermaid/render/edges.py`) computes the geometric midpoint of each edge's polyline independently. It has no awareness of other labels. When two edges share a similar vertical span (same source/target layer region), their midpoints land at nearly the same coordinates.

The rendering loop in `src/pymermaid/render/svg.py` (lines 470-473) calls `_render_edge_delegate` for each edge independently, with no cross-edge label coordination.

### Reproduction

Render `tests/fixtures/corpus/edges/labeled_edges.mmd`:
```
graph TD
    A -->|yes| B
    A -->|no| C
    B -- long label text --> D
    C -. dotted label .-> D
    D == thick label ==> E
```

Labels "long label text" and "dotted label" overlap between nodes B/C and D.

## Implementation Plan

### Step 1: Add label collision detection and nudging to `render_edge` flow

**File:** `src/pymermaid/render/edges.py`

Add a new function `resolve_label_positions()` that:
1. Takes a list of `(edge_layout, ir_edge)` pairs (all edges that have labels).
2. Computes initial label positions using `_edge_midpoint()`.
3. Computes approximate bounding boxes for each label (using the same `char_w=7.0`, `line_h=16.0`, `padding=4.0` constants already in `_render_edge_label`).
4. Detects overlapping bounding box pairs (axis-aligned rectangle intersection test).
5. Nudges overlapping labels apart along the y-axis (preferred) or x-axis until no bounding boxes overlap. A simple iterative approach: sort labels by y then x, and shift any colliding label downward/sideways by the overlap amount plus a small gap (e.g., 6px).
6. Returns a dict mapping `(source, target)` to the adjusted `(cx, cy)` position.

### Step 2: Pass resolved positions into edge rendering

**File:** `src/pymermaid/render/svg.py` (lines 470-473)

Change the edge rendering loop to:
1. Before the loop, collect all labeled edges and call `resolve_label_positions()`.
2. Pass the resolved `(cx, cy)` for each edge into `render_edge()` (or `_render_edge_delegate()`).

**File:** `src/pymermaid/render/edges.py` -- `render_edge()` signature

Add an optional `label_pos: tuple[float, float] | None = None` parameter. When provided, use it instead of calling `_edge_midpoint()`.

### Step 3: Apply to state diagram renderer too

**File:** `src/pymermaid/render/statediag.py` (line 351)

Apply the same pattern if state diagrams have labeled edges. At minimum, pass through the same `label_pos` parameter.

## Acceptance Criteria

- [ ] `from pymermaid.render.edges import resolve_label_positions` imports successfully
- [ ] `resolve_label_positions` returns adjusted positions such that no two label bounding boxes overlap (rect intersection test)
- [ ] Rendering `tests/fixtures/corpus/edges/labeled_edges.mmd` to SVG produces label `<text>` elements whose bounding boxes (computed from x, y, rect width, rect height) do not overlap
- [ ] Each label position remains within 40px of its edge's geometric midpoint (labels stay close to their edge)
- [ ] Labels still have background `<rect>` elements rendered before the `<text>` (no regression)
- [ ] Single-label edges (no collision) are unaffected -- label stays at exact midpoint
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: resolve_label_positions with no overlaps
- Two labels at well-separated positions are returned unchanged
- A single label is returned at its exact midpoint

### Unit: resolve_label_positions with overlapping labels
- Two labels at the same (x, y) are nudged apart so their bounding boxes do not intersect
- Three labels in a vertical stack are all separated with no pairwise overlap
- Labels with different text lengths (different bbox widths) are correctly separated

### Unit: render_edge with explicit label_pos
- When `label_pos=(100, 200)` is passed, the `<text>` element's x/y attributes are 100 and 200 (not the midpoint)
- When `label_pos=None`, behavior is unchanged (midpoint is used)

### Integration: labeled_edges.mmd SVG output
- Parse the SVG output of `labeled_edges.mmd`
- Extract all edge label `<text>` elements and their preceding `<rect>` siblings
- Compute bounding boxes from rect x, y, width, height attributes
- Assert no two bounding boxes overlap (axis-aligned intersection test)
- Assert each label text content matches expected labels ("yes", "no", "long label text", "dotted label", "thick label")

### Integration: single-edge diagram unchanged
- A diagram with one labeled edge produces label at exact midpoint (no nudging applied)

## Dependencies

- None. This task is independent of other open tasks.
