# 01 - Project Setup

## Goal
Set up the Python project structure with packaging, dependencies, and development tooling.

## Dependencies
None -- this is the first task.

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
          __init__.py
      ir/
          __init__.py
      layout/
          __init__.py
      measure/
          __init__.py
      render/
          __init__.py
      cli.py
  tests/
      __init__.py
      fixtures/        # .mmd input files
      reference/       # reference SVGs from mmdc
      test_parser.py
      test_layout.py
      test_render.py
      test_integration.py
  ```
- [ ] Create `src/pymermaid/__init__.py` with public API: `render(mmd_text) -> svg_string`
- [ ] Create CLI entry point in `pyproject.toml`: `pymermaid` command via `src/pymermaid/cli.py`
- [ ] Set up `ruff` config for linting/formatting in `pyproject.toml`
- [ ] Create `.gitignore` (Python, uv, IDE files)
- [ ] Verify `uv sync` works and tests can be discovered

## Acceptance Criteria

- [ ] `pyproject.toml` exists at project root with `name = "pymermaid"` and `requires-python = ">=3.10"`
- [ ] `pyproject.toml` declares optional dependencies for `fonttools` and `Pillow`
- [ ] `pyproject.toml` declares dev dependencies including `pytest` and `ruff`
- [ ] `pyproject.toml` defines a `[project.scripts]` entry: `pymermaid = "pymermaid.cli:main"`
- [ ] `pyproject.toml` contains `[tool.ruff]` configuration
- [ ] `src/pymermaid/__init__.py` exists and exports a `render` function
- [ ] `render` function has the signature `render(mmd_text: str) -> str` (can be a stub that raises `NotImplementedError`)
- [ ] All subpackage directories exist with `__init__.py` files: `parser/`, `ir/`, `layout/`, `measure/`, `render/`
- [ ] `src/pymermaid/cli.py` exists with a `main()` function that accepts `--help`
- [ ] `tests/` directory exists with `__init__.py` and the four test files listed above
- [ ] `tests/fixtures/` and `tests/reference/` directories exist
- [ ] `.gitignore` exists and covers at least: `__pycache__`, `*.egg-info`, `.venv`, `dist/`, `.ruff_cache`
- [ ] `uv sync` completes without errors
- [ ] `uv run pytest` exits with code 0 (no collection errors, even if there are 0 tests)
- [ ] `uv run pymermaid --help` prints usage information and exits with code 0
- [ ] `uv run python -c "from pymermaid import render"` exits with code 0
- [ ] `uv run ruff check src/` exits with code 0 (no lint violations)

## Test Scenarios

### Unit: Public API importability
- `from pymermaid import render` succeeds without error
- `render` is callable
- Calling `render("graph TD; A-->B")` raises `NotImplementedError` (stub behavior)

### Unit: CLI entry point
- `from pymermaid.cli import main` succeeds without error
- `main` is callable

### Unit: Subpackage imports
- `import pymermaid.parser` succeeds
- `import pymermaid.ir` succeeds
- `import pymermaid.layout` succeeds
- `import pymermaid.measure` succeeds
- `import pymermaid.render` succeeds

### Integration: CLI via subprocess
- Running `uv run pymermaid --help` returns exit code 0 and output contains "usage" or "pymermaid" (case-insensitive)

### Smoke: pytest discovery
- `uv run pytest --collect-only` exits with code 0 (no import errors or collection failures)

## Estimated Complexity
Small -- scaffolding only, no logic.
