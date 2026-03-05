# Task 48: Mindmap Support

## Goal

Add parser, IR, layout, and renderer for Mermaid mindmap diagrams. Follow the established pattern used by pie, ER, class, sequence, and state diagrams: dedicated IR dataclass, parser module, layout module, renderer module, and dispatch entry in `__init__.py`.

## Mermaid Mindmap Syntax Reference

Mindmaps use indentation-based hierarchy. Each level of indentation (2 spaces) represents a deeper level in the tree.

### Basic syntax

```
mindmap
  root((Central Topic))
    Topic A
      Sub A1
      Sub A2
    Topic B
      Sub B1
```

### Node shapes

| Syntax | Shape | Description |
|--------|-------|-------------|
| `id((text))` | Circle | Double-parens |
| `id(text)` | Rounded rectangle | Single-parens |
| `id[text]` | Square/rectangle | Brackets |
| `id))text((` | Cloud/bang | Reversed double-parens |
| `id)text(` | Cloud (mermaid docs vary) | Reversed parens |
| `id` or just `text` | Default rectangle | No delimiters |

The root node is the first node at the topmost indentation level (directly after `mindmap`). All subsequent indented lines are children, determined by relative indentation depth.

### Comments

Lines starting with `%%` are comments and should be ignored.

## Implementation Plan

### 1. IR (src/pymermaid/ir/mindmap.py)

Frozen dataclasses following the pattern of `ir/pie.py`:

- `MindmapNode`: `id: str`, `label: str`, `shape: MindmapShape`, `children: tuple[MindmapNode, ...]`
- `MindmapShape` enum: `CIRCLE`, `ROUNDED_RECT`, `RECT`, `CLOUD`, `DEFAULT`
- `MindmapDiagram`: `root: MindmapNode`

The tree is represented recursively (root has children, each child has children, etc). This is the natural IR for indentation-based mindmap syntax.

### 2. Parser (src/pymermaid/parser/mindmap.py)

- Strip `%%` comments
- Find the `mindmap` keyword line
- Parse remaining lines using indentation to determine parent-child nesting
- Detect node shape from delimiter syntax: `((text))`, `(text)`, `[text]`, `))text((`, bare text
- Build tree by tracking an indentation stack (list of `(indent_level, node)` pairs)
- Raise `ParseError` on: empty input, missing `mindmap` keyword, no root node, inconsistent indentation jumps (child indented more than one level deeper than nearest ancestor)

### 3. Layout (src/pymermaid/layout/mindmap.py)

Radial tree layout algorithm:

- Root node placed at the center of the SVG canvas
- First-level children distributed evenly around the root in a circle (angular sector per child proportional to subtree weight)
- Deeper children extend outward along their parent's angular sector
- Each level is placed at an increasing radius from center
- Node positions stored as `(x, y)` in a layout result dict keyed by node id
- Use `TextMeasurer.measure()` for text sizing to determine node dimensions

### 4. Renderer (src/pymermaid/render/mindmap.py)

- Render nodes according to their shape (circle -> `<circle>`, rounded rect -> `<rect rx="...">`, etc.)
- Render branch connections as curved lines (`<path>` with quadratic or cubic bezier curves) from parent center to child center
- Each top-level subtree gets a distinct color from a palette (similar to `PIE_COLORS` in pie renderer)
- Node text rendered with `<text>` elements, centered in the node shape
- SVG viewBox computed to fit all nodes with padding
- CSS classes: `.mindmap-node`, `.mindmap-branch`, `.mindmap-label`
- Each branch `<path>` and node should include `data-node-id` attributes for testability

### 5. Dispatch (src/pymermaid/__init__.py)

Add a new `if re.match(r"^\s*mindmap", source, re.MULTILINE)` block in `render_diagram()`, following the existing pattern. Import and call `parse_mindmap`, `layout_mindmap`, `render_mindmap_svg`.

## Dependencies

- None. This task has no prerequisite tasks that must be `.done.md` first.
- Uses existing infrastructure: `ParseError` from `pymermaid.parser.flowchart`, `TextMeasurer` from `pymermaid.measure`, `Theme` from `pymermaid.theme`.

## Acceptance Criteria

- [ ] `from pymermaid.ir.mindmap import MindmapNode, MindmapDiagram, MindmapShape` works
- [ ] `from pymermaid.parser.mindmap import parse_mindmap` works
- [ ] `from pymermaid.layout.mindmap import layout_mindmap` works
- [ ] `from pymermaid.render.mindmap import render_mindmap_svg` works
- [ ] `render_diagram(mindmap_source)` auto-detects and returns valid SVG (contains `<svg` and `</svg>`)
- [ ] Parser correctly builds a tree where indentation levels determine parent-child relationships
- [ ] Parser detects node shapes: `((text))` -> circle, `(text)` -> rounded rect, `[text]` -> rect, `))text((` -> cloud, bare text -> default
- [ ] Parser raises `ParseError` on empty input, missing `mindmap` keyword, or no root node
- [ ] Root node renders at or near the center of the SVG canvas
- [ ] First-level children are distributed radially around the root (not overlapping each other)
- [ ] Branch connections are rendered as curved `<path>` elements (not straight lines)
- [ ] Each top-level subtree uses a distinct color for its branch and nodes
- [ ] Node text is present in the SVG and does not overlap with other text (verified by bounding box checks or visual inspection)
- [ ] At least 3 corpus fixtures exist in `tests/fixtures/corpus/mindmap/` as `.mmd` files
- [ ] PNG verification: render each fixture to SVG and visually confirm hierarchy, layout, and readability
- [ ] `uv run pytest` passes with no regressions across the entire test suite

## Test Scenarios

### Unit: IR construction (tests/test_mindmap.py)

- Create a `MindmapNode` with all fields, verify attributes
- Create a `MindmapDiagram` with a root that has nested children, verify tree structure
- Verify `MindmapShape` enum has all expected members

### Unit: Parser (tests/test_mindmap.py)

- Parse the basic example from the Mermaid docs (root with 3 branches, sub-branches); verify tree depth and child counts
- Parse a mindmap with a single root node and no children; verify root is returned with empty children
- Parse node shapes: input with `((Circle))`, `(Rounded)`, `[Square]`, `))Cloud((`, and bare text; verify each node gets the correct `MindmapShape`
- Verify `%%` comment lines are stripped and do not appear as nodes
- Verify `ParseError` is raised for empty input
- Verify `ParseError` is raised for input missing the `mindmap` keyword
- Verify `ParseError` is raised for input with `mindmap` but no node lines

### Unit: Layout (tests/test_mindmap.py)

- Layout a single-root mindmap; root position is at the center
- Layout a root with 4 children; verify all children are at approximately equal distance from root and do not overlap each other
- Layout a 3-level deep tree; verify each level is at increasing radius from center

### Unit: Renderer (tests/test_mindmap.py)

- Render a basic mindmap; output is valid SVG (starts with `<svg`, ends with `</svg>`)
- Render a mindmap; verify all node labels appear as `<text>` elements in the SVG
- Render a mindmap with 3 top-level branches; verify at least 3 distinct fill colors appear in the SVG
- Render a mindmap; verify `<path>` elements exist for branch connections
- Render a mindmap with circle root shape; verify `<circle>` element is present in SVG

### Integration: dispatch (tests/test_mindmap.py)

- Call `render_diagram()` with mindmap source text; verify SVG is returned without error
- Call `render_diagram()` with mindmap source; verify the output contains expected node labels

### Corpus fixtures (tests/fixtures/corpus/mindmap/)

#### Fixture 1: basic.mmd
```
mindmap
  root((Central Topic))
    Origins
      Long history
      Popularized by Tony Buzan
    Research
      On effectiveness
      On features
    Tools
      Pen and paper
      Mermaid
```

#### Fixture 2: shapes.mmd
```
mindmap
  root((Shapes Demo))
    (Rounded Node)
    [Square Node]
    ))Cloud Node((
    Default Node
```

#### Fixture 3: deep_tree.mmd
```
mindmap
  root((Project Plan))
    Phase 1
      Design
        Wireframes
        Mockups
      Review
    Phase 2
      Implementation
        Frontend
        Backend
        Database
      Testing
        Unit Tests
        Integration Tests
    Phase 3
      Deployment
      Monitoring
```

#### Fixture 4: single_root.mmd
```
mindmap
  root((Solo Node))
```

## Notes for the Engineer

- Follow the file organization pattern of the pie chart implementation: separate `ir/mindmap.py`, `parser/mindmap.py`, `layout/mindmap.py`, `render/mindmap.py`.
- The radial layout does not need to be pixel-perfect vs. mermaid.js. The goal is a readable, non-overlapping radial tree.
- For branch colors, define a `MINDMAP_COLORS` palette similar to `PIE_COLORS` in `render/pie.py`.
- Use `xml.sax.saxutils.escape` for text content in SVG, as done in the pie renderer.
- Register `__all__` exports in each new module.
