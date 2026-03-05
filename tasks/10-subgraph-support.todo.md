# 10 - Subgraph Support

## Goal
Support subgraph parsing, layout, and rendering. Subgraphs group nodes visually with a labeled bounding box.

## Tasks

### Parser Integration
- [ ] Ensure parser (Task 04) correctly nests subgraphs in IR
- [ ] Resolve node membership (which nodes belong to which subgraph)
- [ ] Handle edges that cross subgraph boundaries

### Layout Integration
- [ ] Constrain nodes within the same subgraph to be grouped together
- [ ] Calculate subgraph bounding box after node positioning
- [ ] Add padding around subgraph contents (default: 20px)
- [ ] Support `direction` override within subgraphs
- [ ] Handle nested subgraphs (recursive layout)
- [ ] Handle edges between a subgraph label and a node

### Rendering
- [ ] Render subgraph as:
  - Background `<rect>` with rounded corners, light fill, dashed or solid border
  - Title `<text>` at top-left of bounding box
- [ ] Render in correct z-order: subgraph bg -> nodes -> edges
- [ ] Support subgraph styling via `classDef`

## Acceptance Criteria
- Nested subgraphs render correctly
- Nodes are visually contained within their subgraph
- Edges crossing subgraph boundaries route cleanly
- Title text is properly positioned

## Dependencies
- Task 04 (parser)
- Task 06 (layout)
- Task 07 (renderer)

## Estimated Complexity
Medium - requires changes across parser, layout, and renderer.
