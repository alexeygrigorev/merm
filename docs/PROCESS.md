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

## Conventions

- Every task must include pytest tests
- Tests run with `uv run pytest`
- Lint with `uv run ruff check`
- Commit message references task: "Implement task 01: project setup"
- Only commit after PM accepts
