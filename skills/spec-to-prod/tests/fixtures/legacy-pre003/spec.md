# Spec: legacy-relay

**Status**: active
**Created**: 2025-11-02
**Branch**: `feature/legacy-relay`

## What
Add a relay switch to the device module: the module gains a relay open and
close pair alongside its existing setters, visible through the module's
public function surface.

## Why
Callers currently drive the relay through raw register writes, and every
caller repeats the same safety delays.

## Business value
A shared relay pair centralizes the safety delays and removes the
register-level knowledge from every caller.

## User stories
### US1 — Drive the relay (P1)
As a device caller, I want to open and close the relay through one pair of
functions, so that the safety delays are applied uniformly.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given the relay open, When I close it, Then it reads closed.

## Requirements
- **FR-001**: WHEN the relay is opened or closed, the system shall apply
  the safety delay before returning.

## Scope
**In**: the relay pair in the device module and its tests.
**Out (deferred)**: other device operations; register-level access.

## Assumptions & risks
- Assumption: the relay state is binary today and its tests pin that.
- Risk: a future multi-relay device needs addressing — mitigation: the
  pair stays a pure single-relay surface.
