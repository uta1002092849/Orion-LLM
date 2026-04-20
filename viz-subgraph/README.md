# Freebase Subgraph Viewer

Interactive line-by-line visualization of training sequences. Each line in the training data represents a subgraph (entity neighborhood) — this tool decodes and renders them one at a time.

## Quick Start

```bash
make run
# then open http://localhost:5001
```

## How It Works

The server lazily reads one line at a time from the training data (no full file loading). Each line's integer tokens are decoded using the node/edge type dictionaries, and the subgraph is reconstructed using the relation schema.

## Controls

| Control          | Action                        |
|------------------|-------------------------------|
| `← Prev` / `→ Next` | Navigate lines sequentially |
| `Go`             | Jump to a specific line number |
| `Random`         | Load a random sequence         |
| Arrow keys       | Prev/Next (when input not focused) |
| `r` key          | Random sequence                |

## Sidebar

- **Stats** — token count, node/edge type counts, graph edges
- **Node list** — all node types in the sequence, color-coded by domain
- **Edge list** — all resolved edges in the subgraph
- **Raw sequence** — the original comma-separated token line

## Input Data

Reads from `../data/`:

| File                    | Purpose                                  |
|-------------------------|------------------------------------------|
| `node_types.tsv`        | Decode node type IDs to names            |
| `edge_types.tsv`        | Decode edge type IDs to names            |
| `relation_schema.csv`   | Resolve which edges connect which nodes  |
| `training_sequences.csv`| The training data (read lazily)          |
