# 15 - Class Diagram Support

## Goal
Add support for UML class diagrams. These reuse the Sugiyama layout engine since class hierarchies are directed graphs.

## Scope (MVP)

### In Scope
- `classDiagram` declaration
- Class definitions: `class Animal { +name: string\n +makeSound() }`
- Shorthand: `class Animal`, `Animal : +name string`, `Animal : +makeSound()`
- Relationships with arrows: `A <|-- B` (inheritance), `A *-- B` (composition), `A o-- B` (aggregation), `A --> B` (association), `A ..> B` (dependency), `A ..|> B` (realization)
- Labels on relationships: `A --> B : uses`
- Cardinality: `A "1" --> "*" B`
- Annotations: `<<interface>>`, `<<abstract>>`, `<<enumeration>>`
- Visibility markers: `+` public, `-` private, `#` protected, `~` package

### Deferred
- Namespaces
- Generic types
- Callbacks/links
- Styling with cssClass

## Implementation Plan

### 1. IR (`src/pymermaid/ir/classdiag.py`)
```python
class Visibility(Enum):
    PUBLIC = "+"
    PRIVATE = "-"
    PROTECTED = "#"
    PACKAGE = "~"

@dataclass(frozen=True)
class ClassMember:
    name: str
    type_str: str  # return type or field type
    visibility: Visibility
    is_method: bool  # True if has ()

@dataclass(frozen=True)
class ClassNode:
    id: str
    label: str
    annotation: str | None  # <<interface>>, etc.
    members: tuple[ClassMember, ...]

class RelationType(Enum):
    INHERITANCE = "inheritance"       # <|--
    COMPOSITION = "composition"       # *--
    AGGREGATION = "aggregation"       # o--
    ASSOCIATION = "association"       # -->
    DEPENDENCY = "dependency"         # ..>
    REALIZATION = "realization"       # ..|>

@dataclass(frozen=True)
class ClassRelation:
    source: str
    target: str
    rel_type: RelationType
    label: str = ""
    source_cardinality: str = ""
    target_cardinality: str = ""

@dataclass(frozen=True)
class ClassDiagram:
    classes: tuple[ClassNode, ...]
    relations: tuple[ClassRelation, ...]
```

### 2. Parser (`src/pymermaid/parser/classdiag.py`)
- `parse_class_diagram(text: str) -> ClassDiagram`
- Line-oriented, handle both block `class X { ... }` and shorthand `X : +method()` syntax
- Auto-create classes from relationship references

### 3. Layout
- Reuse Sugiyama layout by converting ClassDiagram to flowchart-style IR
- Each class becomes a node; each relation becomes an edge
- Node sizes: measure class box (name + divider + fields + divider + methods)

### 4. Renderer (`src/pymermaid/render/classdiag.py`)
- Three-section boxes: header (class name + annotation), fields section, methods section
- Horizontal divider lines between sections
- Visibility markers as text prefix
- Relationship-specific markers:
  - Inheritance: hollow triangle arrowhead
  - Composition: filled diamond
  - Aggregation: hollow diamond
  - Dependency: dashed line + open arrow
  - Realization: dashed line + hollow triangle
- Cardinality labels near endpoints

## Acceptance Criteria
- [ ] `parse_class_diagram()` handles class definitions, members, relationships, annotations
- [ ] Three-section class boxes render correctly (name, fields, methods)
- [ ] All 6 relationship types render with correct arrow markers
- [ ] Visibility markers displayed correctly
- [ ] Cardinality labels positioned near relationship endpoints
- [ ] Annotations (<<interface>>) displayed in class header
- [ ] Auto-creates class nodes from relationship references
- [ ] Layout produces non-overlapping diagram using Sugiyama
- [ ] Theme colors applied
- [ ] 25+ tests
- [ ] All existing tests still pass
- [ ] Lint passes

## Dependencies
- Tasks 01-13, 17-19 complete ✅

## Estimated Complexity
Medium — reuses layout engine, new parser + specialized renderer.
