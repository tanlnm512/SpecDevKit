# Test Cases: mini-calc

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-08
Black-box, business-language verification traced to requirements. Each case
has an observable pass condition. No implementation details.

## TC-001 — Multiply two integers
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** the calculator module loaded
- **When** the multiply operation is called with 6 and 7
- **Then** the result is 42
- **Pass condition**: `cd repo && python3 -m pytest test_calc.py -k multiply` exits 0

## TC-002 — Zero operand returns zero
- **Story**: US1 · **Traces to**: FR-002, AC2
- **Given** the calculator module loaded
- **When** the multiply operation is called with 0 and any integer
- **Then** the result is 0
- **Pass condition**: `cd repo && python3 -m pytest test_calc.py -k zero` exits 0

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001      | TC-001     | auto               |
| FR-002      | TC-002     | auto               |
