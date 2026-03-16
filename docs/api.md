# merm API Reference

`merm` is a pure Python Mermaid diagram renderer. It converts Mermaid syntax
directly to SVG (and optionally PNG) without requiring Node.js, Puppeteer, or
any external service.

## Installation

```bash
pip install merm
# or
uv add merm
```

For PNG output support, also install cairosvg:

```bash
pip install cairosvg
# or
uv add cairosvg
```

---

## Quick Start

```python
from merm import render_diagram

svg = render_diagram("""
flowchart LR
    A[Start] --> B{Decision}
    B -->|Yes| C[OK]
    B -->|No| D[Fail]
""")

# Write to file
with open("diagram.svg", "w") as f:
    f.write(svg)
```

---

## Core Functions

### `render_diagram(source, *, theme=None) -> str`

The main entry point. Auto-detects the diagram type from the source text and
renders it to SVG.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `source` | `str` | *(required)* | Mermaid diagram source text |
| `theme` | `Theme \| str \| None` | `None` | Theme for styling. Can be a `Theme` instance, a theme name string (`"default"`, `"dark"`, `"forest"`, `"neutral"`), or `None` for auto-detection. |

**Returns:** `str` -- A string containing valid SVG XML.

**Raises:**
- `ValueError` -- If `source` is empty or whitespace-only.
- `ParseError` -- If the diagram source contains invalid syntax.

**Theme resolution order:**
1. Explicit `theme` argument (highest priority)
2. `%%{init: {'theme': '...'}}%%` directive in the source
3. Default theme (fallback)

**Example:**

```python
from merm import render_diagram

# Auto-detect type (flowchart)
svg = render_diagram("flowchart TD\n    A --> B")

# With a named theme
svg = render_diagram("flowchart TD\n    A --> B", theme="dark")

# With a Theme instance
from merm import Theme
custom = Theme(node_fill="#ff0000", node_stroke="#000000")
svg = render_diagram("flowchart TD\n    A --> B", theme=custom)
```

**Supported diagram types:**
- `flowchart` / `graph` (default if no type keyword detected)
- `sequenceDiagram`
- `classDiagram`
- `stateDiagram` / `stateDiagram-v2`
- `erDiagram`
- `pie`
- `mindmap`
- `gantt`
- `gitGraph`

---

### `render_to_file(source, path, *, theme=None) -> None`

Render a Mermaid diagram directly to a file. The output format is
auto-detected from the file extension.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `source` | `str` | *(required)* | Mermaid diagram source text |
| `path` | `str \| Path` | *(required)* | Output file path. Parent directory must exist. |
| `theme` | `Theme \| str \| None` | `None` | Theme for styling (see `render_diagram`). |

**Returns:** `None`

**Raises:**
- `FileNotFoundError` -- If the parent directory does not exist.
- `ImportError` -- If cairosvg is not installed and a `.png` path is given.
- `ValueError` -- If `source` is empty or whitespace-only.
- `ParseError` -- If the diagram source contains invalid syntax.

**Format detection:**
- `.png` extension -- renders SVG then converts to PNG via cairosvg
- `.svg` or any other extension -- writes SVG text

**Example:**

```python
from merm import render_to_file

# Write SVG
render_to_file("flowchart TD\n    A --> B", "diagram.svg")

# Write PNG (requires cairosvg)
render_to_file("flowchart TD\n    A --> B", "diagram.png")

# With a theme
render_to_file("flowchart TD\n    A --> B", "dark.svg", theme="dark")
```

---

### `render_to_png(source, *, theme=None) -> bytes`

Render a Mermaid diagram to PNG bytes in memory.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `source` | `str` | *(required)* | Mermaid diagram source text |
| `theme` | `Theme \| str \| None` | `None` | Theme for styling (see `render_diagram`). |

**Returns:** `bytes` -- PNG image data.

**Raises:**
- `ImportError` -- If cairosvg is not installed.
- `ValueError` -- If `source` is empty or whitespace-only.
- `ParseError` -- If the diagram source contains invalid syntax.

**Example:**

```python
from merm import render_to_png

png_data = render_to_png("flowchart TD\n    A --> B")

# Write to file manually
with open("diagram.png", "wb") as f:
    f.write(png_data)

# Or use in a web framework
# return Response(content=png_data, media_type="image/png")
```

---

## Theme System

### `Theme` dataclass

A frozen dataclass containing all visual styling values for diagram rendering.
Every color, size, and spacing value used by the SVG renderer and layout engine
is stored here.

```python
from merm import Theme

# Create a custom theme
my_theme = Theme(
    node_fill="#e0f0ff",
    node_stroke="#336699",
    node_text_color="#000000",
    edge_stroke="#336699",
    background_color="white",
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `node_fill` | `str` | `"#ECECFF"` | Node background color |
| `node_stroke` | `str` | `"#9370DB"` | Node border color |
| `node_stroke_width` | `str` | `"1"` | Node border width |
| `node_text_color` | `str` | `"#333333"` | Node text color |
| `node_font_size` | `str` | `"16px"` | Node text font size |
| `node_padding_h` | `float` | `16.0` | Horizontal padding inside nodes |
| `node_padding_v` | `float` | `8.0` | Vertical padding inside nodes |
| `node_min_height` | `float` | `42.0` | Minimum node height |
| `node_min_width` | `float` | `70.0` | Minimum node width |
| `node_border_radius` | `float` | `5.0` | Border radius for rounded rectangles |
| `edge_stroke` | `str` | `"#333333"` | Edge line color |
| `edge_stroke_width` | `str` | `"2"` | Edge line width |
| `edge_label_bg` | `str` | `"rgba(232,232,232,0.8)"` | Edge label background color |
| `edge_label_font_size` | `str` | `"12px"` | Edge label font size |
| `subgraph_fill` | `str` | `"#ffffde"` | Subgraph background color |
| `subgraph_stroke` | `str` | `"#aaaa33"` | Subgraph border color |
| `subgraph_stroke_width` | `str` | `"1"` | Subgraph border width |
| `subgraph_title_font_size` | `str` | `"12px"` | Subgraph title font size |
| `font_family` | `str` | `"trebuchet ms", ...` | CSS font-family string |
| `text_color` | `str` | `"#333333"` | General text color |
| `background_color` | `str` | `"white"` | Diagram background color |
| `rank_sep` | `float` | `40.0` | Vertical spacing between node ranks |
| `node_sep` | `float` | `30.0` | Horizontal spacing between nodes |

**Methods:**

#### `Theme.replace(**kwargs) -> Theme`

Return a new Theme with the specified fields overridden (the original is
unchanged since Theme is frozen).

```python
from merm import DEFAULT_THEME

dark_bg = DEFAULT_THEME.replace(background_color="#1a1a2e", text_color="#eee")
```

---

### Built-in Themes

Four built-in themes are available:

| Name | Variable | Description |
|------|----------|-------------|
| `"default"` | `DEFAULT_THEME` | Purple nodes, yellow subgraphs (matches mermaid.js) |
| `"dark"` | `DARK_THEME` | Dark background, light text, blue-tinted nodes |
| `"forest"` | `FOREST_THEME` | Green-tinted nodes, dark green edges |
| `"neutral"` | `NEUTRAL_THEME` | Grey-scale nodes, neutral edges |

```python
from merm import DEFAULT_THEME, render_diagram
from merm.theme import DARK_THEME, FOREST_THEME, NEUTRAL_THEME

# Use by name (string)
svg = render_diagram(source, theme="forest")

# Use by instance
svg = render_diagram(source, theme=FOREST_THEME)
```

---

### `get_theme(name) -> Theme`

Look up a built-in theme by name.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | Theme name (case-sensitive): `"default"`, `"dark"`, `"forest"`, or `"neutral"` |

**Returns:** The matching `Theme` instance.

**Raises:** `ValueError` if the name does not match any built-in theme.

```python
from merm import get_theme

theme = get_theme("dark")
```

---

## Error Handling

### `ParseError`

Exception raised when the parser encounters invalid Mermaid syntax.

```python
from merm import ParseError, render_diagram

try:
    svg = render_diagram("flowchart TD\n    invalid!!! syntax")
except ParseError as e:
    print(f"Failed to parse: {e}")
```

**Attributes:**

| Name | Type | Description |
|------|------|-------------|
| `line` | `int \| None` | The source line number where the error occurred, or `None` |

---

## Individual Parsers

For advanced use cases where you need access to the intermediate
representation (IR) rather than the final SVG, individual parser functions
are available. Each returns a diagram-specific IR dataclass.

### `parse_flowchart(text) -> Diagram`

Parse Mermaid flowchart/graph syntax.

```python
from merm import parse_flowchart

diagram = parse_flowchart("flowchart TD\n    A --> B")
print(diagram.nodes)  # list of Node objects
print(diagram.edges)  # list of Edge objects
```

### `parse_sequence(text) -> SequenceDiagram`

Parse Mermaid sequence diagram syntax.

```python
from merm import parse_sequence

diagram = parse_sequence("sequenceDiagram\n    Alice->>Bob: Hello")
```

### `parse_class_diagram(text) -> ClassDiagram`

Parse Mermaid class diagram syntax.

```python
from merm import parse_class_diagram

diagram = parse_class_diagram("classDiagram\n    class Animal")
```

### `parse_state_diagram(text) -> StateDiagram`

Parse Mermaid state diagram syntax.

```python
from merm import parse_state_diagram

diagram = parse_state_diagram("stateDiagram-v2\n    [*] --> Active")
```

### `parse_er_diagram(text) -> ERDiagram`

Parse Mermaid ER diagram syntax. Import from `merm.parser`:

```python
from merm.parser import parse_er_diagram

diagram = parse_er_diagram("erDiagram\n    CUSTOMER ||--o{ ORDER : places")
```

### `parse_pie(text) -> PieChart`

Parse Mermaid pie chart syntax. Import from `merm.parser.pie`:

```python
from merm.parser.pie import parse_pie

chart = parse_pie('pie\n    "Dogs" : 40\n    "Cats" : 60')
```

### `parse_gantt(text) -> GanttChart`

Parse Mermaid gantt chart syntax. Import from `merm.parser.gantt`:

```python
from merm.parser.gantt import parse_gantt

chart = parse_gantt("gantt\n    title Plan\n    section A\n    Task1 :a1, 2024-01-01, 30d")
```

### `parse_mindmap(text) -> MindmapDiagram`

Parse Mermaid mindmap syntax. Import from `merm.parser.mindmap`:

```python
from merm.parser.mindmap import parse_mindmap

diagram = parse_mindmap("mindmap\n  root\n    Child A\n    Child B")
```

### `parse_gitgraph(text) -> GitGraph`

Parse Mermaid gitGraph syntax. Import from `merm.parser.gitgraph`:

```python
from merm.parser.gitgraph import parse_gitgraph

graph = parse_gitgraph('gitGraph\n    commit id: "Initial"')
```

All parsers raise `ParseError` on invalid input.

---

## Low-level Render Function

### `render_svg(diagram, layout, theme=None) -> str`

Render a pre-parsed and pre-laid-out flowchart diagram to SVG. This is the
lower-level rendering function used internally by `render_diagram` for
flowcharts.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `diagram` | `Diagram` | *(required)* | The parsed flowchart IR (from `parse_flowchart`) |
| `layout` | `LayoutResult` | *(required)* | Positioned layout (from `layout_diagram`) |
| `theme` | `Theme \| None` | `None` | Theme for styling. Defaults to `DEFAULT_THEME`. |

**Returns:** `str` -- SVG XML string.

```python
from merm import parse_flowchart, render_svg
from merm.measure import TextMeasurer
from merm.layout import layout_diagram

source = "flowchart TD\n    A --> B"
diagram = parse_flowchart(source)
measurer = TextMeasurer()
layout = layout_diagram(diagram, measure_fn=measurer.measure)
svg = render_svg(diagram, layout)
```

---

## Command-Line Interface

`merm` includes a CLI for rendering diagrams from the terminal.

### Usage

```
merm [-h] [-i INPUT] [-o OUTPUT] [-f {svg,png}]
     [--theme {default,dark,forest,neutral}] [--version]
     [input_file]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `input_file` | Input `.mmd` file path (positional). Reads from stdin if not provided. |
| `-i`, `--input` | Input `.mmd` file path (alternative to positional argument). |
| `-o`, `--output` | Output file path. Writes to stdout if not provided. |
| `-f`, `--format` | Output format: `svg` or `png`. Auto-detected from `-o` extension; defaults to `svg`. |
| `--theme` | Built-in theme name: `default`, `dark`, `forest`, or `neutral`. |
| `--version` | Show version number and exit. |
| `-h`, `--help` | Show help message and exit. |

### Examples

```bash
# Render a file to SVG (stdout)
merm diagram.mmd

# Render to a specific output file
merm diagram.mmd -o output.svg

# Render to PNG
merm diagram.mmd -o output.png

# Pipe from stdin
echo "flowchart TD
    A --> B --> C" | merm -o diagram.svg

# Use a theme
merm diagram.mmd -o output.svg --theme dark

# Use -i flag for input
merm -i diagram.mmd -o output.svg
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Parse error or PNG conversion error |
| `2` | File I/O error (file not found, permission denied, etc.) |
