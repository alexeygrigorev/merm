# 17 - Code Restructuring

## Goal
Move business logic out of `__init__.py` files into properly named modules. Each `__init__.py` should only contain re-exports (imports and `__all__`).

## Current State (confirmed)
| File | Lines | Content |
|------|-------|---------|
| `src/pymermaid/__init__.py` | 5 | Already thin -- just re-exports `render_svg`. No change needed. |
| `src/pymermaid/ir/__init__.py` | 175 | All IR enums and dataclasses. Needs splitting. |
| `src/pymermaid/layout/__init__.py` | 1007 | Entire Sugiyama algorithm, data structures, config. Needs splitting. |
| `src/pymermaid/measure/__init__.py` | 174 | TextMeasurer class. Needs moving. |
| `src/pymermaid/parser/__init__.py` | 5 | Already thin -- re-exports from `flowchart.py`. No change needed. |
| `src/pymermaid/render/__init__.py` | 311 | SVG renderer core. Needs moving. `shapes.py` and `edges.py` already exist as separate modules. |

## Tasks

### ir/ package
- [ ] Create `src/pymermaid/ir/enums.py` -- move all `Enum` classes (NodeShape, EdgeType, Direction, etc.)
- [ ] Create `src/pymermaid/ir/types.py` -- move all dataclasses (Node, Edge, Diagram, Subgraph, Style, etc.)
- [ ] Rewrite `src/pymermaid/ir/__init__.py` to import and re-export all public names from `enums` and `types`

### layout/ package
- [ ] Create `src/pymermaid/layout/types.py` -- move data structures (Point, NodeLayout, EdgeLayout, LayoutResult, etc.)
- [ ] Create `src/pymermaid/layout/config.py` -- move LayoutConfig and any related constants
- [ ] Create `src/pymermaid/layout/sugiyama.py` -- move the core Sugiyama algorithm functions/classes
- [ ] Create `src/pymermaid/layout/subgraph.py` -- move subgraph-specific layout logic (if separable; if tightly coupled with sugiyama, combine into sugiyama.py and note why)
- [ ] Rewrite `src/pymermaid/layout/__init__.py` to re-export `layout_diagram`, `LayoutResult`, `LayoutConfig`, and other public names

### measure/ package
- [ ] Create `src/pymermaid/measure/text.py` -- move TextMeasurer class and any helper functions
- [ ] Rewrite `src/pymermaid/measure/__init__.py` to re-export `TextMeasurer` and any public functions

### render/ package
- [ ] Create `src/pymermaid/render/svg.py` -- move SVG renderer logic (the `render_svg` function and helpers)
- [ ] Keep `shapes.py` and `edges.py` as-is (already proper modules)
- [ ] Rewrite `src/pymermaid/render/__init__.py` to re-export `render_svg` and other public names

## Acceptance Criteria

- [ ] No `__init__.py` file in `src/pymermaid/` (including sub-packages) has more than 30 lines
- [ ] All existing imports still work unchanged -- specifically these must all resolve:
  - `from pymermaid import render_svg`
  - `from pymermaid.ir import Node, Edge, Diagram, NodeShape, EdgeType, Direction`
  - `from pymermaid.layout import layout_diagram, LayoutResult, LayoutConfig`
  - `from pymermaid.measure import TextMeasurer`
  - `from pymermaid.render import render_svg`
  - `from pymermaid.parser import parse_flowchart`
- [ ] `uv run pytest` passes -- all 467+ existing tests pass with zero modifications to test files
- [ ] `uv run ruff check src/ tests/` passes with no errors
- [ ] No circular imports -- `python -c "import pymermaid"` succeeds without ImportError
- [ ] Each new module file has a module-level docstring explaining what it contains
- [ ] The `__all__` list in each `__init__.py` matches the set of names that were previously importable from that package

## Engineer Notes

- This is a pure refactoring task. No logic changes, no new features, no test changes.
- Do NOT modify any test files. If a test breaks, it means an import path is broken -- fix the `__init__.py` re-exports.
- Pay attention to intra-package imports. For example, `layout/sugiyama.py` will likely need to import from `layout/types.py` and `layout/config.py`. Use relative imports within packages (e.g., `from .types import Point, NodeLayout`).
- If `layout/subgraph.py` cannot be cleanly separated from the Sugiyama logic (due to tight coupling), it is acceptable to keep them in one file `sugiyama.py`. Document the reason in the file's docstring.
- Run `uv run pytest` after each package is restructured to catch breakage early. Do not batch all changes and hope it works.
- The `render/__init__.py` imports from `shapes.py` and `edges.py` -- make sure `svg.py` does the same if those are needed by the renderer.

## Dependencies
- Tasks 01-12 must be `.done.md` (all confirmed done)
- This task is independent of task 13 (integration tests) and can be done in parallel

## Estimated Complexity
Medium -- purely mechanical refactoring, but must be done carefully to avoid breaking any of the 467+ existing tests.
