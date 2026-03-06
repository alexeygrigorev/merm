"""SVG renderer for Gantt charts."""

from datetime import date, timedelta
from xml.sax.saxutils import escape

from merm.ir.gantt import GanttChart
from merm.theme import Theme

# Colors for modifier-based styling
_FILL_DEFAULT = "#4572A7"  # steel blue
_FILL_DONE = "#A0A0A0"  # muted grey
_FILL_ACTIVE = "#2ECC71"  # highlighted green
_FILL_CRIT = "#E74C3C"  # red

# Layout constants
_LEFT_MARGIN = 180  # space for section/task labels
_RIGHT_MARGIN = 30
_TOP_MARGIN = 20
_ROW_HEIGHT = 32
_BAR_HEIGHT = 22
_BAR_PADDING = (_ROW_HEIGHT - _BAR_HEIGHT) / 2
_CHART_WIDTH = 600  # width of the bar area
_TICK_HEIGHT = 20
_AXIS_MARGIN = 10

def render_gantt_svg(chart: GanttChart, theme: Theme | None = None) -> str:
    """Render a GanttChart IR to an SVG string."""
    # Collect all tasks to compute date range and row count
    all_tasks = []
    # (kind, label, task_info_dict)
    row_entries: list[tuple[str | None, str, dict]] = []

    for section in chart.sections:
        # Add section header row
        if section.name:
            row_entries.append(("section", section.name, {}))
        for task in section.tasks:
            row_entries.append((
                "task",
                task.name,
                {
                    "start": task.start_date,
                    "end": task.end_date,
                    "modifiers": task.modifiers,
                    "id": task.id,
                    "section_name": section.name,
                },
            ))
            all_tasks.append(task)

    if not all_tasks:
        # Empty chart
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 100 50" width="100" height="50"></svg>'
        )

    # Compute global date range
    min_date = min(t.start_date for t in all_tasks)
    max_date = max(t.end_date for t in all_tasks)
    total_days = (max_date - min_date).days
    if total_days == 0:
        total_days = 1  # avoid division by zero

    # Compute title height
    title_height = 35 if chart.title else 0

    # Compute dimensions
    num_rows = len(row_entries)
    chart_top = _TOP_MARGIN + title_height
    chart_bottom = chart_top + num_rows * _ROW_HEIGHT
    axis_top = chart_bottom + _AXIS_MARGIN
    svg_height = axis_top + _TICK_HEIGHT + 20
    svg_width = _LEFT_MARGIN + _CHART_WIDTH + _RIGHT_MARGIN

    parts: list[str] = []

    # SVG header
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {svg_width} {svg_height}" '
        f'width="{svg_width}" height="{svg_height}">'
    )

    # Styles
    parts.append("<style>")
    parts.append(
        ".gantt-title { font-family: sans-serif;"
        " font-size: 18px; font-weight: bold;"
        " text-anchor: middle; fill: #333; }"
    )
    parts.append(
        ".gantt-section { font-family: sans-serif;"
        " font-size: 13px; font-weight: bold;"
        " fill: #555; }"
    )
    parts.append(
        ".gantt-label { font-family: sans-serif;"
        " font-size: 12px; fill: #333; }"
    )
    parts.append(
        ".gantt-bar-text { font-family: sans-serif;"
        " font-size: 11px; fill: #fff;"
        " text-anchor: middle; dominant-baseline: central; }"
    )
    parts.append(
        ".gantt-tick { font-family: sans-serif;"
        " font-size: 10px; fill: #666;"
        " text-anchor: middle; }"
    )
    parts.append(
        ".gantt-grid { stroke: #e0e0e0; stroke-width: 0.5; }"
    )
    parts.append("</style>")

    # Title
    if chart.title:
        tx = svg_width / 2
        parts.append(
            f'<text x="{tx:.1f}" y="{_TOP_MARGIN + 15}" class="gantt-title">'
            f"{escape(chart.title)}</text>"
        )

    # Helper: date to x coordinate
    def date_to_x(d: date) -> float:
        days_offset = (d - min_date).days
        return _LEFT_MARGIN + (days_offset / total_days) * _CHART_WIDTH

    # Draw grid lines and rows
    for row_idx, entry in enumerate(row_entries):
        y = chart_top + row_idx * _ROW_HEIGHT
        kind = entry[0]

        if kind == "section":
            # Section header: background band
            parts.append(
                f'<rect x="0" y="{y}" width="{svg_width}" height="{_ROW_HEIGHT}" '
                f'fill="#f0f0f0" data-section="{escape(entry[1])}"/>'
            )
            parts.append(
                f'<text x="10" y="{y + _ROW_HEIGHT / 2 + 4}" '
                f'class="gantt-section">{escape(entry[1])}</text>'
            )
        elif kind == "task":
            info = entry[2]
            task_id = info["id"]
            section_name = info["section_name"]

            # Task label on the left
            parts.append(
                f'<text x="{_LEFT_MARGIN - 10}" y="{y + _ROW_HEIGHT / 2 + 4}" '
                f'class="gantt-label" text-anchor="end">{escape(entry[1])}</text>'
            )

            # Task bar
            x1 = date_to_x(info["start"])
            x2 = date_to_x(info["end"])
            bar_width = max(x2 - x1, 2)  # minimum visible width
            bar_y = y + _BAR_PADDING

            fill = _get_fill(info["modifiers"])
            data_attrs = ""
            if task_id:
                data_attrs += f' data-task-id="{escape(task_id)}"'
            if section_name:
                data_attrs += f' data-section="{escape(section_name)}"'

            parts.append(
                f'<rect x="{x1:.2f}" y="{bar_y:.1f}" '
                f'width="{bar_width:.2f}" height="{_BAR_HEIGHT}" '
                f'rx="3" ry="3" fill="{fill}"{data_attrs}/>'
            )

    # Time axis
    # Draw axis line
    parts.append(
        f'<line x1="{_LEFT_MARGIN}" y1="{axis_top}" '
        f'x2="{_LEFT_MARGIN + _CHART_WIDTH}" y2="{axis_top}" '
        f'stroke="#333" stroke-width="1"/>'
    )

    # Tick marks: aim for ~5-8 ticks
    tick_dates = _compute_tick_dates(min_date, max_date)
    for td in tick_dates:
        tx = date_to_x(td)
        # Tick line
        parts.append(
            f'<line x1="{tx:.2f}" y1="{axis_top}" '
            f'x2="{tx:.2f}" y2="{axis_top + 6}" '
            f'stroke="#333" stroke-width="1"/>'
        )
        # Vertical grid line
        parts.append(
            f'<line x1="{tx:.2f}" y1="{chart_top}" '
            f'x2="{tx:.2f}" y2="{axis_top}" '
            f'class="gantt-grid"/>'
        )
        # Tick label
        parts.append(
            f'<text x="{tx:.2f}" y="{axis_top + 16}" '
            f'class="gantt-tick">{td.isoformat()}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)

def _get_fill(modifiers: frozenset[str]) -> str:
    """Return fill color based on task modifiers."""
    if "crit" in modifiers:
        return _FILL_CRIT
    if "done" in modifiers:
        return _FILL_DONE
    if "active" in modifiers:
        return _FILL_ACTIVE
    return _FILL_DEFAULT

def _compute_tick_dates(start: date, end: date) -> list[date]:
    """Compute reasonable tick mark dates for the time axis."""
    total_days = (end - start).days
    if total_days <= 0:
        return [start]

    # Choose interval to get roughly 5-8 ticks
    if total_days <= 14:
        interval = 2
    elif total_days <= 30:
        interval = 5
    elif total_days <= 90:
        interval = 14
    elif total_days <= 180:
        interval = 30
    elif total_days <= 365:
        interval = 60
    else:
        interval = 90

    ticks: list[date] = [start]
    current = start + timedelta(days=interval)
    while current < end:
        ticks.append(current)
        current += timedelta(days=interval)
    ticks.append(end)
    return ticks

__all__ = ["render_gantt_svg"]
