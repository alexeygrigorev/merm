"""Command-line interface for pymermaid."""

import argparse
import sys


def main() -> None:
    """Entry point for the pymermaid CLI."""
    parser = argparse.ArgumentParser(
        prog="pymermaid",
        description="Render Mermaid diagrams to SVG from the command line.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input .mmd file (reads from stdin if not provided)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output SVG file (writes to stdout if not provided)",
    )

    parser.parse_args()

    print("pymermaid: not yet implemented", file=sys.stderr)
    sys.exit(1)
