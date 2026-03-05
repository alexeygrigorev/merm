# 12 - CLI Interface

## Goal

Provide a fully functional command-line interface that renders `.mmd` files to SVG, replacing the current stub in `src/pymermaid/cli.py`.

## Scope

### CLI Arguments

The CLI must support the following arguments via `argparse`:

| Flag | Long | Description | Default |
|------|------|-------------|---------|
| `-i` | `--input` | Input `.mmd` file path (or `-` for stdin) | stdin |
| `-o` | `--output` | Output SVG file path | stdout |
| | `--version` | Print version and exit | |

The following flags are deferred to later tasks (out of scope for now but should be listed in `--help` as "not yet implemented" or simply omitted until the features exist):
- `-t` / `--theme` (depends on task 11 theme selection)
- `-b` / `--background`
- `--font-mode` (heuristic vs font)
- `--font-path`
- `-w` / `--width`

### Core Pipeline

The CLI must wire together the existing pipeline:
1. Read input (file or stdin)
2. `parse_flowchart(text)` to get a `Diagram`
3. `measure_text(...)` + `layout(...)` to get a `LayoutResult`
4. `render_svg(diagram, layout)` to get the SVG string
5. Write output (file or stdout)

### Error Handling

- Exit code 0: success
- Exit code 1: parse error (invalid mermaid syntax)
- Exit code 2: file error (file not found, permission denied)
- All errors print to stderr with a human-readable message (no raw tracebacks)

### Stdin / Stdout

- When no `-i` is provided, read from stdin
- When no `-o` is provided, write SVG to stdout
- Support piping: `echo "graph LR; A-->B" | pymermaid`

## Acceptance Criteria

- [ ] `pymermaid -i test.mmd -o test.svg` reads the file, parses, lays out, renders, and writes valid SVG
- [ ] `echo "graph LR; A-->B" | pymermaid` outputs SVG to stdout containing nodes A and B
- [ ] `pymermaid -i test.mmd` (no `-o`) outputs SVG to stdout
- [ ] `pymermaid -i nonexistent.mmd` exits with code 2 and prints an error to stderr
- [ ] `echo "not valid mermaid" | pymermaid` exits with code 1 and prints a parse error to stderr
- [ ] `pymermaid --version` prints the version string (e.g. `pymermaid 0.1.0`) and exits 0
- [ ] `pymermaid --help` prints usage documentation listing all flags
- [ ] The CLI entry point is registered in `pyproject.toml` as `pymermaid = "pymermaid.cli:main"` (already done)
- [ ] `uv run pytest tests/test_cli.py` passes with 10+ tests
- [ ] All existing tests still pass

## Test Scenarios

### Unit: Argument parsing
- `pymermaid --version` outputs version string containing "0.1.0" and exits 0
- `pymermaid --help` exits 0 and output contains "-i" and "-o" and "--version"
- `pymermaid -i foo.mmd -o bar.svg` parses input="foo.mmd" and output="bar.svg"

### Unit: File input rendering
- Write a temp `.mmd` file with `graph LR; A-->B`, run CLI with `-i tmpfile -o tmpout.svg`, verify tmpout.svg exists and contains `<svg` and `data-node-id="A"` and `data-node-id="B"`

### Unit: Stdin to stdout
- Use `subprocess.run` with input="graph LR; A-->B" and capture stdout; verify SVG output contains nodes A and B

### Unit: Stdin to file
- Use `subprocess.run` with input="graph TD; X-->Y" and `-o tmpfile.svg`; verify file contains valid SVG

### Unit: Error handling -- file not found
- Run CLI with `-i /nonexistent/path.mmd`; assert exit code is 2 and stderr contains an error message

### Unit: Error handling -- parse error
- Run CLI with input="this is not mermaid"; assert exit code is 1 and stderr contains an error message

### Unit: Error handling -- output directory does not exist
- Run CLI with `-o /nonexistent/dir/out.svg`; assert exit code is 2 and stderr contains an error message

### Integration: Pipe chain
- Run `echo "graph LR; A-->B" | pymermaid` via subprocess; verify stdout is valid SVG

## Dependencies

- Task 04 (parser) -- done
- Task 05 (text measurement) -- done
- Task 06 (layout) -- done
- Task 07 (renderer) -- done

Note: The CLI can be implemented and tested before task 11 (styling) is complete. Styling will enhance the output but is not required for the CLI to function.

## Estimated Complexity

Small -- thin wrapper wiring the existing `parse_flowchart` -> `layout` -> `render_svg` pipeline with argparse and error handling.
