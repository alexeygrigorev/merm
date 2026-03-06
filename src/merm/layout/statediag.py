"""State diagram layout: convert StateDiagram to flowchart IR for Sugiyama layout.

This module bridges the state diagram IR to the flowchart-based layout engine,
mapping states to nodes and transitions to edges. Composite states become
subgraphs.
"""

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
from merm.layout.types import LayoutResult

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

def layout_state_diagram(
    diagram: StateDiagram,
    measure_fn: MeasureFn,
    config: LayoutConfig | None = None,
) -> LayoutResult:
    """Lay out a state diagram using the Sugiyama algorithm.

    Converts the StateDiagram to a flowchart IR, runs layout, then
    adjusts sizes for pseudo-states (start/end circles, fork/join bars).
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
    from merm.layout.types import NodeLayout

    adjusted_nodes: dict[str, NodeLayout] = {}
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
            case StateType.FORK | StateType.JOIN:
                cx = nl.x + nl.width / 2
                cy = nl.y + nl.height / 2
                adjusted_nodes[nid] = NodeLayout(
                    x=cx - _FORK_JOIN_WIDTH / 2,
                    y=cy - _FORK_JOIN_HEIGHT / 2,
                    width=_FORK_JOIN_WIDTH,
                    height=_FORK_JOIN_HEIGHT,
                )
            case StateType.CHOICE:
                cx = nl.x + nl.width / 2
                cy = nl.y + nl.height / 2
                adjusted_nodes[nid] = NodeLayout(
                    x=cx - _CHOICE_SIZE / 2,
                    y=cy - _CHOICE_SIZE / 2,
                    width=_CHOICE_SIZE,
                    height=_CHOICE_SIZE,
                )
            case _:
                adjusted_nodes[nid] = nl

    return LayoutResult(
        nodes=adjusted_nodes,
        edges=result.edges,
        width=result.width,
        height=result.height,
        subgraphs=result.subgraphs,
    )

__all__ = [
    "layout_state_diagram",
    "state_diagram_to_flowchart",
]
