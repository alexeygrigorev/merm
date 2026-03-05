# 06 - Sugiyama Layout Algorithm

## Goal
Implement a layered graph layout algorithm (Sugiyama framework) for positioning flowchart nodes and routing edges. This is the core layout engine.

## Dependencies
- Task 03 (IR data model) -- `.done.md`
- Task 05 (text measurement) -- must be `.done.md` before implementation starts

## Scope

The layout engine receives a `Diagram` (from `pymermaid.ir`) and a text-measurement callable, and produces a `LayoutResult` containing positioned nodes, routed edges, and overall dimensions. All code lives in `src/pymermaid/layout/`.

Out of scope for this task:
- Subgraph-aware layout (covered by task 10)
- Bezier curve smoothing (nice-to-have, not required)
- Styling or rendering (tasks 07-11)

## Tasks

### Data Structures (`src/pymermaid/layout/__init__.py` or sub-modules)

- [ ] `Point` dataclass: `x: float`, `y: float`
- [ ] `NodeLayout` dataclass: `x: float`, `y: float`, `width: float`, `height: float`
- [ ] `EdgeLayout` dataclass: `points: list[Point]`, `source: str`, `target: str`
- [ ] `LayoutResult` dataclass: `nodes: dict[str, NodeLayout]`, `edges: list[EdgeLayout]`, `width: float`, `height: float`
- [ ] `LayoutConfig` dataclass with configurable spacing:
  - `rank_sep: float = 50.0` (distance between layers)
  - `node_sep: float = 30.0` (distance between nodes in same layer)
  - `direction: Direction = Direction.TB` (overridable; defaults to diagram's direction)

### Preprocessing
- [ ] Build adjacency lists from IR edges
- [ ] Handle direction (TB/BT/LR/RL) by transforming coordinates at the end
- [ ] Merge multi-edges between same node pairs into a single layout edge

### Step 1: Cycle Removal
- [ ] Detect cycles using DFS
- [ ] Break cycles by reversing selected edges (greedy heuristic)
- [ ] Track reversed edges so rendering can restore correct arrow direction

### Step 2: Layer Assignment (Ranking)
- [ ] Implement longest-path layering
- [ ] Assign each node an integer rank (layer)
- [ ] Insert virtual/dummy nodes for edges that span multiple layers

### Step 3: Crossing Minimization
- [ ] Implement barycenter heuristic for ordering nodes within layers
- [ ] Run multiple sweep passes (at least 4 up-down sweeps)

### Step 4: Coordinate Assignment
- [ ] Assign x, y coordinates based on layer and order within layer
- [ ] Account for node dimensions (width/height from text measurement)
- [ ] Apply `rank_sep` and `node_sep` spacing
- [ ] Center nodes within their layer

### Step 5: Edge Routing
- [ ] Straight-line routing for edges between adjacent layers
- [ ] Polyline routing through dummy nodes for multi-layer edges
- [ ] Calculate edge endpoints on node boundaries (not node centers)
- [ ] Handle self-loops (edge from a node to itself)

### Public API
- [ ] `layout_diagram(diagram: Diagram, measure_fn, config: LayoutConfig | None = None) -> LayoutResult`
  - `measure_fn` signature: `(text: str, font_size: float) -> tuple[float, float]` returning `(width, height)`
  - If `config` is `None`, use defaults with direction from `diagram.direction`

### Direction Transform
- [ ] TB: layers top-to-bottom (rank axis = y, order axis = x) -- default
- [ ] LR: layers left-to-right (rank axis = x, order axis = y) -- swap axes
- [ ] BT: like TB but reverse the rank axis
- [ ] RL: like LR but reverse the rank axis

## Acceptance Criteria

- [ ] `from pymermaid.layout import layout_diagram, LayoutResult, LayoutConfig, NodeLayout, EdgeLayout, Point` works
- [ ] `Point` has fields `x: float` and `y: float`
- [ ] `NodeLayout` has fields `x`, `y`, `width`, `height` (all floats)
- [ ] `EdgeLayout` has fields `points: list[Point]`, `source: str`, `target: str`
- [ ] `LayoutResult` has fields `nodes: dict[str, NodeLayout]`, `edges: list[EdgeLayout]`, `width: float`, `height: float`
- [ ] `LayoutConfig` has fields `rank_sep`, `node_sep`, `direction` with correct defaults (50.0, 30.0, Direction.TB)
- [ ] `layout_diagram` accepts a `Diagram`, a measure function, and an optional `LayoutConfig`, and returns a `LayoutResult`
- [ ] For a simple `A --> B` diagram (2 nodes, 1 edge): result has 2 entries in `nodes`, 1 entry in `edges`, and positive `width`/`height`
- [ ] For `A --> B`, node A is above node B when direction is TB (A.y < B.y)
- [ ] For `A --> B`, node A is to the left of node B when direction is LR (A.x < B.x)
- [ ] For a linear chain `A --> B --> C`, all three nodes are in different layers and the edge from A to C (if present) routes through a dummy node producing a polyline with more than 2 points
- [ ] For a diamond graph `A --> B, A --> C, B --> D, C --> D`, all four nodes have positions and no two nodes overlap (bounding boxes do not intersect)
- [ ] Cyclic graph `A --> B --> C --> A` does not raise an exception; all three nodes are positioned
- [ ] Disconnected graph (nodes with no edges between components) does not raise; all nodes are positioned
- [ ] Self-loop `A --> A` does not raise; edge has at least 2 points
- [ ] Node dimensions from `measure_fn` are reflected in `NodeLayout.width` and `NodeLayout.height`
- [ ] Changing `rank_sep` changes the distance between layers (larger value = more spacing on the rank axis)
- [ ] Changing `node_sep` changes the distance between nodes in the same layer
- [ ] BT direction reverses the rank-axis ordering compared to TB
- [ ] RL direction reverses the rank-axis ordering compared to LR
- [ ] `uv run pytest tests/test_layout.py` passes with all tests green
- [ ] Performance: layout of a 100-node chain completes in under 1 second (generous bound)

## Test Scenarios

### Unit: Data structures
- Create `Point(1.0, 2.0)` and verify `x`, `y`
- Create `NodeLayout` with all fields, verify attributes
- Create `EdgeLayout` with a list of `Point`s, verify `points`, `source`, `target`
- Create `LayoutResult` and verify `nodes`, `edges`, `width`, `height`
- Create `LayoutConfig()` with defaults, verify `rank_sep=50.0`, `node_sep=30.0`, `direction=Direction.TB`
- Create `LayoutConfig(rank_sep=100, node_sep=50, direction=Direction.LR)` and verify overrides

### Unit: Cycle removal
- Acyclic graph `A->B->C` has no cycles, edges unchanged
- Cyclic graph `A->B->C->A` detects and breaks the cycle (at least one edge reversed)
- Self-loop `A->A` is handled without error

### Unit: Layer assignment
- Linear chain `A->B->C` assigns layers 0, 1, 2 (or equivalent increasing sequence)
- Diamond `A->B, A->C, B->D, C->D` assigns A to layer 0, B and C to layer 1, D to layer 2
- Edge spanning 2+ layers inserts at least one dummy node

### Unit: Crossing minimization
- Simple two-layer graph with no crossings preserves order
- Graph with obvious crossing (A->D, B->C where A,B in layer 0 and C,D in layer 1) reorders to reduce crossings

### Unit: Coordinate assignment
- Two nodes in different layers are separated by at least `rank_sep` on the rank axis
- Two nodes in the same layer are separated by at least `node_sep` on the order axis
- Node dimensions affect the spacing (wider nodes push neighbors further apart)

### Unit: Edge routing
- Adjacent-layer edge produces a path with exactly 2 points (start and end)
- Multi-layer edge (through dummy nodes) produces a path with 3+ points
- Self-loop produces a valid path with at least 2 points
- Edge endpoints are on node boundaries, not at node centers

### Integration: layout_diagram end-to-end
- Simple `A --> B` diagram with TB direction: A above B, edge connects them
- Same diagram with LR direction: A left of B
- Same diagram with BT direction: A below B
- Same diagram with RL direction: A right of B
- Chain of 5 nodes: all positioned in order, no overlaps
- Diamond shape: 4 nodes positioned, 4 edges routed, no overlaps
- Cyclic graph: completes without error, all nodes positioned
- Disconnected components: 2 separate pairs, all 4 nodes positioned
- 100-node chain: completes in under 1 second

### Integration: measure function interaction
- Provide a measure function that returns large dimensions; verify node layouts reflect those sizes
- Provide a measure function that returns small dimensions; verify tighter layout

## Estimated Complexity
Large -- this is algorithmically the hardest task. Approximately 600-1000 lines. The Sugiyama algorithm is well-documented with many reference implementations available.
