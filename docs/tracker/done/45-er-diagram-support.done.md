# Task 45: ER Diagram Support

## Problem Statement

pymermaid supports flowcharts, sequence diagrams, class diagrams, and state diagrams but has no support for Entity-Relationship (ER) diagrams. ER diagrams are a common diagram type used to model database schemas, showing entities, their attributes, and the relationships between them. Mermaid's `erDiagram` syntax is widely used and should be supported end-to-end: parsing, IR, layout, and SVG rendering.

## Scope

Add full `erDiagram` support following the established pattern used by `classDiagram` and `stateDiagram`:

1. **IR dataclasses** in `src/pymermaid/ir/erdiag.py`
2. **Parser** in `src/pymermaid/parser/erdiag.py`
3. **Layout** in `src/pymermaid/layout/erdiag.py`
4. **Renderer** in `src/pymermaid/render/erdiag.py`
5. **Dispatch** wired into `render_diagram()` in `src/pymermaid/__init__.py`
6. **Test fixtures** in `tests/fixtures/corpus/er/`

## ER Diagram Syntax Reference

### Declaration

```
erDiagram
```

### Entities with Attributes

Entities are defined by a name followed by a block of typed attributes:

```
CUSTOMER {
    string name
    int age
    string email PK
    string address
}
```

Each attribute line has the form: `type name [key]` where key is optional and can be `PK`, `FK`, or `UK` (primary key, foreign key, unique key). Entities referenced in relationships that have no attribute block are still valid (rendered as empty boxes).

### Relationships

Format: `ENTITY1 [left-cardinality][line-style][right-cardinality] ENTITY2 : label`

Cardinality markers (at each end of the line):

| Marker | Meaning |
|--------|---------|
| `\|\|` | Exactly one |
| `o\|` | Zero or one |
| `\|{` | One or more |
| `o{` | Zero or more |
| `}o` | Zero or more (right side) |
| `}\|` | One or more (right side) |
| `\|o` | Zero or one (right side) |
| `\|\|` | Exactly one (right side) |

Line style:

| Syntax | Meaning |
|--------|---------|
| `--` | Solid line (identifying relationship) |
| `..` | Dashed line (non-identifying relationship) |

Full relationship examples:

```
CUSTOMER ||--o{ ORDER : places
ORDER ||--|{ LINE-ITEM : contains
CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
PERSON ||--|| PASSPORT : "has exactly one"
STUDENT }o--o{ CLASS : enrolls
```

### Comments

Lines starting with `%%` are comments and should be ignored.

## Implementation Plan

### Step 1: IR Dataclasses (`src/pymermaid/ir/erdiag.py`)

Define the following frozen dataclasses:

- `ERAttributeKey` enum: `NONE`, `PK`, `FK`, `UK`
- `ERAttribute(type_str: str, name: str, key: ERAttributeKey)`
- `EREntity(id: str, attributes: tuple[ERAttribute, ...])`
- `ERCardinality` enum: `EXACTLY_ONE`, `ZERO_OR_ONE`, `ONE_OR_MORE`, `ZERO_OR_MORE`
- `ERLineStyle` enum: `SOLID`, `DASHED`
- `ERRelationship(source: str, target: str, source_cardinality: ERCardinality, target_cardinality: ERCardinality, line_style: ERLineStyle, label: str)`
- `ERDiagram(entities: tuple[EREntity, ...], relationships: tuple[ERRelationship, ...])`

Update `src/pymermaid/ir/__init__.py` to re-export these types.

### Step 2: Parser (`src/pymermaid/parser/erdiag.py`)

Implement `parse_er_diagram(text: str) -> ERDiagram` following the same pattern as `parse_class_diagram`:

1. Preprocess: strip comments (`%%`), join multi-line entity blocks
2. Validate `erDiagram` declaration on first non-empty line
3. Parse entity attribute blocks: `ENTITY_NAME { ... }`
4. Parse relationship lines: regex matching cardinality markers, line style, entity names, and label
5. Auto-create entities referenced in relationships but not explicitly defined

Relationship regex should handle all combinations of left-cardinality + line-style + right-cardinality. The key parsing challenge is the cardinality markers which use `|`, `o`, `{`, `}` characters in specific combinations.

Update `src/pymermaid/parser/__init__.py` to export `parse_er_diagram`.

### Step 3: Layout (`src/pymermaid/layout/erdiag.py`)

Implement `layout_er_diagram(diagram: ERDiagram, measure_fn: MeasureFn) -> LayoutResult`:

1. Convert `ERDiagram` to a flowchart `Diagram` IR (same approach as `class_diagram_to_flowchart`)
2. Use a custom measure function that computes entity box sizes based on attribute count
3. Delegate to the Sugiyama layout engine
4. Adjust node sizes post-layout to match measured entity box dimensions
5. Re-route edge endpoints to entity box boundaries

Entity box sizing: header (entity name) + one line per attribute, with horizontal padding.

### Step 4: Renderer (`src/pymermaid/render/erdiag.py`)

Implement `render_er_diagram(diagram: ERDiagram, layout: LayoutResult, theme: Theme | None = None) -> str`:

1. Create SVG root element with viewBox
2. Define SVG markers for cardinality notation at line endpoints:
   - Exactly one: a short perpendicular line (single bar `|`)
   - Zero or one: circle + perpendicular line
   - One or more: crow's foot (three lines spreading out) + perpendicular line
   - Zero or more: crow's foot + circle
3. Render each entity as a rectangle with:
   - Header section with entity name (bold)
   - Divider line
   - Attribute list with `type name` and optional key badge/marker
4. Render each relationship as a line/path with:
   - Cardinality markers at both endpoints
   - Solid or dashed line style
   - Label text centered on the line
5. CSS class names: `.er-entity`, `.er-relationship`

### Step 5: Wire into `render_diagram()`

Add a regex match for `erDiagram` in `src/pymermaid/__init__.py` dispatching to the ER pipeline (import parser, layout, renderer lazily, same as class/state diagrams).

### Step 6: Test Fixtures

Create at least 5 `.mmd` fixture files in `tests/fixtures/corpus/er/`.

## Acceptance Criteria

- [ ] `from pymermaid.ir.erdiag import ERDiagram, EREntity, ERAttribute, ERRelationship, ERCardinality, ERLineStyle, ERAttributeKey` works without error
- [ ] `parse_er_diagram("erDiagram\n    CUSTOMER ||--o{ ORDER : places")` returns an `ERDiagram` with 2 entities and 1 relationship
- [ ] All 6 cardinality markers parse correctly: `||` (exactly one), `o|` (zero or one), `|{` (one or more), `o{` (zero or more), and their right-side mirrors `}|`, `}o`, `|o`, `||`
- [ ] Both line styles parse correctly: `--` (solid/identifying) and `..` (dashed/non-identifying)
- [ ] Entity attributes parse with type, name, and optional key: `string name PK` produces `ERAttribute(type_str="string", name="name", key=ERAttributeKey.PK)`
- [ ] Entities referenced only in relationships (no attribute block) are auto-created with empty attribute lists
- [ ] `render_diagram(er_source)` returns a valid SVG string (contains `<svg` and `</svg>`)
- [ ] The rendered SVG contains a `<rect>` for each entity
- [ ] The rendered SVG contains a `<text>` element with the entity name for each entity
- [ ] The rendered SVG contains a `<path>` or `<line>` for each relationship
- [ ] Relationship labels appear as `<text>` elements in the SVG
- [ ] Entity attributes render inside entity boxes showing `type name`
- [ ] PK/FK/UK key markers render visually distinct from non-key attributes
- [ ] Cardinality markers render at both endpoints of relationship lines (via SVG markers or inline shapes)
- [ ] Dashed line style (`..`) renders with `stroke-dasharray` on the relationship path
- [ ] At least 5 corpus fixtures exist in `tests/fixtures/corpus/er/`
- [ ] `uv run pytest` passes with no regressions
- [ ] Comments (`%%`) in ER diagram source are ignored during parsing

## Test Scenarios

### Unit: IR dataclasses

- Create an `ERAttribute` with all fields, verify attributes
- Create an `ERAttribute` with `key=ERAttributeKey.NONE` (default), verify
- Create an `EREntity` with multiple attributes, verify tuple
- Create an `ERRelationship` with all cardinality/line combinations
- Create an `ERDiagram` with entities and relationships, verify fields

### Unit: Parser - entity blocks

- Parse entity with 3 attributes, verify types and names
- Parse entity with PK/FK/UK keys on attributes
- Parse entity with no attributes (empty block `ENTITY { }`)
- Parse entity referenced only in a relationship (auto-created, empty attributes)
- Parse multiple entities in one diagram

### Unit: Parser - relationships

- Parse `CUSTOMER ||--o{ ORDER : places` -- verify source/target, cardinalities, label
- Parse `A ||--|{ B : contains` -- one-to-one-or-more, solid
- Parse `A }|..|{ B : uses` -- one-or-more to one-or-more, dashed
- Parse `A ||--|| B : has` -- one-to-one, solid
- Parse `A }o--o{ B : enrolls` -- zero-or-more to zero-or-more, solid
- Parse `A o|--|| B : belongs` -- zero-or-one to exactly-one, solid
- Parse relationship with quoted label: `A ||--o{ B : "has many"`

### Unit: Parser - edge cases

- Empty `erDiagram` (declaration only, no entities/relationships) returns empty diagram
- Lines with `%%` comments are skipped
- Entity names with hyphens: `LINE-ITEM` should be valid
- Whitespace variations (extra spaces, tabs) parse correctly

### Unit: Layout

- Layout a 2-entity, 1-relationship diagram -- both entities get positioned (non-overlapping)
- Layout a 4-entity diagram -- all entities have non-zero width/height
- Entity box height scales with number of attributes

### Integration: Full pipeline

- `render_diagram("erDiagram\n    CUSTOMER ||--o{ ORDER : places")` produces valid SVG
- Render each of the 5 corpus fixtures without errors
- Rendered SVG of a 3-entity diagram contains exactly 3 `<rect>` elements (entity boxes)
- Rendered SVG contains relationship label text

## Test Fixtures

Create these files in `tests/fixtures/corpus/er/`:

### `basic.mmd`
```
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
```

### `attributes.mmd`
```
erDiagram
    CUSTOMER {
        string name
        int age
        string email PK
    }
    ORDER {
        int id PK
        date created
        string status
    }
    CUSTOMER ||--o{ ORDER : places
```

### `all_cardinalities.mmd`
```
erDiagram
    A ||--|| B : "one to one"
    C ||--o{ D : "one to zero-or-more"
    E ||--|{ F : "one to one-or-more"
    G }o--o{ H : "zero-or-more to zero-or-more"
    I o|--|| J : "zero-or-one to one"
```

### `dashed_lines.mmd`
```
erDiagram
    PERSON ||..o{ CAR : "may own"
    PERSON }|..|{ ADDRESS : "lives at"
    COMPANY ||..|| HEADQUARTERS : occupies
```

### `complex.mmd`
```
erDiagram
    CUSTOMER {
        string name PK
        string email UK
        int age
    }
    ORDER {
        int id PK
        date created
        float total
        string status
    }
    LINE-ITEM {
        int id PK
        int quantity
        float price
    }
    PRODUCT {
        int id PK
        string name
        string category
        float price
    }
    DELIVERY-ADDRESS {
        int id PK
        string street
        string city
        string zip
    }
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    LINE-ITEM }o--|| PRODUCT : "refers to"
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
    CUSTOMER ||--|| DELIVERY-ADDRESS : "has primary"
```

## Dependencies

- Task 03 (IR) -- done
- Task 06 (Sugiyama layout) -- done
- Task 07 (SVG renderer core) -- done
- Task 15 (Class diagram) -- done (establishes the pattern to follow)
