#!/usr/bin/env python3
"""Render all corpus .mmd files to SVG in docs/examples/.

Usage:
    uv run scripts/render_examples.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from merm import render_diagram

CORPUS_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "corpus"
GITHUB_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "github"
EXAMPLES_DIR = Path(__file__).parent.parent / "docs" / "examples"


def render_file(mmd_path: Path, out_path: Path) -> bool:
    """Render a single .mmd file to SVG. Returns True on success."""
    try:
        source = mmd_path.read_text()
        svg = render_diagram(source)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(svg)
        return True
    except Exception as e:
        print(f"  FAIL: {mmd_path.name}: {e}")
        return False


def main():
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    fail = 0

    # Corpus files (organized by type)
    for mmd in sorted(CORPUS_DIR.rglob("*.mmd")):
        rel = mmd.relative_to(CORPUS_DIR)
        # e.g. flowchart/basic/simple.mmd -> flowchart/basic/simple.svg
        out = EXAMPLES_DIR / rel.with_suffix(".svg")
        if render_file(mmd, out):
            ok += 1
        else:
            fail += 1

    # GitHub real-world examples
    for mmd in sorted(GITHUB_DIR.glob("*.mmd")):
        out = EXAMPLES_DIR / "github" / mmd.with_suffix(".svg").name
        if render_file(mmd, out):
            ok += 1
        else:
            fail += 1

    print(f"\nRendered {ok} examples ({fail} failures) to {EXAMPLES_DIR}/")


if __name__ == "__main__":
    main()
