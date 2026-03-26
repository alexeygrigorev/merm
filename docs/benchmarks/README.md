# Performance Benchmarks

Benchmarks measure the full `render_diagram()` pipeline (parse → layout → SVG render) using [pytest-benchmark](https://pytest-benchmark.readthedocs.io/).

## Running

```bash
uv run pytest tests/test_benchmarks.py --benchmark-only -v
```

## Results

Measured on Linux 6.8.0, Python 3.13, AMD/Intel (single-threaded).

| Benchmark | Diagram | Mean | Median | OPS |
|---|---|---|---|---|
| flowchart_small | 3 nodes, linear | 382 us | 373 us | 2,621 |
| flowchart_medium | ~15 nodes | 1.53 ms | 1.51 ms | 655 |
| flowchart_large | 50 nodes | 5.24 ms | 5.20 ms | 191 |
| sequence_small | 2 participants, 2 messages | 184 us | 176 us | 5,445 |
| sequence_medium | 5 participants, complex | 716 us | 695 us | 1,397 |
| sequence_large | 8 participants, 24 messages | 784 us | 766 us | 1,275 |
| class_small | 2 classes, 1 relationship | 289 us | 283 us | 3,462 |
| class_medium | 4 classes, complex | 544 us | 538 us | 1,837 |
| class_large | 12 classes, members + relationships | 1.59 ms | 1.58 ms | 628 |

*Last updated: 2026-03-26, merm v0.1.4*

## Key takeaways

- Small diagrams (< 5 nodes): **< 400 us** — fast enough for real-time preview
- Medium diagrams (~15 nodes): **~1.5 ms** — instant for batch rendering
- Large diagrams (50 nodes): **~5 ms** — suitable for CI/build pipelines
- Sequence diagrams are fastest (no Sugiyama layout needed)
- Class diagrams scale well with member count
