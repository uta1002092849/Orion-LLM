"""
Visualize the Freebase schema as an interactive graph.

Reads:
  - data/node_types.tsv    (type_id -> type_name)
  - data/edge_types.tsv    (edge_id -> edge_name)
  - data/relation_schema.csv (source_type_id, edge_id, target_type_id)

Outputs:
  - viz/schema_graph.html  (interactive pyvis graph)
"""

import csv
import json
import re
from pathlib import Path
from collections import Counter
from urllib.request import urlopen

import networkx as nx
from pyvis.network import Network

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent


def load_node_types():
    mapping = {}
    with open(DATA_DIR / "node_types.tsv") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                mapping[int(parts[0])] = parts[1]
    return mapping


def load_edge_types():
    mapping = {}
    with open(DATA_DIR / "edge_types.tsv") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                mapping[int(parts[0])] = parts[1]
    return mapping


def load_relations():
    relations = []
    with open(DATA_DIR / "relation_schema.csv") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 3:
                relations.append((int(row[0]), int(row[1]), int(row[2])))
    return relations


def get_domain(type_path):
    """Extract domain from a Freebase type path, e.g. '/location/country' -> 'location'."""
    parts = type_path.strip("/").split("/")
    return parts[0] if parts else "unknown"


# Distinct colors for top domains
DOMAIN_COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9A6324", "#fffac8", "#800000", "#aaffc3",
    "#808000", "#ffd8b1", "#000075", "#a9a9a9", "#e6beff",
]


def build_graph(node_types, edge_types, relations):
    G = nx.MultiDiGraph()

    # Count edges per node to determine sizing
    degree = Counter()
    for src, _, tgt in relations:
        degree[src] += 1
        degree[tgt] += 1

    # Assign colors by domain (for ALL node types)
    domains = set()
    for nid, name in node_types.items():
        domains.add(get_domain(name))
    domain_list = sorted(domains)
    domain_color = {d: DOMAIN_COLORS[i % len(DOMAIN_COLORS)] for i, d in enumerate(domain_list)}

    # Add ALL nodes (including isolated ones with no edges)
    for nid, name in node_types.items():
        domain = get_domain(name)
        short_name = name.split("/")[-1] if "/" in name else name
        d = degree.get(nid, 0)
        G.add_node(
            nid,
            label=short_name,
            title=f"{name}\nID: {nid}\nDegree: {d}",
            color=domain_color[domain],
            size=5 + min(d * 2, 40) if d > 0 else 4,
            domain=domain,
        )

    # Add edges
    for src, eid, tgt in relations:
        edge_name = edge_types.get(eid, f"edge_{eid}")
        short_edge = edge_name.split("/")[-1] if "/" in edge_name else edge_name
        G.add_edge(src, tgt, label=short_edge, title=f"{edge_name}\nID: {eid}")

    return G, domain_color


def build_search_index(G, node_types, edge_types, relations):
    """Build JSON search indices for nodes and edges."""
    nodes_index = []
    for nid in G.nodes:
        name = node_types.get(nid, f"unknown_{nid}")
        short = name.split("/")[-1] if "/" in name else name
        domain = get_domain(name)
        nodes_index.append({
            "id": nid,
            "name": name,
            "short": short,
            "domain": domain,
        })

    edges_index = []
    for src, eid, tgt in relations:
        if src in G.nodes and tgt in G.nodes:
            edge_name = edge_types.get(eid, f"edge_{eid}")
            short_edge = edge_name.split("/")[-1] if "/" in edge_name else edge_name
            edges_index.append({
                "id": eid,
                "name": edge_name,
                "short": short_edge,
                "src": src,
                "tgt": tgt,
                "srcName": node_types.get(src, str(src)),
                "tgtName": node_types.get(tgt, str(tgt)),
            })

    return nodes_index, edges_index


def compute_stats(node_types, edge_types, relations, domain_color):
    """Compute stats for the stats panel."""
    degree = Counter()
    for src, _, tgt in relations:
        degree[src] += 1
        degree[tgt] += 1

    # Connected vs isolated
    connected_nodes = set()
    for src, _, tgt in relations:
        connected_nodes.add(src)
        connected_nodes.add(tgt)
    isolated = len(node_types) - len(connected_nodes)

    # Domain breakdown
    domain_counts = Counter()
    for nid, name in node_types.items():
        domain_counts[get_domain(name)] += 1

    # Top connected nodes
    top_nodes = degree.most_common(10)

    # Self-loop count
    self_loops = sum(1 for src, _, tgt in relations if src == tgt)

    return {
        "total_node_types": len(node_types),
        "total_edge_types": len(edge_types),
        "total_relations": len(relations),
        "connected_nodes": len(connected_nodes),
        "isolated_nodes": isolated,
        "domains": len(domain_color),
        "self_loops": self_loops,
        "domain_counts": domain_counts.most_common(),
        "top_nodes": [(node_types.get(nid, str(nid)), d) for nid, d in top_nodes],
    }


def render(G, domain_color, node_types, edge_types, relations):
    net = Network(
        height="100vh",
        width="100%",
        directed=True,
        bgcolor="#1a1a2e",
        font_color="white",
        notebook=False,
    )

    net.from_nx(G)

    # Physics settings for better layout
    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -80,
          "centralGravity": 0.01,
          "springLength": 150,
          "springConstant": 0.02,
          "damping": 0.5
        },
        "solver": "forceAtlas2Based",
        "stabilization": {
          "iterations": 200
        },
        "timestep": 0.5
      },
      "edges": {
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.5 } },
        "color": { "color": "#555555", "highlight": "#ffffff" },
        "smooth": { "type": "curvedCW", "roundness": 0.15 },
        "font": { "size": 0 }
      },
      "nodes": {
        "font": { "size": 12, "color": "white" },
        "borderWidth": 1,
        "borderWidthSelected": 3
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "multiselect": true
      }
    }
    """)

    # Build legend HTML
    legend_items = ""
    for domain, color in sorted(domain_color.items()):
        legend_items += (
            f'<div style="display:flex;align-items:center;margin:2px 0;">'
            f'<span style="width:12px;height:12px;background:{color};'
            f'border-radius:50%;display:inline-block;margin-right:6px;"></span>'
            f'<span>{domain}</span></div>'
        )

    legend_html = (
        f'<div id="legend" style="position:fixed;top:10px;right:10px;background:rgba(0,0,0,0.8);'
        f'color:white;padding:12px;border-radius:8px;font-family:monospace;font-size:11px;'
        f'max-height:90vh;overflow-y:auto;z-index:1000;">'
        f'<b>Domains ({len(domain_color)})</b><hr style="border-color:#444;">'
        f'{legend_items}</div>'
    )

    # Build stats panel
    stats = compute_stats(node_types, edge_types, relations, domain_color)

    domain_rows = ""
    for domain, count in stats["domain_counts"]:
        color = domain_color.get(domain, "#aaa")
        domain_rows += (
            f'<tr><td style="padding:2px 8px 2px 0;">'
            f'<span style="color:{color};">&#9679;</span> {domain}</td>'
            f'<td style="text-align:right;padding:2px 0;">{count}</td></tr>'
        )

    top_node_rows = ""
    for name, d in stats["top_nodes"]:
        short = name.split("/")[-1] if "/" in name else name
        top_node_rows += (
            f'<tr><td style="padding:2px 8px 2px 0;">{short}</td>'
            f'<td style="text-align:right;padding:2px 0;">{d}</td></tr>'
        )

    stats_html = f"""
    <div id="stats-panel" style="display:none;position:fixed;bottom:10px;left:10px;background:rgba(0,0,0,0.9);
      color:white;padding:16px;border-radius:8px;font-family:monospace;font-size:12px;
      z-index:1001;max-width:420px;max-height:70vh;overflow-y:auto;">

      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <b style="font-size:14px;">Freebase Schema Stats</b>
        <button onclick="toggleStats()"
          style="background:none;border:1px solid #555;color:#aaa;cursor:pointer;
          border-radius:4px;padding:2px 8px;font-family:monospace;">&#10005;</button>
      </div>

      <table style="width:100%;border-collapse:collapse;margin-bottom:12px;">
        <tr style="border-bottom:1px solid #333;">
          <td style="padding:4px 0;color:#42d4f4;">Total Node Types</td>
          <td style="text-align:right;padding:4px 0;">{stats["total_node_types"]}</td>
        </tr>
        <tr style="border-bottom:1px solid #333;">
          <td style="padding:4px 0;color:#42d4f4;">Connected Nodes</td>
          <td style="text-align:right;padding:4px 0;">{stats["connected_nodes"]}</td>
        </tr>
        <tr style="border-bottom:1px solid #333;">
          <td style="padding:4px 0;color:#42d4f4;">Isolated Nodes</td>
          <td style="text-align:right;padding:4px 0;">{stats["isolated_nodes"]}</td>
        </tr>
        <tr style="border-bottom:1px solid #333;">
          <td style="padding:4px 0;color:#f58231;">Total Edge Types</td>
          <td style="text-align:right;padding:4px 0;">{stats["total_edge_types"]}</td>
        </tr>
        <tr style="border-bottom:1px solid #333;">
          <td style="padding:4px 0;color:#f58231;">Relations (schema edges)</td>
          <td style="text-align:right;padding:4px 0;">{stats["total_relations"]}</td>
        </tr>
        <tr style="border-bottom:1px solid #333;">
          <td style="padding:4px 0;color:#f58231;">Self-loops</td>
          <td style="text-align:right;padding:4px 0;">{stats["self_loops"]}</td>
        </tr>
        <tr>
          <td style="padding:4px 0;color:#bfef45;">Domains</td>
          <td style="text-align:right;padding:4px 0;">{stats["domains"]}</td>
        </tr>
      </table>

      <details>
        <summary style="cursor:pointer;color:#42d4f4;margin-bottom:6px;">Top 10 Most Connected Types</summary>
        <table style="width:100%;border-collapse:collapse;margin-top:4px;">
          {top_node_rows}
        </table>
      </details>

      <details style="margin-top:8px;">
        <summary style="cursor:pointer;color:#bfef45;margin-bottom:6px;">Domain Breakdown ({stats["domains"]} domains)</summary>
        <table style="width:100%;border-collapse:collapse;margin-top:4px;">
          {domain_rows}
        </table>
      </details>
    </div>

    <button id="stats-toggle" onclick="toggleStats()"
      style="position:fixed;bottom:10px;left:10px;background:rgba(0,0,0,0.8);
      color:white;padding:10px 16px;border-radius:8px;border:1px solid #555;
      cursor:pointer;font-family:monospace;font-size:12px;z-index:1000;">
      Stats
    </button>
    """

    # Build search index
    nodes_index, edges_index = build_search_index(G, node_types, edge_types, relations)

    search_panel_html = """
    <div id="search-panel" style="position:fixed;top:10px;left:10px;background:rgba(0,0,0,0.9);
      color:white;padding:16px;border-radius:8px;font-family:monospace;font-size:12px;
      z-index:1001;width:380px;">

      <div style="display:flex;gap:6px;margin-bottom:10px;">
        <input id="search-input" type="text" placeholder="Search nodes or edges..."
          style="flex:1;padding:8px;border-radius:4px;border:1px solid #555;
          background:#2a2a4a;color:white;font-family:monospace;font-size:12px;outline:none;" />
        <button onclick="clearSearch()"
          style="padding:8px 12px;border-radius:4px;border:1px solid #555;
          background:#444;color:white;cursor:pointer;font-family:monospace;">Clear</button>
      </div>

      <div style="display:flex;gap:8px;margin-bottom:10px;">
        <label style="cursor:pointer;">
          <input type="radio" name="search-type" value="nodes" checked
            onchange="doSearch()" /> Nodes
        </label>
        <label style="cursor:pointer;">
          <input type="radio" name="search-type" value="edges"
            onchange="doSearch()" /> Edges
        </label>
        <label style="cursor:pointer;">
          <input type="radio" name="search-type" value="both"
            onchange="doSearch()" /> Both
        </label>
      </div>

      <div id="search-results" style="max-height:500px;overflow-y:auto;"></div>
      <div id="search-status" style="margin-top:8px;color:#888;font-size:11px;"></div>
    </div>
    """

    search_script = """
    <script>
    // Freeze physics after 5 seconds
    setTimeout(function() {
      network.setOptions({ physics: { enabled: false } });
    }, 10000);

    var nodeIndex = __NODE_INDEX__;
    var edgeIndex = __EDGE_INDEX__;

    // Store original colors/sizes for reset
    var originalNodeState = {};
    network.body.data.nodes.forEach(function(n) {
      originalNodeState[n.id] = { color: n.color, size: n.size, font: n.font };
    });
    var originalEdgeState = {};
    network.body.data.edges.forEach(function(e) {
      originalEdgeState[e.id] = { color: e.color, width: e.width };
    });

    var searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', function() { doSearch(); });
    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') clearSearch();
    });

    function getSearchType() {
      return document.querySelector('input[name="search-type"]:checked').value;
    }

    function doSearch() {
      var query = searchInput.value.trim().toLowerCase();
      var resultsDiv = document.getElementById('search-results');
      var statusDiv = document.getElementById('search-status');

      if (!query || query.length < 2) {
        resultsDiv.innerHTML = '';
        statusDiv.textContent = 'Type at least 2 characters...';
        resetHighlights();
        return;
      }

      var searchType = getSearchType();
      var nodeMatches = [];
      var edgeMatches = [];

      if (searchType === 'nodes' || searchType === 'both') {
        nodeMatches = nodeIndex.filter(function(n) {
          return n.name.toLowerCase().includes(query) ||
                 n.short.toLowerCase().includes(query) ||
                 n.domain.toLowerCase().includes(query) ||
                 String(n.id) === query;
        });
      }

      if (searchType === 'edges' || searchType === 'both') {
        edgeMatches = edgeIndex.filter(function(e) {
          return e.name.toLowerCase().includes(query) ||
                 e.short.toLowerCase().includes(query) ||
                 String(e.id) === query;
        });
      }

      // Build results HTML
      var html = '';

      if (nodeMatches.length > 0) {
        html += '<div style="color:#42d4f4;font-weight:bold;margin-bottom:4px;">Nodes (' + nodeMatches.length + ')</div>';
        nodeMatches.slice(0, 50).forEach(function(n) {
          html += '<div class="result-item" style="padding:4px 6px;margin:2px 0;border-radius:3px;cursor:pointer;border-left:3px solid #42d4f4;" '
            + 'onmouseover="this.style.background=\\'#333\\'" '
            + 'onmouseout="this.style.background=\\'transparent\\'" '
            + 'onclick="focusNode(' + n.id + ')">'
            + '<span style="color:#aaa;">[' + n.id + ']</span> ' + n.name
            + '</div>';
        });
        if (nodeMatches.length > 50) html += '<div style="color:#888;">...and ' + (nodeMatches.length - 50) + ' more</div>';
      }

      if (edgeMatches.length > 0) {
        html += '<div style="color:#f58231;font-weight:bold;margin:8px 0 4px 0;">Edges (' + edgeMatches.length + ')</div>';
        edgeMatches.slice(0, 50).forEach(function(e) {
          html += '<div class="result-item" style="padding:4px 6px;margin:2px 0;border-radius:3px;cursor:pointer;border-left:3px solid #f58231;" '
            + 'onmouseover="this.style.background=\\'#333\\'" '
            + 'onmouseout="this.style.background=\\'transparent\\'" '
            + 'onclick="focusEdge(' + e.src + ',' + e.tgt + ',' + e.id + ')">'
            + '<span style="color:#aaa;">[' + e.id + ']</span> ' + e.short
            + '<div style="font-size:10px;color:#777;">' + e.srcName.split("/").pop() + ' &rarr; ' + e.tgtName.split("/").pop() + '</div>'
            + '</div>';
        });
        if (edgeMatches.length > 50) html += '<div style="color:#888;">...and ' + (edgeMatches.length - 50) + ' more</div>';
      }

      if (nodeMatches.length === 0 && edgeMatches.length === 0) {
        html = '<div style="color:#888;">No results found.</div>';
      }

      resultsDiv.innerHTML = html;
      statusDiv.textContent = (nodeMatches.length + edgeMatches.length) + ' results';

      highlightMatches(
        nodeMatches.map(function(n) { return n.id; }),
        edgeMatches
      );
    }

    function highlightMatches(nodeIds, edgeMatches) {
      var matchedNodeSet = new Set(nodeIds);

      // Also include nodes connected by matched edges
      edgeMatches.forEach(function(e) {
        matchedNodeSet.add(e.src);
        matchedNodeSet.add(e.tgt);
      });

      // Dim non-matched nodes but keep them visible
      var nodeUpdates = [];
      network.body.data.nodes.forEach(function(n) {
        if (matchedNodeSet.has(n.id)) {
          var orig = originalNodeState[n.id];
          nodeUpdates.push({
            id: n.id,
            color: orig.color,
            size: orig.size,
            font: { color: 'white', size: 14 }
          });
        } else {
          nodeUpdates.push({
            id: n.id,
            color: { background: '#3a3a5c', border: '#4a4a6c' },
            size: 6,
            font: { color: '#7777aa', size: 9 }
          });
        }
      });
      network.body.data.nodes.update(nodeUpdates);

      // Dim non-matched edges but keep them visible
      var edgeUpdates = [];
      network.body.data.edges.forEach(function(e) {
        var isMatched = false;
        edgeMatches.forEach(function(em) {
          if (e.from === em.src && e.to === em.tgt) isMatched = true;
        });
        if (isMatched) {
          edgeUpdates.push({ id: e.id, color: { color: '#f58231' }, width: 3 });
        } else if (matchedNodeSet.has(e.from) || matchedNodeSet.has(e.to)) {
          edgeUpdates.push({ id: e.id, color: { color: '#5a5a8a' }, width: 1 });
        } else {
          edgeUpdates.push({ id: e.id, color: { color: '#33334d' }, width: 0.5 });
        }
      });
      network.body.data.edges.update(edgeUpdates);
    }

    function resetHighlights() {
      var nodeUpdates = [];
      network.body.data.nodes.forEach(function(n) {
        var orig = originalNodeState[n.id];
        if (orig) nodeUpdates.push({ id: n.id, color: orig.color, size: orig.size, font: orig.font });
      });
      network.body.data.nodes.update(nodeUpdates);

      var edgeUpdates = [];
      network.body.data.edges.forEach(function(e) {
        var orig = originalEdgeState[e.id];
        if (orig) edgeUpdates.push({ id: e.id, color: orig.color, width: orig.width });
      });
      network.body.data.edges.update(edgeUpdates);
    }

    function focusNode(nodeId) {
      network.focus(nodeId, { scale: 1.5, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
      network.selectNodes([nodeId]);
    }

    function focusEdge(srcId, tgtId, edgeTypeId) {
      var matchedEdgeIds = [];
      network.body.data.edges.forEach(function(e) {
        if (e.from === srcId && e.to === tgtId) matchedEdgeIds.push(e.id);
      });
      network.selectNodes([srcId, tgtId]);
      if (matchedEdgeIds.length > 0) network.selectEdges(matchedEdgeIds);
      var srcPos = network.getPositions([srcId])[srcId];
      var tgtPos = network.getPositions([tgtId])[tgtId];
      if (srcPos && tgtPos) {
        network.moveTo({
          position: { x: (srcPos.x + tgtPos.x) / 2, y: (srcPos.y + tgtPos.y) / 2 },
          scale: 1.5,
          animation: { duration: 500, easingFunction: 'easeInOutQuad' }
        });
      }
    }

    function clearSearch() {
      searchInput.value = '';
      document.getElementById('search-results').innerHTML = '';
      document.getElementById('search-status').textContent = '';
      resetHighlights();
      network.unselectAll();
    }

    // Stats panel toggle
    function toggleStats() {
      var panel = document.getElementById('stats-panel');
      var btn = document.getElementById('stats-toggle');
      if (panel.style.display === 'none') {
        panel.style.display = 'block';
        btn.style.display = 'none';
      } else {
        panel.style.display = 'none';
        btn.style.display = 'block';
      }
    }
    </script>
    """

    out_path = OUT_DIR / "freebase-schema.html"
    net.save_graph(str(out_path))

    # Inject search index data into script
    search_script = search_script.replace(
        "__NODE_INDEX__", json.dumps(nodes_index, separators=(",", ":"))
    ).replace(
        "__EDGE_INDEX__", json.dumps(edges_index, separators=(",", ":"))
    )

    # Post-process the HTML
    html = out_path.read_text()

    # --- Inline all external dependencies for standalone shipping ---

    # 1. Inline lib/bindings/utils.js
    utils_js = (OUT_DIR / "lib" / "bindings" / "utils.js").read_text()
    html = html.replace(
        '<script src="lib/bindings/utils.js"></script>',
        f"<script>{utils_js}</script>",
    )

    # 2. Inline CDN CSS: <link ... href="https://...vis-network.min.css" .../>
    css_pattern = re.compile(
        r'<link[^>]+href="(https://[^"]*vis-network\.min\.css)"[^>]*/>'
    )
    css_match = css_pattern.search(html)
    if css_match:
        print("  Inlining vis-network CSS from CDN...")
        css_content = urlopen(css_match.group(1)).read().decode()
        html = html.replace(css_match.group(0), f"<style>{css_content}</style>")

    # 3. Inline CDN JS: <script src="https://...vis-network.min.js" ...></script>
    js_pattern = re.compile(
        r'<script[^>]+src="(https://[^"]*vis-network\.min\.js)"[^>]*></script>'
    )
    js_match = js_pattern.search(html)
    if js_match:
        print("  Inlining vis-network JS from CDN...")
        js_content = urlopen(js_match.group(1)).read().decode()
        html = html.replace(js_match.group(0), f"<script>{js_content}</script>")

    # 4. Inline CDN Bootstrap CSS
    bs_css_pattern = re.compile(
        r'<link[^>]+href="(https://[^"]*bootstrap[^"]*\.css)"[^>]*/?\s*>'
    )
    bs_css_match = bs_css_pattern.search(html)
    if bs_css_match:
        print("  Inlining Bootstrap CSS from CDN...")
        bs_css = urlopen(bs_css_match.group(1)).read().decode()
        html = html.replace(bs_css_match.group(0), f"<style>{bs_css}</style>")

    # 5. Inline CDN Bootstrap JS
    bs_js_pattern = re.compile(
        r'<script[^>]+src="(https://[^"]*bootstrap[^"]*\.js)"[^>]*></script>'
    )
    bs_js_match = bs_js_pattern.search(html)
    if bs_js_match:
        print("  Inlining Bootstrap JS from CDN...")
        bs_js = urlopen(bs_js_match.group(1)).read().decode()
        html = html.replace(bs_js_match.group(0), f"<script>{bs_js}</script>")

    # Make fullscreen: remove default margin/padding, set body and canvas to 100vh
    fullscreen_css = """
    <style>
      html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
      #mynetwork { width: 100% !important; height: 100vh !important; }
    </style>
    """
    html = html.replace("</head>", f"{fullscreen_css}</head>")

    # Inject legend, search panel, stats panel, and script
    html = html.replace(
        "</body>",
        f"{legend_html}{search_panel_html}{stats_html}{search_script}</body>",
    )
    out_path.write_text(html)

    print(f"Graph saved to {out_path}")
    print(f"  Nodes: {G.number_of_nodes()} ({G.number_of_nodes() - G.number_of_edges()} may be isolated)")
    print(f"  Edges: {G.number_of_edges()}")
    print(f"  Domains: {len(domain_color)}")


def main():
    print("Loading data...")
    node_types = load_node_types()
    edge_types = load_edge_types()
    relations = load_relations()

    print(f"  {len(node_types)} node types, {len(edge_types)} edge types, {len(relations)} relations")

    print("Building graph...")
    G, domain_color = build_graph(node_types, edge_types, relations)

    print("Rendering...")
    render(G, domain_color, node_types, edge_types, relations)


if __name__ == "__main__":
    main()
