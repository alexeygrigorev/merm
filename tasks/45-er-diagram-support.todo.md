# Task 45: ER Diagram Support

## Goal

Add parser, layout, and renderer for Entity-Relationship diagrams.

## Example Input

```
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
    CUSTOMER {
        string name
        int age
        string email
    }
    ORDER {
        int id
        date created
    }
```

## Scope

- Parse `erDiagram` blocks
- Support all relationship types: ||--o{, ||--|{, }|..|{, ||--||, etc.
- Support entity attributes (fields with types)
- Layout entities in a grid or force-directed arrangement
- Render entities as labeled rectangles with attribute sections
- Render relationships as lines with cardinality markers

## Acceptance Criteria

- [ ] `render_diagram(erDiagram_input)` returns valid SVG without errors
- [ ] All ER relationship types parse correctly (1-to-1, 1-to-many, many-to-many, zero-or-one, etc.)
- [ ] Entity attributes render inside entity boxes with type and name
- [ ] Relationship labels render on the connecting lines
- [ ] Cardinality markers (||, o{, |{, etc.) render at line endpoints
- [ ] At least 5 corpus fixtures in `tests/fixtures/corpus/er/`
- [ ] PNG verification: render each fixture and visually confirm entities, attributes, and relationships
- [ ] `uv run pytest` passes with no regressions

## Dependencies
- None
