# 19 - Comprehensive Comparison Test Suite

## Goal
Build a large test corpus of mermaid flowchart diagrams (50+ `.mmd` files), render them with pymermaid, and verify correctness through structural SVG comparison. Optionally compare against mermaid-cli (mmdc) reference output when available. This catches regressions and ensures we handle the full range of flowchart syntax.

## Dependencies
- Tasks 01-13, 17: all `.done.md` -- VERIFIED
- Task 18 (SVG visual quality): INDEPENDENT. This task can be worked in parallel. The test fixtures and structural comparisons are valid regardless of the theme. If task 18 lands first, some expected values may shift, but the test infrastructure is theme-agnostic.

## Scope Decisions

The original spec included a weighted scoring system (structural 60% / visual 40%) with dashboards. That is over-engineered for this stage. Here is the practical scope:

**IN SCOPE:**
- 50+ `.mmd` fixture files organized by category
- Structural comparison tests: correct node count, edge count, labels, no overlaps
- A batch script to generate mmdc reference SVGs (for manual review, not CI-blocking)
- Layout quality assertions: no overlaps, correct directionality, subgraph containment

**DEFERRED (future task):**
- PNG pixel comparison (SSIM, pixel diff) -- requires `cairosvg` dependency and is fragile across platforms
- Weighted scoring dashboard -- useful later when optimizing visual fidelity
- Visual diff image generation

## Part 1: Test Fixture Corpus

Create 50+ `.mmd` files in `tests/fixtures/corpus/` organized by subdirectory:

### Directory structure
```
tests/fixtures/corpus/
  basic/           # 8-10 files
  shapes/          # 15+ files (one per shape type + mixed)
  edges/           # 8-10 files (all edge types, labels)
  subgraphs/       # 6-8 files
  styling/         # 5-6 files
  direction/       # 5 files (TD, TB, BT, LR, RL)
  scale/           # 3-4 files (small, medium, large)
  text/            # 5-6 files (special chars, multiline, long text)
```

### Required fixtures (minimum):

**basic/ (8 files):**
- `single_node.mmd` -- one node
- `two_nodes.mmd` -- A --> B
- `linear_chain.mmd` -- A --> B --> C --> D --> E
- `fan_out.mmd` -- one node to 4+ targets
- `fan_in.mmd` -- 4+ sources to one node
- `diamond.mmd` -- A->B, A->C, B->D, C->D
- `self_loop.mmd` -- A --> A
- `parallel_paths.mmd` -- two independent chains

**shapes/ (15 files, one per shape + 1 mixed):**
- `rect.mmd`, `rounded.mmd`, `stadium.mmd`, `subroutine.mmd`, `cylinder.mmd`, `circle.mmd`, `asymmetric.mmd`, `diamond.mmd`, `hexagon.mmd`, `parallelogram.mmd`, `parallelogram_alt.mmd`, `trapezoid.mmd`, `trapezoid_alt.mmd`, `double_circle.mmd`
- `mixed_shapes.mmd` -- diagram using 5+ different shapes

**edges/ (8 files):**
- `arrow.mmd`, `open_link.mmd`, `dotted.mmd`, `thick.mmd`, `invisible.mmd`
- `circle_endpoint.mmd`, `cross_endpoint.mmd`
- `labeled_edges.mmd` -- edges with short, long, multi-word labels

**subgraphs/ (6 files):**
- `single_subgraph.mmd`
- `nested_subgraphs.mmd`
- `sibling_subgraphs.mmd`
- `cross_boundary_edges.mmd` -- edges between nodes in different subgraphs
- `subgraph_with_title.mmd`
- `subgraph_direction.mmd` -- subgraph with `direction LR` override

**styling/ (5 files):**
- `classdef_single.mmd`
- `classdef_multiple.mmd`
- `inline_style.mmd`
- `default_class.mmd`
- `mixed_styled_unstyled.mmd`

**direction/ (5 files):**
- `td.mmd`, `tb.mmd`, `bt.mmd`, `lr.mmd`, `rl.mmd`

**scale/ (3 files):**
- `small.mmd` (2-3 nodes)
- `medium.mmd` (10-20 nodes)
- `large.mmd` (50+ nodes)

**text/ (5 files):**
- `short_text.mmd`
- `long_text.mmd` -- nodes with very long labels
- `multiline.mmd` -- labels with `<br/>`
- `special_chars.mmd` -- unicode, ampersands, angle brackets
- `quoted_labels.mmd` -- labels in quotes with special syntax

## Part 2: Structural Comparison Infrastructure

### Extend `tests/comparison.py`

The existing `comparison.py` already has `SVGStructure`, `SVGDiff`, `parse_svg_nodes`, `parse_svg_edges`, and `structural_compare`. Extend it with:

1. **`parse_pymermaid_svg_nodes(svg_text)`** -- parse nodes from pymermaid's SVG format (uses `data-node-id` attribute on `<g class="node">`, text in `<text>` elements). The existing `parse_svg_nodes` is tuned for mmdc's `foreignObject`/`span` format.
2. **`parse_pymermaid_svg_edges(svg_text)`** -- parse edges from pymermaid's format (uses `<g class="edge">` with `data-edge="true"` paths).
3. **`check_no_overlaps(svg_text)`** -- parse node bounding boxes and verify no two nodes overlap.
4. **`check_directionality(svg_text, direction)`** -- verify that nodes flow in the expected direction (e.g., for TD, y-coordinates generally increase from source to target).
5. **`check_subgraph_containment(svg_text)`** -- verify subgraph rects contain their child nodes.

### Test runner: `tests/test_corpus.py`

A parametrized pytest suite that:
- Discovers all `.mmd` files in `tests/fixtures/corpus/`
- For each file: parse -> layout -> render -> structural assertions
- Asserts: renders without error, correct node count, correct edge count, all labels present, no overlaps

```python
@pytest.mark.parametrize("mmd_file", glob("tests/fixtures/corpus/**/*.mmd"))
def test_corpus_renders(mmd_file):
    """Every fixture renders without error and has correct structure."""
    ...

@pytest.mark.parametrize("mmd_file", glob("tests/fixtures/corpus/**/*.mmd"))
def test_corpus_no_overlaps(mmd_file):
    """No node overlaps in any fixture."""
    ...
```

## Part 3: Reference SVG Generation Script

Create `scripts/generate_references.sh`:
- Iterates over all `.mmd` files in `tests/fixtures/corpus/`
- Renders each with `mmdc` to `tests/reference/corpus/`
- Skips gracefully if `mmdc` is not installed
- Prints summary of successes/failures

This is a developer tool, not a CI requirement.

## Acceptance Criteria

- [ ] At least 50 `.mmd` files exist in `tests/fixtures/corpus/` organized by subdirectory
- [ ] Every subdirectory listed above has at least the minimum number of files specified
- [ ] `uv run pytest tests/test_corpus.py` runs and passes
- [ ] Every fixture file parses without error
- [ ] Every fixture file renders to valid SVG without error
- [ ] Structural assertions verify correct node count and edge count for each fixture
- [ ] All expected label text appears in rendered SVG output
- [ ] No node overlap is detected in any rendered fixture
- [ ] Direction fixtures (td, lr, bt, rl) verify correct flow direction
- [ ] Subgraph fixtures verify containment (subgraph rect contains child nodes)
- [ ] `scripts/generate_references.sh` exists and works when `mmdc` is available
- [ ] Existing tests still pass: `uv run pytest` (full suite)
- [ ] `tests/comparison.py` has pymermaid-native SVG parsing (not just mmdc format)

## Test Scenarios

### Parametrized: Corpus rendering
- Each of 50+ `.mmd` files parses successfully
- Each of 50+ `.mmd` files renders to non-empty SVG
- Each rendered SVG has the expected number of nodes (derived from the `.mmd` source)
- Each rendered SVG has the expected number of edges (derived from the `.mmd` source)

### Unit: Overlap detection
- Two nodes at the same position detected as overlap
- Two non-overlapping nodes pass
- Nodes barely touching (shared edge) pass (no false positives)

### Unit: Directionality check
- TD diagram: target node y > source node y
- LR diagram: target node x > source node x
- BT diagram: target node y < source node y

### Unit: Subgraph containment
- Subgraph rect fully contains all child node rects
- Nested subgraph: outer contains inner

### Integration: Full pipeline
- `simple_flowchart.mmd` (existing fixture) still works
- `large.mmd` (50+ nodes) renders in under 5 seconds

## Implementation Notes

1. Start with the fixture files. Write them by hand -- each should be minimal and focused on one feature. Use the mermaid syntax reference in `tasks/plan.md`.
2. For structural assertions, you need to know the expected node/edge counts. Two approaches:
   - (a) Parse the `.mmd` file to count nodes/edges programmatically (preferred -- the parser already exists).
   - (b) Hardcode expected counts per fixture in a companion `.json` or in the test itself.
   Approach (a) is better because it uses our own parser as ground truth.
3. For overlap detection, parse `x`, `y`, `width`, `height` from `<rect>` elements inside `<g class="node">` groups. Two rects overlap if their bounding boxes intersect.
4. Keep the test file well-organized with clear test class names per category.
5. The reference generation script is a nice-to-have convenience. Do not block on it.

## Estimated Complexity
Medium-Large. The bulk of the work is writing 50+ fixture files (tedious but straightforward) and the parametrized test infrastructure. The comparison utilities build on existing code in `tests/comparison.py`.
