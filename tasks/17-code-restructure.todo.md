# 17 - Code Restructuring

## Goal
Move business logic out of `__init__.py` files into properly named modules. `__init__.py` should only re-export public API.

## Problem
Currently most code lives in `__init__.py` files:
- `src/pymermaid/ir/__init__.py` (175 lines) -- all IR types
- `src/pymermaid/layout/__init__.py` (1007 lines) -- entire Sugiyama algorithm
- `src/pymermaid/measure/__init__.py` (174 lines) -- TextMeasurer
- `src/pymermaid/render/__init__.py` (311 lines) -- SVG renderer core

This makes files hard to navigate and violates the principle of `__init__.py` being a thin re-export layer.

## Tasks

### ir/ package
- [ ] Move enums to `src/pymermaid/ir/enums.py`
- [ ] Move dataclasses to `src/pymermaid/ir/types.py`
- [ ] `__init__.py` only re-exports from enums and types

### layout/ package
- [ ] Move data structures (Point, NodeLayout, etc.) to `src/pymermaid/layout/types.py`
- [ ] Move config to `src/pymermaid/layout/config.py`
- [ ] Move Sugiyama algorithm steps to `src/pymermaid/layout/sugiyama.py`
- [ ] Move subgraph layout logic to `src/pymermaid/layout/subgraph.py`
- [ ] `__init__.py` only re-exports `layout_diagram`, `LayoutResult`, `LayoutConfig`, etc.

### measure/ package
- [ ] Move to `src/pymermaid/measure/text.py`
- [ ] `__init__.py` only re-exports `TextMeasurer`, `measure_text`

### render/ package
- [ ] Move SVG renderer to `src/pymermaid/render/svg.py`
- [ ] Keep `shapes.py` and `edges.py` as they are (already proper modules)
- [ ] `__init__.py` only re-exports `render_svg`

## Acceptance Criteria
- [ ] No `__init__.py` has more than 30 lines of code
- [ ] All existing imports still work (`from pymermaid.ir import Node`, etc.)
- [ ] All 400+ existing tests pass without modification
- [ ] `uv run ruff check src/ tests/` passes
- [ ] No circular imports

## Dependencies
- All tasks through 12 must be done

## Estimated Complexity
Medium -- purely mechanical refactoring, but must not break any imports.
