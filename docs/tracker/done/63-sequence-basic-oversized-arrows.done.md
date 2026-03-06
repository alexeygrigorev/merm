# Issue 63: Sequence diagram basic.svg has oversized arrows

## Problem

`basic.mmd` renders with arrow markers that are too large relative to the line thickness and overall diagram scale. The arrowheads appear disproportionately large compared to Mermaid's reference output.

## Reproduction

```
tests/fixtures/corpus/sequence/basic.mmd
```

```
sequenceDiagram
    Alice->>Bob: Hello Bob, how are you?
    Bob-->>Alice: I'm good, thanks!
    Alice->>Bob: Great to hear!
```

## Root Cause Analysis

In `src/merm/render/sequence.py`, the marker definitions use fixed pixel sizes:

```python
m.set("markerWidth", "10")
m.set("markerHeight", "7")
```

These markers are rendered at their native pixel size within the SVG coordinate system. The `markerUnits` attribute defaults to `strokeWidth`, which means the marker scales with the stroke width of the line it's attached to. If `edge_stroke_width` in the theme is larger than 1, the markers get scaled up proportionally, making them appear oversized.

The fix should either:
- Set `markerUnits="userSpaceOnUse"` so markers use absolute coordinates regardless of stroke width
- Or adjust marker dimensions to compensate for stroke-width scaling
- Or reduce marker size to be proportional

## Dependencies

- None (can be fixed independently of issue 62, though both touch `render/sequence.py`)

## Acceptance Criteria

- [ ] Arrow markers in `basic.mmd` are proportional to the line thickness -- arrowhead width should be roughly 6-8px in the rendered output
- [ ] Arrow markers should not be significantly larger than the text height
- [ ] Dashed reply arrows (`-->>`) have the same marker size as solid arrows (`->>`)
- [ ] The fix works for all arrow types (solid, dashed, cross, open, async)
- [ ] Existing tests pass (`uv run pytest`)
- [ ] Render `basic.mmd` to PNG with cairosvg and visually verify arrow markers are proportional -- not oversized, not too small, similar in scale to typical Mermaid output

## Test Scenarios

### Unit: Marker dimensions
- Parse the SVG output for `basic.mmd`, extract marker element attributes, verify markerWidth and markerHeight are reasonable (e.g., <= 12px effective size)
- If markerUnits is set, verify it is `userSpaceOnUse`

### Unit: Marker consistency across types
- Render `arrows.mmd` (after issue 62 fix, or a subset), verify all marker types have consistent proportions

### Regression: Other sequence diagrams
- Render flink diagrams, verify arrows are not too small after the size reduction

### Visual: PNG verification
- Render `basic.mmd` to PNG via cairosvg, visually verify arrowheads are proportional and look clean
- Compare arrow size relative to participant box size and text size
