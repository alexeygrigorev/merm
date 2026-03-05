# 11 - Styling Support + Shape Integration

## Goal

1. Wire the SHAPE_REGISTRY (from task 08, `render/shapes.py`) into the core SVG renderer so that each node renders with its correct shape instead of always using `<rect>`.
2. Implement CSS-like styling for nodes and edges: inline styles, classDef class definitions, and the default theme.

## Scope

### Part A: Shape Integration

Currently `_render_node()` in `render/__init__.py` always emits a `<rect>`. The `SHAPE_REGISTRY` in `render/shapes.py` has renderers for all 14 node shapes but is never called. This task must:

- Look up each node's `shape` field (from `ir.Node.shape`) in `SHAPE_REGISTRY`
- Call the shape renderer's `.render()` method to produce the correct SVG elements (polygon, circle, path, etc.) instead of a hard-coded `<rect>`
- Ensure the `.node rect` CSS selector in `_DEFAULT_STYLE` is broadened or supplemented so non-rect shapes also receive default fill/stroke (e.g. `.node polygon`, `.node circle`, `.node path`, `.node line`)

### Part B: Style Application

- Apply `style nodeId fill:#f9f,stroke:#333,stroke-width:4px` -- set inline `style` attribute on the node's shape SVG element(s)
- Apply `classDef className fill:#f9f,stroke:#333` -- emit a `<style>` block with `.className { ... }` rules, and set the `class` attribute on matching node `<g>` elements
- Support `classDef default` -- properties applied to all nodes that have no other class
- Handle `:::className` inline syntax (already parsed by parser into `Node.css_classes`)
- Support multiple classes on a single node (space-separated class attribute)

### Part C: Default Theme

- Implement the default mermaid theme with cycling node fills: `#f9f9f9`, `#ffe0b2`, `#c8e6c9`, `#bbdefb`, `#f8bbd0`, `#d1c4e9`
- Node stroke: `#333`, text color: `#333`, edge color: `#333`
- Subgraph fill: `#eee` with `#bbb` stroke

### CSS Properties Mapping

Map mermaid style properties to SVG attributes:
- `fill` -> `fill`
- `stroke` -> `stroke`
- `stroke-width` -> `stroke-width`
- `color` -> text `fill`
- `font-size` -> `font-size`
- `stroke-dasharray` -> `stroke-dasharray`

## Acceptance Criteria

- [ ] `_render_node()` uses `SHAPE_REGISTRY` / `get_shape_renderer()` to render the correct SVG element for each `NodeShape`
- [ ] A node with `shape=NodeShape.diamond` produces a `<polygon>` (not `<rect>`) in the final SVG
- [ ] A node with `shape=NodeShape.circle` produces a `<circle>` in the final SVG
- [ ] A node with `shape=NodeShape.stadium` produces a `<rect>` with `rx` equal to half the height
- [ ] The default `<style>` block covers `.node polygon`, `.node circle`, `.node path`, `.node line` in addition to `.node rect`
- [ ] `style nodeId fill:#f9f,stroke:#333` results in an inline `style="fill:#f9f;stroke:#333"` attribute on the shape element(s) of that node
- [ ] `classDef foo fill:#f9f,stroke:#333` produces a `.foo { fill:#f9f;stroke:#333; }` rule in the `<style>` block
- [ ] Nodes with `css_classes=("foo",)` have `class="node foo"` on their `<g>` element
- [ ] `classDef default fill:#aaa` applies to nodes that have no explicit class
- [ ] Multiple classes on a node (`css_classes=("foo", "bar")`) produce `class="node foo bar"`
- [ ] `uv run pytest tests/test_styling.py` passes with 15+ tests
- [ ] All existing tests in `tests/test_render.py`, `tests/test_shapes.py`, `tests/test_integration.py` still pass

## Test Scenarios

### Unit: Shape integration in renderer
- Render a diagram with a single diamond node; assert SVG contains `<polygon>` and no `<rect>` inside that node's `<g>`
- Render a diagram with a circle node; assert SVG contains `<circle>`
- Render a diagram with a stadium node; assert `<rect>` has `rx` attribute
- Render a diagram with a cylinder node; assert SVG contains `<path>`
- Render a diagram with a subroutine node; assert SVG contains `<line>` elements
- Render a diagram with a double_circle node; assert two `<circle>` elements
- Render a diagram with mixed shapes (rect + diamond + circle); verify each node has the correct SVG element

### Unit: Default style block
- Parse the emitted `<style>` text; confirm it includes selectors for `.node rect`, `.node polygon`, `.node circle`, `.node path`

### Unit: Inline style application
- Create a Diagram with `styles=(StyleDef("A", {"fill": "#f9f", "stroke": "#333"}),)` and render; assert the `<g data-node-id="A">` child shape element has `style="fill:#f9f;stroke:#333"`
- Verify inline styles only apply to the target node, not others

### Unit: classDef application
- Create a Diagram with `classes={"highlight": {"fill": "#ff0", "stroke": "#000"}}` and a node with `css_classes=("highlight",)`; verify the `<style>` block contains `.highlight { fill:#ff0;stroke:#000; }` and the node `<g>` has `class="node highlight"`
- Test `classDef default` -- create a Diagram with `classes={"default": {"fill": "#aaa"}}` and nodes without classes; verify default class is applied

### Unit: Multiple classes
- Node with `css_classes=("foo", "bar")` produces `class="node foo bar"` on the `<g>`

### Integration: Round-trip parse-to-SVG
- Parse `graph LR; A{Decision} --> B((Circle))` and render; verify the SVG contains a `<polygon>` for A and a `<circle>` for B
- Parse `graph TD; A-->B; style A fill:#f00` and render; verify A has inline style
- Parse `graph TD; A-->B; classDef red fill:#f00; class A red` and render; verify class in style block and on node

## Dependencies

- Task 04 (parser) -- done
- Task 07 (SVG renderer core) -- done
- Task 08 (node shape renderers) -- done

## Estimated Complexity

Medium -- shape integration is straightforward plumbing, style application requires modifying the renderer to read IR style/class data and emit the right attributes.
