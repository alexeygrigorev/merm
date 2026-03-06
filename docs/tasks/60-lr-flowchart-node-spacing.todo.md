# Task 60: LR flowchart nodes touching/overlapping

## Problem

In left-to-right flowcharts, nodes are placed too close together — they touch or nearly overlap, making arrows between them barely visible.

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

## Expected behavior

- Adequate horizontal spacing between nodes in LR layouts
- Arrows should be clearly visible between nodes (not hidden by node borders touching)
- Spacing should scale with the number of nodes

## Acceptance criteria

- [ ] rag_pipeline.mmd renders with clear gaps between all nodes
- [ ] Arrows are visible between every pair of connected nodes
- [ ] Other LR flowcharts not negatively affected
- [ ] Visual verification via PNG rendering
