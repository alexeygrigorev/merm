"""Comprehensive corpus tests: parametrized tests over 50+ .mmd fixture files.

Each fixture is parsed, laid out, rendered, and verified for structural
correctness, no overlaps, correct directionality, and subgraph containment.
"""

import time
from pathlib import Path

import pytest

from merm.layout import layout_diagram
from merm.measure import TextMeasurer
from merm.parser import parse_flowchart
from merm.render import render_svg
from tests.svg_utils import (
    BBox,
    _extract_direction_from_mmd,
    check_directionality,
    check_no_overlaps,
    check_subgraph_containment,
    parse_merm_svg_edges,
    parse_merm_svg_nodes,
)

CORPUS_DIR = Path(__file__).parent / "fixtures" / "corpus"

# Directories containing flowchart fixtures (this test uses parse_flowchart).
# Non-flowchart diagram types (sequence, state, class) are tested in
# test_corpus_rendering.py via render_diagram() which auto-detects type.
_FLOWCHART_DIRS = {
    "basic", "direction", "edges", "scale", "shapes",
    "styling", "subgraphs", "text", "flowchart",
}

def _discover_corpus_files() -> list[Path]:
    """Discover flowchart .mmd files in the corpus."""
    files: list[Path] = []
    for mmd in sorted(CORPUS_DIR.rglob("*.mmd")):
        # Include file if its top-level corpus subdirectory is a flowchart dir
        rel = mmd.relative_to(CORPUS_DIR)
        top_dir = rel.parts[0]
        if top_dir in _FLOWCHART_DIRS:
            files.append(mmd)
    return files

def _corpus_ids(files: list[Path]) -> list[str]:
    """Generate test IDs from corpus file paths."""
    return [str(f.relative_to(CORPUS_DIR)) for f in files]

CORPUS_FILES = _discover_corpus_files()
CORPUS_IDS = _corpus_ids(CORPUS_FILES)

def _render_mmd(mmd_text: str) -> str:
    """Parse, lay out, and render mermaid text to SVG."""
    diagram = parse_flowchart(mmd_text)
    measurer = TextMeasurer()
    layout = layout_diagram(diagram, measure_fn=measurer.measure)
    return render_svg(diagram, layout)

# ---------------------------------------------------------------------------
# Parametrized corpus tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mmd_file", CORPUS_FILES, ids=CORPUS_IDS)
class TestCorpusRenders:
    """Every fixture in the corpus renders without error and has correct structure."""

    def test_parses_without_error(self, mmd_file: Path) -> None:
        """The .mmd file parses without raising."""
        mmd_text = mmd_file.read_text()
        parse_flowchart(mmd_text)

    def test_renders_to_valid_svg(self, mmd_file: Path) -> None:
        """The fixture renders to non-empty, valid SVG."""
        mmd_text = mmd_file.read_text()
        svg = _render_mmd(mmd_text)
        assert "<svg" in svg
        assert "</svg>" in svg
        assert len(svg) > 100

    def test_correct_node_count(self, mmd_file: Path) -> None:
        """The SVG contains the expected number of nodes (from parser)."""
        mmd_text = mmd_file.read_text()
        diagram = parse_flowchart(mmd_text)
        svg = _render_mmd(mmd_text)
        svg_nodes = parse_merm_svg_nodes(svg)
        assert len(svg_nodes) == len(diagram.nodes), (
            f"Expected {len(diagram.nodes)} nodes, "
            f"found {len(svg_nodes)} in SVG"
        )

    def test_correct_edge_count(self, mmd_file: Path) -> None:
        """The SVG contains the expected number of edges (from parser)."""
        mmd_text = mmd_file.read_text()
        diagram = parse_flowchart(mmd_text)
        svg = _render_mmd(mmd_text)
        svg_edges = parse_merm_svg_edges(svg)
        assert len(svg_edges) == len(diagram.edges), (
            f"Expected {len(diagram.edges)} edges, "
            f"found {len(svg_edges)} in SVG"
        )

    def test_all_node_ids_present(self, mmd_file: Path) -> None:
        """All node IDs from the parser appear in the SVG."""
        mmd_text = mmd_file.read_text()
        diagram = parse_flowchart(mmd_text)
        svg = _render_mmd(mmd_text)
        svg_nodes = parse_merm_svg_nodes(svg)
        svg_node_ids = {n.node_id for n in svg_nodes}
        for node in diagram.nodes:
            assert node.id in svg_node_ids, f"Node {node.id!r} missing from SVG"

    def test_all_labels_present(self, mmd_file: Path) -> None:
        """All node labels from the parser appear somewhere in the SVG text."""
        mmd_text = mmd_file.read_text()
        diagram = parse_flowchart(mmd_text)
        svg = _render_mmd(mmd_text)
        for node in diagram.nodes:
            # Labels may have <br/> which becomes separate text elements
            # Check that at least the plain text parts appear
            label_text = node.label.replace("<br/>", " ").strip()
            if label_text:
                for part in label_text.split():
                    # FA icon references (fa:fa-*) are rendered as SVG
                    # paths, not text -- skip them in label checks.
                    if part.startswith("fa:"):
                        continue
                    assert part in svg, (
                        f"Label part {part!r} from node {node.id!r} "
                        f"not found in SVG"
                    )

@pytest.mark.parametrize("mmd_file", CORPUS_FILES, ids=CORPUS_IDS)
def test_corpus_no_overlaps(mmd_file: Path) -> None:
    """No node overlaps in any corpus fixture."""
    mmd_text = mmd_file.read_text()
    svg = _render_mmd(mmd_text)
    overlaps = check_no_overlaps(svg)
    assert overlaps == [], f"Node overlaps detected: {overlaps}"

# ---------------------------------------------------------------------------
# Direction-specific tests
# ---------------------------------------------------------------------------

DIRECTION_FILES = sorted(
    (CORPUS_DIR / "direction").glob("*.mmd")
)
DIRECTION_IDS = [f.stem for f in DIRECTION_FILES]

@pytest.mark.parametrize("mmd_file", DIRECTION_FILES, ids=DIRECTION_IDS)
def test_direction_flow(mmd_file: Path) -> None:
    """Direction fixtures verify correct flow direction."""
    mmd_text = mmd_file.read_text()
    direction = _extract_direction_from_mmd(mmd_text)
    assert direction is not None, f"Could not extract direction from {mmd_file.name}"
    svg = _render_mmd(mmd_text)
    violations = check_directionality(svg, direction)
    assert violations == [], (
        f"Directionality violations for {direction}: {violations}"
    )

# ---------------------------------------------------------------------------
# Subgraph containment tests
# ---------------------------------------------------------------------------

SUBGRAPH_FILES = sorted(
    (CORPUS_DIR / "subgraphs").glob("*.mmd")
)
SUBGRAPH_IDS = [f.stem for f in SUBGRAPH_FILES]

@pytest.mark.parametrize("mmd_file", SUBGRAPH_FILES, ids=SUBGRAPH_IDS)
def test_subgraph_containment(mmd_file: Path) -> None:
    """Subgraph fixtures verify children are inside subgraph bounds."""
    mmd_text = mmd_file.read_text()
    svg = _render_mmd(mmd_text)
    violations = check_subgraph_containment(svg)
    assert violations == [], f"Subgraph containment violations: {violations}"

# ---------------------------------------------------------------------------
# Unit tests for comparison utilities
# ---------------------------------------------------------------------------

class TestBBox:
    """Unit tests for BBox overlap and containment."""

    def test_overlapping_boxes(self) -> None:
        a = BBox(0, 0, 10, 10)
        b = BBox(5, 5, 10, 10)
        assert a.overlaps(b)
        assert b.overlaps(a)

    def test_non_overlapping_boxes(self) -> None:
        a = BBox(0, 0, 10, 10)
        b = BBox(20, 20, 10, 10)
        assert not a.overlaps(b)
        assert not b.overlaps(a)

    def test_touching_boxes_no_overlap(self) -> None:
        """Boxes sharing an edge should not be flagged as overlapping."""
        a = BBox(0, 0, 10, 10)
        b = BBox(10, 0, 10, 10)
        assert not a.overlaps(b)

    def test_contains(self) -> None:
        outer = BBox(0, 0, 100, 100)
        inner = BBox(10, 10, 20, 20)
        assert outer.contains(inner)
        assert not inner.contains(outer)

    def test_center(self) -> None:
        box = BBox(10, 20, 30, 40)
        assert box.center_x == 25.0
        assert box.center_y == 40.0

class TestOverlapDetection:
    """Unit tests for check_no_overlaps with synthetic SVG."""

    def _make_svg(self, nodes: list[tuple[str, float, float, float, float]]) -> str:
        """Build a minimal SVG with positioned nodes."""
        parts = ['<svg xmlns="http://www.w3.org/2000/svg">']
        for nid, x, y, w, h in nodes:
            parts.append(
                f'<g class="node" data-node-id="{nid}">'
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" />'
                f'<text>{nid}</text></g>'
            )
        parts.append("</svg>")
        return "\n".join(parts)

    def test_overlapping_nodes_detected(self) -> None:
        svg = self._make_svg([
            ("A", 0, 0, 50, 50),
            ("B", 25, 25, 50, 50),
        ])
        overlaps = check_no_overlaps(svg)
        assert len(overlaps) == 1
        assert ("A", "B") in overlaps

    def test_non_overlapping_nodes_pass(self) -> None:
        svg = self._make_svg([
            ("A", 0, 0, 40, 30),
            ("B", 100, 0, 40, 30),
        ])
        overlaps = check_no_overlaps(svg)
        assert overlaps == []

    def test_touching_nodes_pass(self) -> None:
        svg = self._make_svg([
            ("A", 0, 0, 40, 30),
            ("B", 40, 0, 40, 30),
        ])
        overlaps = check_no_overlaps(svg)
        assert overlaps == []

class TestDirectionalityCheck:
    """Unit tests for check_directionality with synthetic SVG."""

    def _make_svg(
        self,
        nodes: list[tuple[str, float, float, float, float]],
        edges: list[tuple[str, str]],
    ) -> str:
        parts = ['<svg xmlns="http://www.w3.org/2000/svg">']
        for nid, x, y, w, h in nodes:
            parts.append(
                f'<g class="node" data-node-id="{nid}">'
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" />'
                f'<text>{nid}</text></g>'
            )
        for src, tgt in edges:
            parts.append(
                f'<g class="edge" data-edge-source="{src}" '
                f'data-edge-target="{tgt}">'
                f'<path d="M0,0 L0,0" /></g>'
            )
        parts.append("</svg>")
        return "\n".join(parts)

    def test_td_correct(self) -> None:
        svg = self._make_svg(
            [("A", 0, 0, 40, 30), ("B", 0, 80, 40, 30)],
            [("A", "B")],
        )
        assert check_directionality(svg, "TD") == []

    def test_td_violation(self) -> None:
        svg = self._make_svg(
            [("A", 0, 80, 40, 30), ("B", 0, 0, 40, 30)],
            [("A", "B")],
        )
        violations = check_directionality(svg, "TD")
        assert len(violations) == 1

    def test_lr_correct(self) -> None:
        svg = self._make_svg(
            [("A", 0, 0, 40, 30), ("B", 100, 0, 40, 30)],
            [("A", "B")],
        )
        assert check_directionality(svg, "LR") == []

    def test_bt_correct(self) -> None:
        svg = self._make_svg(
            [("A", 0, 80, 40, 30), ("B", 0, 0, 40, 30)],
            [("A", "B")],
        )
        assert check_directionality(svg, "BT") == []

    def test_rl_correct(self) -> None:
        svg = self._make_svg(
            [("A", 100, 0, 40, 30), ("B", 0, 0, 40, 30)],
            [("A", "B")],
        )
        assert check_directionality(svg, "RL") == []

class TestSubgraphContainment:
    """Unit tests for check_subgraph_containment with synthetic SVG."""

    def _make_svg(
        self,
        subgraphs: list[tuple[str, float, float, float, float]],
        nodes: list[tuple[str, float, float, float, float]],
    ) -> str:
        parts = ['<svg xmlns="http://www.w3.org/2000/svg">']
        for sg_id, x, y, w, h in subgraphs:
            parts.append(
                f'<g class="subgraph" data-subgraph-id="{sg_id}">'
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" />'
                f'<text>{sg_id}</text></g>'
            )
        for nid, x, y, w, h in nodes:
            parts.append(
                f'<g class="node" data-node-id="{nid}">'
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" />'
                f'<text>{nid}</text></g>'
            )
        parts.append("</svg>")
        return "\n".join(parts)

    def test_contained_node_passes(self) -> None:
        svg = self._make_svg(
            [("sg1", 0, 0, 200, 200)],
            [("A", 10, 10, 40, 30)],
        )
        assert check_subgraph_containment(svg) == []

    def test_node_outside_not_flagged(self) -> None:
        """A node whose center is outside the subgraph is not checked."""
        svg = self._make_svg(
            [("sg1", 0, 0, 100, 100)],
            [("A", 200, 200, 40, 30)],
        )
        assert check_subgraph_containment(svg) == []

    def test_node_center_inside_but_bbox_overflows(self) -> None:
        """Node center is inside subgraph but bbox extends outside."""
        svg = self._make_svg(
            [("sg1", 0, 0, 60, 60)],
            [("A", 10, 10, 80, 80)],  # center at 50,50 inside sg(0,0,60,60)
        )
        violations = check_subgraph_containment(svg)
        assert len(violations) == 1

    def test_nested_subgraph_containment(self) -> None:
        svg = self._make_svg(
            [
                ("outer", 0, 0, 300, 300),
                ("inner", 10, 10, 100, 100),
            ],
            [("A", 20, 20, 40, 30)],
        )
        assert check_subgraph_containment(svg) == []

# ---------------------------------------------------------------------------
# Scale / performance test
# ---------------------------------------------------------------------------

def test_large_diagram_performance() -> None:
    """The large.mmd fixture (50+ nodes) renders in under 5 seconds."""
    large_file = CORPUS_DIR / "scale" / "large.mmd"
    mmd_text = large_file.read_text()

    start = time.monotonic()
    _render_mmd(mmd_text)
    elapsed = time.monotonic() - start

    assert elapsed < 5.0, f"Large diagram took {elapsed:.2f}s (limit 5s)"

# ---------------------------------------------------------------------------
# Integration: existing fixtures still work
# ---------------------------------------------------------------------------

def test_existing_simple_flowchart() -> None:
    """The original simple_flowchart.mmd fixture still works."""
    fixture = Path(__file__).parent / "fixtures" / "simple_flowchart.mmd"
    mmd_text = fixture.read_text()
    svg = _render_mmd(mmd_text)
    assert "<svg" in svg
    nodes = parse_merm_svg_nodes(svg)
    assert len(nodes) == 3
