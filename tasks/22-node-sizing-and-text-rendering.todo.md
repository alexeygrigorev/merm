# Task 22: Fix Node Sizing and Text Rendering

## Problem

Nodes in pymermaid are dramatically oversized compared to mermaid.js reference output. This is the single most pervasive issue across all comparisons. Nodes appear roughly 2-3x larger than the mermaid.js reference, with excessive internal padding. Additionally, text labels are missing from the mmdc reference renders (suggesting a font/rendering issue in the comparison pipeline), but in the pymermaid output the nodes themselves are simply too big relative to the text they contain.

### Specific Observations

1. **Nodes are too large**: In `basic/single_node`, pymermaid renders "Hello" in a node that occupies nearly the entire 800px canvas. The mermaid.js reference shows a much more compact node with reasonable padding around the text.

2. **Excessive padding**: In `basic/two_nodes`, both A and B nodes are roughly 200x200px each when they should be roughly 70x45px (mermaid.js scale). The text-to-node-area ratio is far too low.

3. **Disproportional scaling**: In `basic/linear_chain` (A->B->C->D->E), the pymermaid output is extremely tall and narrow because each oversized node stacks vertically with large gaps. The mermaid.js reference is much more compact.

4. **Long text nodes too tall**: In `text/long_text`, the pymermaid output shows correct-width nodes with visible text, but the mermaid.js reference nodes (without text) appear to be wide and short. Pymermaid nodes have too much vertical padding for long single-line text.

5. **Single-character labels get square nodes**: Nodes with labels like "A", "B" should be wider than tall (landscape rectangle), matching mermaid.js. Currently they appear nearly square or taller than wide.

### Affected Comparisons

Every single comparison is affected. The oversized nodes reduce SSIM scores across the board because the spatial layout and proportions differ fundamentally. Fixing this alone would likely improve 50+ comparisons.

### Root Cause

The text measurement heuristic and/or node padding constants produce nodes that are far too large. The node sizing formula needs to be calibrated against mermaid.js reference dimensions.

## Acceptance Criteria

- [ ] A simple rectangle node with a short label (e.g., "A") has dimensions within 30% of the mermaid.js reference (~68x44 px at default scale)
- [ ] Node padding (space between text and border) matches mermaid.js defaults (~8px horizontal, ~8px vertical)
- [ ] Long single-line text nodes are wide and short, not wide and tall
- [ ] The `basic/single_node` SSIM score improves from 0.63 to at least 0.75
- [ ] The `basic/two_nodes` SSIM score improves from 0.68 to at least 0.78
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: Node dimension calculation
- Verify node with label "A" produces width ~68px and height ~44px
- Verify node with label "Hello World" produces proportionally wider node
- Verify padding constants match mermaid.js defaults

### Visual: Before/after comparison
- Re-render `basic/single_node` and compare to mmdc reference
- Re-render `basic/two_nodes` and compare
- Re-render `text/long_text` and compare

## Dependencies

None (this is the highest-impact standalone fix).

## Estimated Impact

**Very High** -- affects all 53 comparison cases. This is the foundation fix that will improve every SSIM score.
