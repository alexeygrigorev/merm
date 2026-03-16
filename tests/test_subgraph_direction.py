"""Tests for per-subgraph direction support (issue 78).

Verifies that the `direction` directive inside subgraphs is respected:
nodes in a `direction LR` subgraph should be laid out horizontally,
while nodes in a `direction TB` subgraph should be laid out vertically,
regardless of the diagram-level direction.
"""

import xml.etree.ElementTree as ET

from merm import render_diagram
from merm.ir import Direction
from merm.layout.sugiyama import layout_diagram
from merm.measure.text import measure_text
from merm.parser.flowchart import parse_flowchart

_SVG_NS = "{http://www.w3.org/2000/svg}"

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _layout_centers(source: str) -> dict[str, tuple[float, float]]:
    """Parse and lay out a flowchart, returning node center positions."""
    diagram = parse_flowchart(source)
    result = layout_diagram(diagram, measure_text)
    centers: dict[str, tuple[float, float]] = {}
    for nid, nl in result.nodes.items():
        centers[nid] = (nl.x + nl.width / 2.0, nl.y + nl.height / 2.0)
    return centers


def _parse_node_centers_from_svg(svg_str: str) -> dict[str, tuple[float, float]]:
    """Extract node center positions from rendered SVG."""
    root = ET.fromstring(svg_str)
    result: dict[str, tuple[float, float]] = {}
    for g in root.iter(f"{_SVG_NS}g"):
        cls = g.get("class", "")
        if "node" not in cls:
            continue
        node_id = g.get("data-node-id")
        if node_id is None:
            continue
        rect = g.find(f"{_SVG_NS}rect")
        if rect is None:
            continue
        x = float(rect.get("x", "0"))
        y = float(rect.get("y", "0"))
        w = float(rect.get("width", "0"))
        h = float(rect.get("height", "0"))
        result[node_id] = (x + w / 2.0, y + h / 2.0)
    return result


# -------------------------------------------------------------------
# Parser tests
# -------------------------------------------------------------------

class TestSubgraphDirectionParsing:
    """Verify that the parser captures subgraph direction correctly."""

    def test_direction_lr_parsed(self):
        source = """flowchart TD
    subgraph sub1[LR Sub]
        direction LR
        A --> B
    end
"""
        diagram = parse_flowchart(source)
        assert len(diagram.subgraphs) == 1
        assert diagram.subgraphs[0].direction == Direction.LR

    def test_direction_tb_parsed(self):
        source = """flowchart TD
    subgraph sub1[TB Sub]
        direction TB
        A --> B
    end
"""
        diagram = parse_flowchart(source)
        assert diagram.subgraphs[0].direction == Direction.TD

    def test_direction_bt_parsed(self):
        source = """flowchart TD
    subgraph sub1
        direction BT
        A --> B
    end
"""
        diagram = parse_flowchart(source)
        assert diagram.subgraphs[0].direction == Direction.BT

    def test_direction_rl_parsed(self):
        source = """flowchart TD
    subgraph sub1
        direction RL
        A --> B
    end
"""
        diagram = parse_flowchart(source)
        assert diagram.subgraphs[0].direction == Direction.RL

    def test_no_direction_parsed_as_none(self):
        source = """flowchart TD
    subgraph sub1
        A --> B
    end
"""
        diagram = parse_flowchart(source)
        assert diagram.subgraphs[0].direction is None


# -------------------------------------------------------------------
# Layout tests: flowchart TD with subgraph direction overrides
# -------------------------------------------------------------------

class TestSubgraphDirectionLRInTD:
    """Subgraph with `direction LR` inside a `flowchart TD`."""

    def test_lr_subgraph_nodes_horizontal(self):
        """Nodes in a `direction LR` subgraph should have increasing x, ~same y."""
        source = """flowchart TD
    subgraph sub1[Left to Right]
        direction LR
        A --> B --> C
    end
"""
        centers = _layout_centers(source)
        ax, ay = centers["A"]
        bx, by = centers["B"]
        cx, cy = centers["C"]

        # Horizontal: increasing x
        assert ax < bx < cx, (
            f"Expected A.x < B.x < C.x, got {ax:.1f}, {bx:.1f}, {cx:.1f}"
        )
        # Same y (within tolerance)
        assert abs(ay - by) < 5.0, f"A.y={ay:.1f} vs B.y={by:.1f}"
        assert abs(by - cy) < 5.0, f"B.y={by:.1f} vs C.y={cy:.1f}"

    def test_tb_subgraph_unchanged(self):
        """Subgraph with `direction TB` in a TD diagram stays vertical."""
        source = """flowchart TD
    subgraph sub2[Top to Bottom]
        direction TB
        D --> E --> F
    end
"""
        centers = _layout_centers(source)
        dx, dy = centers["D"]
        ex, ey = centers["E"]
        fx, fy = centers["F"]

        # Vertical: increasing y
        assert dy < ey < fy, (
            f"Expected D.y < E.y < F.y, got {dy:.1f}, {ey:.1f}, {fy:.1f}"
        )
        # Same x (within tolerance)
        assert abs(dx - ex) < 5.0
        assert abs(ex - fx) < 5.0


class TestMixedSubgraphDirections:
    """Multiple subgraphs with different directions in one diagram."""

    def test_lr_and_tb_subgraphs_coexist(self):
        """One LR subgraph and one TB subgraph in a TD diagram."""
        source = """flowchart TD
    subgraph sub1[Left to Right]
        direction LR
        A --> B --> C
    end
    subgraph sub2[Top to Bottom]
        direction TB
        D --> E --> F
    end
    sub1 --> sub2
"""
        centers = _layout_centers(source)

        # sub1 should be horizontal
        assert centers["A"][0] < centers["B"][0] < centers["C"][0]
        assert abs(centers["A"][1] - centers["B"][1]) < 5.0

        # sub2 should be vertical
        assert centers["D"][1] < centers["E"][1] < centers["F"][1]
        assert abs(centers["D"][0] - centers["E"][0]) < 5.0


class TestSubgraphDirectionRL:
    """Subgraph with `direction RL` flows right-to-left."""

    def test_rl_subgraph_nodes_reversed_horizontal(self):
        source = """flowchart TD
    subgraph sub1
        direction RL
        A --> B --> C
    end
"""
        centers = _layout_centers(source)
        ax, ay = centers["A"]
        bx, by = centers["B"]
        cx, cy = centers["C"]

        # RL: A should be rightmost, C leftmost
        assert ax > bx > cx, (
            f"Expected A.x > B.x > C.x for RL, got {ax:.1f}, {bx:.1f}, {cx:.1f}"
        )
        # Same y
        assert abs(ay - by) < 5.0
        assert abs(by - cy) < 5.0


class TestSubgraphDirectionBT:
    """Subgraph with `direction BT` flows bottom-to-top."""

    def test_bt_subgraph_nodes_reversed_vertical(self):
        source = """flowchart TD
    subgraph sub1
        direction BT
        A --> B --> C
    end
"""
        centers = _layout_centers(source)
        ax, ay = centers["A"]
        bx, by = centers["B"]
        cx, cy = centers["C"]

        # BT: A should be bottommost, C topmost
        assert ay > by > cy, (
            f"Expected A.y > B.y > C.y for BT, got {ay:.1f}, {by:.1f}, {cy:.1f}"
        )
        # Same x
        assert abs(ax - bx) < 5.0
        assert abs(bx - cx) < 5.0


# -------------------------------------------------------------------
# Layout tests: flowchart LR with subgraph direction overrides
# -------------------------------------------------------------------

class TestSubgraphDirectionTBInLR:
    """Subgraph with `direction TB` inside a `flowchart LR`."""

    def test_tb_subgraph_in_lr_diagram(self):
        """Nodes in a `direction TB` subgraph inside LR diagram should be vertical."""
        source = """flowchart LR
    subgraph sub1[Top to Bottom]
        direction TB
        A --> B --> C
    end
"""
        centers = _layout_centers(source)
        ax, ay = centers["A"]
        bx, by = centers["B"]
        cx, cy = centers["C"]

        # Vertical: increasing y
        assert ay < by < cy, (
            f"Expected A.y < B.y < C.y, got {ay:.1f}, {by:.1f}, {cy:.1f}"
        )
        # Same x (within tolerance)
        assert abs(ax - bx) < 5.0, f"A.x={ax:.1f} vs B.x={bx:.1f}"
        assert abs(bx - cx) < 5.0, f"B.x={bx:.1f} vs C.x={cx:.1f}"


class TestSubgraphDirectionInheritance:
    """Subgraphs without explicit direction inherit the diagram direction."""

    def test_no_direction_inherits_diagram_td(self):
        """Subgraph without direction in TD diagram flows TD."""
        source = """flowchart TD
    subgraph sub1
        A --> B --> C
    end
"""
        centers = _layout_centers(source)
        # Should be vertical (inherits TD)
        assert centers["A"][1] < centers["B"][1] < centers["C"][1]
        assert abs(centers["A"][0] - centers["B"][0]) < 5.0

    def test_no_direction_inherits_diagram_lr(self):
        """Subgraph without direction in LR diagram flows LR."""
        source = """flowchart LR
    subgraph sub1
        A --> B --> C
    end
"""
        centers = _layout_centers(source)
        # Should be horizontal (inherits LR)
        assert centers["A"][0] < centers["B"][0] < centers["C"][0]
        assert abs(centers["A"][1] - centers["B"][1]) < 5.0


# -------------------------------------------------------------------
# End-to-end SVG rendering test
# -------------------------------------------------------------------

class TestSubgraphDirectionSVGRendering:
    """End-to-end test: render to SVG and verify node positions."""

    def test_render_mixed_directions(self):
        source = """flowchart TD
    subgraph sub1[Left to Right]
        direction LR
        A --> B --> C
    end
    subgraph sub2[Top to Bottom]
        direction TB
        D --> E --> F
    end
    sub1 --> sub2
"""
        svg = render_diagram(source)
        centers = _parse_node_centers_from_svg(svg)

        # Verify we found all nodes
        for nid in ["A", "B", "C", "D", "E", "F"]:
            assert nid in centers, f"Node {nid} not found in SVG"

        # sub1 (LR): horizontal
        assert centers["A"][0] < centers["B"][0] < centers["C"][0]

        # sub2 (TB): vertical
        assert centers["D"][1] < centers["E"][1] < centers["F"][1]
