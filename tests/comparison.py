"""SVG structural comparison utilities for pymermaid test infrastructure.

This module provides functions to parse mermaid-generated SVGs and compare
their structure (nodes, edges, labels) against reference renderings.

To regenerate reference SVGs from fixtures, run:
    for f in tests/fixtures/*.mmd; do
        name=$(basename "$f" .mmd)
        mmdc -i "$f" -o "tests/reference/${name}.svg" \
            -t default -c tests/mmdc-config.json \
            -p tests/puppeteer-config.json
    done
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# SVG namespace
SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"
NS = {
    "svg": SVG_NS,
    "xhtml": XHTML_NS,
}

@dataclass
class BBox:
    """Axis-aligned bounding box."""

    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def overlaps(self, other: "BBox", tolerance: float = 1.0) -> bool:
        """Check if this bbox overlaps another, with tolerance for shared edges."""
        return (
            self.x < other.right - tolerance
            and self.right > other.x + tolerance
            and self.y < other.bottom - tolerance
            and self.bottom > other.y + tolerance
        )

    def contains(self, other: "BBox", tolerance: float = 1.0) -> bool:
        """Check if this bbox fully contains another."""
        return (
            self.x <= other.x + tolerance
            and self.y <= other.y + tolerance
            and self.right >= other.right - tolerance
            and self.bottom >= other.bottom - tolerance
        )

@dataclass
class NodeInfo:
    """Extracted information about a node in the SVG."""

    node_id: str
    labels: list[str] = field(default_factory=list)

@dataclass
class EdgeInfo:
    """Extracted information about an edge in the SVG."""

    edge_id: str
    labels: list[str] = field(default_factory=list)

@dataclass
class SVGStructure:
    """Parsed structural data from an SVG."""

    nodes: list[NodeInfo] = field(default_factory=list)
    edges: list[EdgeInfo] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

@dataclass
class SVGDiff:
    """Result of comparing two SVG structures."""

    node_count_expected: int
    node_count_actual: int
    edge_count_expected: int
    edge_count_actual: int
    missing_labels: list[str] = field(default_factory=list)
    extra_labels: list[str] = field(default_factory=list)
    identical: bool = False

    def summary(self) -> str:
        """Return a human-readable summary of differences."""
        parts = []
        if self.node_count_expected != self.node_count_actual:
            parts.append(
                f"Expected {self.node_count_expected} nodes, "
                f"found {self.node_count_actual}"
            )
        if self.edge_count_expected != self.edge_count_actual:
            parts.append(
                f"Expected {self.edge_count_expected} edges, "
                f"found {self.edge_count_actual}"
            )
        if self.missing_labels:
            parts.append(f"missing labels: {self.missing_labels}")
        if self.extra_labels:
            parts.append(f"extra labels: {self.extra_labels}")
        if not parts:
            return "Identical"
        return "; ".join(parts)

def _parse_svg_tree(svg_text: str) -> ET.Element:
    """Parse SVG text into an ElementTree element, handling namespaces."""
    # Register namespaces to avoid ns0/ns1 prefixes in output
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    ET.register_namespace("xhtml", XHTML_NS)
    return ET.fromstring(svg_text)

def _extract_text_content(element: ET.Element) -> str:
    """Recursively extract all text content from an element."""
    texts = []
    if element.text and element.text.strip():
        texts.append(element.text.strip())
    for child in element:
        texts.append(_extract_text_content(child))
    if element.tail and element.tail.strip():
        texts.append(element.tail.strip())
    return " ".join(t for t in texts if t)

def _find_all_recursive(root: ET.Element, match_fn) -> list[ET.Element]:
    """Find all elements matching a predicate, recursively."""
    results = []
    if match_fn(root):
        results.append(root)
    for child in root:
        results.extend(_find_all_recursive(child, match_fn))
    return results

def _has_class(element: ET.Element, class_name: str) -> bool:
    """Check if an element has a specific CSS class."""
    classes = element.get("class", "").split()
    return class_name in classes

def parse_svg_nodes(svg_text: str) -> list[NodeInfo]:
    """Extract node information from an SVG.

    Looks for <g> elements with class 'node' (mermaid's node container),
    extracts IDs and label text.

    Args:
        svg_text: Raw SVG XML content as a string.

    Returns:
        List of NodeInfo objects with node IDs and labels.
    """
    if not svg_text or not svg_text.strip():
        return []

    root = _parse_svg_tree(svg_text)

    nodes = []
    # Find all <g> elements with class "node"
    node_elements = _find_all_recursive(
        root, lambda e: e.tag in (f"{{{SVG_NS}}}g", "g") and _has_class(e, "node")
    )

    for node_el in node_elements:
        node_id = node_el.get("id", "")
        # Extract labels from nodeLabel spans and foreignObject text
        labels = []
        label_spans = _find_all_recursive(
            node_el,
            lambda e: (
                e.tag in (f"{{{XHTML_NS}}}span", "span", f"{{{XHTML_NS}}}p", "p")
                and (
                    _has_class(e, "nodeLabel")
                    or e.tag in (f"{{{XHTML_NS}}}p", "p")
                )
            ),
        )
        for span in label_spans:
            text = _extract_text_content(span)
            if text:
                labels.append(text)
        # Deduplicate (p inside span both match)
        seen = set()
        unique_labels = []
        for lbl in labels:
            if lbl not in seen:
                seen.add(lbl)
                unique_labels.append(lbl)
        nodes.append(NodeInfo(node_id=node_id, labels=unique_labels))

    return nodes

def parse_svg_edges(svg_text: str) -> list[EdgeInfo]:
    """Extract edge information from an SVG.

    Looks for path elements within edgePaths groups and edge labels.

    Args:
        svg_text: Raw SVG XML content as a string.

    Returns:
        List of EdgeInfo objects with edge IDs and labels.
    """
    if not svg_text or not svg_text.strip():
        return []

    root = _parse_svg_tree(svg_text)

    edges = []
    # Find path elements with data-edge attribute or within edgePaths group
    edge_paths = _find_all_recursive(
        root,
        lambda e: (
            e.tag in (f"{{{SVG_NS}}}path", "path") and e.get("data-edge") == "true"
        ),
    )

    # Also find edge labels
    edge_label_groups = _find_all_recursive(
        root,
        lambda e: e.tag in (f"{{{SVG_NS}}}g", "g") and _has_class(e, "edgeLabel"),
    )

    # Build a map of edge labels by data-id
    label_map: dict[str, list[str]] = {}
    for label_group in edge_label_groups:
        label_els = _find_all_recursive(
            label_group,
            lambda e: e.tag in (f"{{{SVG_NS}}}g", "g") and _has_class(e, "label"),
        )
        for label_el in label_els:
            data_id = label_el.get("data-id", "")
            text = _extract_text_content(label_el)
            if text and data_id:
                label_map.setdefault(data_id, []).append(text)

    for path_el in edge_paths:
        edge_id = path_el.get("data-id", path_el.get("id", ""))
        labels = label_map.get(edge_id, [])
        edges.append(EdgeInfo(edge_id=edge_id, labels=labels))

    return edges

def parse_svg_labels(svg_text: str) -> list[str]:
    """Extract all label text from an SVG.

    Collects both node labels and edge labels.

    Args:
        svg_text: Raw SVG XML content as a string.

    Returns:
        List of label text strings found in the SVG.
    """
    if not svg_text or not svg_text.strip():
        return []

    labels = []

    nodes = parse_svg_nodes(svg_text)
    for node in nodes:
        labels.extend(node.labels)

    edges = parse_svg_edges(svg_text)
    for edge in edges:
        labels.extend(edge.labels)

    return labels

def parse_svg_structure(svg_text: str) -> SVGStructure:
    """Parse full structural information from an SVG.

    Args:
        svg_text: Raw SVG XML content as a string.

    Returns:
        SVGStructure with nodes, edges, and labels.
    """
    return SVGStructure(
        nodes=parse_svg_nodes(svg_text),
        edges=parse_svg_edges(svg_text),
        labels=parse_svg_labels(svg_text),
    )

def structural_compare(our_svg: str, reference_svg: str) -> SVGDiff:
    """Compare structural elements of two SVGs.

    Compares node counts, edge counts, and label text between our
    rendered SVG and the reference (mmdc) SVG.

    Args:
        our_svg: SVG content from pymermaid renderer.
        reference_svg: SVG content from mermaid-cli (mmdc).

    Returns:
        SVGDiff describing the differences.
    """
    ref = parse_svg_structure(reference_svg)
    ours = parse_svg_structure(our_svg)

    ref_labels = sorted(ref.labels)
    our_labels = sorted(ours.labels)

    missing = sorted(set(ref_labels) - set(our_labels))
    extra = sorted(set(our_labels) - set(ref_labels))

    identical = (
        len(ref.nodes) == len(ours.nodes)
        and len(ref.edges) == len(ours.edges)
        and not missing
        and not extra
    )

    return SVGDiff(
        node_count_expected=len(ref.nodes),
        node_count_actual=len(ours.nodes),
        edge_count_expected=len(ref.edges),
        edge_count_actual=len(ours.edges),
        missing_labels=missing,
        extra_labels=extra,
        identical=identical,
    )

# ---------------------------------------------------------------------------
# pymermaid-native SVG parsing
# ---------------------------------------------------------------------------

@dataclass
class PymermaidNodeInfo:
    """Node extracted from pymermaid SVG using data-node-id."""

    node_id: str
    labels: list[str] = field(default_factory=list)
    bbox: BBox | None = None

@dataclass
class PymermaidEdgeInfo:
    """Edge extracted from pymermaid SVG using data-edge-source/target."""

    source: str
    target: str
    labels: list[str] = field(default_factory=list)

@dataclass
class PymermaidSubgraphInfo:
    """Subgraph extracted from pymermaid SVG using data-subgraph-id."""

    subgraph_id: str
    title: str | None = None
    bbox: BBox | None = None

def _parse_bbox_from_rect(group: ET.Element) -> BBox | None:
    """Extract bounding box from the first rect element in a group."""
    rects = _find_all_recursive(
        group,
        lambda e: e.tag in (f"{{{SVG_NS}}}rect", "rect"),
    )
    if not rects:
        return None
    rect = rects[0]
    try:
        x = float(rect.get("x", "0"))
        y = float(rect.get("y", "0"))
        w = float(rect.get("width", "0"))
        h = float(rect.get("height", "0"))
        return BBox(x, y, w, h)
    except (ValueError, TypeError):
        return None

def _parse_bbox_from_circle(group: ET.Element) -> BBox | None:
    """Extract bounding box from the first circle element in a group."""
    circles = _find_all_recursive(
        group,
        lambda e: e.tag in (f"{{{SVG_NS}}}circle", "circle"),
    )
    if not circles:
        return None
    circle = circles[0]
    try:
        cx = float(circle.get("cx", "0"))
        cy = float(circle.get("cy", "0"))
        r = float(circle.get("r", "0"))
        return BBox(cx - r, cy - r, 2 * r, 2 * r)
    except (ValueError, TypeError):
        return None

def _parse_bbox_from_polygon(group: ET.Element) -> BBox | None:
    """Extract bounding box from the first polygon element in a group."""
    polygons = _find_all_recursive(
        group,
        lambda e: e.tag in (f"{{{SVG_NS}}}polygon", "polygon"),
    )
    if not polygons:
        return None
    polygon = polygons[0]
    points_str = polygon.get("points", "")
    if not points_str:
        return None
    try:
        coords = []
        for pair in points_str.strip().split():
            parts = pair.split(",")
            if len(parts) == 2:
                coords.append((float(parts[0]), float(parts[1])))
        if not coords:
            return None
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return BBox(min_x, min_y, max_x - min_x, max_y - min_y)
    except (ValueError, TypeError):
        return None

def _parse_node_bbox(group: ET.Element) -> BBox | None:
    """Extract bounding box from a node group (rect, circle, or polygon)."""
    bbox = _parse_bbox_from_rect(group)
    if bbox is not None:
        return bbox
    bbox = _parse_bbox_from_circle(group)
    if bbox is not None:
        return bbox
    return _parse_bbox_from_polygon(group)

def parse_pymermaid_svg_nodes(svg_text: str) -> list[PymermaidNodeInfo]:
    """Parse nodes from pymermaid SVG format.

    pymermaid uses data-node-id on <g class="node"> elements
    and <text> elements for labels.
    """
    if not svg_text or not svg_text.strip():
        return []

    root = _parse_svg_tree(svg_text)
    nodes = []
    node_elements = _find_all_recursive(
        root,
        lambda e: (
            e.tag in (f"{{{SVG_NS}}}g", "g")
            and _has_class(e, "node")
            and e.get("data-node-id") is not None
        ),
    )

    for node_el in node_elements:
        node_id = node_el.get("data-node-id", "")
        labels = []
        text_els = _find_all_recursive(
            node_el,
            lambda e: e.tag in (f"{{{SVG_NS}}}text", "text"),
        )
        for text_el in text_els:
            text = _extract_text_content(text_el)
            if text:
                labels.append(text)
        bbox = _parse_node_bbox(node_el)
        nodes.append(PymermaidNodeInfo(node_id=node_id, labels=labels, bbox=bbox))

    return nodes

def parse_pymermaid_svg_edges(svg_text: str) -> list[PymermaidEdgeInfo]:
    """Parse edges from pymermaid SVG format.

    pymermaid uses data-edge-source and data-edge-target on <g class="edge">.
    """
    if not svg_text or not svg_text.strip():
        return []

    root = _parse_svg_tree(svg_text)
    edges = []
    edge_elements = _find_all_recursive(
        root,
        lambda e: (
            e.tag in (f"{{{SVG_NS}}}g", "g")
            and _has_class(e, "edge")
            and e.get("data-edge-source") is not None
        ),
    )

    for edge_el in edge_elements:
        source = edge_el.get("data-edge-source", "")
        target = edge_el.get("data-edge-target", "")
        labels = []
        text_els = _find_all_recursive(
            edge_el,
            lambda e: e.tag in (f"{{{SVG_NS}}}text", "text"),
        )
        for text_el in text_els:
            text = _extract_text_content(text_el)
            if text:
                labels.append(text)
        edges.append(PymermaidEdgeInfo(source=source, target=target, labels=labels))

    return edges

def parse_pymermaid_svg_subgraphs(svg_text: str) -> list[PymermaidSubgraphInfo]:
    """Parse subgraphs from pymermaid SVG format.

    pymermaid uses data-subgraph-id on <g class="subgraph">.
    """
    if not svg_text or not svg_text.strip():
        return []

    root = _parse_svg_tree(svg_text)
    subgraphs = []
    sg_elements = _find_all_recursive(
        root,
        lambda e: (
            e.tag in (f"{{{SVG_NS}}}g", "g")
            and _has_class(e, "subgraph")
            and e.get("data-subgraph-id") is not None
        ),
    )

    for sg_el in sg_elements:
        sg_id = sg_el.get("data-subgraph-id", "")
        title = None
        text_els = _find_all_recursive(
            sg_el,
            lambda e: e.tag in (f"{{{SVG_NS}}}text", "text"),
        )
        for text_el in text_els:
            text = _extract_text_content(text_el)
            if text:
                title = text
                break
        bbox = _parse_bbox_from_rect(sg_el)
        subgraphs.append(PymermaidSubgraphInfo(
            subgraph_id=sg_id, title=title, bbox=bbox
        ))

    return subgraphs

# ---------------------------------------------------------------------------
# Layout quality checks
# ---------------------------------------------------------------------------

def check_no_overlaps(svg_text: str) -> list[tuple[str, str]]:
    """Check that no two node bounding boxes overlap.

    Returns a list of overlapping node ID pairs. Empty list means no overlaps.
    """
    nodes = parse_pymermaid_svg_nodes(svg_text)
    overlaps = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if nodes[i].bbox is None or nodes[j].bbox is None:
                continue
            if nodes[i].bbox.overlaps(nodes[j].bbox):
                overlaps.append((nodes[i].node_id, nodes[j].node_id))
    return overlaps

def check_directionality(svg_text: str, direction: str) -> list[str]:
    """Check that edges flow in the expected direction.

    For TD/TB: target y > source y (downward)
    For BT: target y < source y (upward)
    For LR: target x > source x (rightward)
    For RL: target x < source x (leftward)

    Returns a list of violation descriptions. Empty list means all edges comply.
    """
    nodes = parse_pymermaid_svg_nodes(svg_text)
    edges = parse_pymermaid_svg_edges(svg_text)

    node_map: dict[str, PymermaidNodeInfo] = {n.node_id: n for n in nodes}
    violations = []

    for edge in edges:
        # Skip self-loops
        if edge.source == edge.target:
            continue
        src = node_map.get(edge.source)
        tgt = node_map.get(edge.target)
        if src is None or tgt is None:
            continue
        if src.bbox is None or tgt.bbox is None:
            continue

        direction_upper = direction.upper()
        if direction_upper in ("TD", "TB"):
            if tgt.bbox.center_y <= src.bbox.center_y:
                violations.append(
                    f"{edge.source}->{edge.target}: "
                    f"target y ({tgt.bbox.center_y:.1f}) "
                    f"<= source y ({src.bbox.center_y:.1f}) in {direction}"
                )
        elif direction_upper == "BT":
            if tgt.bbox.center_y >= src.bbox.center_y:
                violations.append(
                    f"{edge.source}->{edge.target}: "
                    f"target y ({tgt.bbox.center_y:.1f}) "
                    f">= source y ({src.bbox.center_y:.1f}) in BT"
                )
        elif direction_upper == "LR":
            if tgt.bbox.center_x <= src.bbox.center_x:
                violations.append(
                    f"{edge.source}->{edge.target}: "
                    f"target x ({tgt.bbox.center_x:.1f}) "
                    f"<= source x ({src.bbox.center_x:.1f}) in LR"
                )
        elif direction_upper == "RL":
            if tgt.bbox.center_x >= src.bbox.center_x:
                violations.append(
                    f"{edge.source}->{edge.target}: "
                    f"target x ({tgt.bbox.center_x:.1f}) "
                    f">= source x ({src.bbox.center_x:.1f}) in RL"
                )

    return violations

def check_subgraph_containment(svg_text: str) -> list[str]:
    """Check that subgraph rects contain their child nodes.

    This uses heuristic containment: a node is considered a child of a subgraph
    if it is spatially inside the subgraph bbox. Returns a list of violation
    descriptions.
    """
    nodes = parse_pymermaid_svg_nodes(svg_text)
    subgraphs = parse_pymermaid_svg_subgraphs(svg_text)

    violations = []
    for sg in subgraphs:
        if sg.bbox is None:
            continue
        # Find nodes that appear to be inside this subgraph
        for node in nodes:
            if node.bbox is None:
                continue
            # Check if node center is inside subgraph bbox -- if so, the
            # subgraph should fully contain the node
            cx, cy = node.bbox.center_x, node.bbox.center_y
            sg_box = sg.bbox
            if (
                sg_box.x < cx < sg_box.right
                and sg_box.y < cy < sg_box.bottom
            ):
                if not sg_box.contains(node.bbox, tolerance=2.0):
                    violations.append(
                        f"Node {node.node_id} center is inside subgraph "
                        f"{sg.subgraph_id} but bbox is not fully contained"
                    )

    return violations

def _extract_direction_from_mmd(mmd_text: str) -> str | None:
    """Extract the graph direction from mermaid source text."""
    pattern = r"^\s*(?:graph|flowchart)\s+(TD|TB|BT|LR|RL)"
    match = re.search(pattern, mmd_text, re.MULTILINE)
    if match:
        return match.group(1)
    return None
