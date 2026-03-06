# 03 - Intermediate Representation (IR) Data Model

## Goal
Define the core data structures that represent a parsed Mermaid diagram. All other modules operate on these types.

## Dependencies
- `01-project-setup.done.md` -- package structure and tooling must exist
- `02-comparison-test-infra.done.md` -- test infrastructure must be in place

## Tasks

- [ ] Define all enums in `src/pymermaid/ir/__init__.py`:
  - `DiagramType` -- flowchart, sequence, class_diagram, state, er, gantt, pie, mindmap, git_graph
  - `Direction` -- TB, TD, BT, LR, RL
  - `NodeShape` -- rect, rounded, stadium, subroutine, cylinder, circle, asymmetric, diamond, hexagon, parallelogram, parallelogram_alt, trapezoid, trapezoid_alt, double_circle
  - `EdgeType` -- arrow, open, dotted, dotted_arrow, thick, thick_arrow, invisible
  - `ArrowType` -- none, arrow, circle, cross
- [ ] Define `Node` dataclass (frozen)
  - `id`: str
  - `label`: str (may contain markdown/HTML)
  - `shape`: NodeShape (default: `NodeShape.rect`)
  - `css_classes`: tuple[str, ...] (default: empty tuple; use tuple for immutability)
  - `inline_style`: dict[str, str] | None (default: None)
- [ ] Define `Edge` dataclass (frozen)
  - `source`: str (node id)
  - `target`: str (node id)
  - `label`: str | None (default: None)
  - `edge_type`: EdgeType (default: `EdgeType.arrow`)
  - `source_arrow`: ArrowType (default: `ArrowType.none`)
  - `target_arrow`: ArrowType (default: `ArrowType.arrow`)
  - `extra_length`: int (default: 0, number of extra dashes)
- [ ] Define `StyleDef` dataclass (frozen)
  - `target_id`: str (node id or "default")
  - `properties`: dict[str, str]
- [ ] Define `Subgraph` dataclass (frozen)
  - `id`: str
  - `title`: str | None (default: None)
  - `direction`: Direction | None (default: None, override)
  - `node_ids`: tuple[str, ...] (default: empty tuple)
  - `subgraphs`: tuple[Subgraph, ...] (default: empty tuple; self-referencing for nesting)
- [ ] Define `Diagram` dataclass (frozen)
  - `type`: DiagramType (default: `DiagramType.flowchart`)
  - `direction`: Direction (default: `Direction.TB`)
  - `nodes`: tuple[Node, ...] (default: empty tuple)
  - `edges`: tuple[Edge, ...] (default: empty tuple)
  - `subgraphs`: tuple[Subgraph, ...] (default: empty tuple)
  - `styles`: tuple[StyleDef, ...] (default: empty tuple)
  - `classes`: dict[str, dict[str, str]] (default: empty dict; maps class names to style properties)
- [ ] Ensure all types are re-exported from `pymermaid.ir`
- [ ] Write tests in `tests/test_ir.py`

## Acceptance Criteria

- [ ] `from pymermaid.ir import DiagramType, Direction, NodeShape, EdgeType, ArrowType` works
- [ ] `from pymermaid.ir import Node, Edge, Subgraph, StyleDef, Diagram` works
- [ ] All enum classes have the exact members listed above (e.g., `len(NodeShape) == 14`)
- [ ] All dataclasses are frozen (assigning to a field raises `FrozenInstanceError`)
- [ ] `Node("A", "Label A")` creates a node with default shape `NodeShape.rect` and empty css_classes
- [ ] `Edge("A", "B")` creates an edge with default edge_type `EdgeType.arrow` and target_arrow `ArrowType.arrow`
- [ ] `Subgraph` supports self-referencing nesting: `Subgraph("outer", subgraphs=(Subgraph("inner"),))`
- [ ] `Diagram()` creates a valid empty diagram with sensible defaults (type=flowchart, direction=TB)
- [ ] `Diagram(nodes=(Node("A", "Hello"),), edges=(Edge("A", "B"),))` constructs without error
- [ ] `uv run pytest tests/test_ir.py` passes with all tests green
- [ ] `uv run ruff check src/pymermaid/ir/` passes with no errors

## Test Scenarios

### Unit: Enum completeness
- `DiagramType` has at least 9 members (flowchart, sequence, class_diagram, state, er, gantt, pie, mindmap, git_graph)
- `Direction` has exactly 5 members (TB, TD, BT, LR, RL)
- `NodeShape` has exactly 14 members matching the plan's shape list
- `EdgeType` has exactly 7 members
- `ArrowType` has exactly 4 members
- Each enum member is accessible by name: e.g., `NodeShape.diamond`, `EdgeType.dotted_arrow`

### Unit: Node construction
- Create a Node with all fields explicitly, verify each attribute
- Create a Node with only required fields (id, label), verify defaults (shape=rect, css_classes=(), inline_style=None)
- Verify Node is frozen: assigning `node.label = "X"` raises `FrozenInstanceError`

### Unit: Edge construction
- Create an Edge with all fields, verify each attribute
- Create an Edge with only source and target, verify defaults (edge_type=arrow, label=None, extra_length=0)
- Verify Edge is frozen
- Create an Edge with extra_length > 0 to represent long arrows

### Unit: Subgraph construction
- Create a flat Subgraph with node_ids
- Create nested Subgraphs (subgraph containing subgraphs)
- Create a Subgraph with direction override
- Verify Subgraph is frozen

### Unit: StyleDef construction
- Create a StyleDef with target_id and properties dict
- Verify StyleDef is frozen

### Unit: Diagram construction
- Create an empty Diagram(), verify all defaults
- Create a Diagram with nodes, edges, subgraphs, styles, and classes populated
- Verify Diagram is frozen
- Verify the Diagram's direction can be set to each Direction enum value

### Unit: Equality and hashing
- Two Nodes with identical fields are equal
- Two Edges with identical fields are equal
- Frozen dataclasses are hashable (can be added to a set)

## Estimated Complexity
Small -- pure data definitions, no logic beyond construction and validation.
