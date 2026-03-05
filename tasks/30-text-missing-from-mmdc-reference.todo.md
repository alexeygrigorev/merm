# Task 30: Fix Missing Text in mmdc Reference Renders (Comparison Pipeline Issue)

## Problem

The mermaid.js (mmdc) reference PNG renders are missing all text labels -- nodes appear as empty colored rectangles. This is a comparison pipeline issue, not a pymermaid rendering issue, but it degrades SSIM scores across the board and makes visual comparison unreliable.

### Specific Observations

1. **Every mmdc reference image** shows nodes without any text labels. For example:
   - `basic/single_node`: mmdc shows an empty purple rectangle; pymermaid shows "Hello"
   - `basic/two_nodes`: mmdc shows two empty rectangles; pymermaid shows "A" and "B"
   - `edges/labeled_edges`: mmdc shows nodes without labels and edges without label text
   - `shapes/diamond`: mmdc shows diamond shapes without "Diamond" or "Another" text

2. This artificially depresses SSIM scores because text pixels are present in pymermaid but absent in mmdc, creating differences in every node region.

3. Edge labels are also missing from mmdc references (no "yes", "no", "long label" etc. in `edges/labeled_edges`).

### Root Cause

The mmdc rendering pipeline likely does not have access to the required fonts when running in headless/Puppeteer mode, or the SVG-to-PNG conversion step strips text elements. This could be:
- Missing system fonts in the Docker/headless environment
- A `--pdfFit` or `--scale` option causing text to not render
- The SVG using web fonts that are not available during PNG conversion

## Acceptance Criteria

- [ ] mmdc reference renders include visible text labels in all nodes
- [ ] mmdc reference renders include visible edge labels
- [ ] Subgraph titles are visible in mmdc reference renders
- [ ] Re-running the comparison pipeline produces PNGs with text for both pymermaid and mmdc
- [ ] SSIM scores after fixing this pipeline issue reflect actual layout/styling differences, not text-vs-no-text differences

## Test Scenarios

### Integration: Reference render pipeline
- Render `basic/single_node` with mmdc and verify "Hello" appears in the PNG
- Render `edges/labeled_edges` with mmdc and verify "yes", "no", "long label" appear
- Render `subgraphs/subgraph_with_title` with mmdc and verify "Database Layer" appears

### Pipeline: Font availability
- Verify the font used by mermaid.js (typically "trebuchet ms" or a sans-serif fallback) is available in the rendering environment

## Dependencies

None -- this is independent of pymermaid code changes.

## Estimated Impact

**Very High** -- fixes a systematic measurement error that affects all 53 comparisons. Without this fix, SSIM scores are artificially low and visual inspection of mmdc references is unreliable. After this fix, SSIM scores will more accurately reflect true layout and styling differences.
