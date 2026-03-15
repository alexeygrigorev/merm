# Visual Check Guide

Known visual issues to watch for when making rendering changes. Each item describes what correct rendering looks like and what the broken version looks like. Use this as a regression checklist.

## 1. Arrowhead tip must touch target node (no gap)

**Correct:** The pointed tip of the arrowhead triangle touches the target node's border with no visible gap.

**Broken (refX=0):** The arrowhead BASE is at the node border and the TIP floats 8px away in space. This was the original bug — `refX` must equal the tip x-coordinate in the viewBox (refX=10 for polygon `M 0 0 L 10 5 L 0 10 z`).

**Diagrams affected:** All (flowchart, state, class, ER, sequence).

**How to check:** Zoom in 6x on any arrowhead. The pointed tip should visually touch the node border.

## 2. Path stroke must not extend through arrowhead tip

**Correct:** The edge path line stops at the arrowhead BASE. Only the filled arrowhead triangle reaches the node border. The arrowhead is a clean triangle shape.

**Broken (_MARKER_SHORTEN=0):** The path stroke (2px wide) extends all the way through the arrowhead to the node border. At the narrow arrowhead tip, the 2px stroke is wider than the triangle, creating a visible rectangular "stem" that pokes through the arrowhead and into the node. Most visible on vertical/diagonal arrows at >2x zoom.

**Diagrams affected:** All (flowchart, state, class, ER).

**How to check:** Zoom in 6x on any arrowhead. The path line should stop at the wide base of the arrowhead, not continue through to the tip.

**Fix:** Set `_MARKER_SHORTEN` in `edges.py` to the marker width (8) so the path is pulled back by the arrowhead length.

## 3. ER diagram must be compact (not oversized)

**Correct:** A 3-entity ER diagram (CUSTOMER, ORDER, LINE-ITEM) should fit in roughly 400x300px with entity boxes sized proportionally to their text content.

**Broken:** Entity boxes are 200px+ wide for short names, with excessive whitespace between entities. The diagram is 800x800+.

**Diagrams affected:** ER diagrams.

**How to check:** Render the basic 3-entity ER diagram. Total area should be under 400k px². Entity box width for "CUSTOMER" (no attributes) should be under 120px.

## 4. Edge labels must not overlap nodes or other labels

**Correct:** Edge labels (e.g. `|Text|` on flowchart edges) are positioned at the midpoint of the edge with a small background rectangle, and do not overlap with source/target nodes.

**Broken:** Labels overlap with node borders or sit on top of other labels, making text unreadable.

**Diagrams affected:** Flowchart (especially LR direction), class diagrams.

**How to check:** Render `flowchart LR` with edge labels. Labels should be clearly readable between nodes.

## 5. Sequence diagram arrowheads must be reasonably sized

**Correct:** Sequence diagram arrowhead markers are 8x8 with `markerUnits="userSpaceOnUse"`, matching flowchart arrow size. refX=10 so tips touch lifelines.

**Broken (oversized):** Markers at 10x7 or larger look disproportionate on sequence message lines. **Broken (tiny):** Markers at 4x3 are barely visible.

**Diagrams affected:** Sequence diagrams.

**How to check:** Render a basic sequence diagram. Arrowheads should be visible but proportional to the line thickness.

## 6. Marker refX/refY must match polygon geometry

**Correct:** `refX` equals the x-coordinate of the arrowhead tip in the viewBox coordinate system. For polygon `M 0 0 L 10 5 L 0 10 z`, refX=10, refY=5. This places the tip at the path endpoint.

**Broken:** refX=0 places the base at the path endpoint (arrowhead floating). refX=5 places the midpoint at the path endpoint (arrowhead half-penetrating node).

**How to check:** In the SVG `<marker>` element, verify refX equals `max(x-coords)` of the polygon points, and refY equals `viewBox_height / 2`.

## 7. State diagram [*] start/end nodes must be visually distinct

**Correct:** Start state `[*]` is a filled black circle (r=10). End state `[*]` is a double circle (outer ring + inner filled circle).

**Broken:** Start and end states look identical, or are rendered as regular state boxes.

**How to check:** Render a state diagram with both `[*] --> X` and `X --> [*]`. Verify start is solid black circle, end is bullseye (ring + filled center).

## 8. Bidirectional edges should not overlap

**Correct:** When two states have edges in both directions (e.g. `Still --> Moving` and `Moving --> Still`), the two edges should be drawn as separate parallel paths so both arrowheads are visible.

**Known limitation:** Currently both paths are drawn on the same line, causing visual overlap. Both arrowheads are present but the edges share the same path. This is acceptable for now but should be improved in the future.

---

## Quick Visual Regression Test

Render these diagrams and inspect at 2x and 6x zoom:

```
stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
```

```
flowchart LR
    A[Hard] -->|Text| B(Round)
    B --> C{Decision}
    C -->|One| D[Result 1]
    C -->|Two| E[Result 2]
```

```
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
```

```
sequenceDiagram
    Alice->>John: Hello John, how are you?
    John-->>Alice: Great!
    Alice-)John: See you later!
```
