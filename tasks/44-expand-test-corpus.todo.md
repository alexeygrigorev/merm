# Task 44: Expand Test Corpus with All Supported Chart Types

## Goal

Expand `tests/fixtures/corpus/` with comprehensive fixtures for every supported diagram type, organized by chart type in separate folders. Also move the 5 real-world GitHub examples into the corpus.

## Current State

- `tests/fixtures/corpus/` only has flowchart fixtures (basic, direction, edges, scale, shapes, styling, subgraphs, text)
- `tests/fixtures/github/` has 5 real-world flowcharts (registration, coffee_machine, ci_pipeline, api_request, debug_loop)
- Supported renderers: flowchart, sequence, state, class_diagram
- NOT yet supported (parser fails): er, pie, gantt, mindmap, git_graph

## What to Add

### 1. Move GitHub examples into corpus
Move `tests/fixtures/github/*.mmd` → `tests/fixtures/corpus/flowchart/github/`

### 2. Reorganize flowchart fixtures
Move existing corpus subdirs under `tests/fixtures/corpus/flowchart/`:
- `flowchart/basic/`
- `flowchart/direction/`
- `flowchart/edges/`
- `flowchart/scale/`
- `flowchart/shapes/`
- `flowchart/styling/`
- `flowchart/subgraphs/`
- `flowchart/text/`
- `flowchart/github/` (from step 1)

### 3. Add sequence diagram fixtures
`tests/fixtures/corpus/sequence/`
- `basic.mmd` — simple Alice→Bob message exchange
- `arrows.mmd` — all arrow types (->>, -->, -x, -)
- `activations.mmd` — activate/deactivate blocks
- `notes.mmd` — notes over/right of participants
- `loops.mmd` — loop/alt/opt/par blocks
- `complex.mmd` — real-world-style API call sequence with multiple participants

### 4. Add state diagram fixtures
`tests/fixtures/corpus/state/`
- `basic.mmd` — simple state transitions with [*] start/end
- `nested.mmd` — composite/nested states
- `fork_join.mmd` — fork and join states
- `choice.mmd` — choice pseudostate (<<choice>>)
- `notes.mmd` — notes on states
- `complex.mmd` — real-world-style order processing state machine

### 5. Add class diagram fixtures
`tests/fixtures/corpus/class/`
- `basic.mmd` — simple inheritance (Animal <|-- Duck)
- `relationships.mmd` — all relationship types (inheritance, composition, aggregation, association, dependency)
- `members.mmd` — fields and methods with visibility (+, -, #, ~)
- `annotations.mmd` — <<interface>>, <<abstract>>, <<enumeration>>
- `complex.mmd` — real-world-style MVC or repository pattern with multiple classes

## Acceptance Criteria

- [ ] All fixtures render without errors: `render_diagram(open(f).read())` succeeds for every .mmd file
- [ ] All fixtures render to valid SVG (parseable by xml.etree)
- [ ] All fixtures render to PNG via cairosvg without errors
- [ ] Corpus organized by chart type: `corpus/{flowchart,sequence,state,class}/`
- [ ] At least 5 fixtures per non-flowchart chart type
- [ ] GitHub examples included under `corpus/flowchart/github/`
- [ ] Any existing test imports updated to reflect new paths
- [ ] `uv run pytest` passes with no regressions

### 6. Add icon/emoji edge case fixtures
`tests/fixtures/corpus/flowchart/icons/`
- `fa_icons.mmd` — Font Awesome icons (e.g. `fa:fa-tree` Christmas tree icon)
- `emoji.mmd` — Emoji characters in labels (e.g. nodes with rocket, checkmark, warning)
- `mixed.mmd` — Mix of text, icons, and emojis in same diagram

Note: These may not render correctly yet (task 31 covers emoji SVG support). The fixtures should exist so we can track rendering progress.

## Dependencies
- None
