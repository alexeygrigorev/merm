# Task 48: Mindmap Support

## Goal

Add parser, layout, and renderer for mindmap diagrams.

## Example Input

```
mindmap
  root((Central Topic))
    Origins
      Long history
      Popularized by Tony Buzan
    Research
      On effectiveness
      On features
    Tools
      Pen and paper
      Mermaid
```

## Scope

- Parse `mindmap` blocks with indentation-based hierarchy
- Support root node shapes: ((circle)), (rounded), [square], ))cloud((
- Layout as radial tree from center node
- Render nodes with connecting branches (curved lines)
- Different colors per branch

## Acceptance Criteria

- [ ] `render_diagram(mindmap_input)` returns valid SVG without errors
- [ ] Root node renders at center with specified shape
- [ ] Child nodes branch outward from root
- [ ] Indentation levels determine parent-child relationships
- [ ] Branches use distinct colors for each top-level subtree
- [ ] Node text is readable and doesn't overlap
- [ ] At least 3 corpus fixtures in `tests/fixtures/corpus/mindmap/`
- [ ] PNG verification: render each fixture and visually confirm hierarchy, layout, and readability
- [ ] `uv run pytest` passes with no regressions

## Dependencies
- None
