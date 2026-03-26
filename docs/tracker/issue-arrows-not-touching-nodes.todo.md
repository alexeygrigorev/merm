# Arrows don't touch node borders in LR layouts

## Bug

In LR flowcharts, arrows have visible gaps between the arrowhead and the node border. This is especially visible on:
- Diagonal edges (e.g., SQLite → Streamlit Dashboard going up-right)
- Edges to/from cylinder nodes
- Edges from diamond nodes (Decision → Result 1/2 in mermaid_readme)

Vertical arrows in TB layouts look fine — the issue is specific to diagonal/horizontal edges.

## Reproduction

```mermaid
graph LR
    App[Streamlit App] -->|logs & events| SQLite[(SQLite)]
    SQLite --> Dashboard[Streamlit Dashboard]
    SQLite --> Judge[Online Judge]
    Judge -->|evaluation events| SQLite
```

## Expected behavior

Arrow endpoints should touch the node border. No visible gap between arrowhead and node.

## Acceptance Criteria

- [ ] Arrows touch node borders for diagonal edges in LR layouts
- [ ] Arrows touch cylinder node borders
- [ ] Arrows touch diamond node borders
- [ ] No regression on TB layout arrows
- [ ] Existing tests pass
