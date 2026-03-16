# Issue 86: Mindmap layout produces excessive whitespace

## Problem

The `mindmap/deep_tree.mmd` fixture renders with large empty areas in the upper-right and lower-left quadrants. The bounding box is significantly larger than necessary for the content. The radial layout spreads nodes too far apart.

Reproduction: `tests/fixtures/corpus/mindmap/deep_tree.mmd`

## Acceptance criteria

- The mindmap bounding box must tightly wrap the rendered nodes with consistent padding
- Empty quadrants should be minimized — the layout should distribute nodes to fill available space
- The whitespace ratio (empty area / total area) should be under 60% for a typical mindmap
- Existing tests must continue to pass
