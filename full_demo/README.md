# Full Demo

This directory contains validation scripts that exercise each workshop lab end-to-end on a Databricks cluster, including the full graph enrichment pipeline.

## Prerequisites

```bash
cd full_demo
cp .env.example .env
# Edit .env with your values
```

| Variable | Description |
|----------|-------------|
| `DATABRICKS_PROFILE` | CLI profile name (`databricks configure --profile <name>`) |
| `DATABRICKS_CLUSTER_ID` | Existing all-purpose cluster ID |
| `DATABRICKS_WORKSPACE_DIR` | Remote path for uploaded scripts |
| `NEO4J_URI` | Neo4j connection URI |
| `NEO4J_USERNAME` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `DATABRICKS_VOLUME_PATH` | Unity Catalog Volume path (e.g., `/Volumes/catalog/schema/volume`) |
| `SUPERVISOR_AGENT_ENDPOINT` | Supervisor Agent endpoint name from Lab 6 |
| `EMBEDDING_ENDPOINT` | Embedding model endpoint (optional, defaults to `databricks-gte-large-en`) |

---

## Agent Modules

### Overview

Agent modules are standalone validation scripts that exercise each workshop lab by running its core logic as a one-shot Databricks job. Each script replicates a lab's data transformations, executes them headlessly on a cluster, and reports PASS/FAIL results. They serve as both a reference implementation and a regression suite for the workshop content.

### Quick Start

```bash
cd full_demo

# Upload all scripts to Databricks workspace
python -m cli upload --all

# Run in order
python -m cli submit test_hello.py        # 1. Verify cluster
python -m cli submit check_neo4j.py       # 2. Verify Neo4j connectivity
python -m cli submit run_lab2.py          # 3. Import CSV data into Neo4j
python -m cli submit verify_lab2.py       # 4. Read-only verification
python -m cli submit run_lab3.py          # 5. Load embeddings + vector indexes
python -m cli submit run_lab4.py          # 6. Export graph to Delta Lake
python -m cli submit run_lab7.py          # 7. DSPy augmentation analysis
```

Upload a single script or submit without waiting:

```bash
python -m cli upload run_lab2.py
python -m cli submit run_lab2.py --no-wait
```

Clean up remote workspace and job runs:

```bash
python -m cli clean                       # interactive confirmation
python -m cli clean --yes                 # skip confirmation
```

### Architecture

The scripts follow a linear pipeline that mirrors the workshop progression:

```
CSV files (Volume)
    |  [run_lab2.py]  Load 7 node types + 7 relationship types via Spark Connector
    v
Neo4j graph (764 nodes, 814 relationships)
    |  [verify_lab2.py]  Read-only count + constraint checks
    |
    |  [generate_embeddings.py]  Chunk HTML docs, generate vectors via foundation model
    |  [run_lab3.py]  Load embeddings, create vector + fulltext indexes
    v
Neo4j graph + Document/Chunk nodes + hybrid search indexes
    |  [run_lab4.py]  Export all node/relationship types to Delta Lake
    v
Unity Catalog Delta tables (14 tables)
    |  [run_lab7.py]  Full 8-step graph enrichment pipeline:
    |                  Gap analysis, 4 parallel DSPy analyses, instance resolution,
    |                  confidence filtering, Neo4j write-back
    v
Enriched Neo4j graph (new relationships with provenance metadata)
```

| Script | Lab | Destructive | Description |
|--------|-----|:-----------:|-------------|
| `test_hello.py` | -- | No | Smoke test: Python, Spark, Neo4j Spark Connector |
| `check_neo4j.py` | -- | No | Neo4j connectivity, node count, server version |
| `generate_embeddings.py` | -- | No | Chunk HTML, generate embeddings, write JSON to volume |
| `run_lab2.py` | 2 | Yes | Clear Neo4j, import all CSV data via Spark Connector |
| `verify_lab2.py` | 2 | No | Read-only verification of counts and constraints |
| `run_lab3.py` | 3 | Yes | Clear Document/Chunk nodes, load embeddings, create indexes |
| `run_lab4.py` | 4 | No | Export Neo4j to 14 Delta Lake tables |
| `run_lab7.py` | 7 | Configurable | Full enrichment pipeline: analysis, resolution, filtering, write-back (dry run by default) |

All scripts share a common execution pattern: `python -m cli upload` pushes files to the Databricks workspace, and `python -m cli submit` runs them as one-shot jobs. Environment variables from `.env` are passed as `KEY=VALUE` parameters. Each script exits with code 0 on success, code 1 on failure.
