# Task 55: LR Flowchart with Subgraphs Renders Incorrectly

## Problem

`flowchart LR` diagrams with multiple subgraphs render with broken layout. The subgraphs are positioned chaotically instead of flowing left-to-right. Observed in `flowchart/ci_pipeline.mmd`.

### Issues

1. **Overall direction ignored** -- `flowchart LR` should place Build -> Test -> Deploy left-to-right. Instead Build is bottom-left, Test is top-center, Deploy is bottom-right. The Sugiyama layout is treating this as TD.

2. **Subgraphs overlap** -- Build and Test subgraph boundaries overlap vertically. They should be side by side with clear separation.

3. **Edge routing crosses subgraph boundaries chaotically** -- Edges from Compile (in Build) to Unit Tests/Integration Tests (in Test) go diagonally up through the Build subgraph border instead of exiting the right side cleanly.

4. **Edge label clipped by adjacent node** -- "Approved" label between Staging->Production is partially hidden behind the Staging node.

5. **Cross-subgraph edges in LR should be horizontal** -- In LR mode, edges between subgraphs should flow left-to-right, not diagonally.

### Expected behavior (mmdc reference)
Build, Test, Deploy subgraphs sit side by side horizontally. Checkout->Restore->Compile flows left-to-right within Build. Edges from Compile fan out right to Unit Tests and Integration Tests. Both converge right to Staging. Staging->Approved->Production flows right.

## Key Files

### Source files to investigate and modify
- `/home/alexey/git/pymermaid/src/pymermaid/layout/sugiyama.py` -- Main layout engine. `_apply_direction()` at line ~745 transforms TB coordinates to LR/RL/BT. `layout_diagram()` at line ~1148 is the entry point. Subgraph bounding-box computation happens after direction transform; the bug is likely that subgraph positions are computed in TB space and then not correctly transformed, or that the direction transform does not account for subgraph-level grouping constraints.
- `/home/alexey/git/pymermaid/src/pymermaid/layout/types.py` -- `SubgraphLayout` dataclass (x, y, width, height, title).
- `/home/alexey/git/pymermaid/src/pymermaid/render/svg.py` -- SVG renderer. `_render_subgraph_recursive()` at line ~334 renders subgraph `<g class="subgraph" data-subgraph-id="...">` with a `<rect>` child for the bounding box.

### Test fixture
- `/home/alexey/git/pymermaid/tests/fixtures/corpus/flowchart/ci_pipeline.mmd` -- The CI pipeline diagram (`flowchart LR` with 3 subgraphs: Build, Test, Deploy).

### Existing related tests (do NOT break these)
- `/home/alexey/git/pymermaid/tests/test_lr_subgraph_overlap.py` -- Task 36's overlap tests. Your new tests must coexist with these. These tests use the layout API directly; your tests should add end-to-end SVG assertions.

### New test file to create
- `/home/alexey/git/pymermaid/tests/test_lr_subgraph_layout.py`

## Acceptance Criteria

All criteria must pass programmatically -- no visual-only checks.

- [ ] Render `ci_pipeline.mmd` end-to-end via `from pymermaid import render_diagram`; parse the resulting SVG with `xml.etree.ElementTree`.
- [ ] Extract the 3 subgraph `<g class="subgraph">` elements by their `data-subgraph-id` attribute ("Build", "Test", "Deploy"). Each has a `<rect>` child whose `x`, `y`, `width`, `height` attributes define the bounding box.
- [ ] **LR ordering**: `Build` center_x < `Test` center_x < `Deploy` center_x (where center_x = float(rect.x) + float(rect.width) / 2).
- [ ] **No overlaps**: No pair of the 3 subgraph rects overlap (rect A and rect B overlap iff A.x < B.x + B.width AND B.x < A.x + A.width AND A.y < B.y + B.height AND B.y < A.y + A.height). Use a tolerance of 1.0 px.
- [ ] **Internal node ordering within Build subgraph**: Extract node positions for Checkout (A), Restore (B), Compile (C). Assert A.center_x < B.center_x < C.center_x (they should flow left-to-right within the subgraph).
- [ ] **Cross-subgraph edges flow left-to-right**: For each edge whose source is in Build and target is in Test (C->D, C->E), the source node's center_x must be less than the target node's center_x.
- [ ] **Edge label "Approved" is not clipped**: The "Approved" label element (a `<text>` element near the F->G edge) must have its x-coordinate between F.center_x and G.center_x (i.e., it sits in the gap between the two nodes, not overlapping either).
- [ ] **No regression for TD/BT**: Render a simple `flowchart TD` diagram with 2 subgraphs; confirm subgraph center_y values follow the dependency order (upstream center_y < downstream center_y) and subgraphs do not overlap.
- [ ] `uv run pytest tests/test_lr_subgraph_layout.py -v` passes with all tests green.
- [ ] `uv run pytest tests/test_lr_subgraph_overlap.py -v` still passes (no regressions).

## Test Scenarios

Write all tests in `/home/alexey/git/pymermaid/tests/test_lr_subgraph_layout.py`.

### Helper: SVG parsing

Write a helper function `_parse_subgraph_rects(svg_str: str) -> dict[str, dict]` that parses the SVG string with `xml.etree.ElementTree`, finds all `<g class="subgraph">` elements, and returns a dict keyed by `data-subgraph-id` with values `{"x": float, "y": float, "width": float, "height": float, "center_x": float, "center_y": float}`. Similarly, write `_parse_node_positions(svg_str: str) -> dict[str, dict]` that finds node elements and returns their bounding boxes.

### Test: LR subgraph horizontal ordering (ci_pipeline.mmd)
- Render `ci_pipeline.mmd` with `render_diagram`.
- Parse subgraph rects for Build, Test, Deploy.
- Assert `Build.center_x < Test.center_x < Deploy.center_x`.

### Test: LR subgraph no overlap (ci_pipeline.mmd)
- Same render.
- Assert no pair of the 3 subgraph rects overlap (use the overlap formula from acceptance criteria, with 1.0 px tolerance).

### Test: Internal node ordering within Build subgraph
- Same render.
- Find nodes A (Checkout), B (Restore), C (Compile).
- Assert `A.center_x < B.center_x < C.center_x`.

### Test: Cross-subgraph edges flow left-to-right
- Same render.
- For edges C->D and C->E, assert source center_x < target center_x.

### Test: Edge label positioning
- Same render.
- Find the "Approved" text label. Assert its x is between F.center_x and G.center_x.

### Test: TD regression (no breakage)
- Render a simple `flowchart TD` with 2 subgraphs (e.g., `subgraph Frontend ... end` and `subgraph Backend ... end` connected by an edge).
- Assert subgraphs do not overlap and upstream center_y < downstream center_y.

### Test: RL direction works (bonus, optional)
- Render a `flowchart RL` variant of the CI pipeline.
- Assert `Deploy.center_x < Test.center_x < Build.center_x` (reversed).

## Methodology

**TDD -- write failing tests FIRST, then fix the code.**

1. Create `/home/alexey/git/pymermaid/tests/test_lr_subgraph_layout.py` with the tests above.
2. Run `uv run pytest tests/test_lr_subgraph_layout.py -v` and confirm tests FAIL (this proves the bug exists).
3. Investigate and fix the layout code in `/home/alexey/git/pymermaid/src/pymermaid/layout/sugiyama.py`. The likely root cause is in how `_apply_direction()` interacts with subgraph bounding-box computation -- either the direction transform is not applied to subgraph coordinates, or the Sugiyama layer assignment does not respect subgraph grouping when computing LR positions.
4. Run `uv run pytest tests/test_lr_subgraph_layout.py -v` and confirm all tests PASS.
5. Run `uv run pytest tests/test_lr_subgraph_overlap.py -v` and confirm no regressions.
6. Run `uv run pytest` (full suite) and confirm no regressions elsewhere.

## Dependencies

None -- this is a bug fix on existing functionality.

## Estimated Complexity

High -- likely a fundamental issue in how the Sugiyama layout handles direction + subgraphs together. The `_apply_direction()` function transforms node positions but may not correctly transform subgraph bounding boxes, or the layer assignment may not group nodes by subgraph membership when computing LR coordinates.
