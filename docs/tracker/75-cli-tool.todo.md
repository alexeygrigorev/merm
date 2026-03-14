# Issue 75: CLI tool

## Problem

No command-line interface exists for rendering mermaid files.

## Scope

- Add a `merm` CLI command (entry point in pyproject.toml)
- Read .mmd files and output SVG or PNG
- Support stdin/stdout piping
- Options: output format (svg/png), theme, width/height
- Depends on cairosvg for PNG output
