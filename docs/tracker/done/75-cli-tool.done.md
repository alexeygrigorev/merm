# Issue 75: CLI tool improvements

## Problem

The `merm` CLI exists (`src/merm/cli.py`) but is missing key usability features:
- Input file must be specified with `-i` flag instead of as a positional argument
- No PNG output support (only SVG)
- No `-f/--format` option or auto-detection from output file extension
- Duplicates diagram-type detection logic instead of using `render_diagram()`

## Scope

Enhance the existing CLI to support the following usage patterns:

```
merm input.mmd -o output.svg       # positional input, SVG output
merm input.mmd -o output.png       # positional input, PNG output (auto-detect from .png extension)
merm input.mmd                     # positional input, SVG to stdout
cat input.mmd | merm -o output.svg # stdin input, file output
cat input.mmd | merm               # stdin to stdout (SVG)
merm input.mmd -f png              # explicit format override
merm -i input.mmd -o output.svg    # keep backward compat with -i flag
```

### Implementation notes

- Keep using argparse
- Add `input` as an optional positional argument (in addition to keeping `-i/--input` for backward compatibility)
- Add `-f/--format` option accepting `svg` or `png` (default: auto-detect from `-o` extension, fallback to `svg`)
- PNG rendering: call `render_diagram()` to get SVG, then convert with `cairosvg.svg2png()`
- Refactor to use `render_diagram()` from `merm.__init__` instead of duplicating type detection
- When output is PNG and writing to stdout, write binary to `sys.stdout.buffer`
- cairosvg is already a dev dependency; for PNG output at runtime, catch ImportError and print a helpful message

## Dependencies

- None (CLI module and tests already exist; this is an enhancement)

## Acceptance Criteria

- [ ] `merm input.mmd -o output.svg` works (positional input argument)
- [ ] `merm input.mmd -o output.png` produces a valid PNG file
- [ ] `merm input.mmd` prints SVG to stdout
- [ ] `cat input.mmd | merm -o output.svg` works (stdin piping)
- [ ] `cat input.mmd | merm` prints SVG to stdout (stdin + stdout)
- [ ] `merm input.mmd -f png` outputs PNG to stdout (binary on stdout.buffer)
- [ ] `-f/--format` accepts `svg` or `png`; invalid values produce an error
- [ ] Format is auto-detected from output file extension when `-f` is not specified (`.png` -> PNG, `.svg` or anything else -> SVG)
- [ ] `-i/--input` flag still works for backward compatibility
- [ ] If both positional input and `-i` are provided, error out with a clear message
- [ ] Missing input file exits with code 2 and prints error to stderr
- [ ] Parse errors exit with code 1 and print error to stderr
- [ ] When cairosvg is not available and PNG is requested, exit with code 1 and a helpful error message
- [ ] CLI internally uses `render_diagram()` instead of duplicating diagram-type detection
- [ ] `merm --version` still works
- [ ] `merm --help` shows the new positional argument, `-f/--format`, and updated usage
- [ ] `uv run pytest tests/test_cli.py` passes with all new and existing tests

## Test Scenarios

### Unit: Positional input argument
- `merm input.mmd -o output.svg` reads file and writes SVG
- `merm input.mmd` outputs SVG to stdout
- Positional arg with nonexistent file exits 2

### Unit: PNG output
- `merm input.mmd -o output.png` writes valid PNG (check PNG magic bytes `\x89PNG`)
- `merm input.mmd -f png` writes PNG bytes to stdout
- `merm input.mmd -f png -o output.png` writes PNG file

### Unit: Format auto-detection
- `-o foo.png` without `-f` produces PNG
- `-o foo.svg` without `-f` produces SVG
- `-o foo.txt` without `-f` defaults to SVG
- `-f png -o foo.svg` uses explicit format (PNG), not extension

### Unit: Backward compatibility
- `-i input.mmd -o output.svg` still works
- `-i input.mmd` to stdout still works
- Both positional and `-i` provided -> error

### Unit: Error handling
- Invalid format value (`-f pdf`) exits with error
- Missing cairosvg when PNG requested -> helpful error (mock the import)
- Parse error in input -> exit code 1
- Nonexistent input file -> exit code 2
- Nonexistent output directory -> exit code 2

### Unit: Refactored internals
- CLI uses `render_diagram()` (not direct parser imports) -- verify by checking that all diagram types supported by `render_diagram()` work through CLI (at least flowchart, sequence, class, state)

### Integration: stdin piping
- Pipe flowchart text via stdin, get SVG on stdout
- Pipe flowchart text via stdin with `-o output.png`, get PNG file

### Integration: entry point
- `uv run merm --version` works
- `uv run merm --help` shows format option
