# Task 50: Class Diagram Rendering Quality

## Problem Statement

Class diagram rendering has five visual quality issues rooted in specific code defects across the renderer and layout modules.

## Root Cause Analysis

### Issue 1: Inheritance arrows are too large and poorly shaped

**File**: `/home/alexey/git/pymermaid/src/pymermaid/render/classdiag.py`, lines 133-149 (`_marker_triangle_hollow`)

The marker uses `markerUnits="strokeWidth"` (line 144), which scales the marker proportionally to the stroke width of the path. The flowchart edge markers in `/home/alexey/git/pymermaid/src/pymermaid/render/edges.py` correctly use `markerUnits="userSpaceOnUse"` (line 54). Additionally, the path `M0,0 L12,6 L0,12 Z` draws a right-pointing chevron, not a properly proportioned triangle -- the base and height are equal (12x12), making it look like a wide arrowhead rather than a compact UML inheritance triangle.

The same problem affects `_marker_diamond` (lines 152-168) and `_marker_open_arrow` (lines 171-187) -- all three use `markerUnits="strokeWidth"`.

### Issue 2: Parent class renders below children

**File**: `/home/alexey/git/pymermaid/src/pymermaid/layout/classdiag.py`, lines 24-48 (`class_diagram_to_flowchart`)

For inheritance `Animal <|-- Dog`, the parser correctly sets `source="Dog"`, `target="Animal"`. The `class_diagram_to_flowchart` function creates an Edge with `source=rel.source` ("Dog") and `target=rel.target` ("Animal"). In the Sugiyama layout, sources (nodes with no predecessors) get layer 0, which is the top in TB direction. Since Dog has no predecessors but Animal does (Dog -> Animal), Dog gets layer 0 (top) and Animal gets layer 1 (bottom). This inverts the expected hierarchy.

**Fix**: For inheritance and realization relationships, the edge direction in the flowchart IR should be reversed so that the parent class is the source (layer 0, top) and the child is the target (layer 1, bottom). The arrow marker should still point at the parent, so the marker-end needs to go on the correct end.

### Issue 3: Class boxes aren't evenly spaced/aligned

**File**: `/home/alexey/git/pymermaid/src/pymermaid/layout/classdiag.py`, lines 69-76 (`_class_measure`)

The custom measure function subtracts hardcoded padding values (`w - 30.0`, `h - 20.0`) that are supposed to cancel out the padding the Sugiyama layout adds (`_NODE_PADDING_H = 32.0`, `_NODE_PADDING_V = 16.0` in sugiyama.py). But 30 != 32 and 20 != 16 -- the mismatch causes inconsistent sizing. After layout, lines 84-97 re-center nodes using the actual measured sizes, but this post-hoc adjustment can shift nodes off the grid that Sugiyama computed.

### Issue 4: Relationship lines don't connect cleanly to class box edges

**File**: `/home/alexey/git/pymermaid/src/pymermaid/layout/classdiag.py`, lines 81-105

Edge routing happens inside `layout_diagram` (Sugiyama), which uses the original node sizes from the Sugiyama layout. Then `layout_class_diagram` adjusts node positions/sizes in lines 84-97 to match the actual class box dimensions. But the edge endpoints were already computed against the old positions/sizes, so edges no longer connect to the adjusted box boundaries.

**Fix**: Either (a) make the Sugiyama layout use the correct class box sizes from the start (avoid the subtract-then-readd dance), or (b) re-route edge endpoints after adjusting node positions.

### Issue 5: Member text alignment needs improvement

**File**: `/home/alexey/git/pymermaid/src/pymermaid/render/classdiag.py`, lines 279-306

The member text elements use a magic vertical offset of `-4` pixels (e.g., `div1_y + (i + 1) * _MEMBER_LINE_HEIGHT - 4`). This should use `dominant-baseline="central"` or `"middle"` for consistent cross-renderer vertical centering, with the y-coordinate set to the vertical center of each member row rather than using a fudge factor.

---

## Implementation Plan

### Step 1: Fix marker definitions (Issue 1)

In `/home/alexey/git/pymermaid/src/pymermaid/render/classdiag.py`:

1. In `_marker_triangle_hollow` (line 133): Change `markerUnits` from `"strokeWidth"` to `"userSpaceOnUse"`. Add a `viewBox` attribute. Reduce marker size to approximately 10x10 or smaller. Reshape the path to a more compact isoceles triangle (e.g., `M0,0 L10,5 L0,10 Z` with a viewBox of `0 0 10 10` and markerWidth/Height of 10).

2. In `_marker_diamond` (line 152): Same `markerUnits` fix. Verify diamond proportions look correct at the new scale.

3. In `_marker_open_arrow` (line 171): Same `markerUnits` fix.

### Step 2: Fix parent/child layer ordering (Issue 2)

In `/home/alexey/git/pymermaid/src/pymermaid/layout/classdiag.py`, function `class_diagram_to_flowchart` (line 36):

For inheritance (`<|--`, `--|>`) and realization (`..|>`) relationships, reverse the edge direction in the flowchart IR so that the **parent/interface is the source** and the **child/implementor is the target**. This puts the parent at layer 0 (top) in TB layout.

The relationship types that need reversal are: `RelationType.INHERITANCE` and `RelationType.REALIZATION`.

In the renderer (`_render_class_edge`), the marker must still point toward the parent. Since the edge direction is now parent->child in the layout but the arrow should point at the parent, use `marker-start` instead of `marker-end` for these reversed relationship types, or swap the edge points so the marker-end still points at the parent.

### Step 3: Fix class box sizing in layout (Issues 3 and 4)

In `/home/alexey/git/pymermaid/src/pymermaid/layout/classdiag.py`:

1. In `_class_measure` (line 69): Subtract the actual Sugiyama padding constants (`_NODE_PADDING_H = 32.0` and `_NODE_PADDING_V = 16.0`) instead of the hardcoded 30.0 and 20.0. Import these from `pymermaid.layout.sugiyama`.

2. Better approach: After `layout_diagram` returns, re-compute edge endpoints against the adjusted node positions. Add a helper function that takes the adjusted `NodeLayout` dict and re-routes each `EdgeLayout`'s first and last points to the boundaries of the adjusted class boxes using the same `_route_edge_on_boundary` logic.

### Step 4: Improve member text alignment (Issue 5)

In `/home/alexey/git/pymermaid/src/pymermaid/render/classdiag.py`, `_render_class_node` (lines 279-306):

Replace the `-4` magic offset with proper SVG text positioning. Set `dominant-baseline` to `"central"` on member text elements and position the y-coordinate at the vertical center of each row: `div_y + (i + 0.5) * _MEMBER_LINE_HEIGHT`.

### Step 5: Add corpus fixtures

Create `tests/fixtures/corpus/class/` directory with at least 5 `.mmd` fixtures:
- `inheritance.mmd` -- Animal with Duck/Fish/Zebra subclasses
- `all_relationships.mmd` -- all 6 relationship types
- `many_members.mmd` -- class with 8+ fields/methods
- `interface_realization.mmd` -- interface with implementing classes
- `cardinality.mmd` -- relationships with cardinality labels

---

## Acceptance Criteria

- [ ] `markerUnits` is set to `"userSpaceOnUse"` (not `"strokeWidth"`) for all class diagram markers in `_marker_triangle_hollow`, `_marker_diamond`, and `_marker_open_arrow`
- [ ] Inheritance triangle marker path defines a compact isoceles triangle (base height ratio roughly 1:1.2 or less), not a wide chevron
- [ ] For the Animal/Duck/Fish/Zebra inheritance diagram: Animal's `NodeLayout.y` is less than the `NodeLayout.y` of Duck, Fish, and Zebra (parent is above children in TB layout)
- [ ] The padding subtracted in `_class_measure` matches the actual Sugiyama `_NODE_PADDING_H` and `_NODE_PADDING_V` constants (no hardcoded 30.0/20.0 mismatch)
- [ ] Edge endpoints land on (or within 2px of) the adjusted class box boundaries -- verify by checking that each edge's first point is within 2px of the source node's bounding rect and last point is within 2px of the target node's bounding rect
- [ ] Member text elements use `dominant-baseline` for vertical centering (no magic `-4` offset)
- [ ] Composition (`*--`) markers render as filled diamonds; aggregation (`o--`) markers render as hollow diamonds (white fill); these are unchanged but verified not broken
- [ ] Dashed lines still render for dependency (`..>`) and realization (`..|>`) relationships
- [ ] At least 5 `.mmd` fixtures exist in `tests/fixtures/corpus/class/`
- [ ] `uv run pytest tests/test_classdiag.py` passes with no regressions
- [ ] `uv run pytest` passes with no regressions across the full test suite

## Test Scenarios

### Unit: Marker definitions

- Parse SVG output for an inheritance relationship; verify the `inherit-arrow` marker element has `markerUnits="userSpaceOnUse"`
- Parse SVG output; verify the inheritance marker path `d` attribute defines a closed triangle (ends with `Z`), with width <= 12 and height <= 12

### Unit: Parent-above-child layout

- Parse `classDiagram\n Animal <|-- Dog` and run layout; assert `layout.nodes["Animal"].y < layout.nodes["Dog"].y`
- Parse `classDiagram\n Animal <|-- Duck\n Animal <|-- Fish\n Animal <|-- Zebra` and run layout; assert Animal.y < min(Duck.y, Fish.y, Zebra.y)
- Verify the inheritance arrow marker still points toward the parent class (not away from it)

### Unit: Edge endpoint precision

- For a two-class inheritance diagram, verify that the first edge point's x is between `source.x` and `source.x + source.width`, and y is between `source.y` and `source.y + source.height` (within 2px tolerance)
- Same check for the last edge point against the target node

### Unit: Member text vertical alignment

- Parse SVG output for a class with members; verify member `<text>` elements have a `dominant-baseline` attribute set
- Verify no member text element has a y-offset that uses the literal value pattern `- 4` (the magic number is removed)

### Integration: Corpus fixtures

- Each `.mmd` file in `tests/fixtures/corpus/class/` parses without error
- Each fixture produces valid SVG output (parseable by `xml.etree.ElementTree`)

## Dependencies

- None (independent of flowchart fixes)
