# Issue 71: Mutation testing

## Problem

No mutation testing exists to verify test suite effectiveness.

## Scope

- Set up mutmut or similar mutation testing tool
- Run against critical modules (parsers, layout, rendering)
- Identify and kill surviving mutants
- Add tests to cover gaps found by mutation testing
