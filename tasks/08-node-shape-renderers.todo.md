# 08 - Node Shape Renderers

## Goal
Implement SVG rendering for all 14 classic flowchart node shapes plus the double circle.

## Tasks

Each shape needs:
- SVG element generation given (x, y, width, height)
- Text anchor point calculation (where to place the label)
- Edge connection point calculation (where edges attach)

### Shapes

- [ ] **Rectangle** (`A[text]`): `<rect x y width height>`
- [ ] **Rounded Rectangle** (`A("text")`): `<rect rx="5" ...>`
- [ ] **Stadium** (`A(["text"])`): `<rect rx="height/2" ...>` (fully rounded ends)
- [ ] **Subroutine** (`A[["text"]]`): `<rect>` with double vertical borders (inner lines at ~8px from edges)
- [ ] **Cylinder** (`A[("text")]`): `<path>` with elliptical arcs top and bottom
- [ ] **Circle** (`A(("text"))`): `<circle cx cy r>`
- [ ] **Asymmetric** (`A)text(`): `<polygon>` with flag/banner shape
- [ ] **Diamond** (`A{"text"}`): `<polygon>` rotated square
- [ ] **Hexagon** (`A{{"text"}}`): `<polygon>` six-pointed
- [ ] **Parallelogram** (`A[/"text"/]`): `<polygon>` skewed rectangle
- [ ] **Parallelogram Alt** (`A[\"text"\]`): `<polygon>` skewed other direction
- [ ] **Trapezoid** (`A[/"text"\]`): `<polygon>` wider at bottom
- [ ] **Trapezoid Alt** (`A[\"text"/]`): `<polygon>` wider at top
- [ ] **Double Circle** (`A((("text")))`): Two concentric `<circle>` elements

### Architecture
- [ ] `ShapeRenderer` protocol/base class with methods:
  - `render(x, y, w, h, label, style) -> list[SVGElement]`
  - `connection_point(x, y, w, h, angle) -> (px, py)` - where an edge from a given angle connects
- [ ] Registry mapping `NodeShape` enum to renderer
- [ ] Each shape as a function or small class

### Edge Connection Points
For each shape, calculate where an edge entering from angle theta connects:
- Rectangle: intersect ray with rectangle boundary
- Circle: point on circumference
- Diamond: intersect ray with diamond boundary
- etc.

## Acceptance Criteria
- All 14 shapes render correctly
- Visual comparison with mermaid-cli output shows same shapes
- Edge connection points are on shape boundaries (not centers)

## Dependencies
- Task 03 (NodeShape enum)
- Task 07 (SVG renderer core)

## Estimated Complexity
Medium - repetitive but each shape has unique geometry. ~300-400 lines.
