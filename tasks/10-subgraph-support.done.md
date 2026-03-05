# 10 - Subgraph Support

## Goal
Support subgraph parsing, layout, and rendering. Subgraphs group nodes visually with a labeled bounding box. The parser already handles subgraph syntax (task 04). This task focuses on making layout subgraph-aware and improving the renderer for nested subgraphs.

## Current State

The following already exists and must be preserved:

- **Parser** (`src/pymermaid/parser/flowchart.py`): Fully parses `subgraph id[Title] ... end`, tracks node membership via `_SubgraphBuilder`, supports nesting, handles `direction` overrides inside subgraphs.
- **IR** (`src/pymermaid/ir/__init__.py`): `Subgraph` dataclass with `id`, `title`, `direction`, `node_ids`, and recursive `subgraphs`.
- **Renderer** (`src/pymermaid/render/__init__.py`): Has `_compute_subgraph_bbox` and `_render_subgraph` but only iterates top-level subgraphs (no recursion), and bounding box does not account for child subgraphs.
- **Layout** (`src/pymermaid/layout/__init__.py`): No subgraph awareness at all. Nodes are positioned purely by graph topology.

## Tasks

### Layout Integration
- [ ] Add `SubgraphLayout` dataclass to layout output (bbox: x, y, width, height per subgraph id)
- [ ] Constrain nodes within the same subgraph to be grouped together during coordinate assignment (step 4 of Sugiyama). Nodes in a subgraph should be assigned to contiguous positions within each layer.
- [ ] After node positioning, compute subgraph bounding boxes with configurable padding (default: 20px)
- [ ] For nested subgraphs, compute bounding box recursively (parent includes children)
- [ ] Support `direction` override within subgraphs: if a subgraph specifies `direction LR`, lay out its internal nodes left-to-right regardless of the diagram's top-level direction
- [ ] Include `subgraphs: dict[str, SubgraphLayout]` in `LayoutResult`

### Rendering Improvements
- [ ] Render subgraphs recursively (handle nested subgraphs, not just top-level)
- [ ] Render subgraph as: background `<rect>` with `rx="5"` (rounded corners), light fill, solid border
- [ ] Render title `<text>` at top-left of bounding box
- [ ] Render in correct z-order: outermost subgraph bg first, then inner subgraph bg, then edges, then nodes
- [ ] Use `SubgraphLayout` from layout result instead of recomputing bbox in the renderer (eliminate `_compute_subgraph_bbox` or delegate to layout)

### Parser Verification
- [ ] Verify parser correctly nests subgraphs in IR (should already work -- confirm with tests)
- [ ] Verify edges that cross subgraph boundaries are parsed correctly
- [ ] Verify a subgraph id can be used as an edge endpoint (e.g., `A --> sgId`)

## Acceptance Criteria

- [ ] `LayoutResult` has a `subgraphs` attribute mapping subgraph id to a `SubgraphLayout` with `x`, `y`, `width`, `height`
- [ ] `from pymermaid.layout import SubgraphLayout` works
- [ ] Nodes belonging to the same subgraph are positioned closer together than nodes outside the subgraph (grouping constraint)
- [ ] Nested subgraphs: inner subgraph bounding box is fully contained within outer subgraph bounding box
- [ ] Subgraph `direction` override works: a subgraph with `direction LR` inside a `TD` diagram lays out its nodes left-to-right
- [ ] SVG output contains `<g class="subgraph">` elements for each subgraph, including nested ones
- [ ] Each subgraph `<g>` contains a `<rect>` (background) and a `<text>` (title)
- [ ] Z-order in SVG: subgraph `<g>` elements appear before edge and node `<g>` elements
- [ ] For nested subgraphs, outer subgraph `<g>` appears before inner subgraph `<g>` in SVG source
- [ ] Edges crossing subgraph boundaries still render with correct routing (no visual clipping)
- [ ] `uv run pytest tests/test_subgraph.py` passes with 15+ tests
- [ ] Existing tests continue to pass: `uv run pytest tests/ -x` (no regressions)

## Test Scenarios

### Unit: Parser subgraph handling (verify existing behavior)
- Parse `subgraph sg1[Title]\n  A --> B\nend` -- verify `diagram.subgraphs` has one entry with `id="sg1"`, `title="Title"`, `node_ids=("A", "B")`
- Parse nested subgraphs -- verify `subgraphs[0].subgraphs` is populated
- Parse subgraph with `direction LR` -- verify `subgraph.direction == Direction.LR`
- Parse edge from node to subgraph id (e.g., `C --> sg1`) -- verify edge exists with `target="sg1"`
- Unclosed subgraph raises `ParseError`

### Unit: Layout subgraph grouping
- Layout a diagram with one subgraph containing 2 nodes and one node outside -- verify the 2 grouped nodes are adjacent (no outside node between them in the same layer)
- Layout a diagram with nested subgraphs -- verify inner bbox is within outer bbox
- Layout with subgraph `direction LR` inside a `TD` diagram -- verify the subgraph's nodes are arranged horizontally
- `SubgraphLayout` has correct `x`, `y`, `width`, `height` values that encompass all member nodes plus padding

### Unit: Layout SubgraphLayout output
- `LayoutResult.subgraphs` is a dict mapping subgraph id to `SubgraphLayout`
- For an empty subgraph (no nodes), either omit from dict or provide a zero-size layout
- Bounding box includes padding (default 20px on each side)

### Unit: Renderer subgraph SVG output
- Render a diagram with one subgraph -- SVG contains `<g class="subgraph" data-subgraph-id="sg1">`
- The subgraph `<g>` contains a `<rect>` and a `<text>` child
- The `<text>` element contains the subgraph title
- Render nested subgraphs -- SVG contains `<g class="subgraph">` for both outer and inner
- Z-order: subgraph `<g>` appears before node `<g>` elements in the SVG tree

### Integration: End-to-end subgraph rendering
- Parse, layout, and render a flowchart with subgraphs -- verify SVG is valid XML
- Parse, layout, and render nested subgraphs -- verify all subgraph rects and titles present
- Parse, layout, and render a subgraph with cross-boundary edges -- verify edge paths exist

## Dependencies
- Task 04 (parser) -- DONE
- Task 06 (layout) -- DONE
- Task 07 (renderer) -- DONE

## Estimated Complexity
Medium - layout grouping constraint is the hardest part. Parser already works. Renderer needs recursion and z-order fix.
