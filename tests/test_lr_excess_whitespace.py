"""Tests for issue 84: excessive whitespace below LR pipeline diagrams.

After the direction transform (e.g. LR swaps axes), node centres could
be offset from the origin, leaving large unused margins.  The fix
normalises positions so the minimum node edge is always at 0.
"""

import re

from merm import render_diagram
from merm.layout.sugiyama import layout_diagram
from merm.measure.text import measure_text
from merm.parser import parse_flowchart

ETL_SIMPLE = """\
graph LR
  Extract[Extract Data via HTTP REST API] --> Transform[Transform Data in Python]
  Transform --> Query[Query Data with DuckDB]
"""


def _svg_dimensions(svg: str) -> tuple[float, float]:
    """Extract width and height from an SVG string."""
    w = float(re.search(r'width="([^"]+)"', svg).group(1))
    h = float(re.search(r'height="([^"]+)"', svg).group(1))
    return w, h


def test_lr_pipeline_no_excess_whitespace():
    """The SVG height should tightly wrap the nodes (no doubled height)."""
    svg = render_diagram(ETL_SIMPLE)
    _, height = _svg_dimensions(svg)
    # Nodes are ~60px tall + 2*8 padding = ~77px.
    # Before fix, height was ~155px (doubled).
    assert height < 100, f"SVG height {height} is too large; expected < 100"


def test_lr_layout_nodes_start_near_origin():
    """After LR transform, node y-positions should start near 0."""
    diagram = parse_flowchart(ETL_SIMPLE)
    layout = layout_diagram(diagram, measure_text)
    min_y = min(nl.y for nl in layout.nodes.values())
    # Nodes should start at y=0 (no wasted offset)
    assert min_y == 0.0, f"Minimum node y={min_y}, expected 0.0"


def test_lr_layout_height_matches_content():
    """Layout height should equal max node bottom, not inflated."""
    diagram = parse_flowchart(ETL_SIMPLE)
    layout = layout_diagram(diagram, measure_text)
    max_bottom = max(nl.y + nl.height for nl in layout.nodes.values())
    assert layout.height == max_bottom, (
        f"Layout height {layout.height} != max node bottom {max_bottom}"
    )


def test_tb_layout_unaffected():
    """TB layouts should not be changed by this fix."""
    tb_diagram = """\
graph TB
  A --> B --> C
"""
    diagram = parse_flowchart(tb_diagram)
    layout = layout_diagram(diagram, measure_text)
    min_x = min(nl.x for nl in layout.nodes.values())
    min_y = min(nl.y for nl in layout.nodes.values())
    # TB should already have reasonable positioning
    assert min_x >= 0.0
    assert min_y >= 0.0


def test_rl_pipeline_no_excess_whitespace():
    """RL direction should also be tight (same transform path as LR)."""
    rl_text = ETL_SIMPLE.replace("graph LR", "graph RL")
    svg = render_diagram(rl_text)
    _, height = _svg_dimensions(svg)
    assert height < 100, f"RL SVG height {height} is too large"
