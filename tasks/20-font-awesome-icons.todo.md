# 20 - Font Awesome Icon Support

## Goal
Support mermaid's `fa:fa-icon-name` syntax by rendering actual icons in SVG instead of showing the raw text.

## Background
Mermaid.js supports Font Awesome icons in node labels using the `fa:fa-icon-name` syntax, e.g. `A[fa:fa-car Car]` renders a car icon next to the text "Car". Currently pymermaid passes through the literal string.

## Approach Options
1. **Embed FA SVG paths**: Bundle a subset of Font Awesome SVG path data (the free/solid set). When `fa:fa-name` is encountered, replace it with an inline `<svg>` or `<use>` referencing the path data.
2. **Use Font Awesome webfont**: Reference the FA font in CSS and use Unicode codepoints. Only works if the viewer has the font installed.
3. **Strip prefix, show text only**: Minimal approach — just remove `fa:fa-` and show the icon name as text. Graceful degradation.

Recommended: Option 1 for commonly used icons, with option 3 as fallback for unknown icons.

## Tasks
- [ ] Parse `fa:fa-icon-name` tokens in node labels
- [ ] Build a lookup table of FA icon name -> SVG path data (free solid set, ~1000 icons)
- [ ] Render icon as inline SVG alongside text in node labels
- [ ] Size icon to match font size
- [ ] Handle icon-only labels (`fa:fa-car`) and icon+text (`fa:fa-car Car`)
- [ ] Fallback: unknown icons render as text with prefix stripped

## Acceptance Criteria
- [ ] `fa:fa-car Car` renders a car icon next to "Car" text
- [ ] Icon scales with font size
- [ ] Unknown icons degrade gracefully (show text, no crash)
- [ ] All existing tests still pass
- [ ] 10+ tests for icon parsing and rendering

## Dependencies
- Core rendering pipeline complete

## Estimated Complexity
Medium — main effort is building/bundling the icon lookup table.
