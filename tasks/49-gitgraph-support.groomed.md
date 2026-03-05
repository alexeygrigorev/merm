# Task 49: Git Graph Support

## Goal

Add parser, IR, layout, and renderer for Mermaid `gitGraph` diagrams. The output is an SVG showing a horizontal timeline of commits across branch lanes, with merge lines connecting branches.

## Mermaid Syntax Reference

```
gitGraph
   commit
   commit id: "abc123"
   commit id: "feat-1" tag: "v1.0"
   commit type: HIGHLIGHT
   commit type: REVERSE
   branch develop
   checkout develop
   commit
   commit
   checkout main
   merge develop
   commit
   branch feature
   checkout feature
   commit
   cherry-pick id: "abc123"
   checkout develop
   merge feature
   checkout main
   merge develop tag: "v2.0"
```

### Supported Commands

| Command | Description |
|---------|-------------|
| `commit` | Add a commit to the current branch |
| `commit id: "ID"` | Commit with a named ID |
| `commit tag: "TAG"` | Commit with a tag label |
| `commit type: NORMAL\|REVERSE\|HIGHLIGHT` | Commit with visual type |
| `branch NAME` | Create a new branch from the current branch at the current commit |
| `checkout NAME` | Switch the active branch |
| `merge NAME` | Merge the named branch into the current branch |
| `merge NAME tag: "TAG"` | Merge with a tag on the merge commit |
| `cherry-pick id: "ID"` | Cherry-pick a specific commit by ID into the current branch |

### Comments

Lines starting with `%%` are comments and should be ignored.

## Architecture (Follow Existing Patterns)

Following the project's established module structure (as seen in ER, pie, class, state diagram implementations):

1. **IR** -- `src/pymermaid/ir/gitgraph.py` with frozen dataclasses
2. **Parser** -- `src/pymermaid/parser/gitgraph.py` producing the IR
3. **Layout** -- `src/pymermaid/layout/gitgraph.py` computing positions
4. **Renderer** -- `src/pymermaid/render/gitgraph.py` producing SVG
5. **Dispatch** -- Add `gitGraph` detection to `render_diagram()` in `src/pymermaid/__init__.py`

### IR Design (`src/pymermaid/ir/gitgraph.py`)

```python
class CommitType(Enum):
    NORMAL = "NORMAL"
    REVERSE = "REVERSE"
    HIGHLIGHT = "HIGHLIGHT"

@dataclass(frozen=True)
class GitCommit:
    id: str                          # auto-generated or user-specified
    branch: str                      # branch this commit belongs to
    commit_type: CommitType          # visual type
    tag: str                         # empty string if no tag
    parents: tuple[str, ...]         # parent commit IDs (2 for merges)
    is_merge: bool
    cherry_picked_from: str          # empty string if not a cherry-pick

@dataclass(frozen=True)
class GitBranch:
    name: str
    start_commit: str                # commit ID where the branch was created

@dataclass(frozen=True)
class GitGraph:
    commits: tuple[GitCommit, ...]   # in chronological order
    branches: tuple[GitBranch, ...]  # in creation order
    branch_order: tuple[str, ...]    # branch names in lane order (top to bottom)
```

### Layout Design (`src/pymermaid/layout/gitgraph.py`)

- Horizontal timeline: commits spaced evenly left-to-right in chronological order
- Branch lanes: each branch occupies a horizontal lane at a distinct y-coordinate
- Commit circles placed at `(x_index * spacing, branch_lane_y)`
- Branch lines: horizontal lines connecting consecutive commits on the same branch
- Merge lines: diagonal/straight lines from the last commit on the merged branch to the merge commit
- Cherry-pick lines: dashed diagonal lines from the source commit to the cherry-pick commit

Layout output should be a dataclass with positioned elements (commit positions, branch line segments, merge line segments).

### Renderer Design (`src/pymermaid/render/gitgraph.py`)

SVG elements:
- Branch lane lines: horizontal `<line>` or `<path>` elements, each branch a distinct color
- Commit nodes: `<circle>` elements on the branch line
  - NORMAL: filled circle in branch color
  - REVERSE: filled circle with inverted/contrasting color
  - HIGHLIGHT: filled circle with a larger radius or stroke
- Merge lines: `<line>` or `<path>` connecting two branch lanes
- Cherry-pick lines: dashed `<line>` or `<path>` connecting two branch lanes
- Commit labels: `<text>` elements showing commit IDs (when specified)
- Tag labels: `<text>` elements in a rounded-rect badge near the commit
- Branch labels: `<text>` elements at the start of each branch lane

### Branch Color Palette

Use a default palette of at least 8 distinct colors, cycling for additional branches. Follow Mermaid's default gitgraph theme colors.

### Dispatch Integration

Add to `src/pymermaid/__init__.py` before the default flowchart fallback:

```python
if re.match(r"^\s*gitGraph", source, re.MULTILINE):
    from pymermaid.parser.gitgraph import parse_gitgraph
    from pymermaid.layout.gitgraph import layout_gitgraph
    from pymermaid.render.gitgraph import render_gitgraph_svg

    graph = parse_gitgraph(source)
    layout = layout_gitgraph(graph, measure_fn=measurer.measure)
    return render_gitgraph_svg(graph, layout)
```

## Acceptance Criteria

- [ ] `from pymermaid.ir.gitgraph import GitCommit, GitBranch, GitGraph, CommitType` works
- [ ] `GitCommit`, `GitBranch`, `GitGraph` are frozen dataclasses
- [ ] `CommitType` enum has values `NORMAL`, `REVERSE`, `HIGHLIGHT`
- [ ] `from pymermaid.parser.gitgraph import parse_gitgraph` works
- [ ] `parse_gitgraph(source)` returns a `GitGraph` with correct commits, branches, and branch_order
- [ ] Parser handles `commit`, `commit id: "X"`, `commit tag: "X"`, `commit type: HIGHLIGHT`
- [ ] Parser handles `branch NAME`, `checkout NAME`, `merge NAME`, `merge NAME tag: "TAG"`
- [ ] Parser handles `cherry-pick id: "X"` and records the source commit ID
- [ ] Parser raises `ParseError` on invalid input (unknown command, cherry-pick of nonexistent ID, checkout of nonexistent branch)
- [ ] Parser ignores `%%` comment lines
- [ ] Auto-generated commit IDs are unique (e.g., `0-xxxxxxx` pattern or sequential)
- [ ] `from pymermaid.layout.gitgraph import layout_gitgraph` works
- [ ] Layout assigns each branch a distinct y-coordinate (lane)
- [ ] Layout assigns each commit an x-coordinate in chronological order
- [ ] `from pymermaid.render.gitgraph import render_gitgraph_svg` works
- [ ] `render_diagram(gitgraph_input)` returns valid SVG (parseable by `xml.etree.ElementTree`)
- [ ] SVG contains `<circle>` elements for commits
- [ ] SVG contains lines/paths for branch lanes
- [ ] SVG contains lines/paths connecting branches at merge points
- [ ] Branches have distinct stroke colors
- [ ] Commit tags render as visible text labels in the SVG
- [ ] Commit IDs (when user-specified) render as visible text labels in the SVG
- [ ] Branch names render as text labels at the left of each lane
- [ ] HIGHLIGHT commits are visually distinct (larger radius or thicker stroke)
- [ ] REVERSE commits are visually distinct (different fill color)
- [ ] Cherry-pick renders a dashed line from the source commit to the cherry-pick commit
- [ ] At least 3 corpus fixtures exist in `tests/fixtures/corpus/gitgraph/`
- [ ] `uv run pytest` passes with no regressions

## Test Scenarios

### Unit: IR dataclasses (`tests/test_gitgraph.py::TestIRDataclasses`)

- Create a `GitCommit` with all fields, verify attributes
- Create a `GitCommit` with defaults (empty tag, NORMAL type), verify defaults
- Verify `GitCommit` is frozen (assignment raises `FrozenInstanceError`)
- Create a `GitBranch`, verify `name` and `start_commit`
- Create a `GitGraph` with multiple commits and branches, verify tuple lengths
- Verify `CommitType` enum members: NORMAL, REVERSE, HIGHLIGHT

### Unit: Parser (`tests/test_gitgraph.py::TestParser`)

- Parse minimal gitGraph with a single commit on main
- Parse gitGraph with multiple commits, verify count and order
- Parse `commit id: "abc"`, verify the commit ID is "abc"
- Parse `commit tag: "v1.0"`, verify the tag is "v1.0"
- Parse `commit type: HIGHLIGHT`, verify commit_type is CommitType.HIGHLIGHT
- Parse `commit type: REVERSE`, verify commit_type is CommitType.REVERSE
- Parse `branch develop` followed by `checkout develop` and `commit`, verify commit is on "develop"
- Parse `merge develop`, verify the merge commit has two parents and `is_merge` is True
- Parse `cherry-pick id: "abc"`, verify `cherry_picked_from` is "abc"
- Parse gitGraph with `%%` comments, verify comments are ignored
- Parse empty gitGraph (just `gitGraph`), verify empty commits tuple
- Raise `ParseError` for `checkout nonexistent`
- Raise `ParseError` for `cherry-pick id: "nonexistent"`
- Raise `ParseError` for invalid command (e.g., `push origin main`)
- Parse `merge develop tag: "v2.0"`, verify merge commit has tag "v2.0"

### Unit: Layout (`tests/test_gitgraph.py::TestLayout`)

- Layout single-branch graph: all commits share the same y-coordinate
- Layout two-branch graph: branches have distinct y-coordinates
- Commits are assigned x-coordinates in strictly increasing order
- Merge commit x-coordinate is greater than the last commit on the merged branch
- Cherry-pick commit has correct position on the target branch

### Unit: Renderer (`tests/test_gitgraph.py::TestRenderer`)

- Render single-branch graph, SVG contains expected number of `<circle>` elements
- Render two-branch graph, SVG contains branch lane lines with distinct colors
- Render graph with merge, SVG contains a merge line/path connecting two lane y-coordinates
- Render graph with tag, SVG contains `<text>` element with the tag string
- Render graph with commit ID, SVG contains `<text>` element with the ID string
- Render HIGHLIGHT commit, SVG circle has larger radius or thicker stroke than NORMAL
- Render REVERSE commit, SVG circle has a different fill than NORMAL
- Render cherry-pick, SVG contains a dashed line/path

### Integration: `render_diagram()` dispatch (`tests/test_gitgraph.py::TestIntegration`)

- `render_diagram("gitGraph\n   commit\n")` returns valid SVG
- `render_diagram()` with a multi-branch input returns SVG with multiple lane colors
- All corpus fixtures in `tests/fixtures/corpus/gitgraph/` render without errors

### Corpus fixtures (`tests/fixtures/corpus/gitgraph/`)

Each fixture should render to valid SVG via `render_diagram()`.

## Test Fixtures

### `tests/fixtures/corpus/gitgraph/basic.mmd`

```
gitGraph
   commit
   commit
   commit
```

A linear history with 3 commits on main. Validates the simplest case.

### `tests/fixtures/corpus/gitgraph/branching.mmd`

```
gitGraph
   commit
   commit
   branch develop
   checkout develop
   commit
   commit
   checkout main
   merge develop
   commit
```

Two branches with a merge. The canonical gitgraph example from Mermaid docs.

### `tests/fixtures/corpus/gitgraph/complex.mmd`

```
gitGraph
   commit id: "init"
   commit id: "feat-1" tag: "v1.0"
   branch develop
   checkout develop
   commit id: "dev-1"
   commit id: "dev-2"
   branch feature
   checkout feature
   commit id: "f-1" type: HIGHLIGHT
   commit id: "f-2"
   checkout develop
   merge feature tag: "feature-done"
   commit id: "dev-3" type: REVERSE
   checkout main
   merge develop tag: "v2.0"
   commit id: "hotfix"
```

Three branches, merge chains, commit IDs, tags, and commit types. Exercises the full feature set.

### `tests/fixtures/corpus/gitgraph/cherry_pick.mmd`

```
gitGraph
   commit id: "base"
   branch develop
   checkout develop
   commit id: "important-fix"
   commit
   checkout main
   cherry-pick id: "important-fix"
   commit
```

Cherry-pick operation from develop to main. Validates cherry-pick parsing and rendering.

## Dependencies

- No task dependencies. The gitgraph diagram type is self-contained and does not share IR, parser, layout, or renderer code with other diagram types (same pattern as pie, ER, etc.).

## Scope Boundaries

**In scope:**
- `commit`, `branch`, `checkout`, `merge`, `cherry-pick` commands
- Commit IDs, tags, and types (NORMAL, REVERSE, HIGHLIGHT)
- Horizontal left-to-right timeline layout
- Branch lane coloring
- Merge and cherry-pick visual connections

**Out of scope (for this task):**
- `gitGraph LR` / `gitGraph TB` direction options (only LR for now)
- `order` directive on branches
- Custom theme colors via directive
- Rotated commit labels
- Interactive features (click handlers)
