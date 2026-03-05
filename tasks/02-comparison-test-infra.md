# 02 - Comparison Test Infrastructure

## Goal
Set up test fixtures and reference rendering infrastructure EARLY so every subsequent task can validate against mmdc output. Build the comparison harness before writing our own renderer.

## Tasks

### Reference Rendering Setup
- [ ] Script to install mermaid-cli: `npm install -g @mermaid-js/mermaid-cli`
- [ ] Script to render all test fixtures with mmdc:
  ```bash
  mmdc -i fixture.mmd -o reference.svg -t default --configFile config-deterministic.json
  ```
- [ ] Store reference SVGs in `tests/reference/` (committed to repo)
- [ ] Config for deterministic output (disable animations, fixed random seed)

### Test Fixtures
- [ ] Copy/create test fixtures from mermaid-cli's test-positive:
  - `flowchart1.mmd` through `flowchart4.mmd`
  - Additional hand-crafted fixtures for each feature
- [ ] Fixtures covering:
  - All node shapes
  - All edge types
  - Edge labels
  - Subgraphs (simple and nested)
  - Styling (classDef, inline)
  - Multiple directions (LR, TD, BT, RL)
  - CJK characters
  - Line breaks in labels

### Structural Comparison
- [ ] Parse both SVGs as XML
- [ ] Compare node count, edge count, label text
- [ ] Verify all nodes from input appear in output SVG
- [ ] Verify all edges connect correct nodes

### Visual Comparison (optional, nice-to-have)
- [ ] Rasterize both SVGs to PNG (using cairosvg or resvg)
- [ ] Compute pixel-level difference
- [ ] Report similarity percentage
- [ ] Threshold: >90% similarity for basic flowcharts

### pytest Integration
- [ ] Parametrized test that runs all fixtures
- [ ] `pytest -m comparison` marker for slow comparison tests
- [ ] Clear failure messages showing what differs

## Acceptance Criteria
- `pytest -m comparison` runs all fixtures and reports pass/fail
- Reference SVGs are committed and reproducible
- New fixtures can be added by dropping a `.mmd` file in the fixtures directory

## Dependencies
- Task 01 (project setup)
- Node.js + mermaid-cli (external, for generating references)

## Note
This task is intentionally early. The reference SVGs and comparison utilities are created BEFORE our renderer exists. As each rendering task (07-11) lands, the comparison tests start passing incrementally.

## Estimated Complexity
Medium - scripting and test infrastructure, not algorithmic.
