# Issue 93: Cylinder top ellipse has different color from body

## Problem

The cylinder shape renders with a white/lighter top ellipse while the body has the standard node fill color. This makes the top look like a separate element. The entire cylinder should be one uniform color.

Reproduction: `tests/fixtures/corpus/shapes/cylinder.mmd`

## Acceptance criteria

- The cylinder top ellipse must have the same fill color as the body
- The cylinder should look like a single cohesive shape
- Existing tests must continue to pass
