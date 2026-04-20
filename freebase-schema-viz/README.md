# Freebase Schema Visualization

Interactive graph visualization of the Freebase knowledge graph schema. Generates a standalone HTML file with all dependencies inlined.

## Quick Start

```bash
make open
```

## Commands

| Command      | Description                                      |
|--------------|--------------------------------------------------|
| `make build` | Generate `freebase-schema.html`                  |
| `make open`  | Build and open in default browser                |
| `make setup` | Install Python dependencies via uv               |
| `make clean` | Remove generated HTML                            |

## Input Data

Reads from `../data/`:

| File                  | Description                              |
|-----------------------|------------------------------------------|
| `node_types.tsv`      | Node type ID to Freebase type path       |
| `edge_types.tsv`      | Edge type ID to Freebase property path   |
| `relation_schema.csv` | Source type, edge type, target type triples |

## Output

`freebase-schema.html` — a single self-contained HTML file (~2.4 MB) with:

- **2,060 node types** across 92 domains (color-coded)
- **2,663 schema edges** (relations between types)
- **Search** — filter by node type, edge type, or both
- **Stats panel** — toggle to view graph statistics, top connected types, domain breakdown
- **Physics** — layout auto-stabilizes then freezes after 10 seconds

No internet connection required to view the output.
