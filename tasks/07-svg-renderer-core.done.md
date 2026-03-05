# 07 - SVG Renderer Core

## Goal
Generate SVG XML output from positioned layout results. This is the final stage of the pipeline: given a `Diagram` (IR) and a `LayoutResult` (positioned nodes and routed edges), produce a standalone SVG string.

## Scope

This task covers the SVG document structure, node positioning/text rendering, edge path rendering, and subgraph rendering. It does NOT cover:
- Individual node shape SVG elements (Task 08 -- use `<rect>` as fallback for all shapes here)
- Edge type variations and arrow marker details (Task 09 -- use a single default arrow marker here)
- Advanced styling/classDef application (Task 11 -- only apply basic default theme colors here)

## Tasks

### SVG Document Structure
- [ ] `render_svg(diagram: Diagram, layout: LayoutResult) -> str` function in `src/pymermaid/render/__init__.py`
- [ ] Generate SVG root element with `xmlns="http://www.w3.org/2000/svg"`, computed `viewBox`, `width`, `height`
- [ ] Generate `<defs>` section with a single default arrowhead marker (`<marker>` with a triangle `<path>`)
- [ ] Generate `<style>` element with default theme:
  - Node fill: `#f9f9f9`, stroke: `#333`, stroke-width: `1`
  - Text: fill `#333`, `font-family: sans-serif`, `font-size: 14px`
  - Edge stroke: `#333`
  - Background: transparent (no background rect unless explicitly needed)

### Node Rendering
- [ ] For each node in `layout.nodes`, render a `<g>` group containing:
  - A `<rect>` positioned at `(node.x, node.y)` with `node.width` and `node.height` (shape details deferred to Task 08)
  - A `<text>` element centered inside the rect
- [ ] Multi-line labels: split on `<br/>` and use `<tspan>` elements with `dy` offsets
- [ ] Set `data-node-id` attribute on the `<g>` for testability

### Edge Rendering
- [ ] For each edge in `layout.edges`, render a `<path>` element using the polyline points
  - Use SVG path `M x,y L x,y L x,y ...` for the polyline
  - Apply `marker-end` referencing the default arrowhead
- [ ] If the corresponding IR edge has a label, render a `<text>` element positioned at the midpoint of the path
- [ ] Set `data-edge-source` and `data-edge-target` attributes for testability

### Subgraph Rendering
- [ ] For each subgraph in `diagram.subgraphs`, render:
  - A `<rect>` background with rounded corners (`rx="5"`) encompassing member nodes (compute bounding box from layout)
  - A `<text>` element for the subgraph title positioned at the top of the bounding box
- [ ] Set `data-subgraph-id` attribute for testability

### SVG Output Quality
- [ ] Output is well-formed XML (parseable by `xml.etree.ElementTree`)
- [ ] Use `xml.etree.ElementTree` for generation (not string concatenation)
- [ ] Pretty-print with indentation (use `xml.etree.ElementTree.indent` or equivalent)
- [ ] Output is a standalone SVG (embeddable in HTML, includes xmlns)
- [ ] Add a small padding/margin (e.g. 20px) around the viewBox so nodes are not clipped at edges

## Acceptance Criteria

- [ ] `from pymermaid.render import render_svg` works
- [ ] `render_svg(diagram, layout)` returns a `str` containing valid SVG XML
- [ ] The returned string starts with `<svg` and contains `xmlns="http://www.w3.org/2000/svg"`
- [ ] The SVG contains one `<rect>` per node and one `<path>` per edge (at minimum)
- [ ] Each node group has a `<text>` element with the node's label text
- [ ] Multi-line labels (containing `<br/>`) produce multiple `<tspan>` elements
- [ ] Edge labels appear as `<text>` elements near the edge midpoint
- [ ] The SVG can be parsed by `xml.etree.ElementTree.fromstring()` without errors
- [ ] Subgraph bounding boxes are rendered as rounded `<rect>` elements with title text
- [ ] The viewBox dimensions include padding so content is not clipped
- [ ] A `<defs>` section exists containing at least one `<marker>` for arrowheads
- [ ] Default theme colors are applied (node fill `#f9f9f9`, stroke `#333`, text `#333`)
- [ ] `uv run pytest tests/test_render.py` passes with 15+ tests

## Test Scenarios

### Unit: render_svg returns valid SVG
- Call `render_svg` with a simple 2-node, 1-edge diagram and layout; assert return type is `str`
- Parse the result with `xml.etree.ElementTree.fromstring()`; assert no exception
- Assert root tag is `svg` (or `{http://www.w3.org/2000/svg}svg`)
- Assert `xmlns` attribute equals `http://www.w3.org/2000/svg`

### Unit: SVG contains nodes
- Create a diagram with 3 nodes (A, B, C) and corresponding layout
- Parse SVG output; find all elements with `data-node-id` attribute
- Assert there are exactly 3 node groups
- Assert each group contains a `<rect>` and a `<text>`

### Unit: Node text labels
- Create a node with label `"Hello World"`
- Render and parse; find the text element inside that node's group
- Assert text content is `"Hello World"`

### Unit: Multi-line labels with br
- Create a node with label `"Line1<br/>Line2<br/>Line3"`
- Render and parse; find `<tspan>` elements inside that node's text
- Assert there are 3 `<tspan>` elements with correct text

### Unit: SVG contains edges
- Create a diagram with 2 nodes and 1 edge (A-->B)
- Parse SVG output; find `<path>` elements with `data-edge-source="A"` and `data-edge-target="B"`
- Assert exactly 1 such path exists
- Assert the path has a `d` attribute starting with `M`

### Unit: Edge labels
- Create an edge with label `"yes"`
- Render and parse; find a `<text>` element containing `"yes"` near the edge
- Assert it exists

### Unit: Arrowhead marker in defs
- Render any diagram; parse SVG
- Find `<defs>` section; assert it contains a `<marker>` element
- Assert the marker has `id`, `markerWidth`, `markerHeight` attributes

### Unit: Default theme colors
- Render a diagram; parse SVG
- Find the `<style>` element; assert it contains `#f9f9f9` (node fill) and `#333` (text/stroke)

### Unit: ViewBox includes padding
- Create a diagram where layout width=200, height=100
- Render SVG; check the `viewBox` attribute
- Assert viewBox is larger than `0 0 200 100` (padding added)

### Unit: Subgraph rendering
- Create a diagram with a subgraph containing 2 nodes
- Render and parse; find element with `data-subgraph-id`
- Assert it contains a `<rect>` (background) and `<text>` (title)

### Unit: Empty diagram
- Create a diagram with no nodes and no edges; empty layout
- `render_svg` should return valid SVG with no node/edge elements (just the shell)

### Unit: Single node, no edges
- Create a diagram with 1 node and 0 edges
- Render; assert valid SVG with exactly 1 node group and 0 edge paths

### Integration: Round-trip with layout_diagram
- Create a `Diagram` with 3 nodes and 2 edges
- Run `layout_diagram` to get a `LayoutResult`
- Pass both to `render_svg`
- Parse and validate the output is well-formed SVG with correct node/edge counts

### Integration: Diagram with subgraphs
- Create a `Diagram` with a subgraph, run layout, render
- Verify subgraph rect and title appear in output

## Dependencies
- Task 03 (IR data model) -- **done**
- Task 06 (Sugiyama layout) -- **done**

## Estimated Complexity
Medium -- straightforward XML generation using `xml.etree.ElementTree`. The main work is wiring up the IR and layout data into SVG elements with correct positioning and attributes.
