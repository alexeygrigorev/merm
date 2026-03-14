# Issue 73: Edge case bug hunting — compare against mmdc

## Problem

Systematic comparison of pymermaid output against mmdc (mermaid CLI) for complex real-world diagrams has not been done. There are likely rendering edge cases and bugs lurking.

## Scope

- Collect a set of complex real-world mermaid diagrams (from GitHub repos, documentation sites)
- Render each with both pymermaid and mmdc
- Compare outputs visually (side-by-side PNG comparison)
- Log all discrepancies and visual defects
- Fix the most impactful issues found
- Focus areas: edge routing, text overflow, subgraph nesting, large diagrams, unusual syntax
