#!/usr/bin/env bash
# Submit a Python script as a one-time Databricks job run.
#
# Usage:
#   ./submit.sh                                       # runs generate_embeddings.py (default)
#   ./submit.sh generate_embeddings.py                # runs a specific script
#   ./submit.sh generate_embeddings.py --no-wait      # submit without waiting
#
# Scripts live in agent_modules/ on the remote workspace.
# Credentials from .env are injected as script parameters.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load .env
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    echo "Error: $SCRIPT_DIR/.env not found. Copy .env.example to .env and fill in values."
    exit 1
fi
set -a
source "$SCRIPT_DIR/.env"
set +a

PROFILE="$DATABRICKS_PROFILE"
REMOTE_DIR="$WORKSPACE_DIR"
CLUSTER_ID="$DATABRICKS_CLUSTER_ID"

SCRIPT_NAME="${1:-generate_embeddings.py}"
NO_WAIT=""
if [[ "${2:-}" == "--no-wait" ]]; then
    NO_WAIT="--no-wait"
fi

REMOTE_PATH="$REMOTE_DIR/agent_modules/$SCRIPT_NAME"
RUN_NAME="lab_setup: $SCRIPT_NAME"

# ── Check cluster state ─────────────────────────────────────────────────────

echo "Checking cluster $CLUSTER_ID..."
CLUSTER_STATE=$(databricks clusters get --profile "$PROFILE" "$CLUSTER_ID" 2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('state','UNKNOWN'))" 2>/dev/null \
    || echo "UNKNOWN")

if [[ "$CLUSTER_STATE" != "RUNNING" ]]; then
    echo "Error: Cluster $CLUSTER_ID is $CLUSTER_STATE (expected RUNNING)."
    echo "Start the cluster in the Databricks UI and try again."
    exit 1
fi
echo "  Cluster: RUNNING"

# ── Build parameters ────────────────────────────────────────────────────────

echo "Submitting job (profile: $PROFILE)"
echo "  Script:   $REMOTE_PATH"
echo "  Run name: $RUN_NAME"

# Inject parameters from .env. Uses Python to safely handle special characters.
PARAMS=$(python3 -c "
import json, os
params = []
volume_path = os.environ.get('VOLUME_PATH', '')
if volume_path:
    params += ['--volume-path', volume_path]
    params += ['--output-path', volume_path + '/embeddings/document_chunks_embedded.json']
endpoint = os.environ.get('EMBEDDING_ENDPOINT', 'databricks-gte-large-en')
if endpoint:
    params += ['--endpoint', endpoint]
print(json.dumps(params))
")

echo "  Params:   $PARAMS"
echo "---"

# ── Submit job ───────────────────────────────────────────────────────────────

JOB_JSON=$(cat <<EOF
{
  "run_name": "$RUN_NAME",
  "tasks": [
    {
      "task_key": "run_script",
      "spark_python_task": {
        "python_file": "$REMOTE_PATH",
        "parameters": $PARAMS
      },
      "existing_cluster_id": "$CLUSTER_ID"
    }
  ]
}
EOF
)

databricks jobs submit \
    --profile "$PROFILE" \
    --json "$JOB_JSON" \
    $NO_WAIT

echo ""
echo "Job submission complete."
echo ""
echo "Next steps:"
echo "  1. Download the output JSON from: ${VOLUME_PATH}/embeddings/document_chunks_embedded.json"
echo "  2. Copy to labs/Includes/data/embeddings/document_chunks_embedded.json"
echo "  3. Commit to the repository"
