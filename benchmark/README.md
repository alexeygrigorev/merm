# merm Benchmarks

Performance benchmarks comparing merm (pure Python) against mmdc (mermaid-cli, Node.js + Puppeteer).

## Running

```bash
# Full benchmark with mmdc comparison
uv run benchmark/run_benchmark.py --save

# merm only (skip mmdc)
uv run benchmark/run_benchmark.py --no-mmdc

# Custom iterations
uv run benchmark/run_benchmark.py --iterations 200 --mmdc-iterations 5
```

## Scenarios

**Synthetic** (`benchmark/scenarios/`):
- `small_linear` — 5-node chain (baseline)
- `medium_branching` — fan-out/fan-in with 15 nodes
- `large_chain_50` — 50-node linear chain (stress test)
- `wide_fan` — 10-way fan with 33 nodes
- `nested_subgraphs` — 3 levels of nesting
- `mixed_shapes` — all supported shape types
- `lr_complex` — left-to-right with subgraphs

**Real-world** (`tests/fixtures/github/`):
- CI pipelines, ETL flows, API request handling, registration flows, etc.

**Corpus** (`tests/fixtures/corpus/`):
- One representative from each diagram type: sequence, class, state, ER, gantt, mindmap, gitgraph, pie

## Results

Results are saved as JSON in `benchmark/results/` with timestamps.

Each result includes:
- `total_ms` — end-to-end render time
- `parse_ms`, `layout_ms`, `render_ms` — breakdown (flowcharts only)
- `peak_memory_bytes` — peak memory for a single render
- `mmdc.total_ms` — mmdc comparison time (when available)
