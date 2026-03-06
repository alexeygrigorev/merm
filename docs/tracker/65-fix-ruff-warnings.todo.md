# Issue 65: Fix all ruff warnings

## Problem

There are 29 ruff warnings across `src/` and `tests/`:
- 22x I001: Import block is un-sorted or un-formatted
- 4x F811/F401: Unused imports
- Other minor issues

26 of 29 are auto-fixable with `--fix`.

## Expected behavior

- `uv run ruff check src/ tests/` reports zero errors

## Acceptance criteria

- [ ] `uv run ruff check src/ tests/` passes with zero warnings
- [ ] No functional changes to code behavior
- [ ] All existing tests still pass
