# Issue 74: Performance benchmarks

## Problem

No performance benchmarks exist to track rendering speed. Without baselines, we cannot detect performance regressions or measure optimization impact.

## Scope

- Add `pytest-benchmark` as a dev dependency
- Create benchmark tests covering parse, layout, and render for multiple diagram types
- Use small, medium, and large diagrams for each type
- Establish baseline performance numbers (no specific performance targets required -- this is measurement infrastructure)
- At least 9 benchmark tests (3 sizes x 3 diagram types minimum)

## Dependencies

- None

## Acceptance Criteria

- [ ] `pytest-benchmark` is listed as a dev dependency in `pyproject.toml`
- [ ] `uv run pytest tests/test_benchmarks.py` runs and reports benchmark timings
- [ ] At least 9 benchmark tests exist: 3 diagram types (flowchart, sequence, class) x 3 sizes (small, medium, large)
- [ ] Each benchmark measures the full pipeline: `render_diagram(source)` (parse + layout + render)
- [ ] Small diagrams: 2-5 nodes/participants, Medium: 10-20, Large: 40+ nodes
- [ ] Benchmark output includes mean, stddev, and rounds for each test (pytest-benchmark default)
- [ ] Large flowchart benchmark uses `tests/fixtures/corpus/scale/large.mmd` (50 nodes) or a generated equivalent
- [ ] Benchmark tests do not fail -- they always pass (benchmarks measure, they don't assert performance targets)
- [ ] `uv run pytest` (full suite) still passes with benchmarks included
- [ ] Benchmarks can be run in isolation: `uv run pytest tests/test_benchmarks.py --benchmark-only`

## Test Scenarios

### Flowchart benchmarks
- `bench_flowchart_small`: render a 3-node linear flowchart (`A --> B --> C`)
- `bench_flowchart_medium`: render a ~15-node flowchart (use `tests/fixtures/corpus/scale/medium.mmd`)
- `bench_flowchart_large`: render a 50-node flowchart (use `tests/fixtures/corpus/scale/large.mmd`)

### Sequence diagram benchmarks
- `bench_sequence_small`: render a 2-participant, 2-message sequence diagram
- `bench_sequence_medium`: render a sequence diagram with 4+ participants and 8+ messages (use `tests/fixtures/corpus/sequence/complex.mmd` or similar)
- `bench_sequence_large`: render a generated sequence diagram with 8+ participants and 20+ messages

### Class diagram benchmarks
- `bench_class_small`: render a 2-class diagram with basic relationship
- `bench_class_medium`: render a class diagram with 5+ classes (use `tests/fixtures/corpus/class/complex.mmd` or similar)
- `bench_class_large`: render a generated class diagram with 10+ classes, multiple members each

### Optional additional benchmarks (nice to have)
- State diagram: small/medium/large
- ER diagram: small/medium/large
- Parse-only benchmark (isolate parser performance)
- Layout-only benchmark (isolate layout performance)

### Infrastructure verification
- `uv run pytest tests/test_benchmarks.py -v` lists all benchmark names
- `uv run pytest tests/test_benchmarks.py --benchmark-only` runs only benchmarks
- `uv run pytest tests/test_benchmarks.py --benchmark-disable` skips benchmarks (tests still pass as no-ops)
- Benchmark results are printed to stdout in a table format
