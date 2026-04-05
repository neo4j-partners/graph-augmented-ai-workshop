#!/usr/bin/env bash
# Clean up remote workspace and job runs.
#
# Usage:
#   ./clean.sh              # clean workspace + job runs (with confirmation)
#   ./clean.sh --workspace  # clean only remote workspace
#   ./clean.sh --runs       # clean only job runs
#   ./clean.sh --yes        # skip confirmation prompt

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
RUN_NAME_PREFIX="lab_setup:"

# Parse flags
CLEAN_WORKSPACE=true
CLEAN_RUNS=true
SKIP_CONFIRM=false

for arg in "$@"; do
    case "$arg" in
        --workspace) CLEAN_RUNS=false ;;
        --runs)      CLEAN_WORKSPACE=false ;;
        --yes|-y)    SKIP_CONFIRM=true ;;
        *)           echo "Unknown option: $arg"; exit 1 ;;
    esac
done

echo "lab_setup: cleanup (profile: $PROFILE)"
echo "---"

if [[ "$CLEAN_WORKSPACE" == true ]]; then
    echo "  Workspace:  $REMOTE_DIR (will be deleted recursively)"
fi
if [[ "$CLEAN_RUNS" == true ]]; then
    echo "  Job runs:   all one-time runs matching '$RUN_NAME_PREFIX*'"
fi
echo ""

if [[ "$SKIP_CONFIRM" == false ]]; then
    read -rp "Proceed? [y/N] " answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    echo ""
fi

# ── Clean remote workspace ───────────────────────────────────────────────────

if [[ "$CLEAN_WORKSPACE" == true ]]; then
    echo "Deleting remote workspace: $REMOTE_DIR"
    if databricks workspace rm --profile "$PROFILE" --recursive "$REMOTE_DIR" 2>/dev/null; then
        echo "  Done."
    else
        echo "  Directory does not exist or already deleted."
    fi
    echo ""
fi

# ── Clean job runs ───────────────────────────────────────────────────────────

if [[ "$CLEAN_RUNS" == true ]]; then
    echo "Finding lab_setup job runs..."

    RUNS_JSON=$(databricks api get \
        "/api/2.1/jobs/runs/list?run_type=SUBMIT_RUN&limit=100&expand_tasks=false" \
        --profile "$PROFILE" 2>/dev/null || echo '{}')

    RUN_IDS=$(echo "$RUNS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
runs = data.get('runs', [])
for r in runs:
    if r.get('run_name', '').startswith('$RUN_NAME_PREFIX'):
        print(r['run_id'], r.get('run_name', ''))
" 2>/dev/null || true)

    if [[ -z "$RUN_IDS" ]]; then
        echo "  No matching runs found."
    else
        COUNT=0
        while IFS= read -r line; do
            RUN_ID=$(echo "$line" | awk '{print $1}')
            RUN_NAME=$(echo "$line" | cut -d' ' -f2-)
            echo "  Deleting run $RUN_ID ($RUN_NAME)"
            databricks api post /api/2.1/jobs/runs/delete \
                --profile "$PROFILE" \
                --json "{\"run_id\": $RUN_ID}" 2>/dev/null || echo "    Failed to delete run $RUN_ID"
            COUNT=$((COUNT + 1))
        done <<< "$RUN_IDS"
        echo "  Deleted $COUNT run(s)."
    fi
    echo ""
fi

echo "Cleanup complete."
