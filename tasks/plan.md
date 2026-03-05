# PyMermaid - Python Native Mermaid SVG Renderer

## Vision

A pure Python library that renders Mermaid diagram syntax directly to SVG without requiring a browser, Node.js, Puppeteer, or any external service. This eliminates the ~300MB headless browser dependency and achieves orders-of-magnitude faster rendering.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Parser     │───>│  IR (Graph)  │───>│   Layout     │───>│ SVG Renderer │
│ .mmd -> AST  │    │ Nodes/Edges  │    │ Positions    │    │ XML output   │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                             │
                                       ┌─────┴─────┐
                                       │   Text     │
                                       │ Measurement│
                                       └───────────┘
```

### Pipeline

1. **Parse** - Mermaid syntax -> intermediate representation (nodes, edges, labels, styles)
2. **Measure** - Calculate text dimensions using font metrics or heuristic widths
3. **Layout** - Position nodes and route edges using layered graph layout (Sugiyama)
4. **Render** - Generate SVG XML from positioned elements

## Comparison Testing Strategy

We use mermaid-cli (`mmdc` via Puppeteer) as the reference renderer:

1. Collect test fixtures from `mermaid-cli/test-positive/` (28 files)
2. Render each fixture with both `mmdc` and `pymermaid`
3. Compare outputs:
   - Structural comparison: same nodes, edges, labels present in SVG
   - Visual comparison: overlay PNGs and compute pixel difference
   - Bounding box comparison: node sizes within tolerance (text measurement variance)
4. Acceptance criteria: visually equivalent output for supported diagram types

## Scope & Phasing

### Phase 1: Flowcharts (MVP)
The most common diagram type and the most complex syntax. Covers ~60% of real-world usage.

### Phase 2: Sequence Diagrams
Second most popular. Different layout algorithm (timeline-based, not graph-based).

### Phase 3: Class & State Diagrams
Similar graph-based layout to flowcharts, with specialized node rendering.

### Phase 4: Remaining Diagram Types
ER, Gantt, Pie, Mindmap, Git Graph, etc. Each is relatively self-contained.

---

## Phase 1 Detailed Feature Analysis: Flowcharts

### Directions
- `TB` / `TD` - Top to Bottom (default)
- `BT` - Bottom to Top
- `LR` - Left to Right
- `RL` - Right to Left

### Node Shapes (Classic Syntax)
| Syntax | Shape | SVG Element |
|--------|-------|-------------|
| `A["text"]` or `A[text]` | Rectangle | `<rect>` |
| `A("text")` | Rounded rectangle | `<rect rx="...">` |
| `A(["text"])` | Stadium | `<rect rx="height/2">` |
| `A[["text"]]` | Subroutine | `<rect>` + double border |
| `A[("text")]` | Cylinder | `<path>` (elliptical top/bottom) |
| `A(("text"))` | Circle | `<circle>` |
| `A)text(` | Asymmetric | `<polygon>` |
| `A{"text"}` | Diamond/Rhombus | `<polygon>` |
| `A{{"text"}}` | Hexagon | `<polygon>` |
| `A[/"text"/]` | Parallelogram | `<polygon>` |
| `A[\"text"\]` | Parallelogram alt | `<polygon>` |
| `A[/"text"\]` | Trapezoid | `<polygon>` |
| `A[\"text"/]` | Trapezoid alt | `<polygon>` |
| `A((("text")))` | Double circle | `<circle>` x2 |

### Edge Types
| Syntax | Description |
|--------|-------------|
| `A --> B` | Arrow |
| `A --- B` | Open link |
| `A -->│text│ B` | Arrow with label |
| `A -- text --> B` | Arrow with label (alt) |
| `A -.-> B` | Dotted arrow |
| `A -. text .-> B` | Dotted with label |
| `A ==> B` | Thick arrow |
| `A == text ==> B` | Thick with label |
| `A ~~~ B` | Invisible link |
| `A --o B` | Circle endpoint |
| `A --x B` | Cross endpoint |
| Extra dashes for length | `A ----> B` |

### Subgraphs
```
subgraph id[Title]
    direction LR
    A --> B
end
```
- Nested subgraphs supported
- Edges between subgraphs
- Direction override per subgraph

### Styling
- Inline: `style nodeId fill:#f9f,stroke:#333`
- Class definition: `classDef className fill:#f9f`
- Class assignment: `nodeId:::className` or `class nodeId className`
- Default class: `classDef default fill:#f9f`

### Other Features
- Comments: `%% comment`
- Markdown in labels (bold, italic)
- Unicode text and entity codes (`#35;`)
- Line breaks in labels (`<br/>`)
- Click interactions (parsed but not rendered in SVG)

---

## Text Measurement Strategy

Two modes (following mermaid-rs-renderer's proven approach):

1. **Font-based mode** (default): Use `fonttools` to parse TTF/OTF font files, extract glyph advance widths, cache them. Provides accurate measurements.

2. **Heuristic mode** (fast, zero font dependencies): Use calibrated ratio of `font_size * 0.6` per character width. Good enough for most diagrams.

Height estimation: `font_size * 1.2` (standard line-height).

---

## Layout Algorithm: Sugiyama (Layered Graph Drawing)

For flowcharts, implement the classic Sugiyama algorithm:

1. **Cycle removal** - Break cycles with edge reversal
2. **Layer assignment** - Assign each node to a layer (rank)
3. **Crossing minimization** - Reorder nodes within layers to minimize edge crossings
4. **Coordinate assignment** - Assign x,y positions respecting spacing constraints
5. **Edge routing** - Route edges between positioned nodes (orthogonal or polyline)

---

## Dependencies

### Required
- Python 3.10+ (modern typing, match statements)
- No required external dependencies for core rendering

### Optional
- `fonttools` - accurate text measurement from TTF/OTF fonts
- `Pillow` - PNG output (rasterize SVG)
- `cairosvg` - alternative PNG output

### Development
- `pytest` - testing
- `Node.js` + `@mermaid-js/mermaid-cli` - reference rendering for comparison tests

---

## Task Breakdown Summary

1. Project setup (packaging, CI, dev environment)
2. Comparison test infrastructure (mmdc reference) -- early, so we validate from the start
3. Intermediate representation (IR) data model
4. Flowchart parser
5. Text measurement engine
6. Sugiyama layout algorithm
7. SVG renderer core
8. Node shape renderers (all 14 classic shapes)
9. Edge renderers (all edge types, arrow markers)
10. Subgraph support
11. Styling support (classDef, inline styles)
12. CLI interface
13. Integration tests with mermaid-cli fixtures
14. Sequence diagram support (Phase 2)
15. Class diagram support (Phase 3)
16. State diagram support (Phase 3)
