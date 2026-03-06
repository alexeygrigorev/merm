# Task 29: Reduce Inter-Layer and Inter-Node Spacing to Match Mermaid.js

## Problem

The vertical spacing between layers (ranks) and horizontal spacing between nodes in the same layer is too large in pymermaid, producing diagrams that are much taller and narrower than the mermaid.js reference.

### Specific Observations

1. **`basic/linear_chain`** (SSIM 0.71): Pymermaid renders A->B->C->D->E as a very tall, narrow column. The vertical gap between each pair of nodes is approximately 100-120px. In mermaid.js, the gap is approximately 40-50px. The pymermaid output is roughly 2x taller than the reference.

2. **`scale/medium`** (SSIM 0.84 -- our best): Even in our best case, the pymermaid diagram is noticeably more spread out vertically. The diamond pattern (A->B,C->D,E,...) fans out wider and the lower linear chain (J->K->...->O) has larger gaps.

3. **Consistent pattern**: Across all TD/TB diagrams, the inter-layer gap is roughly 2x what mermaid.js uses. This makes every diagram taller than it should be.

### Root Cause

The layout constants for `rank_separation` (vertical distance between layers) and `node_separation` (horizontal distance between nodes in the same layer) are set too high. These need to be calibrated to match mermaid.js defaults:
- mermaid.js default rankSpacing: ~50px
- mermaid.js default nodeSpacing: ~50px

## Acceptance Criteria

- [ ] Vertical gap between layers (rank separation) is approximately 50px (matching mermaid.js)
- [ ] Horizontal gap between sibling nodes (node separation) is approximately 50px
- [ ] The overall aspect ratio of rendered diagrams approximately matches mermaid.js
- [ ] The `basic/linear_chain` SSIM improves from 0.71 to at least 0.80
- [ ] The `scale/medium` SSIM improves from 0.84 to at least 0.88
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: Spacing constants
- Verify rank_separation default is ~50
- Verify node_separation default is ~50

### Unit: Layout output coordinates
- For a linear chain A->B->C (TD), verify B.y - A.y - A.height is approximately 50
- For a fan-out A->B, A->C (TD), verify abs(B.x - C.x) is proportional to node width + 50

### Visual: spacing comparison
- Re-render `basic/linear_chain` and compare vertical compactness to mermaid.js
- Re-render `scale/medium` and verify closer match

## Dependencies

- Task 22 (node sizing) -- spacing is relative to node size, so fix node size first

## Estimated Impact

**High** -- affects all 53 comparison cases. Reducing spacing to match mermaid.js will improve every SSIM score, especially for simple linear/chain diagrams.
