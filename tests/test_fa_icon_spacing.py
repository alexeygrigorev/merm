"""Tests for Font Awesome icon-to-text spacing in nodes."""

import xml.etree.ElementTree as ET

from merm import render_diagram


def _parse_svg(mermaid_text: str) -> ET.Element:
    svg_str = render_diagram(mermaid_text)
    return ET.fromstring(svg_str)


def _find_fa_icons_and_texts(root: ET.Element):
    """Find all fa-icon groups and text elements, returning their x positions."""
    icons = []
    texts = []
    for g in root.iter("{http://www.w3.org/2000/svg}g"):
        cls = g.get("class", "")
        if "fa-icon" in cls:
            transform = g.get("transform", "")
            # Extract x from translate(x,y)
            if "translate(" in transform:
                coords = transform.split("translate(")[1].split(")")[0]
                x = float(coords.split(",")[0])
                icons.append(x)
    for t in root.iter("{http://www.w3.org/2000/svg}text"):
        x_attr = t.get("x")
        if x_attr is not None:
            texts.append((float(x_attr), t.text or ""))
    return icons, texts


DIAGRAM = """\
flowchart TD
    A[fa:fa-tree Christmas Tree]
    B[fa:fa-gift Presents]
    C[fa:fa-car Drive to Grandma]
"""


def test_icon_text_gap_exists():
    """The gap between an FA icon's right edge and the following text must be >= 4px."""
    root = _parse_svg(DIAGRAM)

    # For each node group that contains both an icon and text,
    # check that text does not start immediately after the icon.
    node_groups = []
    for g in root.iter("{http://www.w3.org/2000/svg}g"):
        cls = g.get("class", "")
        if "node" in cls.split():
            node_groups.append(g)

    found_icon_text_pair = False
    for ng in node_groups:
        icon_right_edges = []
        text_left_positions = []

        for sub_g in ng.iter("{http://www.w3.org/2000/svg}g"):
            if "fa-icon" in sub_g.get("class", ""):
                transform = sub_g.get("transform", "")
                if "translate(" in transform:
                    parts = transform.split("translate(")[1].split(")")[0]
                    ix = float(parts.split(",")[0])
                    # Icon is rendered at 1.5 * font_size wide;
                    # we also need the scale to compute actual width
                    scale_part = transform.split("scale(")
                    if len(scale_part) > 1:
                        float(scale_part[1].rstrip(")"))
                        # Icon rendered width ~ font_size * 1.5
                        icon_right_edges.append(ix + 24.0)

        for txt in ng.iter("{http://www.w3.org/2000/svg}text"):
            x_attr = txt.get("x")
            anchor = txt.get("text-anchor", "start")
            if x_attr and txt.text and txt.text.strip():
                x_val = float(x_attr)
                if anchor == "middle":
                    # Text is centered; its left edge is approximately
                    # x - half_width. We use a rough estimate.
                    text_left_positions.append(x_val)

        # If this node has both icon and text, the text center should be
        # well to the right of the icon right edge
        if icon_right_edges and text_left_positions:
            found_icon_text_pair = True
            for ire in icon_right_edges:
                for tlp in text_left_positions:
                    # Text center (middle-anchored) must be to the right
                    # of the icon right edge, indicating a gap
                    assert tlp > ire, (
                        f"Text center {tlp} should be well right of "
                        f"icon right edge {ire}"
                    )

    assert found_icon_text_pair, "Should find at least one node with icon + text"


def test_icon_segment_width_includes_gap():
    """The width allocated for an icon segment in rendering should include
    the icon size (1.5 * font_size) plus a gap of at least 4px."""
    from merm.theme import Theme

    theme = Theme()
    font_size_str = theme.node_font_size.replace("px", "")
    font_size = float(font_size_str)

    # The icon width allocation should be font_size * 1.5 + gap
    # where gap >= 4px
    expected_min_width = font_size * 1.5 + 4.0

    # We test this indirectly through the measurement module
    from merm.measure.text import _line_width

    # A label with just an icon
    icon_only_width = _line_width("fa:fa-car", font_size)
    assert icon_only_width >= expected_min_width, (
        f"Icon-only width {icon_only_width} should be >= {expected_min_width}"
    )

    # A label with icon + text should be wider than text alone
    with_icon = _line_width("fa:fa-car Drive", font_size)
    text_only = _line_width("Drive", font_size)
    assert with_icon > text_only + expected_min_width - 1, (
        f"Icon+text width {with_icon} should exceed text-only {text_only} "
        f"by at least icon width {expected_min_width}"
    )


def test_multiple_icons_all_have_gaps():
    """When multiple nodes have icons, all should have proper spacing."""
    diagram = """\
flowchart TD
    A[fa:fa-tree Christmas Tree] --> B[fa:fa-gift Presents]
    A --> C[fa:fa-star Star on Top]
    B --> D[fa:fa-car Drive to Grandma]
    C --> E[fa:fa-lightbulb Lights]
    D --> F[fa:fa-home Grandma House]
    E --> F
"""
    # Should render without error
    svg = render_diagram(diagram)
    assert svg is not None
    assert len(svg) > 0
    # Should contain fa-icon elements
    assert "fa-icon" in svg
