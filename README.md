# Graph Augmented AI Workshop

A hands-on workshop for building graph-augmented AI systems using Neo4j and Databricks. This project demonstrates how to combine Neo4j's graph database capabilities with Databricks AI/BI agents to create a multi-agent architecture that bridges structured graph data and unstructured documents.

## Overview

This workshop walks through building a graph augmentation pipeline that leverages:

- **Neo4j** for storing and querying connected data as a property graph
- **Databricks Unity Catalog** for governed data storage (Delta Lake tables and document volumes)
- **Neo4j Spark Connector** for bidirectional data transfer between the lakehouse and graph database
- **Databricks Genie Agent** for natural language queries against structured Delta Lake tables
- **Databricks Knowledge Assistant** for RAG-based retrieval over unstructured documents
- **Supervisor Agent** for coordinating structured and unstructured data analysis
- **DSPy Framework** for structured reasoning and graph schema augmentation suggestions

```
┌─────────────────┐     ┌─────────────────────────────────────────────────┐
│                 │     │              DATABRICKS LAKEHOUSE               │
│   Neo4j Graph   │────>│  Delta Tables <──> Genie Agent                  │
│                 │     │  UC Volumes   <──> Knowledge Assistant              │
│  7 node types   │     │                         │                       │
│  7 rel types    │<────│         Supervisor Agent                  │
│                 │     │                         │                       │
│                 │     │         DSPy Augmentation Agent                 │
└─────────────────┘     └─────────────────────────────────────────────────┘
```

### Data Model

The sample graph models a retail investment domain with **customers**, **accounts**, **banks**, **transactions**, **positions**, **stocks**, and **companies**.

```
Customer ──owns──> Account ──held at──> Bank
                      │
                      ├──performs──> Transaction ──benefits──> Account
                      │
                      └──holds──> Position ──of──> Stock ──issued by──> Company
```

For detailed schema documentation including properties, constraints, indexes, and sample queries, see [docs/SCHEMA_MODEL_OVERVIEW.md](./docs/SCHEMA_MODEL_OVERVIEW.md).

## Setup

### 1. Create a Databricks Cluster

Create a **Dedicated** cluster with the Neo4j Spark Connector:

1. Navigate to **Compute** > **Create Compute**
2. **Access mode**: **Dedicated** (required for the Neo4j Spark Connector)
3. **Databricks Runtime**: 13.3 LTS or higher
4. Click **Libraries** > **Install New** > **Maven**
5. Enter coordinates: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
6. Click **Install** and verify the library status shows "Installed"

### 2. Import the Workshop

1. Clone or download this repository
2. In Databricks, go to **Workspace**
3. Click **Import** and upload the `labs/` folder

### 3. Run Required Setup

Open and run **labs/0 - Required Setup**. It will:

- Create a catalog, schema, and volume based on your username
- Copy all data files (CSV, HTML, and pre-computed embeddings) to the volume
- Prompt you for Neo4j connection details and store them as Databricks secrets
- Verify the Neo4j connection

### 4. Run Neo4j Import

Open and run **labs/1 - Neo4j Import**. It loads all data into Neo4j in a single step:

- 7 node types and 7 relationship types from CSV files via the Spark Connector
- 14 documents with pre-computed embedding vectors for hybrid search

After this notebook completes, Neo4j has the full graph and you're ready for the labs.

## Labs

| Lab | Description | Link |
|-----|-------------|------|
| **Setup** | Create catalog, schema, volume, and configure Neo4j credentials | [0 - Required Setup](./labs/0%20-%20Required%20Setup.py) |
| **Import** | Load all CSV and document data into Neo4j | [1 - Neo4j Import](./labs/1%20-%20Neo4j%20Import.py) |
| **Lab 4** | Export Neo4j graph data to Databricks Delta Lake tables | [lab_4_neo4j_to_lakehouse](./lab_4_neo4j_to_lakehouse/README.md) |
| **Lab 5** | Create Databricks AI agents (Genie and Knowledge Assistant) | [lab_5_ai_agents](./lab_5_ai_agents/README.md) |
| **Lab 6** | Build Supervisor Agent with sample queries | [lab_6_multi_agent](./lab_6_multi_agent/README.md) |
| **Lab 7** | Graph augmentation agent for entity extraction | [lab_7_augmentation_agent](./lab_7_augmentation_agent/README.md) |

## Project Structure

```
graph-enrichment/
├── labs/
│   ├── 0 - Required Setup.py                 # Environment setup notebook
│   ├── 1 - Neo4j Import.py                   # Single-step Neo4j data import
│   └── Includes/
│       ├── config.yaml                        # Workshop configuration
│       ├── _lib/
│       │   ├── setup_orchestrator.py          # Setup logic
│       │   └── neo4j_import.py                # Import logic
│       └── data/
│           ├── csv/                           # Source CSV files (7 files)
│           ├── html/                          # Source HTML documents (14 files)
│           └── embeddings/                    # Pre-computed embedding vectors
├── lab_4_neo4j_to_lakehouse/                  # Lab 4: Export to Lakehouse
├── lab_5_ai_agents/                           # Lab 5: AI Agents
├── lab_6_multi_agent/                         # Lab 6: Supervisor Agent
├── lab_7_augmentation_agent/                  # Lab 7: Graph Augmentation
├── lab_setup/                                 # Tooling to regenerate embeddings
│   ├── agent_modules/
│   │   └── generate_embeddings.py
│   ├── upload.sh
│   ├── submit.sh
│   └── clean.sh
├── solutions/                                 # Headless validation scripts
├── docs/                                      # Reference documentation
├── slides/                                    # Marp presentations
├── pyproject.toml                             # Python deps (solutions/ and lab_7 local dev)
└── README.md                                  # This file
```

## Cluster Requirements

| Requirement | Value |
|-------------|-------|
| Access Mode | Dedicated |
| Runtime | 13.3 LTS ML or higher (Spark 3.x) |
| Maven Library | `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3` |

The **ML Runtime** is recommended because it includes `pyyaml`, `neo4j`, and `beautifulsoup4`. If using a standard (non-ML) runtime, install these Python packages as cluster libraries:

| Package | Used By |
|---------|---------|
| `pyyaml` | Setup notebook (reads config.yaml) |
| `neo4j` | Import notebook (Neo4j Python driver for document graph) |
| `beautifulsoup4` | Embedding generation (lab_setup only, not student-facing) |
| `databricks-langchain` | Embedding generation (lab_setup only, not student-facing) |

## Secrets Reference

The setup notebook creates a `neo4j-creds` secret scope with:

| Secret | Description | Example |
|--------|-------------|---------|
| `username` | Neo4j username | `neo4j` |
| `password` | Neo4j password | `your_password` |
| `url` | Neo4j connection URI | `neo4j+s://xxx.databases.neo4j.io` |
| `volume_path` | Databricks volume path | `/Volumes/neo4j_workshop_user/raw_data/source_files` |

## Slides

The `slides/` directory contains [Marp](https://marp.app/) presentations for each lab.

```bash
npm install -g @marp-team/marp-cli
marp slides --server
```
