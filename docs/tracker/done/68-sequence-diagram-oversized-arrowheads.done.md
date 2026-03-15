# Issue 68: Sequence diagram arrowheads too large and lines too thick

## Status: REOPENED — previous fix reduced marker dimensions but visual result still looks oversized

## Problem

Sequence diagram message arrows have disproportionately large arrowheads and thick lines.

## Root Cause

In `src/merm/render/sequence.py`:
- Marker dimensions were reduced from 10x7 to 6x4 but still look too large
- The message line stroke-width (2px) is too thick — mmdc uses ~1px
- The overall effect is heavy/bold rather than clean

## Fix Required

- Reduce stroke-width on message lines from 2 to 1 or 1.5
- Reduce marker dimensions further if needed (try 4x3)
- Adjust refX/refY for alignment

## Acceptance Criteria

- [ ] **MANDATORY PNG CHECK**: Render the diagram below to PNG, read the PNG, and visually confirm arrowheads are small and proportional
- [ ] Message lines should be thin (not bold/heavy) — stroke-width <= 1.5
- [ ] Arrowheads should be visually subordinate to the message text
- [ ] Self-message arrows still render correctly
- [ ] All existing tests pass

### Test diagram
```
sequenceDiagram
    Alice->>John: Hello John, how are you?
    loop HealthCheck
        John->>John: Fight against hypochondria
    end
```
