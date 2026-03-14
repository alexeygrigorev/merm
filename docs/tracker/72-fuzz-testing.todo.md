# Issue 72: Fuzz testing for parsers

## Problem

No fuzz testing exists to catch crashes on malformed input.

## Scope

- Add fuzz tests for all parsers using hypothesis or similar
- Test with malformed, truncated, and adversarial mermaid syntax
- Ensure parsers fail gracefully (raise clean errors, never crash)
