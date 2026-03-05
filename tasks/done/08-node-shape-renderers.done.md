# 08 - Node Shape Renderers

## Goal
Implement SVG rendering for all 14 classic flowchart node shapes defined in `NodeShape` enum (`src/pymermaid/ir/__init__.py`). Each shape must produce SVG elements and calculate edge connection points on its boundary.

## Architecture

### Module Location
`src/pymermaid/render/shapes.py`

### ShapeRenderer Protocol
A `ShapeRenderer` protocol (or abstract base class) with two methods:

- `render(x, y, w, h, label, style) -> list[str]` -- Return SVG element strings for the shape at the given position and size. `style` is an optional dict of CSS properties (fill, stroke, etc.).
- `connection_point(x, y, w, h, angle_rad) -> tuple[float, float]` -- Return the (px, py) coordinate where an edge arriving from the given angle intersects the shape boundary. The angle is in radians, measured from the positive x-axis (0 = right, pi/2 = down in SVG coordinate space).

### Registry
A `SHAPE_REGISTRY: dict[NodeShape, ShapeRenderer]` mapping every `NodeShape` enum value to its renderer. A convenience function `get_shape_renderer(shape: NodeShape) -> ShapeRenderer` that raises `KeyError` with a clear message if a shape is missing.

### Shapes to Implement

Each shape is a callable or small class implementing the `ShapeRenderer` protocol:

1. **Rectangle** (`NodeShape.rect`): `<rect x y width height>`
2. **Rounded Rectangle** (`NodeShape.rounded`): `<rect rx="5" ry="5" ...>`
3. **Stadium** (`NodeShape.stadium`): `<rect rx="{h/2}" ry="{h/2}" ...>` (fully rounded ends)
4. **Subroutine** (`NodeShape.subroutine`): `<rect>` plus two inner vertical `<line>` elements at ~8px from left and right edges
5. **Cylinder** (`NodeShape.cylinder`): `<path>` with elliptical arcs for top/bottom caps
6. **Circle** (`NodeShape.circle`): `<circle cx cy r>` where r = max(w, h) / 2
7. **Asymmetric** (`NodeShape.asymmetric`): `<polygon>` flag/banner shape
8. **Diamond** (`NodeShape.diamond`): `<polygon>` with 4 points (top, right, bottom, left)
9. **Hexagon** (`NodeShape.hexagon`): `<polygon>` with 6 points
10. **Parallelogram** (`NodeShape.parallelogram`): `<polygon>` skewed rectangle (slant right)
11. **Parallelogram Alt** (`NodeShape.parallelogram_alt`): `<polygon>` skewed opposite direction
12. **Trapezoid** (`NodeShape.trapezoid`): `<polygon>` wider at bottom
13. **Trapezoid Alt** (`NodeShape.trapezoid_alt`): `<polygon>` wider at top
14. **Double Circle** (`NodeShape.double_circle`): Two concentric `<circle>` elements with gap ~5px

### Edge Connection Points

For each shape, `connection_point` must return a point on the shape boundary (not the bounding box center). The algorithm varies by shape:
- **Rectangle/Rounded/Stadium/Subroutine/Parallelogram/Trapezoid**: Ray-rectangle (or ray-polygon) intersection
- **Circle/Double Circle**: Point on circumference at given angle
- **Diamond/Hexagon/Asymmetric**: Ray-polygon intersection using the polygon vertices

## Acceptance Criteria

- [ ] Module `src/pymermaid/render/shapes.py` exists and is importable
- [ ] `from pymermaid.render.shapes import ShapeRenderer, SHAPE_REGISTRY, get_shape_renderer` works
- [ ] `ShapeRenderer` is defined as a `Protocol` (or ABC) with `render` and `connection_point` methods
- [ ] `SHAPE_REGISTRY` contains exactly 14 entries, one for every `NodeShape` enum value
- [ ] `get_shape_renderer(shape)` returns a renderer for all 14 shapes
- [ ] `get_shape_renderer` raises `KeyError` for invalid input
- [ ] Each renderer's `render(x, y, w, h, label, style)` returns a non-empty list of SVG element strings
- [ ] Rectangle render output contains `<rect` with correct x, y, width, height attributes
- [ ] Rounded rectangle render output contains `<rect` with `rx` attribute set
- [ ] Stadium render output contains `<rect` with `rx` equal to half the height
- [ ] Subroutine render output contains a `<rect` and two `<line` elements for the inner borders
- [ ] Cylinder render output contains `<path` with elliptical arc commands (`A`)
- [ ] Circle render output contains `<circle` with correct `cx`, `cy`, `r` attributes
- [ ] Diamond render output contains `<polygon` with 4 points
- [ ] Hexagon render output contains `<polygon` with 6 points
- [ ] Double circle render output contains two `<circle` elements with different radii
- [ ] Asymmetric, parallelogram, parallelogram_alt, trapezoid, trapezoid_alt render outputs each contain `<polygon`
- [ ] Each `connection_point(x, y, w, h, angle)` returns a `tuple[float, float]`
- [ ] Circle `connection_point` at angle 0 returns a point on the right edge of the circle
- [ ] Rectangle `connection_point` at angle 0 returns `(x + w/2, y)` (right edge center, adjusting for SVG coords)
- [ ] Diamond `connection_point` returns points on the diamond boundary, not the bounding rect
- [ ] `uv run pytest tests/test_shapes.py` passes with all tests green

## Test Scenarios

### Unit: ShapeRenderer protocol and registry
- `SHAPE_REGISTRY` has exactly 14 entries
- Every `NodeShape` enum value has a corresponding entry in `SHAPE_REGISTRY`
- `get_shape_renderer(NodeShape.rect)` returns a renderer
- `get_shape_renderer` with an invalid value raises `KeyError`

### Unit: Rectangle renderer
- `render(10, 20, 100, 50, "Hello", None)` returns list containing a string with `<rect`
- Output string contains `x=`, `y=`, `width=`, `height=` with correct values
- `connection_point` at angle 0 (right) returns point at right edge
- `connection_point` at angle pi (left) returns point at left edge
- `connection_point` at angle pi/2 (down) returns point at bottom edge

### Unit: Circle renderer
- `render` output contains `<circle` with `cx`, `cy`, `r`
- `r` is derived from max(w, h) / 2
- `connection_point` at angle 0 returns `(cx + r, cy)`
- `connection_point` at angle pi returns `(cx - r, cy)`
- `connection_point` at arbitrary angle returns point at distance r from center

### Unit: Rounded rectangle renderer
- `render` output contains `rx` attribute
- `rx` value is a positive number (e.g., 5)

### Unit: Stadium renderer
- `render` output contains `rx` attribute equal to h/2
- Visually distinct from rounded rectangle for tall nodes

### Unit: Subroutine renderer
- `render` returns at least 3 elements (rect + 2 lines)
- Inner lines are positioned at ~8px from left and right edges

### Unit: Cylinder renderer
- `render` output contains `<path` with arc commands
- Output contains elliptical arc command `A`

### Unit: Diamond renderer
- `render` output contains `<polygon` with `points` attribute
- Points form a diamond (4 vertices: top, right, bottom, left of bounding box)
- `connection_point` at angle 0 returns right vertex
- `connection_point` at angle pi/4 returns a point on the upper-right edge (not a vertex)

### Unit: Hexagon renderer
- `render` output contains `<polygon` with 6 coordinate pairs in `points`

### Unit: Double circle renderer
- `render` returns strings containing two `<circle` elements
- Inner circle has smaller radius than outer circle

### Unit: Polygon shapes (asymmetric, parallelogram, parallelogram_alt, trapezoid, trapezoid_alt)
- Each `render` returns output containing `<polygon`
- Each has a `points` attribute with appropriate vertex count
- Parallelogram and parallelogram_alt are mirror images (skew in opposite directions)
- Trapezoid and trapezoid_alt are mirror images (wider end swapped)

### Unit: Connection point boundary validation
- For each shape, verify `connection_point` returns a point that lies on or very near the shape boundary (within floating-point tolerance)
- For circle: distance from center equals radius
- For rectangle: point lies on one of the four edges
- For diamond: point lies on one of the four edges of the diamond polygon

### Integration: All shapes render valid SVG fragments
- For each of the 14 shapes, call `render` with sample dimensions and verify the output can be parsed as valid XML fragments (well-formed element strings)

## Dependencies
- Task 03 (IR data model with `NodeShape` enum) -- status: **done**
- Task 07 (SVG renderer core) -- status: **todo** (this task can proceed in parallel since shapes are self-contained SVG fragment generators, but final integration requires task 07)

## Estimated Complexity
Medium -- repetitive but each shape has unique geometry. ~300-400 lines of implementation code plus ~400 lines of tests.
