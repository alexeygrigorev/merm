# 18 - SVG Visual Quality Improvements

## Goal
Make the rendered SVG output look like mermaid.js, NOT like Graphviz/dot. Currently our output has that classic "Graphviz grey boxes" look — we need mermaid's modern, polished aesthetic with its signature purple/yellow color scheme and generous spacing.

## Approach: Study mermaid.js Source
Before implementing, study the actual mermaid.js source code to understand exactly how they style things:
- **Theme system**: `src/themes/` in mermaid repo — extract exact color values from the default theme
- **Node rendering**: `src/diagrams/flowchart/` — understand padding, sizing, border-radius
- **Edge rendering**: `src/utils/` — understand path generation, arrow sizing
- **Text styling**: font stacks, sizes, weights used in different contexts
- **Subgraph styling**: background colors, borders, title placement

This ensures we match mermaid's look precisely rather than guessing values.

## Problems to Fix

### Colors and Theme (study mermaid's `themes/theme-default.js`)
- [ ] Node fill should use mermaid's default: `#ECECFF` (light purple) instead of `#f9f9f9` (grey)
- [ ] Node stroke should use `#9370DB` (medium purple) instead of `#333`
- [ ] Edge stroke should use `#333333` with `stroke-width: 2px` (currently 1px feels thin)
- [ ] Edge label background should use `rgba(232,232,232,0.8)` instead of solid white
- [ ] Font family should be `"trebuchet ms", verdana, arial, sans-serif` (mermaid's default)
- [ ] Font size should be 16px for nodes (currently 14px)
- [ ] Subgraph fill should use `#ffffde` (light yellow) with `#aaaa33` stroke

### Node Sizing and Spacing (study mermaid's node renderers)
- [ ] Nodes are too tight around text -- increase default padding (currently 8px h, 4px v -> try 15px h, 10px v)
- [ ] Node height feels cramped (30px) -- should be at least 54px like mermaid
- [ ] Rounded rectangles need visible `rx` value (mermaid uses ~5px)
- [ ] Diamond shape needs to be sized proportionally to text (wider than a rect)

### Edge Routing (study mermaid's edge path generation)
- [ ] Enable smooth Bezier curves by default for multi-segment edges
- [ ] Edge paths should start/end at node boundaries using shape-aware connection points (currently uses rect approximation for all shapes)
- [ ] Arrow markers should use `markerUnits="userSpaceOnUse"` with `markerWidth="8" markerHeight="8"` for consistent sizing

### Layout Spacing
- [ ] Increase default `rank_sep` from 50 to 80 (more vertical breathing room)
- [ ] Increase default `node_sep` from 30 to 50 (more horizontal spacing)
- [ ] Center the diagram better in the viewBox

### Polish
- [ ] Round coordinate values to 2 decimal places (avoid `188.98125000000001` in output)
- [ ] Add `font-family` directly on text elements (not just in CSS) for standalone SVG viewing
- [ ] Add white background to SVG (`style="background-color: white"` on root)

## Acceptance Criteria
- [ ] Side-by-side comparison with mmdc output shows noticeably closer visual match
- [ ] Output looks distinctly like mermaid.js, NOT like Graphviz/dot
- [ ] Default theme colors match mermaid default (purple nodes, yellow subgraphs)
- [ ] Nodes have comfortable padding around text
- [ ] Edges use Bezier curves for multi-segment paths
- [ ] Coordinate values are rounded (no long floating point strings)
- [ ] All existing tests pass (update expected values as needed)
- [ ] Regenerate `docs/demo.svg` with improved output

## Theme Extensibility (Design for the Future)
While implementing the default mermaid theme, architect the styling system for extensibility:
- [ ] Create a `Theme` dataclass/class that holds all color/sizing values
- [ ] Default theme = mermaid's default (purple nodes, yellow subgraphs)
- [ ] Theme is passed through the render pipeline (not hardcoded in CSS strings)
- [ ] Easy to add new themes later (dark, forest, neutral — matching mermaid's built-in themes)
- [ ] CLI could accept `--theme` flag in the future (don't implement yet, just ensure the architecture supports it)

This means: extract ALL magic color/size values into a single Theme object. The renderer reads from the theme, not from hardcoded strings scattered across files.

## Dependencies
- Tasks 11 and 12 must be done (styling + CLI) ✅

## Estimated Complexity
Medium-Large -- many tweaks across measure, layout, and render modules, plus the theme abstraction. The key is studying mermaid.js source first to get exact values rather than guessing.
