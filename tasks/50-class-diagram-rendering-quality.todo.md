# Task 50: Class Diagram Rendering Quality

## Problem

Class diagram rendering has several visual quality issues:

1. **Inheritance arrows**: The hollow triangle markers are too large and poorly shaped — they look like open chevrons rather than clean inheritance triangles
2. **Layout**: Parent class (Animal) renders below children (Duck, Fish, Zebra) — inheritance hierarchy should flow top-down with parent at top or use a proper class diagram layout
3. **Class box alignment**: The three child classes aren't evenly spaced or aligned
4. **Relationship lines**: Arrows don't connect cleanly to class box edges (same endpoint precision issue as flowcharts)
5. **Member text alignment**: Field/method text left-alignment within the class box could be improved

### PNG Evidence

- `docs/class_demo.png` — Animal class below its subclasses, arrows too large, uneven spacing

## Acceptance Criteria

- [ ] Inheritance arrows (`<|--`) render as clean, properly-sized hollow triangles
- [ ] Composition (`*--`) and aggregation (`o--`) markers render correctly
- [ ] Parent classes render ABOVE child classes in the hierarchy (or configurable direction)
- [ ] Class boxes are evenly spaced and aligned
- [ ] Relationship lines connect cleanly to class box edges
- [ ] Class name section visually separated from members section (horizontal line)
- [ ] Fields and methods render with proper left-aligned text inside the box
- [ ] Visibility markers (+, -, #, ~) render correctly
- [ ] At least 5 class diagram corpus fixtures in `tests/fixtures/corpus/class/`
- [ ] `uv run pytest` passes with no regressions

### PNG Verification (mandatory)

- [ ] Render Animal/Duck/Fish/Zebra inheritance diagram — parent on top, clean triangles
- [ ] Render all relationship types (inheritance, composition, aggregation, association) — markers correct
- [ ] Render class with many members — text doesn't overflow box

## Dependencies
- None (independent of flowchart fixes)
