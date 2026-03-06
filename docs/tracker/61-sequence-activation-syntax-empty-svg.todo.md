# Issue 61: Sequence diagram activation syntax produces empty SVG

## Problem

Sequence diagrams using Mermaid's `+`/`-` activation shorthand render as empty SVGs — only defs/styles are output, with no participants, lifelines, messages, or activations.

## Reproduction

```
tests/fixtures/corpus/sequence/activations.mmd
```

```
sequenceDiagram
    Alice->>+Bob: Hello Bob
    Bob->>+Charlie: Hi Charlie
    Charlie-->>-Bob: Reply
    Bob-->>-Alice: All done
```

The `+` prefix on a participant name (e.g. `->>+Bob`) means "activate Bob". The `-` prefix (e.g. `-->>-Bob`) means "deactivate Bob".

## Expected behavior

- Parser strips `+`/`-` from participant names and records activate/deactivate events
- Renderer draws activation boxes on lifelines
- All participants, messages, and lifelines render correctly

## Acceptance criteria

- [ ] activations.mmd renders with all 3 participants visible
- [ ] All 4 messages render with arrows and labels
- [ ] Activation boxes appear on lifelines
- [ ] Other sequence diagrams not broken
- [ ] Visual verification via PNG rendering
