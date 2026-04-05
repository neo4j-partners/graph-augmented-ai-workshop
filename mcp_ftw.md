# MCP FTW: How Databricks MCP Tools Could Supercharge the Solutions

An analysis of how the `solutions/` directory in the Graph-Augmented AI Workshop could be improved by leveraging Databricks MCP tools — replacing shell scripts, simplifying validation, and unlocking capabilities that don't exist in the current implementation.

---

## 1. Kill the Shell Scripts

The three shell scripts (`upload.sh`, `submit.sh`, `clean.sh`) total ~340 lines of bash that parse `.env` files, construct JSON payloads, and shell out to the Databricks CLI. MCP tools replace all of this with single function calls.

### upload.sh → `upload_to_workspace` + `upload_to_volume`

**Current**: 102 lines of bash that loads `.env`, calls `databricks workspace mkdirs`, `databricks workspace import`, and `databricks fs cp` for wheels.

**With MCP**:
- `upload_to_workspace` — upload scripts with a single call, handles directory creation automatically, supports globs (`*.py`) and folders, parallel upload threads
- `upload_to_volume` — upload wheels and data files to UC Volumes, also supports globs and folders

One MCP call replaces ~30 lines of bash per upload operation. No `.env` parsing, no `databricks workspace mkdirs`, no error handling boilerplate.

### submit.sh → `manage_jobs` + `manage_job_runs`

**Current**: 126 lines of bash that checks cluster state, builds job JSON with injected credentials, submits via `databricks jobs submit`, and polls for completion.

**With MCP**:
- `manage_jobs` (action: `create`) — create a job definition with tasks, environments, and dependencies. Idempotent: returns existing job if name matches.
- `manage_job_runs` (action: `run_now`) — trigger a job run with parameters (`python_params`, `python_named_params`)
- `manage_job_runs` (action: `wait`) — wait for completion with configurable timeout and poll interval, returns detailed results including logs
- `list_compute` (with `auto_select: true`) — auto-pick the best running cluster instead of hardcoding `DATABRICKS_CLUSTER_ID`

The MCP approach also unlocks **serverless execution** via `execute_code` — run Python scripts directly without a cluster, no job definition needed.

### clean.sh → `delete_from_workspace` + `manage_jobs`

**Current**: 110 lines of bash that deletes workspace directories and iterates through job runs to delete them.

**With MCP**:
- `delete_from_workspace` — delete the remote workspace directory (with safety checks against protected paths)
- `manage_job_runs` (action: `list`) — list job runs with filters
- `manage_jobs` (action: `delete`) — delete job definitions
- `list_tracked_resources` — see everything MCP has created, then `delete_tracked_resource` to clean up

---

## 2. Direct Code Execution (Skip the Job Dance)

The current flow for running a validation script:

```
build wheel → upload to volume → upload script → create job JSON → submit job → poll for status → fetch logs
```

With `execute_code`:

```
execute_code(file_path="agent_modules/run_lab2.py", compute_type="serverless")
```

Done. One call. The MCP tool handles:
- Serverless or cluster compute (auto-detected)
- File upload and execution
- Timeout management (up to 30 min for serverless)
- Output capture and return

For scripts that need state persistence across calls (like interactive debugging), `execute_code` supports `context_id` to reuse execution contexts on clusters.

---

## 3. Replace the Custom MAS Client

`mas_client.py` (100 lines) builds an OpenAI-compatible client to query the Supervisor Agent endpoint. The MCP tool `query_serving_endpoint` does this natively:

**Current** (`mas_client.py`):
```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
client = w.serving_endpoints.get_open_ai_client()
response = client.chat.completions.create(
    model=endpoint_name,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=4096
)
```

**With MCP**:
```
query_serving_endpoint(
    name="mas-3ae5a347-endpoint",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=4096
)
```

Plus `get_serving_endpoint_status` can verify the MAS endpoint is `READY` before running Lab 7 — something the current code doesn't do (it just fails with a cryptic error if the endpoint isn't ready).

---

## 4. Delta Lake Verification Without Spark

Lab 4 exports Neo4j data to 14 Delta tables. Currently, `run_lab4.py` uses Spark to verify the export. With MCP:

- `get_table_stats_and_schema` — get schema, row counts, and column stats for all 14 tables in one call (supports glob patterns like `["neo4j_*"]`)
- `execute_sql` — run verification queries directly on a SQL warehouse:
  ```sql
  SELECT COUNT(*) FROM catalog.schema.neo4j_customers
  WHERE customer_id IS NOT NULL
  ```
- No Spark session needed. No cluster needed. Serverless SQL warehouse handles it.

This also enables **post-export dashboards** — `create_or_update_dashboard` could generate an AI/BI dashboard showing graph export statistics, data quality checks, and entity relationship summaries.

---

## 5. Vector Search Without Neo4j Python Driver

Lab 3 creates vector and fulltext indexes in Neo4j. The MCP tools offer a parallel Databricks-native path:

- `create_or_update_vs_endpoint` — provision a Vector Search endpoint
- `create_or_update_vs_index` — create a Delta Sync index with managed embeddings (auto-embeds using `databricks-gte-large-en`) or self-managed embeddings (use the pre-computed 1024-dim embeddings from the lab)
- `query_vs_index` — similarity search with filters, supports hybrid (vector + keyword) search

This doesn't replace Neo4j's graph-native vector search, but it creates a **comparison point** for the workshop: same embeddings, same queries, graph-augmented vs. flat vector search. That's a powerful teaching moment.

---

## 6. Knowledge Assistant for Document Q&A

The workshop has 14 HTML documents and 14 text profiles (customer profiles, company analyses, investment guides, etc.) stored in a UC Volume. The MCP tool `manage_ka` can create a Knowledge Assistant from these documents in one call:

```
manage_ka(
    action="create_or_update",
    name="Graph Workshop KA",
    volume_path="/Volumes/catalog/schema/volume/html",
    description="Q&A over financial documents used in the graph workshop",
    instructions="Cite specific documents when answering. Focus on investment themes and customer relationships."
)
```

This creates a RAG-powered document Q&A agent — no code, no embeddings pipeline, no vector index setup. The KA handles chunking, embedding, indexing, and retrieval automatically.

The existing MAS in Lab 6 already orchestrates a KA + Genie agent. But having the MCP tool create the KA means the entire Lab 6 setup could be done programmatically instead of through the UI.

---

## 7. Genie Space for Natural Language SQL

Lab 4 exports the Neo4j graph to Delta tables. Those tables are perfect Genie candidates:

```
create_or_update_genie(
    display_name="Graph Financial Explorer",
    table_identifiers=[
        "catalog.schema.neo4j_customers",
        "catalog.schema.neo4j_accounts",
        "catalog.schema.neo4j_transactions",
        "catalog.schema.neo4j_companies",
        "catalog.schema.neo4j_stocks",
        "catalog.schema.neo4j_portfolio_holdings"
    ],
    description="Explore the financial knowledge graph exported from Neo4j",
    sample_questions=[
        "Which customers have accounts at multiple banks?",
        "What are the top 10 stock holdings by value?",
        "Show me all transactions over $10,000 in the last quarter"
    ]
)
```

Workshop participants could then ask natural language questions about the exported graph data — bridging the graph-to-SQL gap that the workshop teaches.

---

## 8. MAS Creation via MCP

Lab 6 creates a Supervisor Agent through the UI. The `manage_mas` MCP tool can do this programmatically:

```
manage_mas(
    action="create_or_update",
    name="Graph Augmentation MAS",
    agents=[
        {
            "name": "genie_agent",
            "description": "Answers questions about financial data using SQL",
            "genie_space_id": "<space_id>"
        },
        {
            "name": "knowledge_agent",
            "description": "Answers questions from financial documents and reports",
            "ka_tile_id": "<ka_tile_id>"
        }
    ],
    description="Routes financial questions to SQL or document-based agents",
    instructions="Route data/numbers questions to genie_agent. Route document/analysis questions to knowledge_agent."
)
```

This means Labs 5-6 (KA creation + MAS creation) could be fully automated, freeing workshop time for the interesting parts (graph augmentation analysis in Lab 7).

---

## 9. UC Namespace Bootstrapping

The workshop requires a catalog, schema, and volume to exist before any lab runs. Currently this is manual setup. MCP tools can bootstrap the entire namespace:

- `manage_uc_objects` (object_type: `catalog`, action: `create`) — create the workshop catalog
- `manage_uc_objects` (object_type: `schema`, action: `create`) — create the schema
- `manage_uc_objects` (object_type: `volume`, action: `create`) — create the data volume
- `manage_uc_grants` — grant permissions to workshop participants
- `upload_to_volume` — seed the volume with CSV and HTML data files

A single "bootstrap" flow could set up the entire workshop environment from scratch.

---

## 10. Resource Lifecycle Management

The current `clean.sh` only cleans workspace files and job runs. A full cleanup needs to handle:

- Workspace files
- Job definitions and runs
- UC volumes, schemas, catalogs
- Genie Spaces
- Knowledge Assistants
- MAS endpoints
- Vector Search indexes and endpoints
- Dashboards

`list_tracked_resources` returns every resource the MCP server has created, organized by type. `delete_tracked_resource` removes them — both from the manifest and optionally from Databricks. This is complete lifecycle management that `clean.sh` can't touch.

---

## Summary: What Changes

| Current Approach | MCP Replacement | Lines Saved | New Capability |
|---|---|---|---|
| `upload.sh` (102 lines) | `upload_to_workspace` + `upload_to_volume` | ~100 | Parallel uploads, glob support |
| `submit.sh` (126 lines) | `manage_jobs` + `manage_job_runs` | ~120 | Serverless execution, auto-cluster |
| `clean.sh` (110 lines) | `delete_from_workspace` + `list_tracked_resources` | ~110 | Full resource lifecycle cleanup |
| `mas_client.py` (100 lines) | `query_serving_endpoint` | ~95 | Endpoint health checks |
| Manual cluster management | `list_compute` + `manage_cluster` | N/A | Auto-select, state monitoring |
| Manual UC setup | `manage_uc_objects` + `manage_uc_grants` | N/A | Automated namespace bootstrapping |
| No dashboards | `create_or_update_dashboard` | N/A | Graph export visualization |
| No Genie | `create_or_update_genie` | N/A | Natural language SQL over graph data |
| UI-based KA/MAS | `manage_ka` + `manage_mas` | N/A | Programmatic agent setup (Labs 5-6) |
| Neo4j-only vector search | `create_or_update_vs_index` + `query_vs_index` | N/A | Databricks vs. Neo4j vector search comparison |

**Bottom line**: MCP tools eliminate ~330 lines of shell scripts, ~100 lines of custom Python client code, and unlock 6 capabilities that don't exist in the current solution — dashboards, Genie, programmatic KA/MAS, namespace bootstrapping, resource lifecycle management, and Databricks-native vector search.
