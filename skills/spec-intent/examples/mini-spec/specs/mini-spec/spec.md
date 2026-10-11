# Spec: mini-calc

**Status**: draft
**Created**: 2026-09-08
**Branch**: `feature/mini-calc`

## What
Add integer multiplication to the calculator module: the calculator gains
a multiply operation alongside add and subtract, visible through the
module's public function surface.

## Why
Users currently cannot multiply — the operation is the most-requested gap
in the arithmetic module, forcing workarounds with repeated addition.

## Business value
Calculators that ship the four basic operations stop losing users at the
first missing operation; support requests about multiplication workarounds
drop to zero.

## User stories
### US1 — Multiply two numbers (P1)
As a calculator user, I want to multiply two integers, so that I can
compute products without workarounds.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given the calculator module loaded, When I multiply 6 by 7, Then
  the result is 42.
- AC2: Given any operand is zero, When I multiply, Then the result is 0.

## Requirements
- **FR-001**: WHEN the user multiplies two integers, the system shall
  return their integer product.
- **FR-002**: IF either operand is zero, the system shall return 0 without
  special-casing at call sites.

## Scope
**In**: the multiply operation in the arithmetic module and its tests.
**Out (deferred)**: floating-point operands; division; CLI surface changes.

## Assumptions & risks
- Assumption: integers only — the module is integer-today and its tests
  pin that.
- Risk: a future expression parser needs operator precedence — mitigation:
  the operation stays a pure two-operand function.
