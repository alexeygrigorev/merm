"""Theme system for merm SVG rendering.

Provides a Theme dataclass that centralizes all styling values (colors, sizes,
spacing) used by the renderer and layout engine. The DEFAULT_THEME instance
matches mermaid.js's default theme (purple nodes, yellow subgraphs).
"""

from dataclasses import dataclass, replace

@dataclass(frozen=True)
class Theme:
    """All visual styling values for diagram rendering.

    Every color, size, and spacing value used by the SVG renderer and layout
    engine is stored here. The renderer reads from a Theme instance rather
    than using module-level constants.
    """

    # Node styling
    node_fill: str = "#ECECFF"
    node_stroke: str = "#9370DB"
    node_stroke_width: str = "1"
    node_text_color: str = "#333333"
    node_font_size: str = "16px"
    node_padding_h: float = 16.0
    node_padding_v: float = 8.0
    node_min_height: float = 42.0
    node_min_width: float = 70.0
    node_border_radius: float = 5.0

    # Edge styling
    edge_stroke: str = "#333333"
    edge_stroke_width: str = "2"
    edge_label_bg: str = "rgba(232,232,232,0.8)"
    edge_label_font_size: str = "12px"

    # Subgraph styling
    subgraph_fill: str = "#ffffde"
    subgraph_stroke: str = "#aaaa33"
    subgraph_stroke_width: str = "1"
    subgraph_title_font_size: str = "12px"

    # General
    font_family: str = (
        '"trebuchet ms", verdana, arial, sans-serif, '
        '"Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", '
        '"Twemoji Mozilla"'
    )
    text_color: str = "#333333"
    background_color: str = "white"

    # Layout spacing
    rank_sep: float = 40.0
    node_sep: float = 30.0

    def replace(self, **kwargs: object) -> "Theme":
        """Return a new Theme with specified fields overridden."""
        return replace(self, **kwargs)

# Singleton default theme matching mermaid.js defaults.
DEFAULT_THEME = Theme()
