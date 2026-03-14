"""Performance benchmarks for the full render_diagram() pipeline.

Run benchmarks:
    uv run pytest tests/test_benchmarks.py --benchmark-only
    uv run pytest tests/test_benchmarks.py -v

Disable benchmarks (tests still pass):
    uv run pytest tests/test_benchmarks.py --benchmark-disable
"""

from pathlib import Path

from merm import render_diagram

FIXTURES = Path(__file__).parent / "fixtures" / "corpus"


# ---------------------------------------------------------------------------
# Helpers to generate diagrams that don't exist as fixtures
# ---------------------------------------------------------------------------

def _generate_large_sequence() -> str:
    """Generate a sequence diagram with 8 participants and 24 messages."""
    participants = [f"P{i}" for i in range(8)]
    lines = ["sequenceDiagram"]
    for p in participants:
        lines.append(f"    participant {p}")
    for i in range(24):
        src = participants[i % len(participants)]
        dst = participants[(i + 1) % len(participants)]
        arrow = "->>" if i % 2 == 0 else "-->>"
        lines.append(f"    {src}{arrow}{dst}: msg{i}")
    return "\n".join(lines)


def _generate_large_class() -> str:
    """Generate a class diagram with 12 classes, multiple members each."""
    lines = ["classDiagram"]
    for i in range(12):
        lines.append(f"    class C{i} {{")
        lines.append(f"        +int field{i}a")
        lines.append(f"        +String field{i}b")
        lines.append(f"        +process{i}() void")
        lines.append(f"        +get{i}() String")
        lines.append("    }")
    # relationships: chain + some extras
    for i in range(11):
        lines.append(f"    C{i} --> C{i + 1} : uses")
    lines.append("    C0 --> C5 : depends")
    lines.append("    C3 --> C9 : extends")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Flowchart benchmarks
# ---------------------------------------------------------------------------

def test_bench_flowchart_small(benchmark):
    """Benchmark a 3-node linear flowchart."""
    diagram = "flowchart TD\n    A --> B\n    B --> C"
    benchmark(render_diagram, diagram)


def test_bench_flowchart_medium(benchmark):
    """Benchmark a ~15-node flowchart from the medium fixture."""
    source = (FIXTURES / "scale" / "medium.mmd").read_text()
    benchmark(render_diagram, source)


def test_bench_flowchart_large(benchmark):
    """Benchmark a 50-node flowchart from the large fixture."""
    source = (FIXTURES / "scale" / "large.mmd").read_text()
    benchmark(render_diagram, source)


# ---------------------------------------------------------------------------
# Sequence diagram benchmarks
# ---------------------------------------------------------------------------

def test_bench_sequence_small(benchmark):
    """Benchmark a 2-participant, 2-message sequence diagram."""
    diagram = (
        "sequenceDiagram\n"
        "    participant A\n"
        "    participant B\n"
        "    A->>B: Hello\n"
        "    B-->>A: Reply"
    )
    benchmark(render_diagram, diagram)


def test_bench_sequence_medium(benchmark):
    """Benchmark a 5-participant sequence diagram from the complex fixture."""
    source = (FIXTURES / "sequence" / "complex.mmd").read_text()
    benchmark(render_diagram, source)


def test_bench_sequence_large(benchmark):
    """Benchmark a generated 8-participant, 24-message sequence diagram."""
    source = _generate_large_sequence()
    benchmark(render_diagram, source)


# ---------------------------------------------------------------------------
# Class diagram benchmarks
# ---------------------------------------------------------------------------

def test_bench_class_small(benchmark):
    """Benchmark a 2-class diagram with one relationship."""
    diagram = (
        "classDiagram\n"
        "    class Animal {\n"
        "        +String name\n"
        "        +speak() void\n"
        "    }\n"
        "    class Dog {\n"
        "        +fetch() void\n"
        "    }\n"
        "    Animal <|-- Dog"
    )
    benchmark(render_diagram, diagram)


def test_bench_class_medium(benchmark):
    """Benchmark a 4-class diagram from the complex fixture."""
    source = (FIXTURES / "class" / "complex.mmd").read_text()
    benchmark(render_diagram, source)


def test_bench_class_large(benchmark):
    """Benchmark a generated 12-class diagram with members and relationships."""
    source = _generate_large_class()
    benchmark(render_diagram, source)
