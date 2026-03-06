"""PyMermaid - Pure Python Mermaid diagram renderer."""

import re

from merm.render import render_svg


def render_diagram(source: str) -> str:
    """Auto-detect diagram type from source text and render to SVG.

    Convenience function that handles the full pipeline:
    parse -> measure -> layout -> render.
    """
    from merm.measure import TextMeasurer

    measurer = TextMeasurer()

    if re.match(r"^\s*sequenceDiagram", source, re.MULTILINE):
        from merm.layout.sequence import layout_sequence
        from merm.parser.sequence import parse_sequence
        from merm.render.sequence import render_sequence_svg

        diagram = parse_sequence(source)
        layout = layout_sequence(diagram, measure_fn=measurer.measure)
        return render_sequence_svg(diagram, layout)

    if re.match(r"^\s*classDiagram", source, re.MULTILINE):
        from merm.layout.classdiag import layout_class_diagram
        from merm.parser import parse_class_diagram
        from merm.render.classdiag import render_class_diagram

        diagram = parse_class_diagram(source)
        layout = layout_class_diagram(diagram, measure_fn=measurer.measure)
        return render_class_diagram(diagram, layout)

    if re.match(r"^\s*erDiagram", source, re.MULTILINE):
        from merm.layout.erdiag import layout_er_diagram
        from merm.parser import parse_er_diagram
        from merm.render.erdiag import render_er_diagram

        diagram = parse_er_diagram(source)
        layout = layout_er_diagram(diagram, measure_fn=measurer.measure)
        return render_er_diagram(diagram, layout)

    if re.match(r"^\s*pie\b", source, re.MULTILINE):
        from merm.parser.pie import parse_pie
        from merm.render.pie import render_pie_svg

        chart = parse_pie(source)
        return render_pie_svg(chart)

    if re.match(r"^\s*mindmap", source, re.MULTILINE):
        from merm.layout.mindmap import layout_mindmap
        from merm.parser.mindmap import parse_mindmap
        from merm.render.mindmap import render_mindmap_svg

        diagram = parse_mindmap(source)
        layout = layout_mindmap(diagram, measure_fn=measurer.measure)
        return render_mindmap_svg(diagram, layout)

    if re.match(r"^\s*gantt\b", source, re.MULTILINE):
        from merm.parser.gantt import parse_gantt
        from merm.render.gantt import render_gantt_svg

        chart = parse_gantt(source)
        return render_gantt_svg(chart)

    if re.match(r"^\s*stateDiagram", source, re.MULTILINE):
        from merm.layout.statediag import layout_state_diagram
        from merm.parser import parse_state_diagram
        from merm.render.statediag import render_state_svg

        diagram = parse_state_diagram(source)
        layout = layout_state_diagram(diagram, measure_fn=measurer.measure)
        return render_state_svg(diagram, layout)

    if re.match(r"^\s*gitGraph", source, re.MULTILINE):
        from merm.layout.gitgraph import layout_gitgraph
        from merm.parser.gitgraph import parse_gitgraph
        from merm.render.gitgraph import render_gitgraph_svg

        graph = parse_gitgraph(source)
        layout = layout_gitgraph(graph, measure_fn=measurer.measure)
        return render_gitgraph_svg(graph, layout)

    # Default: flowchart
    from merm.layout import layout_diagram
    from merm.parser import parse_flowchart

    diagram = parse_flowchart(source)
    layout = layout_diagram(diagram, measure_fn=measurer.measure)
    return render_svg(diagram, layout)

__all__ = ["render_diagram", "render_svg"]
