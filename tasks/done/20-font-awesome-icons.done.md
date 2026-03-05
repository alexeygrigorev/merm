# 20 - Font Awesome Icon Support

## Goal
Support mermaid's `fa:fa-icon-name` syntax by rendering actual icons in SVG instead of showing raw text like "fa:fa-car Car".

## Approach
Bundle Font Awesome Free SVG path data for the most common icons. When `fa:fa-icon-name` is found in node labels, replace it with an inline SVG icon element. Unknown icons fall back to showing the icon name as text.

## Implementation Plan

### 1. Icon Registry (`src/pymermaid/icons.py`)
- Dict mapping FA icon names to SVG path data strings
- Include ~100 most commonly used Font Awesome Free Solid icons
- Source paths from Font Awesome Free SVG files (MIT licensed)
- Each entry: `{"car": "M135.2 117.4L..."}`  (just the `d` attribute of the `<path>`)
- FA icons use a 512x512 or 640x512 viewBox — store viewBox width per icon
- `get_icon_path(name: str) -> tuple[str, int, int] | None` — returns (path_d, width, height) or None

### 2. Label Parser Updates
- In node label processing (during rendering), detect `fa:fa-*` tokens
- Split label into segments: text and icon references
- Handle: `fa:fa-car` (icon only), `fa:fa-car Car` (icon + text), `Car fa:fa-car` (text + icon)

### 3. Renderer Updates (`src/pymermaid/render/svg.py`)
- When rendering node text, check for `fa:fa-*` tokens
- For each icon token, insert an SVG `<g>` with a scaled `<path>` element
- Scale icon to match font size (e.g., 16px font → 16x16 icon)
- Position icon inline with text (icon takes the place of the fa:fa-* token)
- Use theme text color for icon fill

### 4. Text Measurement Updates (`src/pymermaid/measure/text.py`)
- When measuring text containing `fa:fa-*`, treat each icon as a square character (width = font_size)
- Strip the `fa:fa-name` token from text width calculation, add icon_width instead

## Icon List (starter set — most common FA Solid icons)
Include at minimum: car, home, user, check, times, star, heart, bell, search, cog, trash, edit, save, plus, minus, arrow-right, arrow-left, arrow-up, arrow-down, envelope, phone, lock, unlock, camera, image, file, folder, download, upload, cloud, database, server, code, terminal, bug, wrench, tools, chart-bar, chart-line, globe, map-marker, clock, calendar, comment, share, link, wifi, bolt, fire, shield, flag, tag, bookmark, thumbs-up, thumbs-down, eye, eye-slash, ban, exclamation-triangle, info-circle, question-circle, check-circle, times-circle, spinner

## Acceptance Criteria
- [ ] `fa:fa-car Car` renders a car icon SVG path next to "Car" text
- [ ] Icon scales to match font size
- [ ] Icon uses theme text color
- [ ] Icon-only labels work (`fa:fa-car`)
- [ ] Text+icon combinations work in any order
- [ ] Unknown icons show the name as text (e.g., `fa:fa-unknown` → "unknown")
- [ ] Text measurement accounts for icon width
- [ ] Node sizing accommodates icon + text
- [ ] Works in all diagram types (flowchart at minimum, others as bonus)
- [ ] 15+ tests
- [ ] All existing 1099 tests still pass
- [ ] Lint passes

## Dependencies
- All core tasks complete ✅

## Estimated Complexity
Medium — icon registry is tedious but mechanical. Rendering integration requires careful positioning.
