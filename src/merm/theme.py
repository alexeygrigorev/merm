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

# Dark theme: dark background, light text, blue-ish nodes.
DARK_THEME = Theme(
    node_fill="#1f2937",
    node_stroke="#4a6785",
    node_text_color="#cccccc",
    edge_stroke="#cccccc",
    edge_label_bg="rgba(31,32,32,0.8)",
    subgraph_fill="#2d3748",
    subgraph_stroke="#4a6785",
    text_color="#cccccc",
    background_color="#1f2020",
)

# Forest theme: green-tinted nodes, dark green edges.
FOREST_THEME = Theme(
    node_fill="#cde498",
    node_stroke="#13540c",
    node_text_color="#333333",
    edge_stroke="#13540c",
    edge_label_bg="rgba(205,228,152,0.8)",
    subgraph_fill="#e8f5e9",
    subgraph_stroke="#388e3c",
    text_color="#333333",
    background_color="white",
)

# Neutral theme: grey-scale nodes, neutral edges.
NEUTRAL_THEME = Theme(
    node_fill="#eeeeee",
    node_stroke="#999999",
    node_text_color="#333333",
    edge_stroke="#333333",
    edge_label_bg="rgba(238,238,238,0.8)",
    subgraph_fill="#f5f5f5",
    subgraph_stroke="#cccccc",
    text_color="#333333",
    background_color="white",
)

THEMES: dict[str, Theme] = {
    "default": DEFAULT_THEME,
    "dark": DARK_THEME,
    "forest": FOREST_THEME,
    "neutral": NEUTRAL_THEME,
}


def get_theme(name: str) -> Theme:
    """Return the built-in theme with the given name.

    Args:
        name: Theme name (case-sensitive). One of: default, dark, forest, neutral.

    Returns:
        The matching Theme instance.

    Raises:
        ValueError: If the name does not match any built-in theme.
    """
    try:
        return THEMES[name]
    except KeyError:
        valid = ", ".join(sorted(THEMES))
        raise ValueError(
            f"Unknown theme {name!r}. Valid themes: {valid}"
        ) from None
