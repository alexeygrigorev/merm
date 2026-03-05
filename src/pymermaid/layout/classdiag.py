"""Class diagram layout: convert ClassDiagram to flowchart IR for Sugiyama layout.

Maps class nodes to flowchart Nodes and class relations to Edges,
then uses the Sugiyama layout engine to position them.
"""

from pymermaid.ir import (
    Diagram,
    DiagramType,
    Direction,
    Edge,
    Node,
    NodeShape,
)
from pymermaid.ir.classdiag import ClassDiagram, RelationType
from pymermaid.layout.config import LayoutConfig, MeasureFn
from pymermaid.layout.sugiyama import _NODE_PADDING_H, _NODE_PADDING_V, layout_diagram
from pymermaid.layout.types import EdgeLayout, LayoutResult, NodeLayout, Point
from pymermaid.render.classdiag import measure_class_box

# Relationship types where the edge direction should be reversed in
# the layout so the parent/interface is at the top (source, layer 0).
_REVERSED_RELS = {RelationType.INHERITANCE, RelationType.REALIZATION}

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
        # For inheritance/realization, reverse the edge so that the
        # parent/interface is the source (layer 0, top in TB layout).
        if rel.rel_type in _REVERSED_RELS:
            edges.append(Edge(
                source=rel.target,  # parent becomes source (top)
                target=rel.source,  # child becomes target (bottom)
                label=rel.label or None,
            ))
        else:
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
                # Subtract the exact padding that layout_diagram will add back
                return w - _NODE_PADDING_H, h - _NODE_PADDING_V
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

    # Re-route edge endpoints to connect cleanly to adjusted class boxes (issue 4)
    adjusted_edges = _reroute_edges(result.edges, adjusted_nodes)

    return LayoutResult(
        nodes=adjusted_nodes,
        edges=adjusted_edges,
        width=result.width,
        height=result.height,
        subgraphs=result.subgraphs,
    )

def _snap_to_boundary(
    point: Point, nl: NodeLayout, interior: Point,
) -> Point:
    """Snap a point to the nearest edge of a node's bounding rectangle.

    The *interior* point indicates the direction from which the edge
    approaches so we pick the correct side.
    """
    cx = nl.x + nl.width / 2
    cy = nl.y + nl.height / 2

    dx = interior.x - cx
    dy = interior.y - cy

    # Determine which side to snap to based on direction from center
    if abs(dx) < 0.01 and abs(dy) < 0.01:
        # Degenerate: just return original
        return point

    # Check if edge exits top/bottom vs left/right
    if nl.width > 0 and nl.height > 0:
        aspect = (abs(dy) / nl.height) - (abs(dx) / nl.width)
    else:
        aspect = 0.0

    if aspect >= 0:
        # Top or bottom
        if dy >= 0:
            return Point(cx, nl.y + nl.height)  # bottom
        else:
            return Point(cx, nl.y)  # top
    else:
        # Left or right
        if dx >= 0:
            return Point(nl.x + nl.width, cy)  # right
        else:
            return Point(nl.x, cy)  # left

def _reroute_edges(
    edges: list[EdgeLayout],
    nodes: dict[str, NodeLayout],
) -> list[EdgeLayout]:
    """Re-route edge endpoints to land on adjusted node boundaries."""
    result: list[EdgeLayout] = []
    for el in edges:
        pts = list(el.points)
        if len(pts) < 2:
            result.append(el)
            continue

        src_nl = nodes.get(el.source)
        tgt_nl = nodes.get(el.target)

        if src_nl is not None:
            # Snap first point to source boundary
            interior = pts[1]
            pts[0] = _snap_to_boundary(pts[0], src_nl, interior)

        if tgt_nl is not None:
            # Snap last point to target boundary
            interior = pts[-2]
            pts[-1] = _snap_to_boundary(pts[-1], tgt_nl, interior)

        result.append(EdgeLayout(points=pts, source=el.source, target=el.target))
    return result

__all__ = [
    "class_diagram_to_flowchart",
    "layout_class_diagram",
]
