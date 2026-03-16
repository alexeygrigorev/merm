"""PyMermaid - Pure Python Mermaid diagram renderer."""

from __future__ import annotations

import re
from pathlib import Path

from merm.parser import (
    ParseError,
    parse_class_diagram,
    parse_flowchart,
    parse_state_diagram,
)
from merm.parser.sequence import parse_sequence
from merm.render import render_svg
from merm.theme import DEFAULT_THEME, Theme, get_theme

_SUPPORTED_TYPES = [
    "flowchart / graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "pie",
    "mindmap",
    "gantt",
    "gitGraph",
]

# Regex matching %%{init: {'theme': '...'}}%% or %%{init: {"theme": "..."}}%%
_INIT_DIRECTIVE_RE = re.compile(
    r"""^\s*%%\{\s*init\s*:\s*\{[^}]*['"]theme['"]\s*:\s*['"](\w+)['"]\s*[^}]*\}\s*\}%%\s*$""",
    re.MULTILINE,
)


def _extract_theme_directive(source: str) -> tuple[str | None, str]:
    """Extract theme name from %%{init}%% directive and strip the directive.

    Returns:
        A tuple of (theme_name_or_None, cleaned_source).
    """
    match = _INIT_DIRECTIVE_RE.search(source)
    if match is None:
        return None, source
    theme_name = match.group(1)
    cleaned = source[:match.start()] + source[match.end():]
    # Remove the blank line left behind if directive was on its own line
    cleaned = cleaned.lstrip("\n")
    return theme_name, cleaned


def _resolve_theme(
    theme_arg: Theme | str | None,
    source: str,
) -> tuple[Theme, str]:
    """Resolve the effective theme and clean source.

    Priority: explicit theme_arg > %%{init}%% directive > DEFAULT_THEME.

    Returns:
        (resolved_theme, cleaned_source)
    """
    directive_name, cleaned_source = _extract_theme_directive(source)

    if theme_arg is not None:
        if isinstance(theme_arg, str):
            return get_theme(theme_arg), cleaned_source
        return theme_arg, cleaned_source

    if directive_name is not None:
        return get_theme(directive_name), cleaned_source

    return DEFAULT_THEME, cleaned_source


def render_diagram(source: str, *, theme: Theme | str | None = None) -> str:
    """Auto-detect diagram type from source text and render to SVG.

    Convenience function that handles the full pipeline:
    parse -> measure -> layout -> render.

    Args:
        source: Mermaid diagram source text.
        theme: Optional theme. Can be a Theme instance, a theme name string
            (one of "default", "dark", "forest", "neutral"), or None.
            If None, the theme is auto-detected from a ``%%{init}%%``
            directive in the source, falling back to the default theme.
            An explicit theme argument always overrides the directive.

    Returns:
        A string containing valid SVG XML.

    Raises:
        ValueError: If source is empty or whitespace-only.
        ParseError: If the diagram source contains invalid syntax.
    """
    if not source or not source.strip():
        raise ValueError("Empty diagram source")

    resolved_theme, source = _resolve_theme(theme, source)

    from merm.measure import TextMeasurer

    measurer = TextMeasurer()

    if re.match(r"^\s*sequenceDiagram", source, re.MULTILINE):
        from merm.layout.sequence import layout_sequence
        from merm.render.sequence import render_sequence_svg

        diagram = parse_sequence(source)
        layout = layout_sequence(diagram, measure_fn=measurer.measure)
        return render_sequence_svg(diagram, layout, theme=resolved_theme)

    if re.match(r"^\s*classDiagram", source, re.MULTILINE):
        from merm.layout.classdiag import layout_class_diagram
        from merm.render.classdiag import render_class_diagram

        diagram = parse_class_diagram(source)
        layout = layout_class_diagram(diagram, measure_fn=measurer.measure)
        return render_class_diagram(diagram, layout, theme=resolved_theme)

    if re.match(r"^\s*erDiagram", source, re.MULTILINE):
        from merm.layout.erdiag import layout_er_diagram
        from merm.parser import parse_er_diagram
        from merm.render.erdiag import render_er_diagram

        diagram = parse_er_diagram(source)
        layout = layout_er_diagram(diagram, measure_fn=measurer.measure)
        return render_er_diagram(diagram, layout, theme=resolved_theme)

    if re.match(r"^\s*pie\b", source, re.MULTILINE):
        from merm.parser.pie import parse_pie
        from merm.render.pie import render_pie_svg

        chart = parse_pie(source)
        return render_pie_svg(chart, theme=resolved_theme)

    if re.match(r"^\s*mindmap", source, re.MULTILINE):
        from merm.layout.mindmap import layout_mindmap
        from merm.parser.mindmap import parse_mindmap
        from merm.render.mindmap import render_mindmap_svg

        diagram = parse_mindmap(source)
        layout = layout_mindmap(diagram, measure_fn=measurer.measure)
        return render_mindmap_svg(diagram, layout, theme=resolved_theme)

    if re.match(r"^\s*gantt\b", source, re.MULTILINE):
        from merm.parser.gantt import parse_gantt
        from merm.render.gantt import render_gantt_svg

        chart = parse_gantt(source)
        return render_gantt_svg(chart, theme=resolved_theme)

    if re.match(r"^\s*stateDiagram", source, re.MULTILINE):
        from merm.layout.statediag import layout_state_diagram
        from merm.render.statediag import render_state_svg

        diagram = parse_state_diagram(source)
        layout = layout_state_diagram(diagram, measure_fn=measurer.measure)
        return render_state_svg(diagram, layout, theme=resolved_theme)

    if re.match(r"^\s*gitGraph", source, re.MULTILINE):
        from merm.layout.gitgraph import layout_gitgraph
        from merm.parser.gitgraph import parse_gitgraph
        from merm.render.gitgraph import render_gitgraph_svg

        graph = parse_gitgraph(source)
        layout = layout_gitgraph(graph, measure_fn=measurer.measure)
        return render_gitgraph_svg(graph, layout, theme=resolved_theme)

    # Default: flowchart
    from merm.layout import layout_diagram

    diagram = parse_flowchart(source)
    layout = layout_diagram(diagram, measure_fn=measurer.measure)
    return render_svg(diagram, layout, theme=resolved_theme)


def render_to_file(
    source: str,
    path: str | Path,
    *,
    theme: Theme | str | None = None,
) -> None:
    """Render a Mermaid diagram to a file.

    The output format is auto-detected from the file extension:
    - ``.png`` -- renders SVG then converts to PNG via cairosvg
    - ``.svg`` (or any other extension) -- writes SVG text

    Args:
        source: Mermaid diagram source text.
        path: Output file path. Parent directory must exist.
        theme: Optional theme (Theme instance, name string, or None).

    Raises:
        FileNotFoundError: If the parent directory does not exist.
        ImportError: If cairosvg is not installed and a ``.png`` path is given.
        ValueError: If source is empty or whitespace-only.
    """
    path = Path(path)
    if not path.parent.exists():
        raise FileNotFoundError(
            f"Parent directory does not exist: {path.parent}"
        )

    svg = render_diagram(source, theme=theme)

    if path.suffix.lower() == ".png":
        png_bytes = _svg_to_png(svg)
        path.write_bytes(png_bytes)
    else:
        path.write_text(svg, encoding="utf-8")


def render_to_png(
    source: str,
    *,
    theme: Theme | str | None = None,
) -> bytes:
    """Render a Mermaid diagram to PNG bytes.

    Args:
        source: Mermaid diagram source text.
        theme: Optional theme (Theme instance, name string, or None).

    Returns:
        PNG image as bytes.

    Raises:
        ImportError: If cairosvg is not installed.
        ValueError: If source is empty or whitespace-only.
    """
    svg = render_diagram(source, theme=theme)
    return _svg_to_png(svg)


def _svg_to_png(svg: str) -> bytes:
    """Convert SVG string to PNG bytes using cairosvg."""
    try:
        import cairosvg
    except ImportError:
        raise ImportError(
            "cairosvg is required for PNG rendering. "
            "Install it with: pip install cairosvg"
        ) from None
    return cairosvg.svg2png(bytestring=svg.encode("utf-8"))


__all__ = [
    "DEFAULT_THEME",
    "ParseError",
    "Theme",
    "get_theme",
    "parse_class_diagram",
    "parse_flowchart",
    "parse_sequence",
    "parse_state_diagram",
    "render_diagram",
    "render_svg",
    "render_to_file",
    "render_to_png",
]
