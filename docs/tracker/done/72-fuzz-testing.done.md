# Issue 72: Fuzz testing for parsers

## Problem

No fuzz testing exists to catch crashes on malformed input. Parsers should handle arbitrary input gracefully -- raising clean `ParseError` exceptions rather than crashing with `IndexError`, `KeyError`, `AttributeError`, or other unhandled exceptions.

## Scope

- Add `hypothesis` as a dev dependency
- Write property-based fuzz tests for at least 3 parser types: flowchart, sequence, and state diagram
- Tests must verify that parsers never raise unexpected exceptions on arbitrary string input
- Tests must verify that parsers handle edge cases: empty strings, very long strings, strings with unicode/null bytes, strings with only whitespace
- Fuzz tests should run as part of `uv run pytest` but be marked so they can be skipped in CI if too slow

## Dependencies

- None -- this is an independent testing infrastructure task

## Acceptance Criteria

- [ ] `hypothesis` is listed as a dev dependency in `pyproject.toml`
- [ ] `uv sync` installs hypothesis without errors
- [ ] A test file `tests/test_fuzz_parsers.py` exists
- [ ] Fuzz tests cover at least 3 parsers: `parse_flowchart`, `parse_sequence`, and `parse_statediag`
- [ ] Each parser fuzz test uses `@given(st.text())` from hypothesis to generate arbitrary string input
- [ ] Each fuzz test asserts that the parser either returns a valid diagram object OR raises `ParseError` -- any other exception type is a test failure
- [ ] At least 3 additional targeted edge-case tests per parser (empty string, null bytes, extremely long input, unicode edge cases)
- [ ] All fuzz tests are marked with `@pytest.mark.fuzz`
- [ ] The `fuzz` marker is registered in `pyproject.toml` so no warnings are raised
- [ ] `uv run pytest tests/test_fuzz_parsers.py` passes with no failures
- [ ] `uv run pytest tests/test_fuzz_parsers.py -v` shows at least 15 test cases total
- [ ] If any parser crashes on fuzz input (raises something other than `ParseError`), the bug must be fixed in the parser so the fuzz test passes

## Test Scenarios

### Property-based: Flowchart parser robustness
- `parse_flowchart(arbitrary_text)` must either return a `Diagram` or raise `ParseError`
- Must not raise `IndexError`, `KeyError`, `TypeError`, `AttributeError`, or any other unexpected exception
- Test with hypothesis settings: `max_examples=500` for reasonable runtime

### Property-based: Sequence parser robustness
- `parse_sequence(arbitrary_text)` must either return a diagram or raise `ParseError`
- Same robustness guarantees as flowchart

### Property-based: State diagram parser robustness
- `parse_statediag(arbitrary_text)` must either return a diagram or raise `ParseError`
- Same robustness guarantees as flowchart

### Edge cases: All parsers
- Empty string `""` -- must raise `ParseError`, not crash
- Whitespace-only `"   \n\t  "` -- must raise `ParseError`
- Null bytes `"graph TD\n  A\x00B"` -- must not crash
- Very long input (10000+ characters) -- must not hang or OOM
- Unicode stress: mixed scripts, emoji, RTL text, zero-width characters
- Input that looks almost valid but has subtle syntax errors (e.g., `"graph TD\n  A --> "` with dangling edge)

### Regression: Discovered bugs
- Any input that hypothesis finds which crashes a parser must have a dedicated regression test added with `@example(...)` decorator so it is always re-tested
