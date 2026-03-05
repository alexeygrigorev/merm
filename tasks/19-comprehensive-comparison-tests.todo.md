# 19 - Comprehensive Comparison Test Suite

## Goal
Build a large test corpus of mermaid diagrams, render them with both mermaid.js (mmdc) and pymermaid, and systematically compare the outputs. This ensures we match mermaid's rendering as closely as possible across a wide variety of diagram features.

## Approach

### 1. Build Test Corpus (50+ diagrams)
Collect/generate mermaid flowchart diagrams covering:

**Basic structures:**
- Single node, two nodes with edge, linear chain (3-5 nodes)
- Fan-out (1 -> many), fan-in (many -> 1), diamond pattern
- Self-loops, bidirectional edges, parallel paths

**All node shapes (14 types):**
- One diagram per shape type with varying text lengths
- Mixed shapes in one diagram

**All edge types (7 types):**
- Solid, dotted, thick, invisible
- Arrow types: normal, circle, cross, none
- Bidirectional edges

**Edge labels:**
- Short labels, long labels, multi-word labels
- Labels on different edge types

**Subgraphs:**
- Single subgraph, nested subgraphs, multiple siblings
- Edges crossing subgraph boundaries
- Subgraph with title vs without

**Styling:**
- classDef with single and multiple classes
- Inline style directives
- Mixed styled and unstyled nodes

**Text complexity:**
- Short text, long text, multi-line text (`<br/>`)
- Special characters, unicode
- Markdown in labels (bold, italic, links)

**Direction:**
- TD, TB, BT, LR, RL

**Scale:**
- Small (2-3 nodes), medium (10-20 nodes), large (50+ nodes)

### 2. Generate Reference SVGs
- Script to batch-render all .mmd files with mmdc
- Store in `tests/reference/` alongside fixtures
- CI-friendly: skip comparison if mmdc not installed

### 3. SVG Structural Comparison Checklist
For each diagram pair (pymermaid vs mmdc), verify:

**Node matching:**
- [ ] Same number of nodes rendered
- [ ] Same node IDs present
- [ ] Node shapes match (rect, diamond, circle, etc.)
- [ ] Text content matches exactly

**Edge matching:**
- [ ] Same number of edges rendered
- [ ] Same source/target pairs
- [ ] Edge labels match
- [ ] Arrow types match (markers present/absent)
- [ ] Line styles match (solid, dotted, thick)

**Layout quality:**
- [ ] Nodes don't overlap each other
- [ ] Edges don't pass through nodes
- [ ] Labels don't overlap nodes or other labels
- [ ] Proper directionality (TD flows top-down, LR flows left-right)
- [ ] Subgraph boundaries contain their children

**Visual similarity (color/style):**
- [ ] Node fill color matches (within threshold)
- [ ] Node stroke color matches
- [ ] Node stroke width matches
- [ ] Edge stroke color matches
- [ ] Edge stroke width matches
- [ ] Font family matches
- [ ] Font size matches (within 2px)
- [ ] Subgraph background color matches
- [ ] Subgraph border color matches
- [ ] Arrow marker size is proportional

**Spacing/sizing:**
- [ ] Node width accommodates text with similar padding
- [ ] Node height is proportional to mermaid's
- [ ] Inter-rank spacing is similar (within 20%)
- [ ] Inter-node spacing is similar (within 20%)
- [ ] Overall diagram aspect ratio is similar

### 4. PNG Visual Comparison (selective)
For a subset of key diagrams (10-15):
- Render both SVGs to PNG (using cairosvg or similar)
- Compute pixel-level similarity metrics:
  - SSIM (Structural Similarity Index) — target > 0.8
  - Pixel diff percentage — target < 15% different pixels
- Generate visual diff images for review
- Store comparison reports

### 5. Scoring System
Each diagram gets a similarity score:
- **Structural score** (0-100): based on checklist items above
- **Visual score** (0-100): based on SSIM/pixel comparison
- **Overall score**: weighted average (structural 60%, visual 40%)
- Dashboard/report showing scores per diagram and aggregate

## Acceptance Criteria
- [ ] 50+ test .mmd files in `tests/fixtures/` organized by category
- [ ] Script to batch-generate reference SVGs with mmdc
- [ ] Automated structural comparison runs on all fixtures
- [ ] Checklist above is implemented as assertion checks
- [ ] PNG comparison pipeline works for selected diagrams
- [ ] Summary report shows per-diagram and aggregate scores
- [ ] All diagrams pass structural comparison (correct nodes/edges/labels)
- [ ] Visual similarity score > 70% average across all diagrams
- [ ] No diagram has overlap issues (nodes, edges, labels)

## Dependencies
- Task 18 (SVG visual quality) should be done first so we're comparing improved output
- Task 13 (integration tests) provides the basic comparison infrastructure

## Estimated Complexity
Large -- corpus creation, comparison infrastructure, scoring system, PNG pipeline.
