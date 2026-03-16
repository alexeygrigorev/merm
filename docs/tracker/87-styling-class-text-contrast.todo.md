# Issue 87: Styled nodes have poor text contrast

## Problem

When a CSS class is applied to a node via `:::className`, the class color is applied to the text, producing poor contrast against the default light purple node fill. For example, an olive/dark-yellow text color is nearly illegible against #ECECFF background.

Reproduction: `tests/fixtures/corpus/styling/default_class.mmd`

## Acceptance criteria

- When a style class defines a color, it should be applied to the node fill/border, not the text
- Text color must maintain readable contrast against the node background (WCAG AA: contrast ratio >= 4.5:1)
- If a class explicitly sets both fill and text color, both should be honored
- Default text color (#333333) should be preserved unless explicitly overridden
- Existing tests must continue to pass
