# Remote Validation Proposal

## Problem Statement

The lab notebooks in this project can only be validated by manually opening each one in a Databricks workspace and running cells interactively. There is no way to programmatically verify that the labs work end-to-end against a live Databricks cluster and Neo4j instance. If a code change breaks a lab, the only way to find out is to run through the entire workshop by hand.

The reference project (`databricks-neo4j-lab/lab_setup/notebook_validation`) solves this problem with a pattern that extracts notebook logic into standalone Python scripts, uploads them to a Databricks workspace, and submits them as one-shot jobs. Each script runs the same operations as its corresponding notebook and prints PASS/FAIL assertions to verify correctness.

This project has no equivalent infrastructure.

## Proposed Solution

Create a `solutions/` directory at the project root that mirrors the reference implementation's `notebook_validation/` pattern. This directory will contain:

1. **Standalone Python scripts** -- one per testable lab -- that replicate the core logic from each notebook as a script that can run headlessly on a Databricks cluster.
2. **Shell scripts** to upload those Python scripts to a remote Databricks workspace and submit them as jobs.
3. **A `.env` configuration file** that holds Databricks and Neo4j credentials, cluster ID, and volume paths.

When a developer wants to validate the labs, they run two commands: `./upload.sh --all` to push scripts to the workspace, then `./submit.sh <script_name>` to run any lab as a remote job. The job output shows PASS/FAIL results for each verification check.

## Scope: What Gets a Validation Script

| Lab | Testable? | Why / Why Not |
|-----|-----------|---------------|
| Lab 1 -- Databricks Upload | Yes | Uploads CSV and HTML files to a Unity Catalog Volume. Can verify files exist after upload. |
| Lab 2 -- Neo4j Import | Yes | Imports CSV data into Neo4j via Spark Connector. Can verify node/relationship counts. |
| Lab 3 -- Vector Embeddings | Yes | Processes HTML documents, generates embeddings, creates vector indexes. Can verify chunk counts, index existence, and search results. |
| Lab 4 -- Neo4j to Lakehouse | Yes | Exports graph data to Delta Lake tables. Can verify table existence and row counts. |
| Lab 5 -- AI Agents | No | UI-only Databricks Genie/Knowledge agent configuration. Nothing to run as code. |
| Lab 6 -- Multi-Agent Supervisor | No | UI-only agent orchestration setup. Nothing to run as code. |
| Lab 7 -- Augmentation Agent | Yes | Runs DSPy analysis pipeline. Can verify structured output and graph suggestions. |

## Requirements

### Directory Structure

The `solutions/` directory will live at the project root and contain:

- `solutions/.env.example` -- Template with all required configuration variables.
- `solutions/.env` -- Actual credentials (git-ignored).
- `solutions/upload.sh` -- Uploads Python scripts to the Databricks workspace.
- `solutions/submit.sh` -- Submits a script as a one-shot Databricks job and streams output.
- `solutions/cluster_utils.sh` -- Shared helper that checks cluster state and auto-starts it if terminated.
- `solutions/clean.sh` -- Removes uploaded scripts and job run history from the workspace.
- `solutions/agent_modules/` -- Directory containing the standalone Python validation scripts.

### Configuration (.env)

The `.env` file will contain:

- `DATABRICKS_PROFILE` -- Databricks CLI profile name.
- `DATABRICKS_CLUSTER_ID` -- ID of an existing all-purpose cluster to run jobs on.
- `WORKSPACE_DIR` -- Remote workspace path where scripts get uploaded (e.g., `/Workspace/Users/you@example.com/neo4j_demo_validation`).
- `NEO4J_URI` -- Neo4j Aura connection URI.
- `NEO4J_USERNAME` -- Neo4j username.
- `NEO4J_PASSWORD` -- Neo4j password.
- `VOLUME_PATH` -- Unity Catalog Volume path (e.g., `/Volumes/catalog/schema/volume`).

### Shell Scripts

**upload.sh** -- Uses `databricks workspace import` to push Python files from `agent_modules/` to the remote workspace. Supports uploading a single file by name or all files with `--all`.

**submit.sh** -- Builds a job JSON payload with `spark_python_task`, injects Neo4j and Databricks credentials from `.env` as `--arg value` parameters, and submits via `databricks jobs submit`. Uses Python to serialize parameters (safely handles special characters in passwords). Waits for completion and prints job output.

**cluster_utils.sh** -- Before submitting a job, checks cluster state via `databricks clusters get`. If the cluster is TERMINATED, starts it and polls until RUNNING. Times out after 10 minutes.

**clean.sh** -- Deletes the remote `WORKSPACE_DIR` and optionally cleans up job run history.

### Validation Scripts (agent_modules/)

Each script follows the same pattern from the reference implementation:

1. Parse credentials and paths from command-line arguments using `argparse`.
2. Run the same operations as the corresponding notebook.
3. Print PASS/FAIL for each verification check using a `record()` helper.
4. Print a summary table at the end with total/passed/failed counts.
5. Exit with code 0 on success, non-zero on any failure.

The scripts and their checks:

**test_hello.py** -- Smoke test. Verifies Python, Spark, and the Neo4j Spark Connector jar are available on the cluster. No credentials needed.

**check_neo4j.py** -- Connectivity test. Verifies Neo4j is reachable, reports node count and server version.

**run_lab1.py** -- Lab 1 validation. Uses the Databricks SDK to upload CSV and HTML files from the data directory to the Unity Catalog Volume. Verifies each file exists after upload.

**run_lab2.py** -- Lab 2 validation. Destructive (clears Neo4j first). Reads CSV files from the Volume using Spark, writes nodes and relationships to Neo4j via the Spark Connector. Verifies counts for all 7 node types (Customer, Account, Bank, Stock, Company, Position, Transaction) and all 7 relationship types.

**verify_lab2.py** -- Lab 2 read-only verification. Runs Cypher queries against Neo4j to verify node counts, relationship counts, and constraint existence without modifying data.

**run_lab3.py** -- Lab 3 validation. Destructive (clears document nodes). Processes HTML files, generates embeddings (using Databricks Foundation Model endpoint), creates Document and Chunk nodes in Neo4j, builds vector and fulltext indexes. Verifies chunk counts, index existence, and runs a sample hybrid search.

**run_lab4.py** -- Lab 4 validation. Reads nodes and relationships from Neo4j using the Spark Connector and writes them as Delta Lake tables. Verifies each table exists and has the expected row count.

**run_lab7.py** -- Lab 7 validation. Runs the DSPy augmentation agent pipeline. Verifies that the DSPy modules produce structured output matching the expected Pydantic schemas and that analysis results contain suggested entities, relationships, and attributes.

### How Code Gets Extracted

Each validation script is a standalone rewrite of the corresponding notebook's logic, not a direct copy-paste. The extraction process for each lab:

1. Read the notebook (`.ipynb`) and its companion Python script (`.py`) to identify the core operations.
2. Pull the essential logic (data loading, transformations, Neo4j writes, searches) into the validation script.
3. Replace any interactive/display code (`display()`, widget inputs, markdown cells) with `print()` statements and PASS/FAIL assertions.
4. Replace hardcoded credentials and paths with `argparse` parameters.
5. Replace any Databricks notebook-specific APIs (`dbutils`, `%sql` magic) with equivalent SDK or Spark calls.

### Cluster Prerequisites

The target cluster must have:

- Neo4j Spark Connector Maven package (`org.neo4j:neo4j-connector-apache-spark_2.13:5.3.1_for_spark_3`)
- Python libraries: `neo4j`, `neo4j-graphrag`, `sentence-transformers`, `beautifulsoup4`, `dspy`, `pydantic`
- Access to the Unity Catalog Volume containing the lab data files
- Single-user (Dedicated) access mode (required by the Neo4j Spark Connector)

## Implementation Plan

### Phase 1: Foundation

- [ ] Create the `solutions/` directory structure
- [ ] Write `.env.example` with all required variables
- [ ] Port `upload.sh`, `submit.sh`, `cluster_utils.sh`, and `clean.sh` from the reference implementation, adapted for this project's variable names and paths
- [ ] Write `test_hello.py` and `check_neo4j.py` (quick wins that validate the infrastructure works)

### Phase 2: Core Lab Scripts

- [ ] Extract Lab 1 logic into `run_lab1.py`
- [ ] Extract Lab 2 logic into `run_lab2.py` and `verify_lab2.py`
- [ ] Extract Lab 3 logic into `run_lab3.py`
- [ ] Extract Lab 4 logic into `run_lab4.py`

### Phase 3: Advanced Lab and Polish

- [ ] Extract Lab 7 logic into `run_lab7.py`
- [ ] End-to-end test: run all scripts in sequence against a live cluster
- [ ] Document the full workflow in the solutions README

## Verification

Each phase is verified by running the scripts against a live Databricks cluster and Neo4j instance. The final verification is a full sequential run:

```
./upload.sh --all
./submit.sh test_hello.py
./submit.sh check_neo4j.py
./submit.sh run_lab1.py
./submit.sh run_lab2.py
./submit.sh verify_lab2.py
./submit.sh run_lab3.py
./submit.sh run_lab4.py
./submit.sh run_lab7.py
```

All scripts must exit with code 0 and report zero FAIL assertions.
