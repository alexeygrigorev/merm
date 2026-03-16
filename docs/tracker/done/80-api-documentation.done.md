# Issue 80: API documentation

## Problem

No API documentation exists. Users must read source code to understand available functions, parameters, and return types.

## Scope

- Add docstrings to all public API functions if missing
- Create docs/api.md with complete API reference:
  - render_diagram(source, theme) -> str
  - render_to_file(source, path, theme)
  - render_to_png(source, theme) -> bytes
  - Theme dataclass and built-in themes
  - ParseError
  - Individual parsers (parse_flowchart, parse_sequence, etc.)
- Include usage examples for each function
- Document CLI usage with all flags (--help output)
