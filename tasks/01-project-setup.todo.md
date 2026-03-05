# 01 - Project Setup

## Goal
Set up the Python project structure with packaging, dependencies, and development tooling.

## Tasks

- [ ] Create `pyproject.toml` with project metadata, dependencies, and build config
  - Name: `pymermaid`
  - Python >= 3.10
  - Optional deps: `fonttools`, `Pillow`
  - Dev deps: `pytest`, `ruff`
- [ ] Create package directory structure:
  ```
  src/pymermaid/
      __init__.py
      parser/
      ir/
      layout/
      measure/
      render/
      cli.py
  tests/
      fixtures/        # .mmd input files
      reference/       # reference SVGs from mmdc
      test_parser.py
      test_layout.py
      test_render.py
      test_integration.py
  ```
- [ ] Create `src/pymermaid/__init__.py` with public API: `render(mmd_text) -> svg_string`
- [ ] Create CLI entry point in `pyproject.toml`: `pymermaid` command
- [ ] Set up `ruff` config for linting/formatting
- [ ] Create `.gitignore`
- [ ] Verify `uv sync` works and tests can be discovered

## Acceptance Criteria
- `uv run pytest` runs (even with 0 tests)
- `uv run pymermaid --help` prints usage
- Package is importable: `from pymermaid import render`

## Estimated Complexity
Small - scaffolding only, no logic.
