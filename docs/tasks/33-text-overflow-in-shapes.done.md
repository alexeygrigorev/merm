# Task 33: Fix Text Overflow in Non-Rectangular Shapes

## Problem

Text in diamond `{}`, hexagon `{{}}`, and other non-rectangular shapes can overflow outside the shape boundary. The layout engine computes node dimensions in `sugiyama.py` (lines ~1006-1022) but does not fully account for the geometry of these shapes -- a diamond's inscribed text rectangle is much smaller than its bounding box, and a hexagon loses usable width to its angled sides.

### Current State (verified by rendering)

- **Diamond**: For wrapped multi-line text (e.g., "Out of beans or water?"), the text fits but is very tight against the diagonal edges. For longer single-line text the text can protrude past the diamond boundary. The current extra padding is `+20` horizontal and `+20` vertical beyond the base rectangle padding, but a diamond needs its width/height to be roughly `sqrt(2)` times the inscribed text rectangle dimensions.
- **Hexagon**: Text wraps correctly but the top/bottom lines can extend past the angled side boundaries. The current sizing adds `+20` horizontal padding but the hexagon renderer uses `w/4` inset, meaning 50% of the width is lost to the angles.
- **Circle**: Oversized for short text like "Start processing" -- the circle is much larger than needed. The sizing uses `max(tw, th)` which causes asymmetric text to create huge circles.
- **Parallelogram/Trapezoid**: The 15% skew/inset eats into usable text width. Currently uses the default rectangle sizing with no extra padding for the skewed geometry.
- **Rounded rect / Stadium**: Generally acceptable. Text is contained.

### Root Cause

The shape sizing logic in `src/pymermaid/layout/sugiyama.py` (function around line 985) uses ad-hoc padding additions rather than computing the actual inscribed text rectangle for each shape geometry. The shape renderers in `src/pymermaid/render/shapes.py` define the polygon vertices but the layout code does not reference these geometric constraints.

### Key Code Locations

- **Layout sizing**: `src/pymermaid/layout/sugiyama.py` lines 998-1029 (per-shape size computation)
- **Shape renderers**: `src/pymermaid/render/shapes.py` (vertex definitions for diamond, hexagon, parallelogram, trapezoid)
- **Text measurement**: `src/pymermaid/measure/text.py` (`_line_width`, `_wrap_line`, `TextMeasurer.measure`)
- **Text rendering**: `src/pymermaid/render/svg.py` (`_render_text`, `_render_node`)

## Acceptance Criteria

- [ ] For every non-rectangular shape (diamond, hexagon, circle, double_circle, parallelogram, parallelogram_alt, trapezoid, trapezoid_alt, asymmetric, stadium), rendered text is fully contained within the shape boundary with visible padding
- [ ] Diamond `{text}` with text "Out of beans or water?" (wrapped to 2 lines): all text pixels fall inside the diamond polygon
- [ ] Diamond `{text}` with text "OK?" (short, single line): text is centered and diamond is not excessively oversized
- [ ] Hexagon `{{text}}` with text "Process incoming data packets" (wrapped): text does not extend past the angled side edges
- [ ] Circle `((text))` with text "Start processing": circle radius is proportional to the text, not wildly oversized
- [ ] Parallelogram `[/text/]` with text "Input user credentials": text does not extend past the skewed edges
- [ ] Trapezoid `[/text\]` with text "Manual verification step": text does not extend past the narrower top edge
- [ ] The `tests/fixtures/github/coffee_machine.mmd` diagram renders with all text contained in all shapes (diamonds, rounded rects)
- [ ] Text remains horizontally and vertically centered within every shape
- [ ] `uv run pytest` passes with no regressions
- [ ] PNG verification: at least 3 rendered PNGs are checked (diamond long text, hexagon long text, coffee machine) to confirm visual correctness

## Test Scenarios

### Unit: Diamond text containment
- Diamond with short text ("Yes?") -- text fits inside with visible padding
- Diamond with medium text ("Is it working?") -- text fits inside
- Diamond with long text ("Out of beans or water?") -- text wraps and fits inside diamond boundary
- Diamond with very long text ("Is the system fully operational and ready?") -- text wraps, diamond expands, all text inside

### Unit: Hexagon text containment
- Hexagon with short text ("OK") -- text fits, hexagon not oversized
- Hexagon with long text ("Process incoming data packets") -- text wraps and fits within the angled sides

### Unit: Circle sizing
- Circle with short text ("End") -- circle is compact, not oversized
- Circle with medium text ("Start processing") -- circle sized appropriately (not 3x the text area)

### Unit: Parallelogram / Trapezoid text containment
- Parallelogram with text "Input user credentials" -- text inside skewed boundary
- Trapezoid with text "Manual verification step" -- text inside narrower top edge

### Integration: SVG text-inside-shape verification
- For each non-rectangular shape, render an SVG with a known label, parse the SVG, extract the shape polygon/circle coordinates and the text bounding box (estimated from text x,y and measured width), and verify the text bbox is fully inscribed within the shape boundary
- This can be done by computing the inscribed rectangle of the shape polygon and asserting the text measurement fits within it

### Integration: Coffee machine diagram
- Render `tests/fixtures/github/coffee_machine.mmd` to SVG and PNG
- Verify all diamond nodes ("Machine has power?", "Out of beans or water?", "Filter warning?") have text inside shape boundaries
- Verify all rounded nodes ("Coffee machine not working", etc.) have text inside shape boundaries

### PNG verification (mandatory for rendering tasks)
- Render diamond with "Out of beans or water?" to PNG, visually confirm containment
- Render hexagon with "Process incoming data packets" to PNG, visually confirm containment
- Render coffee_machine.mmd to PNG, visually confirm all shapes contain their text

## Implementation Hints

1. **Diamond**: The inscribed rectangle of a diamond with half-width `a` and half-height `b` has width `a` and height `b` (the rectangle whose corners touch the midpoints of the diamond sides). So for text of size `(tw, th)`, the diamond needs `w = 2*tw + padding` and `h = 2*th + padding`. The current `+20` is insufficient; the multiplier should be closer to 2x the text dimension.

2. **Hexagon**: The `HexagonRenderer` uses `inset = w/4`, meaning 25% of width is lost on each side. Effective text width is `w/2`. So for text width `tw`, the hexagon needs `w = 2*tw + padding`.

3. **Parallelogram/Trapezoid**: The skew of 15% means effective text width is `w * (1 - 2*0.15) = w * 0.7`. So for text width `tw`, the shape needs `w = tw/0.7 + padding`.

4. **Circle**: Consider using `sqrt(tw^2 + th^2) / 2 + padding` for the radius rather than `max(tw, th) / 2 + padding`, which would be tighter while still containing the text.

## Dependencies

- No hard dependency on Task 32 (viewport clipping is about the SVG viewBox, not shape sizing)
- Depends on the existing layout and shape rendering infrastructure (tasks 06, 07, 08 -- all done)
