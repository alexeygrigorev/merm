"""Node shape renderers for SVG output.

Each shape renderer implements the ShapeRenderer protocol, producing SVG element
strings and computing connection points on shape boundaries.
"""

from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

from pymermaid.ir import NodeShape

# Type alias for a 2D point.
Point = tuple[float, float]


def _style_attr(style: dict[str, str] | None) -> str:
    """Build an inline style attribute string from a dict, or empty string."""
    if not style:
        return ""
    css = ";".join(f"{k}:{v}" for k, v in style.items())
    return f' style="{css}"'


def _polygon_svg(points: list[Point], style: dict[str, str] | None) -> str:
    """Build a <polygon> SVG element from a list of points."""
    pts = " ".join(f"{x},{y}" for x, y in points)
    return f'<polygon points="{pts}"{_style_attr(style)} />'


def _ray_polygon_intersection(
    cx: float, cy: float, angle: float, vertices: list[Point],
) -> Point:
    """Find where a ray from (cx, cy) at *angle* intersects a convex polygon.

    Returns the closest intersection point on the polygon boundary.
    """
    dx = math.cos(angle)
    dy = math.sin(angle)
    best_t: float | None = None
    best_point: Point = (cx + dx, cy + dy)

    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        # Edge direction
        ex, ey = x2 - x1, y2 - y1
        denom = dx * ey - dy * ex
        if abs(denom) < 1e-12:
            continue
        t = ((x1 - cx) * ey - (y1 - cy) * ex) / denom
        s = ((x1 - cx) * dy - (y1 - cy) * dx) / denom
        if t > 1e-9 and -1e-9 <= s <= 1.0 + 1e-9:
            if best_t is None or t < best_t:
                best_t = t
                best_point = (cx + dx * t, cy + dy * t)
    return best_point


def _rect_connection_point(
    x: float, y: float, w: float, h: float, angle: float,
) -> Point:
    """Connection point on a rectangle boundary."""
    cx, cy = x + w / 2, y + h / 2
    vertices: list[Point] = [
        (x, y), (x + w, y), (x + w, y + h), (x, y + h),
    ]
    return _ray_polygon_intersection(cx, cy, angle, vertices)


# ---------------------------------------------------------------------------
# ShapeRenderer protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class ShapeRenderer(Protocol):
    """Protocol for shape renderers."""

    def render(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        style: dict[str, str] | None,
    ) -> list[str]: ...

    def connection_point(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        angle_rad: float,
    ) -> Point: ...


# ---------------------------------------------------------------------------
# Individual shape renderers
# ---------------------------------------------------------------------------

class RectRenderer:
    """Rectangle shape."""

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        return [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{_style_attr(style)} />',
        ]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        return _rect_connection_point(x, y, w, h, angle_rad)


class RoundedRectRenderer:
    """Rounded rectangle with fixed corner radius."""

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        sa = _style_attr(style)
        return [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}"'
            f' rx="5" ry="5"{sa} />',
        ]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        return _rect_connection_point(x, y, w, h, angle_rad)


class StadiumRenderer:
    """Stadium (pill) shape -- rect with rx = h/2."""

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        r = h / 2
        sa = _style_attr(style)
        return [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}"'
            f' rx="{r}" ry="{r}"{sa} />',
        ]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        return _rect_connection_point(x, y, w, h, angle_rad)


class SubroutineRenderer:
    """Subroutine -- rectangle with two inner vertical lines."""

    _INSET = 8.0

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        sa = _style_attr(style)
        left_x = x + self._INSET
        right_x = x + w - self._INSET
        return [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{sa} />',
            f'<line x1="{left_x}" y1="{y}" x2="{left_x}" y2="{y + h}"{sa} />',
            f'<line x1="{right_x}" y1="{y}" x2="{right_x}" y2="{y + h}"{sa} />',
        ]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        return _rect_connection_point(x, y, w, h, angle_rad)


class CylinderRenderer:
    """Cylinder shape using an SVG path with elliptical arcs."""

    _RY = 10.0  # vertical radius of the ellipse caps

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        ry = self._RY
        rx = w / 2
        # Top-left of body
        tx, ty = x, y + ry
        bh = h - 2 * ry  # body height between caps
        # Path: top ellipse, right side, bottom ellipse (full), left side, close
        d = (
            f"M {tx},{ty} "
            f"A {rx},{ry} 0 0 1 {tx + w},{ty} "
            f"L {tx + w},{ty + bh} "
            f"A {rx},{ry} 0 0 1 {tx},{ty + bh} "
            f"L {tx},{ty} "
            f"M {tx},{ty} "
            f"A {rx},{ry} 0 0 0 {tx + w},{ty}"
        )
        return [
            f'<path d="{d}"{_style_attr(style)} />',
        ]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        # Approximate as rectangle
        return _rect_connection_point(x, y, w, h, angle_rad)


class CircleRenderer:
    """Circle shape."""

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        r = max(w, h) / 2
        cx = x + w / 2
        cy = y + h / 2
        return [
            f'<circle cx="{cx}" cy="{cy}" r="{r}"{_style_attr(style)} />',
        ]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        r = max(w, h) / 2
        cx = x + w / 2
        cy = y + h / 2
        return (cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad))


class AsymmetricRenderer:
    """Asymmetric / flag / banner shape."""

    def _vertices(self, x: float, y: float, w: float, h: float) -> list[Point]:
        notch = h / 4
        return [
            (x, y),
            (x + w, y),
            (x + w, y + h),
            (x, y + h),
            (x + notch, y + h / 2),
        ]

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        return [_polygon_svg(self._vertices(x, y, w, h), style)]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        cx, cy = x + w / 2, y + h / 2
        return _ray_polygon_intersection(cx, cy, angle_rad, self._vertices(x, y, w, h))


class DiamondRenderer:
    """Diamond / rhombus shape."""

    def _vertices(self, x: float, y: float, w: float, h: float) -> list[Point]:
        cx, cy = x + w / 2, y + h / 2
        return [
            (cx, y),          # top
            (x + w, cy),      # right
            (cx, y + h),      # bottom
            (x, cy),          # left
        ]

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        return [_polygon_svg(self._vertices(x, y, w, h), style)]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        cx, cy = x + w / 2, y + h / 2
        return _ray_polygon_intersection(cx, cy, angle_rad, self._vertices(x, y, w, h))


class HexagonRenderer:
    """Hexagon shape."""

    def _vertices(self, x: float, y: float, w: float, h: float) -> list[Point]:
        inset = w / 4
        return [
            (x + inset, y),
            (x + w - inset, y),
            (x + w, y + h / 2),
            (x + w - inset, y + h),
            (x + inset, y + h),
            (x, y + h / 2),
        ]

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        return [_polygon_svg(self._vertices(x, y, w, h), style)]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        cx, cy = x + w / 2, y + h / 2
        return _ray_polygon_intersection(cx, cy, angle_rad, self._vertices(x, y, w, h))


class ParallelogramRenderer:
    """Parallelogram -- skewed right."""

    _SKEW = 0.15  # fraction of width

    def _vertices(self, x: float, y: float, w: float, h: float) -> list[Point]:
        s = w * self._SKEW
        return [
            (x + s, y),
            (x + w, y),
            (x + w - s, y + h),
            (x, y + h),
        ]

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        return [_polygon_svg(self._vertices(x, y, w, h), style)]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        cx, cy = x + w / 2, y + h / 2
        return _ray_polygon_intersection(cx, cy, angle_rad, self._vertices(x, y, w, h))


class ParallelogramAltRenderer:
    """Parallelogram alt -- skewed opposite direction."""

    _SKEW = 0.15

    def _vertices(self, x: float, y: float, w: float, h: float) -> list[Point]:
        s = w * self._SKEW
        return [
            (x, y),
            (x + w - s, y),
            (x + w, y + h),
            (x + s, y + h),
        ]

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        return [_polygon_svg(self._vertices(x, y, w, h), style)]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        cx, cy = x + w / 2, y + h / 2
        return _ray_polygon_intersection(cx, cy, angle_rad, self._vertices(x, y, w, h))


class TrapezoidRenderer:
    """Trapezoid -- wider at the bottom."""

    _INSET = 0.15

    def _vertices(self, x: float, y: float, w: float, h: float) -> list[Point]:
        s = w * self._INSET
        return [
            (x + s, y),
            (x + w - s, y),
            (x + w, y + h),
            (x, y + h),
        ]

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        return [_polygon_svg(self._vertices(x, y, w, h), style)]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        cx, cy = x + w / 2, y + h / 2
        return _ray_polygon_intersection(cx, cy, angle_rad, self._vertices(x, y, w, h))


class TrapezoidAltRenderer:
    """Trapezoid alt -- wider at the top."""

    _INSET = 0.15

    def _vertices(self, x: float, y: float, w: float, h: float) -> list[Point]:
        s = w * self._INSET
        return [
            (x, y),
            (x + w, y),
            (x + w - s, y + h),
            (x + s, y + h),
        ]

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        return [_polygon_svg(self._vertices(x, y, w, h), style)]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        cx, cy = x + w / 2, y + h / 2
        return _ray_polygon_intersection(cx, cy, angle_rad, self._vertices(x, y, w, h))


class DoubleCircleRenderer:
    """Double circle -- two concentric circles."""

    _GAP = 5.0

    def render(
        self, x: float, y: float, w: float, h: float,
        label: str, style: dict[str, str] | None,
    ) -> list[str]:
        r_outer = max(w, h) / 2
        r_inner = r_outer - self._GAP
        cx = x + w / 2
        cy = y + h / 2
        sa = _style_attr(style)
        return [
            f'<circle cx="{cx}" cy="{cy}" r="{r_outer}"{sa} />',
            f'<circle cx="{cx}" cy="{cy}" r="{r_inner}"{sa} />',
        ]

    def connection_point(
        self, x: float, y: float, w: float, h: float, angle_rad: float,
    ) -> Point:
        r = max(w, h) / 2
        cx = x + w / 2
        cy = y + h / 2
        return (cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SHAPE_REGISTRY: dict[NodeShape, ShapeRenderer] = {
    NodeShape.rect: RectRenderer(),
    NodeShape.rounded: RoundedRectRenderer(),
    NodeShape.stadium: StadiumRenderer(),
    NodeShape.subroutine: SubroutineRenderer(),
    NodeShape.cylinder: CylinderRenderer(),
    NodeShape.circle: CircleRenderer(),
    NodeShape.asymmetric: AsymmetricRenderer(),
    NodeShape.diamond: DiamondRenderer(),
    NodeShape.hexagon: HexagonRenderer(),
    NodeShape.parallelogram: ParallelogramRenderer(),
    NodeShape.parallelogram_alt: ParallelogramAltRenderer(),
    NodeShape.trapezoid: TrapezoidRenderer(),
    NodeShape.trapezoid_alt: TrapezoidAltRenderer(),
    NodeShape.double_circle: DoubleCircleRenderer(),
}


def get_shape_renderer(shape: NodeShape) -> ShapeRenderer:
    """Return the renderer for *shape*, raising KeyError if not found."""
    try:
        return SHAPE_REGISTRY[shape]
    except KeyError:
        raise KeyError(f"No renderer registered for shape: {shape!r}") from None


__all__ = [
    "SHAPE_REGISTRY",
    "ShapeRenderer",
    "get_shape_renderer",
    "Point",
]
