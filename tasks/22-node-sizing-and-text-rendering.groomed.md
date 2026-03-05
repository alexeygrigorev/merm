# Task 22: Calibrate Node Sizing to Match Mermaid.js

## Problem

Node dimensions and inter-node spacing in pymermaid are larger than the mermaid.js reference, producing diagrams that are taller, wider, and more spread out than expected. While tasks 32, 35, and 40 fixed text clipping, missing text, and text wrapping, the underlying sizing constants have not been calibrated against mermaid.js defaults.

### Current State (verified 2026-03-05)

The rendering pipeline works correctly -- text is visible, wrapped, and centered. The issue is purely about dimension constants being too generous:

1. **Node height too tall**: `_NODE_MIN_HEIGHT = 54.0` produces nodes for single-char labels like "A" that are 54px tall. Mermaid.js renders these at roughly 42-44px tall.

2. **Padding too large**: `_NODE_PADDING_H = 60.0` (30px each side) and `_NODE_PADDING_V = 30.0` (15px each side) are larger than mermaid.js defaults (approximately 16px horizontal each side, 8px vertical each side).

3. **Spacing too large**: `rank_sep = 50.0` and `node_sep = 50.0` in LayoutConfig create more vertical/horizontal spacing between nodes than mermaid.js, which uses roughly 40px rank_sep and 30px node_sep.

4. **Short labels get square-ish nodes**: A node with label "A" renders at 70x54 (almost square). Mermaid.js renders it at roughly 68x42 (wider than tall).

5. **Cascading effect on large diagrams**: The `scale/medium.mmd` (15 nodes) and `scale/large.mmd` (49 nodes) diagrams are significantly taller than necessary because the extra padding and spacing accumulate over many layers.

### Key Code Locations

- **Layout sizing constants**: `src/pymermaid/layout/sugiyama.py` lines 31-36 (`_NODE_PADDING_H`, `_NODE_PADDING_V`, `_NODE_MIN_HEIGHT`, `_NODE_MIN_WIDTH`)
- **Theme defaults**: `src/pymermaid/theme.py` (`node_padding_h`, `node_padding_v`, `node_min_height`, `node_min_width`, `rank_sep`, `node_sep`)
- **Layout config**: `src/pymermaid/layout/config.py` (`LayoutConfig.rank_sep`, `LayoutConfig.node_sep`)
- **Text measurer padding**: `src/pymermaid/measure/text.py` (`TextMeasurer.padding_h`, `TextMeasurer.padding_v`)

### What NOT to Change

- Text measurement character-width heuristics (these are working correctly)
- Text wrapping logic (fixed in task 40)
- Text rendering / tspan positioning (fixed in tasks 32/35)
- Non-rectangular shape sizing (diamonds, hexagons, circles -- that is task 33)

## Acceptance Criteria

- [ ] A rectangle node with label "A" renders with dimensions within 15% of 68x42 (mermaid.js reference for a minimal rect node)
- [ ] A rectangle node with label "Hello" renders with dimensions within 15% of 100x42 (mermaid.js reference)
- [ ] `_NODE_MIN_HEIGHT` is reduced from 54 to approximately 42 (matching mermaid.js)
- [ ] `_NODE_PADDING_H` is reduced from 60 to approximately 32 (16px each side, matching mermaid.js)
- [ ] `_NODE_PADDING_V` is reduced from 30 to approximately 16 (8px each side, matching mermaid.js)
- [ ] `rank_sep` default is reduced from 50 to approximately 40 (matching mermaid.js inter-layer gap)
- [ ] `node_sep` default is reduced from 50 to approximately 30 (matching mermaid.js intra-layer gap)
- [ ] Theme dataclass defaults are updated to match the new constants
- [ ] The `scale/medium.mmd` diagram (15 nodes) renders more compactly -- total height decreases by at least 20%
- [ ] The `scale/large.mmd` diagram (49 nodes) renders more compactly -- total height decreases by at least 20%
- [ ] Text remains centered and fully visible in all nodes after resizing
- [ ] `uv run pytest` passes with no regressions

### PNG Verification (mandatory)

- [ ] Render `basic/single_node` to PNG -- node is compact, text "Hello" centered, no excess whitespace
- [ ] Render `basic/two_nodes` to PNG -- both nodes are compact, arrow proportional
- [ ] Render `basic/linear_chain` to PNG -- chain is noticeably shorter than before
- [ ] Render `shapes/mixed_shapes` to PNG -- all shapes render with text centered
- [ ] Render `scale/medium` to PNG -- 15-node graph is compact
- [ ] Render `text/long_text` to PNG -- wrapped text still fits within nodes
- [ ] Render `text/short_text` to PNG -- "Hi" and "Go" nodes are small and compact

## Test Scenarios

### Unit: Node dimension calculation
- Render `graph TD\n    A` -- extract rect from SVG, verify width is in [58, 78] and height is in [36, 48]
- Render `graph TD\n    A[Hello]` -- verify width is in [85, 115] and height is in [36, 48]
- Render `graph TD\n    A[Hello World]` -- verify width scales proportionally with text length

### Unit: Layout spacing
- Render `graph TD\n    A --> B` -- measure vertical distance between bottom of A and top of B; verify it is in [35, 50] (not 50+)
- Render `graph TD\n    A --> B\n    A --> C` -- measure horizontal distance between B and C; verify it is in [25, 40]

### Unit: Theme constants are used
- Create a Theme with custom node_padding_h=10, render, verify nodes are narrower than default
- Verify that LayoutConfig picks up rank_sep and node_sep from Theme

### Integration: Compact layout regression
- Render `scale/large.mmd`, extract LayoutResult.height, verify it decreased relative to a known baseline (current height)
- Render `shapes/mixed_shapes.mmd`, verify all 6 nodes have text centered (cx of text within 2px of cx of shape)

### Integration: No text clipping after resize
- Render `text/long_text.mmd` to SVG, verify no text element has y-coordinate outside its node's rect bounds
- Render `text/multiline.mmd` to SVG, verify all tspan elements are within node bounds

## Dependencies

- Task 33 (text overflow in non-rectangular shapes) should be done AFTER this task, since it depends on the base padding values being calibrated first

## Estimated Impact

**High** -- affects every diagram. Reducing padding and spacing makes all diagrams more compact and closer to mermaid.js proportions. This is a foundational calibration task.
