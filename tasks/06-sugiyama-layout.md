# 06 - Sugiyama Layout Algorithm

## Goal
Implement a layered graph layout algorithm (Sugiyama framework) for positioning flowchart nodes and routing edges. This is the core layout engine.

## Tasks

### Preprocessing
- [ ] Build adjacency lists from IR edges
- [ ] Handle direction (TB/BT/LR/RL) by transforming coordinates at the end
- [ ] Merge multi-edges between same node pairs

### Step 1: Cycle Removal
- [ ] Detect cycles using DFS
- [ ] Break cycles by reversing selected edges (greedy heuristic)
- [ ] Track reversed edges to restore arrow direction in rendering

### Step 2: Layer Assignment (Ranking)
- [ ] Implement longest-path layering (simple, good results)
- [ ] Assign each node to a layer (integer rank)
- [ ] Handle edges spanning multiple layers by inserting virtual/dummy nodes
- [ ] Respect subgraph containment (nodes in same subgraph should be nearby)

### Step 3: Crossing Minimization
- [ ] Implement barycenter heuristic for node ordering within layers
- [ ] Multiple passes (typically 4-8 sweeps up and down)
- [ ] Handle fixed-position nodes (subgraph boundaries)

### Step 4: Coordinate Assignment
- [ ] Assign x,y coordinates to each node
  - Layer determines one axis (rank axis)
  - Order within layer determines the other axis
- [ ] Configurable spacing:
  - `rank_sep`: distance between layers (default: 50px)
  - `node_sep`: distance between nodes in same layer (default: 30px)
- [ ] Center nodes within their layer
- [ ] Account for node dimensions (from text measurement)

### Step 5: Edge Routing
- [ ] Straight-line routing for edges within adjacent layers
- [ ] Polyline routing through dummy nodes for multi-layer edges
- [ ] Calculate edge start/end points on node boundaries (not centers)
- [ ] Bezier curve smoothing for polyline edges (optional, nice-to-have)
- [ ] Handle self-loops

### Subgraph Layout
- [ ] Layout nodes within subgraphs first
- [ ] Calculate subgraph bounding boxes
- [ ] Position subgraphs within parent layout
- [ ] Add padding around subgraph contents

### Output
- [ ] `LayoutResult` dataclass containing:
  - Node positions and dimensions: `dict[str, NodeLayout]`
  - Edge paths: `dict[edge_id, list[Point]]`
  - Subgraph bounding boxes: `dict[str, BBox]`
  - Overall diagram dimensions: `(width, height)`

## Acceptance Criteria
- Correctly layouts acyclic graphs (no edge crossings for simple cases)
- Handles cycles without crashing
- Handles disconnected components
- Reasonable performance: layout 100 nodes in < 100ms
- Visual output matches mermaid-cli roughly (same general structure)

## Dependencies
- Task 03 (IR data model)
- Task 05 (text measurement for node sizing)

## Estimated Complexity
Large - this is algorithmically the hardest task. ~600-1000 lines. Well-documented algorithm though (many reference implementations exist).
