"""PyMermaid - Pure Python Mermaid diagram renderer."""

from __future__ import annotations

import re

from pymermaid.render import render_svg


def render_diagram(source: str) -> str:
    """Auto-detect diagram type from source text and render to SVG.

    Convenience function that handles the full pipeline:
    parse -> measure -> layout -> render.
    """
    from pymermaid.measure import TextMeasurer

    measurer = TextMeasurer()

    if re.match(r"^\s*sequenceDiagram", source, re.MULTILINE):
        from pymermaid.layout.sequence import layout_sequence
        from pymermaid.parser.sequence import parse_sequence
        from pymermaid.render.sequence import render_sequence_svg

        diagram = parse_sequence(source)
        layout = layout_sequence(diagram, measure_fn=measurer.measure)
        return render_sequence_svg(diagram, layout)

    if re.match(r"^\s*classDiagram", source, re.MULTILINE):
        from pymermaid.layout.classdiag import layout_class_diagram
        from pymermaid.parser import parse_class_diagram
        from pymermaid.render.classdiag import render_class_diagram

        diagram = parse_class_diagram(source)
        layout = layout_class_diagram(diagram, measure_fn=measurer.measure)
        return render_class_diagram(diagram, layout)

    if re.match(r"^\s*stateDiagram", source, re.MULTILINE):
        from pymermaid.layout.statediag import layout_state_diagram
        from pymermaid.parser import parse_state_diagram
        from pymermaid.render.statediag import render_state_svg

        diagram = parse_state_diagram(source)
        layout = layout_state_diagram(diagram, measure_fn=measurer.measure)
        return render_state_svg(diagram, layout)

    # Default: flowchart
    from pymermaid.layout import layout_diagram
    from pymermaid.parser import parse_flowchart

    diagram = parse_flowchart(source)
    layout = layout_diagram(diagram, measure_fn=measurer.measure)
    return render_svg(diagram, layout)


__all__ = ["render_diagram", "render_svg"]
