# Issue 60: LR flowchart nodes touching/overlapping

## Problem

In left-to-right flowcharts, nodes are placed too close together -- they touch or nearly overlap, making arrows between them barely visible or completely hidden.

Measured gaps in `rag_pipeline.mmd`:
- Gap C->D: 3.73px (barely visible arrow)
- Gap D->E: -11.47px (nodes actually overlap!)
- Gap E->F: 23.34px (very tight)

## Reproduction

```
tests/fixtures/github/rag_pipeline.mmd
```

```
graph LR
    A[Ask AI] --> B[Fetch Docs]
    B --> C[Create Embeddings]
    C --> D[Find Similar Content]
    D --> E[Add Context to Prompt]
    E --> F[LLM Answer]
```

## Root Cause Analysis

In `src/merm/layout/sugiyama.py`, the LR transform converts TB coordinates to LR by swapping x/y. The `node_sep` in `LayoutConfig` (default 30px) controls vertical spacing in TB mode, which becomes horizontal spacing in LR mode. However, the coordinate assignment does not properly account for variable node widths when computing LR positions -- wider nodes need more spacing to avoid overlap.

## Dependencies

- None (this is an independent layout fix)

## Acceptance Criteria

- [ ] `rag_pipeline.mmd` renders with at least 20px clear gap between all adjacent node pairs
- [ ] Arrows are visible between every pair of connected nodes (no arrow hidden behind overlapping nodes)
- [ ] The gap between nodes scales with node width -- wider nodes get more spacing
- [ ] Other LR flowcharts (check any existing LR fixtures) are not negatively affected
- [ ] TB flowcharts are not affected by the fix
- [ ] Existing tests pass (`uv run pytest`)
- [ ] Render `rag_pipeline.mmd` to PNG with cairosvg and visually verify that all nodes have clear gaps and all arrows are visible between them

## Test Scenarios

### Unit: Node gap measurement
- Render `rag_pipeline.mmd`, extract node positions from SVG, verify every adjacent pair has a gap >= 20px
- Create a synthetic LR graph with varying label lengths, verify no overlaps

### Unit: TB layout unaffected
- Render a TB flowchart before and after the fix, verify dimensions are identical

### Regression: Other LR layouts
- If any other LR fixtures exist in the corpus, render them and verify no regressions

### Visual: PNG verification
- Render `rag_pipeline.mmd` to PNG via cairosvg, visually verify clear gaps and visible arrows between all nodes
