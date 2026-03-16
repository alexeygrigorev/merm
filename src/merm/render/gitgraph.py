"""SVG renderer for gitGraph diagrams."""

from xml.sax.saxutils import escape

from merm.ir.gitgraph import CommitType, GitGraph
from merm.layout.gitgraph import GitGraphLayout
from merm.theme import DEFAULT_THEME, Theme

# Branch color palette (follows Mermaid's default gitgraph theme)
BRANCH_COLORS = [
    "#47d147",  # green (main)
    "#ff6666",  # red
    "#6699ff",  # blue
    "#ffcc00",  # yellow
    "#cc66ff",  # purple
    "#ff9933",  # orange
    "#33cccc",  # teal
    "#ff6699",  # pink
]

# Commit circle radii
_NORMAL_RADIUS = 8
_HIGHLIGHT_RADIUS = 12

# Reverse commit fill
_REVERSE_FILL = "#ffffff"


def _themed_branch_colors(theme: Theme) -> list[str]:
    """Return branch color palette adjusted for the given theme."""
    if theme is DEFAULT_THEME:
        return BRANCH_COLORS
    # For non-default themes, derive a palette from theme colors.
    # Use node_stroke as the primary branch color and generate
    # variants by mixing with the base palette.
    return [
        theme.node_stroke,   # primary branch gets theme node_stroke
        theme.edge_stroke,   # second branch gets edge color
        theme.subgraph_stroke,  # third branch
        "#ffcc00",
        "#cc66ff",
        "#ff9933",
        "#33cccc",
        "#ff6699",
    ]


def render_gitgraph_svg(
    graph: GitGraph,
    layout: GitGraphLayout,
    theme: Theme | None = None,
) -> str:
    """Render a GitGraph and its layout to an SVG string."""
    if theme is None:
        theme = DEFAULT_THEME

    parts: list[str] = []

    # Build branch -> color map
    palette = _themed_branch_colors(theme)
    branch_color: dict[str, str] = {}
    for i, branch_name in enumerate(graph.branch_order):
        branch_color[branch_name] = palette[i % len(palette)]

    # Build commit lookup
    commit_map = {c.id: c for c in graph.commits}

    svg_w = max(layout.width, 200)
    svg_h = max(layout.height, 100)

    bg_color = theme.background_color
    text_color = theme.text_color
    font_family = theme.font_family

    # SVG header
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {svg_w:.0f} {svg_h:.0f}" '
        f'width="{svg_w:.0f}" height="{svg_h:.0f}">'
    )

    # Background rect (only when non-white to match themed appearance)
    if bg_color != "white":
        parts.append(
            f'<rect width="100%" height="100%" fill="{bg_color}" '
            f'class="gitgraph-background"/>'
        )

    # Style
    parts.append("<style>")
    parts.append(
        f".gitgraph-label {{ font-family: {font_family};"
        f" font-size: 12px; fill: {text_color}; }}"
    )
    parts.append(
        f".gitgraph-branch-label {{ font-family: {font_family};"
        f" font-size: 14px; font-weight: bold; }}"
    )
    parts.append(
        f".gitgraph-tag {{ font-family: {font_family};"
        f" font-size: 11px; fill: {text_color}; }}"
    )
    parts.append("</style>")

    # Branch lane lines (full horizontal extent per branch)
    for branch_name, y in layout.branch_lane_y.items():
        color = branch_color.get(branch_name, "#999")
        # Draw a faint horizontal guideline for each branch lane
        if layout.commits:
            branch_xs = [
                cl.x for cl in layout.commits
                if commit_map.get(cl.id)
                and commit_map[cl.id].branch == branch_name
            ]
            min_x = min(branch_xs) if branch_xs else None
            max_x = max(branch_xs) if branch_xs else None
            if min_x is not None and max_x is not None:
                parts.append(
                    f'<line x1="{min_x:.1f}" y1="{y:.1f}" '
                    f'x2="{max_x:.1f}" y2="{y:.1f}" '
                    f'stroke="{color}" stroke-width="2" '
                    f'class="gitgraph-branch-line"/>'
                )

    # Branch line segments (connecting consecutive commits on same branch)
    for seg in layout.branch_lines:
        color = branch_color.get(seg.branch, "#999")
        parts.append(
            f'<line x1="{seg.x1:.1f}" y1="{seg.y:.1f}" '
            f'x2="{seg.x2:.1f}" y2="{seg.y:.1f}" '
            f'stroke="{color}" stroke-width="3" '
            f'class="gitgraph-branch-line"/>'
        )

    # Merge and cherry-pick lines
    merge_stroke = theme.edge_stroke if theme is not DEFAULT_THEME else "#999"
    for ml in layout.merge_lines:
        dash = ' stroke-dasharray="6,4"' if ml.is_cherry_pick else ""
        parts.append(
            f'<line x1="{ml.from_x:.1f}" y1="{ml.from_y:.1f}" '
            f'x2="{ml.to_x:.1f}" y2="{ml.to_y:.1f}" '
            f'stroke="{merge_stroke}" stroke-width="2"{dash} '
            f'class="gitgraph-merge-line"/>'
        )

    # Commit circles
    for cl in layout.commits:
        commit = commit_map.get(cl.id)
        if not commit:
            continue

        color = branch_color.get(commit.branch, "#999")

        if commit.commit_type == CommitType.HIGHLIGHT:
            radius = _HIGHLIGHT_RADIUS
            fill = color
            stroke_width = "3"
        elif commit.commit_type == CommitType.REVERSE:
            radius = _NORMAL_RADIUS
            fill = _REVERSE_FILL
            stroke_width = "2"
        else:
            radius = _NORMAL_RADIUS
            fill = color
            stroke_width = "2"

        parts.append(
            f'<circle cx="{cl.x:.1f}" cy="{cl.y:.1f}" r="{radius}" '
            f'fill="{fill}" stroke="{color}" stroke-width="{stroke_width}" '
            f'class="gitgraph-commit"/>'
        )

    # Commit ID labels (user-specified IDs only)
    for cl in layout.commits:
        commit = commit_map.get(cl.id)
        if not commit:
            continue

        # Show ID label if it doesn't look auto-generated
        if not _is_auto_id(commit.id):
            parts.append(
                f'<text x="{cl.x:.1f}" y="{cl.y - 15:.1f}" '
                f'text-anchor="middle" class="gitgraph-label">'
                f"{escape(commit.id)}</text>"
            )

    # Tag labels
    for cl in layout.commits:
        commit = commit_map.get(cl.id)
        if not commit or not commit.tag:
            continue

        tag_y = cl.y + 22
        # Rounded rect badge + text
        tag_text = escape(commit.tag)
        tw = len(commit.tag) * 7 + 12
        tag_fill = theme.subgraph_fill if theme is not DEFAULT_THEME else "#ffffcc"
        tag_stroke = theme.subgraph_stroke if theme is not DEFAULT_THEME else "#999"
        parts.append(
            f'<rect x="{cl.x - tw / 2:.1f}" y="{tag_y - 10:.1f}" '
            f'width="{tw}" height="16" rx="4" ry="4" '
            f'fill="{tag_fill}" stroke="{tag_stroke}" stroke-width="1" '
            f'class="gitgraph-tag-badge"/>'
        )
        parts.append(
            f'<text x="{cl.x:.1f}" y="{tag_y + 2:.1f}" '
            f'text-anchor="middle" class="gitgraph-tag">'
            f"{tag_text}</text>"
        )

    # Branch labels (at the left of each lane)
    for branch_name, (lx, ly) in layout.branch_label_positions.items():
        color = branch_color.get(branch_name, "#333")
        parts.append(
            f'<text x="{lx:.1f}" y="{ly + 4:.1f}" '
            f'fill="{color}" class="gitgraph-branch-label">'
            f"{escape(branch_name)}</text>"
        )

    parts.append("</svg>")
    return "\n".join(parts)

def _is_auto_id(commit_id: str) -> bool:
    """Check if a commit ID looks auto-generated (e.g. '0-main')."""
    parts = commit_id.split("-", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return True
    return False

__all__ = ["render_gitgraph_svg"]
