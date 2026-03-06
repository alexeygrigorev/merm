# Development Process

## Overview

We use file-based issue tracking in `docs/tracker/`. Four agents handle the lifecycle: PM grooms, Engineer implements, Tester verifies, PM accepts.

Terminology:
- Issue = a file in `docs/tracker/` describing work to be done (bug fix, feature, etc.)
- Task = a Claude Code task panel item tracking pipeline steps within the current session

## Issue Lifecycle

```
PM grooms (.todo)  ->  Engineer builds (.in-progress)  ->  Tester verifies  ->  PM accepts (.done)
```

### File-Based Status

Issue status is encoded in the filename:

| Status | Filename Pattern | Meaning |
|--------|-----------------|---------|
| Todo | `01-name.todo.md` | Not started, needs PM grooming before pickup |
| Groomed | `01-name.groomed.md` | PM has groomed, ready for engineer |
| In Progress | `01-name.in-progress.md` | Engineer is working on it |
| Done | `01-name.done.md` | PM accepted, complete |

### Status Transitions

```
.todo.md  -->  PM grooms  -->  .groomed.md  -->  Engineer picks up  -->  .in-progress.md
                                                      |
                                              Engineer done + Tester pass + PM accept
                                                      |
                                                      v
                                                 .done.md
```

## Agent Workflow

The orchestrator (top-level Claude Code session) drives the process:

1. PM Grooms: Pick `.todo.md` issues, add acceptance criteria and test scenarios, rename to `.groomed.md`
2. Pick 2 issues: Select the lowest-numbered `.groomed.md` issues whose dependencies are met
3. Engineer implements: Write code + tests, rename to `.in-progress.md`
4. Tester reviews: Run tests, verify acceptance criteria, report pass/fail
5. If fail: Engineer fixes, tester re-reviews (repeat)
6. If pass: PM does acceptance review
7. If PM rejects: Engineer fixes, PM re-reviews
8. If PM accepts: Rename to `.done.md`, commit
9. Pick next 2 issues and repeat

## Agents

| Agent | File | Role |
|-------|------|------|
| Product Manager | `.claude/agents/product-manager.md` | Grooms issues + final acceptance |
| Software Engineer | `.claude/agents/software-engineer.md` | Implements code + tests |
| Tester | `.claude/agents/tester.md` | Runs tests, verifies acceptance criteria |

## Technology Stack

- Language: Python 3.10+
- Package manager: uv
- Testing: pytest
- Linting: ruff

## How to Pick Issues

1. List `.groomed.md` files in `docs/tracker/`
2. Pick the lowest-numbered issues first (lower = more foundational)
3. Check dependencies -- don't start until deps are `.done.md`
4. Pick 2 independent issues at a time for parallel implementation

## Visual Verification (Critical)

For any issue that changes rendering or SVG output:

1. SVG alone is NOT sufficient -- SVG source can look structurally correct but render incorrectly
2. Always render to PNG with cairosvg and visually inspect the result
3. PM must include PNG verification in acceptance criteria during grooming
4. Tester must render to PNG and view the actual image, not just check SVG structure
5. PM rejects any rendering issue where PNG verification was not performed

### Common visual issues to check:
- Text clipping outside viewport
- Text overflow outside shapes
- Arrowheads penetrating nodes
- Subgraph titles clipped
- Empty nodes (text missing)
- Overlapping text lines

## Task Panel (Claude Code Built-in Tasks)

The orchestrator MUST use the Claude Code task panel to track every step of the pipeline. Tasks are session-scoped progress trackers -- they are NOT the same as issues in `docs/tracker/`.

### How Task Panel Items Should Look

Each task panel item tracks a pipeline step for a batch of issues:

| Task Subject | Example |
|---|---|
| `[PM groom] issues #59, #60` | PM grooming step |
| `[SWE] implement issues #59, #60` | Engineering step |
| `[QA] verify issues #59, #60` | Testing step |
| `[PM accept] issues #59, #60` | Acceptance + commit step |
| `[Pull next] pick 2 issues from backlog` | Pick up more work |

### Setting Up a Batch

When starting work on a batch of issues, create task panel items for the full pipeline:

1. `[PM groom] issues #N, #M`
2. `[SWE] implement issues #N, #M`
3. `[QA] verify issues #N, #M`
4. `[PM accept] issues #N, #M -> commit`
5. `[Pull next] pick 2 issues from backlog`

Set up blockedBy dependencies so each step waits for the previous one. Mark each item `in_progress` when starting it and `completed` when done.

### Pipeline Per Batch

```
[PM groom] -> [SWE] Implement -> [QA] Test -> [PM accept] -> Commit -> [Pull next]
                  ^                              |
                  +---- Reject (back to SWE) ----+
```

### Task Panel Tags

| Panel Tag | Agent | When | What happens |
|-----------|-------|------|-------------|
| `[PM groom]` | Product Manager | BEFORE implementation | Adds acceptance criteria, PNG verification checklist, test scenarios. Renames .todo -> .groomed |
| `[SWE]` | Software Engineer | After grooming | Implements code + tests (TDD: failing test first). Renames .groomed -> .in-progress |
| `[QA]` | Tester | After implementation | Verifies acceptance criteria, renders to PNG and visually inspects. Pass/Fail |
| `[PM accept]` | Product Manager | AFTER QA passes | Final review. Renders PNGs independently. Accept -> .done + commit. Reject -> back to SWE to finish |
| `[Pull next]` | Orchestrator | AFTER commit | Check docs/tracker/ for remaining .todo/.groomed files. Pick 2 lowest-numbered, create new batch in task panel, repeat |

PM has two distinct roles:
1. Before engineering: groom the issue (define what "done" looks like)
2. After QA: accept or reject (verify it actually looks right). Reject sends it back to engineer for finishing, NOT back to grooming.

### Pull Next Work

The last item in every batch is always "[Pull next] pick 2 issues from backlog". This ensures work continues automatically:
1. Check `docs/tracker/` for `.todo.md` or `.groomed.md` files
2. Pick the 2 lowest-numbered groomed issues (groom first if only .todo.md)
3. Create a new batch of task panel items with dependencies
4. Start the pipeline again

## Conventions

- Every issue must include pytest tests
- Tests run with `uv run pytest`
- Lint with `uv run ruff check`
- Commit message references issue: "Implement issue 01: project setup"
- Only commit after PM accepts
- Issues are NEVER deleted -- they move through statuses (.todo -> .groomed -> .in-progress -> .done)
- Commit regularly -- don't accumulate large uncommitted changes
