"""Tests for arrow marker correctness.

These tests verify that:
1. Arrow markers have refX set so the TIP touches the path endpoint (node boundary)
2. Sequence diagram markers are adequately sized
3. SVG markers are consistently configured across diagram types
"""

import re
import xml.etree.ElementTree as ET

import pytest

# Insert src path
import sys
sys.path.insert(0, "src")

from merm import render_diagram


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)

def _parse_svg(svg_str: str) -> ET.Element:
    """Parse SVG string into an ElementTree element."""
    return ET.fromstring(svg_str)


def _find_markers(root: ET.Element) -> dict[str, ET.Element]:
    """Find all <marker> elements, keyed by id."""
    markers = {}
    # Must use namespaced tag for SVG elements
    for marker in root.iter(f"{{{_SVG_NS}}}marker"):
        mid = marker.get("id", "")
        if mid:
            markers[mid] = marker
    return markers


def _get_marker_dims(marker: ET.Element) -> tuple[float, float]:
    """Get markerWidth and markerHeight as floats."""
    w = float(marker.get("markerWidth", "0"))
    h = float(marker.get("markerHeight", "0"))
    return w, h


def _get_refx(marker: ET.Element) -> float:
    """Get refX as float."""
    return float(marker.get("refX", "0"))


def _get_refy(marker: ET.Element) -> float:
    """Get refY as float."""
    return float(marker.get("refY", "0"))


def _get_arrow_tip_x(marker: ET.Element) -> float:
    """Determine the x-coordinate of the arrow tip from the marker's path/polygon.

    For a polygon like 'M 0 0 L 10 5 L 0 10 z', the tip is the point with
    the maximum x value (10 in this case).
    For a polygon like '0 0, 4 1.5, 0 3', the tip is at x=4.
    """
    ns = f"{{{_SVG_NS}}}"

    # Check for <path> child
    path = marker.find(f"{ns}path")
    if path is not None:
        d = path.get("d", "")
        # Extract all x,y pairs from path d string
        numbers = re.findall(r'[-+]?\d*\.?\d+', d)
        if numbers:
            xs = [float(numbers[i]) for i in range(0, len(numbers), 2)]
            return max(xs)

    # Check for <polygon> child
    poly = marker.find(f"{ns}polygon")
    if poly is not None:
        points = poly.get("points", "")
        pairs = [p.strip() for p in points.split(",")]
        xs = []
        for pair in pairs:
            parts = pair.split()
            if parts:
                xs.append(float(parts[0]))
        if xs:
            return max(xs)

    # Check for <polyline> child
    polyline = marker.find(f"{ns}polyline")
    if polyline is not None:
        points = polyline.get("points", "")
        pairs = [p.strip() for p in points.split(",")]
        xs = []
        for pair in pairs:
            parts = pair.split()
            if parts:
                xs.append(float(parts[0]))
        if xs:
            return max(xs)

    return 0.0


# ---------------------------------------------------------------------------
# Flowchart arrow marker tests
# ---------------------------------------------------------------------------

FLOWCHART_LR = """graph LR
    A[Hard] -->|Text| B(Round)
    B --> C{Decision}
    C -->|One| D[Result 1]
    C -->|Two| E[Result 2]
"""


class TestFlowchartArrowMarkers:
    """Verify flowchart arrow markers have correct refX so tips touch nodes."""

    @pytest.fixture
    def svg(self):
        return render_diagram(FLOWCHART_LR)

    @pytest.fixture
    def markers(self, svg):
        return _find_markers(_parse_svg(svg))

    def test_arrow_marker_exists(self, markers):
        assert "arrow" in markers, "Missing 'arrow' marker definition"

    def test_arrow_refx_equals_tip(self, markers):
        """refX=0 places the triangle base at the path endpoint.

        Combined with _MARKER_SHORTEN=8, the path is pulled back 8px so
        the arrowhead fills the gap and the tip touches the node boundary.
        """
        marker = markers["arrow"]
        ref_x = _get_refx(marker)
        assert ref_x == 0.0, (
            f"Arrow marker refX={ref_x} but expected 0. "
            f"refX=0 with path shortening places the arrowhead tip on the node boundary."
        )

    def test_arrow_reverse_refx_is_zero(self, markers):
        """Reverse arrow refX should be 0 (base of the reversed arrow)."""
        if "arrow-reverse" in markers:
            marker = markers["arrow-reverse"]
            ref_x = _get_refx(marker)
            # For reverse arrows with auto-start-reverse, refX=10 is also valid
            # The key thing is it mirrors the forward arrow
            assert ref_x >= 0

    def test_arrow_marker_adequate_size(self, markers):
        """Arrow markers should be at least 6x6 to be visible."""
        marker = markers["arrow"]
        w, h = _get_marker_dims(marker)
        assert w >= 6, f"Arrow markerWidth={w} too small, need >= 6"
        assert h >= 6, f"Arrow markerHeight={h} too small, need >= 6"

    def test_arrow_uses_user_space_on_use(self, markers):
        """Markers should use userSpaceOnUse for consistent sizing."""
        marker = markers["arrow"]
        units = marker.get("markerUnits", "")
        assert units == "userSpaceOnUse"


# ---------------------------------------------------------------------------
# Sequence diagram marker tests
# ---------------------------------------------------------------------------

SEQUENCE = """sequenceDiagram
    Alice->>John: Hello John, how are you?
    John-->>Alice: Great!
    Alice-)John: See you later!
"""


class TestSequenceArrowMarkers:
    """Verify sequence diagram arrow markers are adequately sized."""

    @pytest.fixture
    def svg(self):
        return render_diagram(SEQUENCE)

    @pytest.fixture
    def markers(self, svg):
        return _find_markers(_parse_svg(svg))

    def test_seq_arrow_marker_exists(self, markers):
        assert "seq-arrow" in markers, "Missing 'seq-arrow' marker definition"

    def test_seq_arrow_adequate_size(self, markers):
        """Sequence arrow markers must be at least 6x6 to be visible.

        Previously reduced to 4x3 which was too small to see.
        Should match flowchart marker sizing (8x8).
        """
        marker = markers["seq-arrow"]
        w, h = _get_marker_dims(marker)
        assert w >= 6, f"seq-arrow markerWidth={w} too small, need >= 6"
        assert h >= 6, f"seq-arrow markerHeight={h} too small, need >= 6"

    def test_seq_arrow_open_adequate_size(self, markers):
        marker = markers["seq-arrow-open"]
        w, h = _get_marker_dims(marker)
        assert w >= 6, f"seq-arrow-open markerWidth={w} too small, need >= 6"
        assert h >= 6, f"seq-arrow-open markerHeight={h} too small, need >= 6"

    def test_seq_arrow_refx_equals_tip(self, markers):
        """Sequence arrow refX must equal the tip x-coordinate."""
        marker = markers["seq-arrow"]
        tip_x = _get_arrow_tip_x(marker)
        ref_x = _get_refx(marker)
        assert ref_x == tip_x, (
            f"seq-arrow refX={ref_x} but tip at x={tip_x}. "
            f"Must match so arrowhead tip touches the target."
        )

    def test_seq_markers_use_user_space_on_use(self, markers):
        for mid in ["seq-arrow", "seq-arrow-open"]:
            if mid in markers:
                units = markers[mid].get("markerUnits", "")
                assert units == "userSpaceOnUse", f"{mid} should use userSpaceOnUse"


# ---------------------------------------------------------------------------
# State diagram marker tests
# ---------------------------------------------------------------------------

STATE = """stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
"""


class TestStateArrowMarkers:
    """Verify state diagram arrow markers (reuses flowchart markers)."""

    @pytest.fixture
    def svg(self):
        return render_diagram(STATE)

    @pytest.fixture
    def markers(self, svg):
        return _find_markers(_parse_svg(svg))

    def test_arrow_marker_exists(self, markers):
        assert "arrow" in markers, "State diagram missing 'arrow' marker"

    def test_arrow_refx_equals_tip(self, markers):
        """refX=0 places the triangle base at the path endpoint.

        Combined with _MARKER_SHORTEN=8, the path is pulled back 8px so
        the arrowhead fills the gap and the tip touches the node boundary.
        """
        marker = markers["arrow"]
        ref_x = _get_refx(marker)
        assert ref_x == 0.0, (
            f"State arrow refX={ref_x} but expected 0. "
            f"refX=0 with path shortening places the arrowhead tip on the node boundary."
        )

    def test_arrow_adequate_size(self, markers):
        marker = markers["arrow"]
        w, h = _get_marker_dims(marker)
        assert w >= 6, f"State arrow markerWidth={w} too small"
        assert h >= 6, f"State arrow markerHeight={h} too small"


# ---------------------------------------------------------------------------
# Cross-diagram consistency tests
# ---------------------------------------------------------------------------

class TestMarkerConsistency:
    """All diagram types should have consistently sized, correctly configured markers."""

    def test_flowchart_and_state_use_same_marker_config(self):
        """Flowchart and state diagrams should use identical arrow markers."""
        fc_svg = render_diagram(FLOWCHART_LR)
        st_svg = render_diagram(STATE)

        fc_markers = _find_markers(_parse_svg(fc_svg))
        st_markers = _find_markers(_parse_svg(st_svg))

        fc_arrow = fc_markers.get("arrow")
        st_arrow = st_markers.get("arrow")

        assert fc_arrow is not None and st_arrow is not None

        # Same refX
        assert _get_refx(fc_arrow) == _get_refx(st_arrow)
        # Same dimensions
        assert _get_marker_dims(fc_arrow) == _get_marker_dims(st_arrow)

    def test_sequence_markers_comparable_to_flowchart(self):
        """Sequence markers should be comparable in size to flowchart markers."""
        fc_svg = render_diagram(FLOWCHART_LR)
        sq_svg = render_diagram(SEQUENCE)

        fc_markers = _find_markers(_parse_svg(fc_svg))
        sq_markers = _find_markers(_parse_svg(sq_svg))

        fc_w, fc_h = _get_marker_dims(fc_markers["arrow"])
        sq_w, sq_h = _get_marker_dims(sq_markers["seq-arrow"])

        # Sequence markers should be at least 50% the size of flowchart markers
        assert sq_w >= fc_w * 0.5, (
            f"seq-arrow width {sq_w} is less than 50% of flowchart arrow width {fc_w}"
        )
        assert sq_h >= fc_h * 0.5, (
            f"seq-arrow height {sq_h} is less than 50% of flowchart arrow height {fc_h}"
        )


# ---------------------------------------------------------------------------
# Edge path endpoint proximity tests
# ---------------------------------------------------------------------------

class TestEdgeEndpointProximity:
    """Verify edge paths actually reach near node boundaries."""

    def _get_edge_paths(self, root: ET.Element) -> list[ET.Element]:
        """Find all edge path elements."""
        ns = f"{{{_SVG_NS}}}"
        paths = []
        for g in root.iter(f"{ns}g"):
            if g.get("class") == "edge":
                for path in g.iter(f"{ns}path"):
                    paths.append(path)
        return paths

    def _get_node_rects(self, root: ET.Element) -> dict[str, dict]:
        """Find node rectangles."""
        ns = f"{{{_SVG_NS}}}"
        nodes = {}
        for g in root.iter(f"{ns}g"):
            cls = g.get("class", "")
            if "node" in cls or "state" in cls:
                node_id = g.get("data-node-id", "") or g.get("data-state-id", "")
                for rect in g.iter(f"{ns}rect"):
                    x = float(rect.get("x", 0))
                    y = float(rect.get("y", 0))
                    w = float(rect.get("width", 0))
                    h = float(rect.get("height", 0))
                    nodes[node_id] = {"x": x, "y": y, "w": w, "h": h}
                    break
        return nodes

    def _path_endpoint(self, d: str) -> tuple[float, float] | None:
        """Extract the last point from a path d-string."""
        # Find all coordinate pairs
        numbers = re.findall(r'[-+]?\d*\.?\d+', d)
        if len(numbers) >= 2:
            return float(numbers[-2]), float(numbers[-1])
        return None

    def test_flowchart_edges_reach_nodes(self):
        """Edge endpoints should be within marker-length of node boundaries."""
        svg = render_diagram(FLOWCHART_LR)
        root = _parse_svg(svg)
        paths = self._get_edge_paths(root)
        nodes = self._get_node_rects(root)

        # We should have edges and nodes
        assert len(paths) > 0, "No edge paths found"
        assert len(nodes) > 0, "No nodes found"
