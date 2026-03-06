# 13 - Integration Tests

## Goal
End-to-end tests that verify the complete pipeline: mermaid text -> parse -> layout -> SVG output. These tests exercise the full stack (not individual modules) and confirm that real-world diagrams render without errors and produce structurally correct SVG.

## Current State
- `tests/test_integration.py` exists but is empty (single docstring).
- CLI tests already exist in `tests/test_cli.py` (9 tests covering file input, stdin, error handling). Do NOT duplicate those -- task 13 focuses on the rendering pipeline, not CLI arg parsing.
- 4 fixture files exist in `tests/fixtures/`: `simple_flowchart.mmd`, `multiple_shapes.mmd`, `styling.mmd`, `subgraphs.mmd`.
- 472 tests already exist across the codebase (467 pass, 1 skip, 4 xfail).
- The mermaid-cli fixtures (`flowchart1.mmd` through `flowchart4.mmd`) referenced in the original task do NOT exist in this repo. Use the 4 existing fixtures plus new inline diagrams.

## Scope Clarification
- All new tests go in `tests/test_integration.py`.
- Tests should call the public API (`render_svg` from `pymermaid`) -- not CLI subprocess calls.
- Each test should parse mermaid text, run the full pipeline, and assert on the resulting SVG string.
- No reference renderer (mmdc) comparison is needed for this task. That infrastructure exists separately in `tests/comparison.py` / `tests/test_comparison.py`.

## Tasks

### Full-pipeline tests using existing fixtures
- [ ] Load each of the 4 fixture `.mmd` files from `tests/fixtures/` and render to SVG
- [ ] Assert each produces valid SVG (starts with `<svg`, contains `</svg>`)
- [ ] Assert expected nodes appear as `data-node-id` attributes in the SVG

### Direction tests
- [ ] Test all 4 directions: TD, LR, BT, RL with a simple 3-node diagram
- [ ] For each direction, verify that SVG is produced without error
- [ ] For TD vs LR, verify that the SVG viewBox dimensions differ (tall vs wide)

### Node shape coverage
- [ ] Create one diagram containing all 14 node shapes (rectangle, rounded, stadium, subroutine, cylinder, circle, asymmetric, diamond, hexagon, parallelogram, parallelogram-alt, trapezoid, trapezoid-alt, double-circle)
- [ ] Render and verify all 14 node IDs appear in the SVG output

### Edge type coverage
- [ ] Create one diagram exercising all edge types: arrow, open link, dotted arrow, thick arrow, invisible link, circle endpoint, cross endpoint, edges with labels
- [ ] Render and verify all node IDs appear and SVG is valid

### Edge cases
- [ ] Single node, no edges -- renders SVG with one node
- [ ] Self-referencing edge (`A --> A`) -- renders without error
- [ ] Disconnected components (nodes with no edges between groups) -- all nodes appear
- [ ] Long labels (100+ characters) -- renders without error
- [ ] Unicode labels (e.g., accented characters, CJK if supported) -- renders without error
- [ ] Diagram with a cycle (`A --> B --> C --> A`) -- renders without error
- [ ] Nested subgraphs (2+ levels deep) -- renders without error, all nodes present

### Styling integration
- [ ] Diagram with `classDef` and `:::className` -- renders without error
- [ ] Diagram with inline `style` -- renders without error

## Acceptance Criteria

- [ ] `uv run pytest tests/test_integration.py -v` passes with 20+ tests
- [ ] Every test calls `render_svg()` (or the equivalent public function) with mermaid text and asserts on SVG output
- [ ] All 4 existing fixture files are covered
- [ ] All 4 directions (TD, LR, BT, RL) are covered
- [ ] All 14 node shapes appear in at least one test
- [ ] Edge cases (single node, self-ref, cycle, disconnected, long labels, unicode, nested subgraphs) each have a dedicated test
- [ ] No test takes more than 2 seconds individually
- [ ] `uv run pytest` (full suite) still passes -- no regressions
- [ ] `uv run ruff check tests/test_integration.py` passes

## Test Scenarios

### Integration: fixture rendering
- Load `tests/fixtures/simple_flowchart.mmd`, call `render_svg()`, assert `data-node-id="A"`, `data-node-id="B"`, `data-node-id="C"` all present
- Load `tests/fixtures/multiple_shapes.mmd`, call `render_svg()`, assert 5 node IDs present
- Load `tests/fixtures/subgraphs.mmd`, call `render_svg()`, assert 4 node IDs present and subgraph titles appear
- Load `tests/fixtures/styling.mmd`, call `render_svg()`, assert renders without error

### Integration: directions
- `graph TD\n A --> B --> C` produces valid SVG
- `graph LR\n A --> B --> C` produces valid SVG
- `graph BT\n A --> B --> C` produces valid SVG
- `graph RL\n A --> B --> C` produces valid SVG
- TD viewBox height > width; LR viewBox width > height (or at minimum they differ)

### Integration: all node shapes
- Single diagram with 14 differently-shaped nodes, assert all 14 `data-node-id` attributes present

### Integration: all edge types
- Single diagram with varied edge syntax, assert valid SVG and all nodes present

### Integration: edge cases
- `graph TD\n A[Alone]` -- single node, valid SVG, `data-node-id="A"` present
- `graph TD\n A --> A` -- self-ref, no crash
- `graph TD\n A --> B\n C --> D` -- disconnected, 4 nodes present
- `graph TD\n A --> B --> C --> A` -- cycle, no crash
- 100-char label -- no crash
- Nested subgraphs 3 levels deep -- no crash, all inner nodes present

## Dependencies
- Tasks 01-12 must be `.done.md` (all confirmed done)

## Estimated Complexity
Medium -- the rendering pipeline is complete; this task is about writing thorough tests against the public API.
