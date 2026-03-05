# Task 31: SVG Emoji Support

**Priority: Low**

## Description

Add emoji shortcode support (`:smile:` → inline SVG emoji) so emojis render identically across all platforms. Uses SVG path data from an open-source emoji library (e.g., Twemoji), similar to how Font Awesome icons work.

## Approach

1. Choose emoji SVG library (Twemoji, Noto Emoji, or OpenMoji)
2. Extract SVG paths into an `emojis.py` registry (like `icons.py`)
3. Parse `:shortcode:` syntax in labels
4. Render as inline SVG `<path>` elements

## Open Questions

- Which emoji SVG library? Twemoji is most popular, MIT-licensed
- Full set (~3,600) or curated subset?
- Shortcode format: GitHub-style `:smile:` or other?

## Dependencies

- Task 20 (Font Awesome icons) — same rendering pattern
