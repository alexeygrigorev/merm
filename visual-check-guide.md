# Visual Check Guide

Known visual issues to watch for when making rendering changes. Each item describes what correct rendering looks like and what the broken version looks like. Use this as a regression checklist.

## 1. Arrowhead must be a sharp, pointy triangle

**Correct:** The arrowhead is a clean, sharp triangle — wide at the base, narrowing to a fine point at the tip. The path stroke line stops at the arrowhead base and does NOT continue through the triangle body. The arrowhead alone bridges the gap between the stroke line and the node border.

**Broken (stroke bleed-through):** The path stroke (2px wide) extends all the way through the arrowhead to the node border. Because the arrowhead triangle narrows to a point but the stroke stays 2px wide, the tip looks **blunt/stubby** — like a funnel with a rectangular stem poking out, instead of a sharp point. This is most visible when zoomed in.

**Root cause:** `_MARKER_SHORTEN=0` in `edges.py` means the path isn't pulled back before the arrowhead. The stroke line and arrowhead overlap, and the stroke is wider than the triangle at the tip.

**Fix:** `_MARKER_SHORTEN=8` (matching markerWidth) pulls the path back so the stroke stops at the arrowhead base. Combined with `refX=0` (base at path endpoint), the arrowhead extends forward from the stroke end to the node border.

**How to check:** Zoom in 6x on any arrowhead. It should be a clean triangle with a sharp point — no rectangular stem at the tip.

## 2. Arrowhead tip must touch target node (no gap)

**Correct:** The pointed tip of the arrowhead triangle touches the target node's border. No visible gap between the arrowhead and the node.

**Broken (gap):** The arrowhead floats in space, disconnected from the target node. This happens when the path is shortened but the marker refX doesn't compensate, or when refX is set incorrectly.

**How to check:** Zoom in 6x on any arrowhead where it meets a node. The sharp point should touch the node border.

## 3. Edge line must touch source node (no gap at start)

**Correct:** The edge path starts right at the source node's border. The line begins at the node edge — no gap between the node and the start of the line.

**Broken:** The line starts a few pixels away from the source node, leaving a visible gap. This can happen if `_shorten_start` is applied when there is no start marker, or if the layout computes incorrect start positions.

**How to check:** Look at where edges leave their source node. The line should begin flush with the node border.

## 4. Marker refX/refY must match the rendering approach

**Current approach:** `refX=0` (base at path endpoint) + `_MARKER_SHORTEN=8` (path pulled back by marker width). The arrowhead extends FORWARD from the shortened path end. The tip reaches the node boundary.

**Broken configurations:**
- `refX=10` + `_MARKER_SHORTEN=0`: Tip at endpoint, but stroke bleeds through arrowhead (blunt tip).
- `refX=10` + `_MARKER_SHORTEN=8`: Tip pulled back 8px from node (gap).
- `refX=0` + `_MARKER_SHORTEN=0`: Base at node boundary, tip extends 8px past the node (overshoots).

**How to check:** Verify in `edges.py` that `_MARKER_SHORTEN` equals `markerWidth` and `refX="0"` for arrow markers.

## 5. ER diagram must be compact (not oversized)

**Correct:** A 3-entity ER diagram (CUSTOMER, ORDER, LINE-ITEM) should fit in roughly 400x300px with entity boxes sized proportionally to their text content.

**Broken:** Entity boxes are 200px+ wide for short names, with excessive whitespace between entities. The diagram is 800x800+.

**How to check:** Render the basic 3-entity ER diagram. Total area should be under 400k px². Entity box width for "CUSTOMER" (no attributes) should be under 120px.

## 6. Edge labels must not overlap nodes or other labels

**Correct:** Edge labels (e.g. `|Text|` on flowchart edges) are positioned at the midpoint of the edge with a small background rectangle, and do not overlap with source/target nodes.

**Broken:** Labels overlap with node borders or sit on top of other labels, making text unreadable.

**How to check:** Render `flowchart LR` with edge labels. Labels should be clearly readable between nodes.

## 7. Sequence diagram arrowheads must be reasonably sized

**Correct:** Sequence diagram arrowhead markers are 8x8 with `markerUnits="userSpaceOnUse"`, matching flowchart arrow size.

**Broken (oversized):** Markers at 10x7 or larger look disproportionate on sequence message lines. **Broken (tiny):** Markers at 4x3 are barely visible.

**How to check:** Render a basic sequence diagram. Arrowheads should be visible but proportional to the line thickness.

## 8. State diagram [*] start/end nodes must be visually distinct

**Correct:** Start state `[*]` is a filled black circle (r=10). End state `[*]` is a double circle (outer ring + inner filled circle).

**Broken:** Start and end states look identical, or are rendered as regular state boxes.

**How to check:** Render a state diagram with both `[*] --> X` and `X --> [*]`. Verify start is solid black circle, end is bullseye (ring + filled center).

## 9. Bidirectional edges should not overlap

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
