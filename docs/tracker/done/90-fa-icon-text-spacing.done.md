# Issue 90: Font Awesome icon too close to text in nodes

## Problem

When a node has a Font Awesome icon (e.g., `fa:fa-car Drive to Grandma`), the icon is rendered too close to the text -- they touch or overlap. There should be a small gap between the icon and the label text.

Reproduction: Christmas tree flowchart in README.

## Root Cause

In `src/merm/render/svg.py` (`_render_text_with_icons`), the icon segment width is calculated as `font_size * 1.5 + 5.0`, where the 5px is intended as a trailing gap. However, the icon `<g>` element is placed at `x_pos` and scaled from its viewBox dimensions. The actual rendered icon path may fill the full viewBox width, consuming the gap visually. The text segment that follows starts immediately after the icon segment's allocated width, leaving insufficient visible space.

## Dependencies

None.

## Acceptance Criteria

- [ ] A visible gap of at least 4px exists between the right edge of any FA icon and the left edge of the following text
- [ ] A visible gap of at least 4px exists between the right edge of text and the left edge of a following FA icon (icon after text)
- [ ] The icon+text combination remains visually centered within the node
- [ ] Node width accounts for the gap so icon/text are not clipped by the node border
- [ ] Existing tests continue to pass (`uv run pytest`)
- [ ] Render a flowchart with `fa:fa-car Drive` to PNG with cairosvg and visually verify the gap between icon and text is visible and consistent

## PNG Verification Checklist

- [ ] Render `graph TD; A[fa:fa-car Drive to Grandma]; B[fa:fa-home Home]; C[Visit fa:fa-gift gifts]` to SVG, then convert to PNG with cairosvg
- [ ] Visually verify in the PNG that each icon has a clear gap separating it from adjacent text
- [ ] Verify the icon+text is centered within the node shape (not shifted left or right)
- [ ] Compare before/after PNGs to confirm the fix improves spacing without breaking layout

## Test Scenarios

### Unit: Icon segment width includes gap
- Parse a label `fa:fa-car Drive` into segments; verify the icon segment's allocated width includes explicit gap pixels beyond the icon's visual width
- Verify that the gap constant is at least 4px

### Unit: Icon positioning leaves gap
- Render a label with icon followed by text; measure the x-position of the icon's right edge and the text segment's left edge; verify there is a gap of at least 4px between them
- Render a label with text followed by icon; verify the same gap exists

### Integration: Full node rendering
- Render a flowchart containing `A[fa:fa-car Drive]` to SVG
- Parse the SVG and verify the `<g class="fa-icon">` transform x-position plus scaled icon width is at least 4px less than the `<text>` element's x-position minus half its width

### Visual: PNG verification
- Render a flowchart with multiple icon+text nodes to PNG using cairosvg
- Visually confirm icons do not touch or overlap with adjacent text
