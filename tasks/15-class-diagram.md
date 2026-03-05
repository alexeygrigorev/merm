# 15 - Class Diagram Support (Phase 3)

## Goal
Add support for UML class diagrams.

## Tasks

### Parser
- [ ] Parse `classDiagram` declaration
- [ ] Parse class definitions: `class Animal { +name: string, +makeSound() }`
- [ ] Parse relationships: inheritance, composition, aggregation, association
- [ ] Parse cardinality: `"1" --> "*"`
- [ ] Parse annotations: `<<interface>>`, `<<abstract>>`
- [ ] Parse namespaces

### IR Extensions
- [ ] `ClassNode` with fields (name, type, visibility) and methods
- [ ] `Relationship` with type enum and cardinality

### Layout
- [ ] Reuse Sugiyama layout from flowcharts (inheritance = rank direction)
- [ ] Class boxes sized to fit all fields and methods

### Rendering
- [ ] Three-section class boxes (name, fields, methods)
- [ ] Visibility markers (+, -, #, ~)
- [ ] Relationship-specific arrow markers (hollow triangle, diamond, etc.)
- [ ] Cardinality labels on edges

## Dependencies
- Phase 1 complete

## Estimated Complexity
Medium - reuses layout engine, needs specialized node rendering.
