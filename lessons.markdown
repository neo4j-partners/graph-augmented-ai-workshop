# Lessons Learned: Building and Testing lab_setup

This document records what we learned while building the embedding generation pipeline and deploying it to Databricks. It captures the commands that worked, the ones that failed, and why. The goal is a reference for anyone who needs to interact programmatically with Databricks clusters, Unity Catalog Volumes, and the job submission pipeline.

---

## The Task

Generate pre-computed vector embeddings for 14 HTML documents using the Databricks foundation model endpoint (`databricks-gte-large-en`), download the output JSON, and commit it to the repo. The script runs as a one-time job on an existing Databricks cluster.

## Environment

- Azure Databricks workspace
- Databricks CLI configured with a named profile (`azure-rk-knight`)
- Dedicated cluster with Neo4j Spark Connector (Maven library)
- Unity Catalog with a managed catalog (`mypoutine`), schema (`graphenrichment`), and volume (`graphenrichment`)

---

## What Worked

### Job Submission via `databricks jobs submit`

The `submit.sh` script mirrors the `solutions/` pattern. It checks cluster state, builds a parameter list from `.env`, and submits a one-time run.

```bash
# Check cluster is running
databricks clusters get --profile "$PROFILE" "$CLUSTER_ID" \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('state','UNKNOWN'))"

# Submit a one-time job
databricks jobs submit --profile "$PROFILE" --json "$JOB_JSON"
```

Parameters are injected as command-line arguments via `spark_python_task.parameters`. The script on the cluster receives them through `argparse`.

The job completed in 20 seconds: 14 documents, 20 chunks, 1024-dimensional embeddings, 544KB output.

### Uploading Files to Volumes via the REST Files API

The only reliable way to upload files to Unity Catalog Volumes from a local machine is the REST Files API. The endpoint is `PUT /api/2.0/fs/files/{path}`.

```bash
HOST="https://adb-XXXXXXXXX.X.azuredatabricks.net"
TOKEN=$(databricks auth token --profile "$PROFILE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl -s -o /dev/null -w "%{http_code}" -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@local_file.html" \
  "$HOST/api/2.0/fs/files/Volumes/catalog/schema/volume/html/file.html"
```

A 204 response means success. This works for both creating new files and overwriting existing ones.

### Downloading Files from Volumes via the REST Files API

Same endpoint, GET method.

```bash
curl -s -o local_output.json \
  -H "Authorization: Bearer $TOKEN" \
  "$HOST/api/2.0/fs/files/Volumes/catalog/schema/volume/embeddings/document_chunks_embedded.json"
```

### Getting Auth Credentials from the CLI

```bash
# Get the workspace host URL
databricks auth env --profile "$PROFILE" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["env"]["DATABRICKS_HOST"])'

# Get a bearer token
databricks auth token --profile "$PROFILE" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
```

### Creating Directories on Volumes via Cluster Execution

Volume subdirectories can be created by running Python on the cluster through the Command Execution API. Volumes appear as regular filesystem paths at `/Volumes/catalog/schema/volume/`.

```bash
# Step 1: Create an execution context
databricks api post /api/1.2/contexts/create \
  --profile "$PROFILE" \
  --json '{"clusterId": "CLUSTER_ID", "language": "python"}'
# Returns: {"id": "CONTEXT_ID"}

# Step 2: Execute a command
databricks api post /api/1.2/commands/execute \
  --profile "$PROFILE" \
  --json '{
    "clusterId": "CLUSTER_ID",
    "contextId": "CONTEXT_ID",
    "language": "python",
    "command": "import os; os.makedirs(\"/Volumes/catalog/schema/volume/html\", exist_ok=True)"
  }'
# Returns: {"id": "COMMAND_ID"}

# Step 3: Poll for the result
databricks api get \
  "/api/1.2/commands/status?clusterId=CLUSTER_ID&contextId=CONTEXT_ID&commandId=COMMAND_ID" \
  --profile "$PROFILE"
```

The Command Execution API is asynchronous. Step 2 returns a command ID immediately. Step 3 must be polled until `status` is `Finished`.

### Running SQL on a Cluster

Same Command Execution API, with `"language": "sql"`:

```bash
databricks api post /api/1.2/commands/execute \
  --profile "$PROFILE" \
  --json '{
    "clusterId": "CLUSTER_ID",
    "contextId": "CONTEXT_ID",
    "language": "sql",
    "command": "CREATE SCHEMA IF NOT EXISTS mypoutine.graphenrichment"
  }'
```

Multiple statements can be separated by semicolons. The result of the last statement is returned.

### Fetching Job Run Errors

When a job fails, the error details are in the task-level run output, not the top-level run.

```bash
# Get the top-level run (contains task run IDs)
databricks jobs get-run --profile "$PROFILE" RUN_ID

# Get error output from the specific task
databricks api get "/api/2.1/jobs/runs/get-output?run_id=TASK_RUN_ID" --profile "$PROFILE"
```

The top-level `get-output` fails with "Retrieving the output of runs with multiple tasks is not supported." Always use the task-level run ID.

### Workspace File Upload

Uploading Python scripts to the workspace (for job execution) works with the standard CLI:

```bash
databricks workspace import \
  --profile "$PROFILE" \
  --format AUTO \
  --overwrite \
  local_script.py /Workspace/Users/user@example.com/path/script.py
```

This is what `upload.sh` uses. Workspace paths (`/Workspace/...`) and volume paths (`/Volumes/...`) are different systems with different APIs.

---

## What Failed

### `databricks fs cp` Does Not Work for Unity Catalog Volumes

```bash
databricks fs cp local_file.html /Volumes/catalog/schema/volume/html/file.html --profile "$PROFILE"
# Error: no such directory: /Volumes/catalog/schema/volume/html/file.html
```

The `databricks fs` commands operate on DBFS (the legacy Databricks filesystem), not Unity Catalog Volumes. Even though the path syntax looks similar, `fs cp`, `fs ls`, and `fs mkdirs` all fail with "no such directory" when targeting Volume paths.

Use the REST Files API (`/api/2.0/fs/files/...`) instead.

### `databricks fs mkdirs` Does Not Work for Volumes

```bash
databricks fs mkdirs /Volumes/catalog/schema/volume/html --profile "$PROFILE"
# Error: mkdir /Volumes/mypoutine: permission denied
```

Same root cause as above. Volume directories must be created from the cluster side using `os.makedirs()`.

### `CREATE CATALOG` Fails Without Managed Storage Location

```sql
CREATE CATALOG IF NOT EXISTS mypoutine
-- AnalysisException: Metastore storage root URL does not exist.
-- Default Storage is enabled in your account. You can use the UI to create
-- a new catalog using Default Storage, or please provide a storage location.
```

On Azure Databricks with Default Storage enabled, catalogs must be created through the UI (which assigns managed storage automatically) or with an explicit `MANAGED LOCATION`. The SQL command without a location fails even though the user has `CREATE CATALOG` privileges.

Creating schemas and volumes within an existing catalog works fine via SQL.

### Command Execution API Without a Context ID

```bash
databricks api post /api/1.2/commands/execute \
  --json '{"clusterId": "CLUSTER_ID", "language": "sql", "command": "..."}'
# Error: IllegalArgumentException: requirement failed: missing contextId
```

The Command Execution API requires a context. Always call `/api/1.2/contexts/create` first and pass the returned `contextId` to every subsequent `commands/execute` call.

### SQL Statements API Without a Warehouse

```bash
databricks api post /api/2.0/sql/statements \
  --json '{"warehouse_id": "", "statement": "CREATE SCHEMA ...", "wait_timeout": "30s"}'
# Error: "" is not a valid endpoint id.
```

The SQL Statements API (`/api/2.0/sql/statements`) requires a SQL Warehouse, not a cluster. If you only have a Dedicated cluster, use the Command Execution API (`/api/1.2/commands/execute`) instead.

### First Job Run Failed: HTML Files Not on Volume

```
FileNotFoundException: No such file or directory /Volumes/.../html
```

The `generate_embeddings.py` script initially used `dbutils.fs.ls()` to read HTML files from the volume. On the first run, the volume existed but the HTML files had not been uploaded yet. The setup notebook (which copies files to the volume) had not been run, and we were testing lab_setup in isolation.

The fix was to upload the HTML files via the Files API before submitting the job.

### `dbutils.fs` Is Unnecessary for Volume Access on Clusters

The original `generate_embeddings.py` used `dbutils.fs.ls()`, `dbutils.fs.head()`, and `dbutils.fs.put()` for all volume file operations, with `try/except NameError` fallbacks for local execution. This created two code paths and introduced bugs in the fallback logic (a no-op string replace that made the local path identical to the volume path).

Since Unity Catalog Volumes are mounted as regular filesystem paths on Databricks clusters, all three calls were replaced with standard Python:
- `dbutils.fs.ls(path)` became `os.listdir(path)`
- `dbutils.fs.head(path, limit)` became `open(path).read()` (no size limit)
- `dbutils.fs.put(path, content)` became `open(path, "w").write(content)`

This eliminates the dual code path entirely. The same code runs on the cluster and locally (if the path exists).

---

## Key Takeaways

**Two file systems, two APIs.** Workspace files (`/Workspace/...`) are managed by `databricks workspace import/export`. Volume files (`/Volumes/...`) are managed by the REST Files API (`/api/2.0/fs/files/...`). The `databricks fs` commands work for neither in a reliable way when targeting UC Volumes.

**Volumes are regular filesystem paths on the cluster.** Code running on a Databricks cluster can use `os.listdir()`, `os.makedirs()`, `open()`, `shutil.copy2()`, and any standard Python file I/O on `/Volumes/...` paths. No `dbutils.fs` required, though `dbutils.fs.ls()` also works.

**The Command Execution API is the escape hatch.** When you need to run arbitrary SQL or Python on a cluster from outside Databricks (no notebook, no job), the Command Execution API (`/api/1.2/contexts/create` + `/api/1.2/commands/execute`) is the tool. It is asynchronous and requires polling.

**Job error output is at the task level.** A submitted job can have multiple tasks. The `get-output` endpoint only works on individual task run IDs, not the top-level run ID. Get the task run ID from `databricks jobs get-run`, then call `get-output` on that.

**Catalog creation needs the UI on Azure.** With Default Storage enabled, `CREATE CATALOG` via SQL fails without a `MANAGED LOCATION`. Create catalogs through the Databricks UI, then use SQL for schemas and volumes within them.

**Neo4j Python driver rejects keyword parameters ending with `_`.** When calling `driver.execute_query()`, passing query parameters as keyword arguments like `documents_=data` fails with `keyword parameters must not end with a single '_'`. Use the `parameters_` dictionary instead:

```python
# Fails:
driver.execute_query(query, documents_=documents)

# Works:
driver.execute_query(query, parameters_={"documents": documents})
```

**Prefer `os` over `dbutils.fs` for volume file operations.** Code running on a Databricks cluster can use standard Python I/O for `/Volumes/...` paths. Using `dbutils.fs` creates a second code path for local testing and introduces subtle bugs. The only reason to use `dbutils.fs` is for DBFS paths (`dbfs:/...`), which Unity Catalog Volumes are not.
