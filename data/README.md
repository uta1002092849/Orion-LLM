# Freebase Knowledge Graph Data

## File Name Mapping

| Original Name | Current Name | Size |
|----------------|--------------|------|
| `freebase_node_types` | `node_types.tsv` | 65K |
| `freebase_edge_types` | `edge_types.tsv` | 431K |
| `freebase_edgetype_relation_id-nointermediateedges-NOconcat-clean-newProp` | `relation_schema.csv` | 47K |
| `entity_types` | `entity_types.csv` | 863M |
| `trainingDataFreebase_3_50_700-NOconcat-newProp-shuffled` | `training_sequences.csv` | 2.1G |

## File Descriptions

### node_types.tsv (2,060 lines)

Maps numeric node type IDs to Freebase type paths (ontology classes).

- **Format:** Tab-separated, 2 columns — `<type_id>\t<freebase_type_path>`
- **Example:** `112\t/location/location`
- **ID range:** ~89 to ~2148

### edge_types.tsv (7,881 lines)

Maps numeric edge type IDs to Freebase property/relation paths.

- **Format:** Tab-separated, 2 columns — `<edge_id>\t<freebase_property_path>`
- **Example:** `47178864\t/comedy/comedy_group_membership/group`
- **ID range:** ~47178864 to ~47186744
- Some entries contain compound paths joined by `-`, representing paths that traverse intermediate/CVT nodes.

### relation_schema.csv (2,663 lines)

Defines the schema for each edge type by mapping it to valid source and target node types.

- **Format:** Comma-separated, 3 columns — `<source_node_type_id>,<edge_type_id>,<target_node_type_id>`
- **Example:** `92,47178872,90` (comedian --comedy_genres--> comedy_genre)
- Original filename flags:
  - `nointermediateedges`: Intermediate/CVT nodes removed; edges connect meaningful types directly.
  - `NOconcat`: Edge paths are not concatenated.
  - `clean`: Filtered and cleaned.
  - `newProp`: Uses an updated property set.

### entity_types.csv (~67M lines)

Assigns node type IDs to every entity in the Freebase graph.

- **Format:** Comma-separated, 2 columns — `<node_type_id>,<entity_id>`
- **Example:** `2101,2149`
- Entities can appear on multiple lines with different type IDs (multi-typed entities).

### training_sequences.csv (~11.5M lines)

Training data for a model. Each line encodes an entity's graph neighborhood as a sequence of type and relation IDs.

- **Format:** Comma-separated, variable-length rows (5 to 254 columns). Each row ends with `1,1` as an end-of-sequence sentinel.
- **Example:** `1076,421,628,47178982,1095,582,940,112,117,234,...,1,1`
- Values are a mix of:
  - Node type IDs (small integers from `node_types.tsv`)
  - Edge type IDs (large ~47M integers from `edge_types.tsv`)
- Original filename parameters: `3_50_700` likely refers to walk/sampling hyperparameters (e.g., 3-hop, 50 walks, max 700 tokens). "Shuffled" indicates rows are randomly ordered.
