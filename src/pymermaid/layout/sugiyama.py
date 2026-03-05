"""Sugiyama layered graph layout algorithm.

Implements the classic Sugiyama algorithm for layered graph drawing:
1. Cycle removal via DFS
2. Layer assignment via longest path
3. Dummy node insertion for long edges
4. Crossing minimization via barycenter heuristic
5. Coordinate assignment
6. Edge routing
7. Direction transform (TB/BT/LR/RL)

Subgraph layout helpers are included here because they are tightly coupled
with the main layout_diagram function (subgraph membership affects layer
grouping and the final bounding-box computation).
"""

import math
from collections import defaultdict

from pymermaid.ir import Diagram, Direction, NodeShape, Subgraph
from pymermaid.measure.text import _line_width, _wrap_line

from .config import LayoutConfig, MeasureFn
from .types import EdgeLayout, LayoutResult, NodeLayout, Point, SubgraphLayout

# Default font size used when calling measure_fn
_DEFAULT_FONT_SIZE = 16.0

# Padding added around measured text to get node dimensions
_NODE_PADDING_H = 32.0  # 16px each side
_NODE_PADDING_V = 16.0  # 8px each side

# Minimum node dimensions (matching mermaid.js defaults)
_NODE_MIN_HEIGHT = 42.0
_NODE_MIN_WIDTH = 70.0

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
# Step 4b: Offset back-edge dummy nodes to separate overlapping back-edges
# ---------------------------------------------------------------------------

_BACK_EDGE_CHANNEL_OFFSET = 30.0  # horizontal gap between back-edge channels

def _offset_back_edge_dummies(
    positions: dict[str, tuple[float, float]],
    node_sizes: dict[str, tuple[float, float]],
    layer_lists: list[list[str]],
    dummy_info: dict[str, tuple[str, str, int]],
    reversed_indices: set[int],
    channel_offset: float = _BACK_EDGE_CHANNEL_OFFSET,
) -> dict[str, tuple[float, float]]:
    """Offset dummy nodes for back-edges so they don't overlap.

    When multiple back-edges route through the same layers, their dummy
    nodes all end up at the same x-coordinate.  This pass assigns each
    back-edge a distinct horizontal channel to the right of the rightmost
    real node in each layer.

    Returns an updated positions dict (does not mutate in place).
    """
    if not reversed_indices or not dummy_info:
        return positions

    # Identify which back-edge (by original edge index) each dummy belongs to
    back_edge_dummies: dict[int, list[str]] = {}
    for dummy_id, (orig_s, orig_t, orig_idx) in dummy_info.items():
        if orig_idx in reversed_indices:
            back_edge_dummies.setdefault(orig_idx, []).append(dummy_id)

    if not back_edge_dummies:
        return positions

    # For each layer, find the rightmost x-coordinate of real (non-dummy) nodes
    layer_right_x: dict[int, float] = {}
    for li, layer_nodes in enumerate(layer_lists):
        max_right = float("-inf")
        for n in layer_nodes:
            if n in dummy_info:
                continue  # skip dummy nodes
            if n in positions:
                cx = positions[n][0]
                w = node_sizes.get(n, (40.0, 30.0))[0]
                right = cx + w / 2.0
                if right > max_right:
                    max_right = right
        if max_right > float("-inf"):
            layer_right_x[li] = max_right

    if not layer_right_x:
        return positions

    # Build a mapping from layer index to which back-edge indices have
    # dummies in that layer
    layer_to_dummy_node: dict[int, str] = {}
    for li, layer_nodes in enumerate(layer_lists):
        for n in layer_nodes:
            if n in dummy_info:
                layer_to_dummy_node[n] = str(li)  # dummy_id -> layer_index as str

    # Actually, we need layer index for each dummy node.
    # The layer_lists already contain this info.
    dummy_to_layer: dict[str, int] = {}
    for li, layer_nodes in enumerate(layer_lists):
        for n in layer_nodes:
            dummy_to_layer[n] = li

    # Sort back-edge indices for deterministic channel assignment.
    # Sort by the source node position (leftmost source gets channel 0).
    sorted_back_edges = sorted(back_edge_dummies.keys())

    # Assign each back-edge a channel index
    n_back_edges = len(sorted_back_edges)
    if n_back_edges <= 1:
        # Single back-edge: no offset needed (it already routes fine)
        return positions

    positions = dict(positions)  # copy

    for channel_idx, edge_idx in enumerate(sorted_back_edges):
        dummies = back_edge_dummies[edge_idx]
        # Compute offset: spread channels evenly, centered around the right
        # side. Channel 0 is closest to the nodes, channel N-1 is furthest.
        offset = (channel_idx + 1) * channel_offset

        for dummy_id in dummies:
            if dummy_id in positions:
                li = dummy_to_layer.get(dummy_id, -1)
                right_x = layer_right_x.get(li, 0.0)
                old_cx, cy = positions[dummy_id]
                # Place dummy at right_x + offset
                new_cx = right_x + offset
                positions[dummy_id] = (new_cx, cy)

    return positions

# ---------------------------------------------------------------------------
# Step 4c: Align parent-child chains
# ---------------------------------------------------------------------------

def _align_parent_child_chains(
    positions: dict[str, tuple[float, float]],
    node_sizes: dict[str, tuple[float, float]],
    layer_lists: list[list[str]],
    edges: list[tuple[str, str, int]],
    dummy_info: dict[str, tuple[str, str, int]],
) -> dict[str, tuple[float, float]]:
    """Align nodes that are in a direct parent-child chain to share center-x.

    When a node has exactly one real (non-dummy) parent in the previous layer
    AND that parent has exactly one real child in this layer, align the child's
    center-x to the parent's center-x.

    This prevents unnecessary horizontal shifts for nodes in a linear chain.
    """
    positions = dict(positions)

    # Build real node sets (excluding dummies)
    real_nodes = {n for n in positions if n not in dummy_info}

    # Build adjacency among real nodes (using original edges, ignoring dummies)
    real_succ: dict[str, list[str]] = defaultdict(list)
    real_pred: dict[str, list[str]] = defaultdict(list)
    for s, t, _ in edges:
        if s in real_nodes and t in real_nodes:
            real_succ[s].append(t)
            real_pred[t].append(s)

    # Build layer index for each real node
    node_layer: dict[str, int] = {}
    for li, layer_nodes in enumerate(layer_lists):
        for n in layer_nodes:
            if n in real_nodes:
                node_layer[n] = li

    # For each layer (top to bottom), check each real node: if it has
    # exactly one real parent in the previous layer and that parent has
    # exactly one real child in this layer, align them.
    for li in range(1, len(layer_lists)):
        for node in layer_lists[li]:
            if node not in real_nodes:
                continue

            # Get real predecessors from the previous layer
            preds = [p for p in real_pred.get(node, [])
                     if node_layer.get(p) == li - 1]
            if len(preds) != 1:
                continue

            parent = preds[0]
            # Check that parent has exactly one real child in this layer
            children_in_layer = [c for c in real_succ.get(parent, [])
                                 if node_layer.get(c) == li]
            if len(children_in_layer) != 1:
                continue

            # Align: set child's center-x to parent's center-x
            parent_cx = positions[parent][0]
            child_cx, child_cy = positions[node]
            if abs(parent_cx - child_cx) > 1.0:
                positions[node] = (parent_cx, child_cy)

    return positions

# ---------------------------------------------------------------------------
# Step 5: Edge routing
# ---------------------------------------------------------------------------

def _route_edge_on_boundary(
    src_pos: tuple[float, float],
    src_size: tuple[float, float],
    tgt_pos: tuple[float, float],
    tgt_size: tuple[float, float],
    *,
    source_gap: float = 0.0,
    target_gap: float = 0.0,
) -> tuple[Point, Point]:
    """Compute edge endpoints on the node boundaries (rectangular approximation).

    Positions are centers; sizes are (width, height).

    *source_gap* pulls the source endpoint inward (away from the source node
    boundary) along the edge direction.  Typically 0 so the edge starts
    exactly on the source rect.

    *target_gap* pulls the target endpoint inward (away from the target node
    boundary).  Used when a marker (arrowhead) needs space so the marker
    tip lands on the node boundary rather than the path endpoint itself.
    With ``refX``-based marker alignment this is usually 0 as well.
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
        return Point(sx, sy + sh / 2 + source_gap), Point(tx, ty - th / 2 - target_gap)

    # Source exit point
    src_point = _boundary_point(sx, sy, sw, sh, dx, dy)
    # Target entry point (reverse direction)
    tgt_point = _boundary_point(tx, ty, tw, th, -dx, -dy)

    # Apply gaps along the edge direction
    total_gap = source_gap + target_gap
    if total_gap > 0:
        length = (dx * dx + dy * dy) ** 0.5
        if length > 2 * total_gap:
            ux = dx / length
            uy = dy / length
            if source_gap > 0:
                src_point = Point(
                    src_point.x + ux * source_gap,
                    src_point.y + uy * source_gap,
                )
            if target_gap > 0:
                tgt_point = Point(
                    tgt_point.x - ux * target_gap,
                    tgt_point.y - uy * target_gap,
                )

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

def _self_loop_points(
    cx: float, cy: float, w: float, h: float, direction: Direction,
) -> list[Point]:
    """Generate 13 control points for a self-loop Bezier path.

    For TB/TD: loop extends below the node, both start and end on bottom edge.
    For BT: loop extends above the node, both start and end on top edge.
    For LR: loop extends to the right of the node, start and end on right edge.
    For RL: loop extends to the left of the node, start and end on left edge.
    """
    if direction in (Direction.LR, Direction.RL):
        # For LR/RL the loop extends horizontally.
        # After _apply_direction, positions are swapped but sizes are NOT.
        # The node in screen space has its width=w (horizontal) and height=h.
        # For LR: loop extends to the right (+x direction).
        # For RL: loop extends to the left (-x direction).
        loop_extent = w * 1.85
        side_offset = h * 0.25
        edge_x = cx + w / 2  # right edge
        sign = 1.0
        if direction == Direction.RL:
            edge_x = cx - w / 2  # left edge
            sign = -1.0

        p0  = Point(edge_x, cy - side_offset)
        p1  = Point(edge_x + sign * loop_extent * 0.1, cy - side_offset * 2.0 * 0.9)
        p2  = Point(edge_x + sign * loop_extent * 0.3, cy - h * 0.5)
        p3  = Point(edge_x + sign * loop_extent * 0.5, cy - h * 0.5)
        p4  = Point(edge_x + sign * loop_extent * 0.7, cy - h * 0.5)
        p5  = Point(edge_x + sign * loop_extent, cy - side_offset * 0.3)
        p6  = Point(edge_x + sign * loop_extent, cy)
        p7  = Point(edge_x + sign * loop_extent, cy + side_offset * 0.3)
        p8  = Point(edge_x + sign * loop_extent * 0.7, cy + h * 0.5)
        p9  = Point(edge_x + sign * loop_extent * 0.5, cy + h * 0.5)
        p10 = Point(edge_x + sign * loop_extent * 0.3, cy + h * 0.5)
        p11 = Point(edge_x + sign * loop_extent * 0.1, cy + side_offset * 2.0 * 0.9)
        p12 = Point(edge_x, cy + side_offset)
        return [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12]

    # TB/TD (default) and BT directions: loop extends vertically.
    loop_drop = h * 1.85
    side_offset = w * 0.25
    bulge = w * 0.5

    if direction == Direction.BT:
        # Loop goes above the node
        top = cy - h / 2
        p0  = Point(cx - side_offset, top)
        p1  = Point(cx - bulge * 0.9, top - loop_drop * 0.1)
        p2  = Point(cx - bulge, top - loop_drop * 0.3)
        p3  = Point(cx - bulge, top - loop_drop * 0.5)
        p4  = Point(cx - bulge, top - loop_drop * 0.7)
        p5  = Point(cx - side_offset * 0.3, top - loop_drop)
        p6  = Point(cx, top - loop_drop)
        p7  = Point(cx + side_offset * 0.3, top - loop_drop)
        p8  = Point(cx + bulge, top - loop_drop * 0.7)
        p9  = Point(cx + bulge, top - loop_drop * 0.5)
        p10 = Point(cx + bulge, top - loop_drop * 0.3)
        p11 = Point(cx + bulge * 0.9, top - loop_drop * 0.1)
        p12 = Point(cx + side_offset, top)
        return [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12]

    # TB/TD: loop goes below the node
    bot = cy + h / 2
    p0  = Point(cx - side_offset, bot)
    p1  = Point(cx - bulge * 0.9, bot + loop_drop * 0.1)
    p2  = Point(cx - bulge, bot + loop_drop * 0.3)
    p3  = Point(cx - bulge, bot + loop_drop * 0.5)
    p4  = Point(cx - bulge, bot + loop_drop * 0.7)
    p5  = Point(cx - side_offset * 0.3, bot + loop_drop)
    p6  = Point(cx, bot + loop_drop)
    p7  = Point(cx + side_offset * 0.3, bot + loop_drop)
    p8  = Point(cx + bulge, bot + loop_drop * 0.7)
    p9  = Point(cx + bulge, bot + loop_drop * 0.5)
    p10 = Point(cx + bulge, bot + loop_drop * 0.3)
    p11 = Point(cx + bulge * 0.9, bot + loop_drop * 0.1)
    p12 = Point(cx + side_offset, bot)
    return [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12]

def _route_edges(
    original_edges: list[tuple[str, str, int]],
    acyclic_edges_with_dummies: list[tuple[str, str, int]],
    dummy_info: dict[str, tuple[str, str, int]],
    reversed_indices: set[int],
    positions: dict[str, tuple[float, float]],
    node_sizes: dict[str, tuple[float, float]],
    self_loops: list[tuple[str, str, int]],
    ir_edges: list[tuple[str, str]],
    direction: Direction = Direction.TD,
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

    # Pre-compute back-edge fan-out offsets: when multiple back-edges
    # target the same node, spread their attachment x-coordinates.
    _BACK_EDGE_FAN_SPACING = 12.0  # px between adjacent attachment points
    back_edge_target_groups: dict[str, list[int]] = defaultdict(list)
    for idx in edge_chains:
        if idx in reversed_indices:
            orig_s, orig_t = ir_edges[idx]
            back_edge_target_groups[orig_t].append(idx)
    # Sort each group for deterministic ordering
    back_edge_fan_offset: dict[int, float] = {}
    for tgt, indices in back_edge_target_groups.items():
        indices.sort()
        n = len(indices)
        if n <= 1:
            continue
        for rank, idx in enumerate(indices):
            # Center the fan around 0: offsets are -span/2 ... +span/2
            back_edge_fan_offset[idx] = (rank - (n - 1) / 2.0) * _BACK_EDGE_FAN_SPACING

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

        # Apply back-edge fan-out: shift the target attachment point's
        # x-coordinate so multiple back-edges to the same node don't
        # all land at the same spot.
        if idx in back_edge_fan_offset:
            dx = back_edge_fan_offset[idx]
            if points:
                last = points[-1]
                points[-1] = Point(last.x + dx, last.y)

        results.append(EdgeLayout(points=points, source=orig_s, target=orig_t))

    # Route self-loops: generate a leaf/oval loop that extends away from the
    # node in the flow direction.  For TB/TD the loop goes below; for BT it
    # goes above; for LR it extends to the right; for RL to the left.
    #
    # We store 13 points encoding 4 cubic Bezier segments.  The edge renderer
    # detects self-loops (source == target) and uses _self_loop_path_d().
    for s, t, idx in self_loops:
        pos = positions.get(s, (0.0, 0.0))
        size = node_sizes.get(s, (40.0, 30.0))
        w, h = size
        cx, cy = pos

        pts = _self_loop_points(cx, cy, w, h, direction)
        results.append(EdgeLayout(points=pts, source=s, target=t))

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
        # Swap x and y axes (positions are centers, sizes stay the same)
        for n, (x, y) in positions.items():
            new_positions[n] = (y, x)
        new_sizes = dict(node_sizes)

    elif direction == Direction.RL:
        # Swap x and y, then flip x
        for n, (x, y) in positions.items():
            new_positions[n] = (y, x)
        new_sizes = dict(node_sizes)
        if new_positions:
            max_x = max(pos[0] for pos in new_positions.values())
            new_positions = {n: (max_x - x, y) for n, (x, y) in new_positions.items()}

    return new_positions, new_sizes

def _transform_point(
    p: Point, direction: Direction, max_y: float, max_x: float,
) -> Point:
    """Transform a single point from TB coordinates to target direction.

    *max_y* and *max_x* are the maximum center coordinates in the original
    TB layout (before direction transform).
    """
    if direction in (Direction.TB, Direction.TD):
        return p
    if direction == Direction.BT:
        return Point(p.x, max_y - p.y)
    if direction == Direction.LR:
        return Point(p.y, p.x)
    if direction == Direction.RL:
        # Swap x/y then flip new-x.  max_y is the TB max-y which becomes
        # the max of the new x-axis after the swap.
        return Point(max_y - p.y, p.x)
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

def _build_node_to_toplevel_subgraph_map(
    subgraphs: tuple[Subgraph, ...],
) -> dict[str, str]:
    """Map each node ID to its top-level subgraph ID.

    All nodes in nested subgraphs are mapped to the outermost parent.
    """
    mapping: dict[str, str] = {}

    for sg in subgraphs:
        all_ids = _collect_all_subgraph_node_ids(sg)
        for nid in all_ids:
            mapping[nid] = sg.id

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

def _separate_subgraphs(
    positions: dict[str, tuple[float, float]],
    node_sizes: dict[str, tuple[float, float]],
    subgraphs: tuple[Subgraph, ...],
    padding: float = _SUBGRAPH_PADDING,
    title_height: float = 24.0,
    gap: float = 30.0,
    direction: Direction = Direction.TB,
) -> dict[str, tuple[float, float]]:
    """Push nodes apart so that sibling subgraph bounding boxes do not overlap.

    For TB/TD/BT directions, this operates in TB coordinate space where
    y is the rank axis: subgraphs are separated along Y first, then X.

    For LR/RL directions (post-transform), the rank axis is X: subgraphs
    are center-aligned along Y (the cross-axis) and separated along X
    only where they overlap.

    Returns an updated positions dict.
    """
    if not subgraphs:
        return positions

    is_horizontal = direction in (Direction.LR, Direction.RL)

    positions = dict(positions)  # copy to avoid mutating caller's dict

    def _bbox_for_sg(
        sg: Subgraph,
    ) -> tuple[float, float, float, float] | None:
        """Compute (min_x, min_y, max_x, max_y) including padding/title."""
        all_ids = _collect_all_subgraph_node_ids(sg)
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")
        found = False
        for nid in all_ids:
            if nid not in positions:
                continue
            cx, cy = positions[nid]
            w, h = node_sizes.get(nid, (40.0, 30.0))
            found = True
            min_x = min(min_x, cx - w / 2.0)
            min_y = min(min_y, cy - h / 2.0)
            max_x = max(max_x, cx + w / 2.0)
            max_y = max(max_y, cy + h / 2.0)
        if not found:
            return None
        # Add padding and title space
        return (
            min_x - padding,
            min_y - padding - title_height,
            max_x + padding,
            max_y + padding,
        )

    def _shift_sg_nodes(sg: Subgraph, dx: float, dy: float) -> None:
        """Shift all nodes in a subgraph (including nested) by (dx, dy)."""
        all_ids = _collect_all_subgraph_node_ids(sg)
        for nid in all_ids:
            if nid in positions:
                ox, oy = positions[nid]
                positions[nid] = (ox + dx, oy + dy)

    def _boxes_overlap(
        bb1: tuple[float, float, float, float],
        bb2: tuple[float, float, float, float],
    ) -> bool:
        """Check if two bounding boxes overlap (with gap tolerance)."""
        # bb = (min_x, min_y, max_x, max_y)
        x_overlap = bb1[0] < bb2[2] + gap and bb2[0] < bb1[2] + gap
        y_overlap = bb1[1] < bb2[3] + gap and bb2[1] < bb1[3] + gap
        return x_overlap and y_overlap

    def _separate_siblings_tb(siblings: tuple[Subgraph, ...]) -> None:
        """Ensure sibling subgraphs don't overlap (TB/BT mode).

        First separates along Y (rank axis in TB), then resolves any
        remaining overlaps along X (order axis in TB).
        """
        if len(siblings) <= 1:
            return

        # Collect subgraphs that have actual nodes
        bboxes: list[tuple[Subgraph, tuple[float, float, float, float]]] = []
        for sg in siblings:
            bb = _bbox_for_sg(sg)
            if bb is not None:
                bboxes.append((sg, bb))

        if len(bboxes) <= 1:
            return

        # --- Pass 1: separate along Y axis ---
        bboxes.sort(key=lambda item: item[1][1])

        for i in range(1, len(bboxes)):
            _prev_sg, prev_bb = bboxes[i - 1]
            curr_sg, curr_bb = bboxes[i]

            prev_bottom = prev_bb[3]
            curr_top = curr_bb[1]

            if curr_top < prev_bottom + gap:
                shift_y = (prev_bottom + gap) - curr_top
                _shift_sg_nodes(curr_sg, 0.0, shift_y)
                new_bb = _bbox_for_sg(curr_sg)
                if new_bb is not None:
                    bboxes[i] = (curr_sg, new_bb)

        # --- Pass 2: separate along X axis for any remaining overlaps ---
        bboxes.sort(key=lambda item: item[1][0])

        for i in range(1, len(bboxes)):
            _prev_sg, prev_bb = bboxes[i - 1]
            curr_sg, curr_bb = bboxes[i]

            if _boxes_overlap(prev_bb, curr_bb):
                prev_right = prev_bb[2]
                curr_left = curr_bb[0]
                shift_x = (prev_right + gap) - curr_left
                if shift_x > 0:
                    _shift_sg_nodes(curr_sg, shift_x, 0.0)
                    new_bb = _bbox_for_sg(curr_sg)
                    if new_bb is not None:
                        bboxes[i] = (curr_sg, new_bb)

    def _separate_siblings_lr(siblings: tuple[Subgraph, ...]) -> None:
        """Ensure sibling subgraphs don't overlap (LR/RL mode).

        For horizontal layouts, the rank axis is X and the cross-axis is Y.
        We center-align subgraphs along Y so they sit side-by-side, then
        separate along X only where they actually overlap.
        """
        if len(siblings) <= 1:
            return

        # Collect subgraphs that have actual nodes
        bboxes: list[tuple[Subgraph, tuple[float, float, float, float]]] = []
        for sg in siblings:
            bb = _bbox_for_sg(sg)
            if bb is not None:
                bboxes.append((sg, bb))

        if len(bboxes) <= 1:
            return

        # --- Center-align along Y (cross-axis) ---
        # Compute the overall vertical center of all subgraph nodes,
        # then shift each subgraph so its vertical center matches.
        all_sg_node_ids: set[str] = set()
        for sg, _bb in bboxes:
            all_sg_node_ids |= _collect_all_subgraph_node_ids(sg)

        # Compute global vertical center across all subgraph nodes
        y_vals: list[float] = []
        for nid in all_sg_node_ids:
            if nid in positions:
                y_vals.append(positions[nid][1])
        if not y_vals:
            return
        global_center_y = (min(y_vals) + max(y_vals)) / 2.0

        # Shift each subgraph so its vertical center aligns with the global center
        for sg, bb in bboxes:
            sg_center_y = (bb[1] + bb[3]) / 2.0
            dy = global_center_y - sg_center_y
            if abs(dy) > 0.5:
                _shift_sg_nodes(sg, 0.0, dy)

        # Recompute bounding boxes after vertical alignment
        bboxes = []
        for sg in siblings:
            bb = _bbox_for_sg(sg)
            if bb is not None:
                bboxes.append((sg, bb))

        if len(bboxes) <= 1:
            return

        # --- Separate along X (rank axis) where boxes overlap ---
        bboxes.sort(key=lambda item: item[1][0])

        for i in range(1, len(bboxes)):
            _prev_sg, prev_bb = bboxes[i - 1]
            curr_sg, curr_bb = bboxes[i]

            if _boxes_overlap(prev_bb, curr_bb):
                prev_right = prev_bb[2]
                curr_left = curr_bb[0]
                shift_x = (prev_right + gap) - curr_left
                if shift_x > 0:
                    _shift_sg_nodes(curr_sg, shift_x, 0.0)
                    new_bb = _bbox_for_sg(curr_sg)
                    if new_bb is not None:
                        bboxes[i] = (curr_sg, new_bb)

        # --- Separate along Y for any remaining overlaps ---
        # Recompute bboxes after X-separation to get accurate positions.
        # Use a small epsilon for the X-overlap check to avoid false
        # positives from floating-point rounding after the X-separation
        # pass (which places boxes at exactly gap distance apart).
        _eps = 1.0
        bboxes = []
        for sg in siblings:
            bb = _bbox_for_sg(sg)
            if bb is not None:
                bboxes.append((sg, bb))
        bboxes.sort(key=lambda item: item[1][1])

        for i in range(1, len(bboxes)):
            _prev_sg, prev_bb = bboxes[i - 1]
            curr_sg, curr_bb = bboxes[i]

            # Check true overlap (with epsilon tolerance on X to avoid
            # floating-point false positives after X separation)
            x_overlap = (
                prev_bb[0] + _eps < curr_bb[2] + gap
                and curr_bb[0] + _eps < prev_bb[2] + gap
            )
            y_overlap = prev_bb[1] < curr_bb[3] + gap and curr_bb[1] < prev_bb[3] + gap
            if x_overlap and y_overlap:
                prev_bottom = prev_bb[3]
                curr_top = curr_bb[1]
                shift_y = (prev_bottom + gap) - curr_top
                if shift_y > 0:
                    _shift_sg_nodes(curr_sg, 0.0, shift_y)
                    new_bb = _bbox_for_sg(curr_sg)
                    if new_bb is not None:
                        bboxes[i] = (curr_sg, new_bb)

    def _separate_recursive(siblings: tuple[Subgraph, ...]) -> None:
        """Recursively separate subgraphs at each nesting level."""
        # First recurse into children of each subgraph
        for sg in siblings:
            if sg.subgraphs:
                _separate_recursive(sg.subgraphs)

        # Then separate the siblings at this level
        if is_horizontal:
            _separate_siblings_lr(siblings)
        else:
            _separate_siblings_tb(siblings)

    _separate_recursive(subgraphs)

    return positions

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

        title_extra = 24.0  # extra top padding for title text
        title_margin = 8.0  # left margin for title text inside rect
        title_padding = 16.0  # total horizontal padding around title text

        content_width = (max_x - min_x) + 2 * padding
        rect_width = content_width

        # Measure title text width and ensure the rect is wide enough
        title = sg.title or sg.id
        _SUBGRAPH_TITLE_FONT_SIZE = 12.0
        title_text_width = _line_width(title, _SUBGRAPH_TITLE_FONT_SIZE)
        min_width_for_title = title_text_width + title_margin + title_padding
        if min_width_for_title > rect_width:
            rect_width = min_width_for_title

        # Center the wider rect around the child content
        content_center_x = (min_x + max_x) / 2.0
        rect_x = content_center_x - rect_width / 2.0

        sgl = SubgraphLayout(
            id=sg.id,
            x=rect_x,
            y=min_y - padding - title_extra,
            width=rect_width,
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
    node_shapes = {n.id: n.shape for n in diagram.nodes}

    # Maximum text width before wrapping (matches mermaid.js max-width: 200px)
    _MAX_TEXT_WIDTH = 200.0

    # Measure nodes (shape-aware sizing, with text wrapping for long labels)
    node_sizes: dict[str, tuple[float, float]] = {}
    for nid, label in node_labels.items():
        # Check if text needs wrapping
        raw_width = _line_width(label, _DEFAULT_FONT_SIZE)
        if raw_width > _MAX_TEXT_WIDTH and "<br/>" not in label:
            # Wrap the label and measure the wrapped version
            wrapped_lines = _wrap_line(label, _DEFAULT_FONT_SIZE, _MAX_TEXT_WIDTH)
            tw = max(_line_width(line, _DEFAULT_FONT_SIZE) for line in wrapped_lines)
            th = _DEFAULT_FONT_SIZE * 1.4 * len(wrapped_lines)
        else:
            tw, th = measure_fn(label, _DEFAULT_FONT_SIZE)
        shape = node_shapes.get(nid, NodeShape.rect)

        if shape in (NodeShape.circle, NodeShape.double_circle):
            # Circle: use diagonal of text bbox for diameter so the
            # rectangular text area is inscribed within the circle.
            _CIRCLE_PAD = 8.0
            diag = math.sqrt(tw ** 2 + th ** 2)
            r = diag / 2.0 + _CIRCLE_PAD
            if shape == NodeShape.double_circle:
                r += 5.0  # extra gap for outer circle
            diameter = r * 2.0
            node_sizes[nid] = (diameter, diameter)
        elif shape == NodeShape.diamond:
            # Diamond: the inscribed rectangle of a diamond with half-dims
            # (a, b) has dimensions (a, b).  So to fit text (tw, th) the
            # diamond bounding box must be ~2x the text dimensions.
            w = 2.0 * tw + _NODE_PADDING_H
            h = 2.0 * th + _NODE_PADDING_V
            node_sizes[nid] = (max(w, _NODE_MIN_WIDTH), max(h, _NODE_MIN_HEIGHT))
        elif shape == NodeShape.cylinder:
            # Cylinder: extra vertical space for top/bottom ellipse caps
            _CYL_RY = 10.0
            w = tw + _NODE_PADDING_H
            h = th + _NODE_PADDING_V + 4 * _CYL_RY  # extra for caps
            min_h = _NODE_MIN_HEIGHT + 2 * _CYL_RY
            node_sizes[nid] = (max(w, _NODE_MIN_WIDTH), max(h, min_h))
        elif shape == NodeShape.hexagon:
            # Hexagon: inset = w/4 on each side, so effective text width
            # is w/2.  To fit text width tw we need w = 2*tw + padding.
            w = 2.0 * tw + _NODE_PADDING_H
            h = th + _NODE_PADDING_V
            node_sizes[nid] = (max(w, _NODE_MIN_WIDTH), max(h, _NODE_MIN_HEIGHT))
        elif shape in (NodeShape.parallelogram, NodeShape.parallelogram_alt):
            # Parallelogram: 10% skew on each side eats 20% of width.
            # Effective text width = w * 0.8, so w = tw / 0.8 + padding.
            w = tw / 0.8 + _NODE_PADDING_H
            h = th + _NODE_PADDING_V
            node_sizes[nid] = (max(w, _NODE_MIN_WIDTH), max(h, _NODE_MIN_HEIGHT))
        elif shape in (NodeShape.trapezoid, NodeShape.trapezoid_alt):
            # Trapezoid: 10% inset on the narrow side eats 20% of width.
            # Effective text width = w * 0.8, so w = tw / 0.8 + padding.
            w = tw / 0.8 + _NODE_PADDING_H
            h = th + _NODE_PADDING_V
            node_sizes[nid] = (max(w, _NODE_MIN_WIDTH), max(h, _NODE_MIN_HEIGHT))
        elif shape == NodeShape.asymmetric:
            # Asymmetric: notch of h/4 on left side reduces usable width.
            # Add extra horizontal padding to compensate.
            w = tw + _NODE_PADDING_H + 20.0
            h = th + _NODE_PADDING_V
            node_sizes[nid] = (max(w, _NODE_MIN_WIDTH), max(h, _NODE_MIN_HEIGHT))
        elif shape == NodeShape.stadium:
            # Stadium: pill shape loses rx = h/2 on each side.
            # Add extra horizontal padding to compensate.
            w = tw + _NODE_PADDING_H + 20.0
            h = th + _NODE_PADDING_V
            node_sizes[nid] = (max(w, _NODE_MIN_WIDTH), max(h, _NODE_MIN_HEIGHT))
        else:
            w = tw + _NODE_PADDING_H
            h = th + _NODE_PADDING_V
            # Minimum dimensions
            w = max(w, _NODE_MIN_WIDTH)
            h = max(h, _NODE_MIN_HEIGHT)
            node_sizes[nid] = (w, h)

    # Build edge list as (source, target) tuples
    ir_edges: list[tuple[str, str]] = [(e.source, e.target) for e in diagram.edges]

    # Preprocess: separate self-loops, merge multi-edges
    normal_edges, self_loops = _preprocess_edges(ir_edges)

    if not node_ids:
        return LayoutResult(nodes={}, edges=[], width=0.0, height=0.0)

    # For LR/RL, adjust rank_sep: after the coordinate swap, inter-rank
    # spacing becomes horizontal.  We need to account for the difference
    # between node width (post-swap horizontal dimension) and node height
    # (pre-swap vertical dimension which determines layer spacing).
    # The goal is rank_sep gap between node EDGES, regardless of direction.
    effective_rank_sep = config.rank_sep
    if direction in (Direction.LR, Direction.RL):
        # In TB layout, inter-rank center distance = max_layer_height + rank_sep.
        # After LR swap, this becomes horizontal distance.  But nodes are wider
        # than tall, so we need extra space: add (avg_width - avg_height).
        if node_sizes:
            avg_w = sum(s[0] for s in node_sizes.values()) / len(node_sizes)
            avg_h = sum(s[1] for s in node_sizes.values()) / len(node_sizes)
            extra = max(0.0, avg_w - avg_h)
            effective_rank_sep = config.rank_sep + extra

    # Find connected components
    all_edges_for_components = normal_edges + self_loops
    components = _find_components(node_ids, all_edges_for_components)

    all_positions: dict[str, tuple[float, float]] = {}
    all_node_sizes: dict[str, tuple[float, float]] = dict(node_sizes)
    component_edge_data: list[dict] = []

    # Layout each component separately, then place them side-by-side
    # (matching mermaid.js behaviour for disconnected components)
    component_positions: list[dict[str, tuple[float, float]]] = []
    component_sizes: list[tuple[float, float]] = []  # (width, height) per component

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
            layer_lists, all_node_sizes, effective_rank_sep, config.node_sep,
        )

        # Step 4b: Offset back-edge dummy nodes so overlapping back-edges
        # get distinct horizontal channels.
        if reversed_indices:
            positions = _offset_back_edge_dummies(
                positions, all_node_sizes, layer_lists,
                dummy_info, reversed_indices,
            )

        # Step 4c: Align parent-child chains so direct parent-child
        # nodes share center-x (prevents unnecessary horizontal shifts).
        positions = _align_parent_child_chains(
            positions, all_node_sizes, layer_lists,
            acyclic_edges, dummy_info,
        )

        # Compute component bounding box
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")
        for n in positions:
            pos = positions[n]
            size = all_node_sizes.get(n, (40.0, 30.0))
            min_x = min(min_x, pos[0] - size[0] / 2.0)
            min_y = min(min_y, pos[1] - size[1] / 2.0)
            max_x = max(max_x, pos[0] + size[0] / 2.0)
            max_y = max(max_y, pos[1] + size[1] / 2.0)
        comp_width = max_x - min_x if positions else 0.0
        comp_height = max_y - min_y if positions else 0.0

        component_positions.append(positions)
        component_sizes.append((comp_width, comp_height))

        component_edge_data.append({
            "comp_edges": comp_edges,
            "dummy_edges": dummy_edges,
            "dummy_info": dummy_info,
            "reversed_indices": reversed_indices,
            "comp_self_loops": comp_self_loops,
        })

    # Place components side-by-side (left to right) with node_sep gap,
    # vertically centered relative to the tallest component.
    max_comp_height = max((h for _, h in component_sizes), default=0.0)
    x_offset = 0.0
    for i, positions in enumerate(component_positions):
        comp_w, comp_h = component_sizes[i]
        y_offset = (max_comp_height - comp_h) / 2.0
        for n, (x, y) in positions.items():
            all_positions[n] = (x + x_offset, y + y_offset)
        x_offset += comp_w + config.node_sep

    # Separate overlapping subgraph bounding boxes (in TB space, before
    # direction transform) so sibling subgraphs don't overlap.
    if diagram.subgraphs:
        all_positions = _separate_subgraphs(
            all_positions, all_node_sizes, diagram.subgraphs,
        )

    # Apply direction transform BEFORE edge routing so that boundary
    # intersection points are computed in the final coordinate space.
    if direction not in (Direction.TB, Direction.TD):
        all_positions, all_node_sizes = _apply_direction(
            all_positions, all_node_sizes, direction,
        )

        # After direction transform, subgraph bounding boxes may overlap
        # in the new coordinate space (e.g. LR swaps axes, so TB X-axis
        # overlap becomes Y-axis overlap).  Run separation again in the
        # transformed space, using direction-aware logic so that LR/RL
        # layouts center-align subgraphs vertically.
        if diagram.subgraphs:
            all_positions = _separate_subgraphs(
                all_positions, all_node_sizes, diagram.subgraphs,
                direction=direction,
            )

        # Normalize: shift everything so min position is >= 0
        all_min_x = float("inf")
        all_min_y = float("inf")
        for nid, (cx, cy) in all_positions.items():
            w, h = all_node_sizes.get(nid, (0, 0))
            all_min_x = min(all_min_x, cx - w / 2.0)
            all_min_y = min(all_min_y, cy - h / 2.0)

        if all_min_x < 0 or all_min_y < 0:
            dx = max(0.0, -all_min_x)
            dy = max(0.0, -all_min_y)
            all_positions = {
                n: (x + dx, y + dy)
                for n, (x, y) in all_positions.items()
            }

    # Route edges for all components (using final transformed positions)
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
            direction=direction,
        )
        all_edge_layouts.extend(edge_layouts)

    # Build NodeLayout results (only real nodes, not dummies)
    node_layouts: dict[str, NodeLayout] = {}
    for nid in node_ids:
        if nid in all_positions:
            cx, cy = all_positions[nid]
            w, h = all_node_sizes.get(nid, (40.0, 30.0))
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

    # Compute bounding box across all elements (nodes, edges, subgraphs)
    min_x = 0.0
    min_y = 0.0
    max_x = 0.0
    max_y = 0.0

    if node_layouts:
        min_x = min(nl.x for nl in node_layouts.values())
        min_y = min(nl.y for nl in node_layouts.values())
        max_x = max(nl.x + nl.width for nl in node_layouts.values())
        max_y = max(nl.y + nl.height for nl in node_layouts.values())

    for el in all_edge_layouts:
        for p in el.points:
            min_x = min(min_x, p.x)
            min_y = min(min_y, p.y)
            max_x = max(max_x, p.x)
            max_y = max(max_y, p.y)

    for sgl in subgraph_layouts.values():
        min_x = min(min_x, sgl.x)
        min_y = min(min_y, sgl.y)
        max_x = max(max_x, sgl.x + sgl.width)
        max_y = max(max_y, sgl.y + sgl.height)

    # If any element extends into negative coordinates, shift everything
    # so that the minimum is at 0.
    shift_x = -min_x if min_x < 0 else 0.0
    shift_y = -min_y if min_y < 0 else 0.0

    if shift_x != 0.0 or shift_y != 0.0:
        for nid in node_layouts:
            nl = node_layouts[nid]
            node_layouts[nid] = NodeLayout(
                x=nl.x + shift_x, y=nl.y + shift_y,
                width=nl.width, height=nl.height,
            )
        for i, el in enumerate(all_edge_layouts):
            shifted_points = [
                Point(p.x + shift_x, p.y + shift_y) for p in el.points
            ]
            all_edge_layouts[i] = EdgeLayout(
                source=el.source, target=el.target,
                points=shifted_points,
            )
        for sg_id in list(subgraph_layouts):
            sgl = subgraph_layouts[sg_id]
            subgraph_layouts[sg_id] = SubgraphLayout(
                id=sgl.id,
                x=sgl.x + shift_x, y=sgl.y + shift_y,
                width=sgl.width, height=sgl.height,
                title=sgl.title,
            )
        max_x += shift_x
        max_y += shift_y

    return LayoutResult(
        nodes=node_layouts,
        edges=all_edge_layouts,
        width=max_x,
        height=max_y,
        subgraphs=subgraph_layouts,
    )
