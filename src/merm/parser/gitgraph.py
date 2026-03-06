"""Parser for Mermaid gitGraph syntax."""

import re

from merm.ir.gitgraph import CommitType, GitBranch, GitCommit, GitGraph
from merm.parser.flowchart import ParseError

# Regex patterns for commit options
_ID_RE = re.compile(r'id:\s*"([^"]+)"')
_TAG_RE = re.compile(r'tag:\s*"([^"]+)"')
_TYPE_RE = re.compile(r"type:\s*(NORMAL|REVERSE|HIGHLIGHT)")

def parse_gitgraph(text: str) -> GitGraph:
    """Parse Mermaid gitGraph syntax into a GitGraph IR.

    Raises ParseError on invalid input.
    """
    if not text or not text.strip():
        raise ParseError("Empty input")

    lines = text.splitlines()

    # Find the gitGraph header line
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("%%"):
            continue
        if re.match(r"gitGraph\b", stripped):
            header_idx = i
            break

    if header_idx is None:
        raise ParseError("Missing 'gitGraph' keyword")

    # State
    commits: list[GitCommit] = []
    branches: list[GitBranch] = []
    branch_order: list[str] = ["main"]
    current_branch = "main"
    commit_counter = 0
    commit_by_id: dict[str, GitCommit] = {}
    # Track the latest commit on each branch
    branch_head: dict[str, str] = {}  # branch_name -> commit_id
    # Track which branches exist
    branch_set: set[str] = {"main"}

    for i in range(header_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("%%"):
            continue

        if stripped.startswith("commit"):
            rest = stripped[len("commit"):].strip()

            # Parse optional id, tag, type
            commit_id = ""
            tag = ""
            commit_type = CommitType.NORMAL

            id_match = _ID_RE.search(rest)
            if id_match:
                commit_id = id_match.group(1)

            tag_match = _TAG_RE.search(rest)
            if tag_match:
                tag = tag_match.group(1)

            type_match = _TYPE_RE.search(rest)
            if type_match:
                commit_type = CommitType(type_match.group(1))

            # Auto-generate ID if not specified
            if not commit_id:
                commit_id = f"{commit_counter}-{current_branch[:7]}"

            if commit_id in commit_by_id:
                raise ParseError(
                    f"Duplicate commit ID: {commit_id}", line=i + 1
                )

            # Determine parent
            parent_id = branch_head.get(current_branch, "")
            parents = (parent_id,) if parent_id else ()

            commit = GitCommit(
                id=commit_id,
                branch=current_branch,
                commit_type=commit_type,
                tag=tag,
                parents=parents,
                is_merge=False,
                cherry_picked_from="",
            )
            commits.append(commit)
            commit_by_id[commit_id] = commit
            branch_head[current_branch] = commit_id
            commit_counter += 1

        elif stripped.startswith("branch "):
            branch_name = stripped[len("branch "):].strip()
            if branch_name in branch_set:
                raise ParseError(
                    f"Branch already exists: {branch_name}", line=i + 1
                )
            branch_set.add(branch_name)
            branch_order.append(branch_name)

            start = branch_head.get(current_branch, "")
            branches.append(GitBranch(name=branch_name, start_commit=start))
            # New branch starts at the same commit as current branch head
            if start:
                branch_head[branch_name] = start

        elif stripped.startswith("checkout "):
            branch_name = stripped[len("checkout "):].strip()
            if branch_name not in branch_set:
                raise ParseError(
                    f"Branch does not exist: {branch_name}", line=i + 1
                )
            current_branch = branch_name

        elif stripped.startswith("merge "):
            rest = stripped[len("merge "):].strip()

            # Parse branch name and optional tag
            # Branch name is the first token
            parts = rest.split()
            merge_branch = parts[0] if parts else ""

            if merge_branch not in branch_set:
                raise ParseError(
                    f"Branch does not exist: {merge_branch}", line=i + 1
                )

            tag = ""
            tag_match = _TAG_RE.search(rest)
            if tag_match:
                tag = tag_match.group(1)

            # Auto-generate merge commit ID
            commit_id = f"{commit_counter}-{current_branch[:7]}"
            commit_counter += 1

            # Parents: current branch head + merged branch head
            parent1 = branch_head.get(current_branch, "")
            parent2 = branch_head.get(merge_branch, "")
            parents_list: list[str] = []
            if parent1:
                parents_list.append(parent1)
            if parent2:
                parents_list.append(parent2)

            commit = GitCommit(
                id=commit_id,
                branch=current_branch,
                commit_type=CommitType.NORMAL,
                tag=tag,
                parents=tuple(parents_list),
                is_merge=True,
                cherry_picked_from="",
            )
            commits.append(commit)
            commit_by_id[commit_id] = commit
            branch_head[current_branch] = commit_id

        elif stripped.startswith("cherry-pick "):
            rest = stripped[len("cherry-pick "):].strip()
            id_match = _ID_RE.search(rest)
            if not id_match:
                raise ParseError(
                    "cherry-pick requires id: \"...\"", line=i + 1
                )
            source_id = id_match.group(1)

            if source_id not in commit_by_id:
                raise ParseError(
                    f"Cherry-pick source not found: {source_id}", line=i + 1
                )

            commit_id = f"{commit_counter}-{current_branch[:7]}"
            commit_counter += 1

            parent_id = branch_head.get(current_branch, "")
            parents = (parent_id,) if parent_id else ()

            commit = GitCommit(
                id=commit_id,
                branch=current_branch,
                commit_type=CommitType.NORMAL,
                tag="",
                parents=parents,
                is_merge=False,
                cherry_picked_from=source_id,
            )
            commits.append(commit)
            commit_by_id[commit_id] = commit
            branch_head[current_branch] = commit_id

        else:
            raise ParseError(
                f"Unknown command: {stripped}", line=i + 1
            )

    return GitGraph(
        commits=tuple(commits),
        branches=tuple(branches),
        branch_order=tuple(branch_order),
    )

__all__ = ["parse_gitgraph"]
