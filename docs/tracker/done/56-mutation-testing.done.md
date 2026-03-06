# Task 56: Add Mutation Testing

## Goal

Add mutation testing to verify that our test suite actually catches bugs. Mutation testing introduces small changes (mutations) to the source code and checks that at least one test fails for each mutation. Surviving mutants indicate weak spots in test coverage.

## Implementation

### 1. Setup mutmut
- Add `mutmut` as a dev dependency (`uv add --dev mutmut`)
- Configure in `pyproject.toml` or `setup.cfg`:
  - Target: `src/pymermaid/`
  - Tests: `pytest tests/`
  - Timeout per mutant: 30s (avoid hanging on infinite loops)
  - Exclude generated/vendored code if any

### 2. Initial baseline run
- Run `mutmut run` on the full codebase
- Record baseline mutation score (killed / total mutants)
- Identify modules with lowest kill rates

### 3. Improve tests for surviving mutants
- Focus on high-value modules: parser, layout (sugiyama), render (edges, nodes, svg)
- Write targeted tests that kill surviving mutants
- Do NOT write trivial tests just to kill mutants — each test should verify meaningful behavior

### 4. CI integration
- Add a script `scripts/run_mutation_tests.sh` that runs mutmut and reports results
- Consider running on a subset of modules for speed (full run can be slow)

## Acceptance Criteria

- [ ] `mutmut` installed and configured
- [ ] Baseline mutation score recorded
- [ ] Mutation score for core modules (parser, layout, render) >= 70%
- [ ] Script to run mutation tests exists
- [ ] No regressions in existing test suite

## Methodology

**TDD — test first.** For surviving mutants:
1. Identify the mutation (e.g. changed `>` to `>=` in boundary check)
2. Write a test that specifically exercises that boundary condition
3. Confirm the test fails against the mutant
4. Confirm the test passes against the original code

## Dependencies

None.

## Estimated Complexity

Medium — setup is straightforward, but analyzing and killing surviving mutants takes effort. Full mutation runs can be slow on large codebases.
