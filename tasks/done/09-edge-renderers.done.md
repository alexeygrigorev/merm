# 09 - Edge Renderers

## Goal
Implement SVG rendering for all edge types, arrow markers, and edge labels. Currently `_render_edge` in `src/pymermaid/render/__init__.py` only produces a basic `<path>` with a single hardcoded `#arrowhead` marker. This task extends the renderer to handle all `EdgeType` and `ArrowType` combinations from the IR, with correct line styles, multiple marker types, edge labels with background rectangles, and smooth Bezier curves for multi-segment edges.

## Architecture

### Module Location
`src/pymermaid/render/edges.py` -- new module for edge-specific rendering logic.

The existing `_render_edge`, `_make_defs`, `_points_to_path_d`, and `_edge_midpoint` functions in `src/pymermaid/render/__init__.py` should be refactored to delegate to this new module.

### Arrow Markers (SVG `<marker>` in `<defs>`)

Define reusable SVG `<marker>` elements in `<defs>`:

1. **Triangle arrow** (`ArrowType.arrow`): The default `-->` arrowhead. `<marker>` containing a `<path>` with triangle shape (`M0,0 L10,3.5 L0,7 Z`). `id="arrow"`.
2. **Circle endpoint** (`ArrowType.circle`): For `--o`. `<marker>` containing a `<circle>`. `id="circle-end"`.
3. **Cross endpoint** (`ArrowType.cross`): For `--x`. `<marker>` containing two crossed `<line>` elements (or a `<path>` forming an X). `id="cross-end"`.
4. **Reverse triangle** (`ArrowType.arrow` used as `source_arrow`): Same triangle but `orient="auto-start-reverse"` or a separate reversed path. `id="arrow-reverse"`.

Each marker must have configurable: `markerWidth`, `markerHeight`, `refX`, `refY`, `orient="auto"`, `markerUnits="strokeWidth"`, and appropriate `fill`/`stroke`.

### Edge Line Styles

Map `EdgeType` to SVG stroke attributes:

| EdgeType | `stroke-dasharray` | `stroke-width` | `visibility` |
|----------|-------------------|----------------|-------------|
| `arrow` | (none/solid) | 2 | visible |
| `open` | (none/solid) | 2 | visible |
| `dotted` | "3" | 2 | visible |
| `dotted_arrow` | "3" | 2 | visible |
| `thick` | (none/solid) | 3.5 | visible |
| `thick_arrow` | (none/solid) | 3.5 | visible |
| `invisible` | (none) | 0 | hidden |

### Marker Assignment Logic

Determine `marker-start` and `marker-end` from the IR `Edge`:
- `target_arrow == ArrowType.arrow` -> `marker-end="url(#arrow)"`
- `target_arrow == ArrowType.circle` -> `marker-end="url(#circle-end)"`
- `target_arrow == ArrowType.cross` -> `marker-end="url(#cross-end)"`
- `target_arrow == ArrowType.none` -> no `marker-end`
- `source_arrow == ArrowType.arrow` -> `marker-start="url(#arrow-reverse)"`
- `source_arrow == ArrowType.none` -> no `marker-start`

### Edge Path Generation

- **Straight segments** (2 points): `M x1,y1 L x2,y2`
- **Multi-segment with smooth curves** (3+ points): Convert to cubic Bezier using `C` commands. Use Catmull-Rom to cubic Bezier conversion or simple control point interpolation for smooth routing.
- Function signature: `points_to_path_d(points: list[Point], smooth: bool = True) -> str`

### Edge Labels

- Position at midpoint of edge path (existing `_edge_midpoint` logic).
- Render as `<rect>` (white fill, small padding) behind `<text>` so the label is legible over the edge line.
- Handle multi-line labels (split on `<br/>`).

### Public API

```python
def make_edge_defs(parent: ET.Element) -> None:
    """Add all arrow/endpoint marker definitions to a <defs> element."""

def render_edge(
    parent: ET.Element,
    edge_layout: EdgeLayout,
    ir_edge: Edge | None,
    smooth: bool = True,
) -> None:
    """Render a single edge with correct style, markers, and optional label."""

def points_to_path_d(points: list[Point], smooth: bool = True) -> str:
    """Convert layout points to an SVG path d-string, optionally smoothed."""
```

## Acceptance Criteria

- [ ] Module `src/pymermaid/render/edges.py` exists and is importable
- [ ] `from pymermaid.render.edges import make_edge_defs, render_edge, points_to_path_d` works
- [ ] `make_edge_defs` creates at least 4 `<marker>` elements: arrow, circle-end, cross-end, arrow-reverse
- [ ] Each marker has `id`, `markerWidth`, `markerHeight`, `refX`, `refY`, `orient`, and `markerUnits` attributes
- [ ] Arrow marker contains a triangle `<path>` with `fill` set
- [ ] Circle marker contains a `<circle>` element
- [ ] Cross marker contains line or path elements forming an X shape
- [ ] `render_edge` with `EdgeType.arrow` produces a `<path>` with no `stroke-dasharray` and `marker-end` pointing to the arrow marker
- [ ] `render_edge` with `EdgeType.open` produces a `<path>` with no `marker-end`
- [ ] `render_edge` with `EdgeType.dotted_arrow` produces a `<path>` with `stroke-dasharray` set (e.g., "3") and `marker-end`
- [ ] `render_edge` with `EdgeType.dotted` produces a `<path>` with `stroke-dasharray` and no arrow markers
- [ ] `render_edge` with `EdgeType.thick_arrow` produces a `<path>` with `stroke-width` of 3.5 (or similar thick value) and `marker-end`
- [ ] `render_edge` with `EdgeType.thick` produces a thick `<path>` with no arrow markers
- [ ] `render_edge` with `EdgeType.invisible` produces a `<path>` with `visibility="hidden"` or `stroke="none"`
- [ ] `render_edge` with `target_arrow=ArrowType.circle` sets `marker-end` to the circle marker
- [ ] `render_edge` with `target_arrow=ArrowType.cross` sets `marker-end` to the cross marker
- [ ] `render_edge` with `source_arrow=ArrowType.arrow` sets `marker-start` to the reverse arrow marker
- [ ] `points_to_path_d` with 2 points returns a path using `M` and `L` commands
- [ ] `points_to_path_d` with 3+ points and `smooth=True` returns a path containing `C` (cubic Bezier) commands
- [ ] `points_to_path_d` with 3+ points and `smooth=False` returns a path using only `M` and `L` commands
- [ ] Edge labels render as `<text>` with a background `<rect>` (white or near-white fill)
- [ ] Edge label `<rect>` appears before the `<text>` in DOM order (so text renders on top)
- [ ] Edge label position is at the midpoint of the edge path
- [ ] Multi-line edge labels (containing `<br/>`) render with `<tspan>` elements
- [ ] `render_svg` in `src/pymermaid/render/__init__.py` is updated to use the new edge rendering functions
- [ ] The old hardcoded `#arrowhead` marker is replaced by the new `make_edge_defs` output
- [ ] `uv run pytest tests/test_edges.py` passes with all tests green

## Test Scenarios

### Unit: Marker definitions
- `make_edge_defs` adds exactly 4 markers to the parent element
- Each marker has required attributes (`id`, `markerWidth`, `markerHeight`, `refX`, `refY`, `orient`)
- Arrow marker `id` is findable and contains a `<path>` child
- Circle marker contains a `<circle>` child
- Cross marker contains path or line children forming an X

### Unit: Edge line styles
- `EdgeType.arrow` edge has no `stroke-dasharray` attribute (or solid)
- `EdgeType.dotted_arrow` edge has `stroke-dasharray` attribute set
- `EdgeType.thick_arrow` edge has `stroke-width` >= 3
- `EdgeType.invisible` edge has `visibility="hidden"` or `stroke="none"`
- `EdgeType.open` edge has no `marker-end` attribute
- `EdgeType.dotted` edge has dashed stroke and no arrow markers
- `EdgeType.thick` edge has thick stroke and no arrow markers

### Unit: Marker assignment
- Edge with `target_arrow=ArrowType.arrow` has `marker-end` containing "arrow"
- Edge with `target_arrow=ArrowType.circle` has `marker-end` containing "circle"
- Edge with `target_arrow=ArrowType.cross` has `marker-end` containing "cross"
- Edge with `target_arrow=ArrowType.none` has no `marker-end` attribute
- Edge with `source_arrow=ArrowType.arrow` has `marker-start` attribute set
- Edge with `source_arrow=ArrowType.none` has no `marker-start` attribute

### Unit: Path generation
- `points_to_path_d` with empty list returns empty string
- `points_to_path_d` with single point returns `M` only
- `points_to_path_d` with 2 points returns `M...L...`
- `points_to_path_d` with 4 points and `smooth=True` contains `C` commands
- `points_to_path_d` with 4 points and `smooth=False` contains only `M` and `L`
- Resulting path string is parseable (starts with M, contains valid SVG path commands)

### Unit: Edge labels
- Edge with `label="Yes"` renders a `<text>` element containing "Yes"
- Label has a sibling `<rect>` with white-ish fill appearing before it in the group
- Label `<text>` has `text-anchor="middle"` for centering
- Edge with no label renders no `<text>` or `<rect>` for the label
- Multi-line label `"Line1<br/>Line2"` renders `<tspan>` elements

### Unit: Edge label positioning
- Label is positioned at approximately the midpoint of a 2-point edge
- Label is positioned at approximately the midpoint of a multi-segment edge

### Integration: Full render_svg with edges
- Render a Diagram with an `EdgeType.arrow` edge and verify SVG output contains a `<path>` with `marker-end`
- Render a Diagram with a `EdgeType.dotted_arrow` edge and verify dashed stroke in output
- Render a Diagram with `target_arrow=ArrowType.circle` and verify circle marker is present in `<defs>` and referenced
- Render a Diagram with an edge label and verify both `<rect>` and `<text>` appear in the edge group

### Integration: All edge type combinations produce valid SVG
- For each `EdgeType` value, create a minimal diagram, render SVG, and verify the output is well-formed XML

## Dependencies
- Task 07 (SVG renderer core) -- status: **done**
- Task 06 (Sugiyama layout / edge paths) -- status: **done**
- Task 03 (IR with `EdgeType`, `ArrowType` enums) -- status: **done**

## Estimated Complexity
Medium -- ~200-300 lines of implementation in `edges.py`, plus ~50 lines of refactoring in `render/__init__.py`, plus ~300-400 lines of tests.
