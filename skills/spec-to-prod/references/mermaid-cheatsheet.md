# Mermaid cheat-sheet (vendored — tech agent's diagram reference)

Write the diagram as a fenced ```mermaid block inside tech-spec.md. It is
documentation first: renders on GitHub/obsidian with zero tooling. Export to
PNG/SVG only if the repo demands image assets (then use the
creating-mermaid-diagrams skill, or `mmdc -i in.mmd -o out.svg` if
mermaid-cli is installed). Prefer simple over pretty: 6–12 nodes max.

## Component / data-flow (the default for § Architecture)

```mermaid
flowchart LR
    consumer -->|reads| store
    store --> db[(SQLite)]
    store -.gated.-> pg[(Postgres)]
```

## Sequence (for request/ordering stories in § Solution or § Impact)

```mermaid
sequenceDiagram
    participant M as MCP tool
    participant S as Store
    M->>S: get_callers(symbol)
    S-->>M: rows (Mapping)
    Note over S: fallback: LIKE scan when FTS absent
```

## State (for lifecycles: spec Status, task states, build pipeline)

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> active: branch cut
    active --> done: all tasks ticked + check green
    done --> [*]
```

## Entity relations (for schema/data-model areas in § Code guide)

```mermaid
erDiagram
    SYMBOLS ||--o{ EDGES : "src/dst"
    SYMBOLS ||--o{ EMBEDDINGS : symbol_id
```

## Conventions

- Direction `LR` for pipelines/flows, `TB` for org/hierarchy.
- Solid arrows = always-on paths; dotted (`-.->`) = gated/optional/fallback.
- Label edges with the verb of the relationship, not the field name.
- One diagram per concept — if you need a legend, split the diagram.
