# Issue 76: Python API improvements

## Problem

The Python API is functional but missing convenience functions. Currently:
- `__init__.py` only exports `render_diagram` and `render_svg`
- No `render_to_file()` or `render_to_png()` convenience functions
- Users must manually handle file I/O and PNG conversion
- Parsers are not re-exported from top-level package

## Scope

### Add convenience functions to `merm.__init__`

1. **`render_to_file(source: str, path: str | Path) -> None`**
   - Renders source to file, auto-detecting format from extension
   - `.png` extension -> render SVG then convert to PNG with cairosvg
   - `.svg` or any other extension -> write SVG
   - Raises `FileNotFoundError` if parent directory does not exist
   - Raises `ImportError` with helpful message if cairosvg not available for PNG

2. **`render_to_png(source: str) -> bytes`**
   - Renders source to PNG bytes
   - Returns `bytes` (not str)
   - Raises `ImportError` with helpful message if cairosvg not available

3. **Re-export key parsers from `merm`**
   - `from merm import parse_flowchart, parse_sequence, parse_class_diagram, parse_state_diagram`
   - Add `ParseError` to top-level exports

4. **Update `__all__`** to include all new exports

### Better error messages

- When `render_diagram()` receives empty/whitespace-only input, raise `ValueError` with message "Empty diagram source"
- When `render_diagram()` cannot detect diagram type AND parsing fails, include in the error message which diagram types are supported

## Dependencies

- None

## Acceptance Criteria

- [ ] `from merm import render_to_file` works
- [ ] `from merm import render_to_png` works
- [ ] `from merm import parse_flowchart, parse_sequence, parse_class_diagram, parse_state_diagram` works
- [ ] `from merm import ParseError` works
- [ ] `render_to_file(source, "output.svg")` writes valid SVG file
- [ ] `render_to_file(source, "output.png")` writes valid PNG file (check PNG magic bytes)
- [ ] `render_to_file(source, Path("output.svg"))` accepts Path objects
- [ ] `render_to_png(source)` returns `bytes` starting with PNG magic bytes `b'\x89PNG'`
- [ ] `render_to_file(source, "/nonexistent/dir/out.svg")` raises `FileNotFoundError`
- [ ] `render_diagram("")` raises `ValueError` with "Empty diagram source" (or similar)
- [ ] `render_diagram("   \n  ")` raises `ValueError` (whitespace-only)
- [ ] `__all__` in `merm/__init__.py` lists all public exports
- [ ] `uv run pytest tests/test_api.py` passes with 15+ tests
- [ ] Existing tests continue to pass (`uv run pytest`)

## Test Scenarios

### Unit: render_to_file SVG
- Write flowchart to .svg file, verify file contains `<svg`
- Write sequence diagram to .svg file, verify valid SVG
- Accept `pathlib.Path` as path argument

### Unit: render_to_file PNG
- Write flowchart to .png file, verify PNG magic bytes
- Write sequence diagram to .png file, verify file size > 0

### Unit: render_to_file errors
- Parent directory does not exist -> `FileNotFoundError`
- cairosvg not available + .png path -> `ImportError` with helpful message (mock the import)

### Unit: render_to_png
- Flowchart source returns bytes with PNG header
- Returned type is `bytes`, not `str`
- Empty source raises `ValueError`

### Unit: re-exported parsers
- `from merm import parse_flowchart` -- call it with valid input, get diagram IR
- `from merm import parse_sequence` -- call it with valid input
- `from merm import parse_class_diagram` -- call it with valid input
- `from merm import parse_state_diagram` -- call it with valid input
- `from merm import ParseError` -- catch it when parsing invalid input

### Unit: error messages
- `render_diagram("")` -> `ValueError`
- `render_diagram("   ")` -> `ValueError`
- `render_diagram("not a diagram at all ^^^")` -> error message mentions supported types or gives useful context

### Unit: __all__ completeness
- All items in `__all__` are importable
- `render_diagram`, `render_svg`, `render_to_file`, `render_to_png`, `ParseError` are all in `__all__`

### Integration: round-trip
- `render_to_png("graph LR\n  A --> B")` produces non-empty bytes
- Write PNG to file, read it back, verify it starts with PNG magic bytes
