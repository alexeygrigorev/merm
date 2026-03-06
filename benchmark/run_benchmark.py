#!/usr/bin/env python3
"""
Benchmark pymermaid rendering performance vs mmdc (mermaid-cli).

Measures parse time, layout time, render time, and total time for pymermaid,
and compares with mmdc end-to-end time. Runs across multiple scenarios of
varying complexity.

Usage:
    uv run benchmark/run_benchmark.py
    uv run benchmark/run_benchmark.py --no-mmdc      # skip mmdc comparison
    uv run benchmark/run_benchmark.py --iterations 50 # custom iteration count
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pymermaid import render_diagram
from pymermaid.parser.flowchart import parse_flowchart
from pymermaid.layout.sugiyama import layout_diagram
from pymermaid.render.svg import render_svg

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
RESULTS_DIR = Path(__file__).parent / "results"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_time(seconds: float) -> str:
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.0f} µs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.2f} s"


def format_memory(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    else:
        return f"{bytes_val / (1024 * 1024):.1f} MB"


def measure_time(func, *args, iterations=1, **kwargs):
    """Run func N times, return (result, total_seconds, per_call_seconds)."""
    # Warmup
    result = func(*args, **kwargs)
    start = time.perf_counter()
    for _ in range(iterations):
        func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed, elapsed / iterations


def measure_memory(func, *args, **kwargs):
    """Measure peak memory of a single call."""
    tracemalloc.start()
    result = func(*args, **kwargs)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, peak


# ---------------------------------------------------------------------------
# Scenario collection
# ---------------------------------------------------------------------------

def collect_scenarios() -> list[dict]:
    """Collect benchmark scenarios from scenarios/ dir and fixtures."""
    scenarios = []

    # Custom scenarios in benchmark/scenarios/
    for mmd in sorted(SCENARIOS_DIR.glob("*.mmd")):
        scenarios.append({
            "name": mmd.stem,
            "path": str(mmd),
            "source": mmd.read_text(),
            "category": "synthetic",
        })

    # Real-world fixtures from tests/fixtures/github/
    for mmd in sorted(FIXTURES_DIR.glob("github/*.mmd")):
        scenarios.append({
            "name": f"github/{mmd.stem}",
            "path": str(mmd),
            "source": mmd.read_text(),
            "category": "real-world",
        })

    # Corpus samples (one per category for variety)
    for category in ["basic", "edges", "shapes", "subgraphs", "direction"]:
        mmds = sorted(FIXTURES_DIR.glob(f"corpus/flowchart/{category}/*.mmd"))
        if mmds:
            # Pick the largest file in each category
            largest = max(mmds, key=lambda p: p.stat().st_size)
            scenarios.append({
                "name": f"corpus/{category}/{largest.stem}",
                "path": str(largest),
                "source": largest.read_text(),
                "category": "corpus",
            })

    # Non-flowchart types
    for dtype in ["sequence", "class", "state", "er", "gantt", "mindmap", "gitgraph", "pie"]:
        mmds = sorted(FIXTURES_DIR.glob(f"corpus/{dtype}/*.mmd"))
        if mmds:
            largest = max(mmds, key=lambda p: p.stat().st_size)
            scenarios.append({
                "name": f"corpus/{dtype}/{largest.stem}",
                "path": str(largest),
                "source": largest.read_text(),
                "category": "corpus",
            })

    return scenarios


# ---------------------------------------------------------------------------
# Benchmark runners
# ---------------------------------------------------------------------------

def bench_pymermaid(source: str, iterations: int) -> dict:
    """Benchmark pymermaid rendering, returning timing breakdown."""
    # Total end-to-end
    _, total_elapsed, total_per = measure_time(
        render_diagram, source, iterations=iterations,
    )

    # Memory for a single render
    _, peak_mem = measure_memory(render_diagram, source)

    # Breakdown: parse + layout + render (flowchart only)
    breakdown = {}
    first_line = source.strip().split("\n")[0].lower()
    is_flowchart = any(kw in first_line for kw in ["graph ", "flowchart "])
    if is_flowchart:
        try:
            _, _, parse_per = measure_time(
                parse_flowchart, source, iterations=iterations,
            )
            diagram = parse_flowchart(source)
            _, _, layout_per = measure_time(
                layout_diagram, diagram, iterations=iterations,
            )
            layout = layout_diagram(diagram)
            _, _, render_per = measure_time(
                render_svg, diagram, layout, iterations=iterations,
            )
            breakdown = {
                "parse_ms": parse_per * 1000,
                "layout_ms": layout_per * 1000,
                "render_ms": render_per * 1000,
            }
        except Exception:
            pass

    return {
        "total_ms": total_per * 1000,
        "iterations": iterations,
        "peak_memory_bytes": peak_mem,
        **breakdown,
    }


def bench_mmdc(source: str, iterations: int) -> dict | None:
    """Benchmark mmdc (mermaid-cli) rendering."""
    with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False) as f:
        f.write(source)
        input_path = f.name

    output_path = input_path.replace(".mmd", ".svg")

    try:
        # Warmup (first run is slow due to Puppeteer startup)
        subprocess.run(
            ["mmdc", "-i", input_path, "-o", output_path, "-q"],
            capture_output=True, timeout=30,
        )

        start = time.perf_counter()
        for _ in range(iterations):
            subprocess.run(
                ["mmdc", "-i", input_path, "-o", output_path, "-q"],
                capture_output=True, timeout=30,
            )
        elapsed = time.perf_counter() - start

        return {
            "total_ms": (elapsed / iterations) * 1000,
            "iterations": iterations,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    finally:
        for p in [input_path, output_path]:
            if os.path.exists(p):
                os.unlink(p)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_benchmark(iterations: int = 100, mmdc_iterations: int = 3,
                  skip_mmdc: bool = False) -> list[dict]:
    scenarios = collect_scenarios()
    print(f"Collected {len(scenarios)} scenarios")
    print(f"pymermaid iterations: {iterations}, mmdc iterations: {mmdc_iterations}")
    print()

    # Header
    print(f"{'Scenario':<45} {'pymermaid':>10} {'mmdc':>10} {'Speedup':>10} {'Memory':>10}")
    print("-" * 90)

    results = []
    for sc in scenarios:
        name = sc["name"]
        source = sc["source"]
        lines = len(source.strip().split("\n"))

        # pymermaid
        try:
            pm = bench_pymermaid(source, iterations)
        except Exception as e:
            pm = {"total_ms": -1, "error": str(e)}

        # mmdc
        mm = None
        if not skip_mmdc and pm.get("total_ms", -1) >= 0:
            mm = bench_mmdc(source, mmdc_iterations)

        # Format output
        pm_time = format_time(pm["total_ms"] / 1000) if pm["total_ms"] >= 0 else "ERROR"
        mm_time = format_time(mm["total_ms"] / 1000) if mm else "—"
        speedup = ""
        if mm and pm["total_ms"] > 0:
            ratio = mm["total_ms"] / pm["total_ms"]
            speedup = f"{ratio:.0f}x"

        mem = format_memory(pm.get("peak_memory_bytes", 0))

        print(f"{name:<45} {pm_time:>10} {mm_time:>10} {speedup:>10} {mem:>10}")

        result = {
            "name": name,
            "category": sc["category"],
            "lines": lines,
            "pymermaid": pm,
        }
        if mm:
            result["mmdc"] = mm
        results.append(result)

    # Summary
    print()
    print("=" * 90)
    pm_times = [r["pymermaid"]["total_ms"] for r in results if r["pymermaid"].get("total_ms", -1) > 0]
    if pm_times:
        print(f"pymermaid  avg: {sum(pm_times)/len(pm_times):.2f} ms  "
              f"min: {min(pm_times):.2f} ms  max: {max(pm_times):.2f} ms  "
              f"({len(pm_times)} scenarios)")

    mm_times = [r["mmdc"]["total_ms"] for r in results if "mmdc" in r]
    if mm_times:
        print(f"mmdc       avg: {sum(mm_times)/len(mm_times):.0f} ms  "
              f"min: {min(mm_times):.0f} ms  max: {max(mm_times):.0f} ms  "
              f"({len(mm_times)} scenarios)")
        if pm_times and mm_times:
            avg_speedup = (sum(mm_times) / len(mm_times)) / (sum(pm_times) / len(pm_times))
            print(f"Average speedup: {avg_speedup:.0f}x")

    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark pymermaid vs mmdc")
    parser.add_argument("--iterations", type=int, default=100,
                        help="pymermaid iterations per scenario (default: 100)")
    parser.add_argument("--mmdc-iterations", type=int, default=3,
                        help="mmdc iterations per scenario (default: 3)")
    parser.add_argument("--no-mmdc", action="store_true",
                        help="Skip mmdc comparison")
    parser.add_argument("--save", action="store_true",
                        help="Save results to benchmark/results/")
    args = parser.parse_args()

    results = run_benchmark(
        iterations=args.iterations,
        mmdc_iterations=args.mmdc_iterations,
        skip_mmdc=args.no_mmdc,
    )

    if args.save:
        RESULTS_DIR.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out_path = RESULTS_DIR / f"benchmark_{timestamp}.json"
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
