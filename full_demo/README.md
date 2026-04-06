# Remote Validation

Standalone Python scripts that validate the workshop labs by running them as one-shot Databricks jobs. Each script replicates a lab's core logic, executes it headlessly on a cluster, and reports PASS/FAIL results.

## Prerequisites

- **Databricks SDK** (`databricks-sdk`) installed (included in project dependencies)
- **Cluster** running in Dedicated access mode with:
  - Neo4j Spark Connector (`org.neo4j:neo4j-connector-apache-spark_2.13:5.3.1_for_spark_3`)
  - Python libraries: `neo4j`, `beautifulsoup4`
  - Access to Unity Catalog Volumes
- **Neo4j instance** (Aura or self-hosted) accessible from the cluster
- **Lab data** (CSV and HTML files) uploaded to a Unity Catalog Volume

## Setup

```bash
cd full_demo
cp .env.example .env
# Edit .env with your values
```

Required `.env` variables:

| Variable | Description |
|----------|-------------|
| `DATABRICKS_PROFILE` | CLI profile name (`databricks configure --profile <name>`) |
| `DATABRICKS_CLUSTER_ID` | Existing all-purpose cluster ID |
| `DATABRICKS_WORKSPACE_DIR` | Remote path for uploaded scripts (e.g., `/Workspace/Users/you@example.com/graph_validation`) |
| `NEO4J_URI` | Neo4j connection URI |
| `NEO4J_USERNAME` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `DATABRICKS_VOLUME_PATH` | Unity Catalog Volume path (e.g., `/Volumes/catalog/schema/volume`) |
| `SUPERVISOR_AGENT_ENDPOINT` | Supervisor Agent endpoint name from Lab 6 (for Lab 7) |
| `EMBEDDING_ENDPOINT` | Embedding model endpoint for `generate_embeddings.py` (optional, defaults to `databricks-gte-large-en`) |

## Usage

Upload scripts, then submit them as jobs:

```bash
python -m cli upload --all                # upload all scripts
python -m cli submit test_hello.py        # smoke test
python -m cli submit check_neo4j.py       # connectivity check
python -m cli submit run_lab2.py          # Lab 2 (destructive)
python -m cli submit verify_lab2.py       # Lab 2 read-only verify
python -m cli submit run_lab3.py          # Lab 3 (destructive for doc nodes)
python -m cli submit run_lab4.py          # Lab 4
python -m cli submit generate_embeddings.py # regenerate embeddings (admin)
```

Upload a single script:

```bash
python -m cli upload run_lab2.py          # upload one file
```

Submit without waiting:

```bash
python -m cli submit run_lab2.py --no-wait
```

Clean up remote workspace and job runs:

```bash
python -m cli clean                       # interactive confirmation
python -m cli clean --yes                 # skip confirmation
python -m cli clean --workspace           # only delete remote scripts
python -m cli clean --runs                # only delete job run history
```

## Scripts

### Infrastructure

| Script | Description |
|--------|-------------|
| `test_hello.py` | Smoke test — verifies Python, Spark, and the Neo4j Spark Connector are available |
| `check_neo4j.py` | Connectivity check — verifies Neo4j is reachable, reports node count and server version |
| `generate_embeddings.py` | Reads HTML files from the volume, chunks text, generates embeddings via Databricks endpoint, writes JSON output |

### Lab Validation

| Script | Lab | Destructive | Description |
|--------|-----|:-----------:|-------------|
| `run_lab2.py` | Lab 2 | Yes | Clears Neo4j, imports CSV data via Spark Connector, validates 7 node types (764 nodes) and 7 relationship types (814 rels) |
| `verify_lab2.py` | Lab 2 | No | Read-only verification of node counts, relationship counts, constraints, and sample queries |
| `run_lab3.py` | Lab 3 | Yes | Clears Document/Chunk nodes, loads pre-computed embeddings JSON (14 docs, 20 chunks, 1024-dim), writes Document and Chunk nodes to Neo4j, creates vector and fulltext indexes, verifies search |
| `run_lab4.py` | Lab 4 | No | Reads nodes and relationships from Neo4j via Spark Connector, writes 14 Delta tables to Unity Catalog, verifies row counts |
| `run_lab7.py` | Lab 7 | No | Queries Supervisor Agent for gap analysis, runs 4 DSPy analyses (investment themes, new entities, missing attributes, implied relationships) concurrently via `dspy.Parallel`, validates structured Pydantic output |

### Execution Order

Scripts with destructive operations should run in this order:

```
test_hello.py       # 1. verify cluster
check_neo4j.py      # 2. verify Neo4j
run_lab2.py         # 3. import data (clears Neo4j)
verify_lab2.py      # 4. verify import
run_lab3.py         # 5. vector pipeline (clears doc nodes)
run_lab4.py         # 6. export to Delta Lake
run_lab7.py         # 7. DSPy augmentation agent (requires Supervisor Agent from Lab 6)
```

## How It Works

- `python -m cli upload` pushes Python files to the Databricks workspace via the Databricks SDK
- `python -m cli submit` checks that the cluster is RUNNING (auto-starts if terminated), passes all non-core `.env` keys as `KEY=VALUE` parameters, and submits a one-shot job via the SDK Jobs API
- Each script parses `KEY=VALUE` parameters from `sys.argv` into `os.environ` at startup, then reads configuration via `os.environ` / `os.getenv()`
- Scripts exit with code 0 on success, code 1 on any failure
- `python -m cli clean` removes the remote workspace directory and deletes job runs matching the `graph_validation:` prefix
