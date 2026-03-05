# 12 - CLI Interface

## Goal
Provide a command-line interface similar to `mmdc` for rendering `.mmd` files to SVG.

## Tasks

- [ ] Implement CLI using `argparse` (no extra dependency):
  ```
  pymermaid -i input.mmd -o output.svg
  pymermaid -i input.mmd -o output.svg -t default
  pymermaid --help
  cat input.mmd | pymermaid -o output.svg   # stdin support
  pymermaid -i input.mmd                     # stdout if no -o
  ```
- [ ] Arguments:
  - `-i, --input`: Input .mmd file (or `-` for stdin)
  - `-o, --output`: Output file (default: stdout)
  - `-t, --theme`: Theme name (default, dark, forest, neutral)
  - `-b, --background`: Background color
  - `--font-mode`: `heuristic` or `font` (text measurement mode)
  - `--font-path`: Path to TTF/OTF font file (for font mode)
  - `-w, --width`: Max width in pixels
  - `--version`: Print version
- [ ] Support rendering markdown files with ` ```mermaid ` blocks (extract and render each block)
- [ ] Meaningful error messages for invalid input
- [ ] Exit codes: 0 success, 1 parse error, 2 file error

## Acceptance Criteria
- `pymermaid -i test.mmd -o test.svg` produces valid SVG
- `echo "graph LR; A-->B" | pymermaid` outputs SVG to stdout
- `--help` documents all options
- Errors print to stderr with non-zero exit code

## Dependencies
- All core tasks (01-10)

## Estimated Complexity
Small - thin wrapper around the library API.
