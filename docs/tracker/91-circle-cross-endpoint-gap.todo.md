# Issue 91: Circle and cross endpoint markers don't touch target node

## Problem

Edges with circle (`--o`) or cross (`--x`) endpoint markers have a visible gap between the marker and the target node. The path is shortened by `_MARKER_SHORTEN=8` (designed for arrow markers), but circle-end (`refX=5`) and cross-end (`refX=5.5`) markers are smaller and don't extend far enough to reach the node border.

Reproduction: `tests/fixtures/corpus/edges/circle_endpoint.mmd` and `cross_endpoint.mmd`

## Root cause

`_MARKER_SHORTEN` is a single constant (8px) applied to all edge types. Arrow markers extend 8px forward (markerWidth=8, refX=0), so they reach the node. But circle/cross markers only extend ~5px forward, leaving a ~3px gap.

## Acceptance criteria

- Circle endpoint markers must touch the target node border (no visible gap)
- Cross endpoint markers must touch the target node border (no visible gap)
- Arrow markers must continue to work correctly (tip touches node)
- The fix should use per-marker-type shortening rather than a single constant
- Existing tests must continue to pass
