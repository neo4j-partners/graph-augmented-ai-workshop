# Testing Plan

This document covers how to test the restructured workshop end-to-end and what work remains before the new flow is ready for students.

---

## Prerequisites

Before any testing begins, you need:

- A Databricks workspace with access to foundation model endpoints
- A **Dedicated** cluster with Maven library `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3` installed
- A running Neo4j Aura instance (or any Neo4j 5.x instance with bolt access)
- Databricks CLI configured locally with a profile
- The `labs/` folder imported into the Databricks workspace

---

## Phase 1: Generate Embeddings (lab_setup)

The embeddings JSON does not exist yet. This is the critical blocker. Nothing downstream works without it.

### Steps

1. **Configure the environment**

   ```bash
   cd lab_setup
   cp .env.example .env
   # Fill in: DATABRICKS_PROFILE, DATABRICKS_CLUSTER_ID, WORKSPACE_DIR,
   #          VOLUME_PATH, EMBEDDING_ENDPOINT
   ```

2. **Upload HTML files to the volume**

   The generate_embeddings script reads HTML from `{VOLUME_PATH}/html/`. Either run the setup notebook first (which copies HTML files to the volume) or upload them manually:

   ```bash
   databricks fs cp --recursive labs/Includes/data/html/ \
       dbfs:/Volumes/<catalog>/<schema>/<volume>/html/ \
       --profile <profile>
   ```

3. **Upload the script to the workspace**

   ```bash
   ./upload.sh
   ```

   Verify: `databricks workspace ls $WORKSPACE_DIR/agent_modules --profile <profile>` should show `generate_embeddings.py`.

4. **Submit the job**

   ```bash
   ./submit.sh
   ```

   The script checks cluster state before submitting. Watch the job output in the Databricks UI for:
   - `[1/4] Listing HTML files...` should find 14 files
   - `[2/4] Processing HTML files...` should produce ~20 chunks across 14 documents
   - `[3/4] Generating embeddings...` should complete without rate limit errors
   - `[4/4] Writing output...` should write JSON to the volume

5. **Validate the output JSON**

   Download the file from `{VOLUME_PATH}/embeddings/document_chunks_embedded.json` and check:

   - Top-level keys: `metadata`, `documents`, `chunks`
   - `metadata.embedding_model` is `"databricks-gte-large-en"`
   - `metadata.embedding_dimensions` is `1024`
   - `documents` array has 14 entries, each with `document_id`, `filename`, `document_type`, `title`, `source_path`, `char_count`, `entity_references`
   - `chunks` array has entries with `chunk_id`, `document_id`, `index`, `text`, `metadata`, `embedding`
   - Each `embedding` is a list of exactly 1024 floats
   - Every chunk's `document_id` matches a document in the `documents` array

6. **Commit to the repo**

   ```bash
   cp document_chunks_embedded.json labs/Includes/data/embeddings/
   git add labs/Includes/data/embeddings/document_chunks_embedded.json
   git commit -m "Add pre-computed embeddings"
   ```

7. **Clean up**

   ```bash
   ./clean.sh
   ```

### What Can Go Wrong

- **`databricks_langchain` not installed on the cluster.** The `DatabricksEmbeddings` class comes from this package. Databricks Runtime ML includes it; standard runtime may not. If the import fails, install `databricks-langchain` as a cluster library or switch to the REST API directly.
- **`beautifulsoup4` not installed.** Same situation. ML Runtime includes it; standard runtime may not. Install as a cluster library if needed.
- **Rate limiting on the embedding endpoint.** The script batches 16 texts at a time. If rate limited, reduce `batch_size` in `generate_embeddings_databricks()` or add a `time.sleep()` between batches.
- **File read errors.** The script uses standard Python `open()` to read HTML files from the volume. If a file is missing or unreadable, it will fail with a clear error.

---

## Phase 2: Test the Setup Notebook (0 - Required Setup)

Run this on a clean workspace where the catalog does not already exist.

### Steps

1. Open `labs/0 - Required Setup` in the Databricks notebook UI
2. Attach to the Dedicated cluster
3. Run all cells

### What to Verify

- **Catalog creation.** A catalog named `neo4j_workshop_<username>` should appear in Unity Catalog. Confirm via `SHOW CATALOGS` or the UI.
- **Schema creation.** Schema `raw_data` exists within the catalog.
- **Volume creation.** Volume `source_files` exists within the schema.
- **Data copy.** The volume should contain:
  - `csv/` with 7 CSV files (accounts, banks, companies, customers, portfolio_holdings, stocks, transactions)
  - `html/` with 14 HTML files
  - `embeddings/document_chunks_embedded.json` (once Phase 1 is complete)
- **Widget prompts.** The notebook should prompt for Neo4j URI, username, and password via Databricks widgets.
- **Secret creation.** After entering credentials, verify:
  ```python
  dbutils.secrets.list("neo4j-creds")
  ```
  Should return keys: `username`, `password`, `url`, `volume_path`.
- **Neo4j connection.** The verification step should connect successfully and print the server version.
- **Idempotency.** Run the notebook a second time. It should not fail on "catalog already exists" or "scope already exists" errors. Everything should pass cleanly.

### What Can Go Wrong

- **`pyyaml` not available.** The setup orchestrator reads `config.yaml` with PyYAML. This package is included in Databricks Runtime ML but may be missing from standard runtimes. If `import yaml` fails, install `pyyaml` as a cluster library.
- **Permission errors on catalog creation.** The user needs `CREATE CATALOG` privilege. If this fails, the student needs their workspace admin to grant the privilege.
- **WorkspaceClient secrets API permission.** Creating secret scopes requires workspace-level permissions. If `w.secrets.create_scope()` fails with a 403, the student lacks the necessary privileges.
- **Workspace path resolution.** The notebook computes its own workspace path to find `config.yaml`. If the notebook is not in the expected location (e.g., it was copied to a different folder), the config path will be wrong. The error message should say which path it tried.

---

## Phase 3: Test the Import Notebook (1 - Neo4j Import)

Run this immediately after the setup notebook, with a clean (empty) Neo4j database.

### Steps

1. Open `labs/1 - Neo4j Import` in the Databricks notebook UI
2. Attach to the same Dedicated cluster
3. Run all cells

### What to Verify

- **Database cleared.** The first step deletes all existing nodes and relationships. Confirm via `MATCH (n) RETURN count(n)` returning 0.
- **Constraints created.** 9 uniqueness constraints (Customer, Bank, Account, Company, Stock, Position, Transaction, Document, Chunk).
- **Structured data loaded.** Verify node counts:
  - Customer nodes (from customers.csv)
  - Account nodes (from accounts.csv)
  - Bank nodes (from banks.csv)
  - Company nodes (from companies.csv)
  - Stock nodes (from stocks.csv)
  - Position nodes (from portfolio_holdings.csv)
  - Transaction nodes (from transactions.csv)
- **Relationships created.** 7 relationship types: OWNS, HELD_AT, PERFORMS, BENEFITS, HOLDS, OF, ISSUED_BY.
- **Document graph loaded.** 14 Document nodes and 20 Chunk nodes, each with an `embedding` property (list of 1024 floats).
- **Document relationships.** FROM_DOCUMENT, NEXT_CHUNK, and DESCRIBES relationships exist.
- **Vector index.** A vector index named `chunk_embedding_index` exists on Chunk nodes with 1024 dimensions and cosine similarity.
- **Full-text index.** A full-text index exists on Chunk.text.
- **Vector search works.** Run a sample vector query in Neo4j Browser:
  ```cypher
  CALL db.index.vector.queryNodes('chunk_embedding_index', 5, <any-embedding-vector>)
  YIELD node, score
  RETURN node.chunk_id, node.document_title, score
  ```

### What Can Go Wrong

- **Spark Connector not installed.** The notebook will fail immediately at the first `df.write.format("org.neo4j.spark.DataSource")` call. The cluster must have the Neo4j Maven library installed. This is the most common failure mode.
- **Embeddings JSON missing.** If Phase 1 was not completed, the import will fail at `load_and_write_document_graph()` with a FileNotFoundError. The structured CSV data will have loaded successfully up to that point.
- **Neo4j connection refused.** The Aura instance may be paused, or the firewall may block the Databricks cluster's outbound traffic. Check that the Neo4j URI is reachable from the cluster.
- **neo4j Python driver not installed.** The `clear_database()` and `load_and_write_document_graph()` functions import `from neo4j import GraphDatabase`. This package must be on the cluster. Databricks Runtime ML includes it; standard runtime may not.

---

## Phase 4: Validate Labs 4-7

These labs were not restructured, but their assumptions about the graph state changed. The import notebook now loads everything in one shot instead of across three labs.

### Lab 4 (Export to Lakehouse)

- Run the notebook. It should export Neo4j data to Delta tables without errors.
- Verify the exported tables contain the expected row counts.
- Check that the notebook does not reference `lab_2_neo4j_import` or any of the removed labs.

### Lab 5 (AI Agents)

- Follow the README instructions to create Genie and Knowledge agents in the Databricks UI.
- Verify the agents can query the Delta tables (from Lab 4) and the volume documents.

### Lab 6 (Supervisor Agent)

- Follow the README to configure the multi-agent supervisor.
- Run the sample queries and verify responses reference both structured and unstructured data.

### Lab 7 (Augmentation Agent)

- Run the DSPy-based augmentation agent.
- Verify it can read from Neo4j and suggest new relationships.
- Check that it does not depend on any removed files or directories.

---

## Remaining Work

### Blockers (must be done before the workshop is usable)

1. **Generate and commit the embeddings JSON.** Run `lab_setup/submit.sh` against a cluster with the HTML files in the volume. Download the output and commit it to `labs/Includes/data/embeddings/`. Without this file, the import notebook fails.

2. **End-to-end test on a clean workspace.** Run Phase 2 and Phase 3 back-to-back on a workspace where neither the catalog nor the Neo4j data exists. This is the student experience and must work without manual intervention.

### Should Fix

3. **Verify Python package availability on standard Databricks Runtime.** The import module uses `neo4j` (Python driver) and the setup orchestrator uses `pyyaml`. The embedding generator uses `beautifulsoup4` and `databricks-langchain`. Confirm which of these are included in the target runtime. If any are missing, either add `%pip install` cells to the notebooks or document ML Runtime as a requirement.

### Done

- ~~Remove the old `data/` directory at the repo root.~~ Removed. Labs 4-7 and solutions/ all read from the Databricks volume, not local files.
- ~~Remove `src/` directory.~~ Removed. Not referenced by any lab or solution.
- ~~Clean up root-level artifacts.~~ Already in `.gitignore` (`mlflow.db`, `mlruns/`, `results.json`).
- ~~Verify the `solutions/` directory still works.~~ Verified. No references to removed directories or old lab structure. All paths use `VOLUME_PATH` from `.env`.
- ~~Verify labs 4-7 for broken references.~~ Verified. No references to removed labs, no local `data/` paths. Cross-lab links are correct.
- ~~Add a validation cell at the end of the import notebook.~~ Already exists. `validate_import()` runs at the end of `run_full_import()` and prints node/relationship count summary.
- ~~Document the cluster library requirements.~~ README now lists both Maven and Python package requirements, with ML Runtime recommended.
