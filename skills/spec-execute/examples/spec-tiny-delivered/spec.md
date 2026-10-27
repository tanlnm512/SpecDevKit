# Spec: tiny-delivered-demo

**Status**: done
**Tier**: tiny
**Effort**: standard
**Created**: 2026-09-08
**Baseline**: tiny-demo v1 @ 3fa9c21

A delivered one-file contract — the terminal state of the execute
span at the tiny tier: every § Tasks entry ticked with its proof
sub-line, Status done, the delivery record written. `check.py` gates
this file on the in-file contract alone (D-037); the delivered
docset is historical, so the baseline-vs-HEAD comparison no longer
applies (spec-shape D-046).

## What
A demo calculator feature delivered as a one-file spec: the task
list lives in § Tasks, ticked and proven.

## Why
Proves the tiny-tier delivery end state a repo can hold and re-check:
the one file is both contract and status holder.

## User stories
### US1 — Multiply on demand (P1)
As a script author, I want the calculator to multiply two integers,
so that I can drop my repeated-addition loop.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given two integers, When I run multiply, Then the product
  prints and the command exits 0.
- AC2: Given non-integer input, When I run multiply, Then a one-line
  error prints and the command exits nonzero.

## Requirements
- **FR-001**: The system shall multiply two integers passed as CLI
  arguments and print the product.
- **FR-002**: WHEN either argument is not an integer, the system
  shall print a one-line error and exit nonzero.

## Tasks
- [x] T001 Multiply lands (FR-001) [P]
  Touches: `calc.py`
  Accept: `python3 calc.py multiply 6 7` prints 42
  done 2026-09-08 — `python3 -m unittest test_calc.MultiplyTests` green (2 tests)
- [x] T002 Non-integer input errors cleanly (FR-002) [P]
  Touches: `calc.py`, `test_calc.py`
  Accept: `python3 calc.py multiply 6 x` exits nonzero
  done 2026-09-08 — `python3 -m unittest test_calc.MultiplyTests` green (2 tests)

Delivered: commit @ -
