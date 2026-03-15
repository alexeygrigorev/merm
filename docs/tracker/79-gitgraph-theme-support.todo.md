# Issue 79: GitGraph theme support

## Problem

The `render_gitgraph_svg` function does not accept a `theme` parameter, so gitGraph diagrams ignore theme customization while all other diagram types support it.

## Scope

- Add `theme: Theme | None = None` parameter to `render_gitgraph_svg`
- Apply theme colors to branches, commits, tags, and text
- Wire up the theme parameter in `render_diagram()` for gitgraph type
