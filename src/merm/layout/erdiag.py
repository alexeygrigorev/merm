"""ER diagram layout: convert ERDiagram to flowchart IR for Sugiyama layout.

Maps ER entities to flowchart Nodes and relationships to Edges,
then uses the Sugiyama layout engine to position them.
"""

from merm.ir import (
    Diagram,
    DiagramType,
    Direction,
    Edge,
    Node,
    NodeShape,
)
from merm.ir.erdiag import ERDiagram
from merm.layout.config import LayoutConfig, MeasureFn
from merm.layout.sugiyama import _NODE_PADDING_H, _NODE_PADDING_V, layout_diagram
from merm.layout.types import EdgeLayout, LayoutResult, NodeLayout, Point
from merm.render.erdiag import measure_er_entity_box


def er_diagram_to_flowchart(diagram: ERDiagram) -> Diagram:
    """Convert an ERDiagram to a flowchart Diagram for layout."""
    nodes: list[Node] = []
    edges: list[Edge] = []

    for entity in diagram.entities:
        nodes.append(Node(
            id=entity.id,
            label=entity.id,
            shape=NodeShape.rect,
        ))

    for rel in diagram.relationships:
        edges.append(Edge(
            source=rel.source,
            target=rel.target,
            label=rel.label or None,
        ))

    return Diagram(
        type=DiagramType.flowchart,
        direction=Direction.TB,
        nodes=tuple(nodes),
        edges=tuple(edges),
    )

def layout_er_diagram(
    diagram: ERDiagram,
    measure_fn: MeasureFn,
    config: LayoutConfig | None = None,
) -> LayoutResult:
    """Lay out an ER diagram using the Sugiyama algorithm.

    Uses the entity box measurement function to determine node sizes,
    then delegates to the Sugiyama layout engine.
    """
    flowchart = er_diagram_to_flowchart(diagram)

    # Pre-compute entity box sizes
    entity_sizes: dict[str, tuple[float, float]] = {}
    for entity in diagram.entities:
        entity_sizes[entity.id] = measure_er_entity_box(entity)

    # Custom measure function that returns pre-computed sizes
    def _entity_measure(text: str, font_size: float) -> tuple[float, float]:
        # Find the entity by id (label == id for ER entities)
        for entity in diagram.entities:
            if entity.id == text:
                w, h = entity_sizes[entity.id]
                # Subtract the exact padding that layout_diagram will add back
                return w - _NODE_PADDING_H, h - _NODE_PADDING_V
        return measure_fn(text, font_size)

    if config is None:
        config = LayoutConfig(
            direction=Direction.TB,
            rank_sep=20.0,
            node_sep=35.0,
        )

    result = layout_diagram(flowchart, measure_fn=_entity_measure, config=config)

    # Ensure entity boxes use their measured sizes
    adjusted_nodes: dict[str, NodeLayout] = {}
    for nid, nl in result.nodes.items():
        if nid in entity_sizes:
            w, h = entity_sizes[nid]
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

    # Re-route edge endpoints to connect cleanly to adjusted entity boxes
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
    """Snap a point to the nearest edge of a node's bounding rectangle."""
    cx = nl.x + nl.width / 2
    cy = nl.y + nl.height / 2

    dx = interior.x - cx
    dy = interior.y - cy

    if abs(dx) < 0.01 and abs(dy) < 0.01:
        return point

    if nl.width > 0 and nl.height > 0:
        aspect = (abs(dy) / nl.height) - (abs(dx) / nl.width)
    else:
        aspect = 0.0

    if aspect >= 0:
        if dy >= 0:
            return Point(cx, nl.y + nl.height)  # bottom
        else:
            return Point(cx, nl.y)  # top
    else:
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
            interior = pts[1]
            pts[0] = _snap_to_boundary(pts[0], src_nl, interior)

        if tgt_nl is not None:
            interior = pts[-2]
            pts[-1] = _snap_to_boundary(pts[-1], tgt_nl, interior)

        result.append(EdgeLayout(points=pts, source=el.source, target=el.target))
    return result

__all__ = [
    "er_diagram_to_flowchart",
    "layout_er_diagram",
]
