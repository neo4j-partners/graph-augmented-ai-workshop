# Workshop Admin - Pre-compute Embeddings

This folder contains tooling to pre-compute vector embeddings for the workshop's HTML documents. The output JSON file ships with the workshop so students don't need to generate embeddings themselves.

**This is not student-facing.** It is only used by workshop authors when the HTML documents change or when a newer embedding model is available.

## Structure

```
workshop_admin/
├── agent_modules/
│   └── generate_embeddings.py    # Script that runs on the cluster
├── cli/
│   ├── __init__.py               # Runner config and build_params
│   └── __main__.py               # Entry point
├── pyproject.toml
├── .env.example                  # Configuration template
└── README.md
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Databricks CLI configured with a profile
- A running Databricks cluster (Dedicated mode)
- HTML files already uploaded to a Unity Catalog Volume (run the setup notebook first, or upload manually)
- Access to the Databricks foundation model embedding endpoint

## Usage

```bash
# 1. Configure
cp .env.example .env
# Edit .env with your workspace details

# 2. Install dependencies
uv sync

# 3. Upload the script to the workspace
python -m cli upload generate_embeddings.py

# 4. Submit the job on your cluster
python -m cli submit generate_embeddings.py

# 5. Check logs if needed
python -m cli logs

# 6. Download the output JSON from the volume path shown in the job output
#    e.g. /Volumes/catalog/schema/volume/embeddings/document_chunks_embedded.json

# 7. Copy to the repo
cp document_chunks_embedded.json ../labs/Includes/data/embeddings/

# 8. Commit
git add ../labs/Includes/data/embeddings/document_chunks_embedded.json
git commit -m "Update pre-computed embeddings"
```

## What generate_embeddings.py Does

1. Reads all HTML files from `{VOLUME_PATH}/html/`
2. Parses each file with BeautifulSoup, extracts clean text
3. Classifies document types (customer_profile, company_analysis, etc.)
4. Splits text into chunks (4000 chars, 200 char overlap)
5. Generates embeddings via the Databricks foundation model endpoint (1024 dimensions)
6. Writes everything to a single JSON file

## Other Commands

```bash
# Validate workspace setup
python -m cli validate

# Clean up workspace scripts and job runs
python -m cli clean --yes
```
