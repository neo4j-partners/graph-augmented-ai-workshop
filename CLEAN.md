# Proposal: Restructure to Databricks Academy Format

## What This Is

A plan to restructure the graph-augmented-ai-workshop to follow the same patterns used by the Databricks Academy labs (like the AI/BI Dashboards and Lakebase AI Integration workshops). The goal is to replace the current multi-step, multi-environment setup with a single setup notebook and a single Neo4j import step, then let each remaining lab focus purely on teaching.

---

## Decisions Made

1. **Drop local development entirely.** Everything runs on Databricks. No .env files, no uv, no dual execution paths.
2. **Pre-compute embeddings.** Create a lab_setup folder with a script that generates embeddings ahead of time using the latest Databricks embedding model. The pre-computed embeddings ship with the workshop data. Students are told the embeddings already exist and shown how they were created, but they do not need to generate them.
3. **Bundle data in the repo.** All CSV, HTML, and pre-computed embedding files live in Includes/data/ and get copied to the student's volume during setup. No Marketplace share.
4. **No Vocareum support.** This is for field workshops and self-guided use only.
5. **Keep the Spark Connector.** Students use a Dedicated cluster with the Neo4j Spark Connector Maven library. This is a real integration pattern worth teaching despite the setup cost.
6. **Only convert Labs 1, 2, and 3.** Labs 1 (upload), 2 (import), and 3 (embeddings) get folded into the new simplified flow (setup notebook plus single import). Labs 4 through 7 stay in their current structure.

---

## The lab_setup Folder

A new lab_setup folder provides the tooling to pre-compute embeddings before the workshop ships. This follows the same pattern as the solutions/ folder: a self-contained package with shell scripts to upload code to Databricks and submit it as a job.

### What It Does

The lab_setup folder contains a Python script that:

- Reads the 14 HTML files from the Databricks volume (uploaded there by the setup notebook or manually)
- Parses each HTML file using BeautifulSoup (same logic as the current Lab 3 processing pipeline)
- Splits each document into chunks using a fixed-size splitter (4000 characters, 200 character overlap)
- Calls the latest Databricks foundation model embedding endpoint (currently databricks-gte-large-en, 1024 dimensions) to generate a vector for each chunk
- Writes the results to a JSON file that contains all documents, chunks, and their embeddings
- That JSON file then gets committed to the repo under Includes/data/embeddings/ and ships with the workshop

### How It Runs

Following the solutions/ pattern:

- upload.sh copies the Python script to the Databricks workspace
- submit.sh submits it as a job on the Dedicated cluster
- The script reads HTML files from the volume, generates embeddings, and writes the output JSON back to the volume
- The workshop author downloads the JSON file and commits it to the repo

The script only needs to run once (or whenever the HTML source documents change). It is not student-facing.

### What the Output Looks Like

A single JSON file (or a small set of JSON files) containing:

- For each document: document ID, filename, document type, title, source path
- For each chunk within a document: chunk ID, document ID, chunk index, text content, and the embedding vector (a list of 1024 floats)
- Metadata: which embedding model was used, dimensions, when it was generated

This file is small enough to commit to git. Fourteen HTML documents produce 20 chunks. At 1024 floats per chunk encoded as JSON, the file is about 544KB.

### Why This Approach

- Students do not wait for embedding generation during the workshop
- The import step loads everything in one shot: structured CSV data plus document graph with pre-computed embeddings
- The embedding model and parameters are documented in the JSON metadata, so students can see exactly how the embeddings were created
- If the embedding model changes or the HTML documents change, the workshop author reruns the lab_setup script and commits the updated JSON

---

## What Changes

### Current Structure (7 labs, scattered setup)

The student currently has to:

1. Manually create a catalog, schema, and volume in the Databricks UI
2. Create a compute cluster and install the Neo4j Spark Connector Maven library
3. Choose between local development or Databricks-only, each with different setup steps
4. Upload CSV and HTML files to the volume (Lab 1 is entirely about this)
5. Create a Databricks secrets scope and add four secrets via CLI
6. Run the Neo4j import notebook (Lab 2)
7. Run the vector embeddings pipeline, choosing between two embedding providers (Lab 3)
8. Export Neo4j data back to Delta tables (Lab 4)
9. Manually configure AI agents in the Databricks UI (Labs 5-6)
10. Run the augmentation agent (Lab 7)

That is a lot of setup before anyone learns anything about graphs.

### Proposed Structure

The student would:

1. Create a Dedicated cluster with the Neo4j Spark Connector (documented prerequisite)
2. Run the Required Setup notebook (creates catalog, schema, volume, copies data, stores Neo4j credentials)
3. Run the Neo4j Import notebook (loads all structured data plus pre-computed document graph with embeddings)
4. Work through Labs 4 through 7 as they exist today

---

## Proposed File Layout

```
graph-augmented-ai-workshop/
    labs/
        0 - Required Setup.py
        1 - Neo4j Import.py
        Includes/
            config.yaml
            _lib/
                setup_orchestrator.py
                neo4j_import.py
            data/
                csv/         (7 CSV files)
                html/        (14 HTML files)
                embeddings/  (pre-computed embedding JSON)
    lab_4_neo4j_to_lakehouse/
        (stays as-is)
    lab_5_ai_agents/
        (stays as-is)
    lab_6_multi_agent/
        (stays as-is)
    lab_7_augmentation_agent/
        (stays as-is)
    lab_setup/
        agent_modules/
            generate_embeddings.py
        upload.sh
        submit.sh
        clean.sh
        .env.example
        README.md
    solutions/
        (stays as-is)
    docs/
    slides/
    README.md
```

---

## How Each Piece Works

### 0 - Required Setup

This is the single entry point for all environment preparation. The student runs it once and everything is ready. Behind the scenes it does:

- Creates the catalog and schema (using a simple naming convention based on the student's username)
- Creates a volume for data files
- Copies all CSV files, HTML files, and the pre-computed embeddings JSON from Includes/data/ into the volume
- Prompts the student to enter their Neo4j connection details (URI, username, password) using Databricks notebook widgets and stores them as Databricks secrets, or verifies that the secrets already exist
- Validates that the Neo4j instance is reachable
- Displays a summary of everything that was created

The student does not need to touch the Databricks CLI, create anything manually in the UI, or understand volumes. They just run the notebook.

The config.yaml file in Includes controls the catalog prefix, schema name, secret scope name, and embedding model metadata.

### 1 - Neo4j Import

This is the single step that loads all data into Neo4j using the Spark Connector. It:

- Reads the CSV files from the Databricks volume
- Creates the full graph schema (7 node types, 7 relationship types, all constraints and indexes)
- Loads all structured data (customers, accounts, banks, transactions, positions, stocks, companies)
- Reads the pre-computed embeddings JSON from the volume
- Creates Document and Chunk nodes with their embedding vectors already populated
- Creates the vector index and full-text index on Chunk nodes
- Creates relationships: FROM_DOCUMENT, NEXT_CHUNK, and DESCRIBES (linking documents to the entities they mention)

After this notebook runs, Neo4j has the complete graph: structured financial data plus the document/chunk layer with embeddings and search indexes. The student does not need to run anything else before starting Lab 4.

The notebook includes markdown cells explaining what embeddings are, how they were generated (pointing to the lab_setup script), and what the document graph structure looks like. Students learn the concepts without waiting for the computation.

### Labs 4 through 7

These stay in their current directory structure and format. The only change is that they no longer need to worry about whether embeddings exist or whether the graph is fully loaded. The import step guarantees a complete graph before students reach these labs.

- **Lab 4 (Export to Lakehouse):** Exports Neo4j graph to Delta tables using the Spark Connector. Stays as-is.
- **Lab 5 (AI Agents):** README with UI walkthrough for creating Genie and Knowledge agents. Stays as-is.
- **Lab 6 (Multi-Agent):** README with configuration guide and sample queries. Stays as-is.
- **Lab 7 (Augmentation Agent):** DSPy-based graph augmentation. Stays as-is.

---

## What Gets Eliminated

- **Lab 1 as a standalone lab.** File upload becomes part of the setup notebook.
- **Lab 2 as a standalone lab.** Neo4j import becomes the single import notebook.
- **Lab 3 as a standalone lab.** Embeddings are pre-computed. The import notebook loads them. The concepts are explained in the import notebook markdown.
- **The dual execution model.** No more .env files, uv sync, local Python scripts alongside notebooks.
- **pyproject.toml, uv.lock, .env.sample** as student-facing concerns.
- **Per-lab README files for Labs 1, 2, and 3.** Instructions move into the notebook markdown cells.
- **The scripts/ directory.** Secret setup is handled by the setup notebook.
- **Scattered root-level docs.** AUGMENTATION.md, VECTOR.md, EMBED.md either move into relevant notebook markdown or into docs/ for reference.

---

## What Gets Kept

- **Labs 4 through 7** stay in their current structure.
- **solutions/** stays as-is for validation and headless job testing.
- **slides/** stays as-is.
- **docs/** stays for reference material.
- **databricks.yml** stays for asset bundle deployment if needed.
- **The data files** move into Includes/data/ with the addition of the pre-computed embeddings.

---

## Migration Steps (Status)

1. **DONE** - Create the lab_setup folder with the embedding generation script (upload.sh, submit.sh, .env.example, generate_embeddings.py, README.md)
2. **DONE** - Run the embedding generation script against the 14 HTML files using the latest Databricks embedding model
3. **DONE** - Commit the resulting JSON to Includes/data/embeddings/
4. **DONE** - Create the Includes directory structure with config.yaml and _lib modules (setup_orchestrator.py, neo4j_import.py)
5. **DONE** - Build the setup notebook (0 - Required Setup.py) with catalog/schema/volume creation, data copying, and Neo4j credential management via widgets and secrets
6. **DONE** - Build the import notebook (1 - Neo4j Import.py) that loads all CSV data via Spark Connector and document/chunk/embedding data from pre-computed JSON
7. **DONE** - Update the top-level README to match the new structure and simplified setup flow
8. **DONE** - Remove lab_1_databricks_upload/, lab_2_neo4j_import/, lab_3_vector_embeddings/, scripts/
9. **DONE** - Clean up root-level files (.env.sample, AUGMENTATION.md, EMBED.md, VECTOR.md)
10. **TODO** - Test end-to-end in a clean Databricks workspace with a fresh Neo4j instance

### Remaining files at root level

- `pyproject.toml` / `uv.lock` - Still used by solutions/ and lab_7 for local development
- `mlflow.db` / `mlruns/` / `results.json` - Local artifacts from development. Already in .gitignore.
- `REMOTE.md` / `gitpush.sh` - Developer utilities. Not student-facing.

### Cleaned up

- `data/` - Removed. Was duplicated in `labs/Includes/data/`. Labs 4-7 and solutions/ all read from the Databricks volume, not local files.
- `src/` - Removed. Demo utilities, not referenced by any lab or solution.

---

## Risks and Tradeoffs

**Losing the embedding teaching moment.** Students no longer generate embeddings themselves. Mitigation: the import notebook explains the concepts and points to the lab_setup script so curious students can see exactly how it was done. The pre-computed JSON includes metadata about the model and parameters used.

**Spark Connector still requires a Dedicated cluster.** This is the biggest remaining setup friction. Students must create the cluster and install the Maven library before anything works. Mitigation: the setup notebook validates the cluster configuration and gives clear error messages if the connector is missing.

**Pre-computed embeddings can go stale.** If the HTML documents change or a better embedding model comes out, someone needs to rerun lab_setup. Mitigation: the JSON includes metadata about when and how it was generated, and the lab_setup README documents the regeneration process.

**Neo4j secrets in the setup notebook.** The reference projects do not deal with external service credentials. We use Databricks notebook widgets to collect the Neo4j URI, username, and password during setup and store them as secrets. This is a clean pattern but students need to have their Neo4j connection details ready before running setup.
