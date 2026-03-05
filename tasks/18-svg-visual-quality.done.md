# 18 - SVG Visual Quality Improvements + Theme System

## Goal
Make the rendered SVG output look like mermaid.js, NOT like Graphviz/dot. Currently our output uses grey boxes, thin strokes, and tight spacing -- we need mermaid's modern aesthetic with its signature purple/yellow color scheme, generous spacing, and proper font stack. Additionally, architect a Theme system so all styling values flow from a single dataclass rather than being hardcoded.

## Dependencies
- Tasks 01-13, 17: all `.done.md` -- VERIFIED

## Scope

This task has two parts:
1. **Theme dataclass** -- Extract all hardcoded color/size constants from `render/svg.py` (and anywhere else) into a `Theme` dataclass. The renderer reads from the theme object, never from module-level constants.
2. **Default mermaid theme** -- Populate the default `Theme` instance with values from mermaid.js source code (`src/themes/theme-default.js` in the mermaid repo). Update spacing in `layout/config.py` accordingly.

## Part 1: Theme System

### Where to put it
Create `src/pymermaid/theme.py` with a `Theme` dataclass.

### What it must contain
All values currently hardcoded in `render/svg.py` lines 18-31 (the `_NODE_FILL`, `_NODE_STROKE`, etc. constants), plus layout spacing defaults. At minimum:

```python
@dataclass
class Theme:
    # Node styling
    node_fill: str
    node_stroke: str
    node_stroke_width: str
    node_text_color: str
    node_font_size: str
    node_padding_h: float  # horizontal padding inside node
    node_padding_v: float  # vertical padding inside node
    node_min_height: float
    node_border_radius: float  # rx for rounded rects

    # Edge styling
    edge_stroke: str
    edge_stroke_width: str
    edge_label_bg: str
    edge_label_font_size: str

    # Subgraph styling
    subgraph_fill: str
    subgraph_stroke: str
    subgraph_stroke_width: str
    subgraph_title_font_size: str

    # General
    font_family: str
    text_color: str
    background_color: str

    # Layout spacing
    rank_sep: float
    node_sep: float
```

### How the renderer uses it
- `render_svg()` accepts an optional `theme: Theme | None` parameter (defaults to `DEFAULT_THEME`).
- All CSS generation, inline attributes, and spacing decisions reference the theme.
- `LayoutConfig` should either accept a `Theme` or have its defaults updated from the theme.

## Part 2: Mermaid Default Theme Values

Study `src/themes/theme-default.js` in the mermaid.js repository. The engineer should look at the actual source to get precise values. The following are known starting points (verify against source):

### Colors
- Node fill: `#ECECFF` (light purple) -- currently `#f9f9f9`
- Node stroke: `#9370DB` (medium purple) -- currently `#333`
- Edge stroke: `#333333` with `stroke-width: 2px` -- currently 1px
- Edge label background: `rgba(232,232,232,0.8)` -- currently solid white
- Font family: `"trebuchet ms", verdana, arial, sans-serif` -- currently `sans-serif`
- Node font size: `16px` -- currently `14px`
- Subgraph fill: `#ffffde` (light yellow) with `#aaaa33` stroke -- currently `#e8e8e8`/`#999`
- Background: white

### Node Sizing
- Increase default horizontal padding from 8px to ~15px
- Increase default vertical padding from 4px to ~10px
- Minimum node height: ~54px (currently 30px feels cramped)
- Rounded rects: `rx="5"` (verify mermaid uses ~5px)
- Diamond shape should be sized proportionally to text content

### Edge Rendering
- Bezier curves for multi-segment edges (not straight polylines)
- Shape-aware connection points (not rect approximation for all shapes)
- Arrow markers: `markerUnits="userSpaceOnUse"` with `markerWidth="8" markerHeight="8"`

### Layout Spacing
- `rank_sep`: 80 (currently 50 in `layout/config.py`)
- `node_sep`: 50 (currently 30 in `layout/config.py`)
- Better viewBox centering

### Polish
- Round all coordinate values to 2 decimal places (avoid `188.98125000000001`)
- Add `font-family` directly on `<text>` elements for standalone SVG viewing
- Add `style="background-color: white"` on root `<svg>` element

## Acceptance Criteria

- [ ] `from pymermaid.theme import Theme, DEFAULT_THEME` works
- [ ] `Theme` is a dataclass with fields for all colors, sizes, and spacing listed above
- [ ] `DEFAULT_THEME` has values matching mermaid.js default theme (purple nodes, yellow subgraphs)
- [ ] `render_svg()` accepts an optional `theme` parameter
- [ ] No hardcoded color/size strings remain in `render/svg.py` -- all come from the theme
- [ ] Node fill in output SVG is `#ECECFF` (not `#f9f9f9`) when using default theme
- [ ] Node stroke in output SVG is `#9370DB` (not `#333`)
- [ ] Font family in output SVG is `"trebuchet ms", verdana, arial, sans-serif`
- [ ] Edge stroke-width is `2` (not `1`)
- [ ] Subgraph fill is `#ffffde` with stroke `#aaaa33`
- [ ] Default `rank_sep` is 80 and `node_sep` is 50
- [ ] Coordinate values in SVG output are rounded to max 2 decimal places
- [ ] SVG root element has white background style
- [ ] `<text>` elements have `font-family` attribute set directly
- [ ] `uv run pytest` passes (update expected values in tests as needed)
- [ ] Creating a custom theme with different colors and passing it to `render_svg()` produces output with those custom colors
- [ ] `docs/demo.svg` is regenerated with the new default theme

## Test Scenarios

### Unit: Theme dataclass
- Create Theme with all default values, verify each field
- Create Theme with overridden values, verify overrides applied
- DEFAULT_THEME has expected mermaid purple/yellow colors

### Unit: Theme integration with renderer
- Render with DEFAULT_THEME, parse SVG, verify node fill is `#ECECFF`
- Render with DEFAULT_THEME, parse SVG, verify font-family is mermaid's font stack
- Render with DEFAULT_THEME, parse SVG, verify edge stroke-width is `2`
- Render with custom theme (red nodes), verify node fill is red in output
- Render with custom theme, verify subgraph colors match custom values

### Unit: Coordinate rounding
- Render a diagram, parse SVG, verify no coordinate has more than 2 decimal places

### Unit: SVG output structure
- Root `<svg>` has background-color style
- `<text>` elements have font-family attribute (not just CSS class)

### Integration: Visual quality
- Render `tests/fixtures/simple_flowchart.mmd`, verify output uses new theme colors
- Render all 4 existing fixtures, verify no regressions (tests pass)

## Implementation Notes

1. Start by creating `src/pymermaid/theme.py` with the `Theme` dataclass and `DEFAULT_THEME`.
2. Modify `render/svg.py` to accept and use Theme -- replace all `_NODE_FILL` etc. constants with reads from `theme.*`.
3. Update `LayoutConfig` defaults or wire theme spacing through the pipeline.
4. Update node sizing (padding, min height) in the measurement/layout code.
5. Update `render/edges.py` for stroke-width, markers, and Bezier curves.
6. Add coordinate rounding in the render step.
7. Run full test suite and fix any broken expected values.
8. Regenerate `docs/demo.svg`.

## Estimated Complexity
Medium-Large. The theme dataclass is straightforward. The main work is threading it through the renderer, updating all hardcoded values, and adjusting node sizing / edge rendering. Expect many test expected-value updates.
