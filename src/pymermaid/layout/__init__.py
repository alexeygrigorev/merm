"""Graph layout algorithms -- Sugiyama layered layout."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from pymermaid.ir import Diagram, Direction, Subgraph


@dataclass(frozen=True)
class Point:
    """A 2D point."""

    x: float
    y: float


@dataclass(frozen=True)
class NodeLayout:
    """Positioned node with dimensions."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class EdgeLayout:
    """Routed edge as a polyline."""

    points: list[Point]
    source: str
    target: str


@dataclass(frozen=True)
class SubgraphLayout:
    """Bounding box for a laid-out subgraph."""

    id: str
    x: float
    y: float
    width: float
    height: float
    title: str | None = None


@dataclass(frozen=True)
class LayoutResult:
    """Complete layout output."""

    nodes: dict[str, NodeLayout]
    edges: list[EdgeLayout]
    width: float
    height: float
    subgraphs: dict[str, SubgraphLayout] | None = None


@dataclass
class LayoutConfig:
    """Configuration for the layout engine."""

    rank_sep: float = 50.0
    node_sep: float = 30.0
    direction: Direction = Direction.TB


# Type alias for the measure function
MeasureFn = Callable[[str, float], tuple[float, float]]

# Default font size used when calling measure_fn
_DEFAULT_FONT_SIZE = 14.0

# Padding added around measured text to get node dimensions
_NODE_PADDING_H = 16.0
_NODE_PADDING_V = 12.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_adjacency(
    node_ids: list[str],
    edges: list[tuple[str, str, int]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Build forward and reverse adjacency lists.

    *edges* is a list of (source, target, original_index).
    Returns (successors, predecessors) dicts.
    """
    succ: dict[str, list[str]] = defaultdict(list)
    pred: dict[str, list[str]] = defaultdict(list)
    for s, t, _ in edges:
        succ[s].append(t)
        pred[t].append(s)
    # Ensure every node appears
    for n in node_ids:
        succ.setdefault(n, [])
        pred.setdefault(n, [])
    return dict(succ), dict(pred)


# ---------------------------------------------------------------------------
# Step 0: Preprocessing -- merge multi-edges, separate self-loops
# ---------------------------------------------------------------------------

def _preprocess_edges(
    ir_edges: list[tuple[str, str]],
) -> tuple[list[tuple[str, str, int]], list[tuple[str, str, int]]]:
    """Split edges into normal (deduplicated) and self-loop lists.

    Each entry is (source, target, original_index).
    Multi-edges between the same pair are merged to a single layout edge
    (we keep the first occurrence).
    """
    seen: set[tuple[str, str]] = set()
    normal: list[tuple[str, str, int]] = []
    self_loops: list[tuple[str, str, int]] = []
    for idx, (s, t) in enumerate(ir_edges):
        if s == t:
            self_loops.append((s, t, idx))
            continue
        key = (s, t)
        if key not in seen:
            seen.add(key)
            normal.append((s, t, idx))
    return normal, self_loops


# ---------------------------------------------------------------------------
# Step 1: Cycle removal via DFS
# ---------------------------------------------------------------------------

def _remove_cycles(
    node_ids: list[str],
    edges: list[tuple[str, str, int]],
) -> tuple[list[tuple[str, str, int]], set[int]]:
    """Remove cycles by reversing back-edges found during DFS.

    Returns (acyclic_edges, reversed_original_indices).
    """
    succ: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for s, t, idx in edges:
        succ[s].append((t, idx))

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in node_ids}
    reversed_indices: set[int] = set()

    def dfs(u: str) -> None:
        color[u] = GRAY
        for v, idx in succ.get(u, []):
            if color.get(v, WHITE) == GRAY:
                # Back edge -- mark for reversal
                reversed_indices.add(idx)
            elif color.get(v, WHITE) == WHITE:
                dfs(v)
        color[u] = BLACK

    for n in node_ids:
        if color[n] == WHITE:
            dfs(n)

    result: list[tuple[str, str, int]] = []
    for s, t, idx in edges:
        if idx in reversed_indices:
            result.append((t, s, idx))
        else:
            result.append((s, t, idx))
    return result, reversed_indices


# ---------------------------------------------------------------------------
# Step 2: Layer assignment -- longest path
# ---------------------------------------------------------------------------

def _longest_path_layering(
    node_ids: list[str],
    edges: list[tuple[str, str, int]],
) -> dict[str, int]:
    """Assign layers using longest-path algorithm.

    Sources (no predecessors) get layer 0; each other node gets
    max(predecessor layers) + 1.
    """
    succ: dict[str, list[str]] = defaultdict(list)
    pred: dict[str, list[str]] = defaultdict(list)
    for s, t, _ in edges:
        succ[s].append(t)
        pred[t].append(s)

    layer: dict[str, int] = {}

    def assign(n: str) -> int:
        if n in layer:
            return layer[n]
        preds = pred.get(n, [])
        if not preds:
            layer[n] = 0
        else:
            layer[n] = -1  # sentinel to detect recursion in degenerate cases
            layer[n] = max(assign(p) for p in preds) + 1
        return layer[n]

    for n in node_ids:
        if n not in layer:
            assign(n)

    # Handle isolated nodes (no edges) -- put them at layer 0
    for n in node_ids:
        if n not in layer:
            layer[n] = 0

    return layer


# ---------------------------------------------------------------------------
# Step 2b: Insert dummy nodes for long edges
# ---------------------------------------------------------------------------

def _insert_dummy_nodes(
    layers: dict[str, int],
    edges: list[tuple[str, str, int]],
) -> tuple[dict[str, int], list[tuple[str, str, int]], dict[str, tuple[str, str, int]]]:
    """Insert dummy nodes for edges spanning more than one layer.

    Returns (updated_layers, new_edges, dummy_info).
    dummy_info maps dummy_node_id -> original (source, target, idx).
    """
    new_layers = dict(layers)
    new_edges: list[tuple[str, str, int]] = []
    dummy_info: dict[str, tuple[str, str, int]] = {}
    dummy_counter = 0

    for s, t, idx in edges:
        ls = new_layers[s]
        lt = new_layers[t]
        span = lt - ls
        if span <= 1:
            new_edges.append((s, t, idx))
        else:
            # Create chain of dummy nodes
            prev = s
            for i in range(1, span):
                dummy_id = f"__dummy_{dummy_counter}"
                dummy_counter += 1
                new_layers[dummy_id] = ls + i
                dummy_info[dummy_id] = (s, t, idx)
                new_edges.append((prev, dummy_id, idx))
                prev = dummy_id
            new_edges.append((prev, t, idx))

    return new_layers, new_edges, dummy_info


# ---------------------------------------------------------------------------
# Step 3: Crossing minimization -- barycenter heuristic
# ---------------------------------------------------------------------------

def _build_layer_lists(
    layers: dict[str, int],
) -> list[list[str]]:
    """Build ordered lists of nodes per layer."""
    max_layer = max(layers.values()) if layers else 0
    result: list[list[str]] = [[] for _ in range(max_layer + 1)]
    for node, layer in layers.items():
        result[layer].append(node)
    return result


def _crossing_minimization(
    layer_lists: list[list[str]],
    edges: list[tuple[str, str, int]],
    layers: dict[str, int],
    num_sweeps: int = 4,
) -> list[list[str]]:
    """Barycenter heuristic: sweep up and down to minimize crossings."""
    if len(layer_lists) <= 1:
        return layer_lists

    # Build adjacency by layer for fast lookup
    # For each edge, record the positions
    down_adj: dict[str, list[str]] = defaultdict(list)  # node -> children in next layer
    up_adj: dict[str, list[str]] = defaultdict(list)  # node -> parents in prev layer

    for s, t, _ in edges:
        down_adj[s].append(t)
        up_adj[t].append(s)

    for _ in range(num_sweeps):
        # Sweep down
        for li in range(1, len(layer_lists)):
            fixed = layer_lists[li - 1]
            free = layer_lists[li]
            pos = {n: i for i, n in enumerate(fixed)}
            bary: dict[str, float] = {}
            for node in free:
                parents = up_adj.get(node, [])
                positions = [pos[p] for p in parents if p in pos]
                if positions:
                    bary[node] = sum(positions) / len(positions)
                else:
                    # Keep original position
                    bary[node] = free.index(node)
            layer_lists[li] = sorted(free, key=lambda n: bary[n])

        # Sweep up
        for li in range(len(layer_lists) - 2, -1, -1):
            fixed = layer_lists[li + 1]
            free = layer_lists[li]
            pos = {n: i for i, n in enumerate(fixed)}
            bary: dict[str, float] = {}
            for node in free:
                children = down_adj.get(node, [])
                positions = [pos[c] for c in children if c in pos]
                if positions:
                    bary[node] = sum(positions) / len(positions)
                else:
                    bary[node] = free.index(node)
            layer_lists[li] = sorted(free, key=lambda n: bary[n])

    return layer_lists


# ---------------------------------------------------------------------------
# Step 4: Coordinate assignment
# ---------------------------------------------------------------------------

def _assign_coordinates(
    layer_lists: list[list[str]],
    node_sizes: dict[str, tuple[float, float]],
    rank_sep: float,
    node_sep: float,
) -> dict[str, tuple[float, float]]:
    """Assign (x, y) coordinates for TB direction.

    Layers go top-to-bottom (y axis), nodes within a layer go left-to-right (x axis).
    Returns dict of node_id -> (center_x, center_y).
    """
    positions: dict[str, tuple[float, float]] = {}

    # Compute the width of each layer (sum of node widths + separators)
    layer_widths: list[float] = []
    for layer_nodes in layer_lists:
        if not layer_nodes:
            layer_widths.append(0.0)
            continue
        total = sum(node_sizes.get(n, (40.0, 30.0))[0] for n in layer_nodes)
        total += node_sep * (len(layer_nodes) - 1)
        layer_widths.append(total)

    max_width = max(layer_widths) if layer_widths else 0.0

    y = 0.0
    for li, layer_nodes in enumerate(layer_lists):
        if not layer_nodes:
            y += rank_sep
            continue

        # Compute max height in this layer
        max_h = max(node_sizes.get(n, (40.0, 30.0))[1] for n in layer_nodes)

        # Center this layer horizontally
        lw = layer_widths[li]
        x_start = (max_width - lw) / 2.0

        x = x_start
        for node in layer_nodes:
            w, h = node_sizes.get(node, (40.0, 30.0))
            cx = x + w / 2.0
            cy = y + max_h / 2.0
            positions[node] = (cx, cy)
            x += w + node_sep

        y += max_h + rank_sep

    return positions


# ---------------------------------------------------------------------------
# Step 5: Edge routing
# ---------------------------------------------------------------------------

def _route_edge_on_boundary(
    src_pos: tuple[float, float],
    src_size: tuple[float, float],
    tgt_pos: tuple[float, float],
    tgt_size: tuple[float, float],
) -> tuple[Point, Point]:
    """Compute edge endpoints on the node boundaries (rectangular approximation).

    Positions are centers; sizes are (width, height).
    """
    sx, sy = src_pos
    sw, sh = src_size
    tx, ty = tgt_pos
    tw, th = tgt_size

    # Direction from source center to target center
    dx = tx - sx
    dy = ty - sy

    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        # Same position -- just use center
        return Point(sx, sy + sh / 2), Point(tx, ty - th / 2)

    # Source exit point
    src_point = _boundary_point(sx, sy, sw, sh, dx, dy)
    # Target entry point (reverse direction)
    tgt_point = _boundary_point(tx, ty, tw, th, -dx, -dy)

    return src_point, tgt_point


def _boundary_point(
    cx: float, cy: float, w: float, h: float, dx: float, dy: float,
) -> Point:
    """Find ray-rectangle intersection point."""
    hw, hh = w / 2.0, h / 2.0

    if abs(dx) < 1e-9:
        # Vertical
        return Point(cx, cy + hh * (1 if dy > 0 else -1))
    if abs(dy) < 1e-9:
        # Horizontal
        return Point(cx + hw * (1 if dx > 0 else -1), cy)

    # Time to hit vertical edge
    tx_time = hw / abs(dx)
    # Time to hit horizontal edge
    ty_time = hh / abs(dy)

    t = min(tx_time, ty_time)
    return Point(cx + dx * t, cy + dy * t)


def _route_edges(
    original_edges: list[tuple[str, str, int]],
    acyclic_edges_with_dummies: list[tuple[str, str, int]],
    dummy_info: dict[str, tuple[str, str, int]],
    reversed_indices: set[int],
    positions: dict[str, tuple[float, float]],
    node_sizes: dict[str, tuple[float, float]],
    self_loops: list[tuple[str, str, int]],
    ir_edges: list[tuple[str, str]],
) -> list[EdgeLayout]:
    """Route all edges, collecting polylines through dummy nodes."""
    # Group dummy edges by original edge index to reconstruct paths
    # For each original edge, collect the chain of nodes (source -> dummies -> target)
    edge_chains: dict[int, list[str]] = {}

    # Build adjacency from the dummy-augmented edge list
    succ_by_idx: dict[int, dict[str, str]] = defaultdict(dict)
    for s, t, idx in acyclic_edges_with_dummies:
        succ_by_idx[idx][s] = t

    # For each original edge index that has dummies, trace the chain
    seen_indices: set[int] = set()
    for s, t, idx in acyclic_edges_with_dummies:
        if idx in seen_indices:
            continue
        seen_indices.add(idx)

        # Find the real source and target of this original edge
        orig_s, orig_t = ir_edges[idx]
        if idx in reversed_indices:
            # In the acyclic graph, the edge was reversed
            chain_start = orig_t
            chain_end = orig_s
        else:
            chain_start = orig_s
            chain_end = orig_t

        # Trace the chain
        chain = [chain_start]
        current = chain_start
        adj = succ_by_idx[idx]
        visited = {chain_start}
        while current != chain_end and current in adj:
            nxt = adj[current]
            if nxt in visited:
                break
            chain.append(nxt)
            visited.add(nxt)
            current = nxt
        if chain[-1] != chain_end:
            chain.append(chain_end)

        edge_chains[idx] = chain

    results: list[EdgeLayout] = []

    # Route normal edges
    processed: set[int] = set()
    for idx, chain in edge_chains.items():
        if idx in processed:
            continue
        processed.add(idx)

        orig_s, orig_t = ir_edges[idx]

        # Build polyline through the chain
        points: list[Point] = []
        for i in range(len(chain)):
            node = chain[i]
            if node not in positions:
                continue
            pos = positions[node]
            size = node_sizes.get(node, (40.0, 30.0))

            if i == 0 and i < len(chain) - 1:
                # Source node -- compute exit point
                next_node = chain[i + 1]
                if next_node in positions:
                    next_pos = positions[next_node]
                    next_size = node_sizes.get(next_node, (40.0, 30.0))
                    src_pt, _ = _route_edge_on_boundary(pos, size, next_pos, next_size)
                    points.append(src_pt)
                else:
                    points.append(Point(pos[0], pos[1]))
            elif i == len(chain) - 1 and i > 0:
                # Target node -- compute entry point
                prev_node = chain[i - 1]
                if prev_node in positions:
                    prev_pos = positions[prev_node]
                    prev_size = node_sizes.get(prev_node, (40.0, 30.0))
                    _, tgt_pt = _route_edge_on_boundary(prev_pos, prev_size, pos, size)
                    points.append(tgt_pt)
                else:
                    points.append(Point(pos[0], pos[1]))
            elif i == 0 and len(chain) == 1:
                # Single-node chain (shouldn't happen for normal edges)
                points.append(Point(pos[0], pos[1]))
            else:
                # Dummy node -- use center
                points.append(Point(pos[0], pos[1]))

        if len(points) < 2:
            # Fallback: straight line between source and target
            sp = positions.get(orig_s, (0.0, 0.0))
            tp = positions.get(orig_t, (0.0, 0.0))
            points = [Point(sp[0], sp[1]), Point(tp[0], tp[1])]

        if idx in reversed_indices:
            # The edge was reversed for acyclicity; reverse the points back
            points = list(reversed(points))

        results.append(EdgeLayout(points=points, source=orig_s, target=orig_t))

    # Route self-loops
    for s, t, idx in self_loops:
        pos = positions.get(s, (0.0, 0.0))
        size = node_sizes.get(s, (40.0, 30.0))
        w, h = size
        cx, cy = pos
        # Create a small loop to the right and back
        p1 = Point(cx + w / 2, cy)
        p2 = Point(cx + w / 2 + 20, cy - h / 2 - 15)
        p3 = Point(cx, cy - h / 2)
        results.append(EdgeLayout(points=[p1, p2, p3], source=s, target=t))

    return results


# ---------------------------------------------------------------------------
# Step 6: Direction transform
# ---------------------------------------------------------------------------

def _apply_direction(
    positions: dict[str, tuple[float, float]],
    node_sizes: dict[str, tuple[float, float]],
    direction: Direction,
) -> tuple[dict[str, tuple[float, float]], dict[str, tuple[float, float]]]:
    """Transform coordinates from TB to the requested direction.

    TB: default (rank=y, order=x)
    BT: flip y
    LR: swap x and y
    RL: swap x and y, then flip x
    """
    if direction in (Direction.TB, Direction.TD):
        return positions, node_sizes

    new_positions: dict[str, tuple[float, float]] = {}
    new_sizes: dict[str, tuple[float, float]] = {}

    if direction == Direction.BT:
        # Flip y axis
        if positions:
            max_y = max(pos[1] for pos in positions.values())
        else:
            max_y = 0.0
        for n, (x, y) in positions.items():
            new_positions[n] = (x, max_y - y)
        new_sizes = dict(node_sizes)

    elif direction == Direction.LR:
        # Swap x and y axes
        for n, (x, y) in positions.items():
            new_positions[n] = (y, x)
        for n, (w, h) in node_sizes.items():
            new_sizes[n] = (h, w)

    elif direction == Direction.RL:
        # Swap x and y, then flip x
        for n, (x, y) in positions.items():
            new_positions[n] = (y, x)
        for n, (w, h) in node_sizes.items():
            new_sizes[n] = (h, w)
        if new_positions:
            max_x = max(pos[0] for pos in new_positions.values())
            new_positions = {n: (max_x - x, y) for n, (x, y) in new_positions.items()}

    return new_positions, new_sizes


def _transform_point(
    p: Point, direction: Direction, max_y: float, max_x: float,
) -> Point:
    """Transform a single point from TB coordinates to target direction."""
    if direction in (Direction.TB, Direction.TD):
        return p
    if direction == Direction.BT:
        return Point(p.x, max_y - p.y)
    if direction == Direction.LR:
        return Point(p.y, p.x)
    if direction == Direction.RL:
        return Point(max_x - p.y, p.x)
    return p


# ---------------------------------------------------------------------------
# Subgraph helpers
# ---------------------------------------------------------------------------

_SUBGRAPH_PADDING = 20.0


def _collect_all_subgraph_node_ids(sg: Subgraph) -> set[str]:
    """Recursively collect all node IDs belonging to a subgraph and its children."""
    result = set(sg.node_ids)
    for child in sg.subgraphs:
        result |= _collect_all_subgraph_node_ids(child)
    return result


def _build_node_to_subgraph_map(
    subgraphs: tuple[Subgraph, ...],
) -> dict[str, str]:
    """Map each node ID to its innermost subgraph ID.

    When a node belongs to a nested subgraph, the innermost wins.
    """
    mapping: dict[str, str] = {}

    def _walk(sg: Subgraph) -> None:
        # First map direct members to this subgraph
        for nid in sg.node_ids:
            mapping[nid] = sg.id
        # Then recurse into children (children override parent mapping)
        for child in sg.subgraphs:
            _walk(child)

    for sg in subgraphs:
        _walk(sg)
    return mapping


def _group_subgraph_nodes_in_layers(
    layer_lists: list[list[str]],
    node_to_sg: dict[str, str],
) -> list[list[str]]:
    """Reorder nodes within each layer so that nodes belonging to the same
    subgraph are contiguous."""
    result: list[list[str]] = []
    for layer_nodes in layer_lists:
        # Stable sort: group by subgraph id (None for no subgraph)
        # Preserve relative order within each group.
        groups: dict[str | None, list[str]] = {}
        order: list[str | None] = []
        for n in layer_nodes:
            sg_id = node_to_sg.get(n)
            if sg_id not in groups:
                groups[sg_id] = []
                order.append(sg_id)
            groups[sg_id].append(n)
        new_layer: list[str] = []
        for sg_id in order:
            new_layer.extend(groups[sg_id])
        result.append(new_layer)
    return result


def _compute_subgraph_layouts(
    subgraphs: tuple[Subgraph, ...],
    node_layouts: dict[str, NodeLayout],
    padding: float = _SUBGRAPH_PADDING,
) -> dict[str, SubgraphLayout]:
    """Compute bounding boxes for all subgraphs, recursively.

    For nested subgraphs, the parent bbox includes child bboxes.
    """
    result: dict[str, SubgraphLayout] = {}

    def _compute(sg: Subgraph) -> SubgraphLayout | None:
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")
        found = False

        # Include direct member nodes
        all_node_ids = _collect_all_subgraph_node_ids(sg)
        for nid in all_node_ids:
            nl = node_layouts.get(nid)
            if nl is None:
                continue
            found = True
            min_x = min(min_x, nl.x)
            min_y = min(min_y, nl.y)
            max_x = max(max_x, nl.x + nl.width)
            max_y = max(max_y, nl.y + nl.height)

        # Recurse into child subgraphs and include their bboxes
        for child in sg.subgraphs:
            child_layout = _compute(child)
            if child_layout is not None:
                found = True
                min_x = min(min_x, child_layout.x)
                min_y = min(min_y, child_layout.y)
                max_x = max(max_x, child_layout.x + child_layout.width)
                max_y = max(max_y, child_layout.y + child_layout.height)

        if not found:
            return None

        title_extra = 16.0  # extra top padding for title text
        sgl = SubgraphLayout(
            id=sg.id,
            x=min_x - padding,
            y=min_y - padding - title_extra,
            width=(max_x - min_x) + 2 * padding,
            height=(max_y - min_y) + 2 * padding + title_extra,
            title=sg.title,
        )
        result[sg.id] = sgl
        return sgl

    for sg in subgraphs:
        _compute(sg)

    return result


# ---------------------------------------------------------------------------
# Disconnected components
# ---------------------------------------------------------------------------

def _find_components(
    node_ids: list[str],
    edges: list[tuple[str, str, int]],
) -> list[list[str]]:
    """Find connected components using union-find."""
    parent: dict[str, str] = {n: n for n in node_ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for s, t, _ in edges:
        union(s, t)

    groups: dict[str, list[str]] = defaultdict(list)
    for n in node_ids:
        groups[find(n)].append(n)

    return list(groups.values())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def layout_diagram(
    diagram: Diagram,
    measure_fn: MeasureFn,
    config: LayoutConfig | None = None,
) -> LayoutResult:
    """Lay out a diagram using the Sugiyama layered graph algorithm.

    Args:
        diagram: The IR diagram to lay out.
        measure_fn: A callable ``(text, font_size) -> (width, height)``.
        config: Optional layout configuration.  If *None*, defaults are used
            with the direction taken from ``diagram.direction``.

    Returns:
        A :class:`LayoutResult` with positioned nodes and routed edges.
    """
    if config is None:
        config = LayoutConfig(direction=diagram.direction)

    direction = config.direction

    # Build subgraph membership map for grouping constraint
    node_to_sg = _build_node_to_subgraph_map(diagram.subgraphs)

    # Collect node info
    node_ids = [n.id for n in diagram.nodes]
    node_labels = {n.id: n.label for n in diagram.nodes}

    # Measure nodes
    node_sizes: dict[str, tuple[float, float]] = {}
    for nid, label in node_labels.items():
        tw, th = measure_fn(label, _DEFAULT_FONT_SIZE)
        w = tw + _NODE_PADDING_H
        h = th + _NODE_PADDING_V
        # Minimum dimensions
        w = max(w, 40.0)
        h = max(h, 30.0)
        node_sizes[nid] = (w, h)

    # Build edge list as (source, target) tuples
    ir_edges: list[tuple[str, str]] = [(e.source, e.target) for e in diagram.edges]

    # Preprocess: separate self-loops, merge multi-edges
    normal_edges, self_loops = _preprocess_edges(ir_edges)

    if not node_ids:
        return LayoutResult(nodes={}, edges=[], width=0.0, height=0.0)

    # Find connected components
    all_edges_for_components = normal_edges + self_loops
    components = _find_components(node_ids, all_edges_for_components)

    all_positions: dict[str, tuple[float, float]] = {}
    all_node_sizes: dict[str, tuple[float, float]] = dict(node_sizes)
    component_edge_data: list[dict] = []

    # Layout each component separately, then stack them
    component_offsets: list[float] = []
    y_offset = 0.0

    for comp_nodes in components:
        comp_set = set(comp_nodes)
        comp_edges = [
            (s, t, idx) for s, t, idx in normal_edges
            if s in comp_set and t in comp_set
        ]
        comp_self_loops = [(s, t, idx) for s, t, idx in self_loops if s in comp_set]

        # Step 1: Cycle removal
        acyclic_edges, reversed_indices = _remove_cycles(comp_nodes, comp_edges)

        # Step 2: Layer assignment
        layers = _longest_path_layering(comp_nodes, acyclic_edges)

        # Step 2b: Insert dummy nodes
        layers, dummy_edges, dummy_info = _insert_dummy_nodes(layers, acyclic_edges)

        # Add dummy node sizes (thin)
        for dummy_id in dummy_info:
            all_node_sizes[dummy_id] = (1.0, 1.0)

        # Step 3: Build layer lists and minimize crossings
        layer_lists = _build_layer_lists(layers)
        layer_lists = _crossing_minimization(layer_lists, dummy_edges, layers)

        # Step 3b: Group subgraph members together within layers
        if node_to_sg:
            layer_lists = _group_subgraph_nodes_in_layers(
                layer_lists, node_to_sg,
            )

        # Step 4: Coordinate assignment (in TB space)
        positions = _assign_coordinates(
            layer_lists, all_node_sizes, config.rank_sep, config.node_sep,
        )

        # Apply y offset for stacking components
        component_offsets.append(y_offset)
        for n, (x, y) in positions.items():
            all_positions[n] = (x, y + y_offset)

        # Calculate component height
        comp_height = 0.0
        for n in positions:
            pos = positions[n]
            size = all_node_sizes.get(n, (40.0, 30.0))
            bottom = pos[1] + size[1] / 2.0
            if bottom > comp_height:
                comp_height = bottom

        y_offset = comp_height + config.rank_sep

        component_edge_data.append({
            "comp_edges": comp_edges,
            "dummy_edges": dummy_edges,
            "dummy_info": dummy_info,
            "reversed_indices": reversed_indices,
            "comp_self_loops": comp_self_loops,
        })

    # Route edges for all components
    all_edge_layouts: list[EdgeLayout] = []
    for data in component_edge_data:
        edge_layouts = _route_edges(
            data["comp_edges"],
            data["dummy_edges"],
            data["dummy_info"],
            data["reversed_indices"],
            all_positions,
            all_node_sizes,
            data["comp_self_loops"],
            ir_edges,
        )
        all_edge_layouts.extend(edge_layouts)

    # Apply direction transform
    if direction not in (Direction.TB, Direction.TD):
        # Compute max coords for transform reference
        max_y = max((pos[1] for pos in all_positions.values()), default=0.0)
        max_x = max((pos[0] for pos in all_positions.values()), default=0.0)

        # Transform positions
        all_positions, all_node_sizes = _apply_direction(
            all_positions, all_node_sizes, direction,
        )

        # Transform edge points
        transformed_edges: list[EdgeLayout] = []
        for el in all_edge_layouts:
            new_points = [
                _transform_point(p, direction, max_y, max_x)
                for p in el.points
            ]
            transformed_edges.append(EdgeLayout(
                points=new_points,
                source=el.source,
                target=el.target,
            ))
        all_edge_layouts = transformed_edges

    # Build NodeLayout results (only real nodes, not dummies)
    node_layouts: dict[str, NodeLayout] = {}
    for nid in node_ids:
        if nid in all_positions:
            cx, cy = all_positions[nid]
            w, h = all_node_sizes.get(nid, (40.0, 30.0))
            # For LR/RL, sizes were swapped, but we want original logical sizes
            if direction in (Direction.LR, Direction.RL):
                # Sizes were swapped in _apply_direction; swap back for NodeLayout
                w, h = h, w
            node_layouts[nid] = NodeLayout(
                x=cx - w / 2.0,
                y=cy - h / 2.0,
                width=w,
                height=h,
            )

    # Compute subgraph layouts
    subgraph_layouts = _compute_subgraph_layouts(
        diagram.subgraphs, node_layouts,
    )

    # Compute overall dimensions (include subgraph bboxes)
    if node_layouts:
        overall_w = max(nl.x + nl.width for nl in node_layouts.values())
        overall_h = max(nl.y + nl.height for nl in node_layouts.values())
    else:
        overall_w = 0.0
        overall_h = 0.0

    # Expand overall dimensions to include subgraph bounding boxes
    for sgl in subgraph_layouts.values():
        overall_w = max(overall_w, sgl.x + sgl.width)
        overall_h = max(overall_h, sgl.y + sgl.height)

    return LayoutResult(
        nodes=node_layouts,
        edges=all_edge_layouts,
        width=overall_w,
        height=overall_h,
        subgraphs=subgraph_layouts,
    )


__all__ = [
    "EdgeLayout",
    "LayoutConfig",
    "LayoutResult",
    "NodeLayout",
    "Point",
    "SubgraphLayout",
    "layout_diagram",
]
