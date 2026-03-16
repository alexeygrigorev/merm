"""Tests for mindmap layout whitespace reduction (issue 86)."""

from pathlib import Path

import pytest

from merm.layout.mindmap import layout_mindmap
from merm.measure.text import measure_text
from merm.parser.mindmap import parse_mindmap

FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "mindmap"


def _whitespace_ratio(layout) -> float:
    """Compute 1 - (node_area / total_area)."""
    total_area = layout.width * layout.height
    if total_area == 0:
        return 0.0
    node_area = sum(n.width * n.height for n in layout.nodes.values())
    return 1 - (node_area / total_area)


def _has_overlaps(layout) -> list[tuple[str, str]]:
    """Return pairs of node IDs that overlap (axis-aligned bounding box)."""
    nodes = list(layout.nodes.items())
    overlaps = []
    for i in range(len(nodes)):
        id_i, n_i = nodes[i]
        for j in range(i + 1, len(nodes)):
            id_j, n_j = nodes[j]
            if (
                abs(n_i.x - n_j.x) < (n_i.width + n_j.width) / 2
                and abs(n_i.y - n_j.y) < (n_i.height + n_j.height) / 2
            ):
                overlaps.append((id_i, id_j))
    return overlaps


class TestDeepTreeWhitespace:
    """The deep_tree fixture should have under 60% whitespace."""

    @pytest.fixture
    def deep_tree_layout(self):
        text = (FIXTURES / "deep_tree.mmd").read_text()
        diagram = parse_mindmap(text)
        return layout_mindmap(diagram, measure_text)

    def test_whitespace_under_60_percent(self, deep_tree_layout):
        ratio = _whitespace_ratio(deep_tree_layout)
        assert ratio < 0.60, (
            f"Whitespace ratio {ratio:.2%} exceeds 60% target"
        )

    def test_no_overlapping_nodes(self, deep_tree_layout):
        overlaps = _has_overlaps(deep_tree_layout)
        assert overlaps == [], f"Overlapping nodes: {overlaps}"

    def test_all_nodes_present(self, deep_tree_layout):
        assert len(deep_tree_layout.nodes) == 17

    def test_bounding_box_reasonable(self, deep_tree_layout):
        """Canvas should be significantly smaller than the old 1771x1640."""
        assert deep_tree_layout.width < 1000
        assert deep_tree_layout.height < 500


class TestMindmapWhitespaceGeneral:
    """All mindmap fixtures should have compact layouts."""

    @pytest.fixture(params=sorted(FIXTURES.glob("*.mmd")), ids=lambda p: p.stem)
    def fixture_layout(self, request):
        text = request.param.read_text()
        diagram = parse_mindmap(text)
        return layout_mindmap(diagram, measure_text)

    def test_no_overlapping_nodes(self, fixture_layout):
        overlaps = _has_overlaps(fixture_layout)
        assert overlaps == [], f"Overlapping nodes: {overlaps}"

    def test_whitespace_under_70_percent(self, fixture_layout):
        """All mindmaps should be reasonably compact (under 70%)."""
        ratio = _whitespace_ratio(fixture_layout)
        assert ratio < 0.70, (
            f"Whitespace ratio {ratio:.2%} exceeds 70% threshold"
        )


class TestMindmapLayoutProperties:
    """Verify structural properties of the new compact layout."""

    def test_root_centered_horizontally(self):
        """Root should be roughly in the middle of the canvas horizontally."""
        text = (FIXTURES / "deep_tree.mmd").read_text()
        diagram = parse_mindmap(text)
        layout = layout_mindmap(diagram, measure_text)
        root = layout.nodes["root"]
        mid_x = layout.width / 2
        # Root should be within 30% of center
        assert abs(root.x - mid_x) < layout.width * 0.3

    def test_children_on_both_sides(self):
        """For trees with multiple children, nodes should extend both left
        and right of the root."""
        text = (FIXTURES / "deep_tree.mmd").read_text()
        diagram = parse_mindmap(text)
        layout = layout_mindmap(diagram, measure_text)
        root = layout.nodes["root"]
        left_count = sum(
            1 for nid, n in layout.nodes.items()
            if nid != "root" and n.x < root.x
        )
        right_count = sum(
            1 for nid, n in layout.nodes.items()
            if nid != "root" and n.x > root.x
        )
        assert left_count > 0, "No nodes to the left of root"
        assert right_count > 0, "No nodes to the right of root"

    def test_canvas_smaller_than_before(self):
        """Canvas area should be at most 30% of the old 1771x1640 area."""
        text = (FIXTURES / "deep_tree.mmd").read_text()
        diagram = parse_mindmap(text)
        layout = layout_mindmap(diagram, measure_text)
        old_area = 1771 * 1640
        new_area = layout.width * layout.height
        assert new_area < old_area * 0.30, (
            f"New area {new_area:.0f} is not much smaller than old {old_area}"
        )
