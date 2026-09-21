# Spec: legacy-gadget

**Status**: active
**Created**: 2026-01-15
**Branch**: `feature/legacy-gadget`

## What
Add a gadget toggle to the device module: the module gains a boolean
toggle operation alongside its existing setters, visible through the
module's public function surface.

## Why
Callers currently toggle the gadget by reading, negating, and writing the
value themselves, and two concurrent callers can interleave those steps.

## Business value
A single toggle operation removes the read-modify-write race for every
caller and shrinks the module's documented surface.

## User stories
### US1 — Toggle the gadget (P1)
As a device caller, I want to toggle the gadget atomically, so that
concurrent toggles cannot interleave.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given the gadget off, When I toggle it, Then it reads on.

## Requirements
- **FR-001**: WHEN the gadget is toggled, the system shall flip its value
  atomically.

## Scope
**In**: the toggle operation in the device module and its tests.
**Out (deferred)**: other device operations; CLI surface changes.

## Assumptions & risks
- Assumption: the gadget value is boolean today and its tests pin that.
- Risk: a future multi-state gadget needs richer operations — mitigation:
  the operation stays a pure single-gadget toggle.
