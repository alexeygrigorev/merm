# 04 - Flowchart Parser

## Goal
Parse Mermaid flowchart syntax into the IR data model. This is the most complex parser since flowcharts have the richest syntax.

## Tasks

### Core Parsing
- [ ] Parse diagram declaration: `graph TD`, `graph LR`, `flowchart TB`, etc.
- [ ] Parse node declarations with all 14 classic shapes:
  - `A` (bare id = rectangle)
  - `A[text]` (rectangle)
  - `A("text")` (rounded)
  - `A(["text"])` (stadium)
  - `A[["text"]]` (subroutine)
  - `A[("text")]` (cylinder)
  - `A(("text"))` (circle)
  - `A)text(` (asymmetric)
  - `A{"text"}` (diamond)
  - `A{{"text"}}` (hexagon)
  - `A[/"text"/]` (parallelogram)
  - `A[\"text"\]` (parallelogram alt)
  - `A[/"text"\]` (trapezoid)
  - `A[\"text"/]` (trapezoid alt)
  - `A((("text")))` (double circle)
- [ ] Parse edge declarations:
  - `A --> B` (arrow)
  - `A --- B` (open)
  - `A -.-> B` (dotted arrow)
  - `A -.- B` (dotted)
  - `A ==> B` (thick arrow)
  - `A === B` (thick)
  - `A ~~~ B` (invisible)
  - `A --o B` (circle end)
  - `A --x B` (cross end)
  - `A <--> B` (bidirectional)
  - Extra length: `A ----> B`
- [ ] Parse edge labels:
  - `A -->|label| B`
  - `A -- label --> B`
  - Same for all edge types
- [ ] Parse inline node definitions on edges: `A[Start] --> B[End]`
- [ ] Parse chained edges: `A --> B --> C`
- [ ] Parse multi-target: `A --> B & C`

### Subgraphs
- [ ] Parse `subgraph id[Title] ... end`
- [ ] Parse nested subgraphs
- [ ] Parse `direction` override inside subgraphs
- [ ] Parse edges between subgraphs

### Styling
- [ ] Parse `style nodeId prop:val,prop:val`
- [ ] Parse `classDef className prop:val,prop:val`
- [ ] Parse `class nodeId1,nodeId2 className`
- [ ] Parse `nodeId:::className` inline syntax

### Other
- [ ] Strip comments: `%% comment`
- [ ] Handle quoted labels with special characters
- [ ] Handle entity codes: `#35;` -> `#`
- [ ] Handle `<br/>` in labels
- [ ] Handle semicolons as line separators

## Implementation Approach
Use a hand-written recursive descent parser (not regex-only). The grammar is context-sensitive in places (e.g., `A)text(` asymmetric shape) which makes pure regex fragile.

Tokenization phase:
1. Strip comments
2. Split into logical lines (handle `;` separators)
3. For each line, identify: direction declaration, node+edge statement, subgraph start/end, style/class directive

## Acceptance Criteria
- Parse all 28 mermaid-cli test fixtures without errors
- Round-trip test: parse -> serialize -> parse produces identical IR
- Unit tests for each node shape and edge type
- Error reporting with line numbers for invalid syntax

## Dependencies
- Task 03 (IR data model)

## Estimated Complexity
Large - most complex task in the project. ~500-800 lines of parsing code.
