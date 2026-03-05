"""SVG renderer for pie charts."""

import math
from xml.sax.saxutils import escape

from pymermaid.ir.pie import PieChart
from pymermaid.theme import Theme

PIE_COLORS = [
    "#4572A7",  # steel blue
    "#AA4643",  # brick red
    "#89A54E",  # olive green
    "#80699B",  # muted purple
    "#3D96AE",  # teal
    "#DB843D",  # warm orange
    "#92A8CD",  # light slate blue
    "#A47D7C",  # mauve
    "#B5CA92",  # sage green
    "#5C6BC0",  # indigo
]

def render_pie_svg(chart: PieChart, theme: Theme | None = None) -> str:
    """Render a PieChart IR to an SVG string."""
    # Chart geometry
    cx, cy = 200, 200  # center of pie
    radius = 150
    title_height = 40 if chart.title else 0
    legend_x = cx + radius + 40
    legend_width = 250
    svg_width = legend_x + legend_width + 20
    svg_height = max(cy + radius + 40, title_height + len(chart.slices) * 28 + 40)

    total = sum(s.value for s in chart.slices)
    parts: list[str] = []

    # SVG header
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {svg_width} {svg_height}" '
        f'width="{svg_width}" height="{svg_height}">'
    )

    # Style
    parts.append("<style>")
    parts.append(
        ".pie-title { font-family: sans-serif;"
        " font-size: 20px; font-weight: bold;"
        " text-anchor: middle; }"
    )
    parts.append(
        ".pie-label { font-family: sans-serif;"
        " font-size: 12px; text-anchor: middle;"
        " fill: #333; }"
    )
    parts.append(
        ".pie-legend { font-family: sans-serif;"
        " font-size: 14px; fill: #333; }"
    )
    parts.append(".pie-slice { stroke: #fff; stroke-width: 2; }")
    parts.append("</style>")

    # Title
    if chart.title:
        parts.append(
            f'<text x="{cx}" y="25" class="pie-title">'
            f"{escape(chart.title)}</text>"
        )
        # Shift pie down for title
        cy_actual = cy + title_height
    else:
        cy_actual = cy

    # Draw slices
    if len(chart.slices) == 1:
        # Single slice: full circle
        color = PIE_COLORS[0]
        parts.append(
            f'<circle cx="{cx}" cy="{cy_actual}" r="{radius}" '
            f'fill="{color}" class="pie-slice" '
            f'data-slice-label="{escape(chart.slices[0].label)}"/>'
        )
    else:
        angle = -90.0  # start from top (12 o'clock)
        for i, slc in enumerate(chart.slices):
            sweep = (slc.value / total) * 360.0
            color = PIE_COLORS[i % len(PIE_COLORS)]

            start_rad = math.radians(angle)
            end_rad = math.radians(angle + sweep)

            x1 = cx + radius * math.cos(start_rad)
            y1 = cy_actual + radius * math.sin(start_rad)
            x2 = cx + radius * math.cos(end_rad)
            y2 = cy_actual + radius * math.sin(end_rad)

            large_arc = 1 if sweep > 180 else 0

            d = (
                f"M {cx} {cy_actual} "
                f"L {x1:.4f} {y1:.4f} "
                f"A {radius} {radius} 0 {large_arc} 1 {x2:.4f} {y2:.4f} "
                f"Z"
            )
            parts.append(
                f'<path d="{d}" fill="{color}" class="pie-slice" '
                f'data-slice-label="{escape(slc.label)}"/>'
            )

            # Label outside the wedge
            mid_angle_rad = math.radians(angle + sweep / 2)
            label_r = radius + 20
            lx = cx + label_r * math.cos(mid_angle_rad)
            ly = cy_actual + label_r * math.sin(mid_angle_rad)
            pct = (slc.value / total) * 100
            parts.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" class="pie-label">'
                f"{pct:.1f}%</text>"
            )

            angle += sweep

    # Legend
    legend_y_start = (cy_actual - radius) if not chart.title else title_height + 10
    for i, slc in enumerate(chart.slices):
        color = PIE_COLORS[i % len(PIE_COLORS)]
        ly = legend_y_start + i * 28
        pct = (slc.value / total) * 100

        # Colored square
        parts.append(
            f'<rect x="{legend_x}" y="{ly}" width="16" height="16" '
            f'fill="{color}" class="pie-legend"/>'
        )

        # Label text
        label_text = f"{escape(slc.label)}: {pct:.1f}%"
        if chart.show_data:
            label_text += f" ({slc.value:g})"
        parts.append(
            f'<text x="{legend_x + 22}" y="{ly + 13}" class="pie-legend">'
            f"{label_text}</text>"
        )

    parts.append("</svg>")
    return "\n".join(parts)

__all__ = ["render_pie_svg"]
