# Task 47: Gantt Chart Support

## Goal

Add parser, layout, and renderer for Gantt charts.

## Example Input

```
gantt
    title A Project Plan
    dateFormat YYYY-MM-DD
    section Design
        Research     :a1, 2024-01-01, 30d
        Wireframes   :a2, after a1, 20d
    section Development
        Backend      :b1, 2024-02-01, 45d
        Frontend     :b2, after b1, 30d
    section Testing
        QA           :c1, after b2, 15d
```

## Scope

- Parse `gantt` blocks with title, dateFormat, sections, and tasks
- Support task syntax: name, id, start date, duration (and `after` dependencies)
- Support `done`, `active`, `crit` task modifiers
- Render horizontal bar chart with time axis
- Render section groupings
- Render task bars with labels

## Acceptance Criteria

- [ ] `render_diagram(gantt_input)` returns valid SVG without errors
- [ ] Tasks render as horizontal bars at correct time positions
- [ ] Task bars are proportional to duration
- [ ] `after` dependencies position tasks correctly (start after predecessor ends)
- [ ] Section headers group tasks visually
- [ ] Title renders above the chart
- [ ] Time axis labels are readable
- [ ] At least 3 corpus fixtures in `tests/fixtures/corpus/gantt/`
- [ ] PNG verification: render each fixture and visually confirm task bars, sections, and timeline
- [ ] `uv run pytest` passes with no regressions

## Dependencies
- None
