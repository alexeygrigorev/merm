# 04 - Flowchart Parser

## Goal
Parse Mermaid flowchart syntax into the IR data model. This is the most complex parser since flowcharts have the richest syntax.

## Dependencies

- **Task 03 (IR data model)** must be `.done.md` first -- the parser produces `Diagram`, `Node`, `Edge`, `Subgraph`, and `StyleDef` instances, and uses `NodeShape`, `EdgeType`, `ArrowType`, `Direction`, and `DiagramType` enums.

## Scope

The parser module lives at `src/pymermaid/parser/flowchart.py` (or a sub-package under `src/pymermaid/parser/`). It exposes a top-level function such as `parse_flowchart(text: str) -> Diagram` that is importable from `pymermaid.parser`.

### In scope
- Diagram declaration parsing (`graph TD`, `graph LR`, `flowchart TB`, etc.)
- All 14 classic node shapes
- All edge types (arrow, open, dotted, thick, invisible, circle-end, cross-end, bidirectional, extra-length)
- Edge labels (pipe syntax and inline syntax)
- Inline node definitions on edges
- Chained edges and multi-target (`&`) edges
- Subgraphs (including nested, direction override, edges between subgraphs)
- Styling directives (`style`, `classDef`, `class`, `:::` inline)
- Comments (`%%`), semicolon line separators, entity codes, `<br/>` in labels, quoted labels

### Out of scope
- Click interactions (ignore / skip gracefully)
- Markdown-in-labels rendering (store raw label text; rendering is a later task)
- Any layout or SVG generation

## Implementation Approach
Use a hand-written recursive descent parser (not regex-only). The grammar is context-sensitive in places (e.g., `A)text(` asymmetric shape) which makes pure regex fragile.

Tokenization phase:
1. Strip comments
2. Split into logical lines (handle `;` separators)
3. For each line, identify: direction declaration, node+edge statement, subgraph start/end, style/class directive

## Acceptance Criteria

### Module structure
- [ ] `from pymermaid.parser import parse_flowchart` works
- [ ] `parse_flowchart(text: str) -> Diagram` accepts a string of Mermaid flowchart syntax and returns a `Diagram` instance from `pymermaid.ir`
- [ ] The parser raises a well-defined exception (e.g., `ParseError`) for invalid input, and the exception includes the line number where the error occurred

### Diagram declaration
- [ ] `parse_flowchart("graph TD\n  A --> B")` returns a `Diagram` with `direction == Direction.TD`
- [ ] `parse_flowchart("flowchart LR\n  A --> B")` returns a `Diagram` with `direction == Direction.LR`
- [ ] All four directions are supported: `TB`, `TD`, `BT`, `LR`, `RL` (note: `TB` and `TD` are synonyms for top-to-bottom)
- [ ] Both `graph` and `flowchart` keywords are accepted

### Node shapes (all 14)
- [ ] `A` (bare id, no brackets) produces a node with `shape == NodeShape.rect` and `label == "A"`
- [ ] `A[text]` produces `shape == NodeShape.rect`, `label == "text"`
- [ ] `A("text")` produces `shape == NodeShape.rounded`
- [ ] `A(["text"])` produces `shape == NodeShape.stadium`
- [ ] `A[["text"]]` produces `shape == NodeShape.subroutine`
- [ ] `A[("text")]` produces `shape == NodeShape.cylinder`
- [ ] `A(("text"))` produces `shape == NodeShape.circle`
- [ ] `A)text(` produces `shape == NodeShape.asymmetric`
- [ ] `A{"text"}` produces `shape == NodeShape.diamond`
- [ ] `A{{"text"}}` produces `shape == NodeShape.hexagon`
- [ ] `A[/"text"/]` produces `shape == NodeShape.parallelogram`
- [ ] `A[\"text"\]` produces `shape == NodeShape.parallelogram_alt`
- [ ] `A[/"text"\]` produces `shape == NodeShape.trapezoid`
- [ ] `A[\"text"/]` produces `shape == NodeShape.trapezoid_alt`
- [ ] `A((("text")))` produces `shape == NodeShape.double_circle`

### Edge types
- [ ] `A --> B` produces an edge with `edge_type == EdgeType.arrow`, `target_arrow == ArrowType.arrow`
- [ ] `A --- B` produces `edge_type == EdgeType.open`, arrows are `ArrowType.none`
- [ ] `A -.-> B` produces `edge_type == EdgeType.dotted_arrow`
- [ ] `A -.- B` produces `edge_type == EdgeType.dotted`
- [ ] `A ==> B` produces `edge_type == EdgeType.thick_arrow`
- [ ] `A === B` produces `edge_type == EdgeType.thick`
- [ ] `A ~~~ B` produces `edge_type == EdgeType.invisible`
- [ ] `A --o B` produces `target_arrow == ArrowType.circle`
- [ ] `A --x B` produces `target_arrow == ArrowType.cross`
- [ ] `A <--> B` produces `source_arrow == ArrowType.arrow` and `target_arrow == ArrowType.arrow`
- [ ] `A ----> B` produces `extra_length == 2` (two extra dashes beyond the minimum `-->`; exact number TBD based on IR definition)

### Edge labels
- [ ] `A -->|label text| B` produces an edge with `label == "label text"`
- [ ] `A -- label text --> B` produces an edge with `label == "label text"`
- [ ] Label syntax works with all edge types (dotted, thick, etc.)

### Inline node definitions
- [ ] `A[Start] --> B[End]` creates two nodes with the correct labels and an edge between them
- [ ] If a node ID was already defined with a shape, a later inline reference uses the previously defined shape (no conflict)

### Chained and multi-target edges
- [ ] `A --> B --> C` produces two edges: A->B and B->C
- [ ] `A --> B & C` produces two edges: A->B and A->C
- [ ] `A & B --> C & D` produces four edges: A->C, A->D, B->C, B->D

### Subgraphs
- [ ] `subgraph sg1[Title]\n  A --> B\nend` produces a `Subgraph` with `id == "sg1"`, `title == "Title"`, containing node IDs `A` and `B`
- [ ] Nested subgraphs are parsed correctly (a subgraph inside a subgraph)
- [ ] `direction LR` inside a subgraph sets the subgraph's `direction` to `Direction.LR`
- [ ] Edges between a node inside a subgraph and a node outside are captured in the diagram's edge list

### Styling
- [ ] `style nodeId fill:#f9f,stroke:#333` produces a `StyleDef` with `target_id == "nodeId"` and the correct properties dict
- [ ] `classDef className fill:#f9f,stroke:#333` populates `diagram.classes["className"]`
- [ ] `class nodeId1,nodeId2 className` assigns the class to the specified nodes' `css_classes` list
- [ ] `A:::className` inline syntax adds `"className"` to the node's `css_classes`

### Comments and special characters
- [ ] Lines starting with `%%` are stripped and do not affect parsing
- [ ] Inline `%%` comments are stripped from the end of lines
- [ ] Semicolons act as line separators: `A --> B; C --> D` produces two edges
- [ ] Entity code `#35;` in a label is decoded to `#`
- [ ] `<br/>` in labels is preserved in the label string (rendering handles it later)
- [ ] Quoted labels with special characters like `A["(special)"]` preserve the content

### Error handling
- [ ] Invalid syntax (e.g., `A -->`) raises `ParseError` with a message containing the line number
- [ ] Missing `end` for a subgraph raises `ParseError`
- [ ] Unknown diagram keyword (e.g., `chart TD`) raises `ParseError`

### Test suite
- [ ] `uv run pytest tests/test_flowchart_parser.py` passes with all tests green
- [ ] At least 50 test cases covering the scenarios below

## Test Scenarios

### Unit: Diagram declaration
- Parse `graph TD` -- verify direction is TD
- Parse `graph LR` -- verify direction is LR
- Parse `flowchart BT` -- verify direction is BT
- Parse `flowchart RL` -- verify direction is RL
- Parse `graph TB` -- verify TB is treated the same as TD
- Parse missing direction (e.g., just `graph`) -- verify sensible default or error

### Unit: Node shapes (one test per shape, 15 tests)
- Bare id `A` -- rect shape, label equals id
- `A[text]` -- rect
- `A("text")` -- rounded
- `A(["text"])` -- stadium
- `A[["text"]]` -- subroutine
- `A[("text")]` -- cylinder
- `A(("text"))` -- circle
- `A)text(` -- asymmetric
- `A{"text"}` -- diamond
- `A{{"text"}}` -- hexagon
- `A[/"text"/]` -- parallelogram
- `A[\"text"\]` -- parallelogram_alt
- `A[/"text"\]` -- trapezoid
- `A[\"text"/]` -- trapezoid_alt
- `A((("text")))` -- double_circle

### Unit: Edge types (one test per type, 11 tests)
- `A --> B` -- arrow
- `A --- B` -- open
- `A -.-> B` -- dotted arrow
- `A -.- B` -- dotted
- `A ==> B` -- thick arrow
- `A === B` -- thick
- `A ~~~ B` -- invisible
- `A --o B` -- circle end
- `A --x B` -- cross end
- `A <--> B` -- bidirectional
- `A ----> B` -- extra length

### Unit: Edge labels
- Pipe syntax: `A -->|some label| B` -- label is "some label"
- Inline syntax: `A -- some label --> B` -- label is "some label"
- Label on dotted edge: `A -. label .-> B`
- Label on thick edge: `A == label ==> B`
- Empty pipe label: `A -->|| B` -- label is empty string or None (define which)

### Unit: Inline node definitions
- `A[Start] --> B[End]` -- both nodes created with labels
- `A[Start] --> B` -- A gets label, B is bare
- Redefinition: define `A[First]` then `A[Second]` -- second label wins (or error; define behavior)

### Unit: Chained edges
- `A --> B --> C` -- two edges
- `A --> B --> C --> D` -- three edges
- Chained with labels: `A -->|yes| B -->|no| C`

### Unit: Multi-target edges
- `A --> B & C` -- two edges from A
- `A & B --> C` -- two edges to C
- `A & B --> C & D` -- four edges

### Unit: Subgraphs
- Simple subgraph with title
- Subgraph without title: `subgraph sg1\n  A\nend`
- Nested subgraph (two levels)
- Direction override inside subgraph
- Edge from inside subgraph to outside node
- Edge between two different subgraphs

### Unit: Styling
- `style` directive with multiple properties
- `classDef` with multiple properties
- `class` assigning to multiple nodes
- Inline `:::className` on a node definition
- `classDef default` -- verify it is stored with key "default"

### Unit: Comments and special characters
- Line with only `%%` comment -- ignored
- Inline comment after a statement
- Semicolon-separated statements on one line
- Entity code `#35;` decoded in label
- `<br/>` preserved in label
- Quoted label with parentheses and brackets

### Unit: Error handling
- Incomplete edge `A -->` with no target -- ParseError with line number
- Unclosed subgraph (no `end`) -- ParseError
- Unknown declaration keyword -- ParseError
- Empty input -- ParseError or empty diagram (define which)

### Integration: Multi-statement diagrams
- A complete flowchart with nodes, edges, subgraph, and styling -- verify full Diagram structure
- A flowchart using every node shape at least once
- A flowchart using every edge type at least once

## Estimated Complexity
Large -- most complex task in the project. ~500-800 lines of parsing code.
