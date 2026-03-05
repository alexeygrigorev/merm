"""Parametrized corpus rendering tests: every .mmd fixture renders to valid SVG.

Discovers all .mmd files under tests/fixtures/corpus/ and verifies each one
renders successfully via render_diagram() and produces well-formed SVG.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from pymermaid import render_diagram

CORPUS_DIR = Path(__file__).parent / "fixtures" / "corpus"

def _discover_corpus_files() -> list[Path]:
    """Discover all .mmd files in the corpus, sorted for deterministic order."""
    return sorted(CORPUS_DIR.rglob("*.mmd"))

def _corpus_id(path: Path) -> str:
    """Generate a readable test ID from a corpus file path."""
    return str(path.relative_to(CORPUS_DIR))

CORPUS_FILES = _discover_corpus_files()
CORPUS_IDS = [_corpus_id(f) for f in CORPUS_FILES]

@pytest.mark.parametrize("mmd_file", CORPUS_FILES, ids=CORPUS_IDS)
def test_renders_without_error(mmd_file: Path) -> None:
    """render_diagram() completes without raising for every corpus fixture."""
    source = mmd_file.read_text()
    svg = render_diagram(source)
    assert isinstance(svg, str)
    assert len(svg) > 0

@pytest.mark.parametrize("mmd_file", CORPUS_FILES, ids=CORPUS_IDS)
def test_produces_valid_svg(mmd_file: Path) -> None:
    """The output is well-formed XML containing an <svg> root element."""
    source = mmd_file.read_text()
    svg = render_diagram(source)

    # Must contain SVG markers
    assert "<svg" in svg
    assert "</svg>" in svg

    # Must be parseable as XML
    root = ET.fromstring(svg)
    # Root tag should be svg (possibly with namespace)
    assert root.tag.endswith("svg"), f"Expected <svg> root, got <{root.tag}>"
