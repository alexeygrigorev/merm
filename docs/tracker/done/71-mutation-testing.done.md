# Issue 71: Mutation testing

## Problem

No mutation testing exists to verify test suite effectiveness. While `mutmut` is already configured as a dev dependency and there is an existing `test_mutation_killing.py` file targeting measure and flowchart parser modules, the setup is incomplete: it only covers render modules in the mutmut config (`svg.py`, `edges.py`, `shapes.py`) and the mutation-killing tests only target measure and flowchart parser. There is no systematic process for running mutation tests and tracking scores across modules.

## Scope

- Expand mutmut configuration to cover parser modules (at minimum `flowchart.py`, `sequence.py`, `statediag.py`)
- Run mutmut against the flowchart parser module and document the baseline mutation score
- Identify and kill at least 10 additional surviving mutants in the flowchart parser by adding targeted tests
- Add a pytest marker (`@pytest.mark.mutation`) to all mutation-killing tests so they can be run selectively
- Update `scripts/run_mutation_tests.sh` to accept a module name argument and report scores clearly

## Dependencies

- None -- this is an independent testing infrastructure task

## Acceptance Criteria

- [ ] `mutmut` is configured in `pyproject.toml` with `paths_to_mutate` including at least `src/merm/parser/flowchart.py`
- [ ] Running `uv run mutmut run --paths-to-mutate src/merm/parser/flowchart.py` completes without errors
- [ ] A new test file `tests/test_mutation_parser.py` exists with targeted mutant-killing tests for the flowchart parser
- [ ] At least 10 new test cases are added that each kill a specific surviving mutant (documented in test docstrings)
- [ ] The flowchart parser mutation score improves by at least 3 percentage points from the baseline documented in `test_mutation_killing.py` (74.3% baseline)
- [ ] All mutation-killing tests are marked with `@pytest.mark.mutation`
- [ ] `pytest.ini` or `pyproject.toml` registers the `mutation` marker so no warnings are raised
- [ ] `uv run pytest tests/test_mutation_parser.py` passes
- [ ] `uv run pytest tests/test_mutation_killing.py` still passes (no regressions)
- [ ] `scripts/run_mutation_tests.sh` works with no arguments and with a specific module path argument

## Test Scenarios

### Unit: Targeted mutant killing for flowchart parser
- For each surviving mutant identified, write a test that fails if the mutant is applied
- Each test docstring must reference the specific mutation being killed (e.g., "Kills mutant that changes `>` to `>=` on line N")
- Tests must be independent -- each tests one specific code path

### Integration: mutmut run
- `uv run mutmut run --paths-to-mutate src/merm/parser/flowchart.py` should complete and produce a results summary
- The killed/total ratio should be documented in a comment at the top of the test file

### Process: mutation test script
- `./scripts/run_mutation_tests.sh` runs without errors
- `./scripts/run_mutation_tests.sh src/merm/parser/flowchart.py` runs only against the flowchart parser
