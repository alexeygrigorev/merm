# Visual Check Guide

Known visual issues to watch for when making rendering changes. Each item describes what correct rendering looks like and what the broken version looks like. Use this as a regression checklist.

These rules apply to all diagram types unless noted otherwise.

## 1. Arrowheads must be sharp and pointy

The arrowhead is a clean, sharp triangle — wide at the base, narrowing to a fine point at the tip. The path stroke line stops at the arrowhead base and does NOT continue through the triangle body.

Broken: The stroke extends through the arrowhead, making the tip look blunt/stubby — like a funnel with a rectangular stem instead of a sharp point. Most visible when zoomed in.

How to check: Zoom in 6x on any arrowhead. It should be a clean triangle with a sharp point — no rectangular stem at the tip.

## 2. Arrowhead tip must touch target node

The pointed tip of the arrowhead touches the target node's border. No visible gap between the arrowhead and the node.

Broken: The arrowhead floats in space, disconnected from the target node.

How to check: Zoom in 6x on any arrowhead where it meets a node. The sharp point should touch the node border.

## 3. Edge line must touch source node

The edge path starts right at the source node's border. No gap between the node and the start of the line.

Broken: The line starts a few pixels away from the source node, leaving a visible gap.

How to check: Look at where edges leave their source node. The line should begin flush with the node border.

## 4. Arrowheads must be proportionally sized

Arrowheads should be large enough to be clearly visible, but small enough to look proportional to the stroke width and overall diagram scale. They should not dominate the diagram or be barely visible.

Broken (too large): Arrowheads dwarf the connecting lines, looking cartoonishly oversized.
Broken (too small): Arrowheads are tiny specks, barely distinguishable from the line end.

How to check: Render any diagram at 1x scale. Arrowheads should be noticeable but not distracting — roughly 3-5x the stroke width.

## 5. Diagram must be compact and reasonably sized

Diagrams should fit within a reasonable bounding box without excessive whitespace. Node boxes should be sized proportionally to their text content — short labels get small boxes, long labels get wider boxes.

Broken: Nodes are hundreds of pixels wide for short labels, or the diagram has huge empty gaps between elements, making the total area much larger than necessary.

How to check: Render a simple diagram (3-5 nodes). The result should look compact and balanced, not stretched out with wasted space.

## 6. Edge labels must not overlap nodes or other labels

Edge labels are positioned at the midpoint of the edge with a small background rectangle. They should not overlap with source/target nodes or other labels.

Broken: Labels overlap with node borders or sit on top of other labels, making text unreadable.

How to check: Render a diagram with edge labels. Labels should be clearly readable between nodes, not clipped or overlapping.

## 7. Nodes and text must not overlap each other

Nodes should be spaced far enough apart that they don't overlap. Text inside nodes should fit within the node boundaries.

Broken: Two nodes overlap visually, or text extends past the node border.

How to check: Render a diagram with several nodes. All nodes should have clear separation and all text should fit inside its container.

## 8. Start/end markers must be visually distinct

Special nodes like state diagram `[*]` start/end states should be visually distinct from regular nodes and from each other.

Broken: Start and end states look identical, or are rendered as regular boxes instead of circles.

How to check: Render a diagram with start/end markers. They should be immediately recognizable as different from normal nodes.

## 9. Bidirectional edges should be distinguishable

When two nodes have edges in both directions, both arrows should be visually distinguishable — ideally drawn as separate parallel paths.

Known limitation: Currently both paths may overlap on the same line. Both arrowheads are present but hard to see. Acceptable for now.

---

## How to Run the Visual Check

### Step 1: Render test diagrams to PNG at multiple zoom levels

```python
from merm import render_diagram
import cairosvg

diagrams = {
    "state": """stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
""",
    "flowchart_lr": """flowchart LR
    A[Hard] -->|Text| B(Round)
    B --> C{Decision}
    C -->|One| D[Result 1]
    C -->|Two| E[Result 2]
""",
    "flowchart_tb": """flowchart TB
    A[Start] --> B[Process]
    B --> C{Decision}
    C -->|Yes| D[End]
    C -->|No| B
""",
    "er": """erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
""",
    "sequence": """sequenceDiagram
    Alice->>John: Hello John, how are you?
    John-->>Alice: Great!
    Alice-)John: See you later!
""",
    "class": """classDiagram
    Animal <|-- Duck
    Animal <|-- Fish
    Animal : +int age
    Animal: +isMammal()
    Duck : +swim()
    Fish : +canEat()
""",
}

for name, text in diagrams.items():
    svg = render_diagram(text)
    # Normal scale (1x) — for overall layout check
    cairosvg.svg2png(bytestring=svg.encode(),
                     write_to=f".tmp/check/{name}_1x.png", scale=1)
    # 2x — for general visual check
    cairosvg.svg2png(bytestring=svg.encode(),
                     write_to=f".tmp/check/{name}_2x.png", scale=2)
    # 6x — for arrowhead detail check
    cairosvg.svg2png(bytestring=svg.encode(),
                     write_to=f".tmp/check/{name}_6x.png", scale=6)
```

### Step 2: Inspect each PNG with the Read tool

For each diagram, check:

At 1x scale (overall layout):
- [ ] Diagram is compact, no excessive whitespace
- [ ] Nodes don't overlap each other
- [ ] Text fits inside nodes
- [ ] Edge labels are readable and don't overlap nodes
- [ ] Start/end markers (if any) are visually distinct

At 2x scale (general quality):
- [ ] Arrowheads are clearly visible and proportional to line thickness
- [ ] Edge lines connect flush to source nodes (no gap at start)
- [ ] Arrowhead tips touch target nodes (no gap at end)

At 6x scale (arrowhead detail):
- [ ] Arrowheads are sharp, pointy triangles — no blunt/stubby tips
- [ ] No rectangular "stem" visible at the arrowhead tip
- [ ] The stroke line stops at the arrowhead base, not at the tip
- [ ] The arrowhead tip touches the node border cleanly

### Step 3: Check SVG structure (optional, for debugging)

If a visual issue is found, inspect the SVG source:

```python
import xml.etree.ElementTree as ET

svg = render_diagram(diagram_text)
root = ET.fromstring(svg)

# Check marker definitions
for marker in root.iter("{http://www.w3.org/2000/svg}marker"):
    print(f"id={marker.get('id')} refX={marker.get('refX')} "
          f"markerWidth={marker.get('markerWidth')}")

# Check diagram dimensions
print(f"width={root.get('width')} height={root.get('height')}")
```

Verify:
- Arrow markers have `refX="0"` (base at path endpoint)
- `_MARKER_SHORTEN` in `edges.py` equals `markerWidth` (currently 8)
- Edge path endpoints are shortened (not on node boundary)
