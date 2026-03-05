# Rendering Mermaid Diagrams Without a Browser

## The Problem

Mermaid.js is a JavaScript library that renders diagrams in the browser. It depends on browser DOM APIs for text measurement and layout (`getBBox()`, `getComputedTextLength()`, CSS layout). This means every tool that renders mermaid server-side ships a headless browser:

- Node.js `mmdc` CLI (mermaid-cli) uses Puppeteer (headless Chrome)
- Python `mmdc` package uses PhantomJS via `phasma` (~25MB dependency)
- `mermaid-cli-python` uses Playwright (headless Chromium)
- `mermaid-py` sidesteps the problem by calling the `mermaid.ink` online API

This is heavy for what amounts to rendering a few simple flowcharts to SVG.


## Existing Approaches

### Browser-based (current state of the art)

All official and most third-party tools use a headless browser. The mermaid-js project has an open issue since 2022 requesting non-browser rendering with no official solution: https://github.com/mermaid-js/mermaid/issues/2485

### Native reimplementations

Two projects reimplement mermaid parsing and rendering from scratch:

1. mermaid-rs-renderer (Rust): https://github.com/1jehuang/mermaid-rs-renderer
   - Parses mermaid syntax natively in Rust, renders directly to SVG
   - No browser, Node.js, or Puppeteer
   - Claims 100-1400x faster than mermaid-cli
   - CLI tool `mmdr`
   - Tradeoff: won't support every diagram type or edge case

2. rendermaid (TypeScript): https://blogo.timok.deno.net/posts/mermaid-ssr-renderer
   - Parses mermaid into an AST, renders to SVG using functional TypeScript
   - No DOM or browser APIs
   - Designed for static site generators


## What a Python Native Renderer Would Need

The core challenge is text measurement. Mermaid needs to know the pixel dimensions of text labels to:

- Size boxes/nodes around their text content
- Calculate edge routing between nodes
- Position labels on edges
- Determine the overall diagram dimensions

Without a browser, you need an alternative for text measurement:

- `fonttools` / `freetype-py` - read font metrics from .ttf/.otf files
- `Pillow` (PIL) - `ImageFont.getbbox()` for text measurement
- `cairo` (via `pycairo`) - `text_extents()` for precise text metrics
- Hardcoded character width tables (less accurate but zero dependencies)

The rendering pipeline would be:

1. Parse mermaid syntax into a graph structure (nodes, edges, labels)
2. Measure text dimensions using font metrics
3. Layout the graph (node positions, edge routing)
4. Render to SVG (straightforward string/XML generation)

Step 1 (parsing) is well-defined - mermaid syntax is documented.
Step 4 (SVG output) is trivial.
Steps 2-3 (measurement and layout) are the hard parts.


## Scope for This Project

For the immediate use case (simple `graph LR` / `graph TD` flowcharts), the subset of mermaid to support is small:

- `graph LR` / `graph TD` direction
- Rectangular nodes: `NodeId[Label]`
- Cylinder nodes: `NodeId[(Label)]`
- Edge labels: `A -->|label| B`
- Basic edge types: `-->`, `---`

This is a tractable problem. A simple force-directed or layered layout algorithm (like Sugiyama) would handle it, and text measurement can be approximated with font metrics or hardcoded widths.
