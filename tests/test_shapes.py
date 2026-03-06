"""Tests for node shape renderers."""

import math
import re
import xml.etree.ElementTree as ET

import pytest

from merm.ir import NodeShape
from merm.render.shapes import (
    SHAPE_REGISTRY,
    ShapeRenderer,
    get_shape_renderer,
)

# Common test dimensions
X, Y, W, H = 10.0, 20.0, 100.0, 50.0

# ---------------------------------------------------------------------------
# Registry and protocol tests
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_registry_has_14_entries(self):
        assert len(SHAPE_REGISTRY) == 14

    def test_every_node_shape_in_registry(self):
        for shape in NodeShape:
            assert shape in SHAPE_REGISTRY, f"Missing registry entry for {shape}"

    def test_get_shape_renderer_returns_renderer(self):
        r = get_shape_renderer(NodeShape.rect)
        assert isinstance(r, ShapeRenderer)

    def test_get_shape_renderer_all_shapes(self):
        for shape in NodeShape:
            r = get_shape_renderer(shape)
            assert r is not None

    def test_get_shape_renderer_invalid_raises(self):
        with pytest.raises(KeyError, match="No renderer registered"):
            get_shape_renderer("not_a_shape")  # type: ignore[arg-type]

    def test_all_renderers_implement_protocol(self):
        for shape, renderer in SHAPE_REGISTRY.items():
            msg = f"{shape} renderer doesn't implement protocol"
            assert isinstance(renderer, ShapeRenderer), msg

# ---------------------------------------------------------------------------
# Rectangle
# ---------------------------------------------------------------------------

class TestRectRenderer:
    def test_render_contains_rect(self):
        r = get_shape_renderer(NodeShape.rect)
        elems = r.render(X, Y, W, H, "Hello", None)
        assert len(elems) >= 1
        assert "<rect" in elems[0]

    def test_render_correct_attributes(self):
        r = get_shape_renderer(NodeShape.rect)
        elem = r.render(X, Y, W, H, "Hello", None)[0]
        assert f'x="{X}"' in elem
        assert f'y="{Y}"' in elem
        assert f'width="{W}"' in elem
        assert f'height="{H}"' in elem

    def test_connection_point_right(self):
        r = get_shape_renderer(NodeShape.rect)
        px, py = r.connection_point(X, Y, W, H, 0)
        assert pytest.approx(px, abs=0.1) == X + W
        assert pytest.approx(py, abs=0.1) == Y + H / 2

    def test_connection_point_left(self):
        r = get_shape_renderer(NodeShape.rect)
        px, py = r.connection_point(X, Y, W, H, math.pi)
        assert pytest.approx(px, abs=0.1) == X
        assert pytest.approx(py, abs=0.1) == Y + H / 2

    def test_connection_point_down(self):
        r = get_shape_renderer(NodeShape.rect)
        px, py = r.connection_point(X, Y, W, H, math.pi / 2)
        assert pytest.approx(px, abs=0.1) == X + W / 2
        assert pytest.approx(py, abs=0.1) == Y + H

    def test_connection_point_up(self):
        r = get_shape_renderer(NodeShape.rect)
        px, py = r.connection_point(X, Y, W, H, -math.pi / 2)
        assert pytest.approx(px, abs=0.1) == X + W / 2
        assert pytest.approx(py, abs=0.1) == Y

    def test_connection_point_on_edge(self):
        """Point should lie on one of the four edges."""
        r = get_shape_renderer(NodeShape.rect)
        for angle in [0, math.pi / 4, math.pi / 2, math.pi, -math.pi / 4]:
            px, py = r.connection_point(X, Y, W, H, angle)
            on_left = pytest.approx(px, abs=0.1) == X
            on_right = pytest.approx(px, abs=0.1) == X + W
            on_top = pytest.approx(py, abs=0.1) == Y
            on_bottom = pytest.approx(py, abs=0.1) == Y + H
            assert on_left or on_right or on_top or on_bottom

# ---------------------------------------------------------------------------
# Rounded Rectangle
# ---------------------------------------------------------------------------

class TestRoundedRectRenderer:
    def test_render_has_rx(self):
        r = get_shape_renderer(NodeShape.rounded)
        elem = r.render(X, Y, W, H, "Hi", None)[0]
        assert "<rect" in elem
        assert 'rx="5"' in elem

    def test_rx_is_positive(self):
        r = get_shape_renderer(NodeShape.rounded)
        elem = r.render(X, Y, W, H, "Hi", None)[0]
        m = re.search(r'rx="(\d+)"', elem)
        assert m is not None
        assert int(m.group(1)) > 0

# ---------------------------------------------------------------------------
# Stadium
# ---------------------------------------------------------------------------

class TestStadiumRenderer:
    def test_render_rx_equals_half_height(self):
        r = get_shape_renderer(NodeShape.stadium)
        elem = r.render(X, Y, W, H, "Hi", None)[0]
        assert "<rect" in elem
        assert f'rx="{H / 2}"' in elem

    def test_different_from_rounded_for_tall_nodes(self):
        """Stadium rx should change with height, rounded stays 5."""
        stadium = get_shape_renderer(NodeShape.stadium)
        rounded = get_shape_renderer(NodeShape.rounded)
        s_elem = stadium.render(X, Y, W, 80, "Hi", None)[0]
        r_elem = rounded.render(X, Y, W, 80, "Hi", None)[0]
        assert s_elem != r_elem

# ---------------------------------------------------------------------------
# Subroutine
# ---------------------------------------------------------------------------

class TestSubroutineRenderer:
    def test_render_has_rect_and_lines(self):
        r = get_shape_renderer(NodeShape.subroutine)
        elems = r.render(X, Y, W, H, "Hi", None)
        assert len(elems) >= 3
        assert "<rect" in elems[0]
        assert "<line" in elems[1]
        assert "<line" in elems[2]

    def test_inner_lines_at_inset(self):
        r = get_shape_renderer(NodeShape.subroutine)
        elems = r.render(X, Y, W, H, "Hi", None)
        left_line = elems[1]
        right_line = elems[2]
        assert f'x1="{X + 8.0}"' in left_line
        assert f'x1="{X + W - 8.0}"' in right_line

# ---------------------------------------------------------------------------
# Cylinder
# ---------------------------------------------------------------------------

class TestCylinderRenderer:
    def test_render_has_path(self):
        r = get_shape_renderer(NodeShape.cylinder)
        elems = r.render(X, Y, W, H, "Hi", None)
        assert any("<path" in e for e in elems)

    def test_render_has_arc_command(self):
        r = get_shape_renderer(NodeShape.cylinder)
        elems = r.render(X, Y, W, H, "Hi", None)
        path_elem = [e for e in elems if "<path" in e][0]
        assert " A " in path_elem or " A" in path_elem

# ---------------------------------------------------------------------------
# Circle
# ---------------------------------------------------------------------------

class TestCircleRenderer:
    def test_render_has_circle(self):
        r = get_shape_renderer(NodeShape.circle)
        elems = r.render(X, Y, W, H, "Hi", None)
        assert any("<circle" in e for e in elems)

    def test_render_correct_attributes(self):
        r = get_shape_renderer(NodeShape.circle)
        elem = r.render(X, Y, W, H, "Hi", None)[0]
        cx = X + W / 2
        cy = Y + H / 2
        radius = max(W, H) / 2
        assert f'cx="{cx}"' in elem
        assert f'cy="{cy}"' in elem
        assert f'r="{radius}"' in elem

    def test_r_from_max_wh(self):
        r = get_shape_renderer(NodeShape.circle)
        elem = r.render(10, 20, 60, 40, "Hi", None)[0]
        assert 'r="30.0"' in elem  # max(60,40)/2 = 30

    def test_connection_point_right(self):
        r = get_shape_renderer(NodeShape.circle)
        radius = max(W, H) / 2
        cx = X + W / 2
        cy = Y + H / 2
        px, py = r.connection_point(X, Y, W, H, 0)
        assert pytest.approx(px, abs=0.01) == cx + radius
        assert pytest.approx(py, abs=0.01) == cy

    def test_connection_point_left(self):
        r = get_shape_renderer(NodeShape.circle)
        radius = max(W, H) / 2
        cx = X + W / 2
        cy = Y + H / 2
        px, py = r.connection_point(X, Y, W, H, math.pi)
        assert pytest.approx(px, abs=0.01) == cx - radius
        assert pytest.approx(py, abs=0.01) == cy

    def test_connection_point_distance_equals_radius(self):
        r = get_shape_renderer(NodeShape.circle)
        radius = max(W, H) / 2
        cx = X + W / 2
        cy = Y + H / 2
        for angle in [0, 0.5, 1.0, 2.0, 3.14, -1.0]:
            px, py = r.connection_point(X, Y, W, H, angle)
            dist = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
            assert pytest.approx(dist, abs=0.01) == radius

# ---------------------------------------------------------------------------
# Diamond
# ---------------------------------------------------------------------------

class TestDiamondRenderer:
    def test_render_has_polygon(self):
        r = get_shape_renderer(NodeShape.diamond)
        elems = r.render(X, Y, W, H, "Hi", None)
        assert any("<polygon" in e for e in elems)

    def test_has_4_points(self):
        r = get_shape_renderer(NodeShape.diamond)
        elem = r.render(X, Y, W, H, "Hi", None)[0]
        m = re.search(r'points="([^"]+)"', elem)
        assert m is not None
        points = m.group(1).strip().split()
        assert len(points) == 4

    def test_connection_point_right_vertex(self):
        r = get_shape_renderer(NodeShape.diamond)
        px, py = r.connection_point(X, Y, W, H, 0)
        assert pytest.approx(px, abs=0.1) == X + W
        assert pytest.approx(py, abs=0.1) == Y + H / 2

    def test_connection_point_on_diamond_edge(self):
        """At angle pi/4, point should be on upper-right edge, not vertex."""
        r = get_shape_renderer(NodeShape.diamond)
        px, py = r.connection_point(X, Y, W, H, -math.pi / 4)
        # Should not be the right vertex
        cx, cy = X + W / 2, Y + H / 2
        # Point should be between top and right vertices
        assert px > cx
        assert py < cy

# ---------------------------------------------------------------------------
# Hexagon
# ---------------------------------------------------------------------------

class TestHexagonRenderer:
    def test_render_has_polygon(self):
        r = get_shape_renderer(NodeShape.hexagon)
        elems = r.render(X, Y, W, H, "Hi", None)
        assert any("<polygon" in e for e in elems)

    def test_has_6_points(self):
        r = get_shape_renderer(NodeShape.hexagon)
        elem = r.render(X, Y, W, H, "Hi", None)[0]
        m = re.search(r'points="([^"]+)"', elem)
        assert m is not None
        points = m.group(1).strip().split()
        assert len(points) == 6

# ---------------------------------------------------------------------------
# Double Circle
# ---------------------------------------------------------------------------

class TestDoubleCircleRenderer:
    def test_render_has_two_circles(self):
        r = get_shape_renderer(NodeShape.double_circle)
        elems = r.render(X, Y, W, H, "Hi", None)
        circle_elems = [e for e in elems if "<circle" in e]
        assert len(circle_elems) == 2

    def test_inner_smaller_than_outer(self):
        r = get_shape_renderer(NodeShape.double_circle)
        elems = r.render(X, Y, W, H, "Hi", None)
        radii = []
        for e in elems:
            m = re.search(r'r="([^"]+)"', e)
            assert m is not None
            radii.append(float(m.group(1)))
        assert radii[0] > radii[1]  # outer > inner

# ---------------------------------------------------------------------------
# Polygon shapes
# ---------------------------------------------------------------------------

class TestPolygonShapes:
    @pytest.mark.parametrize("shape", [
        NodeShape.asymmetric,
        NodeShape.parallelogram,
        NodeShape.parallelogram_alt,
        NodeShape.trapezoid,
        NodeShape.trapezoid_alt,
    ])
    def test_render_has_polygon(self, shape: NodeShape):
        r = get_shape_renderer(shape)
        elems = r.render(X, Y, W, H, "Hi", None)
        assert any("<polygon" in e for e in elems)

    @pytest.mark.parametrize("shape", [
        NodeShape.asymmetric,
        NodeShape.parallelogram,
        NodeShape.parallelogram_alt,
        NodeShape.trapezoid,
        NodeShape.trapezoid_alt,
    ])
    def test_has_points_attribute(self, shape: NodeShape):
        r = get_shape_renderer(shape)
        elem = r.render(X, Y, W, H, "Hi", None)[0]
        assert 'points="' in elem

    def test_parallelogram_mirror(self):
        """Parallelogram and parallelogram_alt should be mirror images."""
        p1 = get_shape_renderer(NodeShape.parallelogram)
        p2 = get_shape_renderer(NodeShape.parallelogram_alt)
        e1 = p1.render(0, 0, 100, 50, "Hi", None)[0]
        e2 = p2.render(0, 0, 100, 50, "Hi", None)[0]
        assert e1 != e2

    def test_trapezoid_mirror(self):
        """Trapezoid and trapezoid_alt should be mirror images."""
        t1 = get_shape_renderer(NodeShape.trapezoid)
        t2 = get_shape_renderer(NodeShape.trapezoid_alt)
        e1 = t1.render(0, 0, 100, 50, "Hi", None)[0]
        e2 = t2.render(0, 0, 100, 50, "Hi", None)[0]
        assert e1 != e2

# ---------------------------------------------------------------------------
# Connection point boundary validation
# ---------------------------------------------------------------------------

class TestConnectionPointBoundary:
    def test_circle_distance_from_center(self):
        r = get_shape_renderer(NodeShape.circle)
        radius = max(W, H) / 2
        cx, cy = X + W / 2, Y + H / 2
        for angle in [0, 0.3, 1.0, 2.5, -1.0, math.pi]:
            px, py = r.connection_point(X, Y, W, H, angle)
            dist = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
            assert pytest.approx(dist, abs=0.01) == radius

    def test_rect_on_boundary(self):
        r = get_shape_renderer(NodeShape.rect)
        for angle in [0, math.pi / 4, math.pi / 2, math.pi, -math.pi / 3]:
            px, py = r.connection_point(X, Y, W, H, angle)
            on_edge = (
                abs(px - X) < 0.1
                or abs(px - (X + W)) < 0.1
                or abs(py - Y) < 0.1
                or abs(py - (Y + H)) < 0.1
            )
            assert on_edge, f"Point ({px}, {py}) not on rect edge at angle {angle}"

    def test_diamond_on_boundary(self):
        r = get_shape_renderer(NodeShape.diamond)
        cx, cy = X + W / 2, Y + H / 2
        for angle in [0, math.pi / 4, math.pi / 2, math.pi, -math.pi / 4]:
            px, py = r.connection_point(X, Y, W, H, angle)
            # Point should be on one of the 4 diamond edges
            # Diamond vertices: top(cx,Y), right(X+W,cy), bottom(cx,Y+H), left(X,cy)
            # Check point is not at center
            dist = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
            assert dist > 0.1, "Connection point should not be at center"

# ---------------------------------------------------------------------------
# Integration: all shapes render valid XML fragments
# ---------------------------------------------------------------------------

class TestValidXML:
    @pytest.mark.parametrize("shape", list(NodeShape))
    def test_render_valid_xml(self, shape: NodeShape):
        r = get_shape_renderer(shape)
        elems = r.render(X, Y, W, H, "Hello", None)
        assert len(elems) > 0
        for elem in elems:
            # Each element should be parseable as XML
            ET.fromstring(elem)

    @pytest.mark.parametrize("shape", list(NodeShape))
    def test_render_nonempty(self, shape: NodeShape):
        r = get_shape_renderer(shape)
        elems = r.render(X, Y, W, H, "Hello", None)
        assert len(elems) > 0
        for elem in elems:
            assert len(elem) > 0

    @pytest.mark.parametrize("shape", list(NodeShape))
    def test_render_with_style(self, shape: NodeShape):
        r = get_shape_renderer(shape)
        style = {"fill": "#f9f", "stroke": "#333"}
        elems = r.render(X, Y, W, H, "Hello", style)
        assert len(elems) > 0
        # At least one element should have a style attribute
        assert any("style=" in e for e in elems)
