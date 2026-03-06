# Issue 66: Remove reference tests (mmdc comparison)

## Problem

The mmdc reference test infrastructure is no longer useful -- our implementation is mature enough that comparing against mmdc output doesn't add value. The reference PNGs and comparison tests add 3MB+ of bloat and maintenance burden.

## Scope

### Delete entirely

- `tests/reference/` directory (SVGs, PNGs, corpus subdirs -- 3MB)
- `tests/test_comparison.py` (mmdc comparison test suite)
- `tests/test_svg_parsing.py` (tests for mmdc SVG parsing helpers that will be removed)
- `tests/mmdc-config.json`
- `tests/puppeteer-config.json`
- `scripts/render_comparison.py`
- `scripts/regenerate_corpus_references.sh`
- `scripts/regenerate_references.sh`

### Refactor: split comparison.py

`tests/comparison.py` contains two categories of code:

1. **mmdc SVG parsing** (`parse_svg_nodes`, `parse_svg_edges`, `parse_svg_labels`, `parse_svg_structure`, `structural_compare`, `SVGDiff`, `SVGStructure`, `NodeInfo`, `EdgeInfo`) -- DELETE these, they parse mmdc-generated SVGs
2. **pymermaid SVG utilities** (`BBox`, `PymermaidNodeInfo`, `PymermaidEdgeInfo`, `PymermaidSubgraphInfo`, `parse_merm_svg_nodes`, `parse_merm_svg_edges`, `parse_merm_svg_subgraphs`, `check_no_overlaps`, `check_directionality`, `check_subgraph_containment`, `_extract_direction_from_mmd`, and their private helpers `_parse_bbox_from_rect`, `_parse_bbox_from_circle`, `_parse_bbox_from_polygon`, `_parse_node_bbox`) -- KEEP these, they are used by `tests/test_corpus.py`

The recommended approach: extract the pymermaid utilities into a new module (e.g. `tests/svg_utils.py`), update `tests/test_corpus.py` imports, then delete `tests/comparison.py`.

### Update pyproject.toml

- Remove the `comparison` pytest marker from `[tool.pytest.ini_options].markers`
- Remove `--ignore=tests/test_comparison.py` from `[tool.mutmut].pytest_add_cli_args`

### Update .gitignore

- Remove `docs/comparisons/` and `docs/comparison_scores.json` lines (cleanup)

## Dependencies

- None -- this is a standalone cleanup task

## Acceptance Criteria

- [ ] `tests/reference/` directory does not exist
- [ ] `tests/comparison.py` does not exist
- [ ] `tests/test_comparison.py` does not exist
- [ ] `tests/test_svg_parsing.py` does not exist
- [ ] `tests/mmdc-config.json` does not exist
- [ ] `tests/puppeteer-config.json` does not exist
- [ ] `scripts/render_comparison.py` does not exist
- [ ] `scripts/regenerate_corpus_references.sh` does not exist
- [ ] `scripts/regenerate_references.sh` does not exist
- [ ] A new `tests/svg_utils.py` (or similar) exists containing: `BBox`, `PymermaidNodeInfo`, `PymermaidEdgeInfo`, `PymermaidSubgraphInfo`, `parse_merm_svg_nodes`, `parse_merm_svg_edges`, `parse_merm_svg_subgraphs`, `check_no_overlaps`, `check_directionality`, `check_subgraph_containment`, `_extract_direction_from_mmd`
- [ ] `tests/test_corpus.py` imports from the new module, not from `tests.comparison`
- [ ] No file in the repo imports from `tests.comparison`
- [ ] `pyproject.toml` does not contain the `comparison` pytest marker
- [ ] `pyproject.toml` does not reference `test_comparison.py` in mutmut config
- [ ] `.gitignore` does not contain `docs/comparisons/` or `docs/comparison_scores.json`
- [ ] `uv run pytest tests/test_corpus.py -x` passes (the surviving consumer of the extracted utilities)
- [ ] `uv run pytest -x --ignore=tests/test_corpus.py --ignore=tests/test_corpus_rendering.py --ignore=tests/test_flowchart_parser.py --ignore=tests/test_cli.py --ignore=tests/test_mutation_killing.py --ignore=tests/test_lr_subgraph_layout.py` passes
- [ ] `uv run ruff check` passes

## Test Scenarios

### Verify: deleted files are gone
- Confirm each of the 9 deleted paths (files and directory) does not exist on disk
- Confirm `git status` shows them as deleted

### Verify: extracted utilities work
- `from tests.svg_utils import BBox` succeeds
- `from tests.svg_utils import parse_merm_svg_nodes` succeeds
- `from tests.svg_utils import check_no_overlaps` succeeds
- `from tests.svg_utils import check_directionality` succeeds
- `from tests.svg_utils import check_subgraph_containment` succeeds

### Verify: test_corpus.py still works
- `uv run pytest tests/test_corpus.py -x` -- all tests pass, no import errors

### Verify: no stale references
- `grep -r "from tests.comparison" tests/` returns nothing
- `grep -r "tests/reference" tests/` returns nothing
- `grep -r "mmdc-config" tests/` returns nothing
- `grep -r "puppeteer-config" tests/` returns nothing

### Verify: pyproject.toml is clean
- No `comparison` marker in pytest markers list
- No `test_comparison.py` in mutmut ignore list
