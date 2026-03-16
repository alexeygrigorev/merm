# Issue 84: Excessive whitespace below LR pipeline diagrams

## Problem

The `flowchart/etl_simple.mmd` fixture renders with significant empty whitespace below the diagram content. The bottom margin is disproportionately large, roughly doubling the image height.

Reproduction: `tests/fixtures/corpus/flowchart/etl_simple.mmd`

## Acceptance criteria

- The SVG bounding box (viewBox/width/height) must tightly wrap the diagram content with consistent padding on all sides
- Bottom padding must not exceed 2x the standard padding used on other sides
- The fix must apply to all diagram types, not just this specific fixture
- Existing tests must continue to pass
