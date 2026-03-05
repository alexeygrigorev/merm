# 14 - Sequence Diagram Support (Phase 2)

## Goal
Add support for sequence diagrams - the second most popular mermaid diagram type.

## Tasks

### Parser
- [ ] Parse `sequenceDiagram` declaration
- [ ] Parse participants: `participant A`, `actor B`
- [ ] Parse messages: `A->>B: message`, `A-->>B: message`, `A-xB: message`
- [ ] Parse activations: `activate A`, `deactivate A`, `+`/`-` shorthand
- [ ] Parse notes: `Note left of A: text`, `Note over A,B: text`
- [ ] Parse loops: `loop text ... end`
- [ ] Parse conditionals: `alt text ... else text ... end`
- [ ] Parse `opt`, `par`, `critical`, `break` blocks
- [ ] Parse `rect` background highlights

### IR Extensions
- [ ] `Participant` dataclass (name, alias, type: participant|actor)
- [ ] `Message` dataclass (from, to, text, type, activation)
- [ ] `Fragment` dataclass (type, label, messages) for loops/alt/opt

### Layout
- [ ] Participant placement: evenly spaced horizontal
- [ ] Timeline: messages placed vertically in order
- [ ] Lifeline rendering (dashed vertical lines)
- [ ] Activation box rendering (thin rectangles on lifelines)
- [ ] Fragment boxes (alt/loop/opt rectangles)
- [ ] Note positioning (left, right, over)

### Rendering
- [ ] Participant boxes/stick figures at top
- [ ] Lifeline dashed lines
- [ ] Message arrows (solid, dashed, with/without arrowhead)
- [ ] Activation rectangles
- [ ] Fragment boxes with labels
- [ ] Note boxes

## Dependencies
- Phase 1 complete (core infrastructure)

## Estimated Complexity
Large - different layout algorithm, new parser, new renderer components.
