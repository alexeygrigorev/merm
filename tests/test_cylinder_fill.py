"""Tests for cylinder shape rendering — top ellipse must match body fill."""

import re

from merm import render_diagram
from merm.render.shapes import CylinderRenderer


class TestCylinderTopEllipseFill:
    """The cylinder top ellipse must have the same fill as the body."""

    def test_cylinder_renderer_produces_two_paths(self):
        """CylinderRenderer should produce two <path> elements (body + top)."""
        renderer = CylinderRenderer()
        elements = renderer.render(0, 0, 80, 60, "Test", {"fill": "#cde498"})
        assert len(elements) == 2
        assert elements[0].startswith("<path")
        assert elements[1].startswith("<path")

    def test_cylinder_both_paths_have_same_fill(self):
        """Both path elements must carry the same fill style."""
        renderer = CylinderRenderer()
        style = {"fill": "#cde498", "stroke": "#000"}
        elements = renderer.render(0, 0, 80, 60, "DB", style)

        fill_pattern = re.compile(r"fill:(#[0-9a-fA-F]+)")
        fills = []
        for el in elements:
            m = fill_pattern.search(el)
            assert m, f"Expected fill in element: {el}"
            fills.append(m.group(1))

        assert fills[0] == fills[1], (
            f"Body fill {fills[0]} != top ellipse fill {fills[1]}"
        )

    def test_cylinder_top_ellipse_is_closed(self):
        """The top ellipse path should form a full ellipse (two arcs)."""
        renderer = CylinderRenderer()
        elements = renderer.render(10, 20, 100, 80, "X", None)
        top_path = elements[1]
        # Extract d attribute
        d_match = re.search(r'd="([^"]+)"', top_path)
        assert d_match
        d = d_match.group(1)
        # Should have two arcs (A commands) forming a full ellipse
        arcs = re.findall(r"A ", d)
        assert len(arcs) == 2, f"Expected 2 arcs in top ellipse, got {len(arcs)}"

    def test_full_cylinder_diagram_renders(self):
        """A complete flowchart with cylinder nodes should render without error."""
        mmd = 'graph TD\n    A[("Cylinder")] --> B[("Database")]'
        svg = render_diagram(mmd)
        assert "<svg" in svg
        # Should contain path elements for cylinders
        assert "<path" in svg

    def test_cylinder_no_white_top(self):
        """The rendered SVG should not have a white-filled top ellipse."""
        mmd = 'graph TD\n    A[("Cylinder")]'
        svg = render_diagram(mmd)
        # Count path elements — cylinder produces 2 paths
        paths = re.findall(r'<path [^>]*>', svg)
        # None of the paths should have fill:white or fill:#fff while others differ
        fills = []
        for p in paths:
            m = re.search(r'fill:(#[0-9a-fA-F]+|[a-z]+)', p)
            if m:
                fills.append(m.group(1))
        # All fills from cylinder paths should be the same
        if len(fills) >= 2:
            assert len(set(fills)) == 1, (
                f"Cylinder paths have different fills: {fills}"
            )
