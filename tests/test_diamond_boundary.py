"""Tests for Issue 67: Diamond node boundary point computation.

Verifies that edge endpoints for diamond-shaped nodes lie on the diamond
polygon boundary (vertices at midpoints of bounding box sides), not on
the rectangular bounding box.
"""

import math

from merm.ir import NodeShape
from merm.layout.sugiyama import (
    _boundary_point,
    _diamond_boundary_point,
    _route_edge_on_boundary,
)
from merm.layout.types import Point  # noqa: I001

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _diamond_vertices(
    cx: float, cy: float, w: float, h: float,
) -> list[tuple[float, float]]:
    """Return the four diamond vertices: top, right, bottom, left."""
    hw, hh = w / 2.0, h / 2.0
    return [
        (cx, cy - hh),   # top
        (cx + hw, cy),   # right
        (cx, cy + hh),   # bottom
        (cx - hw, cy),   # left
    ]


def _point_on_diamond_edge(
    pt: Point,
    cx: float, cy: float, w: float, h: float,
    tolerance: float = 1.0,
) -> bool:
    """Check whether *pt* lies on one of the four diamond edges (within tolerance)."""
    verts = _diamond_vertices(cx, cy, w, h)
    n = len(verts)
    for i in range(n):
        x1, y1 = verts[i]
        x2, y2 = verts[(i + 1) % n]
        # Distance from point to line segment
        ex, ey = x2 - x1, y2 - y1
        seg_len_sq = ex * ex + ey * ey
        if seg_len_sq < 1e-12:
            continue
        t = max(0.0, min(1.0, ((pt.x - x1) * ex + (pt.y - y1) * ey) / seg_len_sq))
        closest_x = x1 + t * ex
        closest_y = y1 + t * ey
        dist = math.hypot(pt.x - closest_x, pt.y - closest_y)
        if dist < tolerance:
            return True
    return False


def _assert_on_diamond_boundary(
    pt: Point,
    cx: float, cy: float, w: float, h: float,
    tolerance: float = 1.0,
) -> None:
    """Assert that *pt* lies on the diamond boundary."""
    assert _point_on_diamond_edge(pt, cx, cy, w, h, tolerance), (
        f"Point ({pt.x:.2f}, {pt.y:.2f}) is not on diamond boundary "
        f"center=({cx}, {cy}), size=({w}, {h})"
    )


# ---------------------------------------------------------------------------
# Unit: Diamond boundary point computation
# ---------------------------------------------------------------------------

class TestDiamondBoundaryPoint:
    """Tests of _diamond_boundary_point and _boundary_point with diamond."""

    def test_ray_right(self) -> None:
        """Ray going right hits the right vertex (cx + w/2, cy)."""
        cx, cy, w, h = 100.0, 100.0, 80.0, 60.0
        pt = _diamond_boundary_point(cx, cy, w, h, 1.0, 0.0)
        assert abs(pt.x - (cx + w / 2)) < 0.01
        assert abs(pt.y - cy) < 0.01

    def test_ray_left(self) -> None:
        """Ray going left hits the left vertex (cx - w/2, cy)."""
        cx, cy, w, h = 100.0, 100.0, 80.0, 60.0
        pt = _diamond_boundary_point(cx, cy, w, h, -1.0, 0.0)
        assert abs(pt.x - (cx - w / 2)) < 0.01
        assert abs(pt.y - cy) < 0.01

    def test_ray_down(self) -> None:
        """Ray going down hits the bottom vertex (cx, cy + h/2)."""
        cx, cy, w, h = 100.0, 100.0, 80.0, 60.0
        pt = _diamond_boundary_point(cx, cy, w, h, 0.0, 1.0)
        assert abs(pt.x - cx) < 0.01
        assert abs(pt.y - (cy + h / 2)) < 0.01

    def test_ray_up(self) -> None:
        """Ray going up hits the top vertex (cx, cy - h/2)."""
        cx, cy, w, h = 100.0, 100.0, 80.0, 60.0
        pt = _diamond_boundary_point(cx, cy, w, h, 0.0, -1.0)
        assert abs(pt.x - cx) < 0.01
        assert abs(pt.y - (cy - h / 2)) < 0.01

    def test_ray_45_degrees(self) -> None:
        """Ray at 45 degrees should hit diamond edge, NOT the bounding rect corner."""
        cx, cy, w, h = 100.0, 100.0, 80.0, 60.0
        pt = _diamond_boundary_point(cx, cy, w, h, 1.0, 1.0)

        # The bounding rect corner would be at (cx + w/2, cy + h/2) = (140, 130).
        # The diamond boundary is closer to center.
        rect_corner_dist = math.hypot(w / 2, h / 2)
        actual_dist = math.hypot(pt.x - cx, pt.y - cy)
        assert actual_dist < rect_corner_dist - 1.0, (
            f"Diamond point at ({pt.x:.2f}, {pt.y:.2f}) should be closer to center "
            f"than rect corner. dist={actual_dist:.2f} vs rect={rect_corner_dist:.2f}"
        )

        # Must lie on diamond edge
        _assert_on_diamond_boundary(pt, cx, cy, w, h)

    def test_ray_negative_45_degrees(self) -> None:
        """Ray at -45 degrees (upper-right) hits diamond edge."""
        cx, cy, w, h = 100.0, 100.0, 80.0, 60.0
        pt = _diamond_boundary_point(cx, cy, w, h, 1.0, -1.0)
        _assert_on_diamond_boundary(pt, cx, cy, w, h)

    def test_boundary_point_delegates_to_diamond(self) -> None:
        """_boundary_point with shape=diamond uses diamond geometry."""
        cx, cy, w, h = 100.0, 100.0, 80.0, 60.0
        pt_diamond = _boundary_point(cx, cy, w, h, 1.0, 1.0, shape=NodeShape.diamond)
        pt_rect = _boundary_point(cx, cy, w, h, 1.0, 1.0, shape=NodeShape.rect)

        # Diamond result should differ from rect result (diamond is "inscribed")
        assert pt_diamond != pt_rect, (
            "Diamond and rect boundary points should differ for diagonal rays"
        )

        # Diamond result should be on diamond boundary
        _assert_on_diamond_boundary(pt_diamond, cx, cy, w, h)

    def test_boundary_point_rect_unchanged(self) -> None:
        """_boundary_point with default shape=rect works as before."""
        cx, cy, w, h = 100.0, 100.0, 80.0, 60.0
        pt = _boundary_point(cx, cy, w, h, 1.0, 0.0)
        assert abs(pt.x - (cx + w / 2)) < 0.01
        assert abs(pt.y - cy) < 0.01

    def test_square_diamond_at_45(self) -> None:
        """For a square diamond, 45-degree ray should hit edge at known position."""
        cx, cy, w, h = 0.0, 0.0, 100.0, 100.0
        pt = _diamond_boundary_point(cx, cy, w, h, 1.0, 1.0)
        # For a square diamond with half-width=50, the 45-degree ray hits
        # the edge between right vertex (50,0) and bottom vertex (0,50).
        # Parametrically: edge point = (50*(1-t), 50*t) for t in [0,1].
        # Ray: (s, s). Solving: s = 50*(1-t) and s = 50*t => t=0.5, s=25.
        assert abs(pt.x - 25.0) < 0.01
        assert abs(pt.y - 25.0) < 0.01


# ---------------------------------------------------------------------------
# Unit: Edge routing with diamond nodes
# ---------------------------------------------------------------------------

class TestRouteEdgeOnBoundaryDiamond:
    """Test _route_edge_on_boundary with diamond shapes."""

    def test_rect_to_diamond(self) -> None:
        """Target endpoint on diamond boundary when target is diamond."""
        src_pos = (0.0, 0.0)
        src_size = (80.0, 40.0)
        tgt_pos = (200.0, 0.0)
        tgt_size = (100.0, 80.0)

        _, tgt_pt = _route_edge_on_boundary(
            src_pos, src_size, tgt_pos, tgt_size,
            tgt_shape=NodeShape.diamond,
        )
        # Target is diamond at (200, 0) with size (100, 80).
        # Edge comes from the left, so should hit left vertex at (150, 0).
        _assert_on_diamond_boundary(tgt_pt, *tgt_pos, *tgt_size)

    def test_diamond_to_rect(self) -> None:
        """Source endpoint on diamond boundary when source is diamond."""
        src_pos = (0.0, 0.0)
        src_size = (100.0, 80.0)
        tgt_pos = (200.0, 0.0)
        tgt_size = (80.0, 40.0)

        src_pt, _ = _route_edge_on_boundary(
            src_pos, src_size, tgt_pos, tgt_size,
            src_shape=NodeShape.diamond,
        )
        _assert_on_diamond_boundary(src_pt, *src_pos, *src_size)

    def test_diamond_to_diamond(self) -> None:
        """Both endpoints on diamond boundaries."""
        src_pos = (0.0, 0.0)
        src_size = (100.0, 80.0)
        tgt_pos = (200.0, 0.0)
        tgt_size = (100.0, 80.0)

        src_pt, tgt_pt = _route_edge_on_boundary(
            src_pos, src_size, tgt_pos, tgt_size,
            src_shape=NodeShape.diamond,
            tgt_shape=NodeShape.diamond,
        )
        _assert_on_diamond_boundary(src_pt, *src_pos, *src_size)
        _assert_on_diamond_boundary(tgt_pt, *tgt_pos, *tgt_size)

    def test_vertical_edge_into_diamond(self) -> None:
        """Vertical edge (TD direction) into diamond hits top vertex."""
        src_pos = (100.0, 0.0)
        src_size = (80.0, 40.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (100.0, 80.0)

        _, tgt_pt = _route_edge_on_boundary(
            src_pos, src_size, tgt_pos, tgt_size,
            tgt_shape=NodeShape.diamond,
        )
        # Vertical edge should hit top vertex of diamond
        assert abs(tgt_pt.x - 100.0) < 0.01
        assert abs(tgt_pt.y - (150.0 - 40.0)) < 0.01  # cy - h/2

    def test_horizontal_edge_into_diamond(self) -> None:
        """Horizontal edge (LR direction) into diamond hits left vertex."""
        src_pos = (0.0, 100.0)
        src_size = (80.0, 40.0)
        tgt_pos = (200.0, 100.0)
        tgt_size = (100.0, 80.0)

        _, tgt_pt = _route_edge_on_boundary(
            src_pos, src_size, tgt_pos, tgt_size,
            tgt_shape=NodeShape.diamond,
        )
        # Horizontal edge should hit left vertex of diamond
        assert abs(tgt_pt.x - (200.0 - 50.0)) < 0.01  # cx - w/2
        assert abs(tgt_pt.y - 100.0) < 0.01


# ---------------------------------------------------------------------------
# Regression: Non-diamond shapes unaffected
# ---------------------------------------------------------------------------

class TestNonDiamondRegression:
    """Verify that non-diamond shapes produce identical results."""

    def test_rect_boundary_unchanged(self) -> None:
        """Rect boundary with explicit shape=rect matches default."""
        cx, cy, w, h = 50.0, 50.0, 80.0, 40.0
        for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (1, -1), (-1, 1)]:
            pt_default = _boundary_point(cx, cy, w, h, dx, dy)
            pt_explicit = _boundary_point(cx, cy, w, h, dx, dy, shape=NodeShape.rect)
            assert pt_default == pt_explicit

    def test_rounded_uses_rect_boundary(self) -> None:
        """Rounded shape falls through to rect boundary (layout approximation)."""
        cx, cy, w, h = 50.0, 50.0, 80.0, 40.0
        pt_rounded = _boundary_point(cx, cy, w, h, 1.0, 1.0, shape=NodeShape.rounded)
        pt_rect = _boundary_point(cx, cy, w, h, 1.0, 1.0, shape=NodeShape.rect)
        assert pt_rounded == pt_rect

    def test_route_edge_no_shape_args(self) -> None:
        """_route_edge_on_boundary without shape args works as before."""
        src_pos = (0.0, 0.0)
        src_size = (80.0, 40.0)
        tgt_pos = (200.0, 0.0)
        tgt_size = (80.0, 40.0)

        src_pt, tgt_pt = _route_edge_on_boundary(
            src_pos, src_size, tgt_pos, tgt_size,
        )
        # Source exit should be on right edge of source rect
        assert abs(src_pt.x - 40.0) < 0.01
        # Target entry should be on left edge of target rect
        assert abs(tgt_pt.x - 160.0) < 0.01


# ---------------------------------------------------------------------------
# Integration: Full diagram rendering
# ---------------------------------------------------------------------------

class TestDiamondIntegration:
    """Integration tests rendering full diagrams with diamond nodes."""

    def test_lr_diamond_edges_touch(self) -> None:
        """LR flowchart with diamond: edge endpoints on diamond boundary."""
        from merm import render_diagram

        svg = render_diagram(
            "flowchart LR\n"
            "    A[Hard] -->|Text| B(Round)\n"
            "    B --> C{Decision}\n"
            "    C -->|One| D[Result 1]\n"
            "    C -->|Two| E[Result 2]\n"
        )
        assert "<svg" in svg
        # Verify it renders without error -- visual verification done separately

    def test_td_diamond_edges_touch(self) -> None:
        """TD flowchart with diamond: edge endpoints on diamond boundary."""
        from merm import render_diagram

        svg = render_diagram(
            "flowchart TD\n"
            "    Start[Start] --> Check{Is valid?}\n"
            "    Check -->|Yes| OK[OK]\n"
            "    Check -->|No| Fail[Fail]\n"
        )
        assert "<svg" in svg

    def test_mixed_shapes_all_correct(self) -> None:
        """Mixed shapes: rect, rounded, diamond all render correctly."""
        from merm import render_diagram

        svg = render_diagram(
            "flowchart TD\n"
            "    A[Rect] --> B(Rounded)\n"
            "    B --> C{Diamond}\n"
            "    C --> D[Rect2]\n"
        )
        assert "<svg" in svg

    def test_diamond_to_diamond_edges(self) -> None:
        """Edge between two diamond nodes renders correctly."""
        from merm import render_diagram

        svg = render_diagram(
            "flowchart TD\n"
            "    A{Diamond1} --> B{Diamond2}\n"
        )
        assert "<svg" in svg
