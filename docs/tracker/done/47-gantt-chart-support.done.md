# Task 47: Gantt Chart Support

## Goal

Add parser, IR, and renderer for Mermaid gantt charts. Gantt charts are self-contained (like pie charts) -- they do not use the Sugiyama layout engine. The renderer computes horizontal bar positions directly from parsed dates/durations.

## Dependencies

- None (all required infrastructure already exists)

---

## Mermaid Gantt Syntax Reference

```
gantt
    title A Project Plan
    dateFormat YYYY-MM-DD
    excludes weekends
    section Design
        Research           :a1, 2024-01-01, 30d
        Wireframes         :a2, after a1, 20d
    section Development
        Backend            :crit, b1, 2024-02-01, 45d
        Frontend           :active, b2, after b1, 30d
    section Testing
        QA                 :done, c1, after b2, 15d
```

### Task line syntax

Each task line inside a section has the format:

```
TaskName : [modifiers,] [id,] start, duration
```

- **Modifiers** (optional, comma-separated before id/start): `done`, `active`, `crit`
- **Id** (optional): alphanumeric identifier like `a1`, `task2`
- **Start**: either an ISO date (`2024-01-01`) or `after <id>` referencing another task
- **Duration**: integer followed by `d` (days), e.g. `30d`

### Supported directives

| Directive | Example | Required |
|-----------|---------|----------|
| `title` | `title My Plan` | No |
| `dateFormat` | `dateFormat YYYY-MM-DD` | No (default: `YYYY-MM-DD`) |
| `excludes` | `excludes weekends` | No (out of scope for v1) |
| `section` | `section Design` | No (tasks can exist without sections) |

### Modifier semantics

| Modifier | Visual meaning |
|----------|---------------|
| `done` | Completed task (greyed out / muted fill) |
| `active` | Currently active task (highlighted fill) |
| `crit` | Critical path task (red/bold fill) |

Modifiers can be combined: `crit, done, t1, 2024-01-01, 10d`

---

## Implementation Plan

### Step 1: IR (`src/pymermaid/ir/gantt.py`)

Create frozen dataclasses:

- `GanttTask`: name, id (optional), start (date or "after <id>"), duration_days, modifiers (frozenset of str), resolved_start (date), resolved_end (date)
- `GanttSection`: name, tasks (tuple of GanttTask)
- `GanttChart`: title (str), date_format (str), sections (tuple of GanttSection)

### Step 2: Parser (`src/pymermaid/parser/gantt.py`)

- Detect `gantt` keyword
- Parse `title`, `dateFormat` directives
- Parse `section` headers
- Parse task lines with regex, extracting modifiers, id, start, duration
- Resolve `after <id>` references by looking up predecessor end dates
- Raise `ParseError` on unknown task references, malformed lines
- Register in `src/pymermaid/parser/__init__.py`

### Step 3: Renderer (`src/pymermaid/render/gantt.py`)

No layout module needed -- the renderer computes positions directly:

- Calculate the global date range (min start to max end)
- Map dates to x-coordinates proportionally
- Render a time axis (x-axis) with date tick labels
- Render section headers as row group labels on the left
- Render each task as a horizontal `<rect>` bar with label text
- Apply modifier-based styling (fill colors for done/active/crit)
- Render title above chart
- Add `data-task-id`, `data-section` attributes for testability
- Accept optional `Theme` parameter (matching pie chart pattern)

### Step 4: Dispatch (`src/pymermaid/__init__.py`)

Add gantt detection in `render_diagram()`:

```python
if re.match(r"^\s*gantt", source, re.MULTILINE):
    from pymermaid.parser.gantt import parse_gantt
    from pymermaid.render.gantt import render_gantt_svg

    chart = parse_gantt(source)
    return render_gantt_svg(chart)
```

### Step 5: Corpus fixtures (`tests/fixtures/corpus/gantt/`)

Create at least 3 `.mmd` fixture files (see Test Fixtures below).

### Step 6: Tests (`tests/test_gantt.py`)

Unit tests for parser and renderer (see Test Scenarios below).

---

## Acceptance Criteria

- [ ] `from pymermaid.ir.gantt import GanttTask, GanttSection, GanttChart` works
- [ ] `GanttTask` dataclass has fields: `name`, `id`, `modifiers`, `start_date`, `end_date`, `duration_days`
- [ ] `GanttSection` dataclass has fields: `name`, `tasks`
- [ ] `GanttChart` dataclass has fields: `title`, `date_format`, `sections`
- [ ] `from pymermaid.parser.gantt import parse_gantt` works
- [ ] `parse_gantt(gantt_text)` returns a `GanttChart` with correctly parsed sections and tasks
- [ ] `parse_gantt` resolves `after <id>` dependencies so each task has concrete `start_date` and `end_date`
- [ ] `parse_gantt` raises `ParseError` for unknown `after` references
- [ ] `parse_gantt` raises `ParseError` for empty input or missing `gantt` keyword
- [ ] `parse_gantt` correctly parses `done`, `active`, `crit` modifiers
- [ ] `from pymermaid.render.gantt import render_gantt_svg` works
- [ ] `render_gantt_svg(chart)` returns valid SVG (starts with `<svg`, ends with `</svg>`)
- [ ] SVG contains a `<text>` element with the chart title (when title is set)
- [ ] SVG contains `<rect>` elements for each task bar with `data-task-id` attributes
- [ ] Task bars are positioned proportionally: a 30-day task bar is wider than a 15-day task bar
- [ ] Section names appear as labels in the SVG
- [ ] Tasks with `after` dependencies are positioned at the correct x-offset (after predecessor ends)
- [ ] Modifier styling: `crit` tasks have a distinct fill, `done` tasks have a muted fill, `active` tasks have a highlighted fill
- [ ] `render_diagram(gantt_source)` auto-detects and renders gantt charts (dispatch works)
- [ ] At least 3 corpus fixtures exist in `tests/fixtures/corpus/gantt/`
- [ ] `uv run pytest tests/test_gantt.py` passes with 15+ tests
- [ ] `uv run pytest` passes with no regressions

---

## Test Scenarios

### Unit: IR dataclasses
- Create a `GanttTask` with all fields, verify attributes
- Create a `GanttSection` with multiple tasks, verify tuple access
- Create a `GanttChart` with title, sections, verify structure
- Verify frozen dataclasses are immutable

### Unit: Parser -- basic parsing
- Parse a minimal gantt chart (one section, one task) -- verify section name, task name, dates
- Parse gantt with title directive -- verify `chart.title`
- Parse gantt with custom dateFormat -- verify `chart.date_format`
- Parse gantt without title -- verify `chart.title` is empty string
- Parse gantt with tasks outside any section -- handled gracefully (default/unnamed section)

### Unit: Parser -- task line variants
- Task with explicit date and duration: `Research :a1, 2024-01-01, 30d`
- Task with `after` dependency: `Wireframes :a2, after a1, 20d` -- verify start_date == a1.end_date
- Task with modifiers: `Backend :crit, done, b1, 2024-02-01, 10d` -- verify modifiers set
- Task without explicit id -- auto-generated or None
- Task with only name, start, duration (no id, no modifiers)

### Unit: Parser -- error cases
- Empty input raises `ParseError`
- Missing `gantt` keyword raises `ParseError`
- `after` referencing nonexistent task id raises `ParseError`
- Circular `after` references raise `ParseError` (or are detected)
- Malformed task line (missing duration) raises `ParseError`

### Unit: Parser -- comments
- Lines with `%%` comments are stripped and do not affect parsing

### Unit: Renderer -- SVG structure
- Render a simple gantt chart, verify SVG contains `<svg>` root element
- Verify title text element is present when title is set
- Verify title is absent when no title
- Verify each task produces a `<rect>` element with `data-task-id`
- Verify section labels appear as `<text>` elements

### Unit: Renderer -- proportional bar widths
- Render two tasks: one 30d, one 15d. Parse SVG, verify the 30d bar width is approximately 2x the 15d bar width.

### Unit: Renderer -- modifier styling
- Render tasks with `crit`, `done`, `active` modifiers. Verify they have distinct fill colors.

### Unit: Renderer -- time axis
- Verify SVG contains tick mark labels (date text elements on the x-axis)

### Integration: dispatch
- `render_diagram("gantt\n    title Test\n    section S\n        Task1 :t1, 2024-01-01, 10d\n")` returns valid SVG
- Verify existing diagram types still work (no regressions)

### Corpus: fixture rendering
- Each `.mmd` file in `tests/fixtures/corpus/gantt/` renders without error via `render_diagram()`

---

## Test Fixtures

### `tests/fixtures/corpus/gantt/basic.mmd`

```
gantt
    title Simple Project
    dateFormat YYYY-MM-DD
    section Planning
        Requirements :a1, 2024-01-01, 14d
        Design       :a2, after a1, 10d
    section Build
        Development  :b1, after a2, 30d
        Testing      :b2, after b1, 14d
```

### `tests/fixtures/corpus/gantt/modifiers.mmd`

```
gantt
    title Release Pipeline
    dateFormat YYYY-MM-DD
    section Phase 1
        Research     :done, r1, 2024-01-01, 20d
        Prototype    :done, p1, after r1, 15d
    section Phase 2
        Development  :active, d1, after p1, 40d
        Code Review  :crit, cr1, after d1, 5d
    section Phase 3
        QA           :q1, after cr1, 10d
        Release      :crit, rel1, after q1, 3d
```

### `tests/fixtures/corpus/gantt/no_title.mmd`

```
gantt
    dateFormat YYYY-MM-DD
    section Sprint 1
        Story A :s1, 2024-03-01, 7d
        Story B :s2, 2024-03-01, 14d
        Story C :s3, after s1, 7d
```

### `tests/fixtures/corpus/gantt/single_section.mmd`

```
gantt
    title Weekly Tasks
    dateFormat YYYY-MM-DD
    section This Week
        Monday meeting    :m1, 2024-06-03, 1d
        Write report      :m2, 2024-06-03, 3d
        Review PRs        :m3, after m2, 2d
        Deploy            :crit, m4, after m3, 1d
```

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/pymermaid/ir/gantt.py` | Create -- IR dataclasses |
| `src/pymermaid/parser/gantt.py` | Create -- parser |
| `src/pymermaid/render/gantt.py` | Create -- SVG renderer |
| `src/pymermaid/__init__.py` | Modify -- add gantt dispatch |
| `src/pymermaid/parser/__init__.py` | Modify -- export `parse_gantt` |
| `tests/test_gantt.py` | Create -- unit and integration tests |
| `tests/fixtures/corpus/gantt/basic.mmd` | Create -- fixture |
| `tests/fixtures/corpus/gantt/modifiers.mmd` | Create -- fixture |
| `tests/fixtures/corpus/gantt/no_title.mmd` | Create -- fixture |
| `tests/fixtures/corpus/gantt/single_section.mmd` | Create -- fixture |
