"""Tests for LR flowchart with subgraphs layout (Task 55).

Verifies that `flowchart LR` diagrams with multiple subgraphs render
correctly: subgraphs flow left-to-right, do not overlap, internal nodes
are ordered correctly, cross-subgraph edges flow horizontally, and
edge labels are positioned properly.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from merm import render_diagram

_SVG_NS = "{http://www.w3.org/2000/svg}"

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _parse_subgraph_rects(svg_str: str) -> dict[str, dict]:
    """Parse SVG and extract subgraph bounding boxes.

    Returns a dict keyed by data-subgraph-id with values:
    {"x": float, "y": float, "width": float, "height": float,
     "center_x": float, "center_y": float}
    """
    root = ET.fromstring(svg_str)
    result: dict[str, dict] = {}

    for g in root.iter(f"{_SVG_NS}g"):
        cls = g.get("class", "")
        if "subgraph" not in cls:
            continue
        sg_id = g.get("data-subgraph-id")
        if sg_id is None:
            continue

        rect = g.find(f"{_SVG_NS}rect")
        if rect is None:
            rect = g.find("rect")
        if rect is None:
            continue

        x = float(rect.get("x", "0"))
        y = float(rect.get("y", "0"))
        w = float(rect.get("width", "0"))
        h = float(rect.get("height", "0"))
        result[sg_id] = {
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "center_x": x + w / 2.0,
            "center_y": y + h / 2.0,
        }

    return result

def _parse_node_positions(svg_str: str) -> dict[str, dict]:
    """Parse SVG and extract node bounding boxes.

    Returns a dict keyed by data-node-id with values:
    {"x": float, "y": float, "width": float, "height": float,
     "center_x": float, "center_y": float}
    """
    root = ET.fromstring(svg_str)
    result: dict[str, dict] = {}

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

        result[node_id] = {
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "center_x": x + w / 2.0,
            "center_y": y + h / 2.0,
        }

    return result

def _rects_overlap(
    a: dict, b: dict, tolerance: float = 1.0,
) -> bool:
    """Check if two rects overlap (with tolerance)."""
    ax2 = a["x"] + a["width"] - tolerance
    bx2 = b["x"] + b["width"] - tolerance
    ay2 = a["y"] + a["height"] - tolerance
    by2 = b["y"] + b["height"] - tolerance
    x_overlap = a["x"] < bx2 and b["x"] < ax2
    y_overlap = a["y"] < by2 and b["y"] < ay2
    return x_overlap and y_overlap

# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
CI_PIPELINE_PATH = (
    _FIXTURE_DIR / "corpus" / "flowchart" / "ci_pipeline.mmd"
)

@pytest.fixture()
def ci_pipeline_svg() -> str:
    """Render ci_pipeline.mmd and return the SVG string."""
    source = CI_PIPELINE_PATH.read_text()
    return render_diagram(source)

# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------

class TestLRSubgraphHorizontalOrdering:
    """Build, Test, Deploy subgraphs ordered left-to-right."""

    def test_lr_ordering(self, ci_pipeline_svg: str):
        rects = _parse_subgraph_rects(ci_pipeline_svg)
        for name in ("Build", "Test", "Deploy"):
            assert name in rects, (
                f"{name} not found. Got: {list(rects.keys())}"
            )

        build_cx = rects["Build"]["center_x"]
        test_cx = rects["Test"]["center_x"]
        deploy_cx = rects["Deploy"]["center_x"]

        assert build_cx < test_cx, (
            f"Build cx ({build_cx}) should be < "
            f"Test cx ({test_cx})"
        )
        assert test_cx < deploy_cx, (
            f"Test cx ({test_cx}) should be < "
            f"Deploy cx ({deploy_cx})"
        )

class TestLRSubgraphNoOverlap:
    """No pair of the 3 subgraph rects should overlap."""

    def test_no_overlap(self, ci_pipeline_svg: str):
        rects = _parse_subgraph_rects(ci_pipeline_svg)
        names = ["Build", "Test", "Deploy"]
        for name in names:
            assert name in rects, f"{name} not found"

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                assert not _rects_overlap(
                    rects[a], rects[b],
                ), (
                    f"{a} and {b} overlap: "
                    f"{rects[a]} vs {rects[b]}"
                )

class TestLRSubgraphVerticalAlignment:
    """In LR mode, subgraphs should be roughly vertically aligned.

    The subgraphs should sit side-by-side horizontally, meaning their
    vertical center positions should be within a reasonable range of
    each other, not scattered across the full height of the diagram.
    """

    def test_subgraphs_vertically_aligned(self, ci_pipeline_svg: str):
        rects = _parse_subgraph_rects(ci_pipeline_svg)
        for name in ("Build", "Test", "Deploy"):
            assert name in rects, f"{name} not found"

        centers_y = [
            rects["Build"]["center_y"],
            rects["Test"]["center_y"],
            rects["Deploy"]["center_y"],
        ]
        min_cy = min(centers_y)
        max_cy = max(centers_y)
        spread = max_cy - min_cy

        # The vertical spread of subgraph centers should be small
        # relative to the diagram height. A tolerance of 200px allows
        # for differing subgraph heights while catching the broken
        # layout where subgraphs are scattered hundreds of pixels apart.
        max_allowed_spread = 200.0
        assert spread < max_allowed_spread, (
            f"Subgraph center_y values are too spread out "
            f"(spread={spread:.1f}px, max={max_allowed_spread}px). "
            f"Build cy={centers_y[0]:.1f}, "
            f"Test cy={centers_y[1]:.1f}, "
            f"Deploy cy={centers_y[2]:.1f}. "
            f"In LR mode, subgraphs should be roughly "
            f"vertically aligned (side by side)."
        )

class TestInternalNodeOrdering:
    """Nodes within Build subgraph flow left-to-right."""

    def test_build_node_ordering(self, ci_pipeline_svg: str):
        nodes = _parse_node_positions(ci_pipeline_svg)
        for nid in ("A", "B", "C"):
            assert nid in nodes, (
                f"Node {nid} not found. "
                f"Got: {list(nodes.keys())}"
            )

        a_cx = nodes["A"]["center_x"]
        b_cx = nodes["B"]["center_x"]
        c_cx = nodes["C"]["center_x"]

        assert a_cx < b_cx, (
            f"A cx ({a_cx}) should be < B cx ({b_cx})"
        )
        assert b_cx < c_cx, (
            f"B cx ({b_cx}) should be < C cx ({c_cx})"
        )

class TestCrossSubgraphEdges:
    """Cross-subgraph edges should flow left-to-right."""

    def test_build_to_test_edges_flow_lr(
        self, ci_pipeline_svg: str,
    ):
        nodes = _parse_node_positions(ci_pipeline_svg)
        # C=Compile, D=Unit Tests, E=Integration Tests
        for target in ["D", "E"]:
            if target not in nodes:
                pytest.skip(f"Node {target} not found")
            c_cx = nodes["C"]["center_x"]
            t_cx = nodes[target]["center_x"]
            assert c_cx < t_cx, (
                f"C cx ({c_cx}) should be "
                f"< {target} cx ({t_cx})"
            )

class TestEdgeLabelPositioning:
    """The 'Approved' label sits between F and G nodes."""

    def test_approved_label_between_nodes(
        self, ci_pipeline_svg: str,
    ):
        nodes = _parse_node_positions(ci_pipeline_svg)
        assert "F" in nodes and "G" in nodes, (
            "Nodes F and G must be present"
        )

        f_cx = nodes["F"]["center_x"]
        g_cx = nodes["G"]["center_x"]

        root = ET.fromstring(ci_pipeline_svg)
        approved_text = None
        for text_el in root.iter(f"{_SVG_NS}text"):
            if text_el.text and "Approved" in text_el.text:
                approved_text = text_el
                break
            for tspan in text_el:
                if tspan.text and "Approved" in tspan.text:
                    approved_text = text_el
                    break

        assert approved_text is not None, (
            "Could not find 'Approved' text label"
        )

        label_x = float(approved_text.get("x", "0"))
        lo = min(f_cx, g_cx)
        hi = max(f_cx, g_cx)

        assert lo <= label_x <= hi, (
            f"'Approved' x ({label_x}) should be "
            f"between F cx ({f_cx}) and G cx ({g_cx})"
        )

class TestTDRegression:
    """flowchart TD with 2 subgraphs still works."""

    def test_td_subgraphs_no_overlap_and_ordered(self):
        source = """flowchart TD
    subgraph Frontend
        A[Component] --> B[Page]
    end
    subgraph Backend
        C[API] --> D[Database]
    end
    B --> C
"""
        svg = render_diagram(source)
        rects = _parse_subgraph_rects(svg)

        for name in ("Frontend", "Backend"):
            assert name in rects, (
                f"{name} not found. "
                f"Got: {list(rects.keys())}"
            )

        assert not _rects_overlap(
            rects["Frontend"], rects["Backend"],
        ), (
            f"Frontend and Backend overlap: "
            f"{rects['Frontend']} vs {rects['Backend']}"
        )

        fe_cy = rects["Frontend"]["center_y"]
        be_cy = rects["Backend"]["center_y"]
        assert fe_cy < be_cy, (
            f"Frontend cy ({fe_cy}) should be "
            f"< Backend cy ({be_cy})"
        )

class TestRLDirection:
    """flowchart RL should reverse the ordering."""

    def test_rl_reversed_ordering(self):
        source = """flowchart RL
    subgraph Build
        A[Checkout] --> B[Restore]
        B --> C[Compile]
    end
    subgraph Test
        D[Unit Tests]
        E[Integration Tests]
    end
    subgraph Deploy
        F[Staging]
        G[Production]
    end
    C --> D
    C --> E
    D --> F
    E --> F
    F -->|Approved| G
"""
        svg = render_diagram(source)
        rects = _parse_subgraph_rects(svg)

        assert "Build" in rects
        assert "Test" in rects
        assert "Deploy" in rects

        deploy_cx = rects["Deploy"]["center_x"]
        test_cx = rects["Test"]["center_x"]
        build_cx = rects["Build"]["center_x"]

        assert deploy_cx < test_cx, (
            f"Deploy cx ({deploy_cx}) should be "
            f"< Test cx ({test_cx})"
        )
        assert test_cx < build_cx, (
            f"Test cx ({test_cx}) should be "
            f"< Build cx ({build_cx})"
        )
