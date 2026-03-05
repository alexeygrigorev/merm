# Task 46: Pie Chart Support

## Goal

Add parser, IR, and SVG renderer for Mermaid pie charts. Pie charts are self-contained and do not require the Sugiyama layout engine -- they only need trigonometric wedge placement within a fixed-size circle.

## Mermaid Pie Chart Syntax Reference

```
pie [showData] [title TITLE_TEXT]
    "Label 1" : value1
    "Label 2" : value2
    "Label 3" : value3
```

Rules:
- The block starts with `pie` on the first non-blank line.
- `showData` is an optional keyword that indicates raw values should be displayed alongside percentages.
- `title` followed by text sets a centered title above the chart (the title extends to end-of-line).
- `title` and `showData` can appear on the same line as `pie` or on subsequent lines.
- Each data entry is `"Label" : number` where the label is a quoted string and the number is a positive integer or float.
- `%%` comments are supported (same as all Mermaid diagrams).
- At least one data entry is required.

## Architecture (following existing patterns)

### 1. IR dataclass: `src/pymermaid/ir/pie.py`

```python
@dataclass(frozen=True)
class PieSlice:
    label: str
    value: float

@dataclass(frozen=True)
class PieChart:
    title: str           # empty string if no title
    show_data: bool      # whether showData was specified
    slices: tuple[PieSlice, ...]
```

### 2. Parser: `src/pymermaid/parser/pie.py`

- Function: `parse_pie(text: str) -> PieChart`
- Raises `ParseError` on invalid input (empty input, no slices, negative values, malformed lines).
- Strips `%%` comments before processing.

### 3. Renderer: `src/pymermaid/render/pie.py`

- Function: `render_pie_svg(chart: PieChart, theme: Theme | None = None) -> str`
- No layout engine needed. The renderer computes wedge angles from slice values.
- SVG structure:
  - `<svg>` with viewBox sized to fit chart + legend + title
  - `<style>` with CSS classes for `.pie-slice`, `.pie-label`, `.pie-title`, `.pie-legend`
  - Title `<text>` centered above the circle (if title is non-empty)
  - For each slice: `<path>` element using SVG arc commands with the appropriate fill color
  - Legend to the right of the circle: colored square + label text (+ percentage, + raw value if `showData`)
- Single-slice special case: render as a full `<circle>` instead of arc path (arcs degenerate at 360 degrees).

### 4. Dispatch: `src/pymermaid/__init__.py`

Add a branch in `render_diagram()`:

```python
if re.match(r"^\s*pie\b", source, re.MULTILINE):
    from pymermaid.parser.pie import parse_pie
    from pymermaid.render.pie import render_pie_svg
    chart = parse_pie(source)
    return render_pie_svg(chart)
```

### 5. Re-exports

- Add `parse_pie` to `src/pymermaid/parser/__init__.py`
- Add `render_pie_svg` to `src/pymermaid/render/__init__.py` (if it has re-exports)

## Color Palette for Wedges

Use a 10-color palette (cycling for charts with >10 slices). These match mermaid.js pie chart defaults:

```python
PIE_COLORS = [
    "#4572A7",  # steel blue
    "#AA4643",  # brick red
    "#89A54E",  # olive green
    "#80699B",  # muted purple
    "#3D96AE",  # teal
    "#DB843D",  # warm orange
    "#92A8CD",  # light slate blue
    "#A47D7C",  # mauve
    "#B5CA92",  # sage green
    "#5C6BC0",  # indigo
]
```

## Test Fixtures

Create `tests/fixtures/corpus/pie/` with at least these files:

### `tests/fixtures/corpus/pie/basic.mmd`
```
pie title Favorite Pets
    "Dogs" : 386
    "Cats" : 85
    "Rats" : 15
```

### `tests/fixtures/corpus/pie/show_data.mmd`
```
pie showData title Project Time Allocation
    "Development" : 45
    "Testing" : 25
    "Documentation" : 15
    "Meetings" : 10
    "Code Review" : 5
```

### `tests/fixtures/corpus/pie/single_slice.mmd`
```
pie title Full Circle
    "Everything" : 100
```

### `tests/fixtures/corpus/pie/many_slices.mmd`
```
pie title Monthly Budget
    "Rent" : 1200
    "Food" : 400
    "Transport" : 150
    "Utilities" : 100
    "Entertainment" : 80
    "Savings" : 300
    "Insurance" : 120
    "Healthcare" : 60
    "Clothing" : 50
    "Misc" : 40
    "Education" : 100
```

### `tests/fixtures/corpus/pie/no_title.mmd`
```
pie
    "Yes" : 70
    "No" : 30
```

## Acceptance Criteria

- [ ] `from pymermaid.ir.pie import PieSlice, PieChart` works without error
- [ ] `from pymermaid.parser.pie import parse_pie` works without error
- [ ] `from pymermaid.render.pie import render_pie_svg` works without error
- [ ] `parse_pie(...)` returns a `PieChart` with correct `title`, `show_data`, and `slices`
- [ ] `parse_pie` raises `ParseError` on empty input, on input with no slices, and on negative values
- [ ] `render_pie_svg(chart)` returns a valid SVG string (starts with `<svg`, contains `</svg>`)
- [ ] The SVG contains one `<path>` or `<circle>` element per slice (verifiable by counting `class="pie-slice"` elements or `data-slice-label` attributes)
- [ ] Wedge angles are proportional to values -- the sum of all arc sweep angles equals 360 degrees (within floating-point tolerance)
- [ ] Each wedge has a distinct fill color from the palette
- [ ] A legend is rendered with one entry per slice showing label and percentage
- [ ] When `showData` is set, raw values also appear in the legend
- [ ] Title renders as a centered `<text>` element above the pie (when title is non-empty)
- [ ] Single-item pie renders as a full circle (not a degenerate arc)
- [ ] `render_diagram("pie title Test\n    \"A\" : 50\n    \"B\" : 50")` dispatches correctly and returns valid SVG
- [ ] At least 5 corpus fixture files exist in `tests/fixtures/corpus/pie/`
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: PieChart IR
- Create a PieChart with title, show_data=False, and 3 slices -- verify all fields
- Create a PieChart with empty title, show_data=True -- verify defaults

### Unit: Parser basics
- Parse the `basic.mmd` fixture -- verify title is "Favorite Pets", 3 slices, correct labels and values
- Parse the `show_data.mmd` fixture -- verify show_data=True
- Parse the `no_title.mmd` fixture -- verify title is empty string
- Parse the `single_slice.mmd` fixture -- verify 1 slice with value 100

### Unit: Parser edge cases
- Input with `%%` comments between slices -- comments are stripped, slices parse correctly
- Input with extra blank lines -- parsed correctly
- Float values (e.g., `"X" : 3.14`) -- parsed as float
- Negative value raises `ParseError`
- No slices (just `pie title Foo`) raises `ParseError`
- Empty string input raises `ParseError`
- Missing quotes on label raises `ParseError`

### Unit: Renderer output structure
- Render basic chart -- SVG contains `<svg` and `</svg>`
- Render basic chart -- SVG contains 3 path elements (one per slice)
- Render single-slice chart -- SVG contains a `<circle>` (not a degenerate `<path>`)
- Render chart with title -- SVG contains a `<text>` element with the title string
- Render chart without title -- no title text element present

### Unit: Renderer geometry
- For a 2-slice chart with equal values (50/50) -- verify the two arc sweep angles are each 180 degrees (by checking the SVG path arc flags or computing from the path data)
- For a chart with values [75, 25] -- first wedge spans 270 degrees, second spans 90 degrees

### Integration: render_diagram dispatch
- `render_diagram("pie title X\n    \"A\" : 1")` returns valid SVG
- `render_diagram("pie\n    \"A\" : 60\n    \"B\" : 40")` returns valid SVG

### Corpus: fixture rendering
- Each `.mmd` file in `tests/fixtures/corpus/pie/` renders without error via `render_diagram()`
- Each rendered SVG is well-formed XML (parseable by `xml.etree.ElementTree.fromstring`)

## Dependencies

- None. This task is independent of other in-progress tasks.
- Uses existing infrastructure: `ParseError` from `pymermaid.parser.flowchart`, `Theme` from `pymermaid.theme`.
