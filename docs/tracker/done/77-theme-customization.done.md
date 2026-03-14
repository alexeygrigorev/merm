# Issue 77: Theme customization

## Problem

Theme customization is limited. The `Theme` dataclass exists and is already threaded through
all renderers, but there is only one built-in theme (`DEFAULT_THEME`). Users cannot select
a theme by name, and the public API functions (`render_diagram`, `render_to_file`,
`render_to_png`) do not accept a `theme` parameter. The CLI has no `--theme` flag. The
mermaid `%%{init: {'theme': '...'}}%%` directive in diagram source is not parsed.

## Scope

### 1. Built-in theme definitions (in `src/merm/theme.py`)

Add four named themes as `Theme` instances:

- **default** -- the current `DEFAULT_THEME` (purple nodes `#ECECFF`/`#9370DB`, white background)
- **dark** -- dark background (`#1f2020`), light text (`#ccc`), blue-ish nodes (`#1f2937`/`#4a6785`)
- **forest** -- green-tinted nodes (`#cde498`/`#13540c`), white background, dark green edges
- **neutral** -- grey-scale nodes (`#eee`/`#999`), white background, `#333` edges

Add a `THEMES: dict[str, Theme]` lookup mapping name strings to instances.

Add a `get_theme(name: str) -> Theme` function that returns the matching theme or raises
`ValueError` for unknown names.

### 2. Thread `theme` through the public API (`src/merm/__init__.py`)

- `render_diagram(source, *, theme=None)` -- accepts `Theme | str | None`
  - `str` is resolved via `get_theme(name)`
  - `None` means auto-detect from `%%{init}%%` directive, falling back to `DEFAULT_THEME`
- `render_to_file(source, path, *, theme=None)` -- same parameter, passes through
- `render_to_png(source, *, theme=None)` -- same parameter, passes through

Currently `render_diagram` calls per-type renderers but never passes `theme`. After this
change it must pass the resolved `Theme` instance to every renderer that accepts one.

### 3. Parse `%%{init: {'theme': '...'}}%%` directive

Before diagram-type detection in `render_diagram`, scan the source for the init directive.
Extract the theme name. If a `theme` keyword argument was also provided, the explicit
argument takes precedence over the directive.

Supported directive formats (matching mermaid.js):
- `%%{init: {'theme': 'dark'}}%%`
- `%%{init: {"theme": "dark"}}%%`
- `%%{ init: { "theme": "forest" } }%%`

Strip the directive line from source before passing to the parser (parsers may choke on it).

### 4. CLI `--theme` flag (`src/merm/cli.py`)

Add `--theme` argument with choices `["default", "dark", "forest", "neutral"]`.
Pass the resolved theme to `render_diagram(source, theme=theme_name)`.

### 5. No changes needed to per-type renderers

All renderers (`render_svg`, `render_sequence_svg`, `render_class_diagram`,
`render_state_svg`, `render_er_diagram`, `render_pie_svg`, `render_mindmap_svg`,
`render_gantt_svg`, `render_gitgraph_svg`) already accept `theme: Theme | None = None`.
The only change is that `render_diagram` must actually pass the theme through.

Note: `render_gitgraph_svg` currently does NOT accept a theme parameter. The engineer
should add `theme: Theme | None = None` to its signature if needed, or skip it if the
effort is disproportionate (document the gap).

## Dependencies

- None. Issue 75 (CLI) and 76 (API improvements) are already done.

## Acceptance Criteria

- [ ] `from merm.theme import THEMES, get_theme` works
- [ ] `THEMES` is a `dict[str, Theme]` with keys `"default"`, `"dark"`, `"forest"`, `"neutral"`
- [ ] `get_theme("dark")` returns a `Theme` instance with dark-appropriate colors
- [ ] `get_theme("nonexistent")` raises `ValueError`
- [ ] `render_diagram(source, theme="dark")` produces SVG with dark theme colors
- [ ] `render_diagram(source, theme=Theme(node_fill="#ff0000"))` works with a `Theme` instance
- [ ] `render_diagram(source)` with `%%{init: {'theme': 'forest'}}%%` in source uses forest theme
- [ ] Explicit `theme=` argument overrides `%%{init}%%` directive in source
- [ ] The `%%{init}%%` line is stripped from source before parsing (does not cause parse error)
- [ ] `render_to_file(source, path, theme="dark")` passes theme through
- [ ] `render_to_png(source, theme="dark")` passes theme through
- [ ] CLI: `merm --theme dark input.mmd -o output.svg` uses dark theme
- [ ] CLI: `--theme` accepts only valid theme names (default, dark, forest, neutral)
- [ ] Each built-in theme produces visually distinct SVG output (different node fill, stroke, background, text colors)
- [ ] Render all 4 themes to PNG with cairosvg and visually verify they look correct (not just structurally different -- actually visually distinct and readable)
- [ ] `uv run pytest` passes with all new and existing tests

## Test Scenarios

### Unit: Theme definitions (`tests/test_theme.py` -- extend existing)

- `get_theme("default")` returns `DEFAULT_THEME`
- `get_theme("dark")` returns a Theme with dark background color (not "white")
- `get_theme("forest")` returns a Theme with green-ish node colors
- `get_theme("neutral")` returns a Theme with grey-ish node colors
- `get_theme("DARK")` raises ValueError (case-sensitive)
- `get_theme("")` raises ValueError
- `THEMES` has exactly 4 keys
- All themes are frozen `Theme` instances (cannot be mutated)
- Each theme has a distinct `node_fill` value (no two themes share the same)

### Unit: Directive parsing

- Source with `%%{init: {'theme': 'dark'}}%%` extracts theme name `"dark"`
- Source with `%%{init: {"theme": "forest"}}%%` extracts `"forest"`
- Source with extra whitespace `%%{ init: { "theme": "neutral" } }%%` extracts `"neutral"`
- Source with no directive returns `None`
- Source with unknown theme in directive returns the name (let `get_theme` handle the error)
- Directive line is stripped from the returned source text
- Directive on first line, middle line, or with leading whitespace all work

### Integration: render_diagram with theme

- `render_diagram("graph TD\n A-->B", theme="dark")` produces SVG containing dark background color
- `render_diagram("graph TD\n A-->B", theme="default")` produces SVG matching default theme
- `render_diagram("graph TD\n A-->B", theme=Theme(node_fill="#abc"))` produces SVG with `#abc`
- `render_diagram("%%{init: {'theme': 'forest'}}%%\ngraph TD\n A-->B")` uses forest colors
- `render_diagram("%%{init: {'theme': 'dark'}}%%\ngraph TD\n A-->B", theme="neutral")` uses neutral (explicit wins)
- `render_diagram("graph TD\n A-->B", theme="bogus")` raises ValueError

### Integration: render_to_file and render_to_png with theme

- `render_to_file(source, tmp_path / "out.svg", theme="dark")` writes SVG with dark colors
- `render_to_png(source, theme="dark")` returns PNG bytes (non-empty, starts with PNG magic)

### Integration: CLI --theme flag

- `merm --theme dark` is accepted (no argparse error)
- `merm --theme invalid` exits with error code 2
- `merm --theme dark -o out.svg` produces SVG with dark theme colors in the file
- `merm --help` shows `--theme` in help text

### Visual: PNG rendering of all themes

- For a simple flowchart `graph TD\n A[Start] --> B[End]`, render with each of the 4 themes
- Convert each SVG to PNG with cairosvg
- Verify PNGs are non-empty and have distinct file sizes (different colors = different bytes)
- Visually inspect that dark theme has a dark background, forest has green nodes, etc.
