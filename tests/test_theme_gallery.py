"""Tests for theme gallery generation and theme rendering across diagram types."""

from pathlib import Path

import pytest

from merm import render_diagram
from merm.theme import THEMES

GALLERY_DIAGRAMS = {
    "flowchart": """\
flowchart TD
    A[Start] --> B{Decision?}
    B -->|Yes| C[Do something]
    B -->|No| D[Do something else]
    C --> E[End]
    D --> E
""",
    "sequence": """\
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>Bob: Hello Bob!
    Bob-->>Alice: Hi Alice!
""",
    "class": """\
classDiagram
    class Animal {
        +String name
        +makeSound()
    }
    class Dog {
        +fetch()
    }
    Animal <|-- Dog
""",
}


@pytest.mark.parametrize("theme_name", list(THEMES.keys()))
@pytest.mark.parametrize("diagram_name", list(GALLERY_DIAGRAMS.keys()))
def test_render_diagram_with_theme(theme_name: str, diagram_name: str) -> None:
    """Each diagram type renders successfully with each built-in theme."""
    source = GALLERY_DIAGRAMS[diagram_name]
    svg = render_diagram(source, theme=theme_name)
    assert svg.startswith("<svg")
    assert "</svg>" in svg


@pytest.mark.parametrize("theme_name", list(THEMES.keys()))
def test_theme_colors_appear_in_flowchart_svg(theme_name: str) -> None:
    """The node fill color from the theme appears in the rendered SVG."""
    source = "flowchart TD\n    A[Hello] --> B[World]\n"
    theme = THEMES[theme_name]
    svg = render_diagram(source, theme=theme_name)
    # Node fill color should appear somewhere in the SVG
    assert theme.node_fill.lower() in svg.lower()


def test_gallery_svgs_exist() -> None:
    """All expected gallery SVG files exist (after running the generation script)."""
    themes_dir = Path(__file__).parent.parent / "docs" / "themes"
    if not themes_dir.exists():
        pytest.skip("docs/themes/ not yet generated")
    for theme_name in THEMES:
        for diagram_name in ("flowchart", "sequence", "class"):
            svg_path = themes_dir / f"{diagram_name}_{theme_name}.svg"
            assert svg_path.exists(), f"Missing gallery SVG: {svg_path.name}"
            content = svg_path.read_text()
            assert content.startswith("<svg"), f"{svg_path.name} is not valid SVG"


def test_themes_md_exists() -> None:
    """docs/themes.md exists and references all four themes."""
    md_path = Path(__file__).parent.parent / "docs" / "themes.md"
    if not md_path.exists():
        pytest.skip("docs/themes.md not yet created")
    content = md_path.read_text()
    for theme_name in THEMES:
        assert theme_name in content, f"themes.md missing reference to {theme_name}"
