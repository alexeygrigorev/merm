# Development Process

## Overview

We use file-based task tracking in `tasks/`. Four agents handle the lifecycle: PM grooms, Engineer implements, Tester verifies, PM accepts.

## Task Lifecycle

```
PM grooms (.todo)  ->  Engineer builds (.in-progress)  ->  Tester verifies  ->  PM accepts (.done)
```

### File-Based Status

Task status is encoded in the filename:

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

1. **PM Grooms**: Pick `.todo.md` tasks, add acceptance criteria and test scenarios, rename to `.groomed.md`
2. **Pick 2 tasks**: Select the lowest-numbered `.groomed.md` tasks whose dependencies are met
3. **Engineer implements**: Write code + tests, rename to `.in-progress.md`
4. **Tester reviews**: Run tests, verify acceptance criteria, report pass/fail
5. **If fail**: Engineer fixes, tester re-reviews (repeat)
6. **If pass**: PM does acceptance review
7. **If PM rejects**: Engineer fixes, PM re-reviews
8. **If PM accepts**: Rename to `.done.md`, commit
9. **Pick next 2 tasks** and repeat

## Agents

| Agent | File | Role |
|-------|------|------|
| Product Manager | `.claude/agents/product-manager.md` | Grooms tasks + final acceptance |
| Software Engineer | `.claude/agents/software-engineer.md` | Implements code + tests |
| Tester | `.claude/agents/tester.md` | Runs tests, verifies acceptance criteria |

## Technology Stack

- Language: Python 3.10+
- Package manager: uv
- Testing: pytest
- Linting: ruff
- Reference renderer: Node.js + @mermaid-js/mermaid-cli (for comparison tests)

## How to Pick Tasks

1. List `.groomed.md` files in `tasks/`
2. Pick the lowest-numbered tasks first (lower = more foundational)
3. Check dependencies — don't start until deps are `.done.md`
4. Pick 2 independent tasks at a time for parallel implementation

## Visual Verification (Critical)

For any task that changes rendering or SVG output:

1. **SVG alone is NOT sufficient** — SVG source can look structurally correct but render incorrectly
2. **Always render to PNG** with cairosvg and visually inspect the result
3. **PM must include PNG verification** in acceptance criteria during grooming
4. **Tester must render to PNG** and view the actual image, not just check SVG structure
5. **PM rejects** any rendering task where PNG verification was not performed

### Common visual issues to check:
- Text clipping outside viewport
- Text overflow outside shapes
- Arrowheads penetrating nodes
- Subgraph titles clipped
- Empty nodes (text missing)
- Overlapping text lines

## Task List (Claude Code Task Panel)

The orchestrator MUST use the Claude Code **task list** (task panel) to track every step of the pipeline. This provides visibility into what's happening and what's next.

### Setting Up a Batch

When starting work on a batch of tasks, create task list items for the full pipeline:

1. `PM groom tasks N+M` — grooming step
2. `SWE implement tasks N+M (TDD)` — engineering step
3. `QA verify tasks N+M` — testing step
4. `PM accept tasks N+M → commit` — acceptance + commit step
5. `Pull next 2 tasks from backlog` — pick up more work

Set up **blockedBy** dependencies so each step waits for the previous one. Mark each item `in_progress` when starting it and `completed` when done.

### Pipeline Per Batch

```
[PM groom] → [SWE] Implement → [QA] Test → [PM accept] → Commit → [Pull next 2]
                  ↑                              |
                  └──── Reject (back to SWE) ────┘
```

### Task Panel Tags

| Panel Tag | Agent | When | What happens |
|-----------|-------|------|-------------|
| `[PM groom]` | Product Manager | BEFORE implementation | Adds acceptance criteria, PNG verification checklist, test scenarios. Renames .todo → .groomed |
| `[SWE]` | Software Engineer | After grooming | Implements code + tests (TDD: failing test first). Renames .groomed → .in-progress |
| `[QA]` | Tester | After implementation | Verifies acceptance criteria, renders to PNG and visually inspects. Pass/Fail |
| `[PM accept]` | Product Manager | AFTER QA passes | Final review. Renders PNGs independently. Accept → .done + commit. Reject → back to SWE to finish |
| `[Pull next]` | Orchestrator | AFTER commit | Check tasks/ for remaining .todo/.groomed files. Pick 2 lowest-numbered, create new batch in task list, repeat |

**PM has two distinct roles:**
1. **Before** engineering: groom the task (define what "done" looks like)
2. **After** QA: accept or reject (verify it actually looks right). Reject sends it back to engineer for finishing, NOT back to grooming.

### Pull Next Work

The last item in every batch is always **"Pull next 2 tasks from backlog"**. This ensures work continues automatically:
1. Check `tasks/` for `.todo.md` or `.groomed.md` files
2. Pick the 2 lowest-numbered groomed tasks (groom first if only .todo.md)
3. Create a new batch of task list items with dependencies
4. Start the pipeline again

## Conventions

- Every task must include pytest tests
- Tests run with `uv run pytest`
- Lint with `uv run ruff check`
- Commit message references task: "Implement task 01: project setup"
- Only commit after PM accepts
- Tasks are NEVER deleted — they move through statuses (.todo → .groomed → .in-progress → .done)
- Commit regularly — don't accumulate large uncommitted changes
