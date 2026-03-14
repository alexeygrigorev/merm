# Issue 73: Edge case bug hunting with complex diagrams

## Problem

Systematic rendering of complex real-world diagrams from the existing test fixtures has not been done with PNG visual verification. There are likely rendering edge cases and bugs lurking in complex diagrams involving nested subgraphs, many edges, special shapes, styling, and multi-type diagrams.

## Scope

- Select 12-15 complex diagrams from the existing test fixtures (`tests/fixtures/corpus/` and `tests/fixtures/github/`)
- Render each with `merm.render_diagram()`, convert SVG to PNG with cairosvg
- Verify no crashes, no tracebacks, and PNG output is non-degenerate (non-zero size, has visual content)
- Identify and fix 3-5 concrete rendering issues found during this process
- Focus areas: edge routing, text overflow, subgraph nesting, large diagrams, unusual shapes, styling, multi-type coverage

## Diagram Selection

The engineer must include at least these fixture files (covering multiple diagram types and complexity levels):

### Flowcharts (complex)
1. `tests/fixtures/corpus/flowchart/ci_pipeline.mmd`
2. `tests/fixtures/corpus/flowchart/elt_bigquery.mmd`
3. `tests/fixtures/corpus/flowchart/registration.mmd`

### Subgraphs
4. `tests/fixtures/corpus/subgraphs/nested_subgraphs.mmd`
5. `tests/fixtures/corpus/subgraphs/cross_boundary_edges.mmd`

### Shapes and styling
6. `tests/fixtures/corpus/shapes/mixed_shapes.mmd`
7. `tests/fixtures/corpus/styling/mixed_styled_unstyled.mmd`

### Edges
8. `tests/fixtures/corpus/edges/labeled_edges.mmd`
9. `tests/fixtures/corpus/edges/circle_endpoint.mmd`

### Scale
10. `tests/fixtures/corpus/scale/large.mmd`

### Other diagram types
11. `tests/fixtures/corpus/sequence/complex.mmd`
12. `tests/fixtures/corpus/class/complex.mmd`
13. `tests/fixtures/corpus/state/complex.mmd`

### Real-world (GitHub)
14. `tests/fixtures/github/flink_late_upsert.mmd`
15. `tests/fixtures/github/ci_pipeline.mmd`

The engineer may add more if additional edge cases are discovered.

## Dependencies

- None (uses existing fixtures and rendering pipeline)

## Acceptance Criteria

- [ ] A test file `tests/test_edge_case_rendering.py` exists with at least 12 parametrized test cases
- [ ] Each test case: reads a fixture `.mmd` file, calls `render_diagram()`, asserts the result is valid SVG (non-empty, starts with `<svg`)
- [ ] Each test case: converts SVG to PNG via cairosvg, asserts PNG is non-zero bytes
- [ ] Each test case: asserts PNG dimensions are reasonable (width > 50px, height > 50px) to catch degenerate layouts
- [ ] `uv run pytest tests/test_edge_case_rendering.py` passes with all 12+ tests green
- [ ] At least 3 concrete rendering bugs are identified and fixed (documented in the test file or issue)
- [ ] For each bug fixed, a targeted regression test exists that would fail without the fix
- [ ] Render all 12+ diagrams to PNG in `.tmp/edge_cases/` and visually verify: no obviously broken output (overlapping nodes, text outside viewport, blank images, missing labels)
- [ ] No existing tests are broken by the fixes (`uv run pytest` full suite passes)

## Test Scenarios

### Parametrized: Render-and-verify for all selected fixtures
- For each of the 12-15 fixture files:
  - Parse and render to SVG without raising any exception
  - SVG output is well-formed (contains `<svg` and `</svg>`)
  - Convert to PNG with cairosvg, PNG size > 0 bytes
  - PNG dimensions > 50x50 pixels (no degenerate layout)

### Regression tests for found bugs
- For each bug fixed (minimum 3):
  - A minimal reproduction diagram that triggers the bug
  - The test fails if the fix is reverted
  - The test verifies the correct behavior (not just "doesn't crash")

### Full suite non-regression
- `uv run pytest` passes (all existing tests still work after fixes)

### Visual PNG verification
- Render all selected diagrams to `.tmp/edge_cases/*.png`
- Engineer and tester must view the PNGs and confirm no obviously broken output
- Specific things to check in PNGs:
  - Labels are visible and not clipped
  - Edges connect to nodes (not floating in space)
  - Subgraph boundaries contain their children
  - Text does not overflow shape boundaries dramatically
  - Large diagrams render completely (not truncated)
