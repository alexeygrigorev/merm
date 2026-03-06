# Issue 66: Remove reference tests (mmdc comparison)

## Problem

The mmdc reference test infrastructure is no longer useful — our implementation is mature enough that comparing against mmdc output doesn't add value. The reference PNGs and comparison tests add 3MB+ of bloat and maintenance burden.

## Scope

- Remove `tests/reference/` directory (SVGs and PNGs)
- Remove `tests/comparison.py` helper module
- Remove `tests/test_comparison.py` comparison test suite
- Remove `tests/mmdc-config.json`
- Remove `tests/puppeteer-config.json`
- Remove any mmdc reference comparison logic from other test files (but keep the tests themselves if they test our own output quality)
- Remove mmdc/Node.js dev dependencies if any exist in pyproject.toml

## Acceptance criteria

- [ ] `tests/reference/` directory deleted
- [ ] `tests/comparison.py` deleted
- [ ] `tests/test_comparison.py` deleted
- [ ] `tests/mmdc-config.json` deleted
- [ ] `tests/puppeteer-config.json` deleted
- [ ] References to mmdc comparison removed from other test files
- [ ] All remaining tests still pass
- [ ] No Node.js/mmdc dependencies remain in pyproject.toml
