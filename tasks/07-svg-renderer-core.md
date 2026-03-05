# 07 - SVG Renderer Core

## Goal
Generate SVG XML output from positioned layout results. This is the final stage of the pipeline.

## Tasks

### SVG Document Structure
- [ ] Generate SVG root element with proper namespace, viewBox, dimensions
- [ ] Generate `<defs>` section for reusable elements:
  - Arrow markers (triangle, circle, cross)
  - CSS styles (from classDef)
- [ ] Generate `<style>` element for default styling (font, colors)
- [ ] Use mermaid-compatible default theme colors:
  - Node fill: `#f9f9f9` with `#333` stroke
  - Text: `#333`
  - Edge: `#333`
  - Background: `white` or `transparent`

### Node Rendering
- [ ] Render each node shape as SVG elements (detailed in Task 08)
- [ ] Position nodes at layout-computed coordinates
- [ ] Render text labels inside nodes:
  - Single line: centered `<text>` element
  - Multi-line: `<text>` with `<tspan>` elements
  - Handle `<br/>` line breaks
- [ ] Apply inline styles and CSS classes

### Edge Rendering
- [ ] Render edges as `<path>` elements (detailed in Task 09)
- [ ] Render edge labels as `<text>` positioned at path midpoint
- [ ] Apply edge styling (solid, dotted, thick)

### Subgraph Rendering
- [ ] Render subgraph background as rounded `<rect>`
- [ ] Render subgraph title as `<text>` at top
- [ ] Apply subgraph styling

### SVG Output
- [ ] `render_svg(diagram: Diagram, layout: LayoutResult) -> str`
- [ ] Pretty-print XML with proper indentation
- [ ] Minimal SVG (no unnecessary attributes or elements)
- [ ] Standalone SVG (embeddable in HTML without modifications)

## Acceptance Criteria
- Output is valid SVG (passes XML validation)
- SVG renders correctly in browsers and image viewers
- Output matches mermaid-cli structure (same element types, similar attribute names)
- File size comparable to mermaid-cli output

## Dependencies
- Task 03 (IR data model)
- Task 06 (layout results)

## Estimated Complexity
Medium - straightforward XML generation, but many details to get right.
