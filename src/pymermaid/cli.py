"""Command-line interface for pymermaid."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version

from pymermaid.layout import layout_diagram
from pymermaid.measure import TextMeasurer
from pymermaid.parser import ParseError, parse_flowchart
from pymermaid.render import render_svg


def _get_version() -> str:
    """Return the version string for display."""
    try:
        return f"pymermaid {version('pymermaid')}"
    except Exception:
        return "pymermaid 0.1.0"


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="pymermaid",
        description="Render Mermaid diagrams to SVG from the command line.",
    )
    parser.add_argument(
        "-i",
        "--input",
        default=None,
        help="Input .mmd file path (reads from stdin if not provided)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output SVG file path (writes to stdout if not provided)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=_get_version(),
    )
    return parser


def main() -> None:
    """Entry point for the pymermaid CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    # --- Read input ---
    if args.input is not None:
        try:
            with open(args.input) as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            sys.exit(2)
        except PermissionError:
            print(
                f"Error: permission denied: {args.input}", file=sys.stderr
            )
            sys.exit(2)
        except OSError as exc:
            print(f"Error: cannot read file: {exc}", file=sys.stderr)
            sys.exit(2)
    else:
        source = sys.stdin.read()

    # --- Parse ---
    try:
        diagram = parse_flowchart(source)
    except ParseError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Measure + Layout ---
    measurer = TextMeasurer()
    layout = layout_diagram(
        diagram,
        measure_fn=measurer.measure,
    )

    # --- Render ---
    svg_output = render_svg(diagram, layout)

    # --- Write output ---
    if args.output is not None:
        try:
            with open(args.output, "w") as f:
                f.write(svg_output)
        except FileNotFoundError:
            print(
                f"Error: output directory does not exist: {args.output}",
                file=sys.stderr,
            )
            sys.exit(2)
        except PermissionError:
            print(
                f"Error: permission denied writing: {args.output}",
                file=sys.stderr,
            )
            sys.exit(2)
        except OSError as exc:
            print(f"Error: cannot write file: {exc}", file=sys.stderr)
            sys.exit(2)
    else:
        print(svg_output)


if __name__ == "__main__":
    main()
