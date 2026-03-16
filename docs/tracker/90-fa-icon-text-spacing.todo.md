# Issue 90: Font Awesome icon too close to text in nodes

## Problem

When a node has a Font Awesome icon (e.g., `fa:fa-car Drive to Grandma`), the icon is rendered too close to the text — they touch or overlap. There should be a small gap between the icon and the label text.

Reproduction: Christmas tree flowchart in README.

## Acceptance criteria

- A visible gap (4-6px) between the FA icon and the label text
- Icons should not overlap with text in any node
- Existing tests must continue to pass
