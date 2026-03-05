"""Class diagram layout: convert ClassDiagram to flowchart IR for Sugiyama layout.

Maps class nodes to flowchart Nodes and class relations to Edges,
then uses the Sugiyama layout engine to position them.
"""

from __future__ import annotations

from pymermaid.ir import (
    Diagram,
    DiagramType,
    Direction,
    Edge,
    Node,
    NodeShape,
)
from pymermaid.ir.classdiag import ClassDiagram
from pymermaid.layout.config import LayoutConfig, MeasureFn
from pymermaid.layout.sugiyama import layout_diagram
from pymermaid.layout.types import LayoutResult, NodeLayout
from pymermaid.render.classdiag import measure_class_box


def class_diagram_to_flowchart(diagram: ClassDiagram) -> Diagram:
    """Convert a ClassDiagram to a flowchart Diagram for layout."""
    nodes: list[Node] = []
    edges: list[Edge] = []

    for cls in diagram.classes:
        nodes.append(Node(
            id=cls.id,
            label=cls.label,
            shape=NodeShape.rect,
        ))

    for rel in diagram.relations:
        edges.append(Edge(
            source=rel.source,
            target=rel.target,
            label=rel.label or None,
        ))

    return Diagram(
        type=DiagramType.class_diagram,
        direction=Direction.TB,
        nodes=tuple(nodes),
        edges=tuple(edges),
    )


def layout_class_diagram(
    diagram: ClassDiagram,
    measure_fn: MeasureFn,
    config: LayoutConfig | None = None,
) -> LayoutResult:
    """Lay out a class diagram using the Sugiyama algorithm.

    Uses the class box measurement function to determine node sizes,
    then delegates to the Sugiyama layout engine.
    """
    flowchart = class_diagram_to_flowchart(diagram)

    # Pre-compute class box sizes
    class_sizes: dict[str, tuple[float, float]] = {}
    for cls in diagram.classes:
        class_sizes[cls.id] = measure_class_box(cls)

    # Custom measure function that returns pre-computed sizes
    def _class_measure(text: str, font_size: float) -> tuple[float, float]:
        # Find the class by label
        for cls in diagram.classes:
            if cls.label == text:
                w, h = class_sizes[cls.id]
                # Subtract padding that layout_diagram will add back
                return w - 30.0, h - 20.0
        return measure_fn(text, font_size)

    if config is None:
        config = LayoutConfig(direction=Direction.TB)

    result = layout_diagram(flowchart, measure_fn=_class_measure, config=config)

    # Ensure class boxes use their measured sizes
    adjusted_nodes: dict[str, NodeLayout] = {}
    for nid, nl in result.nodes.items():
        if nid in class_sizes:
            w, h = class_sizes[nid]
            cx = nl.x + nl.width / 2
            cy = nl.y + nl.height / 2
            adjusted_nodes[nid] = NodeLayout(
                x=cx - w / 2,
                y=cy - h / 2,
                width=w,
                height=h,
            )
        else:
            adjusted_nodes[nid] = nl

    return LayoutResult(
        nodes=adjusted_nodes,
        edges=result.edges,
        width=result.width,
        height=result.height,
        subgraphs=result.subgraphs,
    )


__all__ = [
    "class_diagram_to_flowchart",
    "layout_class_diagram",
]
