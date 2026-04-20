"""
Subgraph viewer — lazy line-by-line visualization of training sequences.

Serves a local web UI that reads one line at a time from the training data,
decodes node/edge type IDs, reconstructs the subgraph, and renders it
interactively with vis.js.

Usage:
    uv run server.py
    # then open http://localhost:5001
"""

import linecache
import os
import random
from pathlib import Path

from flask import Flask, jsonify, send_file

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TRAINING_FILE = str(DATA_DIR / "training_sequences.csv")

app = Flask(__name__)

# --- Load lookup tables once at startup ---

node_types = {}
edge_types = {}
# relation_schema: edge_id -> list of (src_type, tgt_type)
relation_schema = {}
# For quick lookup: (src_type, tgt_type) -> list of edge_ids
edge_by_pair = {}


def load_lookups():
    global node_types, edge_types, relation_schema, edge_by_pair, total_lines

    with open(DATA_DIR / "node_types.tsv") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                node_types[int(parts[0])] = parts[1]

    with open(DATA_DIR / "edge_types.tsv") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                edge_types[int(parts[0])] = parts[1]

    with open(DATA_DIR / "relation_schema.csv") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 3:
                src, eid, tgt = int(parts[0]), int(parts[1]), int(parts[2])
                relation_schema.setdefault(eid, []).append((src, tgt))
                edge_by_pair.setdefault((src, tgt), []).append(eid)


def count_lines():
    """Count total lines without loading the file into memory."""
    count = 0
    with open(TRAINING_FILE, "rb") as f:
        for _ in f:
            count += 1
    return count


total_lines = 0


def decode_line(line_num):
    """Read and decode a single training sequence line."""
    raw = linecache.getline(TRAINING_FILE, line_num).strip()
    if not raw:
        return None

    tokens = [int(x) for x in raw.split(",")]

    # Separate node types and edge types, strip trailing 1,1 sentinel
    if tokens[-2:] == [1, 1]:
        tokens = tokens[:-2]

    node_ids = set()
    edge_ids = set()
    for t in tokens:
        if t in node_types:
            node_ids.add(t)
        elif t in edge_types:
            edge_ids.add(t)

    # Build subgraph: for each edge_id present, check if its src and tgt
    # node types are also present in this sequence
    nodes = []
    edges = []
    seen_nodes = set()

    for eid in edge_ids:
        if eid not in relation_schema:
            continue
        for src, tgt in relation_schema[eid]:
            if src in node_ids and tgt in node_ids:
                edges.append({
                    "from": src,
                    "to": tgt,
                    "id": eid,
                    "label": edge_types[eid].split("/")[-1],
                    "title": f"{edge_types[eid]}\nID: {eid}",
                })
                seen_nodes.add(src)
                seen_nodes.add(tgt)

    # Add all node types found (some may be isolated in this subgraph)
    for nid in node_ids:
        domain = node_types[nid].strip("/").split("/")[0]
        nodes.append({
            "id": nid,
            "label": node_types[nid].split("/")[-1],
            "title": f"{node_types[nid]}\nID: {nid}",
            "domain": domain,
            "connected": nid in seen_nodes,
        })

    return {
        "line": line_num,
        "total_lines": total_lines,
        "raw": raw,
        "token_count": len(tokens) + 2,  # include sentinel
        "node_count": len(node_ids),
        "edge_count": len(edge_ids),
        "graph_edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/line/<int:line_num>")
def get_line(line_num):
    line_num = max(1, min(line_num, total_lines))
    result = decode_line(line_num)
    if result is None:
        return jsonify({"error": "Line not found"}), 404
    return jsonify(result)


@app.route("/api/random")
def get_random():
    line_num = random.randint(1, total_lines)
    result = decode_line(line_num)
    return jsonify(result)


@app.route("/api/info")
def get_info():
    return jsonify({
        "total_lines": total_lines,
        "node_types": len(node_types),
        "edge_types": len(edge_types),
        "relations": sum(len(v) for v in relation_schema.values()),
    })


if __name__ == "__main__":
    print("Loading lookup tables...")
    load_lookups()
    print(f"  {len(node_types)} node types, {len(edge_types)} edge types")
    print("Counting lines (this may take a moment)...")
    total_lines = count_lines()
    print(f"  {total_lines:,} training sequences")
    print("Starting server at http://localhost:5001")
    app.run(port=5001, debug=False)
