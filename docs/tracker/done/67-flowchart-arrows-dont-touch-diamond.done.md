# Issue 67: Flowchart arrows don't touch diamond (decision) nodes

## Status: REOPENED — previous fix was insufficient

The layout engine was fixed to compute correct diamond boundary points, but `_MARKER_SHORTEN = 8.0` in the renderer pulls the arrow back 8px from the node, creating a visible gap.

## Problem

Arrows connecting to diamond/rhombus `{Decision}` nodes have a visible gap. The arrowhead tip does not touch the diamond border.

## Root Cause (CONFIRMED by visual inspection)

`_MARKER_SHORTEN = 8.0` in `src/merm/render/edges.py` (line 14) pulls the path endpoint back 8px from the node boundary AFTER the layout engine correctly computes the boundary point. The arrowhead marker has `refX="0"` which places the tip at the shortened endpoint — 8px away from the node.

This affects ALL node shapes, not just diamonds.

## Fix Required

In `src/merm/render/edges.py`:
- Reduce `_MARKER_SHORTEN` to 0 (the filled arrowhead covers the line stroke)
- Or adjust the marker `refX` so the tip extends to the original boundary point

## Acceptance Criteria

- [ ] **MANDATORY PNG CHECK**: Render the diagram below to PNG, read the PNG, and visually confirm arrows touch the diamond with NO visible gap
- [ ] Arrow from "Round" to "Decision" diamond touches the left tip of the diamond
- [ ] Arrows from "Decision" to "Result 1" and "Result 2" start from the diamond edge
- [ ] Arrows between rectangular nodes also touch those nodes (no gaps anywhere)
- [ ] All existing tests pass (`uv run pytest`)

### Test diagram
```
flowchart LR
    A[Hard] -->|Text| B(Round)
    B --> C{Decision}
    C -->|One| D[Result 1]
    C -->|Two| E[Result 2]
```
