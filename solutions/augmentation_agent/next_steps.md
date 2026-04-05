# Next Steps: Running the Augmentation Agent on Databricks

## What happened so far

The augmentation_agent package is built and deployed. A test run on the cluster confirmed that:

- The wheel installs correctly as a task library from a UC Volume
- Databricks authentication passes (Step 1)
- DSPy configures successfully with `BaseLM` and `model_type=responses` (Step 2)
- Step 3 fails because the MAS endpoint `mas-3ae5a347-endpoint` does not exist on this workspace

## What you need to do

### 1. Get the correct MAS endpoint name

The endpoint was created in Lab 6. Find it in the Databricks UI:

**Serving > Endpoints** — look for an endpoint whose name starts with `mas-` (the Supervisor Agent endpoint).

Or list endpoints from the CLI:

```bash
databricks serving-endpoints list --profile azure-rk-knight --output json \
  | python3 -c "import json,sys; [print(e['name']) for e in json.load(sys.stdin) if 'mas' in e['name'].lower() or 'agent' in e['name'].lower()]"
```

If no MAS endpoint exists, you need to complete Lab 6 first to create one.

### 2. Set the endpoint in .env

```bash
cd solutions
```

Edit `.env` and add (or update) the MAS endpoint name:

```
MAS_ENDPOINT_NAME=<your-actual-endpoint-name>
```

### 3. Run it

Three commands, in order:

```bash
# Build the wheel and upload to the UC Volume
python -m cli upload --wheel

# Upload the runner script to the workspace
python -m cli upload run_augmentation_agent.py

# Submit the job
python -m cli submit run_augmentation_agent.py
```

The job takes 2-4 minutes total: ~1-3 minutes for the MAS gap analysis query, then ~30-60 seconds for the four parallel DSPy analyses.

### 4. Expected output on success

```
Step 1: Databricks Authentication
  [PASS] authentication — connected to https://eastus-c3.azuredatabricks.net

Step 2: Configure DSPy
  [PASS] dspy_config — BaseLM  model_type=responses

Step 3: Query MAS for Gap Analysis
  [PASS] mas_gap_analysis — 3,421 chars

Step 4: Run DSPy Analyses
  [investment_themes] OK
  [new_entities] OK
  [missing_attributes] OK
  [implied_relationships] OK
  [PASS] analysis_investment_themes — 42.3s
  [PASS] analysis_new_entities — 42.3s
  [PASS] analysis_missing_attributes — 42.3s
  [PASS] analysis_implied_relationships — 42.3s

Step 5: Validate Results
  [PASS] total_suggestions — 14 suggestions, 6 high-confidence
  [PASS] structured_output — Pydantic models returned

Results: 8 passed, 0 failed, 8 total
SUCCESS: All checks passed
```

### 5. If it fails

**ENDPOINT_NOT_FOUND (404)** — wrong endpoint name, or the endpoint is not active. Check the Databricks Serving UI.

**Timeout / slow response** — MAS queries can take up to 3 minutes. The submit command waits by default. Use `--no-wait` and check the run in the Databricks UI if you prefer.

**Import errors** — the wheel didn't install. Re-run `python -m cli upload --wheel` and verify the file exists in the UC Volume.

**DSPy parsing errors** — the MAS response format didn't match what DSPy expected. Check the run output in the Databricks UI (the run page URL is printed by the submit command). The `provide_traceback=True` setting on `dspy.Parallel` will show the full stack trace.

## Rebuilding after code changes

If you modify any file in `augmentation_agent/`:

```bash
# Rebuild and re-upload the wheel (one command does both)
python -m cli upload --wheel

# Re-submit
python -m cli submit run_augmentation_agent.py
```

The runner script (`run_augmentation_agent.py`) only changes if you modify its imports, which is unlikely. You don't need to re-upload it on every iteration.
