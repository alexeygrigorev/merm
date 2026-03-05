# 13 - Integration Tests

## Goal
End-to-end tests that verify the complete pipeline: mermaid text -> SVG output.

## Tasks

### Unit Test Suite (per module)
- [ ] Parser tests: one test per node shape, edge type, subgraph pattern
- [ ] Text measurement tests: verify widths against known values
- [ ] Layout tests: verify node positions are reasonable (no overlaps, correct ordering)
- [ ] Renderer tests: verify SVG validity and element presence

### Integration Tests
- [ ] Test each mermaid-cli fixture end-to-end:
  - `flowchart1.mmd`: basic flowchart with decisions
  - `flowchart2.mmd`: complex flowchart
  - `flowchart3.mmd`: subgraphs
  - `flowchart4.mmd`: styling
- [ ] Test all directions: TD, LR, BT, RL
- [ ] Test all node shapes (single diagram with all 14 shapes)
- [ ] Test all edge types (single diagram with all types)
- [ ] Test edge cases:
  - Empty diagram
  - Single node, no edges
  - Self-referencing edge
  - Disconnected components
  - Very long labels
  - Unicode / CJK labels
  - Deeply nested subgraphs
  - Cycles in graph

### Regression Tests
- [ ] Golden file tests: render known inputs, compare byte-for-byte with saved output
- [ ] Any bug fix gets a regression test

### CLI Tests
- [ ] Test CLI with file input
- [ ] Test CLI with stdin input
- [ ] Test CLI error handling (invalid file, bad syntax)

## Acceptance Criteria
- >95% code coverage on parser and renderer
- All mermaid-cli flowchart fixtures pass
- Test suite runs in < 10 seconds (no browser needed!)

## Dependencies
- All core tasks (01-12)

## Estimated Complexity
Medium - writing tests is straightforward but comprehensive coverage takes effort.
