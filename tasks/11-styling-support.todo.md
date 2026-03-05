# 11 - Styling Support

## Goal
Implement CSS-like styling for nodes and edges: inline styles, class definitions, and the default theme.

## Tasks

### Default Theme
- [ ] Implement mermaid's default theme colors:
  - Node fills cycle through: `#f9f9f9`, `#ffe0b2`, `#c8e6c9`, `#bbdefb`, `#f8bbd0`, `#d1c4e9`, etc.
  - Node stroke: `#333`
  - Text color: `#333`
  - Edge color: `#333`
  - Subgraph fill: `#eee` with `#bbb` stroke
- [ ] Support theme selection (default, dark, forest, neutral) - start with default only

### Style Application
- [ ] Parse `style nodeId fill:#f9f,stroke:#333,stroke-width:4px`
- [ ] Apply inline styles as SVG `style` attribute on node elements
- [ ] Parse `classDef className fill:#f9f,stroke:#333`
- [ ] Apply classes via `class="className"` on SVG elements, with `<style>` block in `<defs>`
- [ ] Support `classDef default` for default node styling
- [ ] Handle `:::className` inline syntax on node declarations

### CSS Properties Mapping
Map mermaid style properties to SVG attributes:
- `fill` -> `fill`
- `stroke` -> `stroke`
- `stroke-width` -> `stroke-width`
- `color` -> text `fill`
- `font-size` -> `font-size`
- `stroke-dasharray` -> `stroke-dasharray`

## Acceptance Criteria
- Styled diagrams match mermaid-cli output colors
- Multiple classes on same node work
- Default theme produces recognizable mermaid-style output

## Dependencies
- Task 04 (parser extracts styles)
- Task 07 (renderer applies styles)

## Estimated Complexity
Small-Medium - mostly plumbing style data through the pipeline.
