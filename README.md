[![Databricks](https://img.shields.io/badge/Databricks-Solution_Accelerator-FF3621?style=for-the-badge&logo=databricks)](https://databricks.com)
[![Unity Catalog](https://img.shields.io/badge/Unity_Catalog-Enabled-00A1C9?style=for-the-badge)](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
[![Neo4j](https://img.shields.io/badge/Neo4j-Partner-4581C3?style=for-the-badge&logo=neo4j)](https://neo4j.com/partners/databricks/)

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

In Databricks, go to **Workspace** > right-click your user folder > **Import** > **URL** and paste:

```
<DBC_URL>
```

This imports all lab notebooks into your workspace. Data files (CSV, HTML, embeddings) are downloaded automatically from GitHub when you run the setup notebook.

> **Alternative:** If you prefer to import manually, clone the repo and use the Databricks CLI:
> ```bash
> git clone https://github.com/neo4j-partners/graph-enrichment.git
> databricks workspace import-dir graph-enrichment/labs /Users/<your-email>/graph-enrichment
> ```

### 3. Run Required Setup

Open and run **0 - Required Setup**. It will:

- Create a catalog, schema, and volume based on your username
- Download all data files (CSV, HTML, and pre-computed embeddings) from GitHub into your volume
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
│   ├── 4 - Neo4j to Lakehouse.py             # Export graph to Delta tables
│   ├── 5 - AI Agents.py                      # Genie + Knowledge Assistant
│   ├── 6 - Supervisor Agent.py               # Multi-agent coordinator
│   └── Includes/
│       ├── config.py                          # Workshop configuration (imported via %run)
│       ├── _lib/
│       │   ├── setup_orchestrator.py          # Setup + GitHub data download
│       │   └── neo4j_import.py                # Import logic
│       └── data/
│           ├── csv/                           # Source CSV files (7 files)
│           ├── html/                          # Source HTML documents (14 files)
│           └── embeddings/                    # Pre-computed embedding vectors
├── build_dbc.py                               # Script to package labs/ as a .dbc archive
├── lab_7_augmentation_agent/                  # Lab 7: Graph Augmentation
├── full_demo/                                 # Reference implementation, validation scripts, and admin tools
├── docs/                                      # Reference documentation
├── slides/                                    # Marp presentations
├── pyproject.toml                             # Python deps (full_demo/ and lab_7 local dev)
└── README.md                                  # This file
```

## Cluster Requirements

| Requirement | Value |
|-------------|-------|
| Access Mode | Dedicated |
| Runtime | 13.3 LTS ML or higher (Spark 3.x) |
| Maven Library | `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3` |

The **ML Runtime** is recommended because it includes `neo4j` and `beautifulsoup4`. If using a standard (non-ML) runtime, install these Python packages as cluster libraries:

| Package | Used By |
|---------|---------|
| `neo4j` | Import notebook (Neo4j Python driver for document graph) |
| `beautifulsoup4` | Embedding generation (`generate_embeddings.py`, not student-facing) |
| `databricks-langchain` | Embedding generation (`generate_embeddings.py`, not student-facing) |

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

## Project Support

Please note the code in this project is provided for your exploration only, and are not formally supported by Databricks with Service Level Agreements (SLAs). They are provided AS-IS and we do not make any guarantees of any kind. Please do not submit a support ticket relating to any issues arising from the use of these projects. The source in this project is provided subject to the Databricks [License](./LICENSE.md). All included or referenced third party libraries are subject to the licenses set forth below.

Any issues discovered through the use of this project should be filed as GitHub Issues on the Repo. They will be reviewed as time permits, but there are no formal SLAs for support.

## Third-Party Package Licenses

| library | description | license | source |
|---------|-------------|---------|--------|
| neo4j | Neo4j Python driver | Apache 2.0 | https://github.com/neo4j/neo4j-python-driver |
| neo4j-connector-apache-spark | Neo4j Spark Connector | Apache 2.0 | https://github.com/neo4j/neo4j-spark-connector |
| dspy | Structured reasoning framework | MIT | https://github.com/stanfordnlp/dspy |
| langchain | LLM orchestration | MIT | https://github.com/langchain-ai/langchain |
| langgraph | Agent workflow graphs | MIT | https://github.com/langchain-ai/langgraph |
| databricks-langchain | Databricks LLM integration | Apache 2.0 | https://github.com/langchain-ai/langchain-databricks |
| pydantic | Data validation | MIT | https://github.com/pydantic/pydantic |
| mlflow | ML experiment tracking | Apache 2.0 | https://github.com/mlflow/mlflow |
| beautifulsoup4 | HTML parsing | MIT | https://www.crummy.com/software/BeautifulSoup/ |
| sentence-transformers | Embedding models | Apache 2.0 | https://github.com/UKPLab/sentence-transformers |

&copy; 2026 Databricks, Inc. All rights reserved. The source in this notebook is provided subject to the [Databricks License](https://databricks.com/db-license-source). All included or referenced third party libraries are subject to the licenses set forth above.
