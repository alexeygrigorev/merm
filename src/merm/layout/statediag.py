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

def state_diagram_to_flowchart(
    diagram: StateDiagram,
) -> tuple[Diagram, dict[str, str], dict[str, str]]:
    """Convert a StateDiagram into a flowchart Diagram for layout.

    States become Nodes, transitions become Edges, and composite
    states with children become Subgraphs.

    Edges to/from composite states are redirected to internal child
    nodes so the layout engine keeps everything connected within the
    subgraph region.

    Returns a tuple of (Diagram, composite_entry, composite_exit) where
    the maps are {composite_id: child_id} for edge redirection.
    """
    nodes: list[Node] = []
    edges: list[Edge] = []
    subgraphs: list[Subgraph] = []

    # Track composite states for edge redirection
    composite_ids: set[str] = set()
    # Maps composite id -> entry node id (for incoming edges)
    composite_entry: dict[str, str] = {}
    # Maps composite id -> exit node id (for outgoing edges)
    composite_exit: dict[str, str] = {}

    def _add_state(state: State) -> None:
        if state.children:
            composite_ids.add(state.id)
            child_ids: list[str] = []

            # Find an internal start/fork pseudo-state for entry
            entry_id: str | None = None
            for child in state.children:
                if child.state_type in (StateType.START, StateType.FORK):
                    entry_id = child.id
                    break
            if entry_id is None and state.children:
                entry_id = state.children[0].id

            if entry_id is not None:
                composite_entry[state.id] = entry_id

            # Find a suitable exit node: prefer JOIN/END, else last non-start child
            exit_id: str | None = None
            for child in reversed(state.children):
                if child.state_type in (StateType.JOIN, StateType.END):
                    exit_id = child.id
                    break
            if exit_id is None:
                for child in reversed(state.children):
                    if child.state_type not in (StateType.START, StateType.FORK):
                        exit_id = child.id
                        break
            if exit_id is None and state.children:
                exit_id = state.children[-1].id

            if exit_id is not None:
                composite_exit[state.id] = exit_id

            for child in state.children:
                _add_state(child)
                child_ids.append(child.id)

            subgraphs.append(Subgraph(
                id=state.id,
                title=state.label,
                node_ids=tuple(child_ids),
            ))
        else:
            shape = _state_to_node_shape(state.state_type)
            nodes.append(Node(
                id=state.id,
                label=state.label,
                shape=shape,
            ))

    for state in diagram.states:
        _add_state(state)

    # Redirect edges to/from composite states to internal children
    for trans in diagram.transitions:
        source = trans.source
        target = trans.target
        if target in composite_ids and target in composite_entry:
            target = composite_entry[target]
        if source in composite_ids and source in composite_exit:
            source = composite_exit[source]
        edges.append(Edge(
            source=source,
            target=target,
            label=trans.label or None,
        ))

    result = Diagram(
        type=DiagramType.state,
        direction=Direction.TB,
        nodes=tuple(nodes),
        edges=tuple(edges),
        subgraphs=tuple(subgraphs),
    )
    return result, composite_entry, composite_exit

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
    flowchart, composite_entry, composite_exit = state_diagram_to_flowchart(diagram)

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

    # Reroute edges that cross subgraph boundaries for composite states.
    # Edges redirected to internal children need their endpoints moved
    # to the subgraph boundary so arrows connect to the composite box.
    # composite_entry and composite_exit are from state_diagram_to_flowchart
    sg_layouts = result.subgraphs or {}

    if composite_entry or composite_exit:
        # Build reverse maps: child_id -> composite_id
        entry_to_composite = {v: k for k, v in composite_entry.items()}
        exit_to_composite = {v: k for k, v in composite_exit.items()}

        # Build set of all child IDs per composite for internal edge detection
        composite_children: dict[str, set[str]] = {}
        for s in diagram.states:
            if s.children:
                composite_children[s.id] = {c.id for c in s.children}

        rerouted_edges: list[EdgeLayout] = []
        for el in adjusted_edges:
            points = list(el.points)

            # If edge target was redirected into a composite (incoming edge),
            # clip the last point to the subgraph boundary -- but only if
            # the source is OUTSIDE the composite.
            if el.target in entry_to_composite:
                comp_id = entry_to_composite[el.target]
                children = composite_children.get(comp_id, set())
                if el.source not in children:
                    sgl = sg_layouts.get(comp_id)
                    if sgl and len(points) >= 2:
                        target_nl = NodeLayout(
                            x=sgl.x, y=sgl.y,
                            width=sgl.width, height=sgl.height,
                        )
                        ref = points[0]  # source point
                        bp = _rect_boundary_point(target_nl, ref.x, ref.y)
                        points[-1] = bp

            # If edge source was redirected from a composite (outgoing edge),
            # clip the first point to the subgraph boundary -- but only if
            # the target is OUTSIDE the composite.
            if el.source in exit_to_composite:
                comp_id = exit_to_composite[el.source]
                children = composite_children.get(comp_id, set())
                if el.target not in children:
                    sgl = sg_layouts.get(comp_id)
                    if sgl and len(points) >= 2:
                        source_nl = NodeLayout(
                            x=sgl.x, y=sgl.y,
                            width=sgl.width, height=sgl.height,
                        )
                        ref = points[-1]  # target point
                        bp = _rect_boundary_point(source_nl, ref.x, ref.y)
                        points[0] = bp

            rerouted_edges.append(EdgeLayout(
                points=points, source=el.source, target=el.target,
            ))
        adjusted_edges = rerouted_edges

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
