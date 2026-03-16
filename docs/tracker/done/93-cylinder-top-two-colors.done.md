# Issue 93: Cylinder top ellipse has different color from body

## Problem

The cylinder shape renders with a visible color difference between the top ellipse and the body. The `CylinderRenderer` in `src/merm/render/shapes.py` produces a single `<path>` element that draws the cylinder outline (body sides, bottom arc, top arc). However, the top ellipse arc is drawn as a separate `M`-move followed by an arc with sweep-flag 0 (drawing the "back" of the ellipse). This creates a visual artifact where the top portion appears lighter/white because the path's fill region does not correctly cover the top ellipse area -- the fill only covers the closed body region, while the top ellipse arc is an open sub-path that does not enclose a filled area.

Reproduction: `tests/fixtures/corpus/shapes/cylinder.mmd`

## Root Cause

In `CylinderRenderer.render()`, the path is constructed as:
```
M tx,ty  A ... (top arc, sweep=1)  L (right side down)  A ... (bottom arc, sweep=1)  L (left side up)
M tx,ty  A ... (top arc, sweep=0, the visible front ellipse)
```

The second `M` starts a new sub-path for the visible top ellipse. Because this sub-path is not closed and only draws an arc, SVG fill rules leave it unfilled or fill it differently from the body. The fix is to either:
1. Draw the body and top ellipse as separate elements where the top ellipse explicitly has the same fill, or
2. Restructure the path so the top ellipse is part of a closed, filled region

## Scope

- Fix `CylinderRenderer.render()` in `src/merm/render/shapes.py` so the entire cylinder has uniform fill color
- The top ellipse must have the same fill as the body
- Must not break existing cylinder tests or any other shape rendering

## Dependencies

- None

## Acceptance Criteria

- [ ] `CylinderRenderer.render()` produces SVG where the top ellipse has the same fill color as the body
- [ ] The cylinder visually appears as a single cohesive shape with uniform color
- [ ] All existing tests pass: `uv run pytest tests/test_shapes.py tests/test_styling.py`
- [ ] Rendering `tests/fixtures/corpus/shapes/cylinder.mmd` produces a correct cylinder with uniform fill
- [ ] Render to PNG with cairosvg and visually verify: (a) the top ellipse and body are the same color, (b) the cylinder looks like a single shape, not two separate elements, (c) the outline/stroke is clean around the entire shape including the top ellipse

## Test Scenarios

### Unit: CylinderRenderer fill uniformity
- Render a cylinder with an explicit fill style (e.g., `{"fill": "#ECECFF"}`) and verify that all SVG sub-elements (path or separate elements) carry the same fill
- If the renderer produces multiple elements, verify each element has the fill attribute set
- Parse the rendered SVG path and verify the top ellipse region is part of a closed, filled area (or is a separate element with explicit fill)

### Unit: CylinderRenderer path structure
- Verify the path `d` attribute produces a valid cylinder shape (has arc commands, correct dimensions)
- Verify the rendered elements produce correct visual output (no open sub-paths that would cause fill artifacts)

### Integration: Full diagram rendering
- Render `cylinder.mmd` fixture through the full pipeline (`render_diagram`)
- Verify the SVG contains the cylinder shape with uniform fill
- Verify no regression in other shapes by running the full shape test suite

### Visual: PNG verification
- Render `cylinder.mmd` to PNG via cairosvg, save to `.tmp/`, visually confirm the top ellipse matches the body color
- Compare with mmdc reference PNG if available
