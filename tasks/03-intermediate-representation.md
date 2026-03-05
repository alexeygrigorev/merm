# 03 - Intermediate Representation (IR) Data Model

## Goal
Define the core data structures that represent a parsed Mermaid diagram. All other modules operate on these types.

## Tasks

- [ ] Define `Diagram` dataclass - top-level container
  - `type`: DiagramType enum (flowchart, sequence, class, state, ...)
  - `direction`: Direction enum (TB, TD, BT, LR, RL)
  - `nodes`: list of Node
  - `edges`: list of Edge
  - `subgraphs`: list of Subgraph
  - `styles`: list of StyleDef
  - `classes`: dict mapping class names to style properties
- [ ] Define `Node` dataclass
  - `id`: str
  - `label`: str (may contain markdown/HTML)
  - `shape`: NodeShape enum (rect, rounded, stadium, subroutine, cylinder, circle, asymmetric, diamond, hexagon, parallelogram, parallelogram_alt, trapezoid, trapezoid_alt, double_circle)
  - `css_classes`: list[str]
  - `inline_style`: dict[str, str] | None
- [ ] Define `Edge` dataclass
  - `source`: str (node id)
  - `target`: str (node id)
  - `label`: str | None
  - `edge_type`: EdgeType enum (arrow, open, dotted, dotted_arrow, thick, thick_arrow, invisible)
  - `source_arrow`: ArrowType enum (none, arrow, circle, cross)
  - `target_arrow`: ArrowType enum
  - `extra_length`: int (number of extra dashes)
- [ ] Define `Subgraph` dataclass
  - `id`: str
  - `title`: str | None
  - `direction`: Direction | None (override)
  - `node_ids`: list[str]
  - `subgraphs`: list[Subgraph] (nested)
- [ ] Define `StyleDef` dataclass
  - `target_id`: str (node id or "default")
  - `properties`: dict[str, str]
- [ ] Define all enums: `DiagramType`, `Direction`, `NodeShape`, `EdgeType`, `ArrowType`

## Acceptance Criteria
- All types are importable from `pymermaid.ir`
- Types are immutable dataclasses or NamedTuples
- Unit tests verify construction and basic validation

## Dependencies
None - this is a leaf module.

## Estimated Complexity
Small - pure data definitions.
