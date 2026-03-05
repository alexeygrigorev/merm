# Task 49: Git Graph Support

## Goal

Add parser, layout, and renderer for git graph diagrams.

## Example Input

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

## Scope

- Parse `gitGraph` blocks with commit, branch, checkout, merge commands
- Support commit ids and tags
- Support cherry-pick
- Layout commits as a horizontal timeline with branch lanes
- Render commit dots on branch lines
- Render merge lines between branches
- Color-code branches

## Acceptance Criteria

- [ ] `render_diagram(gitgraph_input)` returns valid SVG without errors
- [ ] Commits render as dots/circles on a horizontal timeline
- [ ] Branches render as separate horizontal lanes
- [ ] Branch lines have distinct colors
- [ ] `merge` renders a line connecting two branch lanes at the merge commit
- [ ] `checkout` switches the active branch for subsequent commits
- [ ] Commit tags/ids render as labels if specified
- [ ] At least 3 corpus fixtures in `tests/fixtures/corpus/gitgraph/`
- [ ] PNG verification: render each fixture and visually confirm branches, commits, and merges
- [ ] `uv run pytest` passes with no regressions

## Dependencies
- None
