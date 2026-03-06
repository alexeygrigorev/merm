"""Tests for LR flowchart node spacing (Issue 60).

Verifies that LR flowcharts have adequate gaps between adjacent nodes,
that gaps scale with node width, and that TB flowcharts are unaffected.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from merm import render_diagram

_SVG_NS = "{http://www.w3.org/2000/svg}"
_MIN_GAP = 20.0  # minimum acceptable gap in pixels


def _extract_node_rects(svg_str: str) -> list[dict]:
    """Extract node rectangles from SVG, sorted by x position.

    Returns list of dicts with keys: x, y, width, height, right, bottom.
    """
    root = ET.fromstring(svg_str)
    rects = []
    for rect in root.iter(f"{_SVG_NS}rect"):
        # Skip subgraph rects (they have data-subgraph-id)
        if rect.get("data-subgraph-id"):
            continue
        x = float(rect.get("x", 0))
        y = float(rect.get("y", 0))
        w = float(rect.get("width", 0))
        h = float(rect.get("height", 0))
        rects.append({
            "x": x, "y": y, "width": w, "height": h,
            "right": x + w, "bottom": y + h,
        })
    return rects


def _horizontal_gaps(rects: list[dict]) -> list[float]:
    """Compute horizontal gaps between adjacent rects sorted by x."""
    sorted_rects = sorted(rects, key=lambda r: r["x"])
    gaps = []
    for i in range(len(sorted_rects) - 1):
        gap = sorted_rects[i + 1]["x"] - sorted_rects[i]["right"]
        gaps.append(gap)
    return gaps


def _vertical_gaps(rects: list[dict]) -> list[float]:
    """Compute vertical gaps between adjacent rects sorted by y."""
    sorted_rects = sorted(rects, key=lambda r: r["y"])
    gaps = []
    for i in range(len(sorted_rects) - 1):
        gap = sorted_rects[i + 1]["y"] - sorted_rects[i]["bottom"]
        gaps.append(gap)
    return gaps


# -------------------------------------------------------------------
# Test: rag_pipeline.mmd has adequate gaps
# -------------------------------------------------------------------

class TestRagPipelineSpacing:
    """Tests for the rag_pipeline.mmd fixture."""

    @pytest.fixture()
    def svg(self) -> str:
        path = Path("tests/fixtures/github/rag_pipeline.mmd")
        return render_diagram(path.read_text())

    @pytest.fixture()
    def rects(self, svg: str) -> list[dict]:
        return _extract_node_rects(svg)

    def test_all_gaps_at_least_20px(self, rects: list[dict]):
        """Every adjacent node pair must have >= 20px horizontal gap."""
        gaps = _horizontal_gaps(rects)
        assert len(gaps) > 0, "Expected multiple nodes"
        for i, gap in enumerate(gaps):
            assert gap >= _MIN_GAP, (
                f"Gap between node {i} and {i+1} is {gap:.1f}px, "
                f"expected >= {_MIN_GAP}px"
            )

    def test_no_overlapping_nodes(self, rects: list[dict]):
        """No nodes should overlap horizontally."""
        gaps = _horizontal_gaps(rects)
        for i, gap in enumerate(gaps):
            assert gap > 0, f"Nodes {i} and {i+1} overlap by {-gap:.1f}px"

    def test_arrows_visible(self, svg: str, rects: list[dict]):
        """Arrows (paths or lines) should exist between nodes."""
        root = ET.fromstring(svg)
        # Count path elements (edges are rendered as paths)
        paths = list(root.iter(f"{_SVG_NS}path"))
        # rag_pipeline has 5 edges (A->B, B->C, C->D, D->E, E->F)
        assert len(paths) >= 5, (
            f"Expected at least 5 edge paths, found {len(paths)}"
        )


# -------------------------------------------------------------------
# Test: Synthetic LR graph with varying label lengths
# -------------------------------------------------------------------

class TestSyntheticLRVariableWidths:
    """LR graph with labels of varying lengths should not overlap."""

    CHART = """\
graph LR
    A[X] --> B[A moderately long label here]
    B --> C[Short]
    C --> D[This is quite a wide node with lots of text]
    D --> E[Y]
"""

    @pytest.fixture()
    def rects(self) -> list[dict]:
        svg = render_diagram(self.CHART)
        return _extract_node_rects(svg)

    def test_no_overlaps(self, rects: list[dict]):
        """No nodes should overlap regardless of width differences."""
        gaps = _horizontal_gaps(rects)
        for i, gap in enumerate(gaps):
            assert gap > 0, (
                f"Nodes {i} and {i+1} overlap by {-gap:.1f}px"
            )

    def test_all_gaps_at_least_20px(self, rects: list[dict]):
        """All gaps should be at least 20px."""
        gaps = _horizontal_gaps(rects)
        for i, gap in enumerate(gaps):
            assert gap >= _MIN_GAP, (
                f"Gap {i}->{i+1} is {gap:.1f}px, expected >= {_MIN_GAP}px"
            )


# -------------------------------------------------------------------
# Test: TB layout is unaffected
# -------------------------------------------------------------------

class TestTBLayoutUnaffected:
    """TB flowcharts should not be affected by the LR spacing fix."""

    CHART = """\
graph TB
    A[Start] --> B[Process Data]
    B --> C[End]
"""

    @pytest.fixture()
    def rects(self) -> list[dict]:
        svg = render_diagram(self.CHART)
        return _extract_node_rects(svg)

    def test_vertical_gaps_are_positive(self, rects: list[dict]):
        """TB layout should have positive vertical gaps."""
        gaps = _vertical_gaps(rects)
        assert len(gaps) > 0
        for i, gap in enumerate(gaps):
            assert gap > 0, f"TB nodes {i} and {i+1} overlap vertically"

    def test_vertical_gaps_match_rank_sep(self, rects: list[dict]):
        """TB vertical gaps should equal rank_sep (40px default)."""
        gaps = _vertical_gaps(rects)
        for gap in gaps:
            assert abs(gap - 40.0) < 1.0, (
                f"TB gap {gap:.1f}px, expected ~40px"
            )


# -------------------------------------------------------------------
# Test: Gap scales with node width
# -------------------------------------------------------------------

class TestGapScalesWithWidth:
    """Wider nodes should result in adequate spacing."""

    NARROW = """\
graph LR
    A[X] --> B[Y]
"""
    WIDE = """\
graph LR
    A[This is a very wide node] --> B[Another wide node here]
"""

    def test_wide_nodes_have_adequate_gaps(self):
        """Wide node LR charts should still have >= 20px gaps."""
        svg = render_diagram(self.WIDE)
        rects = _extract_node_rects(svg)
        gaps = _horizontal_gaps(rects)
        for i, gap in enumerate(gaps):
            assert gap >= _MIN_GAP, (
                f"Wide node gap {i} is {gap:.1f}px, expected >= {_MIN_GAP}px"
            )

    def test_narrow_nodes_have_adequate_gaps(self):
        """Narrow node LR charts should also have >= 20px gaps."""
        svg = render_diagram(self.NARROW)
        rects = _extract_node_rects(svg)
        gaps = _horizontal_gaps(rects)
        for i, gap in enumerate(gaps):
            assert gap >= _MIN_GAP, (
                f"Narrow node gap {i} is {gap:.1f}px, expected >= {_MIN_GAP}px"
            )
