"""SVG parsing and layout-quality utilities for pymermaid test infrastructure.

Provides helpers to parse pymermaid-generated SVGs and check layout properties
such as node overlaps, edge directionality, and subgraph containment.
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


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def _parse_svg_tree(svg_text: str) -> ET.Element:
    """Parse SVG text into an ElementTree element, handling namespaces."""
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


# ---------------------------------------------------------------------------
# Pymermaid-native SVG parsing
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


def parse_merm_svg_nodes(svg_text: str) -> list[PymermaidNodeInfo]:
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


def parse_merm_svg_edges(svg_text: str) -> list[PymermaidEdgeInfo]:
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


def parse_merm_svg_subgraphs(svg_text: str) -> list[PymermaidSubgraphInfo]:
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
        subgraphs.append(
            PymermaidSubgraphInfo(subgraph_id=sg_id, title=title, bbox=bbox)
        )

    return subgraphs


# ---------------------------------------------------------------------------
# Layout quality checks
# ---------------------------------------------------------------------------


def check_no_overlaps(svg_text: str) -> list[tuple[str, str]]:
    """Check that no two node bounding boxes overlap.

    Returns a list of overlapping node ID pairs. Empty list means no overlaps.
    """
    nodes = parse_merm_svg_nodes(svg_text)
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
    nodes = parse_merm_svg_nodes(svg_text)
    edges = parse_merm_svg_edges(svg_text)

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
    nodes = parse_merm_svg_nodes(svg_text)
    subgraphs = parse_merm_svg_subgraphs(svg_text)

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
