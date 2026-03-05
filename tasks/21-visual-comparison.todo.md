# 21 - Visual Comparison: Render and Compare Against mermaid.js

## Goal
Actually render our SVGs and mmdc reference SVGs side by side, compute visual similarity scores, and identify where our output diverges from mermaid.js. This was descoped from task 19 but shouldn't have been — structural checks alone don't tell us if the output *looks right*.

## Prerequisites
- mmdc works with `--no-sandbox` flag on this system
- 55 corpus fixtures already exist in `tests/fixtures/corpus/`
- `scripts/regenerate_corpus_references.sh` exists but needs `--no-sandbox`

## Implementation

### 1. Fix reference generation script
- Update `scripts/regenerate_corpus_references.sh` to use `--no-sandbox`
- Generate mmdc reference SVGs for all 55 corpus fixtures
- Store in `tests/reference/corpus/` mirroring the fixture directory structure

### 2. SVG-to-PNG conversion
- Use `cairosvg` (add as optional dev dependency) to convert SVGs to PNG
- Script: `scripts/render_comparison.py`
  - For each .mmd in corpus: render with pymermaid, render with mmdc
  - Convert both SVGs to PNG
  - Generate side-by-side comparison image
  - Store in `docs/comparisons/`

### 3. Visual similarity scoring
- SSIM (Structural Similarity Index) using PIL/scikit-image
- Pixel diff percentage
- Per-diagram scores + aggregate summary
- Output as markdown table and/or JSON

### 4. Human review gallery
- Generate `docs/comparison_gallery.html` showing all pairs side by side
- pymermaid on left, mmdc on right
- Score underneath each pair
- Sort by worst score first (focus attention on biggest gaps)

## Acceptance Criteria
- [ ] mmdc reference SVGs generated for all 55 corpus fixtures
- [ ] PNG rendering pipeline works (SVG -> PNG for both pymermaid and mmdc output)
- [ ] Side-by-side comparison images generated
- [ ] SSIM scores computed per diagram
- [ ] Summary report with scores
- [ ] HTML gallery for visual review
- [ ] I (Claude) have looked at the comparison images and identified specific issues

## Dependencies
- Task 19 (corpus fixtures) ✅
- mmdc with --no-sandbox ✅

## Estimated Complexity
Medium — mostly scripting, plus adding cairosvg dependency.
