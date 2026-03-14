"""State diagram layout: convert StateDiagram to flowchart IR for Sugiyama layout.

This module bridges the state diagram IR to the flowchart-based layout engine,
mapping states to nodes and transitions to edges. Composite states become
subgraphs.
"""

import math

from merm.ir import (
    Diagram,
    DiagramType,
    Direction,
    Edge,
    Node,
    NodeShape,
    Subgraph,
)
from merm.ir.statediag import (
    State,
    StateDiagram,
    StateType,
)
from merm.layout.config import LayoutConfig, MeasureFn
from merm.layout.sugiyama import layout_diagram
from merm.layout.types import EdgeLayout, LayoutResult, NodeLayout, Point

# Size constants for pseudo-states
_START_END_SIZE = 20.0  # diameter for start/end circles
_FORK_JOIN_WIDTH = 80.0
_FORK_JOIN_HEIGHT = 8.0
_CHOICE_SIZE = 30.0

def _state_to_node_shape(state_type: StateType) -> NodeShape:
    """Map state type to a node shape for layout sizing."""
    match state_type:
        case StateType.START | StateType.END:
            return NodeShape.circle
        case StateType.CHOICE:
            return NodeShape.diamond
        case StateType.FORK | StateType.JOIN:
            return NodeShape.rect
        case _:
            return NodeShape.rounded

def state_diagram_to_flowchart(diagram: StateDiagram) -> Diagram:
    """Convert a StateDiagram into a flowchart Diagram for layout.

    States become Nodes, transitions become Edges, and composite
    states with children become Subgraphs.
    """
    nodes: list[Node] = []
    edges: list[Edge] = []
    subgraphs: list[Subgraph] = []

    def _add_state(state: State) -> None:
        shape = _state_to_node_shape(state.state_type)
        nodes.append(Node(
            id=state.id,
            label=state.label,
            shape=shape,
        ))
        if state.children:
            child_ids: list[str] = []
            for child in state.children:
                _add_state(child)
                child_ids.append(child.id)
            subgraphs.append(Subgraph(
                id=state.id,
                title=state.label,
                node_ids=tuple(child_ids),
            ))

    for state in diagram.states:
        _add_state(state)

    for trans in diagram.transitions:
        edges.append(Edge(
            source=trans.source,
            target=trans.target,
            label=trans.label or None,
        ))

    return Diagram(
        type=DiagramType.state,
        direction=Direction.TB,
        nodes=tuple(nodes),
        edges=tuple(edges),
        subgraphs=tuple(subgraphs),
    )

def _circle_boundary_point(cx: float, cy: float, radius: float,
                           ref_x: float, ref_y: float) -> Point:
    """Compute the point on a circle boundary closest to (ref_x, ref_y).

    Given a circle at (cx, cy) with the given radius, find where the line
    from the center to the reference point intersects the circle boundary.
    If ref equals the center, default to the bottom of the circle.
    """
    dx = ref_x - cx
    dy = ref_y - cy
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        # Reference point is at center; default to bottom
        return Point(cx, cy + radius)
    return Point(cx + radius * dx / dist, cy + radius * dy / dist)


def _rect_boundary_point(nl: NodeLayout, ref_x: float, ref_y: float) -> Point:
    """Compute the point on a rectangle boundary closest to (ref_x, ref_y).

    Uses ray-casting from center to the reference point to find the
    intersection with the rectangle boundary.
    """
    cx = nl.x + nl.width / 2
    cy = nl.y + nl.height / 2
    dx = ref_x - cx
    dy = ref_y - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return Point(cx, cy + nl.height / 2)

    hw = nl.width / 2
    hh = nl.height / 2

    # Scale factors to reach each edge
    scales: list[float] = []
    if abs(dx) > 1e-6:
        scales.append(hw / abs(dx))
    if abs(dy) > 1e-6:
        scales.append(hh / abs(dy))

    t = min(scales) if scales else 1.0
    return Point(cx + dx * t, cy + dy * t)


def _reroute_edges(
    edges: list[EdgeLayout],
    adjusted_nodes: dict[str, NodeLayout],
    resized_node_ids: set[str],
    state_types: dict[str, StateType],
) -> list[EdgeLayout]:
    """Re-route edge endpoints to match resized node boundaries.

    For each edge whose source or target was resized, move the first/last
    point to lie on the new node boundary.
    """
    adjusted_edges: list[EdgeLayout] = []
    for el in edges:
        points = list(el.points)

        # Re-route source endpoint (first point)
        if el.source in resized_node_ids and len(points) >= 2:
            nl = adjusted_nodes[el.source]
            st = state_types.get(el.source, StateType.NORMAL)
            ref = points[1]  # next waypoint after source
            match st:
                case StateType.START | StateType.END:
                    cx = nl.x + nl.width / 2
                    cy = nl.y + nl.height / 2
                    r = nl.width / 2
                    points[0] = _circle_boundary_point(cx, cy, r, ref.x, ref.y)
                case StateType.FORK | StateType.JOIN | StateType.CHOICE:
                    points[0] = _rect_boundary_point(nl, ref.x, ref.y)

        # Re-route target endpoint (last point)
        if el.target in resized_node_ids and len(points) >= 2:
            nl = adjusted_nodes[el.target]
            st = state_types.get(el.target, StateType.NORMAL)
            ref = points[-2]  # waypoint before target
            match st:
                case StateType.START | StateType.END:
                    cx = nl.x + nl.width / 2
                    cy = nl.y + nl.height / 2
                    r = nl.width / 2
                    points[-1] = _circle_boundary_point(cx, cy, r, ref.x, ref.y)
                case StateType.FORK | StateType.JOIN | StateType.CHOICE:
                    points[-1] = _rect_boundary_point(nl, ref.x, ref.y)

        adjusted_edges.append(EdgeLayout(
            points=points, source=el.source, target=el.target,
        ))
    return adjusted_edges


def layout_state_diagram(
    diagram: StateDiagram,
    measure_fn: MeasureFn,
    config: LayoutConfig | None = None,
) -> LayoutResult:
    """Lay out a state diagram using the Sugiyama algorithm.

    Converts the StateDiagram to a flowchart IR, runs layout, then
    adjusts sizes for pseudo-states (start/end circles, fork/join bars)
    and re-routes edge endpoints to the new boundaries.
    """
    flowchart = state_diagram_to_flowchart(diagram)

    # Build a custom measure function that returns fixed sizes for
    # pseudo-states
    state_types: dict[str, StateType] = {}
    for s in diagram.states:
        state_types[s.id] = s.state_type
        for child in s.children:
            state_types[child.id] = child.state_type

    original_measure = measure_fn

    def _state_measure(text: str, font_size: float) -> tuple[float, float]:
        return original_measure(text, font_size)

    if config is None:
        config = LayoutConfig(direction=Direction.TB)

    result = layout_diagram(flowchart, measure_fn=_state_measure, config=config)

    # Post-process: resize pseudo-state nodes to their natural sizes
    adjusted_nodes: dict[str, NodeLayout] = {}
    resized_node_ids: set[str] = set()

    for nid, nl in result.nodes.items():
        st = state_types.get(nid, StateType.NORMAL)
        match st:
            case StateType.START | StateType.END:
                # Shrink to a small circle centered on original position
                cx = nl.x + nl.width / 2
                cy = nl.y + nl.height / 2
                s = _START_END_SIZE
                adjusted_nodes[nid] = NodeLayout(
                    x=cx - s / 2, y=cy - s / 2,
                    width=s, height=s,
                )
                resized_node_ids.add(nid)
            case StateType.FORK | StateType.JOIN:
                cx = nl.x + nl.width / 2
                cy = nl.y + nl.height / 2
                adjusted_nodes[nid] = NodeLayout(
                    x=cx - _FORK_JOIN_WIDTH / 2,
                    y=cy - _FORK_JOIN_HEIGHT / 2,
                    width=_FORK_JOIN_WIDTH,
                    height=_FORK_JOIN_HEIGHT,
                )
                resized_node_ids.add(nid)
            case StateType.CHOICE:
                cx = nl.x + nl.width / 2
                cy = nl.y + nl.height / 2
                adjusted_nodes[nid] = NodeLayout(
                    x=cx - _CHOICE_SIZE / 2,
                    y=cy - _CHOICE_SIZE / 2,
                    width=_CHOICE_SIZE,
                    height=_CHOICE_SIZE,
                )
                resized_node_ids.add(nid)
            case _:
                adjusted_nodes[nid] = nl

    # Re-route edge endpoints to the resized node boundaries
    adjusted_edges = _reroute_edges(
        result.edges, adjusted_nodes, resized_node_ids, state_types,
    )

    return LayoutResult(
        nodes=adjusted_nodes,
        edges=adjusted_edges,
        width=result.width,
        height=result.height,
        subgraphs=result.subgraphs,
    )

__all__ = [
    "layout_state_diagram",
    "state_diagram_to_flowchart",
]
