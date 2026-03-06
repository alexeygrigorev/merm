# Task 57: Extract Icon SVG Paths to Separate Files

## Problem

`src/pymermaid/icons.py` is 353 lines, mostly hardcoded SVG path data for Font Awesome icons. This makes the file hard to maintain and bloats the Python source with static data.

## Implementation

1. Create `src/pymermaid/icons/` directory with individual `.svg` files per icon (e.g. `fa-tree.svg`, `fa-gift.svg`)
2. Each SVG file contains just the `<path>` or `<svg>` content for that icon
3. Replace the hardcoded dict in `icons.py` with a loader that reads from the `icons/` directory
4. Use `importlib.resources` (or `Path(__file__).parent`) to locate the SVG files at runtime
5. Lazy-load and cache icons on first use

## Acceptance Criteria

- [x] Icon SVG data lives in individual `.svg` files under `src/pymermaid/icons/`
- [x] `icons.py` contains only the loader logic, not SVG path data
- [x] All existing icon tests pass without modification
- [x] Icons render identically to before (no visual regression)
- [x] SVG files are included in the package (added to package_data or similar)
- [x] Lazy loading: icons are only read from disk when first requested

## Methodology

**TDD — test first.** Write a test that the loader returns the same data as the old hardcoded dict, confirm it passes after extraction.

## Dependencies

None.

## Estimated Complexity

Low — mechanical extraction, straightforward loader.
