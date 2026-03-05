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

from __future__ import annotations

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
