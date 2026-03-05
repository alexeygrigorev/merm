# 09 - Edge Renderers

## Goal
Implement SVG rendering for all edge types, arrow markers, and edge labels.

## Tasks

### Arrow Markers (SVG `<marker>` in `<defs>`)
- [ ] Triangle arrow (default `-->`)
- [ ] Circle endpoint (`--o`)
- [ ] Cross endpoint (`--x`)
- [ ] Reverse triangle (for `<--` source arrow)
- [ ] Configure marker size, fill color, refX/refY

### Edge Line Styles
- [ ] Solid line (`-->`, `---`): `stroke-dasharray: none`
- [ ] Dotted line (`-.->`, `-.-`): `stroke-dasharray: 3`
- [ ] Thick line (`==>`, `===`): `stroke-width: 3.5` (vs default 2)
- [ ] Invisible (`~~~`): `stroke: none` or `visibility: hidden`

### Edge Path Generation
- [ ] Generate `<path d="M... L... C...">` from layout point list
- [ ] Straight segments for simple edges
- [ ] Smooth curves using cubic Bezier (`C`) for multi-segment edges
- [ ] Apply `marker-start` and `marker-end` attributes for arrows

### Edge Labels
- [ ] Position label at midpoint of edge path
- [ ] Render as `<text>` with background `<rect>` (white fill to cover edge line)
- [ ] Handle multi-line edge labels

### Extra Length
- [ ] Edges with extra dashes (`---->`) get additional minimum length in layout
- [ ] Map extra dash count to layout constraint (each extra dash = +1 rank span)

## Acceptance Criteria
- All edge types render with correct line style and arrows
- Labels are legible and properly positioned
- Markers scale correctly with edge stroke width

## Dependencies
- Task 07 (SVG renderer core)
- Task 06 (edge paths from layout)

## Estimated Complexity
Medium - ~200-300 lines.
