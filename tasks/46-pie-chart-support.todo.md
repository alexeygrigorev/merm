# Task 46: Pie Chart Support

## Goal

Add parser and renderer for pie charts.

## Example Input

```
pie title Favorite Pets
    "Dogs" : 386
    "Cats" : 85
    "Rats" : 15
    "Hamsters" : 35
```

## Scope

- Parse `pie` blocks with optional `title`
- Support `showData` keyword to display values
- Parse label-value pairs
- Render as SVG circle with colored wedges
- Render labels (either as legend or inline)
- Render title centered above the chart

## Acceptance Criteria

- [ ] `render_diagram(pie_input)` returns valid SVG without errors
- [ ] Pie wedge angles are proportional to values
- [ ] Each wedge has a distinct fill color (use a standard palette)
- [ ] Labels identify each wedge (legend or inline)
- [ ] Title renders centered above the pie
- [ ] Single-item pie renders as a full circle
- [ ] At least 3 corpus fixtures in `tests/fixtures/corpus/pie/`
- [ ] PNG verification: render each fixture and visually confirm wedges, labels, and proportions
- [ ] `uv run pytest` passes with no regressions

## Dependencies
- None
