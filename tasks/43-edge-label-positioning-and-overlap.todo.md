# Task 43: Edge Label Positioning and Overlap

## Problem

Edge labels have two positioning issues:

1. **Labels overlap each other**: When multiple edges converge on the same target node (e.g. B→D and C→D), their labels are placed at the same vertical position and overlap, making them unreadable.

2. **Labels sit directly on top of edge lines**: There is no background behind the label text, so the edge path renders through the text, reducing readability. Mermaid.js renders a white/semi-transparent rectangle behind edge labels.

### PNG Evidence

- `.tmp/edges/labeled_edges.png` — "long label" and "dotted label" overlap each other between B→D and C→D. "thick label" sits on top of the edge line with no background.
- `.tmp/basic/diamond.png` — fan-in edges converging could have similar label overlap issues.

### Root Cause

- Edge labels are positioned at the midpoint of each edge path. When two edges share the same vertical midpoint (parallel edges converging on one node), labels stack on each other.
- No `<rect>` background element is rendered behind edge label `<text>` elements.

## Acceptance Criteria

- [ ] Edge labels do not overlap with other edge labels — when multiple edges share a midpoint region, labels are offset horizontally or vertically to avoid collision
- [ ] Edge labels have a white (or matching background) rectangle behind them so edge lines don't render through the text
- [ ] Label background rect has small padding (2-4px) around the text
- [ ] Labels remain centered on their respective edge path
- [ ] `uv run pytest` passes with no regressions

### Testable / Automatable Checks (pytest)

- [ ] Parse SVG of `corpus/edges/labeled_edges.mmd` — each edge label `<text>` element has a preceding `<rect>` sibling (the background)
- [ ] For converging edges (B→D, C→D), extract label positions and verify their bounding boxes do not overlap (no shared pixel area)
- [ ] Label background `<rect>` width >= text width, height >= text height
- [ ] Label position is within 10% of the edge path midpoint (still roughly centered)

### PNG Verification (mandatory)

- [ ] Render `corpus/edges/labeled_edges.mmd` to PNG — all labels readable, no overlap, backgrounds visible
- [ ] Render `corpus/basic/diamond.mmd` with labels added — fan-in labels don't overlap
- [ ] Render `github/coffee_machine.mmd` to PNG — "Yes"/"No" labels readable on decision branches

## Dependencies

- None (independent of edge endpoint precision task 42)
